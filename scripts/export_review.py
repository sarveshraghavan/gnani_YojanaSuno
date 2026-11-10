"""Export extraction fixtures and current UI/localized strings for human review."""
import csv, json, sys
from html.parser import HTMLParser
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.app.dialogue.next_question import QUESTIONS
from backend.app.dialogue.disclosure import AI_DISCLOSURES
from backend.app.main import voice_fallback
from backend.tests.test_i18n_complete import landing_tables

class Texts(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]
    def handle_data(self,data):
        if data.strip(): self.parts.append(data)
def write(path, rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    prior={}
    if path.exists():
        with path.open(encoding="utf-8-sig",newline="") as f:
            prior={row.get("id"):row for row in csv.DictReader(f)}
    for row in rows:
        old=prior.get(row["id"],{})
        for key in ("reviewer_ok","correction","notes"):
            if old.get(key): row[key]=old[key]
    with path.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=["id","language","text","expected_slots","reviewer_ok","correction","notes"]);w.writeheader();w.writerows(rows)

def landing_translations():
    """Resolve the active page translation table, including inline runtime copy."""
    return landing_tables()
def main():
    catalog_path=ROOT/"backend/app/dialogue/review_strings.json"
    existing=json.loads(catalog_path.read_text(encoding="utf-8")) if catalog_path.exists() else {}
    catalog={**existing,"questions":QUESTIONS,"disclosures":AI_DISCLOSURES,"fallbacks":{lang:voice_fallback(lang+"-IN") for lang in ("hi","ta","te","en")}}
    (ROOT/"backend/app/dialogue/review_strings.json").write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    eval_path=ROOT/"eval/extraction_cases.jsonl"; cases=[json.loads(x) for x in eval_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    eval_rows=[{"id":f"case:{i}","language":c["lang"],"text":c["utterance"],"expected_slots":json.dumps(c["expected_slots"],ensure_ascii=False),"reviewer_ok":"true" if c.get("reviewed_by") else "","correction":"","notes":f"reviewed_by={c['reviewed_by']}" if c.get("reviewed_by") else ""} for i,c in enumerate(cases,1)]
    write(ROOT/"eval/review/extraction_cases.csv",eval_rows)
    language_data=yaml.safe_load((ROOT/"backend/tests/language_cases.yaml").read_text(encoding="utf-8"))["languages"]
    language_rows=[]
    for lang,items in language_data.items():
        for c in items:
            language_rows.append({"id":f"language:{lang}:{c['id']}","language":lang,"text":c["input_text"],
                "expected_slots":json.dumps(c.get("expected_slots",{}),ensure_ascii=False),
                "reviewer_ok":"true" if c.get("reviewed_by") else "","correction":"",
                "notes":f"reviewed_by={c['reviewed_by']}" if c.get("reviewed_by") else ""})
    write(ROOT/"eval/review/language_cases.csv",language_rows)
    rows=[]
    for slot,langs in QUESTIONS.items():
        for lang,text in langs.items():
            needs_native_review = lang in {"hi", "ta", "te"} and slot in {
                "has_grid_connected_pump", "state_application_open", "state_requirements_confirmed",
                "farmer_age", "cultivable_land_hectares", "kcc_farmer_category", "micro_irrigation_interest"
            }
            rows.append({"id":f"question:{slot}:{lang}","language":lang,"text":text,
                "expected_slots":"","reviewer_ok":"","correction":"",
                "notes":"Needs native-speaker review" if needs_native_review else ""})
    for group in ("disclosures","fallbacks","privacy_warning","retry","scope","pm_kisan_next_steps"):
        for lang,text in catalog.get(group,{}).items():
            rows.append({"id":f"{group}:{lang}","language":lang,"text":text,"expected_slots":"","reviewer_ok":"","correction":"",
                         "notes":"Needs native-speaker review" if group == "pm_kisan_next_steps" and lang in {"hi","ta","te"} else ""})
    html=(ROOT/"frontend/index.html").read_text(encoding="utf-8")
    tables=landing_translations()
    keys=set()
    for attr in ("data-i","data-ip","data-ia","data-im","data-ititle","data-prompt-key"):
        import re
        keys.update(re.findall(rf'{attr}="([^"]+)"',html))
    for key in sorted(keys):
        for lang in ("hi","ta","te","en"):
            text=tables[lang].get(key)
            if text is None: raise ValueError(f"Missing {lang} landing string: {key}")
            rows.append({"id":f"landing:{key}:{lang}","language":lang,"text":text,"expected_slots":"","reviewer_ok":"","correction":"",
                         "notes":"Needs native-speaker review" if lang in {"hi","ta","te"} else ""})
    write(ROOT/"frontend/review/user_facing_strings.csv",rows)
    print(f"Exported {len(eval_rows)} extraction cases, {len(language_rows)} language cases, and {len(rows)} dialogue/landing-page strings.")
    print("Review the CSVs, mark reviewer_ok, and fill correction or notes. Import prints the proposed diff before writing.")
if __name__=="__main__": main()
