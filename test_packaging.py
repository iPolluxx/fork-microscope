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


def test_connect_creates_token_and_keeps_worker_on_loopback(monkeypatch,capsys):
    import os, sys, fork_cli, microscope_server
    from worker_connection import WorkerAccess
    monkeypatch.delenv('FORK_WORKER_TOKEN',raising=False)
    monkeypatch.setattr(fork_cli,'check_upstream',lambda:None)
    monkeypatch.setattr(sys,'argv',['fork-microscope'])
    calls=[]
    monkeypatch.setattr(microscope_server,'main',lambda:calls.append(list(sys.argv)))
    fork_cli.connect('https://dashboard.example.org/',8790)
    token=os.environ['FORK_WORKER_TOKEN']
    access=WorkerAccess('127.0.0.1',token,['https://dashboard.example.org'])
    assert access.authorize('127.0.0.1:8790','https://dashboard.example.org','Bearer '+token,8790)
    assert calls==[['fork-microscope','--port','8790','--host','127.0.0.1','--allow-origin','https://dashboard.example.org']]
    output=capsys.readouterr().out
    assert 'Worker URL: http://127.0.0.1:8790' in output and token in output
    assert 'No model is loaded' in output


def test_connect_preserves_existing_token_and_rejects_bad_origin(monkeypatch,capsys):
    import os,sys,fork_cli,microscope_server
    token='fixture-token-for-test-only-0000000000'
    monkeypatch.setenv('FORK_WORKER_TOKEN',token)
    monkeypatch.setattr(fork_cli,'check_upstream',lambda:None)
    monkeypatch.setattr(microscope_server,'main',lambda:None)
    monkeypatch.setattr(sys,'argv',['fork-microscope'])
    fork_cli.connect('https://dashboard.example.org')
    assert os.environ['FORK_WORKER_TOKEN']==token
    capsys.readouterr()
    with pytest.raises(ValueError):fork_cli.connect('https://dashboard.example.org/secret-path')
    assert capsys.readouterr().out==''
