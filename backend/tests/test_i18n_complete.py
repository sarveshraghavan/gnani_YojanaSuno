from __future__ import annotations

import ast
import json
import re
from html.parser import HTMLParser
from pathlib import Path

from backend.app.dialogue.disclosure import AI_DISCLOSURES
from backend.app.dialogue.next_question import QUESTIONS

ROOT=Path(__file__).resolve().parents[2]
LANGS={"hi","ta","te","en"}
SCRIPT_RANGES={"hi":range(0x0900,0x0980),"ta":range(0x0B80,0x0C00),"te":range(0x0C00,0x0C80)}
ALLOWED_ENGLISH={"PM-KISAN","PMFBY","PM-KUSUM","WhatsApp","English","1551","1800 180 1551","1800-180-1551","Aadhaar","YojanaSuno","yojana","suno","yojanasuno","Gnani","Evon","Timbre","Ministry of Agriculture","& Farmers Welfare","NABARD","Krishi Vigyan Kendra (KVK)"}

class LanguageOptions(HTMLParser):
    def __init__(self): super().__init__();self.in_language=False;self.options={}
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=="select" and attrs.get("id")=="language":self.in_language=True
        if self.in_language and tag=="option":self.current=attrs.get("value","");self.options[self.current]=""
    def handle_data(self,data):
        if self.in_language and hasattr(self,"current"):self.options[self.current]+=data.strip()
    def handle_endtag(self,tag):
        if tag=="select" and self.in_language:self.in_language=False

def _has_native_script(text,lang):
    return any(ord(char) in SCRIPT_RANGES[lang] for char in text)

def _check_localized(text,lang):
    if lang=="en":return
    if text in ALLOWED_ENGLISH:return
    residue=text
    for token in ALLOWED_ENGLISH:residue=residue.replace(token,"")
    # Any remaining Latin word is an untranslated fragment; native script is mandatory too.
    assert not re.search(r"[A-Za-z]{3,}",residue), f"untranslated English in {lang}: {text}"
    if residue.strip() and not re.fullmatch(r"[\d\s.,·/+-]*",residue):
        assert _has_native_script(text,lang), f"missing native script in {lang}: {text}"


class LandingCoverage(HTMLParser):
    """Collect untranslated visible text and localization key references."""
    def __init__(self):
        super().__init__(convert_charrefs=True); self.stack=[]; self.uncovered=[]; self.references=set(); self.aria_without_key=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        for attr in ("data-i","data-ip","data-ia","data-im","data-ititle","data-prompt-key"):
            if a.get(attr): self.references.add(a[attr])
        if a.get("aria-label") and not a.get("data-ia"):
            self.aria_without_key.append((tag,a["aria-label"]))
        if tag not in {"meta","link","input","br","hr","img","source","area","wbr"}:
            self.stack.append((tag,tag in {"script","style"} or any(k in a for k in ("data-i","data-ip","data-ia","data-im","data-ititle","data-prompt-key")),a.get("aria-hidden")=="true"))
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag:
                del self.stack[i:]; break
    def handle_data(self,data):
        text=data.strip()
        if text and not any(marked or hidden for _,marked,hidden in self.stack): self.uncovered.append(text)


def landing_tables():
    html=(ROOT/"frontend/index.html").read_text(encoding="utf-8")
    embedded=re.search(r"window\.YS_I18N\s*=\s*\{(.*?)\n\};",html,re.S)
    source=embedded.group(1) if embedded else (ROOT/"frontend/i18n.js").read_text(encoding="utf-8")
    tables={}
    for lang in LANGS:
        match=re.search(rf"\b{lang}:\s*\{{(.*?)(?=\n  \}})",source,re.S)
        assert match, f"missing landing translation table: {lang}"
        tables[lang]=dict(re.findall(r"([A-Za-z_][A-Za-z0-9_]*):\s*\"([^\"]*)\"",match.group(1)))
    extra=re.search(r"const extraTranslations\s*=\s*\{(.*?)\n\};",html,re.S)
    if extra:
        for lang,body in re.findall(r"\b(hi|ta|te|en):\s*\{([^{}]*)\}",extra.group(1)):
            tables[lang].update(dict(re.findall(r"([A-Za-z_][A-Za-z0-9_]*):\s*\"([^\"]*)\"",body)))
    for lang,value in re.findall(r'extraTranslations\.(hi|ta|te|en)\.reply_title\s*=\s*"([^"]*)"',html):
        tables[lang]["reply_title"]=value
    return tables


