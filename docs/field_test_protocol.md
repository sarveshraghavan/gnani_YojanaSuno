# YojanaSuno field-test protocol

This kit is for real, consented recordings used to inspect speech recognition and slot extraction. It is not a representative accuracy study unless the sample design supports that claim.

## Recording plan

1. Recruit at least three speakers for each language where possible. Use anonymous speaker IDs; do not collect phone numbers, Aadhaar, bank details, or other identifiers.
2. Record with both a phone microphone and a laptop microphone. For each speaker/device combination, record in a quiet room, near a running fan, and outdoors with ordinary background noise.
3. Ask each speaker to say scenarios 1, 2, 3, and 5 from the language fixture set in their own words. Scenario 3 includes both a short yes and a short no. Do not ask them to recite unnaturally or include personal account numbers.
4. Obtain consent before recording. Store audio locally in the ignored `samples/` folder under names such as `ta_1.wav`; keep the mapping from speaker ID to person outside this repository.
5. Transcribe each recording using `python scripts/transcribe_samples.py`. Review the transcript with a fluent speaker, then add one CSV row per recording to `field_tests.csv`. Put `real_recording=true` in `notes` only for real, consented field recordings. Use JSON objects for expected and extracted slots.
6. Run `python scripts/score_field_tests.py`. The script reports exact-match slot rates by language and noise condition. It excludes rows not explicitly marked as real recordings.

The suggested coverage is 3 speakers × 2 microphone types × 3 noise conditions × 4 scenarios (with both yes/no variants for scenario 3) per language. If you collect less, record the actual coverage and limitations in the notes rather than extrapolating.

## CSV fields

`id`, `language` (`hi`, `ta`, `te`, `en`), pseudonymous `speaker`, `device` (`phone` or `laptop`), `noise` (`quiet`, `fan`, `outdoor`), `scenario`, human-checked `transcript`, `expected_slots` JSON, `extracted_slots` JSON, `correct` (`y`/`n`), and notes including `real_recording=true` when applicable.

Do not call synthetic fixture results field-test results. Report consent, speakers, device/noise coverage, and exclusions alongside any field-test table.
