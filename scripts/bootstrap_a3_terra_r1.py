#!/usr/bin/env python3
"""Create an immutable A3 offline Evidence-provenance run."""
from __future__ import annotations
import hashlib,json,os,subprocess,tomllib
from datetime import datetime,timezone
from pathlib import Path

REPO=Path("/Users/aricredemption/Projects/AwareLiquid-M2")
RUN_ID="a3-20260719T210000Z-terra-r1"; THREAD="019f76af-976a-7012-b207-acefa2f456aa"
RUN=REPO/"docs"/"runs"/RUN_ID; TMP=Path("/tmp/awareliquid-verification")/RUN_ID
RULES=REPO/"reference"/"AFAC2026_OFFICIAL_RULES.md"; SPEC=REPO/"docs"/"AFAC2026_FINAL_EXECUTION_PROMPT.md"; MODEL="gpt-5.6-terra"
def canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def oh(x):return hashlib.sha256(canon(x)).hexdigest()
def raw(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def new(p,b):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open("xb") as f:f.write(b)
def side(p,h):new(str(p)+".sha256",f"{h}  {Path(p).name}\n".encode())
def git(*a):return subprocess.check_output(["git",*a],cwd=REPO,text=True,stderr=subprocess.STDOUT)
def inventory():
 out=[]
 for p in sorted(REPO.rglob("*")):
  if any(x in {".git",".venv",".pytest_cache"} or x.endswith(".egg-info") for x in p.parts):continue
  q=p.relative_to(REPO).as_posix()
  if p.is_symlink():out.append({"path":q,"type":"symlink","sha256":hashlib.sha256(os.readlink(p).encode()).hexdigest()})
  elif p.is_file():out.append({"path":q,"type":"file","sha256":raw(p)})
 return out
def probe():
 cp=Path("/Users/aricredemption/.codex/config.toml");mp=Path("/Users/aricredemption/.codex/models_cache.json");cb,mb=cp.read_bytes(),mp.read_bytes();cfg=tomllib.loads(cb.decode());cache=json.loads(mb);by={x.get("slug"):x for x in cache.get("models",[]) if isinstance(x,dict)}
 ms={}
 for slug in ("gpt-5.6-luna","gpt-5.6-terra","gpt-5.6-sol"):
  x=by.get(slug);ms[slug]={"present":bool(x),"visibility":x.get("visibility") if x else None,"supported_in_api":x.get("supported_in_api") if x else None,"model_hash":oh(x) if x else None,"registry_eligible":bool(x and x.get("visibility")=="list" and x.get("supported_in_api") is True),"execution_available":slug==MODEL}
 return {"probe_kind":"local-registry-plus-structured-execution-probe","probe_timestamp_utc":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"cwd":str(REPO),"argv":["multi_agent_v1.spawn_agent","model=gpt-5.6-luna","reasoning_effort=high","service_tier=priority","fork_context=false","message=availability-probe"],"network_called_by_controller":False,"api_called_by_controller":False,"config_path":str(cp),"config_sha256":hashlib.sha256(cb).hexdigest(),"cache_path":str(mp),"cache_sha256":hashlib.sha256(mb).hexdigest(),"cache_timestamp":cache.get("fetched_at"),"codex_client_version":cache.get("client_version"),"active_provider":cfg.get("model_provider"),"active_model":cfg.get("model"),"models":ms,"luna_execution_probe":{"agent_id":"019f77f2-8bca-70d1-9e94-a99218156641","model":"gpt-5.6-luna","result":"UNAVAILABLE","error":"404 Not Found: Model gpt-5.6-luna is not supported by any configured account in this group","request_id":"59aafcaa-795c-4d08-9d4a-88586fcd84de"},"decision":"TERRA_SELECTED_AFTER_LUNA_EXECUTION_404","exit_code":0}
def roleprompt(role,p):
 return f"You are independent {role} for A3 in AwareLiquid-M2. Use only contract-selected model. Do not call Qwen, API, network, or credentials; do not generate candidates/answer.csv or claims of accuracy. Verify immutable artifacts first. Canonical JSON hashes exclude persisted final LF; prompts use full UTF-8 bytes; ordinary files use raw bytes. A3 scope: create only offline deterministic Evidence provenance/normalization for parsed text, not semantic summaries/FAQ/conclusions. Required Evidence fields: domain, doc_id, page, source_path, char_start, char_end, section, title, table_id, row_id, column_ids, unit, footnote, parent_evidence_id, neighbor_evidence_ids, parse_warning. evidence_id must be deterministic from parser version/source/position/content hash. Preserve warnings and boundary information. Add synthetic fixture tests for stable IDs, offsets, tables/units/footnotes/warnings; never use real A material for semantic derivation. Return AC evidence/no accuracy claim.\n\nBEGIN PACKET\n{json.dumps(p,ensure_ascii=False,sort_keys=True,separators=(',',':'))}\nEND PACKET\n"
def main():
 if RUN.exists() or TMP.exists():raise SystemExit("existing A3 run")
 TMP.mkdir(parents=True);base={"head":git("rev-parse","HEAD").strip(),"status":git("status","--porcelain=v1").splitlines(),"diff_stat":git("diff","--stat"),"dirty_files":inventory()}
 pr=probe();php=oh(pr);pp=RUN/"model-probe.json";new(pp,canon(pr)+b"\n");side(pp,php)
 writes=[str(REPO/x) for x in ("awareliquid/evidence.py","tests/test_evidence.py","tests/fixtures/evidence_synthetic.json")]
 ac=["AC-A3-01: deterministic offline evidence records contain all required provenance and boundary fields","AC-A3-02: evidence IDs are stable from parser/version/source/position/content without semantic generation","AC-A3-03: parse warnings, pages, offsets, headers/table row/unit/footnote/parent-neighbor boundaries are preserved","AC-A3-04: synthetic fixture verifies provenance only; no Qwen/API/network/embedding/rerank/semantic-summary use","AC-A3-05: focused offline tests and baseline evidence pass without candidate or accuracy output"]
 packet={"packet_version":1,"run_id":RUN_ID,"thread_id":THREAD,"stage":"A3","role":"E/V/R-A3","rules_source":"reference/AFAC2026_OFFICIAL_RULES.md","rules_sha256":raw(RULES),"model":MODEL,"model_hash":pr["models"][MODEL]["model_hash"],"model_probe":pr,"model_probe_snapshot":{"path":str(pp),"sha256":php},"hash_domain":{"canonical_json":"UTF-8/no BOM/recursive key sort/comma-colon/no final LF","prompt":"complete UTF-8 bytes","ordinary_files":"complete raw bytes"},"objective":"Offline Evidence provenance and deterministic parsing boundaries only.","acceptance_criteria":ac,"fail_conditions":["Qwen/API/network/credential use","semantic summary/FAQ/conclusion generation","candidate/answer.csv","write outside allowlist","missing provenance or unstable ID"],"stop_conditions":["hash/model/scope mismatch","unclassified path","embedding/rerank/dense dependency"],"read_roots":[str(REPO)],"write_roots":writes+[str(TMP)],"forbidden":["network","Qwen API","embedding","rerank","answer.csv","upload","submit","git reset","git clean"]}
 pkh=oh(packet);prompts={}
 for role in ("E-A3","V-A3","R-A3"):
  x=RUN/role/"prompt.md";new(x,(roleprompt(role,packet).rstrip()+"\n").encode());side(x,raw(x));prompts[role]=x
 reports={r:TMP/f"A3-{r}.md" for r in prompts}
 def cmd(i,role,write):return {"id":i,"cwd":str(REPO),"argv":["multi_agent_v1.spawn_agent","model=gpt-5.6-terra","reasoning_effort=high","fork_context=false","service_tier=priority","message=stdin"],"env_inheritance":"none","env_allow":{},"env_deny":["HTTP_PROXY","HTTPS_PROXY","ALL_PROXY","http_proxy","https_proxy","all_proxy"],"stdin":{"source":"absolute-file","path":str(prompts[role]),"sha256":raw(prompts[role])},"network_enforcement":{"mode":"actual-deny","egress_allowlist":[],"preflight_argv":[".venv/bin/python","-B","-c","import awareliquid.evidence"],"verify_argv":[".venv/bin/python","-B","-c","import awareliquid.evidence"],"expected_preflight_exit":0,"expected_verify_exit":0},"credential_ref":None,"proxy_unset":True,"timeout_seconds":600,"kill_grace_seconds":5,"allowed_read_roots":[{"path":str(REPO),"type":"directory","recursive":True,"access":"read"}],"allowed_writes":([{"path":x,"type":"file","recursive":False,"access":"write"} for x in writes] if write else [])+[{"path":str(TMP),"type":"directory","recursive":True,"access":"create"}],"expected_exit_codes":[0],"expected_artifacts":[str(reports[role])]}
 commands=[cmd("A3-E-CMD-01","E-A3",True),cmd("A3-V-CMD-01","V-A3",False),cmd("A3-R-CMD-01","R-A3",True)]
 con={"run_id":RUN_ID,"thread_id":THREAD,"stage":"A3","rules_path":"reference/AFAC2026_OFFICIAL_RULES.md","rules_sha256":raw(RULES),"model_probe":pr,"model":MODEL,"model_hash":pr["models"][MODEL]["model_hash"],"decision":pr["decision"],"git":base,"inputs":[{"path":"docs/AFAC2026_FINAL_EXECUTION_PROMPT.md","sha256":raw(SPEC),"purpose":"execution spec"},{"path":"reference/AFAC2026_OFFICIAL_RULES.md","sha256":raw(RULES),"purpose":"rules"},{"path":str(pp),"sha256":php,"purpose":"probe"}],"packet_sha256":pkh,"commands":commands,"acceptance_criteria":ac,"fail_conditions":packet["fail_conditions"],"stop_conditions":packet["stop_conditions"],"permissions":{"read":packet["read_roots"],"write":packet["write_roots"],"forbidden":packet["forbidden"]},"artifacts":[str(RUN/"stage-contract.json"),str(RUN/"packet.json"),str(RUN/"manifest.json"),str(pp),*map(str,reports.values())],"handoff":"E-A3 -> independent V-A3; only V FAIL permits new R-A3 -> new V-A3."}
 ch=oh(con);man={"run_id":RUN_ID,"thread_id":THREAD,"stage":"A3","rules_path":"reference/AFAC2026_OFFICIAL_RULES.md","rules_sha256":raw(RULES),"contract_sha256":ch,"packet_sha256":pkh,"model":MODEL,"model_hash":pr["models"][MODEL]["model_hash"],"prompts":{r:{"path":str(x),"sha256":raw(x)} for r,x in prompts.items()},"artifacts":con["artifacts"]+list(map(str,prompts.values()))};mh=oh(man)
 for n,x,h in (("stage-contract.json",con,ch),("packet.json",packet,pkh),("manifest.json",man,mh)):
  q=RUN/n;new(q,canon(x)+b"\n");side(q,h)
 print(json.dumps({"run_id":RUN_ID,"contract_sha256":ch,"packet_sha256":pkh,"manifest_sha256":mh},sort_keys=True))
if __name__=="__main__":main()
