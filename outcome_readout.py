"""Model-specific answer extraction without confusing Muse reasoning with its reply."""
from forking_paths.answers import parse_mmlu_answer
from forking_paths.run import extract_answers_for_branches as upstream_extract


def muse_answer(raw):
    marker="to=user<|message|>"
    if marker not in raw:
        return None
    reply=raw.rsplit(marker,1)[1]
    if "<|eot|>" not in reply:
        return None
    return parse_mmlu_answer(reply.split("<|eot|>",1)[0])


def extract_answers_for_branches(model, base, branches, continuations, cfg, suffix, diag_sample=0):
    if not getattr(model,"is_muse",False):
        return upstream_extract(model,base,branches,continuations,cfg,suffix,diag_sample=diag_sample)
    answers=[]; total=resolved=0
    for branch,draws in zip(branches,continuations):
        labels=[]
        for cont in draws:
            ids=base.gen_ids[:branch.idx]+[branch.tok_id]+cont
            # The upstream sampler removes its terminal EOS. A short continuation
            # stopped by EOS (or an EOS branch) has completed the turn.
            complete=branch.tok_id in model.eos_ids or len(cont)<cfg.cont_max_tokens
            raw=model.tokenizer.decode(ids,skip_special_tokens=False)
            if complete and "<|eot|>" not in raw:
                raw+="<|eot|>"
            label=muse_answer(raw)
            labels.append(label or "Other");total+=1;resolved+=label is not None
        answers.append(labels)
    return answers,dict(n_continuations=total,n_regex_resolved=resolved,
        regex_coverage=resolved/total if total else None,n_logit_fallback=0,
        n_other=total-resolved,regex_vs_logit_agreement=None,
        extractor="Muse completed to=user channel; unfinished/unparseable -> Other")
