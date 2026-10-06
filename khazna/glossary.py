"""Arabic <-> English workplace glossary for cross-lingual query expansion.

Built from the vocabulary of HR, finance, IT and legal documents (not from evaluation questions). Each entry maps
an Arabic term (normalised, unstemmed) to English words; the reverse map is derived automatically.
With a multilingual embedding model enabled (KHAZNA_EMBED=e5) cross-lingual matching also works without it.
"""
from __future__ import annotations

from .text import normalise_ar, stem_ar, stem_en, tokens

AR_EN = {
    # time and work
    "رمضان": "ramadan", "ساعات": "hours", "ساعة": "hour", "العمل": "working work", "عمل": "work working",
    "دوام": "working hours", "اسبوع": "week", "اسبوعيا": "weekly week", "يوم": "day", "يوما": "days", "ايام": "days",
    "شهر": "month", "شهريا": "monthly month", "سنة": "year", "سنويا": "yearly year annual", "سنوي": "annual",
    "المنزل": "home remote", "عن بعد": "remote", "بعد": "remote", "التجربة": "probation", "تجربة": "probation",
    "الاشعار": "notice", "اشعار": "notice", "استقالة": "resignation notice", "الجديد": "new", "جديد": "new",
    "الاب": "father paternity", "الام": "mother maternity", "موظف": "employee", "الموظف": "employee", "الموظفين": "employees", "مدير": "manager", "المدير": "manager",
    "مستودع": "warehouse", "المستودع": "warehouse", "سائق": "driver", "عطلة": "holiday", "العطلات": "holidays",
    "الرسمية": "public official", "عيد": "holiday eid", "مدة": "length period long",
    # leave
    "اجازة": "leave", "الاجازة": "leave", "اجازات": "leave", "الاجازات": "leave", "السنوية": "annual",
    "مرضية": "sick", "المرضية": "sick", "الامومة": "maternity", "امومة": "maternity", "الابوة": "paternity",
    "والدية": "paternity parental", "الحداد": "bereavement", "الحج": "hajj", "الدراسة": "study exam",
    "ترحيل": "carry over", "رصيد": "balance unused",
    # pay and benefits
    "راتب": "salary pay", "الراتب": "salary pay", "رواتب": "salary salaries", "الرواتب": "salary salaries",
    "سلم": "band", "درجة": "grade", "بدل": "allowance", "البدل": "allowance", "السكن": "housing", "سكن": "housing",
    "المواصلات": "transport", "مكافاة": "bonus", "حافز": "bonus incentive", "زيادة": "increase merit",
    "التامين": "insurance", "تامين": "insurance", "الطبي": "medical", "طبي": "medical", "تذكرة": "ticket air",
    "طيران": "air flight", "اللياقة": "wellness gym fitness", "البدنية": "wellness fitness", "رياضة": "gym",
    "التعليم": "education", "تعليم": "education", "الاطفال": "children child", "نهاية الخدمة": "end-of-service gratuity",
    "مكافاة نهاية": "gratuity", "تقاعد": "pension",
    # travel and expenses
    "السفر": "travel trip", "سفر": "travel trip", "رحلة": "trip travel", "فندق": "hotel", "الفندق": "hotel",
    "الحد": "limit", "الاقصي": "maximum limit", "سعر": "price limit rate", "يومي": "daily per diem allowance",
    "اليومي": "daily per diem allowance", "الخليج": "gcc", "دول الخليج": "gcc", "خارج": "outside", "داخل": "within",
    "مصروفات": "expense expenses", "المصروفات": "expense expenses", "مطالبة": "claim", "ايصال": "receipt",
    "فاتورة": "invoice receipt", "سيارة": "car", "كيلومتر": "kilometre", "مخالفات": "fines",
    "درجة رجال الاعمال": "business class", "رجال الاعمال": "business class", "حجز": "book booking",
    "دبي": "dubai", "ابوظبي": "abu dhabi", "الشارقة": "sharjah", "عجمان": "ajman",
    # IT and security
    "كلمة المرور": "password", "كلمة": "password", "المرور": "password traffic", "طول": "length long", "الادني": "minimum",
    "الحد الادني": "minimum", "حرفا": "characters", "التحقق": "authentication mfa", "حاسوب": "laptop computer",
    "الحاسوب": "laptop computer", "مفقود": "lost", "سرقة": "stolen", "التصيد": "phishing", "احتيالي": "phishing suspicious",
    "حادث": "incident", "حادثة": "incident", "الحوادث": "incidents", "امني": "security", "الامن": "security",
    "فدية": "ransomware ransom", "تصنيف": "classification", "البيانات": "data", "بيانات": "data",
    "سرية": "confidential", "مقيدة": "restricted", "الاتصال": "call contact", "رقم": "number",
    # data protection
    "حماية": "protection", "مسؤول": "officer", "الشخصية": "personal", "شخصية": "personal", "الاحتفاظ": "kept retention",
    "حذف": "deleted delete", "اختراق": "breach", "تسريب": "breach leak", "العملاء": "customer customers",
    "تخزين": "stored storage", "تخزن": "stored", "الامارات": "uae",
    # procurement, legal, finance
    "المشتريات": "procurement purchase", "شراء": "purchase", "عروض": "quotes", "عرض": "quote offer proposal",
    "اسعار": "quotes prices", "مناقصة": "tender", "لجنة": "committee", "المورد": "supplier", "مورد": "supplier",
    "الموردين": "suppliers", "هدية": "gift", "هدايا": "gifts", "الدفع": "payment", "شروط": "terms",
    "عقد": "contract agreement", "العقد": "contract agreement", "اتفاقية": "agreement", "انهاء": "terminate termination",
    "رسوم": "fee fees", "الرسوم": "fee fees", "المحاكم": "courts", "نزاع": "dispute", "الايرادات": "revenue",
    "ايرادات": "revenue", "ميزانية": "budget", "استحواذ": "acquire acquisition", "المدير المالي": "chief financial officer",
    "مجلس الادارة": "board",
}


