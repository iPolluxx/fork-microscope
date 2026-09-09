"""Model-native HF adapter. Reuses upstream token-space decoding and sampling."""
import inspect
import torch
from transformers import AutoConfig, AutoModelForCausalLM, AutoModelForImageTextToText, AutoProcessor, AutoTokenizer
from forking_paths.model import ForkingModel
from forking_paths.prompts import format_mmlu_base, format_mmlu_instruct_user


class AttachedModel(ForkingModel):
    def __init__(self, model_id, revision="main", device="auto", gen_batch=4):
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cuda" and not torch.cuda.is_available():
            raise ValueError("CUDA is unavailable in this runtime. Choose CPU or run the dashboard on a GPU machine.")
        self.device, self.gen_batch, self.seed = device, gen_batch, 0
        self.enable_prefix_caching = False  # Ordinary generate caching; no cross-branch reuse claim.
        torch.set_num_threads(min(4, torch.get_num_threads()))
        config = AutoConfig.from_pretrained(model_id, revision=revision, trust_remote_code=False)
        self.is_muse = config.model_type == "muse_glimmer"
        if self.is_muse:
            processor = AutoProcessor.from_pretrained(model_id, revision=revision, trust_remote_code=False)
            self.tokenizer = processor.tokenizer
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision, trust_remote_code=False)
        loader = AutoModelForImageTextToText if self.is_muse else AutoModelForCausalLM
        dtype = torch.float32 if device == "cpu" else (torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16)
        self.model = loader.from_pretrained(model_id, revision=revision,
            dtype=dtype, trust_remote_code=False, use_safetensors=True,
            device_map={"": device}).eval()
        text_config = getattr(self.model.config, "text_config", self.model.config)
        ids = self.model.generation_config.eos_token_id
        self.eos_ids = list(ids) if isinstance(ids, list) else ([] if ids is None else [ids])
        if self.tokenizer.eos_token_id is not None:
            self.eos_ids = sorted(set(self.eos_ids + [self.tokenizer.eos_token_id]))
        if self.is_muse:
            vocab = self.tokenizer.get_vocab()
            if "<|eot|>" not in vocab:
                raise ValueError("Muse tokenizer lacks its expected end-of-turn marker.")
            self.eos_ids = sorted(set(self.eos_ids + [vocab[x] for x in ("<|eot|>","<|end_of_text|>") if x in vocab]) - {vocab.get("<|eom|>")})
        if self.tokenizer.pad_token_id is None:
            if self.tokenizer.eos_token_id is None:
                raise ValueError("This tokenizer needs an EOS or padding token.")
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.padding_side = "left"
        self.info = dict(model_id=model_id, requested_revision=revision,
            resolved_revision=getattr(self.model.config, "_commit_hash", None), device=device,
            dtype=str(dtype), parameters=sum(p.numel() for p in self.model.parameters()),
            context_limit=getattr(text_config, "max_position_embeddings", None),
            vocab_size=text_config.vocab_size, architecture=type(self.model).__name__,
            chat_template=bool(self.tokenizer.chat_template), batch_size=gen_batch)

    def prompt(self, question, choices, mode):
        if mode == "chat":
            if not self.tokenizer.chat_template:
                raise ValueError("This tokenizer has no chat template. Choose base/completion mode.")
            return list(self.tokenizer.apply_chat_template(
                [{"role": "user", "content": format_mmlu_instruct_user(question, choices)}],
                tokenize=True, add_generation_prompt=True, return_dict=False))
        return list(self.tokenizer(format_mmlu_base(question, choices), add_special_tokens=True)["input_ids"])

    def prompt_text(self, text, mode):
        if mode == 'chat':
            if not self.tokenizer.chat_template:
                raise ValueError('This tokenizer has no chat template. Choose base/completion mode.')
            return list(self.tokenizer.apply_chat_template(
                [{'role': 'user', 'content': text}], tokenize=True,
                add_generation_prompt=True, return_dict=False))
        return list(self.tokenizer(text, add_special_tokens=True)['input_ids'])

    @torch.no_grad()
    def logit_read_letters(self, prefixes, seed=0):
        self.letter_ids = [self.tokenizer(x, add_special_tokens=False)['input_ids'] for x in 'ABCD']
        if any(len(x) != 1 for x in self.letter_ids) or len({x[0] for x in self.letter_ids}) != 4:
            raise ValueError('Legacy logit readout requires distinct single-token A–D labels.')
        # Process one prefix at a time to bound answer-extraction memory.
        out = []
        supports_last = "logits_to_keep" in inspect.signature(self.model.forward).parameters or self.is_muse
        for prefix in prefixes:
            ids = torch.tensor([prefix], device=self.device)
            kw = {"logits_to_keep": 1} if supports_last else {}
            logits = self.model(ids, attention_mask=torch.ones_like(ids), **kw).logits[0, -1]
            out.append("ABCD"[int(logits[[x[0] for x in self.letter_ids]].argmax())])
        return out

    def draw_branch(self, branch, count, cap, temperature, seed, check):
        if branch.tok_id in self.eos_ids:
            return [[] for _ in range(count)]
        result = []
        for lo in range(0, count, self.gen_batch):
            check()
            n = min(self.gen_batch, count-lo)
            sampled, _ = self.resample([branch.prefix_ids], n=n, max_tokens=cap,
                temperature=temperature, seed=(seed+lo) % (2**31-1))
            result.extend(sampled[0])
        return result
