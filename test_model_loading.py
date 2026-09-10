"""Deployment selection, asynchronous load reporting, and snapshot consistency."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('autoload', ROOT / 'docker/autoload.py')
autoload = importlib.util.module_from_spec(spec)
spec.loader.exec_module(autoload)


def test_default_pinned_muse_and_legacy_switch():
    config = autoload.load_config({})
    assert config == json.loads((ROOT / 'configs/muse-smoke.json').read_text())['load']
    assert autoload.enabled({})
    assert not autoload.enabled({'AUTO_LOAD_MUSE': '0'})
    assert autoload.enabled({'AUTO_LOAD_MODEL': '1', 'AUTO_LOAD_MUSE': '0'})
    with pytest.raises(ValueError, match='0 or 1'):
        autoload.enabled({'AUTO_LOAD_MODEL': 'yes'})


def test_profile_selection_and_explicit_runtime_overrides():
    config = autoload.load_config({'FORK_MODEL_PROFILE': 'configs/cpu-smoke.json'})
    assert config['model_id'] == 'HuggingFaceTB/SmolLM2-135M-Instruct'
    assert config['device'] == 'cpu'
    config = autoload.load_config({'FORK_MODEL_ID': '/workspace/my-model',
        'FORK_MODEL_REVISION': 'local', 'FORK_MODEL_DEVICE': 'cpu', 'FORK_MODEL_BATCH_SIZE': '2'})
    assert config == dict(model_id='/workspace/my-model', revision='local', device='cpu', batch_size=2)


def test_cannot_inherit_another_models_revision():
    with pytest.raises(ValueError, match='requires FORK_MODEL_REVISION'):
        autoload.load_config({'FORK_MODEL_ID': 'different/model'})


@pytest.mark.parametrize('overrides', [
    {'FORK_MODEL_DEVICE': 'cuda:9'}, {'FORK_MODEL_BATCH_SIZE': '0'},
    {'FORK_MODEL_BATCH_SIZE': '129'}, {'FORK_MODEL_BATCH_SIZE': '1.5'},
    {'FORK_MODEL_REVISION': '  '},
])
def test_invalid_deployment_settings_fail_before_http(overrides):
    with pytest.raises(ValueError):
        autoload.load_config(overrides)


def test_profile_supports_load_only_and_rejects_unexpected_fields(tmp_path):
    payload = autoload.load_config({})
    path = tmp_path / 'model.json'
    path.write_text(json.dumps(payload))
    assert autoload.load_config({'FORK_MODEL_PROFILE': str(path)}) == payload
    payload['token'] = 'not-accepted-in-model-profile'
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match='only'):
        autoload.load_config({'FORK_MODEL_PROFILE': str(path)})


def test_autoload_waits_for_actual_model_ready(monkeypatch, capsys):
    monkeypatch.setattr(autoload, 'load_config', lambda: {'model_id': 'test/model'})
    monkeypatch.setattr(autoload, 'enabled', lambda: True)
    monkeypatch.setattr('sys.argv', ['autoload'])
    monkeypatch.setattr(autoload.time, 'sleep', lambda seconds: None)
    responses = iter([{}, {'job_id': 'job'},
        {'job': {'id': 'job', 'status': 'running', 'phase': 'Weights'}},
        {'job': {'id': 'job', 'status': 'complete', 'phase': 'Load complete'}, 'model': {'model_id': 'test/model'}}])
    calls = []
    def request(path, payload=None):
        calls.append((path, payload))
        return next(responses)
    monkeypatch.setattr(autoload, 'request_json', request)
    autoload.main()
    assert [x[0] for x in calls] == ['/api/live/status', '/api/live/load', '/api/live/status', '/api/live/status']
    assert 'Model ready:' in capsys.readouterr().out


def test_autoload_reports_job_error_not_success(monkeypatch):
    monkeypatch.setattr(autoload, 'load_config', lambda: {})
    monkeypatch.setattr(autoload, 'enabled', lambda: True)
    monkeypatch.setattr('sys.argv', ['autoload'])
    responses = iter([{}, {'job_id': 'job'},
        {'job': {'id': 'job', 'status': 'error', 'phase': 'CUDA out of memory'}}])
    monkeypatch.setattr(autoload, 'request_json', lambda *a: next(responses))
    with pytest.raises(RuntimeError, match='CUDA out of memory'):
        autoload.main()


@pytest.mark.parametrize('is_muse', [False, True])
def test_adapter_pins_tokenizer_and_weights_to_resolved_config(monkeypatch, is_muse):
    import live_model as lm
    calls = []
    config = SimpleNamespace(model_type='muse_glimmer' if is_muse else 'other', _commit_hash='a' * 40,
        vocab_size=8, max_position_embeddings=256)
    tok = SimpleNamespace(eos_token_id=2, pad_token_id=0, chat_template='template',
        get_vocab=lambda: {'<|eot|>': 2, '<|eom|>': 3})
    model = SimpleNamespace(config=config, generation_config=SimpleNamespace(eos_token_id=2),
        parameters=lambda: [], eval=lambda: model)
    def factory(name, value):
        def load(model_id, **kwargs):
            calls.append((name, model_id, kwargs))
            return value
        return load
    monkeypatch.setattr(lm.AutoConfig, 'from_pretrained', factory('config', config))
    monkeypatch.setattr(lm.AutoTokenizer, 'from_pretrained', factory('tokenizer', tok))
    monkeypatch.setattr(lm.AutoProcessor, 'from_pretrained', factory('processor', SimpleNamespace(tokenizer=tok)))
    loader = lm.AutoModelForImageTextToText if is_muse else lm.AutoModelForCausalLM
    monkeypatch.setattr(loader, 'from_pretrained', factory('weights', model))
    phases = []
    attached = lm.AttachedModel('test/model', 'main', 'cpu', 1, progress=phases.append)
    assert calls[0][2]['revision'] == 'main'
    assert all(call[2]['revision'] == 'a' * 40 for call in calls[1:])
    assert calls[-1][2]['config'] is config
    assert calls[-1][2]['dtype'] == lm.torch.float32
    assert calls[-1][2]['trust_remote_code'] is False
    assert calls[-1][2]['use_safetensors'] is True
    assert calls[-1][2]['device_map'] == {'': 'cpu'}
    assert attached.info['requested_revision'] == 'main'
    assert attached.info['resolved_revision'] == 'a' * 40
    assert attached.info['loading']['total_seconds'] >= attached.info['loading']['weights_seconds'] >= 0
    assert len(phases) == 4


def test_disabled_autoload_never_requests_a_model(monkeypatch, capsys):
    monkeypatch.setattr('sys.argv', ['autoload'])
    monkeypatch.setattr(autoload, 'load_config', lambda: {})
    monkeypatch.setattr(autoload, 'enabled', lambda: False)
    monkeypatch.setattr(autoload, 'request_json', lambda *a: pytest.fail('Disabled autoload must not call dashboard.'))
    autoload.main()
    assert 'disabled' in capsys.readouterr().out
