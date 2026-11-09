from collections import Counter
import json
from pathlib import Path
from typing import Iterable

from ..eligibility.models import Result

QUESTIONS = {
    "owns_land": {
        "en": "Is the farmland in your own name?",
        "hi": "क्या खेत आपके अपने नाम पर है?",
        "ta": "விவசாய நிலம் உங்கள் பெயரில் உள்ளதா?",
        "te": "వ్యవసాయ భూమి మీ పేరుపై ఉందా?",
    },
    "is_institutional_holder": {
        "en": "Is the farmland held by an institution, such as a company?",
        "hi": "क्या खेत किसी संस्था या कंपनी के नाम पर है?",
        "ta": "விவசாய நிலம் நிறுவனம் அல்லது நிறுவனத்தின் பெயரில் உள்ளதா?",
        "te": "వ్యవసాయ భూమి ఏదైనా సంస్థ లేదా కంపెనీ పేరుపై ఉందా?",
    },
    "pays_income_tax": {
        "en": "Did anyone in your farmer family pay income tax last year?",
        "hi": "क्या आपके किसान परिवार में किसी ने पिछले साल आयकर दिया था?",
        "ta": "உங்கள் விவசாயக் குடும்பத்தில் யாராவது கடந்த ஆண்டு வருமான வரி செலுத்தினார்களா?",
        "te": "మీ రైతు కుటుంబంలో ఎవరైనా గత సంవత్సరం ఆదాయపు పన్ను చెల్లించారా?",
    },
    "state": {
        "en": "Which state is your farm in?",
        "hi": "आपका खेत किस राज्य में है?",
        "ta": "உங்கள் விவசாய நிலம் எந்த மாநிலத்தில் உள்ளது?",
        "te": "మీ వ్యవసాయ భూమి ఏ రాష్ట్రంలో ఉంది?",
    },
    "district": {
        "en": "Which district is your farm in?",
        "hi": "आपका खेत किस ज़िले में है?",
        "ta": "உங்கள் விவசாய நிலம் எந்த மாவட்டத்தில் உள்ளது?",
        "te": "మీ వ్యవసాయ భూమి ఏ జిల్లాలో ఉంది?",
    },
    "crop": {
        "en": "Which crop are you growing?",
        "hi": "आप कौन-सी फ़सल उगा रहे हैं?",
        "ta": "நீங்கள் என்ன பயிர் செய்கிறீர்கள்?",
        "te": "మీరు ఏ పంటను సాగు చేస్తున్నారు?",
    },
    "season": {
        "en": "Is this the kharif or rabi season?",
        "hi": "यह खरीफ़ की फ़सल है या रबी की?",
        "ta": "இது காரிஃப் பருவமா அல்லது ரபி பருவமா?",
        "te": "ఇది ఖరీఫ్ పంటా లేదా రబీ పంటా?",
    },
    "area_notified": {
        "en": "Have you confirmed that your crop and village are notified for insurance this season?",
        "hi": "क्या आपने पुष्टि की है कि इस मौसम में आपकी फ़सल और गाँव बीमा के लिए अधिसूचित हैं?",
        "ta": "இந்தப் பருவத்தில் உங்கள் பயிரும் கிராமமும் காப்பீட்டுக்கு அறிவிக்கப்பட்டுள்ளதா என்று உறுதி செய்தீர்களா?",
        "te": "ఈ సీజన్‌లో మీ పంట, గ్రామం బీమా కోసం నోటిఫై అయ్యాయని నిర్ధారించారా?",
    },
    "component": {
        "en": "Which PM-KUSUM pump component are you asking about: B or C?",
        "hi": "आप PM-KUSUM के किस पंप घटक के बारे में पूछ रहे हैं: B या C?",
        "ta": "PM-KUSUM திட்டத்தில் எந்த பம்ப் பிரிவு வேண்டும்: B அல்லது C?",
        "te": "PM-KUSUM పథకంలో ఏ పంపు భాగం గురించి అడుగుతున్నారు: B లేదా C?",
    },
    "has_grid_connected_pump": {
        "en": "Does your pump have an electricity (grid) connection?",
        "hi": "क्या आपके पंप में बिजली (ग्रिड) का कनेक्शन है?",
        "ta": "உங்கள் பம்ப்புக்கு மின் இணைப்பு உள்ளதா?",
        "te": "మీ పంపుకు విద్యుత్ (గ్రిడ్) కనెక్షన్ ఉందా?",
    },
    "state_application_open": {
        "en": "Has the government in your state said farmers can apply now?",
        "hi": "क्या आपके राज्य की सरकार ने बताया है कि किसान अभी आवेदन कर सकते हैं?",
        "ta": "உங்கள் மாநில அரசு, விவசாயிகள் இப்போது விண்ணப்பிக்கலாம் என்று தெரிவித்துள்ளதா?",
        "te": "మీ రాష్ట్ర ప్రభుత్వం రైతులు ఇప్పుడు దరఖాస్తు చేసుకోవచ్చని తెలిపిందా?",
    },
    "state_requirements_confirmed": {
        "en": "Has the state agriculture office checked that your pump meets the local rules?",
        "hi": "क्या राज्य के कृषि कार्यालय ने जाँचा है कि आपका पंप वहाँ के नियमों के अनुसार है?",
        "ta": "மாநில வேளாண்மை அலுவலகம் உங்கள் பம்ப் உள்ளூர் விதிகளுக்கு ஏற்ப உள்ளதா என்று சரிபார்த்துள்ளதா?",
        "te": "రాష్ట్ర వ్యవసాయ కార్యాలయం మీ పంపు అక్కడి నిబంధనలకు సరిపోతుందో చూసిందా?",
    },
    "farmer_age": {"en":"How old are you?", "hi":"आपकी उम्र कितनी है?", "ta":"உங்கள் வயது என்ன?", "te":"మీ వయసు ఎంత?"},
    "cultivable_land_hectares": {"en":"How many hectares of cultivable land do you own? Please answer in hectares.", "hi":"आपके पास खेती योग्य जमीन कितने हेक्टेयर है? हेक्टेयर में बताइए।", "ta":"உங்களுக்குச் சொந்தமாக எத்தனை ஹெக்டேர் சாகுபடி நிலம் உள்ளது? ஹெக்டேரில் சொல்லுங்கள்.", "te":"మీకు ఎన్ని హెక్టార్ల సాగు భూమి ఉంది? హెక్టార్లలో చెప్పండి."},
    "kcc_farmer_category": {"en":"Which best describes you: you farm your own land, lease or share land, or apply with a farmer group?", "hi":"आप पर कौन-सी बात लागू होती है: अपनी जमीन पर खेती, पट्टे या बटाई की जमीन पर खेती, या किसान समूह के साथ आवेदन?", "ta":"உங்களுக்கு எது பொருந்தும்: சொந்த நிலத்தில் விவசாயம், குத்தகை அல்லது பங்கு நிலத்தில் விவசாயம், அல்லது விவசாயக் குழுவாக விண்ணப்பிப்பது?", "te":"మీకు ఏది సరిపోతుంది: సొంత భూమిలో సాగు, కౌలు లేదా కౌలు భాగస్వామ్య భూమిలో సాగు, లేదా రైతుల బృందంగా దరఖాస్తు?"},
    "micro_irrigation_interest": {"en":"Would you like to ask about drip or sprinkler irrigation support?", "hi":"क्या आप ड्रिप या स्प्रिंकलर सिंचाई सहायता के बारे में पूछना चाहते हैं?", "ta":"சொட்டு நீர் அல்லது தெளிப்பு நீர் பாசன உதவி பற்றி அறிய விரும்புகிறீர்களா?", "te":"డ్రిప్ లేదా స్ప్రింక్లర్ నీటిపారుదల సహాయం గురించి తెలుసుకోవాలనుకుంటున్నారా?"},
    "state_application_open": {
        "en": "Has the government in your state said farmers can apply now?",
        "hi": "क्या आपके राज्य की सरकार ने बताया है कि किसान अभी आवेदन कर सकते हैं?",
        "ta": "உங்கள் மாநில அரசு, விவசாயிகள் இப்போது விண்ணப்பிக்கலாம் என்று தெரிவித்துள்ளதா?",
        "te": "మీ రాష్ట్ర ప్రభుత్వం రైతులు ఇప్పుడు దరఖాస్తు చేసుకోవచ్చని తెలిపిందా?",
    },
    "state_requirements_confirmed": {
        "en": "Has the state agriculture office checked that your pump meets the local rules?",
        "hi": "क्या राज्य के कृषि कार्यालय ने जाँचा है कि आपका पंप वहाँ के नियमों के अनुसार है?",
        "ta": "மாநில வேளாண்மை அலுவலகம் உங்கள் பம்ப் உள்ளூர் விதிகளுக்கு ஏற்ப உள்ளதா என்று சரிபார்த்துள்ளதா?",
        "te": "రాష్ట్ర వ్యవసాయ కార్యాలయం మీ పంపు అక్కడి నిబంధనలకు సరిపోతుందో చూసిందా?",
    },
}
_catalog = Path(__file__).with_name("review_strings.json")
if _catalog.exists():
    QUESTIONS = json.loads(_catalog.read_text(encoding="utf-8")).get("questions", QUESTIONS)


def next_slot(results: Iterable[Result], excluded: Iterable[str] = ()) -> str | None:
    """Return the missing slot shared by the most schemes still needing details."""
    excluded_slots = set(excluded)
    counts = Counter(
        slot
        for result in results
        if result.status == "need_more_info"
        for slot in result.missing_slots
        if slot not in excluded_slots
    )
    if not counts:
        return None
    fixed_order = (
        "owns_land", "state", "water_source", "has_grid_connected_pump",
        "cultivable_land_hectares", "pays_income_tax", "is_institutional_holder",
    )
    return next((slot for slot in fixed_order if slot in counts), counts.most_common(1)[0][0])


def next_question(results: Iterable[Result], lang: str = "en", excluded: Iterable[str] = ()) -> str | None:
    slot = next_slot(results, excluded)
    if slot is None:
        return None
    question = QUESTIONS.get(slot)
    if question is None:
        return f"Please tell me {slot.replace('_', ' ')}."
    return question.get(lang.split("-")[0].lower(), question["en"])
