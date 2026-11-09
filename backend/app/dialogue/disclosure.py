"""Required first-turn disclosure in supported languages."""
import json
from pathlib import Path

AI_DISCLOSURES = {
    "en": "I’m an AI assistant. I can help with a preliminary scheme check; this is not an official decision.",
    "hi": "मैं एक AI सहायक हूँ। मैं योजनाओं की शुरुआती जाँच में मदद कर सकता हूँ; यह आधिकारिक निर्णय नहीं है।",
    "ta": "நான் ஒரு AI உதவியாளர். திட்டங்களைப் பற்றிய ஆரம்ப வழிகாட்டுதலை வழங்குவேன்; இது அதிகாரப்பூர்வ முடிவு அல்ல.",
    "te": "నేను ఒక AI సహాయకుడిని. పథకాలపై ప్రాథమిక మార్గదర్శకం ఇస్తాను; ఇది అధికారిక నిర్ణయం కాదు.",
}
_catalog = Path(__file__).with_name("review_strings.json")
if _catalog.exists():
    AI_DISCLOSURES = json.loads(_catalog.read_text(encoding="utf-8")).get("disclosures", AI_DISCLOSURES)


def disclosure_for(language: str) -> str:
    return AI_DISCLOSURES.get((language or "en").split("-")[0].lower(), AI_DISCLOSURES["en"])
