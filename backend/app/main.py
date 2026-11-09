from __future__ import annotations
import json
import re
import time
import base64
import inspect
import logging
import unicodedata
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .dialogue import next_question, next_slot
from .dialogue.next_question import QUESTIONS
from .dialogue.disclosure import disclosure_for
from .dialogue.extractor import get_extractor, validate_slots
from .dialogue.component_aliases import as_grid_connection, parse_pump_component
from .eligibility import check_all, load_schemes
from .config import settings
from .voice.providers import get_voice_providers
from .voice.gnani import GnaniProviderError

logger = logging.getLogger(__name__)
@asynccontextmanager
async def lifespan(app: FastAPI):
    voice, llm = active_provider_names()
    logger.info("YojanaSuno providers active: voice=%s, extractor=%s", voice, llm)
    yield

app = FastAPI(title="YojanaSuno", description="A demo voice guide for farm scheme screening", lifespan=lifespan)
ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
GNANI_KEY = settings.gnani_api_key
APP_VERSION = "0.2.0"
SESSION_TTL_SECONDS = 30 * 60
SENSITIVE_DIGITS = re.compile(r"(?<!\d)(?:\d[\s-]?){9,13}\d(?!\d)")
ALLOWED_SLOTS = {
    "owns_land", "is_institutional_holder", "pays_income_tax", "state", "district",
    "crop", "season", "area_notified", "component", "state_application_open",
    "state_requirements_confirmed", "water_source", "has_grid_connected_pump",
    "farmer_age", "cultivable_land_hectares", "kcc_farmer_category", "micro_irrigation_interest",
}
SESSIONS: dict[str, dict[str, Any]] = {}

class ChatRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    language: str = "hi-IN"
    known_slots: dict[str, Any] = Field(default_factory=dict)
    session_id: UUID | None = None
    pending_slot: str | None = None

class EligibilityRequest(BaseModel):
    slots: dict[str, Any] = Field(default_factory=dict)
    language: str = "en-IN"
    session_id: UUID | None = None
    confirmed: bool = False

def purge_expired_sessions(now: float | None = None) -> None:
    current = time.monotonic() if now is None else now
    for session_id, session in list(SESSIONS.items()):
        if current - session["last_seen"] > SESSION_TTL_SECONDS:
            del SESSIONS[session_id]

def clean_slot_updates(updates: dict[str, Any]) -> dict[str, Any]:
    cleaned = {}
    for slot, value in validate_slots(updates).items():
        if slot not in ALLOWED_SLOTS:
            continue
        if isinstance(value, str) and SENSITIVE_DIGITS.search(value):
            continue
        if isinstance(value, int) and not isinstance(value, bool) and len(str(abs(value))) >= 10:
            continue
        cleaned[slot] = value
    return cleaned

def source_basis_for(scheme) -> str:
    references = list(dict.fromkeys(rule.source_ref for rule in scheme.rules if rule.source_ref.strip()))
    if not references:
        return "No guideline section has been confirmed for this draft."
    return f"Based on {scheme.name} guidelines, {', '.join(references)}, checked {scheme.last_verified}."

def merge_session(session_id: UUID | str | None, updates: dict[str, Any]) -> dict[str, Any]:
    updates = clean_slot_updates(updates)
    if not session_id:
        return dict(updates)
    now = time.monotonic()
    purge_expired_sessions(now)
    key = str(session_id)
    if key not in SESSIONS and len(SESSIONS) >= 1000:
        SESSIONS.pop(next(iter(SESSIONS)))
    session = SESSIONS.setdefault(key, {"slots": {}, "last_seen": now, "disclosure_sent": False,
        "voice_failures": 0, "slot_failures": {}, "slot_question_counts": {}, "abandoned_slots": []})
    session.setdefault("slot_failures", {})
    session.setdefault("slot_question_counts", {})
    session.setdefault("abandoned_slots", [])
    session.setdefault("questions_asked", 0)
    session["slots"].update(updates)
    session["last_seen"] = now
    return dict(session["slots"])

def reserve_slot_question(session_id: UUID | str, slot: str) -> bool:
    """Reserve one of at most two prompts for a missing slot in this session."""
    merge_session(session_id, {})
    session = SESSIONS[str(session_id)]
    if slot in session["abandoned_slots"]:
        return False
    if int(session.get("questions_asked", 0)) >= 6:
        session["abandoned_slots"].append(slot)
        return False
    count = int(session["slot_question_counts"].get(slot, 0))
    if count >= 2:
        session["abandoned_slots"].append(slot)
        return False
    session["slot_question_counts"][slot] = count + 1
    session["questions_asked"] = int(session.get("questions_asked", 0)) + 1
    return True

def record_slot_failure(session_id: UUID | str, slot: str) -> bool:
    """Record an unanswered prompt; return True once two failures abandon it."""
    merge_session(session_id, {})
    session = SESSIONS[str(session_id)]
    failures = int(session["slot_failures"].get(slot, 0)) + 1
    session["slot_failures"][slot] = failures
    if failures >= 2 or int(session["slot_question_counts"].get(slot, 0)) >= 2:
        if slot not in session["abandoned_slots"]:
            session["abandoned_slots"].append(slot)
        return True
    reserve_slot_question(session_id, slot)
    return False

def take_disclosure(session_id: UUID, language: str) -> str:
    merge_session(session_id, {})
    session = SESSIONS[str(session_id)]
    if session.get("disclosure_sent"):
        return ""
    session["disclosure_sent"] = True
    return disclosure_for(language)

def include_disclosure(payload: dict[str, Any], line: str) -> dict[str, Any]:
    payload["disclosure"] = line
    if line:
        if payload.get("next_question"):
            payload["next_question"] = f"{line} {payload['next_question']}"
        if payload.get("reply"):
            payload["reply"] = f"{line} {payload['reply']}"
        elif not payload.get("next_question"):
            payload["reply"] = line
    return payload

def active_provider_names() -> tuple[str, str]:
    voice_active = "mock" if settings.use_mock_voice or not settings.gnani_api_key else "Gnani"
    llm_active = "mock/local" if settings.use_mock_llm or not settings.evon_base_url else "Evon"
    return voice_active, llm_active

