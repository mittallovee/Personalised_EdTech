# Question Language Support

Consolidated 18 October 2026. Initial question-language catalogue is English (en), Hindi (hi), Gujarati (gu), Bengali (bn), Marathi (mr), Telugu (te) and Tamil (ta). Admin may add languages; real engine/rendering quality remains unverified.

## Selection basis

English/Hindi/Gujarati were explicitly requested, with three or four additional widely used Indian regional languages. Bengali/Marathi/Telugu/Tamil were selected under that delegated criterion using the historical [Government of India language statement, 16 March 2021](https://mha.gov.in/MHA1/Par2017/pdfs/par2021-pdfs/LS-16032021/292.pdf), based on Census 2011. This preserves the earlier documented selection basis; it is not a new 2026 population ranking or a measured coaching-user preference.

## Confirmed behavior

Display one language at a time; no mandatory simultaneous bilingual question display. User-facing metadata follows question language without mandatory English duplication. Stable concept IDs remain separate from localized labels/aliases.

Translation runs on faculty request after source review completes, not automatically for every upload/language. Source need not be published. Translation gets its own master/global code and exact source-version link; source and translation can be edited independently. Translated output follows its own QC/approval/publication.

## Catalogue and rendering proposal

Use stable language tags with native/display labels and capability status. Coaching admin extends its catalogue; platform admin may manage explicit targets. Extension never changes old published language/content or creates unrelated concept identities solely because spelling differs.

Track manual storage/rendering/search, OCR/handwriting recognition, tagging and translation capabilities separately. A language dropdown does not prove a selected model/decoder supports it. Unavailable labels/capabilities are visible; do not silently substitute English to satisfy the metadata rule.

Preserve Unicode/mathematics/source context. Verify fonts/search/entry and representative OCR/AI output for all seven initial languages, and label any unsupported route honestly before release.

[AI](AI_MODEL_ORCHESTRATION.md), [taxonomy](TAXONOMY_AND_KNOWLEDGE_GRAPH.md), [examples](QUESTION_SCHEMA_EXAMPLES.md).
