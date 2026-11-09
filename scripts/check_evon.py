"""Small, non-scoring connectivity check for a running optional Evon endpoint."""
from __future__ import annotations
import sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from backend.app.config import settings  # noqa: E402
from backend.app.dialogue.extractor import EvonExtractor, validate_slots  # noqa: E402

CASES=[("hi","मेरे नाम पर दो एकड़ जमीन है"),("ta","என் பெயரில் நிலம் உள்ளது"),("te","నా పేరుపై భూమి ఉంది"),("en","I own land in Tamil Nadu and grow rice")]
def main():
    if not settings.evon_base_url:
        print("Evon unavailable: configure EVON_BASE_URL through backend settings."); return 2
    model=EvonExtractor(settings.evon_base_url,settings.evon_model,settings.evon_api_key)
    print("| Language | Slots | Latency ms | JSON validated |\n|---|---|---:|---|")
    failures=0
    unavailable=False
    for lang,text in CASES:
        if unavailable:
            print(f"| {lang} | — | — | endpoint unavailable (not retried) |")
            failures+=1; continue
        start=time.perf_counter(); slots=model.extract(text,lang,{}); latency=(time.perf_counter()-start)*1000
        valid=bool(validate_slots(slots)); failures += not valid or model.last_error is not None
        state=f"unavailable ({model.last_error})" if model.last_error else ('yes' if valid else 'no')
        print(f"| {lang} | `{slots}` | {latency:.0f} | {state} |")
        unavailable=model.last_error is not None
    return int(failures>0)
if __name__=="__main__": raise SystemExit(main())