def voice_mode() -> str:
    return "mock" if settings.use_mock_voice or not GNANI_KEY else "gnani"

def redact_sensitive_numbers(text: str) -> str:
    """Remove Aadhaar, phone, and other long digit runs before extraction or retention."""
    return SENSITIVE_DIGITS.sub("[redacted]", text)

def localized_copy(key: str, language: str) -> str:
    try:
        catalog = json.loads((Path(__file__).resolve().parent / "dialogue" / "review_strings.json").read_text(encoding="utf-8"))
        values = catalog.get(key, {})
        return values.get((language or "en").split("-")[0].lower(), values.get("en", ""))
    except (OSError, ValueError):
        return ""

def voice_retry_message(language: str, attempt: int) -> str:
    if attempt >= 2:
        return voice_fallback(language)
    return localized_copy("retry", language) or "Please say that again. Call 1551 for help."

def register_voice_failure(session_id: UUID, language: str) -> tuple[int, str]:
    merge_session(session_id, {})
    session = SESSIONS[str(session_id)]
    attempt = int(session.get("voice_failures", 0)) + 1
    session["voice_failures"] = attempt
    return attempt, voice_retry_message(language, attempt)

def short_answer(text: str, slot: str | None) -> dict[str, Any]:
    if not slot:
        return {}
    answer = "".join(char if char.isspace() or unicodedata.category(char)[0] in {"L","M","N"} else " "
                     for char in text.strip().casefold()).strip()
    yes = ("yes", "yep", "yeah", "correct", "haan", "han", "ji haan", "jee haan", "ஆம்", "ஆமாம்", "சரி", "అవును", "ఔను", "సరే", "हाँ", "हां", "जी हाँ", "जी हां")
    no = ("no", "nope", "nahi", "nahin", "ji nahi", "jee nahi", "नहीं", "नही", "இல்லை", "இல்ல", "కాదు", "లేదు")
    is_yes = any(answer == word or answer.startswith(word + " ") or answer.startswith(word + ",") for word in yes)
    is_no = any(answer == word or answer.startswith(word + " ") or answer.startswith(word + ",") for word in no)
    if slot == "__confirm__":
        if is_yes or any(phrase in answer for phrase in ("that's right", "that is right", "சரிதான்", "అది సరైనది", "सही है")):
            return {"__confirmation__": True}
        if is_no:
            return {"__confirmation__": False}
        return {}
    if slot in {"component", "has_grid_connected_pump"}:
        component = parse_pump_component(text)
        if component:
            answer = {"has_grid_connected_pump": as_grid_connection(component)}
            # Keep old clients and the unapproved current scheme card working
            # while the reviewed YAML slot mapping is pending.
            if slot == "component": answer["component"] = component
            return answer
        if slot == "has_grid_connected_pump":
            if any(phrase in answer for phrase in (
                "no electricity connection", "no grid connection", "not connected to electricity",
                "மின் இணைப்பு இல்லை", "மின்சாரம் இணைப்பு இல்லை", "बिजली का कनेक्शन नहीं",
                "ग्रिड से जुड़ा नहीं", "విద్యుత్ కనెక్షన్ లేదు", "గ్రిడ్ కనెక్షన్ లేదు",
            )):
                return {slot: False}
            if any(phrase in answer for phrase in (
                "has electricity connection", "has a grid connection", "connected to electricity",
                "மின் இணைப்பு உள்ளது", "மின்சார இணைப்பு உள்ளது", "बिजली का कनेक्शन है",
                "ग्रिड से जुड़ा है", "విద్యుత్ కనెక్షన్ ఉంది", "గ్రిడ్ కనెక్షన్ ఉంది",
            )):
                return {slot: True}
    if slot == "owns_land":
        if re.search(r"\b(?:not|isn't|is not)\b.{0,24}\b(?:in my name|registered to me|my own name)\b", answer):
            return {slot: False}
        if any(phrase in answer for phrase in ("not in my name", "not registered to me", "not my land", "என் பெயரில் இல்லை", "నా పేరు మీద లేదు", "मेरे नाम पर नहीं", "मेरे नाम में नहीं")):
            return {slot: False}
        if any(phrase in answer for phrase in ("in my name", "registered to me", "my own name", "என் பெயரில் உள்ளது", "என் பெயரில் நிலம் இருக்கிறது", "నా పేరు మీద ఉంది", "నా పేరు మీద భూమి ఉంది", "मेरे नाम पर", "मेरे नाम जमीन", "मेरे नाम ज़मीन")):
            return {slot: True}
    if slot == "pays_income_tax":
        if any(phrase in answer for phrase in ("nobody in my family", "no one in my family", "no one in the family", "என் குடும்பத்தில் யாரும் இல்லை", "எங்கள் குடும்பத்தில் யாரும்", "வருமான வரி செலுத்துவதில்லை", "முன்னும் யாரும் வரி செலுத்தவில்லை", "మా కుటుంబంలో ఎవరూ లేరు", "మా కుటుంబంలో ఎవరూ ఆదాయపు పన్ను కట్టరు", "కుటుంబంలో ఎవరూ ఆదాయపు పన్ను కట్టరు", "परिवार में कोई आयकर नहीं देता", "परिवार में कोई आयकर नहीं देता है")):
            return {slot: False}
        family_member = r"(?:my |our )?(?:brother|sister|wife|husband|father|mother|son|daughter|family member)"
        if re.search(f"{family_member}.{{0,35}}\\b(?:pays|pay|paid|does)\\b", answer):
            return {slot: True}
    boolean_slots = {"owns_land", "is_institutional_holder", "pays_income_tax", "area_notified", "state_application_open", "state_requirements_confirmed", "has_grid_connected_pump", "micro_irrigation_interest"}
    if slot in boolean_slots:
        if is_yes:
            return {slot: True}
        if is_no:
            return {slot: False}
    if slot == "component":
        match = re.search(r"\b([ABC])\b", text.upper())
        if match:
            return {slot: match.group(1)}
    if slot == "district" and 1 <= len(text.strip()) <= 80:
        return {slot: text.strip()}
    if slot in {"farmer_age", "cultivable_land_hectares"}:
        number = re.search(r"\d+(?:\.\d+)?", text)
        if number:
            return {slot: float(number.group()) if "." in number.group() else int(number.group())}
    if slot == "kcc_farmer_category":
        if any(x in answer for x in ("tenant", "lease", "sharecrop", "बटाई", "पट्टे", "குத்தகை", "பங்கு நிலம்", "కౌలు")):
            return {slot: "tenant_or_sharecropper"}
        if any(x in answer for x in ("group", "shg", "jlg", "समूह", "குழு", "బృందం")):
            return {slot: "farmer_group"}
        if any(x in answer for x in ("own land", "owner", "अपनी जमीन", "சொந்த நிலம்", "సొంత భూమి")):
            return {slot: "owner_cultivator"}
    return {}