def test_landing_page_visible_copy_is_keyed_and_complete_in_all_languages():
    html=(ROOT/"frontend/index.html").read_text(encoding="utf-8")
    assert "window.YS_I18N" in html or '<script src="/static/i18n.js"></script>' in html, "landing translation table is not loaded"
    parser=LandingCoverage(); parser.feed(html)
    tables=landing_tables()
    assert set(tables)==LANGS
    expected=set(tables["en"])
    assert all(set(table)==expected for table in tables.values()), "landing translation tables have different keys"
    missing=parser.references-expected
    assert not missing, f"HTML references missing translation keys: {sorted(missing)}"
    assert not parser.aria_without_key, f"aria-label is not localized: {parser.aria_without_key}"
    allowed_visible={"PM-KISAN","PMFBY","PM-KUSUM","YS","1800 180 1551"}
    uncovered=[text for text in parser.uncovered if text not in allowed_visible and not re.fullmatch(r"[0-9\s/—+·↘↗✳✓∿♫●↑]+",text)]
    assert not uncovered, f"visible HTML text is outside translation tables: {uncovered}"
    for lang in ("hi","ta","te"):
        for key,text in tables[lang].items():
            if key.startswith("language_"):
                residue=text
                for token in ALLOWED_ENGLISH: residue=residue.replace(token,"")
                assert not re.search(r"[A-Za-z]{3,}",residue), f"English language label in {lang}: {text}"
            else:
                _check_localized(text,lang)

def test_backend_string_tables_have_complete_language_keys_and_native_text():
    assert set(AI_DISCLOSURES)==LANGS
    assert set(QUESTIONS)
    for slot,translations in QUESTIONS.items():
        assert set(translations)==LANGS, f"question slot {slot} has incomplete translations"
        for lang,text in translations.items():_check_localized(text,lang)
    for lang,text in AI_DISCLOSURES.items():_check_localized(text,lang)
    catalog=json.loads((ROOT/"backend/app/dialogue/review_strings.json").read_text(encoding="utf-8"))
    for key in ("disclosures","fallbacks","privacy_warning","retry","scope","pm_kisan_next_steps"):
        assert set(catalog[key])==LANGS, f"{key} translation table has incomplete language keys"
        for lang,text in catalog[key].items():_check_localized(text,lang)
    assert set(catalog["questions"])==set(QUESTIONS)
    for slot,translations in catalog["questions"].items():
        assert set(translations)==LANGS

def test_confirmation_labels_are_key_complete_and_translated():
    source=(ROOT/"backend/app/main.py").read_text(encoding="utf-8")
    tree=ast.parse(source)
    fn=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=="confirmation_message")
    dictionaries=[]
    for node in ast.walk(fn):
        if not isinstance(node,ast.Assign) or not any(isinstance(t,ast.Name) and t.id=="labels" for t in node.targets):continue
        if isinstance(node.value,ast.Dict):
            mapping={ast.literal_eval(k):ast.literal_eval(v) for k,v in zip(node.value.keys,node.value.values)}
            dictionaries.append(mapping)
    assert len(dictionaries)==4
    expected=set(dictionaries[0])
    for mapping in dictionaries:
        assert set(mapping)==expected
    for lang,mapping in zip(("hi","ta","te","en"),dictionaries):
        for text in mapping.values():_check_localized(text,lang)

def test_compose_status_and_slot_names_are_complete_for_all_languages():
    source=(ROOT/"backend/app/main.py").read_text(encoding="utf-8")
    tree=ast.parse(source)
    fn=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=="compose")
    for variable in ("labels","field_names"):
        dictionaries=[]
        for node in ast.walk(fn):
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id==variable for t in node.targets) and isinstance(node.value,ast.Dict):
                dictionaries.append({ast.literal_eval(k):ast.literal_eval(v) for k,v in zip(node.value.keys,node.value.values)})
        assert len(dictionaries)==4, f"expected four language maps for {variable}"
        keys=set(dictionaries[0])
        assert all(set(mapping)==keys for mapping in dictionaries), f"{variable} keys differ between languages"
        for lang,mapping in zip(("hi","ta","te","en"),dictionaries):
            for text in mapping.values():_check_localized(text,lang)

def test_html_language_picker_lists_all_supported_languages():
    parser=LanguageOptions();parser.feed((ROOT/"frontend/index.html").read_text(encoding="utf-8"))
    assert set(parser.options)=={"hi-IN","ta-IN","te-IN","en-IN"}
    assert "हिन्दी" in parser.options["hi-IN"]
    assert "தமிழ்" in parser.options["ta-IN"]
    assert "తెలుగు" in parser.options["te-IN"]
    assert "English" in parser.options["en-IN"]

