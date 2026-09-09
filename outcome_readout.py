"""Model-specific answer extraction without confusing Muse reasoning with its reply."""
from forking_paths.answers import parse_mmlu_answer
from forking_paths.run import extract_answers_for_branches as upstream_extract


def muse_answer(raw):
    marker="to=user<|message|>"
    if marker not in raw:
        return None
    reply=raw.rsplit(marker,1)[1]
    endings=[reply.index(x) for x in ("<|eot|>","<|end_of_text|>") if x in reply]
    if not endings: return None
    return parse_mmlu_answer(reply[:min(endings)])


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


def inspect_continuation(model, base, branch, cont, cap):
    """Strict outcome readout: a capped generation is never a final answer.

    Upstream strips EOS; len(cont)<cap (or a forced EOS) establishes stopping.
    The exact stripped EOS token cannot be recovered and is not fabricated.
    """
    complete = branch.tok_id in model.eos_ids or len(cont)<cap
    ids=base.gen_ids[:branch.idx]+[branch.tok_id]+cont
    raw=model.tokenizer.decode(ids,skip_special_tokens=False)
    text=model.tokenizer.decode(cont,skip_special_tokens=False)
    is_muse=getattr(model,'is_muse',False)
    channel=('user' if 'to=user<|message|>' in raw else 'reasoning') if is_muse else 'not_applicable'
    label=None; source='incomplete'
    if complete:
        if is_muse:
            # An EOS removed by the upstream sampler still terminates the reply.
            label=muse_answer(raw+'<|eot|>')
            source='muse_completed_user' if label else 'unparsed'
        else:
            label=parse_mmlu_answer(raw)
            source='completed_regex' if label else 'unparsed'
    return dict(label=label or 'Other',label_source=source,channel_reached=channel,
        stop_reason='eos' if complete else 'length',
        stop_reason_evidence='forced_eos' if branch.tok_id in model.eos_ids else 'inferred_from_stripped_length',
        generated_tokens=len(cont),continuation_text=text,full_response_text=raw)