FIX_SLOT_ALIASES = {
    "owns_land": ("land", "ownership", "name", "जमीन", "பெயர்", "భూమి"),
    "is_institutional_holder": ("institution", "company", "संस्था", "நிறுவனம்", "సంస్థ"),
    "pays_income_tax": ("tax", "आयकर", "வரி", "పన్ను"),
    "state": ("state", "राज्य", "மாநிலம்", "రాష్ట్రం"),
    "district": ("district", "ज़िला", "जिला", "மாவட்டம்", "జిల్లా"),
    "crop": ("crop", "फ़सल", "फसल", "பயிர்", "పంట"),
    "season": ("season", "मौसम", "பருவம்", "సీజన్"),
    "area_notified": ("notified", "अधिसूचित", "அறிவிக்கப்பட்ட", "నోటిఫై"),
    "component": ("component", "घटक", "பிரிவு", "భాగం"),
    "has_grid_connected_pump": ("grid connection", "electricity connection", "बिजली कनेक्शन", "ग्रिड कनेक्शन", "மின் இணைப்பு", "வண்டிக்கு மின்சாரம்", "విద్యుత్ కనెక్షన్", "గ్రిడ్ కనెక్షన్"),
    "state_application_open": ("application", "आवेदन", "விண்ணப்பம்", "దరఖాస్తు"),
    "state_requirements_confirmed": ("state agency", "agency", "एजेंसी", "அலுவலகம்", "రాష్ట్ర అమలు సంస్థ"),
}

def resolve_fix_slot(text: str) -> str | None:
    lowered = text.casefold()
    matches = [slot for slot, terms in FIX_SLOT_ALIASES.items() if any(term in lowered for term in terms)]
    return matches[0] if len(matches) == 1 else None

def question_for_slot(slot: str, language: str) -> str:
    labels = QUESTIONS.get(slot, {})
    return labels.get(language.split("-")[0].lower(), labels.get("en", f"Please tell me {slot.replace('_', ' ')}."))

def confirmation_message(slots: dict[str, Any], language: str) -> str:
    if language.startswith("hi"):
        labels = {"owns_land":"ज़मीन आपके नाम पर", "is_institutional_holder":"ज़मीन किसी संस्था के नाम पर", "pays_income_tax":"परिवार में किसी ने आयकर दिया", "state":"राज्य", "district":"ज़िला", "crop":"फ़सल", "season":"मौसम", "area_notified":"फ़सल और गाँव बीमा के लिए अधिसूचित", "component":"PM-KUSUM घटक", "has_grid_connected_pump":"पंप में बिजली का कनेक्शन", "state_application_open":"आवेदन खुले हैं", "state_requirements_confirmed":"राज्य एजेंसी ने पात्रता की पुष्टि की"}
        affirmative, negative, prompt, heard = "हाँ", "नहीं", "क्या ये विवरण सही हैं?", "मैंने यह सुना: "
    elif language.startswith("ta"):
        labels = {"owns_land":"நிலம் உங்கள் பெயரில்", "is_institutional_holder":"நிலம் நிறுவனம் பெயரில்", "pays_income_tax":"குடும்பத்தில் வருமான வரி செலுத்தினர்", "state":"மாநிலம்", "district":"மாவட்டம்", "crop":"பயிர்", "season":"பருவம்", "area_notified":"பயிரும் கிராமமும் காப்பீட்டுக்கு அறிவிக்கப்பட்டது", "component":"PM-KUSUM பிரிவு", "has_grid_connected_pump":"பம்ப்புக்கு மின் இணைப்பு", "state_application_open":"விண்ணப்பங்கள் திறந்துள்ளன", "state_requirements_confirmed":"மாநில அலுவலகம் தகுதியை உறுதி செய்தது"}
        affirmative, negative, prompt, heard = "ஆம்", "இல்லை", "இந்த விவரங்கள் சரியா?", "நான் கேட்டது: "
    elif language.startswith("te"):
        labels = {"owns_land":"భూమి మీ పేరుపై", "is_institutional_holder":"భూమి సంస్థ పేరుపై", "pays_income_tax":"కుటుంబంలో ఆదాయపు పన్ను చెల్లించారు", "state":"రాష్ట్రం", "district":"జిల్లా", "crop":"పంట", "season":"సీజన్", "area_notified":"పంట, గ్రామం బీమాకు నోటిఫై అయ్యాయి", "component":"PM-KUSUM భాగం", "has_grid_connected_pump":"పంపుకు విద్యుత్ కనెక్షన్", "state_application_open":"దరఖాస్తులు తెరిచి ఉన్నాయి", "state_requirements_confirmed":"రాష్ట్ర సంస్థ అర్హత నిర్ధారించింది"}
        affirmative, negative, prompt, heard = "అవును", "కాదు", "ఈ వివరాలు సరైనవేనా?", "మీరు చెప్పిన వివరాలు: "
    else:
        labels = {"owns_land":"land in your name", "is_institutional_holder":"land held by an institution", "pays_income_tax":"a family member paid income tax", "state":"state", "district":"district", "crop":"crop", "season":"season", "area_notified":"crop and village notification", "component":"PM-KUSUM component", "has_grid_connected_pump":"whether the pump has a grid connection", "state_application_open":"applications open", "state_requirements_confirmed":"state agency confirmation"}
        affirmative, negative, prompt, heard = "yes", "no", "Is that right?", "I heard: "
    details = []
    for slot, value in slots.items():
        if slot not in ALLOWED_SLOTS:
            continue
        if isinstance(value, bool):
            value = affirmative if value else negative
        details.append(f"{labels.get(slot, slot.replace('_', ' '))}: {value}")
    return f"{heard}{', '.join(details)}. {prompt}"

