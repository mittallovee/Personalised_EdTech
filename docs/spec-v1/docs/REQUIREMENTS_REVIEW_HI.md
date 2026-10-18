# Requirements Review — संक्षिप्त हिंदी गाइड

**18 अक्टूबर 2026:** इस round के जरूरी सवाल पूरे हैं। अब documents एक consolidated review package में हैं। अभी application code शुरू नहीं हुआ है।

## पहली release में क्या बनेगा

- Coaching का पूरा question bank: manual entry, PDF/DOC/DOCX/images से bulk upload, extraction, correction, QC, approve और publish।
- सभी नौ formats: SCQ, multiple-correct, integer, single digit, numerical, matching, assertion–reason, multiple-statement और passage-based।
- English, Hindi, Gujarati, Bengali, Marathi, Telugu और Tamil; admin आगे भाषा जोड़ सकेगा। एक समय में एक भाषा; metadata उसी भाषा में।
- AI tagging और taxonomy; primary के साथ कई secondary concepts। Same-subject prerequisites अलग classes में भी जुड़ सकते हैं; faculty graph देखकर questions खोल सकेगा।
- Faculty के कहने पर variants, translation, diagrams, missing-answer solve और existing-answer/solution check।
- Background jobs चलते समय नई files upload और बाकी app का काम। Cancellation में निकले हुए drafts सुरक्षित।
- Unknown document layout पर AI से pattern सीखना और compatible files पर saved pattern reuse; handwriting और solutions भी शामिल।
- Admin storage/cost dashboard, monthly AI budget, in-app notifications और platform admin द्वारा coaching का independent educational dataset copy।

## महत्वपूर्ण पक्के नियम

शुरुआत में एक coaching और कम faculty होंगे, लेकिन architecture कई coaching और लाखों questions के लिए design होगा। Capacity/speed अभी measured नहीं है।

हर faculty अपना coaching का पूरा bank और उपलब्ध original sources देख सकेगा। Upload/manual/AI default tools हैं। QC, approve, publish और दूसरे creator का question edit करने के लिए अलग permissions हैं। Creator को permission हो तो खुद formal action कर सकता है। Review के लिए अलग व्यक्ति हमेशा जरूरी नहीं।

Platform admin को पूरा supported access रहेगा और वही coaching name/logo बदलेगा। Coaching Owner दूसरे admins को manage करेगा; सभी admins सामान्य faculty को invite/create/remove कर सकेंगे। हटे हुए user का coaching-owned content/history नहीं मिटेगा।

AI metadata सीधे भरेगा। Missing concept/prerequisite जोड़कर तुरंत इस्तेमाल कर सकता है; admin को app में सूचना और बाद में सुधार/approve/merge/revoke की सुविधा मिलेगी। **Email notifications नहीं होंगी।**

Numerical answer 0.00–999.00 में एक exact value या एक inclusive range होगा, दो decimal के साथ। ज्यादा precision flag होगी, चुपचाप rounding नहीं। अलग numerical-unit field नहीं होगा। Multiple-correct में एक option भी correct हो सकता है। Matching के correct mapping में एक right item अलग-अलग left items से share नहीं होगा; unused right items चलेंगे।

Publish के लिए सही answer/valid content और जरूरी classification चाहिए; **solution optional है**। Published content बदलने पर उसी code में नया version बनेगा। Variant/translation का नया global eight-character code होगा। Translation source review के बाद माँगी जा सकेगी; बाद में दोनों versions अलग बदल सकते हैं।

Originals admin के delete करने तक रखेंगे; faculty देख सकेगा। Original हटने पर saved questions/जरूरी diagrams/history सुरक्षित रहेंगे।

## AI और development

Google, Anthropic, OpenAI और OpenRouter पहले; बाद में नए providers जोड़ सकेंगे। हर coaching अपनी keys रखेगी। Admin enabled models/default तय करेगा; compatible fallback error दिखाकर उसी coaching की keys/budget में होगा।

Monthly faculty budget: 80% पर warning, 100% पर नया AI work stop, महीने की पहली तारीख से नया period और पुरानी history सुरक्षित। Actual/estimated/unknown costs अलग दिखेंगे।

Development app **इसी PC पर** चलेगी। Production hosting और hosting budget बाद में। Local app होने पर भी AI APIs/SMS/Google की external configuration/cost अलग हो सकती है।

## क्या अभी बाद के लिए है

Test creation/paper export, student attempts/analytics/recommendations, coaching payments, courses/live/recorded classes और student के level/need के हिसाब से AI teaching/concept videos बाद के phases में हैं। Samples आप बाद में देंगे; अभी फिर से upload माँगना जरूरी नहीं।

## इस package में किस चीज़ का review करना है

[PRD](PRD.md) में current scope, [permissions](PERMISSIONS_MATRIX.md) में अधिकार, [examples](QUESTION_SCHEMA_EXAMPLES.md) में content और [technical proposals](TECHNICAL_DESIGN_PROPOSALS.md) में engineering defaults हैं। Technical proposals आपके बताए requirements को implement करने की हमारी recommendation हैं; उन्हें पहले से approved user decisions नहीं लिखा गया है।

[Roadmap](IMPLEMENTATION_ROADMAP.md) में पहले executable slice का प्रस्ताव है: local web/API/database foundation, tenant isolation, stable codes और version protection। Documents review के बाद उस slice से coding शुरू की जा सकेगी। अभी कोई installation, app server, provider call या application test नहीं चला है।
