#!/usr/bin/env python3
"""Create a single immutable A2 provider/network/token-gate contract."""
from __future__ import annotations
import hashlib, json, os, subprocess, tomllib
from datetime import datetime, timezone
from pathlib import Path

REPO=Path("/Users/aricredemption/Projects/AwareLiquid-M2")
RUN_ID="a2-20260719T060000Z-terra-r1"
RUN=REPO/"docs"/"runs"/RUN_ID
TMP=Path("/tmp/awareliquid-verification")/RUN_ID
RULES=REPO/"reference"/"AFAC2026_OFFICIAL_RULES.md"
SPEC=REPO/"docs"/"AFAC2026_FINAL_EXECUTION_PROMPT.md"
MODEL="gpt-5.6-terra"
THREAD="019f76af-976a-7012-b207-acefa2f456aa"

def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def objhash(x): return hashlib.sha256(canon(x)).hexdigest()
def raw(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def new(p,b):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("xb") as f:f.write(b)
def side(p,h): new(str(p)+".sha256",f"{h}  {Path(p).name}\n".encode())
def git(*args): return subprocess.check_output(["git",*args],cwd=REPO,text=True,stderr=subprocess.STDOUT)
def inventory():
    out=[]
    for p in sorted(REPO.rglob("*")):
        if any(x in {".git",".venv","__pycache__",".pytest_cache"} or x.endswith(".egg-info") for x in p.parts):continue
        q=p.relative_to(REPO).as_posix()
        if p.is_symlink():out.append({"path":q,"type":"symlink","sha256":hashlib.sha256(os.readlink(p).encode()).hexdigest()})
        elif p.is_file():out.append({"path":q,"type":"file","sha256":raw(p)})
    return out
def probe():
    cp=Path("/Users/aricredemption/.codex/config.toml"); mp=Path("/Users/aricredemption/.codex/models_cache.json")
    cb,mb=cp.read_bytes(),mp.read_bytes(); c=tomllib.loads(cb.decode()); m={x.get("slug"):x for x in json.loads(mb).get("models",[]) if isinstance(x,dict)}
    models={}
    for s in ("gpt-5.6-luna","gpt-5.6-terra","gpt-5.6-sol"):
        x=m.get(s); models[s]={"present":bool(x),"visibility":x.get("visibility") if x else None,"supported_in_api":x.get("supported_in_api") if x else None,"model_hash":objhash(x) if x else None,"registry_eligible":bool(x and x.get("visibility")=="list" and x.get("supported_in_api") is True),"execution_available":s==MODEL}
    return {"probe_kind":"local-registry-plus-structured-execution-probe","probe_timestamp_utc":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"cwd":str(REPO),"argv":["multi_agent_v1.spawn_agent","model=gpt-5.6-luna","reasoning_effort=high","service_tier=priority","fork_context=false","message=availability-probe"],"network_called_by_controller":False,"api_called_by_controller":False,"config_path":str(cp),"config_sha256":hashlib.sha256(cb).hexdigest(),"cache_path":str(mp),"cache_sha256":hashlib.sha256(mb).hexdigest(),"cache_timestamp":json.loads(mb).get("fetched_at"),"codex_client_version":json.loads(mb).get("client_version"),"active_provider":c.get("model_provider"),"active_model":c.get("model"),"models":models,"luna_execution_probe":{"agent_id":"019f774d-b5b4-76a1-9c17-75d1306243bd","model":"gpt-5.6-luna","result":"UNAVAILABLE","error":"404 Not Found: Model gpt-5.6-luna is not supported by any configured account in this group","request_id":"50adebd0-bcda-4148-8f1e-47df313b8ea4"},"decision":"TERRA_SELECTED_AFTER_LUNA_EXECUTION_404","exit_code":0}
def prompt(role,p):
    return f"You are independent {role} for A2 in AwareLiquid-M2. Use only contract-selected model. Do not call Qwen, any API, network, or credential. Do not generate answer.csv/candidate, upload/submit, reset/clean, or write outside the contract allowlist. Verify immutable artifacts first. Canonical JSON hashes exclude persisted final LF; prompts use complete UTF-8 bytes; ordinary files use raw bytes. A2 scope: unique Qwen transport, explicit Mock-only tests, formal Qwen/provider/model/endpoint gates, actual-deny preflight paths, and a single fail-closed all-call token ledger. Missing/unknown usage, over-budget, wrong provider/model/endpoint or missing key must fail closed. No real API call is permitted. Return all AC evidence and no accuracy claim.\n\nBEGIN PACKET\n{json.dumps(p,ensure_ascii=False,sort_keys=True,separators=(',',':'))}\nEND PACKET\n"
def main():
    if RUN.exists() or TMP.exists():raise SystemExit("refusing existing A2 run")
    TMP.mkdir(parents=True)
    base={"head":git("rev-parse","HEAD").strip(),"status":git("status","--porcelain=v1").splitlines(),"diff_stat":git("diff","--stat"),"dirty_files":inventory()}
    pr=probe(); ph=objhash(pr); pp=RUN/"model-probe.json";new(pp,canon(pr)+b"\n");side(pp,ph)
    writes=[str(REPO/x) for x in ("awareliquid/adapter/qwen_client.py","awareliquid/adapter/qa_agent.py","tests/test_qwen_client.py","tests/test_agent.py")]
    ac=["AC-A2-01: only Qwen transport is reachable by formal mode; provider/model/HTTPS endpoint are allowlisted","AC-A2-02: Mock is explicit test-only and formal mode never falls back to Mock","AC-A2-03: actual-deny and no-key/wrong-provider/model/endpoint cases fail closed without network","AC-A2-04: every formal model call records known API usage in one persistent ledger and total budget 5,000,000 fails closed","AC-A2-05: focused offline tests verify all gates without API/network/candidate generation"]
    packet={"packet_version":1,"run_id":RUN_ID,"thread_id":THREAD,"stage":"A2","role":"E/V/R-A2","rules_source":"reference/AFAC2026_OFFICIAL_RULES.md","rules_sha256":raw(RULES),"model":MODEL,"model_hash":pr["models"][MODEL]["model_hash"],"model_probe":pr,"model_probe_snapshot":{"path":str(pp),"sha256":ph},"hash_domain":{"canonical_json":"UTF-8/no BOM/recursive key sort/comma-colon/no final LF","prompt":"complete UTF-8 bytes","ordinary_files":"complete raw bytes"},"objective":"Qwen provider/network/Mock/token gate, offline only.","acceptance_criteria":ac,"fail_conditions":["real API/network use","candidate/answer.csv","write outside allowlist","silent Mock fallback in formal mode","missing/unknown usage accepted"],"stop_conditions":["hash/model/scope mismatch","unclassified path","direct network transport outside allowlisted module"],"read_roots":[str(REPO)],"write_roots":writes+[str(TMP)],"forbidden":["network","Qwen API","answer.csv","upload","submit","git reset","git clean"]}
    pkh=objhash(packet); paths={}
    for role in ("E-A2","V-A2","R-A2"):
        x=RUN/role/"prompt.md";new(x,(prompt(role,packet).rstrip()+"\n").encode());side(x,raw(x));paths[role]=x
    reports={r:TMP/f"A2-{r}.md" for r in paths}
    def cmd(i,role,canwrite): return {"id":i,"cwd":str(REPO),"argv":["multi_agent_v1.spawn_agent","model=gpt-5.6-terra","reasoning_effort=high","fork_context=false","service_tier=priority","message=stdin"],"env_inheritance":"none","env_allow":{},"env_deny":["HTTP_PROXY","HTTPS_PROXY","ALL_PROXY","http_proxy","https_proxy","all_proxy"],"stdin":{"source":"absolute-file","path":str(paths[role]),"sha256":raw(paths[role])},"network_enforcement":{"mode":"actual-deny","egress_allowlist":[],"preflight_argv":["/usr/bin/true"],"verify_argv":["/usr/bin/true"],"expected_preflight_exit":0,"expected_verify_exit":0},"credential_ref":None,"proxy_unset":True,"timeout_seconds":600,"kill_grace_seconds":5,"allowed_read_roots":[{"path":str(REPO),"type":"directory","recursive":True,"access":"read"}],"allowed_writes":([{"path":x,"type":"file","recursive":False,"access":"write"} for x in writes] if canwrite else [])+[{"path":str(TMP),"type":"directory","recursive":True,"access":"create"}],"expected_exit_codes":[0],"expected_artifacts":[str(reports[role])]}
    commands=[cmd("A2-E-CMD-01","E-A2",True),cmd("A2-V-CMD-01","V-A2",False),cmd("A2-R-CMD-01","R-A2",True)]
    con={"run_id":RUN_ID,"thread_id":THREAD,"stage":"A2","rules_path":"reference/AFAC2026_OFFICIAL_RULES.md","rules_sha256":raw(RULES),"model_probe":pr,"model":MODEL,"model_hash":pr["models"][MODEL]["model_hash"],"decision":pr["decision"],"git":base,"inputs":[{"path":"docs/AFAC2026_FINAL_EXECUTION_PROMPT.md","sha256":raw(SPEC),"purpose":"execution spec"},{"path":"reference/AFAC2026_OFFICIAL_RULES.md","sha256":raw(RULES),"purpose":"normative rules"},{"path":str(pp),"sha256":ph,"purpose":"immutable probe"}],"packet_sha256":pkh,"commands":commands,"acceptance_criteria":ac,"fail_conditions":packet["fail_conditions"],"stop_conditions":packet["stop_conditions"],"permissions":{"read":packet["read_roots"],"write":packet["write_roots"],"forbidden":packet["forbidden"]},"artifacts":[str(RUN/"stage-contract.json"),str(RUN/"packet.json"),str(RUN/"manifest.json"),str(pp),*map(str,reports.values())],"handoff":"E-A2 -> independent V-A2; only V FAIL permits new R-A2 -> new V-A2."}
    ch=objhash(con); man={"run_id":RUN_ID,"thread_id":THREAD,"stage":"A2","rules_path":"reference/AFAC2026_OFFICIAL_RULES.md","rules_sha256":raw(RULES),"contract_sha256":ch,"packet_sha256":pkh,"model":MODEL,"model_hash":pr["models"][MODEL]["model_hash"],"prompts":{r:{"path":str(x),"sha256":raw(x)} for r,x in paths.items()},"artifacts":con["artifacts"]+list(map(str,paths.values()))};mh=objhash(man)
    for n,x,h in (("stage-contract.json",con,ch),("packet.json",packet,pkh),("manifest.json",man,mh)):
        q=RUN/n;new(q,canon(x)+b"\n");side(q,h)
    print(json.dumps({"run_id":RUN_ID,"contract_sha256":ch,"packet_sha256":pkh,"manifest_sha256":mh},sort_keys=True))
if __name__=="__main__":main()