def correction_prompt(language: str) -> str:
    if language.startswith("hi"): return "कौन-सी जानकारी ठीक करनी है?"
    if language.startswith("ta"): return "எந்த விவரத்தை மாற்ற வேண்டும்?"
    if language.startswith("te"): return "ఏ వివరాన్ని సరిచేయాలి?"
    return "Which detail should I fix?"

def local_extract(text: str, pending_slot: str | None = None) -> dict[str, Any]:
    """Small conservative fallback extractor for demo phrases; uncertain values stay empty."""
    t = text.casefold()
    out: dict[str, Any] = {}
    if any(phrase in t for phrase in (
        "no electricity connection", "no grid connection", "not connected to electricity",
        "மின் இணைப்பு இல்லை", "மின்சார இணைப்பு இல்லை", "बिजली का कनेक्शन नहीं",
        "ग्रिड से जुड़ा नहीं", "విద్యుత్ కనెక్షన్ లేదు", "గ్రిడ్ కనెక్షన్ లేదు",
    )):
        out["has_grid_connected_pump"] = False
    elif any(phrase in t for phrase in (
        "electricity connection is connected", "has a grid connection", "connected to electricity",
        "மின் இணைப்பு உள்ளது", "மின்சார இணைப்பு உள்ளது", "बिजली का कनेक्शन है",
        "ग्रिड से जुड़ा है", "విద్యుత్ కనెక్షన్ ఉంది", "గ్రిడ్ కనెక్షన్ ఉంది",
    )):
        out["has_grid_connected_pump"] = True
    if any(x in t for x in ["don't own land", "do not own land", "tenant", "lease", "ठेके", "குத்தகை", "కౌలు", "मेरे नाम पर नहीं", "என் பெயரில் இல்லை", "నా పేరు మీద లేదు"]): out["owns_land"] = False
    elif any(x in t for x in ["i own the land", "i own land", "i own ", "मेरी अपनी जमीन", "எனக்கு சொந்தமான நிலம்", "నా సొంత భూమి"]): out["owns_land"] = True
    elif any(phrase in t for phrase in ["not in my name", "not registered to me", "என் பெயரில் இல்லை", "నా పేరు మీద లేదు", "मेरे नाम पर नहीं"]): out["owns_land"] = False
    elif any(phrase in t for phrase in ["मेरे नाम", "என் பெயரில்", "என் பெயரில் நிலம்", "నా పేరు మీద", "నా పేరు మీద భూమి"]): out["owns_land"] = True
    if any(x in t for x in ["not institutional", "not an institutional", "individual land"]): out["is_institutional_holder"] = False
    elif any(x in t for x in ["institutional land", "owned by an institution"]): out["is_institutional_holder"] = True
    if any(x in t for x in ["do not pay income tax", "did not pay income tax", "not an income tax payer", "परिवार में कोई आयकर नहीं देता", "आयकर नहीं देता", "வருமான வரி செலுத்துவதில்லை", "எங்கள் குடும்பத்தில் யாரும் வருமான வரி", "ఆదాయపు పన్ను కట్టరు", "ఎవరూ ఆదాయపు పన్ను"]): out["pays_income_tax"] = False
    elif any(x in t for x in ["pay income tax", "paid income tax", "income tax payer"]): out["pays_income_tax"] = True
    elif any(x in t for x in ["no one in my family pays", "nobody in my family pays", "என் குடும்பத்தில் யாரும் வரி செலுத்தவில்லை", "మా కుటుంబంలో ఎవరూ పన్ను చెల్లించరు"]): out["pays_income_tax"] = False
    elif re.search(r"(?:my |our )?(?:brother|sister|wife|husband|father|mother|son|daughter|family member).{0,35}\b(?:pays|pay|paid|does)\b", t): out["pays_income_tax"] = True
    for state, terms in {"Tamil Nadu":["tamil nadu","தமிழ்நாடு","தமிழ்நாட்டில்","तमिलनाडु","తమిళనాడు"], "Karnataka":["karnataka","கர்நாடகா","கன்னட நாடு","कर्नाटक","కర్ణాటక"], "Andhra Pradesh":["andhra pradesh","ఆంధ్రప్రదేశ్","ఆంధ్ర ప్రదేశ్","आंध्र प्रदेश"], "Uttar Pradesh":["uttar pradesh","उत्तर प्रदेश"], "Maharashtra":["maharashtra","மகாராஷ்டிரா","महाराष्ट्र"]}.items():
        if any(term in t for term in terms): out["state"] = state; break
    for crop, terms in {"rice":["rice","paddy","धान","நெல்","వరి"], "wheat":["wheat","गेहूं","கோதுமை","గోధుమ"], "cotton":["cotton","कपास","பருத்தி","పత్తి"]}.items():
        if any(term in t for term in terms): out["crop"] = crop; break
    if any(x in t for x in ["kharif","खरीफ","காரிஃப்","ఖరీఫ్"]): out["season"] = "kharif"
    elif any(x in t for x in ["rabi","रबी","ரபி","రబీ"]): out["season"] = "rabi"
    if any(x in t for x in ["not notified", "not a notified area", "அறிவிக்கப்படவில்லை", "నోటిఫై చేయలేదు"]): out["area_notified"] = False
    elif any(x in t for x in ["notified crop", "area is notified", "அறிவிக்கப்பட்ட பயிர்", "నోటిఫైడ్ పంట"]): out["area_notified"] = True
    if any(x in t for x in ["applications are closed", "application is closed", "விண்ணப்பம் மூடப்பட்டது", "దరఖాస్తులు మూసివేశారు"]): out["state_application_open"] = False
    elif any(x in t for x in ["kusum applications are open", "application is open", "விண்ணப்பம் திறந்துள்ளது", "దరఖాస్తులు తెరిచి ఉన్నాయి"]): out["state_application_open"] = True
    if any(x in t for x in ["borewell", "bore well", "போர்வெல்", "ஆழ்துளை கிணறு", "బోర్‌వెల్", "బోరుబావి", "బోరు బావి", "बोरवेल"]): out["water_source"] = "borewell"
    elif any(x in t for x in ["canal", "கால்வாய்", "కాలువ"]): out["water_source"] = "canal"
    elif any(x in t for x in ["rain water", "rainwater", "மழைநீர்", "వర్షపు నీరు"]): out["water_source"] = "rain"
    elif any(x in t for x in ["well", "கிணறு", "బావి"]): out["water_source"] = "well"
    out.update(short_answer(text, pending_slot))
    if pending_slot in {"state", "district", "crop", "kcc_farmer_category"} and 1 <= len(text.strip()) <= 80 and pending_slot not in out:
        out[pending_slot] = text.strip()
    if pending_slot == "season" and any(word in t for word in ["kharif", "खरीफ", "காரிஃப்", "ఖరీఫ్"]):
        out["season"] = "kharif"
    elif pending_slot == "season" and any(word in t for word in ["rabi", "रबी", "ரபி", "రబీ"]):
        out["season"] = "rabi"
    return out

