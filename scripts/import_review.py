"""Apply reviewer edits, displaying a unified diff before any write."""
import csv, difflib, json, sys
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
def read_csv(path):
    with path.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def write_diff(path, old, new):
    diff="".join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=str(path),tofile=str(path)+" (reviewed)"))
    if diff: print(diff)
    return bool(diff)
def main():
    # Windows PowerShell may use cp1252; reviewer diffs include native scripts.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    changes=[]; evalpath=ROOT/"eval/extraction_cases.jsonl"; original=evalpath.read_text(encoding="utf-8")
    cases=[json.loads(x) for x in original.splitlines() if x.strip()]
    rows=read_csv(ROOT/"eval/review/extraction_cases.csv")
    for row in rows:
        i=int(row["id"].split(":")[1])-1
        correction=(row.get("correction") or "").strip()
        if correction:
            try: updated=json.loads(correction)
            except json.JSONDecodeError: updated={"utterance":correction}
            if not isinstance(updated,dict): raise ValueError(f"Expected JSON object or corrected utterance for {row['id']}")
            if "expected_slots" in updated:
                if not isinstance(updated["expected_slots"],dict): raise ValueError(f"expected_slots must be a JSON object for {row['id']}")
                cases[i]["expected_slots"]=updated["expected_slots"]
            elif not "utterance" in updated:
                cases[i]["expected_slots"]=updated
            if "utterance" in updated: cases[i]["utterance"]=updated["utterance"]
        if (row.get("reviewer_ok") or "").strip().casefold() in {"yes","true","1","ok"}:
            from datetime import date
            reviewer=(row.get("notes") or "").strip().removeprefix("reviewed_by=").strip()
            cases[i]["reviewed_by"]=reviewer or "reviewer (name not supplied)"
            cases[i]["review_date"]=date.today().isoformat()
    new="".join(json.dumps(c,ensure_ascii=False)+"\n" for c in cases)
    if new!=original: changes.append((evalpath,original,new))
    languagepath=ROOT/"backend/tests/language_cases.yaml"
    languageold=languagepath.read_text(encoding="utf-8")
    language_data=yaml.safe_load(languageold)
    language_rows=read_csv(ROOT/"eval/review/language_cases.csv")
    language_by_id={f"language:{lang}:{case['id']}":case for lang,caseset in language_data["languages"].items() for case in caseset}
    from datetime import date
    for row in language_rows:
        case=language_by_id.get(row["id"])
        if not case: continue
        correction=(row.get("correction") or "").strip()
        if correction:
            try: corrected=json.loads(correction)
            except json.JSONDecodeError: corrected={"input_text":correction}
            if not isinstance(corrected,dict): raise ValueError(f"Expected JSON object or corrected utterance for {row['id']}")
            for key in ("input_text","expected_slots","forbidden_slots","pending_question","expected_dialogue_action"):
                if key in corrected: case[key]=corrected[key]
        if (row.get("reviewer_ok") or "").strip().casefold() in {"yes","true","1","ok"}:
            reviewer=(row.get("notes") or "").strip()
            case["reviewed_by"]=reviewer.removeprefix("reviewed_by=").strip() or "reviewer (name not supplied)"
            case["review_date"]=date.today().isoformat()
    languagenew=yaml.safe_dump(language_data,allow_unicode=True,sort_keys=False,width=120)
    if languagenew!=languageold: changes.append((languagepath,languageold,languagenew))
    stringpath=ROOT/"frontend/review/user_facing_strings.csv"; srows=read_csv(stringpath)
    catalogpath=ROOT/"backend/app/dialogue/review_strings.json"
    catalogold=catalogpath.read_text(encoding="utf-8") if catalogpath.exists() else "{}\n"
    catalog=json.loads(catalogold)
    for row in srows:
        correction=(row.get("correction") or "").strip()
        if not correction: continue
        parts=row["id"].split(":")
        if parts[0]=="question":catalog.setdefault("questions",{}).setdefault(parts[1],{})[parts[2]]=correction
        elif parts[0] in {"disclosures","fallbacks","privacy_warning","retry","scope"}:
            catalog.setdefault(parts[0],{})[parts[1]]=correction
    catalognew=json.dumps(catalog,ensure_ascii=False,indent=2)+"\n"
    if catalognew!=catalogold:changes.append((catalogpath,catalogold,catalognew))
    htmlpath=ROOT/"frontend/index.html"; htmlold=htmlpath.read_text(encoding="utf-8"); htmlnew=htmlold
    landing_changes=0
    for row in srows:
        correction=(row.get("correction") or "").strip()
        if not correction: continue
        ident=row["id"]
        if ident.startswith("landing:"):
            source=row["text"]
            if source in htmlnew: htmlnew=htmlnew.replace(source,correction,1);landing_changes+=1
            else: raise ValueError(f"Could not locate original landing string for {ident}")
    if htmlnew!=htmlold: changes.append((htmlpath,htmlold,htmlnew))
    for path,old,newtext in changes: write_diff(path,old,newtext)
    if not changes: print("No corrections to apply.");return
    print(f"Applying {len(changes)} file update(s); fixture review metadata updated for corrected cases; landing strings replaced: {landing_changes}.")
    for path,_,newtext in changes:path.write_text(newtext,encoding="utf-8")
if __name__=="__main__":main()
