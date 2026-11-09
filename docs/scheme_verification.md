# Scheme rule verification record

Checked against the official government material linked below on 2026-11-06. The YAML cards remain **unverified drafts**. This review does not approve changing encoded rules. Wording and applicability should receive a human official-source review before any card is marked verified.

## PM-KISAN

Source: [Revised PM-KISAN Operational Guidelines](https://pmkisan.gov.in/Documents/RevisedPM-KISANOperationalGuidelines%28English%29.pdf), especially §§3, 4.1(a), 4.1(b)(v), 5.1–5.3.

| Encoded rule | Official-source statement | Verdict | Reference / gap |
|---|---|---|---|
| `owns_land == true` | The guidelines describe a farmer family owning cultivable land as per land records; beneficiary inclusion is tied to land records. | matches (partial) | §§3 and 5.1. Rule does not verify land-record entry, family definition, cutoff date, or exceptions. |
| `is_institutional_holder == false` | Institutional landholders are excluded. | matches | §4.1(a). |
| `pays_income_tax == false` | A person who paid income tax in the last assessment year is in an excluded category. | matches (partial) | §4.1(b)(v). The YAML's family-level phrasing should be reviewed against the guideline's exact beneficiary/family application. |

Not encoded: other exclusions, land-record cutoff/succession conditions, duplicate/beneficiary validation, e-KYC and payment-account checks. These are documented in YAML `not_checked`; the card's positive result is only a preliminary screen.

## PMFBY

Source: [PMFBY Revised Operational Guidelines](https://pmfby.gov.in/pdf/Revised_Operational_Guidelines.pdf), especially §§3 (Coverage of Farmers), 4 (Coverage of Crops), 7 (Notification), 16 (Seasonality), and 17 (Proposals/premium).

| Encoded rule | Official-source statement | Verdict | Reference / gap |
|---|---|---|---|
| `area_notified == true` | States/UTs issue notifications defining covered crops and insurance units/areas for a season. | matches (partial) | §7, with season dates in §16. The boolean is not verified against live state, district, crop, village, and season notifications. |

The required state, district, crop, and season fields are useful lookup inputs, not eligibility proof by themselves. Farmer category, insurable interest, enrollment deadlines, and live notification details are not fully checked by this rule. No rule changes proposed here.

## PM-KUSUM

Sources: [PM-KUSUM National Portal](https://pmkusum.mnre.gov.in/), [scheme guidelines (2019)](https://pmkusum.mnre.gov.in/pdf/Guidelines%20for%20PM%20KUSUM%20Scheme%20%2822-07-2019%29.pdf), and [official FAQs](https://pmkusum.mnre.gov.in/assets/pdf/PM%20KUSUM%20FAQs%20-%20Revised_%20April%20%28Brand%29.pdf).

| Encoded rule | Official-source statement | Verdict | Reference / gap |
|---|---|---|---|
| `component in [B, C]` | The scheme has components A, B, and C; B covers standalone pumps and C covers solarisation of grid-connected agricultural pumps. | matches (scoped) | Scheme guidelines, component descriptions; FAQ sections “Component B” and “Component C”. This card intentionally screens pump-related B/C only and omits A. |
| `state_application_open == true` | Applications are implemented through state agencies; a current open/closed window is dynamic and was not established as a universal rule in the reviewed static guideline. | unclear | FAQ on application route and the portal's state-wise implementation. Verify the current state notification/window before relying on it. |
| `state_requirements_confirmed == true` | State agencies administer implementation, but this exact confirmation flag is not presented as a universal scheme eligibility condition in the reviewed material. | unclear | FAQ/application route. Treat this as a conservative workflow guard, not an official rule. |

The state window and agency confirmation remain screening safeguards. Pump capacity, grid connection, water source, contribution, technical conditions, beneficiary category, and district allocation still need current state-level checking. No rule changes proposed.

## Verification status

All current YAML files set `verified: false`. Change that only after a person checks every applicable current central and state source, confirms exact rule scope and the dynamic application status, and updates `last_verified`. API responses and the UI display “Unverified draft” while false. Automated freshness checks only guard dates for cards that have been marked verified; they do not independently verify source content.