def extract_slots(text: str, language: str, known: dict[str, Any],
                  pending_slot: str | None = None) -> tuple[dict[str, Any], bool, bool]:
    """Return validated facts, whether local fallback was used, and whether to re-ask."""
    extractor = get_extractor()
    try:
        model_slots = validate_slots(extractor.extract(text, language, known, pending_slot))
    except Exception:
        model_slots = {}
    local_slots = validate_slots(local_extract(text, pending_slot))
    # Explicit local yes/no and regex signals take precedence over uncertain model output.
    slots = validate_slots({**model_slots, **local_slots})
    used_fallback = extractor.is_mock or not model_slots
    should_reask = bool(pending_slot and pending_slot not in slots)
    return slots, used_fallback, should_reask

def compose(results: list[dict], language: str) -> str:
    if language.startswith("hi"):
        head = "यह शुरुआती डेमो जाँच है। आधिकारिक पात्रता की पुष्टि योजना कार्यालय से करें।"
        labels = {"eligible":"मेल हो सकता है", "not_eligible":"मेल नहीं हो सकता", "need_more_info":"और जानकारी चाहिए"}
        missing = "कृपया बताएं: "
        field_names = {"state":"आपका राज्य", "district":"आपका ज़िला", "owns_land":"क्या किसान परिवार के पास भूमि है", "is_institutional_holder":"क्या भूमि किसी संस्था के नाम है", "pays_income_tax":"क्या परिवार के सदस्य ने आयकर दिया", "crop":"आपकी फ़सल", "season":"फ़सल का मौसम", "area_notified":"क्या गाँव और फ़सल अधिसूचित हैं", "component":"PM-KUSUM घटक", "has_grid_connected_pump":"पंप में बिजली का कनेक्शन", "water_source":"पानी का स्रोत", "grid_connected":"बिजली कनेक्शन", "state_application_open":"क्या राज्य में आवेदन खुले हैं", "state_requirements_confirmed":"राज्य एजेंसी की पुष्टि"}
        next_step = "ताज़ा जानकारी के लिए आधिकारिक पोर्टल या नज़दीकी सामान्य सेवा केंद्र से पूछें।"
    elif language.startswith("ta"):
        head = "இது ஒரு ஆரம்ப டெமோ வழிகாட்டி. அதிகாரப்பூர்வ தகுதியை திட்ட அலுவலகத்தில் உறுதிப்படுத்தவும்."
        labels = {"eligible":"பொருந்தக்கூடும்", "not_eligible":"பொருந்தாமல் இருக்கலாம்", "need_more_info":"மேலும் விவரம் தேவை"}
        missing = "தேவையான விவரங்கள்: "
        field_names = {"state":"மாநிலம்", "district":"மாவட்டம்", "owns_land":"நில உரிமை", "is_institutional_holder":"நிறுவன நிலமா", "pays_income_tax":"வருமான வரி", "crop":"பயிர்", "season":"பருவம்", "area_notified":"அறிவிக்கப்பட்ட பகுதி", "component":"திட்டப் பிரிவு", "has_grid_connected_pump":"பம்ப்புக்கு மின் இணைப்பு", "water_source":"நீர் ஆதாரம்", "grid_connected":"மின் இணைப்பு", "state_application_open":"விண்ணப்பம் திறந்திருப்பது", "state_requirements_confirmed":"மாநிலத் தகுதி உறுதி"}
        next_step = "மேலும் விவரங்களுக்கு அதிகாரப்பூர்வ இணையதளம் அல்லது அருகிலுள்ள பொது சேவை மையத்தை அணுகவும்."
    elif language.startswith("te"):
        head = "ఇది ప్రాథమిక డెమో మార్గదర్శకం. అధికారిక అర్హతను పథకం కార్యాలయంలో నిర్ధారించండి."
        labels = {"eligible":"సరిపోవచ్చు", "not_eligible":"సరిపోకపోవచ్చు", "need_more_info":"మరిన్ని వివరాలు కావాలి"}
        missing = "అవసరమైన వివరాలు: "
        field_names = {"state":"రాష్ట్రం", "district":"జిల్లా", "owns_land":"భూమి యాజమాన్యం", "is_institutional_holder":"సంస్థ భూమినా", "pays_income_tax":"ఆదాయపు పన్ను", "crop":"పంట", "season":"సీజన్", "area_notified":"నోటిఫై చేసిన ప్రాంతం", "component":"పథకం భాగం", "has_grid_connected_pump":"పంపుకు విద్యుత్ కనెక్షన్", "water_source":"నీటి వనరు", "grid_connected":"విద్యుత్ కనెక్షన్", "state_application_open":"దరఖాస్తులు తెరిచి ఉన్నాయా", "state_requirements_confirmed":"రాష్ట్ర అర్హత నిర్ధారణ"}
        next_step = "మరిన్ని వివరాల కోసం అధికారిక వెబ్‌సైట్ లేదా సమీపంలోని సాధారణ సేవా కేంద్రాన్ని సంప్రదించండి."
    else:
        head = "This is an initial demo screening. Confirm current eligibility with the official scheme office."
        labels = {"eligible":"Potential match", "not_eligible":"May not match", "need_more_info":"More information needed"}
        missing = "Please tell me: "
        field_names = {"state":"your state", "district":"your district", "owns_land":"whether your farmer family owns the land", "is_institutional_holder":"whether an institution holds the land", "pays_income_tax":"whether a family member paid income tax last year", "crop":"your crop", "season":"the crop season", "area_notified":"whether your village and crop are notified", "component":"the PM-KUSUM component", "has_grid_connected_pump":"whether the pump has a grid connection", "water_source":"your water source", "grid_connected":"whether electricity is connected", "state_application_open":"whether applications are open in your state", "state_requirements_confirmed":"whether the state agency confirmed your requirements"}
        next_step = "For current details, check the official portal or ask your nearest Common Service Centre."
    lines = [head]
    for r in results:
        line = f"{r['name']}: {labels[r['status']]}"
        if r["missing"]: line += ". " + missing + ", ".join(field_names.get(k, k.replace("_", " ")) for k in r["missing"])
        elif r["status"] == "eligible": line += ". " + next_step
        elif r["reasons"]:
            failed_slots = {reason.get("slot") for reason in r["reasons"] if isinstance(reason, dict)}
            if "owns_land" in failed_slots:
                reason_text = {
                    "hi": "क्योंकि जमीन किसान परिवार के अपने नाम पर नहीं है।",
                    "ta": "விவசாயக் குடும்பத்தின் பெயரில் நிலம் இல்லாததால் இது பொருந்தவில்லை.",
                    "te": "రైతు కుటుంబం పేరుపై భూమి లేనందున ఇది సరిపోలలేదు.",
                    "en": "because the land is not in the farmer family's name.",
                }.get(language[:2], "because the land is not in the farmer family's name.")
            elif "pays_income_tax" in failed_slots:
                reason_text = {
                    "hi": "क्योंकि किसान परिवार का सदस्य पिछले आकलन वर्ष में आयकर देता था।",
                    "ta": "விவசாயக் குடும்பத்தில் ஒருவர் கடந்த மதிப்பீட்டு ஆண்டில் வருமான வரி செலுத்தியதால் இது பொருந்தவில்லை.",
                    "te": "రైతు కుటుంబ సభ్యుడు గత అంచనా సంవత్సరంలో ఆదాయపు పన్ను చెల్లించినందున ఇది సరిపోలలేదు.",
                    "en": "because a member of the farmer family paid income tax in the last assessment year.",
                }.get(language[:2], "because a family member paid income tax in the last assessment year.")
            else:
                reason_text = next_step
            line += ". " + reason_text
        lines.append(line)
    return "\n".join(lines)

