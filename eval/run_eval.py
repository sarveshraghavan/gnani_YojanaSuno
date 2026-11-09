"""Fixture evaluation. Scores describe fixtures only, never field accuracy."""
from __future__ import annotations
import argparse, json, sys
from collections import defaultdict
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.app.config import settings  # noqa: E402
from backend.app.dialogue.extractor import EvonExtractor, validate_slots  # noqa: E402
from backend.app.eligibility import check_all, load_schemes  # noqa: E402
from backend.app.main import local_extract, short_answer, redact_sensitive_numbers, extract_slots, resolve_fix_slot  # noqa: E402
EVAL_DIR=Path(__file__).resolve().parent

def read_jsonl(path): return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
def mock_extract(case):
    got=local_extract(case["utterance"],case.get("pending_slot"))
    got.update(short_answer(case["utterance"],case.get("pending_slot")))
    return validate_slots(got)
def evon_extract(case, extractor):
    return validate_slots(extractor.extract(case["utterance"],case["lang"],{},case.get("pending_slot")))
def score(cases,predict):
    per=defaultdict(lambda:[0,0]); predictions=[]
    for case in cases:
        try: got=predict(case)
        except Exception: got={}
        predictions.append(got)
        for slot,target in case["expected_slots"].items():
            per[case["lang"]][1]+=1;per[case["lang"]][0]+=(got.get(slot)==target)
    return per,predictions

def score_language_scenarios():
    """Score offline behavioral fixtures; never label these as field accuracy."""
    source=ROOT/"backend/tests/language_cases.yaml"
    data=yaml.safe_load(source.read_text(encoding="utf-8"))["languages"]
    out={}
    locale={"hi":"hi-IN","ta":"ta-IN","te":"te-IN","en":"en-IN"}
    for lang,items in data.items():
        correct=reviewed=synthetic=0
        for case in items:
            text=case["input_text"]; pending=case.get("pending_question"); known=case.get("initial_slots",{})
            got,_,reask=extract_slots(text,locale[lang],known,pending)
            got.update(short_answer(text,pending))
            okay=True
            for slot,value in case.get("expected_slots",{}).items():
                if got.get(slot)!=value: okay=False
            for slot,value in case.get("forbidden_slots",{}).items():
                if value=="any" and slot in got: okay=False
                elif value=="changes" and got.get(slot,known.get(slot))!=known.get(slot): okay=False
                elif value!="any" and value!="changes" and got.get(slot)==value: okay=False
            action=case["expected_dialogue_action"]
            # The complete dialogue action (including retries, confirmation and
            # correction turns) is exercised in pytest's API scenarios. This
            # report scores fixture extraction/safety assertions only; it does
            # not approximate those API state transitions here.
            if action=="fallback" and not (case.get("mock_stt_confidence",1.0)<0.45 or not text.strip()): okay=False
            if case["scenario"]=="sensitive_numbers" and "1234 5678 9012" in redact_sensitive_numbers(text): okay=False
            correct+=int(okay)
            if case.get("reviewed_by") and case.get("review_date"): reviewed+=1
            else: synthetic+=1
        out[lang]=(correct,len(items),reviewed,synthetic)
    return out
def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8",errors="replace")
    parser=argparse.ArgumentParser();parser.add_argument("--extractor",choices=["mock","evon","both"],default="mock");args=parser.parse_args()
    cases=read_jsonl(EVAL_DIR/"extraction_cases.jsonl")
    review=defaultdict(lambda:[0,0])
    for c in cases: review[c["lang"]][0 if c.get("reviewed_by") and c.get("review_date") else 1]+=1
    mock_scores,mock_preds=score(cases,mock_extract)
    evon_scores=None;evon_preds=[];evon_status="not run"
    if args.extractor in {"evon","both"}:
        if not settings.evon_base_url:
            evon_status="unreachable/not configured; used mock fallback"
            evon_scores,evon_preds=mock_scores,mock_preds
        else:
            ex=EvonExtractor(settings.evon_base_url,settings.evon_model,settings.evon_api_key)
            probe=evon_extract(cases[0],ex) if cases else {}
            if ex.last_error:
                evon_status="unreachable; used mock fallback"
                evon_scores,evon_preds=mock_scores,mock_preds
            else:
                evon_preds=[probe]
                for case in cases[1:]:
                    evon_preds.append(evon_extract(case,ex))
                    if ex.last_error: break
                if ex.last_error:
                    evon_status="unreachable; used mock fallback"
                    evon_scores,evon_preds=mock_scores,mock_preds
                else:
                    evon_scores=defaultdict(lambda:[0,0])
                    for case,got in zip(cases,evon_preds):
                        for slot,target in case["expected_slots"].items():
                            evon_scores[case["lang"]][1]+=1
                            evon_scores[case["lang"]][0]+=(got.get(slot)==target)
                    evon_status="connected"
    schemes={s.id:s for s in load_schemes()};correct=total=0
    for case in read_jsonl(EVAL_DIR/"eligibility_cases.jsonl"):
        correct+=check_all(case["slots"],[schemes[case["scheme_id"]]])[0].status==case["expected_status"];total+=1
    lines=["# YojanaSuno evaluation report","","These scores are exact-match results on a small fixture set. They are **not field accuracy**; most fixtures are synthetic and have not been reviewed by a native speaker.","",f"Selected extractor: `{args.extractor}`. Evon: {evon_status}.","","| Language | Human-reviewed cases | Synthetic/unreviewed cases | Mock slot accuracy | Evon slot accuracy |","|---|---:|---:|---:|---:|"]
    for lang in ("hi","ta","te","en"):
        mc,mt=mock_scores[lang]; ec,et=(evon_scores or mock_scores)[lang]
        lines.append(f"| {lang} | {review[lang][0]} | {review[lang][1]} | {mc}/{mt} ({mc/mt:.1%}) | {ec}/{et} ({ec/et:.1%}) |")
    language_scores=score_language_scenarios()
    lines += ["",f"Eligibility engine: {correct}/{total} ({correct/total:.1%}) on deterministic fixture cases.","","## Language-scenario fixture checks","","Offline behavioral pass rates on curated YAML scenarios. These are fixture checks, not field accuracy.","","| Language | Passed / total | Fixture pass rate | Human-reviewed | Synthetic / unreviewed |","|---|---:|---:|---:|---:|"]
    for lang in ("hi","ta","te","en"):
        passed,count,reviewed,synthetic=language_scores[lang]
        lines.append(f"| {lang} | {passed}/{count} | {passed/count:.1%} | {reviewed} | {synthetic} |" if count else f"| {lang} | 0/0 | — | {reviewed} | {synthetic} |")
    if args.extractor=="both":
        disagreements=[]
        for c,m,e in zip(cases,mock_preds,evon_preds):
            keys=set(c["expected_slots"]);diff=[k for k in keys if m.get(k)!=e.get(k)]
            if diff: disagreements.append((c,diff,m,e))
        lines += ["","## Side-by-side disagreements","", "| Case | Language | Fields | Mock values | Evon values |","|---|---|---|---|---|"]
        if disagreements:
            for i,(c,d,m,e) in enumerate(disagreements,1): lines.append(f"| {i} | {c['lang']} | {', '.join(d)} | `{ {k:m.get(k) for k in d} }` | `{ {k:e.get(k) for k in d} }` |")
        else: lines.append("| — | — | No disagreements in compared fields | — | — |")
    report="\n".join(lines)+"\n";(EVAL_DIR/"report.md").write_text(report,encoding="utf-8");print(report,end="")
    return 0
if __name__=="__main__": raise SystemExit(main())
