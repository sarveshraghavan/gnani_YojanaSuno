# YojanaSuno — Solution Pitch

**YojanaSuno helps farmers understand which government agriculture schemes may fit their situation, in a language they can speak.**

## The problem

Scheme information is spread across portals and notices, while eligibility rules and paperwork can be difficult to interpret. A farmer may not know which details matter, what information is still missing, or where to go next.

## The solution

YojanaSuno is a voice-first guide that asks simple follow-up questions about a farmer’s circumstances, such as land ownership, crop, season, and pump connection. It returns a preliminary scheme screening, explains which answers affected the result, identifies details that still need checking, and gives practical next steps. It is designed for Indian languages and for a phone-friendly experience; the current prototype is a local web demo.

## How it works

Gnani **Prisma** transcribes speech and **Timbre** can speak the response. Extracted answers are checked by a deterministic Python rules engine against versioned scheme data. The language model is not the eligibility decision-maker. The demo has live Prisma/Timbre adapters; Evon extraction is not connected in the current configuration, which uses a conservative local extractor.

## Farmer workflow

**Speak or type → answer a few follow-up questions → confirm the details → review possible schemes, missing checks, and next steps.** Prisma handles speech input; the rules engine screens the answers; Timbre reads the response aloud. If a detail is unclear, the guide asks again instead of guessing.

## Trust and next step

Results are preliminary, not government decisions or approvals. Scheme cards identify unverified rules and information not checked; farmers are directed to official sources or a relevant service centre for confirmation. The prototype does not ask farmers to speak Aadhaar or bank-account numbers and does not submit applications.

**YojanaSuno’s goal:** make the first step toward a relevant scheme clearer, safer, and easier to take.