def incomplete_message(language: str) -> str:
    """Explain an incomplete rule check without misreporting a voice outage."""
    messages = {
        "hi": "कुछ योजनाओं की शुरुआती जाँच के लिए जानकारी पूरी नहीं है। ऊपर दी गई बाकी जानकारी को आधिकारिक योजना कार्यालय से जाँचें। यह सरकारी निर्णय नहीं है।",
        "ta": "சில திட்டங்களுக்கான ஆரம்பச் சரிபார்ப்புக்கு தகவல் போதவில்லை. மேலே காட்டியுள்ள விடுபட்ட விவரங்களை அதிகாரப்பூர்வ திட்ட அலுவலகத்தில் சரிபார்க்கவும். இது அரசு முடிவு அல்ல.",
        "te": "కొన్ని పథకాల ప్రాథమిక పరిశీలనకు సమాచారం సరిపోలేదు. పైన చూపిన మిగిలిన వివరాలను అధికారిక పథకం కార్యాలయంలో నిర్ధారించండి. ఇది ప్రభుత్వ నిర్ణయం కాదు.",
        "en": "Some scheme checks are incomplete because the required details could not be confirmed. Review the missing details above with the official scheme office. This is not an official decision.",
    }
    return messages.get((language or "en").split("-")[0].lower(), messages["en"])

@app.get("/api/schemes")
def schemes():
    return [{k:v for k,v in s.model_dump().items() if k != "rules"} for s in load_schemes()]

@app.get("/api/health")
def health():
    voice, extractor = active_provider_names()
    return {"status": "ok", "version": APP_VERSION, "providers": {"stt": voice, "tts": voice, "extractor": extractor},
            "modes": {"voice_mock": settings.use_mock_voice, "llm_mock": settings.use_mock_llm},
            "schemes": {s.id: s.version for s in load_schemes()}}

@app.post("/api/check")
def check_eligibility(req: EligibilityRequest):
    """Evaluate known slots against the versioned YAML scheme registry."""
    session_id = req.session_id or uuid4()
    disclosure = take_disclosure(session_id, req.language)
    slots = merge_session(session_id, req.slots)
    session = SESSIONS[str(session_id)]
    scheme_list = load_schemes()
    results = check_all(slots, scheme_list)
    abandoned = set(session["abandoned_slots"])
    slot_to_ask = next_slot(results, abandoned)
    while slot_to_ask and not reserve_slot_question(session_id, slot_to_ask):
        abandoned = set(session["abandoned_slots"])
        slot_to_ask = next_slot(results, abandoned)
    if slot_to_ask:
        question = next_question(results, req.language, abandoned)
        return include_disclosure({"results": [], "slots": slots, "next_slot": slot_to_ask,
                "next_question": question, "stage": "collecting",
                "reply": question,
                "scope": localized_copy("scope", req.language),
                "session_id": str(session_id)}, disclosure)

    by_id = {scheme.id: scheme for scheme in scheme_list}
    response_results = []
    for result in results:
        scheme = by_id[result.scheme_id]
        unchecked = [slot for slot in scheme.required_slots if slot in abandoned]
        response_results.append({**result.model_dump(), "benefit": scheme.benefit,
            "source_url": scheme.source_url, "sources": scheme.sources,
            "last_verified": scheme.last_verified, "verified": scheme.verified,
            "badge": "Verified" if scheme.verified else "Unverified draft",
            "source_basis": source_basis_for(scheme),
            "not_checked": [*scheme.not_checked, *unchecked],
            "not_checked_slots": unchecked,
            "next_steps": scheme.next_steps})

    if any(result.status == "need_more_info" for result in results):
        return include_disclosure({"results": response_results, "slots": slots,
                "next_slot": None, "next_question": None, "stage": "incomplete",
                "reply": incomplete_message(req.language),
                "scope": localized_copy("scope", req.language),
                "session_id": str(session_id)}, disclosure)
    if not req.confirmed:
        confirm = confirmation_message(slots, req.language)
        return include_disclosure({"results": [], "slots": slots, "next_slot": "__confirm__",
                "next_question": confirm, "stage": "confirming", "reply": confirm,
                "scope": localized_copy("scope", req.language),
                "session_id": str(session_id)}, disclosure)
    presentation = [{"name": result["scheme_name"], "status": result["status"],
                     "missing": result["missing_slots"], "reasons": result["failed_rules"]}
                    for result in response_results]
    return include_disclosure({"results": response_results, "slots": slots,
            "next_slot": None, "next_question": None, "stage": "complete",
            "reply": compose(presentation, req.language),
            "scope": localized_copy("scope", req.language),
            "session_id": str(session_id)}, disclosure)

