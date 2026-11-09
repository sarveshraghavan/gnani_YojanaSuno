"""Score only rows explicitly marked as real recordings in field_tests.csv."""
from __future__ import annotations
import argparse,csv,json
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def load_rows(path):
    with path.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def main():
    parser=argparse.ArgumentParser();parser.add_argument("--input",default=str(ROOT/"field_tests.csv"));parser.add_argument("--output",default=str(ROOT/"eval/field_test_report.md"));args=parser.parse_args()
    rows=load_rows(Path(args.input));real=[r for r in rows if "real_recording=true" in (r.get("notes") or "").casefold()]
    by_lang=defaultdict(lambda:[0,0]);by_noise=defaultdict(lambda:[0,0]);invalid=[]
    for row in real:
        try:expected=json.loads(row["expected_slots"] or "{}");extracted=json.loads(row["extracted_slots"] or "{}")
        except (json.JSONDecodeError,TypeError):invalid.append(row.get("id","?"));continue
        if not isinstance(expected,dict) or not isinstance(extracted,dict):invalid.append(row.get("id","?"));continue
        for slot,value in expected.items():
            ok=extracted.get(slot)==value
            by_lang[row.get("language","?")][1]+=1;by_lang[row.get("language","?")][0]+=ok
            by_noise[row.get("noise","?")][1]+=1;by_noise[row.get("noise","?")][0]+=ok
    lines=["# Field-test report","","This report uses rows tagged `real_recording=true` only. It must not be generalized beyond the speakers, devices, and noise conditions actually recorded.",""]
    if not real:
        lines += ["No real recording rows are marked yet. No field-test accuracy is claimed."]
    else:
        lines += [f"Included {len(real)} real recording rows. Invalid slot JSON rows excluded: {len(invalid)}.","","## By language","","| Language | Correct slots / total | Exact-match slot rate |","|---|---:|---:|"]
        for lang,(correct,total) in sorted(by_lang.items()):lines.append(f"| {lang} | {correct}/{total} | {correct/total:.1%} |" if total else f"| {lang} | 0/0 | — |")
        lines += ["","## By noise condition","","| Noise | Correct slots / total | Exact-match slot rate |","|---|---:|---:|"]
        for noise,(correct,total) in sorted(by_noise.items()):lines.append(f"| {noise} | {correct}/{total} | {correct/total:.1%} |" if total else f"| {noise} | 0/0 | — |")
        if invalid:lines += ["", "Invalid rows: "+", ".join(invalid)]
    report="\n".join(lines)+"\n";output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(report,encoding="utf-8");print(report,end="")
if __name__=="__main__":raise SystemExit(main())