# English synonyms common in policy documents (both directions are added)
EN_SYN = {
    "contract": "agreement", "length": "long characters", "minimum": "least", "maximum": "limit cap",
    "stick": "drive storage", "laptop": "device computer", "salary": "pay", "fee": "fees charge",
    "boss": "manager", "sack": "terminate", "fire": "terminate", "quit": "resign notice", "vacation": "leave",
    "holiday": "leave", "doctor": "medical", "illness": "sick", "receipt": "receipts", "reimburse": "reimbursed",
    "price": "cost rate", "fine": "fines", "lost": "stolen", "hack": "incident breach", "virus": "malware",
    "court": "courts disputes", "law": "governed", "bonus": "incentive", "allowance": "per diem", "trip": "travel",
    "carry": "carried", "night": "nightly", "attack": "incident ransomware", "father": "paternity",
    "mother": "maternity", "stop": "no", "alternative": "instead cash", "abroad": "outside",
}


def _build():
    ar2en: dict[str, set[str]] = {}
    en2ar: dict[str, set[str]] = {}
    for ar, en in AR_EN.items():
        ar_key = " ".join(stem_ar(w) for w in normalise_ar(ar).split())
        en_toks = [stem_en(w) for w in en.lower().split()]
        ar2en.setdefault(ar_key, set()).update(en_toks)
        for e in en_toks:
            en2ar.setdefault(e, set()).update(stem_ar(w) for w in normalise_ar(ar).split())
    for a, bs in EN_SYN.items():
        for b in bs.split():
            sa, sb = stem_en(a), stem_en(b)
            en2ar.setdefault(sa, set()).add(sb)
            en2ar.setdefault(sb, set()).add(sa)
    return ar2en, en2ar


AR2EN, EN2AR = _build()


def expand(query: str) -> list[str]:
    """Tokens of the query plus their translations (one hop, both directions)."""
    base = tokens(query)
    extra: list[str] = []
    joined = " ".join(base)
    for key, ens in AR2EN.items():
        if " " in key and key in joined:
            extra.extend(ens)
    for t in base:
        if t in AR2EN:
            extra.extend(AR2EN[t])
        if t in EN2AR:
            extra.extend(EN2AR[t])
    return base + [t for t in extra if t not in base]