@app.post("/api/chat")
def chat(req: ChatRequest):
    session_id = req.session_id or uuid4()
    disclosure = take_disclosure(session_id, req.language)
    sensitive_input = redact_sensitive_numbers(req.text) != req.text
    previous = merge_session(session_id, req.known_slots)
    def response(payload: dict[str, Any]) -> dict[str, Any]:
        payload["session_id"] = str(session_id)
        payload = include_disclosure(payload, disclosure)
        if sensitive_input:
            warning = localized_copy("privacy_warning", req.language)
            payload["privacy_warning"] = warning
            if payload.get("reply"):
                payload["reply"] = f"{warning} {payload['reply']}"
            if payload.get("next_question"):
                payload["next_question"] = f"{warning} {payload['next_question']}"
            if not payload.get("reply") and not payload.get("next_question"):
                payload["reply"] = warning
        return payload
    if req.pending_slot == "__confirm__":
        answer = short_answer(req.text, "__confirm__").get("__confirmation__")
        if answer is True:
            return response({"stage": "confirmed", "confirmed": True, "slots": previous, "pending_slot": None})
        if answer is False:
            return response({"stage": "fix_detail", "next_question": correction_prompt(req.language),
                    "pending_slot": "__fix_slot__", "slots": previous})
        return response({"stage": "confirm_retry", "next_question": confirmation_message(previous, req.language),
                "pending_slot": "__confirm__", "slots": previous})
    if req.pending_slot == "__fix_slot__":
        slot = resolve_fix_slot(req.text)
        if slot:
            return response({"stage": "correction", "next_slot": slot,
                    "next_question": question_for_slot(slot, req.language),
                    "pending_slot": slot, "slots": previous})
        return response({"stage": "fix_detail", "next_question": correction_prompt(req.language),
                "pending_slot": "__fix_slot__", "slots": previous})
    safe_text = redact_sensitive_numbers(req.text)
    extracted, used_fallback, should_reask = extract_slots(safe_text, req.language, previous, req.pending_slot)
    if should_reask:
        abandoned = record_slot_failure(session_id, req.pending_slot or "")
        if abandoned:
            return response({"stage": "slot_abandoned", "next_question": None,
                    "abandoned_slot": req.pending_slot, "slots": previous,
                    "transcript": safe_text,
                    "mode": "mock/local extraction" if used_fallback else "evon"})
        return response({"stage": "clarify", "next_question": question_for_slot(req.pending_slot or "", req.language),
                         "pending_slot": req.pending_slot, "slots": previous, "transcript": safe_text,
                         "mode": "mock/local extraction" if used_fallback else "evon"})
    slots = merge_session(session_id, {**previous, **extracted})
    session = SESSIONS[str(session_id)]
    completed = set(extracted)
    if req.pending_slot == "component" and "has_grid_connected_pump" in extracted:
        completed.add("component")
    session["abandoned_slots"] = [slot for slot in session["abandoned_slots"] if slot not in completed]
    return response({"transcript": safe_text, "slots": slots,
            "mode": "mock/local extraction" if used_fallback else "evon"})

@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...), language: str = Form("hi-IN")):
    content = await audio.read()
    if len(content) > 15_000_000: raise HTTPException(413, "Audio clip is too large")
    try:
        stt, _ = get_voice_providers()
        result = stt.transcribe(content, language, filename=audio.filename or "farmer-audio.wav",
                                mime_type=audio.content_type or "audio/wav")
        if inspect.isawaitable(result):
            result = await result
        return {"success": True, "transcript": redact_sensitive_numbers(result.transcript),
                "detected_language_code": result.language, "confidence": result.confidence,
                "mode": voice_mode()}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, "Prisma transcription failed. Please try again or call 1551.") from exc

@app.post("/api/speak")
async def speak(payload: dict):
    lang = payload.get("language", "hi-IN")
    if voice_mode() == "mock":
        raise HTTPException(503, "Model-generated speech is off in mock mode. Start the demo in live mode.")
    try:
        _, tts = get_voice_providers()
        audio = tts.synthesize(str(payload.get("text", "")), lang)
        if inspect.isawaitable(audio):
            audio = await audio
        return Response(audio, media_type="audio/wav")
    except Exception as exc:
        raise HTTPException(503, "Model-generated speech is unavailable for this reply. Please try again.") from exc

def voice_fallback(language: str) -> str:
    try:
        catalog_path = Path(__file__).resolve().parent / "dialogue" / "review_strings.json"
        localized = json.loads(catalog_path.read_text(encoding="utf-8")).get("fallbacks", {})
        code = (language or "en").split("-")[0].lower()
        if code in localized:
            return localized[code]
    except (OSError, ValueError):
        pass
    if language.startswith("hi"):
        return "आवाज़ सेवा अभी उपलब्ध नहीं है। कृपया फिर से कोशिश करें या किसान कॉल सेंटर 1551 पर कॉल करें।"
    if language.startswith("ta"):
        return "குரல் சேவை இப்போது கிடைக்கவில்லை. மீண்டும் முயற்சிக்கவும் அல்லது விவசாயிகள் அழைப்பு மையம் 1551-ஐ அழைக்கவும்."
    if language.startswith("te"):
        return "వాయిస్ సేవ అందుబాటులో లేదు. మళ్లీ ప్రయత్నించండి లేదా కిసాన్ కాల్ సెంటర్ 1551కు కాల్ చేయండి."
    return "Voice service is unavailable. Please try again or call the Kisan Call Centre at 1551."

