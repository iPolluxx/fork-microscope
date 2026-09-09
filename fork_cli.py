"""VM entry point: verify, serve, or run a versioned experiment config."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
os.environ.setdefault("OTRECON_FORCE_RUPTURES","1")
ROOT=Path(__file__).resolve().parent
UPSTREAM=ROOT/"vendor/forking-fast"
COMMIT="d32fed8d4162a4888291c4b3a38b059727c85a41"


def check_upstream():
    actual=subprocess.check_output(["git","-C",str(UPSTREAM),"rev-parse","HEAD"],text=True).strip()
    if actual!=COMMIT: raise RuntimeError("Upstream revision differs from the tested pin. Run git submodule update --init.")


def doctor(muse=False):
    import torch,transformers
    check_upstream()
    report=dict(python=sys.version.split()[0],torch=torch.__version__,transformers=transformers.__version__,
        cuda_available=torch.cuda.is_available(),gpu=torch.cuda.get_device_name() if torch.cuda.is_available() else None,
        upstream=COMMIT)
    if muse:
        from transformers import AutoConfig,AutoProcessor,AutoModelForImageTextToText
        from accelerate import init_empty_weights
        profile=json.loads((ROOT/"configs/muse-smoke.json").read_text())["load"]
        kw=dict(revision=profile["revision"],trust_remote_code=False)
        cfg=AutoConfig.from_pretrained(profile["model_id"],**kw)
        processor=AutoProcessor.from_pretrained(profile["model_id"],**kw)
        tok=processor.tokenizer
        ids=tok.apply_chat_template([{"role":"user","content":"What is 7 multiplied by 8?"}],tokenize=True,add_generation_prompt=True,return_dict=False)
        assert len(ids)>2 and all(isinstance(x,int) for x in ids)
        with init_empty_weights():
            model=AutoModelForImageTextToText.from_config(cfg)
        assert type(model).__name__=="MuseGlimmerForConditionalGeneration"
        assert "<|eot|>" in tok.get_vocab() and "<|eom|>" in tok.get_vocab()
        report["muse"]=dict(architecture=type(model).__name__,resolved_revision=cfg._commit_hash,
            context_limit=cfg.text_config.max_position_embeddings,vocab_size=cfg.text_config.vocab_size,
            prompt_tokens=len(ids),letter_token_lengths=[len(tok(x,add_special_tokens=False)["input_ids"]) for x in "ABCD"],
            validation="Config, processor, template and empty-weight model constructed; no model weights or GPU execution.")
    print(json.dumps(report,indent=2))


def wait(service):
    previous=None
    while True:
        job=service.status()["job"]
        if job["phase"]!=previous:
            print(job["phase"],flush=True);previous=job["phase"]
        if job["status"]!="running":
            if job["status"]!="complete":raise RuntimeError(job["phase"])
            return job
        time.sleep(.5)


def run(path,prepare_only=False):
    from live_service import LiveService
    check_upstream()
    config=json.loads(Path(path).read_text())
    if set(config)!={"load","base","run"}:raise ValueError("Config requires exactly load, base and run objects.")
    service=LiveService()
    try:
        service.start("load",config["load"]);wait(service)
        service.start("base",config["base"]);wait(service)
        estimate=service.estimate(config["run"])
        print(json.dumps({"sampling_budget":estimate},indent=2),flush=True)
        if prepare_only:return
        service.start("run",config["run"]);job=wait(service)
        print("SAVED",ROOT/"live-runs"/job["result_id"]/"result.json",flush=True)
    except KeyboardInterrupt:
        service.cancel()
        print("Stopping at the next sampling boundary…",flush=True)
        while service.status()["job"]["status"]=="running":time.sleep(.5)
        raise SystemExit(130)


def verify():
    check_upstream()
    spec=importlib.util.spec_from_file_location("upstream_verify",UPSTREAM/"scripts/verify_release.py")
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.check_data()
    subprocess.run([sys.executable,"-m","pytest",str(UPSTREAM/"otrecon/tests"),str(UPSTREAM/"forking_paths/tests"),"-q"],check=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="command",required=True)
    p=sub.add_parser("doctor");p.add_argument("--muse",action="store_true")
    p=sub.add_parser("serve");p.add_argument("--port",type=int,default=8766)
    p=sub.add_parser("run");p.add_argument("config");p.add_argument("--prepare-only",action="store_true")
    sub.add_parser("verify-upstream")
    args=parser.parse_args()
    if args.command=="doctor":doctor(args.muse)
    elif args.command=="verify-upstream":verify()
    elif args.command=="run":run(args.config,args.prepare_only)
    else:
        check_upstream()
        import microscope_server
        sys.argv=[sys.argv[0],"--port",str(args.port)]
        microscope_server.main()


if __name__=="__main__":main()
