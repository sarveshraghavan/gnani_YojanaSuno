# Demo personas

These are mock-only voice scenarios. Tamil, Hindi, and Telugu text is draft wording and needs native-speaker review before a public demo. New scheme cards below are proposal-only YAMLs and are not loaded by the API until approved.

## Personas 1–3 — central scheme screening

These short utterances seed a complete mock session; the bot's follow-up prompts are listed so a demo operator can supply the missing facts in the order shown.

| Persona | Tamil (say this) | Hindi | Telugu | English | Expected prompt / outcome |
|---|---|---|---|---|---|
| 1. Small farmer, land in own name, borewell, no family income tax | என் பெயரில் இரண்டு ஏக்கர் நிலம் உள்ளது. நான் ஆழ்துளை கிணற்றில் இருந்து தண்ணீர் எடுக்கிறேன். எங்கள் குடும்பத்தில் யாரும் வருமான வரி செலுத்துவதில்லை. | मेरे नाम दो एकड़ जमीन है। मैं बोरवेल से पानी लेता हूँ। मेरे परिवार में कोई आयकर नहीं देता। | నా పేరుపై రెండు ఎకరాల భూమి ఉంది. బోరుబావి నీటిని వాడుతాను. మా కుటుంబంలో ఎవరూ ఆదాయపు పన్ను చెల్లించరు. | I have two acres in my name, use a borewell, and nobody in my family pays income tax. | Ask state, crop/season/notification, and PM-KUSUM state/pump details if needed. PM-KISAN should be a potential match; other cards show missing checks as applicable. |
| 2. Land in father's name | நிலம் என் அப்பா பெயரில் உள்ளது; என் பெயரில் இல்லை. | जमीन मेरे पिता के नाम पर है, मेरे नाम पर नहीं। | భూమి మా నాన్న పేరుపై ఉంది, నా పేరుపై లేదు. | The land is in my father's name, not mine. | Confirm land ownership; PM-KISAN should be not eligible under this preliminary screen, with an explanation. Other scheme cards remain independently screened. |
| 3. Family member pays income tax | என் பெயரில் நிலம் உள்ளது; என் அண்ணன் வருமான வரி செலுத்துகிறார். | जमीन मेरे नाम पर है; मेरा भाई आयकर देता है। | భూమి నా పేరుపై ఉంది; మా అన్న ఆదాయపు పన్ను చెల్లిస్తాడు. | The land is in my name; my brother pays income tax. | Clarify whether the taxpayer belongs to the PM-KISAN farmer family; if yes, PM-KISAN should be not eligible. Other scheme cards remain independently screened. |

## Persona 4 — Diesel pump, no grid connection

Say this when the grid-connection question is asked. The expected PM-KUSUM path is Component B (standalone solar pump). Other known profile details are supplied as session context in the integration test; a missing state-specific fact should remain `need_more_info` rather than be inferred.

| Language | Sentence |
|---|---|
| Tamil | என்னிடம் டீசல் பம்ப் உள்ளது; மின் இணைப்பு இல்லை. |
| Hindi | मेरे पास डीज़ल पंप है और बिजली का कनेक्शन नहीं है। |
| Telugu | నా దగ్గర డీజిల్ పంపు ఉంది, విద్యుత్ కనెక్షన్ లేదు. |
| English | I have a diesel pump and no electricity connection. |

Expected: the voice endpoint accepts the answer, retains `has_grid_connected_pump: false`, and the deterministic PM-KUSUM rule mapping resolves to B. Unconfirmed state application details must not be described as approved eligibility.

## Remaining personas from the demo brief

Personas 1–3 (fully matching profile, land in a parent's name, and family income-tax exclusion) still need to be authored with reviewed, exact utterances and end-to-end fixtures before they can be claimed as validated demo scenarios.