def voice_fallback_text(reply: str, language: str) -> str:
    return " ".join(part for part in (reply, voice_fallback(language)) if part)

@app.post("/api/voice")
async def voice_turn(
    audio: UploadFile = File(...),
    language: str = Form("hi-IN"),
    session_id: UUID | None = Form(None),
    pending_slot: str | None = Form(None),
    known_slots: str = Form("{}"),
):
    """Mock-ready audio turn: STT -> slot/dialogue -> rules -> TTS."""
    content = await audio.read()
    if len(content) > 15_000_000:
        raise HTTPException(413, "Audio clip is too large")
    try:
        parsed_slots = json.loads(known_slots)
        if not isinstance(parsed_slots, dict):
            raise ValueError("known_slots must be a JSON object")
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(400, "known_slots must be a JSON object") from exc
    session_id = session_id or uuid4()
    stt, tts = get_voice_providers()
    stt_started = time.perf_counter()
    try:
        transcript_result = stt.transcribe(
            content, language, filename=audio.filename or "farmer-audio.wav",
            mime_type=audio.content_type or "audio/wav")
        if inspect.isawaitable(transcript_result):
            transcript_result = await transcript_result
    except Exception:
        stt_ms = (time.perf_counter() - stt_started) * 1000
        _, retry_message = register_voice_failure(session_id, language)
        disclosure = take_disclosure(session_id, language)
        prompt = " ".join(part for part in (disclosure, retry_message) if part)
        tts_started = time.perf_counter()
        audio_bytes = await tts_or_none(tts, prompt, language)
        logger.info("voice_request_timings stt_ms=%.1f dialogue_ms=0.0 tts_ms=%.1f", stt_ms, (time.perf_counter()-tts_started)*1000)
        return {"stage": "retry", "results": [], "slots": parsed_slots,
                "next_question": prompt, "reply": prompt, "next_slot": pending_slot,
                "session_id": str(session_id), "audio_base64": base64.b64encode(audio_bytes).decode("ascii") if audio_bytes else None,
                "fallback_audio_text": prompt, "mode": voice_mode()}
    raw_transcript = transcript_result.transcript
    sensitive_transcript = redact_sensitive_numbers(raw_transcript) != raw_transcript
    transcript = redact_sensitive_numbers(raw_transcript)
    stt_ms = (time.perf_counter() - stt_started) * 1000
    lang = transcript_result.language or language
    if not transcript.strip() or (transcript_result.confidence is not None and transcript_result.confidence < 0.45):
        _, retry_message = register_voice_failure(session_id, lang)
        disclosure = take_disclosure(session_id, lang)
        prompt = " ".join(part for part in (disclosure, retry_message) if part)
        checked = {"stage": "retry", "results": [], "slots": parsed_slots,
                   "next_question": prompt, "reply": prompt, "next_slot": pending_slot,
                   "session_id": str(session_id)}
    else:
        SESSIONS.setdefault(str(session_id), {"slots": {}, "last_seen": time.monotonic(), "disclosure_sent": False, "voice_failures": 0})["voice_failures"] = 0
        dialogue_started = time.perf_counter()
        extracted = chat(ChatRequest(text=transcript, language=lang, known_slots=parsed_slots,
                                     session_id=session_id, pending_slot=pending_slot))
        if extracted.get("stage") in {"fix_detail", "correction", "confirm_retry", "clarify"}:
            prompt = extracted.get("next_question", "")
            checked = {**extracted, "results": [], "reply": prompt,
                       "next_slot": extracted.get("next_slot", extracted.get("pending_slot"))}
        else:
            confirmed = bool(extracted.get("confirmed"))
            slots = extracted.get("slots", parsed_slots)
            checked = check_eligibility(EligibilityRequest(
                slots=slots, language=lang, session_id=session_id, confirmed=confirmed))
            checked = {**checked, "transcript": transcript,
                       "mode": voice_mode()}
            checked = include_disclosure(checked, extracted.get("disclosure", ""))
            warning=extracted.get("privacy_warning") or (localized_copy("privacy_warning",lang) if sensitive_transcript else "")
            if warning:
                checked["privacy_warning"]=warning
                if checked.get("reply") and warning not in checked["reply"]:
                    checked["reply"]=f"{warning} {checked['reply']}"
                if checked.get("next_question") and warning not in checked["next_question"]:
                    checked["next_question"]=f"{warning} {checked['next_question']}"
        dialogue_ms = (time.perf_counter() - dialogue_started) * 1000
        prompt = checked.get("next_question") or checked.get("reply", "")
    if not transcript.strip() or (transcript_result.confidence is not None and transcript_result.confidence < 0.45):
        dialogue_ms = 0.0
    tts_started = time.perf_counter()
    spoken = await tts_or_none(tts, prompt, lang) if prompt else b""
    logger.info("voice_request_timings stt_ms=%.1f dialogue_ms=%.1f tts_ms=%.1f", stt_ms, dialogue_ms, (time.perf_counter()-tts_started)*1000)
    fallback_text = "" if spoken else voice_fallback_text(checked.get("reply", ""), lang)
    return {**checked, "transcript": transcript,
            "detected_language_code": lang,
            "audio_base64": base64.b64encode(spoken).decode("ascii") if spoken else None,
            "fallback_audio_text": fallback_text,
            "session_id": str(session_id),
            "mode": voice_mode()}

async def tts_or_none(tts: Any, text: str, language: str) -> bytes:
    try:
        result = tts.synthesize(text, language)
        if inspect.isawaitable(result):
            result = await result
        return result if isinstance(result, bytes) else b""
    except Exception:
        return b""

@app.get("/")
def home():
    return FileResponse(FRONTEND / "index.html")

@app.get("/style.css")
def stylesheet():
    return FileResponse(FRONTEND / "style.css", media_type="text/css")

@app.get("/app.js")
def frontend_script():
    return FileResponse(FRONTEND / "app.js", media_type="application/javascript")

app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
