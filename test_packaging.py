"""Protocol boundaries and portable configuration checks."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from fork_cli import check_upstream
from live_service import grid_plan
from outcome_readout import muse_answer, extract_answers_for_branches

ROOT = Path(__file__).resolve().parent


def test_upstream_pin_and_checkout_assets():
    check_upstream()
    assert (ROOT / "public/fork-microscope/live.html").is_file()


@pytest.mark.parametrize("profile", ["cpu-smoke", "muse-smoke"])
def test_profiles_are_versioned_and_have_valid_grids(profile):
    config = json.loads((ROOT / f"configs/{profile}.json").read_text())
    assert set(config) == {"load", "base", "run"}
    assert len(config["load"]["revision"]) == 40
    grids = grid_plan(config["run"], config["base"]["max_tokens"] - 1)
    assert len(grids["pass_1"]) == 2 and "second" not in grids


def test_only_completed_user_channel_supplies_muse_answer():
    reasoning = "<|channel|>analysis<|message|>The answer is (A).<|eom|>"
    assert muse_answer(reasoning) is None
    assert muse_answer(reasoning + "to=user<|message|>The answer is (B).") is None
    assert muse_answer(reasoning + "to=user<|message|>The answer is (B).<|eot|>") == "B"


def test_muse_truncation_is_other_and_stripped_eos_is_restored():
    # Same visible reply, but one draw used its full cap and never completed.
    tok = SimpleNamespace(decode=lambda *a, **kw: "to=user<|message|>The answer is (B).")
    model = SimpleNamespace(is_muse=True, eos_ids=[99], tokenizer=tok)
    base = SimpleNamespace(gen_ids=[1, 2, 3])
    branch = SimpleNamespace(idx=1, tok_id=5)
    answers, diag = extract_answers_for_branches(model, base, [branch],
        [[[7], [7, 8]]], SimpleNamespace(cont_max_tokens=2), [])
    assert answers == [["B", "Other"]]
    assert diag["n_logit_fallback"] == 0
    assert diag["n_other"] == 1


def test_native_chat_template_returns_integer_ids_not_mapping_keys():
    from live_model import AttachedModel
    calls = []
    def template(*args, **kwargs):
        calls.append(kwargs)
        return [11, 12] if kwargs.get("return_dict") is False else {"input_ids": [11, 12]}
    adapter = AttachedModel.__new__(AttachedModel)
    adapter.tokenizer = SimpleNamespace(chat_template="native", apply_chat_template=template)
    assert adapter.prompt("Question?", ["one", "two", "three", "four"], "chat") == [11, 12]



def test_anticipation_profile_keeps_prompt_and_pilot_separate():
    from outcome_readout import validate_answers
    config=json.loads((ROOT/'configs/muse-anticipation.json').read_text())
    assert config['base']['prompt']=='In your reasoning do you anticipate future turns in the conversation when you give your final output?'
    assert validate_answers(config['base']['answers'])==['yes','no','uncertain']
    assert grid_plan(config['run'],2047)['pass_1']==[0,64,128]
    assert config['run']['passes'][0]['samples']==5
    assert config['run']['cont_max']==2048 and not config['run']['dense']
