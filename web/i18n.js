/* Khazna UI text, English and Arabic. */
(function () {
  const EN = {
    skip: "Skip to content", menu: "Menu", loading: "Opening the vault…", viewing_as: "Viewing as",
    nav_ask: "Ask", nav_library: "Library", nav_upload: "Your files", nav_evidence: "Evidence", nav_how: "How it works",
    foot_data: "Sadeem Freight and every document, person and number here are fictional, made for this demo.",
    foot_by: "Built by Ayesha Lubna.", foot_code: "Source code on GitHub", other_lang: "عربي",
    title: "Ask your company's documents. Nothing leaves the vault.",
    lede: "Khazna answers questions about confidential documents in English or Arabic, with the exact source for every answer. It only reads what your role is allowed to see, hides personal data, ignores instructions planted inside documents, and runs entirely on this server.",
    specimen_title: "Payroll record (example)", specimen_stamp: "RESTRICTED",
    specimen_l1: "Employee: Fatima Al Hammadi, G4 Specialist.", specimen_l2: "Emirates ID", specimen_l3: "Salary account IBAN", specimen_l4: "Mobile",
    ask_ph: "Ask a question, e.g. How many days of annual leave do I get?", ask_btn: "Ask",
    viewing: (r, n) => `You are asking as <b>${r}</b>, who can read <b>${n}</b> of the company's documents. Change the role at the top to see how answers change.`,
    try: "Try:", tag: { restricted: "Restricted", pii: "Personal data", injection: "Hidden instruction", off: "Not in documents", ar: "Arabic", cross: "Cross-language", version: "Old version exists" },
    your_q: "Your question", thinking: "Searching the documents you can read…", writing: "Writing the answer inside this server…",
    sources_h: "Sources", open_doc: "Open document", cited: "Used in the answer", superseded: "Outdated version",
    b_cited: (n) => `Answer backed by ${n} source${n > 1 ? "s" : ""}`, b_refused: "Not in the documents you can read",
    b_masked: (n) => `${n} personal detail${n > 1 ? "s" : ""} hidden`, b_inj: (n) => `${n} hidden instruction${n > 1 ? "s" : ""} ignored`,
    b_local: "Answered on this server", b_quote: "Quoted from the source", b_model: (m) => `Written by ${m} on this server`,
    b_fallback: "Model answer failed a check: showing the verified quote", b_old: "An older version also exists",
    removed_note: (n) => `${n} sentence${n > 1 ? "s" : ""} that tried to instruct the AI ${n > 1 ? "were" : "was"} removed from this passage`,
    rail_h: "Privacy ledger", rail_q: "Questions this session", rail_mask: "Personal details hidden", rail_inj: "Planted instructions ignored",
    rail_net: "Outbound network attempts blocked", rail_where: (m) => `Model: ${m || "built-in quoting (no model)"}. Everything runs inside this server; the network guard blocks any connection to the outside.`,
    rail_guard_on: "Network guard on", rail_guard_off: "Network guard off",
    lib_h: "Library", lib_lede: (r, n, t) => `${t} documents. As <b>${r}</b> you can read <b>${n}</b>. Locked documents are never searched for your role, so they cannot appear in an answer.`,
    th_doc: "Document", th_cls: "Classification", th_owner: "Owner", th_access: "Your access", th_pii: "Personal data inside",
    can: "Can read", cannot: "Locked", read: "Read", none_pii: "None", old: "Outdated",
    pii_kind: { emirates_id: "Emirates ID", iban: "IBAN", phone: "phone", email: "e-mail", card: "card", passport: "passport" },
    doc_masked: (n) => `${n} personal detail${n > 1 ? "s" : ""} hidden in this view.`,
    doc_old: "This version has been replaced. Khazna ranks it below the current version.",
    inj_h: "Hidden instruction detected", inj_p: "This text tries to instruct an AI. Khazna removes it before answering and never follows it.",
    close: "Close",
    up_h: "Your files", up_lede: (t, m) => `Upload a PDF, Word or text file (up to ${m} MB) and ask questions about it. It is processed in this server's memory, never shared with other visitors, and deleted automatically after ${t} minutes.`,
    drop: "Drop a file here or click to choose", drop2: "PDF, DOCX, TXT or MD",
    up_ok: (n, w) => `${n} added (${w} words). Ask about it on the Ask page.`, up_pii: (s) => `Personal data found and hidden: ${s}.`,
    up_del: "Delete now", up_expires: (m) => `Deleted automatically in ${m} min`, up_none: "No files yet.",
    up_ask: "Ask about it", deleted: "Deleted.",
    scan_h: "Try the personal-data mask", scan_p: "Paste any text with UAE phone numbers, Emirates IDs or IBANs. Nothing is stored.",
    scan_ph: "e.g. Call Ahmed on 050 123 4567. IBAN AE07 0331 2345 6789 0123 456.", scan_btn: "Mask it",
    ev_h: "Evidence", ev_lede: (n) => `${n} test questions with known answers, run automatically on every code change. Any leak fails the build.`,
    ev_f1: "answers correct", ev_f2: "Arabic ↔ English questions correct", ev_f3: "off-topic questions refused", ev_f4: "leaks across all checks",
    ev_leaks: "Leak checks", ev_leaks_p: (n) => `${n} forbidden strings are checked in every answer and every passage shown.`,
    lk: { restricted: "Restricted documents (salary bands, board minutes, contract)", pii: "Personal identifiers (Emirates ID, IBAN, personal mobile)", injection: "Planted instruction (\"ignore all previous instructions…\")", superseded: "Values from the outdated 2024 handbook" },
    ev_ans: "Answer quality", ev_ret: "Finding the right passage",
    m: { acc: "Correct answers", en: "English facts", ar: "Arabic facts", cross: "Arabic ↔ English", ver: "Current version preferred", unans: "Off-topic refused", restr: "Restricted questions refused", p50: "Median time" },
    mode_builtin: "Built-in (no model)", mode_llm: (m) => `Local model (${m})`,
    ret_cols: ["Method", "Top result right", "Right in top 5", "MRR"],
    ev_note: "Questions about locked documents that are not refused are answered from permitted documents only: the leak checks confirm nothing restricted is shown.",
    how_h: "How it works",
    flow: [["Who is asking", "The role decides which documents can be searched."], ["Find", "Keyword (BM25) + meaning (FAISS) search, Arabic↔English glossary."], ["Clean", "Sentences that try to instruct the AI are removed."], ["Answer", "A local model, or a verified quote, with citations."], ["Check", "Citations must exist; every number must be in the sources."], ["Mask", "Emirates IDs, IBANs and personal numbers are hidden."]],
    how_html: () => `
<h2>Private by design, not by promise</h2>
<ul>
<li><b>No outside services.</b> The search index, the masking and the answer model all run inside this server. After start-up a network guard refuses every outbound connection, and the counter on the Ask page shows any attempt.</li>
<li><b>Permission-aware search.</b> Documents the role may not read are excluded inside the search itself, so they can never be quoted, cited or hinted at.</li>
<li><b>Personal data masking.</b> Emirates ID, IBAN, card and passport numbers are always hidden; personal phone numbers only appear for IT and executives, and only from operational runbooks.</li>
<li><b>Prompt-injection guard.</b> Text inside documents is treated as data. Sentences that try to give the AI instructions are removed and flagged.</li>
<li><b>Grounded answers.</b> Every answer cites its sources. A model answer whose numbers are not in the cited text is replaced by the verified quote. If the documents do not contain the answer, Khazna says so.</li>
<li><b>Version awareness.</b> Superseded documents rank below the current version and are labelled.</li>
<li><b>Temporary uploads.</b> Your files stay in memory for your session only and are deleted after 30 minutes.</li>
<li><b>Audit trail.</b> Every question is logged with the role, the documents used, and what was hidden.</li>
</ul>
<h2>Running it inside a company</h2>
<p>The same code runs on a company server with Docker. Point it at a larger model served by Ollama on the same machine (for example Qwen2.5 7B, which handles Arabic well) and load the company's own documents with their access labels.</p>
<h2>Limits</h2>
<ul>
<li>The demo library is small (21 documents), so search is easy; larger libraries need the multilingual embedding model option.</li>
<li>Without a model, answers are quotes, so very differently worded questions can miss. The model mode handles those.</li>
<li>Scanned PDFs need OCR, which is not included.</li>
</ul>`,
    lede_br: "Khazna answers questions about confidential documents in English or Arabic, with the exact source for every answer. It only reads what your role is allowed to see, hides personal data and ignores instructions planted inside documents. In this live demo the whole engine runs inside your browser, so nothing you type or upload leaves your device.",
    b_local_br: "Answered in your browser", rail_net_br: "Requests to other servers since loading", rail_guard_on_br: "Running in your browser",
    rail_where_br: (m) => `Model: ${m || "built-in quoting (no model)"}. The Python engine runs inside this page (Pyodide); questions and files are never sent anywhere.`,
    up_lede_br: (t, m) => `Upload a PDF, Word or text file (up to ${m} MB) and ask questions about it. It is read inside your browser and never uploaded anywhere; it is forgotten after ${t} minutes or when you close the tab.`,
    how_br: "<h2>How this live demo runs</h2><p>To keep the demo free and private, the same Python engine (search, masking, guards and checks) runs inside your browser with Pyodide. In a company it runs as a server with Docker, optionally with a local model (Qwen2.5 via Hugging Face transformers or Ollama); that mode is scored by a separate CI job.</p>",
    toast_err: "Something went wrong. Try again.", rate: "Too many requests. Wait a minute.", err_upload: "Upload failed",
  };

  const AR = {
    skip: "انتقل إلى المحتوى", menu: "القائمة", loading: "جارٍ فتح الخزنة…", viewing_as: "الدور",
    nav_ask: "اسأل", nav_library: "المكتبة", nav_upload: "ملفاتك", nav_evidence: "الدليل", nav_how: "كيف تعمل",
    foot_data: "شركة سديم للشحن وجميع المستندات والأشخاص والأرقام هنا افتراضية، أُعدّت لهذا العرض.",
    foot_by: "من إعداد عائشة لبنى.", foot_code: "الشيفرة المصدرية على GitHub", other_lang: "English",
    title: "اسأل مستندات شركتك. لا شيء يغادر الخزنة.",
    lede: "تجيب «خزنة» عن الأسئلة حول المستندات السرية بالعربية أو الإنجليزية، مع ذكر المصدر الدقيق لكل إجابة. ولا تقرأ إلا ما يسمح به دورك، وتُخفي البيانات الشخصية، وتتجاهل التعليمات المدسوسة داخل المستندات، وتعمل بالكامل على هذا الخادم.",
    specimen_title: "سجل رواتب (مثال)", specimen_stamp: "مقيّد",
    specimen_l1: "الموظفة: فاطمة الحمادي، أخصائية الدرجة G4.", specimen_l2: "رقم الهوية الإماراتية", specimen_l3: "رقم الآيبان لحساب الراتب", specimen_l4: "الهاتف المتحرك",
    ask_ph: "اكتب سؤالك، مثلًا: كم مدة إجازة الأمومة؟", ask_btn: "اسأل",
    viewing: (r, n) => `أنت تسأل بصفة <b>${r}</b>، ويمكنك قراءة <b>${n}</b> من مستندات الشركة. غيّر الدور في الأعلى لترى كيف تتغير الإجابات.`,
    try: "جرّب:", tag: { restricted: "مقيّد", pii: "بيانات شخصية", injection: "تعليمات مدسوسة", off: "غير موجود", ar: "عربي", cross: "بين اللغتين", version: "توجد نسخة قديمة" },
    your_q: "سؤالك", thinking: "جارٍ البحث في المستندات المتاحة لك…", writing: "جارٍ كتابة الإجابة داخل هذا الخادم…",
    sources_h: "المصادر", open_doc: "افتح المستند", cited: "مستخدم في الإجابة", superseded: "نسخة قديمة",
    b_cited: (n) => `الإجابة مدعومة بـ ${n} ${n > 1 ? "مصادر" : "مصدر"}`, b_refused: "غير موجود في المستندات المتاحة لك",
    b_masked: (n) => `أُخفيت ${n} من البيانات الشخصية`, b_inj: (n) => `تم تجاهل ${n} من التعليمات المدسوسة`,
    b_local: "أُجيب على هذا الخادم", b_quote: "اقتباس من المصدر", b_model: (m) => `كتبها ${m} على هذا الخادم`,
    b_fallback: "إجابة النموذج لم تجتز التحقق: نعرض الاقتباس المتحقق منه", b_old: "توجد نسخة أقدم أيضًا",
    removed_note: (n) => `أُزيلت ${n} من الجمل التي حاولت توجيه الذكاء الاصطناعي من هذا المقطع`,
    rail_h: "سجل الخصوصية", rail_q: "الأسئلة في هذه الجلسة", rail_mask: "بيانات شخصية مخفية", rail_inj: "تعليمات مدسوسة تم تجاهلها",
    rail_net: "محاولات اتصال خارجي محجوبة", rail_where: (m) => `النموذج: ${m || "الاقتباس المدمج (بدون نموذج)"}. كل شيء يعمل داخل هذا الخادم، وحارس الشبكة يمنع أي اتصال بالخارج.`,
    rail_guard_on: "حارس الشبكة مفعّل", rail_guard_off: "حارس الشبكة متوقف",
    lib_h: "المكتبة", lib_lede: (r, n, t) => `${t} مستندًا. بصفة <b>${r}</b> يمكنك قراءة <b>${n}</b>. لا يُبحث في المستندات المقفلة لدورك إطلاقًا، فلا يمكن أن تظهر في أي إجابة.`,
    th_doc: "المستند", th_cls: "التصنيف", th_owner: "الجهة المالكة", th_access: "صلاحيتك", th_pii: "بيانات شخصية بداخله",
    can: "يمكنك القراءة", cannot: "مقفل", read: "اقرأ", none_pii: "لا يوجد", old: "قديم",
    pii_kind: { emirates_id: "هوية إماراتية", iban: "آيبان", phone: "هاتف", email: "بريد إلكتروني", card: "بطاقة", passport: "جواز سفر" },
    doc_masked: (n) => `أُخفيت ${n} من البيانات الشخصية في هذا العرض.`,
    doc_old: "تم استبدال هذه النسخة. تضعها «خزنة» بعد النسخة الحالية في الترتيب.",
    inj_h: "تم رصد تعليمات مدسوسة", inj_p: "يحاول هذا النص توجيه الذكاء الاصطناعي. تُزيله «خزنة» قبل الإجابة ولا تنفّذه أبدًا.",
    close: "إغلاق",
    up_h: "ملفاتك", up_lede: (t, m) => `ارفع ملف PDF أو Word أو نصًا (حتى ${m} ميغابايت) واسأل عنه. يُعالج في ذاكرة هذا الخادم، ولا يُشارك مع أي زائر آخر، ويُحذف تلقائيًا بعد ${t} دقيقة.`,
    drop: "اسحب ملفًا إلى هنا أو انقر للاختيار", drop2: "PDF أو DOCX أو TXT أو MD",
    up_ok: (n, w) => `تمت إضافة ${n} (${w} كلمة). اسأل عنه في صفحة «اسأل».`, up_pii: (s) => `بيانات شخصية وُجدت وأُخفيت: ${s}.`,
    up_del: "احذف الآن", up_expires: (m) => `يُحذف تلقائيًا خلال ${m} دقيقة`, up_none: "لا توجد ملفات بعد.",
    up_ask: "اسأل عنه", deleted: "تم الحذف.",
    scan_h: "جرّب إخفاء البيانات الشخصية", scan_p: "الصق أي نص يحتوي على أرقام هواتف إماراتية أو أرقام هوية أو آيبان. لا يُحفظ شيء.",
    scan_ph: "مثال: اتصل بأحمد على 050 123 4567. الآيبان AE07 0331 2345 6789 0123 456.", scan_btn: "أخفِ البيانات",
    ev_h: "الدليل", ev_lede: (n) => `${n} سؤالًا اختباريًا بإجابات معروفة، تُشغّل تلقائيًا مع كل تعديل على الشيفرة. أي تسريب يُفشل البناء.`,
    ev_f1: "إجابات صحيحة", ev_f2: "أسئلة بين العربية والإنجليزية صحيحة", ev_f3: "أسئلة خارج المستندات رُفضت", ev_f4: "تسريبات في كل الفحوص",
    ev_leaks: "فحوص التسريب", ev_leaks_p: (n) => `يُفحص ${n} نصًا محظورًا في كل إجابة وكل مقطع معروض.`,
    lk: { restricted: "مستندات مقيّدة (سلالم الرواتب، محاضر المجلس، العقد)", pii: "معرّفات شخصية (الهوية، الآيبان، الهاتف الشخصي)", injection: "تعليمات مدسوسة («تجاهل كل التعليمات السابقة…»)", superseded: "قيم من دليل 2024 القديم" },
    ev_ans: "جودة الإجابات", ev_ret: "العثور على المقطع الصحيح",
    m: { acc: "إجابات صحيحة", en: "حقائق بالإنجليزية", ar: "حقائق بالعربية", cross: "بين العربية والإنجليزية", ver: "تفضيل النسخة الحالية", unans: "رفض الأسئلة غير الموجودة", restr: "رفض الأسئلة المقيّدة", p50: "الوقت الوسيط" },
    mode_builtin: "مدمج (بدون نموذج)", mode_llm: (m) => `نموذج محلي (${m})`,
    ret_cols: ["الطريقة", "النتيجة الأولى صحيحة", "ضمن أول 5", "MRR"],
    ev_note: "الأسئلة عن مستندات مقفلة التي لم تُرفض أُجيبت من المستندات المسموح بها فقط، وتؤكد فحوص التسريب أنه لم يُعرض أي شيء مقيّد.",
    how_h: "كيف تعمل",
    flow: [["من يسأل", "الدور يحدد المستندات التي يمكن البحث فيها."], ["البحث", "بحث بالكلمات (BM25) وبالمعنى (FAISS) مع مسرد عربي-إنجليزي."], ["التنظيف", "تُزال الجمل التي تحاول توجيه الذكاء الاصطناعي."], ["الإجابة", "نموذج محلي أو اقتباس متحقق منه، مع المصادر."], ["التحقق", "يجب أن تكون المصادر موجودة وكل رقم وارد فيها."], ["الإخفاء", "تُخفى أرقام الهوية والآيبان والأرقام الشخصية."]],
    how_html: () => `
<h2>الخصوصية بالتصميم لا بالوعود</h2>
<ul>
<li><b>لا خدمات خارجية.</b> فهرس البحث والإخفاء ونموذج الإجابة تعمل كلها داخل هذا الخادم. وبعد التشغيل يرفض حارس الشبكة أي اتصال خارجي، ويُظهر العدّاد في صفحة «اسأل» أي محاولة.</li>
<li><b>بحث يحترم الصلاحيات.</b> تُستبعد المستندات غير المسموح بها داخل البحث نفسه، فلا يمكن اقتباسها أو الإشارة إليها.</li>
<li><b>إخفاء البيانات الشخصية.</b> أرقام الهوية والآيبان والبطاقات وجوازات السفر مخفية دائمًا، ولا تظهر أرقام الهواتف الشخصية إلا لفريق التقنية والإدارة التنفيذية ومن أدلة التشغيل فقط.</li>
<li><b>حماية من التعليمات المدسوسة.</b> يُعامل نص المستندات كبيانات، وتُزال الجمل التي تحاول توجيه الذكاء الاصطناعي ويُشار إليها.</li>
<li><b>إجابات موثّقة.</b> كل إجابة تذكر مصادرها، وأي إجابة من النموذج تحتوي أرقامًا غير موجودة في المصدر تُستبدل بالاقتباس المتحقق منه. وإذا لم تكن الإجابة في المستندات تقول «خزنة» ذلك.</li>
<li><b>مراعاة الإصدارات.</b> المستندات الملغاة تأتي بعد النسخة الحالية وتُوسم بذلك.</li>
<li><b>رفع مؤقت.</b> تبقى ملفاتك في الذاكرة لجلستك فقط وتُحذف بعد 30 دقيقة.</li>
<li><b>سجل تدقيق.</b> يُسجَّل كل سؤال مع الدور والمستندات المستخدمة وما أُخفي.</li>
</ul>
<h2>التشغيل داخل الشركة</h2>
<p>تعمل الشيفرة نفسها على خادم الشركة باستخدام Docker، مع نموذج أكبر عبر Ollama على الجهاز نفسه (مثل Qwen2.5 7B الجيد في العربية)، وتحميل مستندات الشركة مع تصنيفات الوصول الخاصة بها.</p>
<h2>الحدود</h2>
<ul>
<li>مكتبة العرض صغيرة (21 مستندًا)، والمكتبات الأكبر تحتاج خيار نموذج التضمين متعدد اللغات.</li>
<li>بدون نموذج تكون الإجابات اقتباسات، فقد تفوتها الأسئلة المصاغة بشكل مختلف كثيرًا، ويعالج وضع النموذج ذلك.</li>
<li>ملفات PDF الممسوحة ضوئيًا تحتاج إلى تقنية التعرف الضوئي، وهي غير مضمّنة.</li>
</ul>`,
    lede_br: "تجيب «خزنة» عن الأسئلة حول المستندات السرية بالعربية أو الإنجليزية، مع ذكر المصدر الدقيق لكل إجابة. ولا تقرأ إلا ما يسمح به دورك، وتُخفي البيانات الشخصية، وتتجاهل التعليمات المدسوسة داخل المستندات. في هذا العرض المباشر يعمل المحرك بالكامل داخل متصفحك، فلا يغادر جهازك أي شيء تكتبه أو ترفعه.",
    b_local_br: "أُجيب داخل متصفحك", rail_net_br: "طلبات إلى خوادم أخرى منذ التحميل", rail_guard_on_br: "يعمل داخل متصفحك",
    rail_where_br: (m) => `النموذج: ${m || "الاقتباس المدمج (بدون نموذج)"}. يعمل محرك بايثون داخل هذه الصفحة (Pyodide)، ولا تُرسل الأسئلة أو الملفات إلى أي جهة.`,
    up_lede_br: (t, m) => `ارفع ملف PDF أو Word أو نصًا (حتى ${m} ميغابايت) واسأل عنه. يُقرأ داخل متصفحك ولا يُرفع إلى أي مكان، ويُنسى بعد ${t} دقيقة أو عند إغلاق الصفحة.`,
    how_br: "<h2>كيف يعمل هذا العرض المباشر</h2><p>ليبقى العرض مجانيًا وخاصًا، يعمل محرك بايثون نفسه (البحث والإخفاء والحماية والتحقق) داخل متصفحك باستخدام Pyodide. وفي الشركة يعمل كخادم باستخدام Docker، مع نموذج محلي اختياري (Qwen2.5 عبر transformers أو Ollama)، ويُقيَّم هذا الوضع في مهمة CI منفصلة.</p>",
    toast_err: "حدث خطأ. حاول مرة أخرى.", rate: "طلبات كثيرة. انتظر دقيقة.", err_upload: "تعذر الرفع",
  };
  window.KH_I18N = { en: EN, ar: AR };
})();
