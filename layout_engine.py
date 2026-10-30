
"""Local keyboard-layout recovery using lexical and corpus bigram evidence."""
from __future__ import annotations
import math, re, sys
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
try:
    from wordfreq import zipf_frequency
except ImportError:
    zipf_frequency = None

EN = chr(96) + "qwertyuiop[]asdfghjkl;'zxcvbnm,./"
RU = "ёйцукенгшщзхъфывапролджэячсмитьбю."
UA = chr(96) + "йцукенгшщзхїфівапролджєячсмитьбю."
MAPS = {
 ("en","ru"): dict(zip(EN,RU)), ("ru","en"): {v:k for k,v in dict(zip(EN,RU)).items()},
 ("en","ua"): dict(zip(EN,UA)), ("ua","en"): {v:k for k,v in dict(zip(EN,UA)).items()},
}
MAPS[("ru","ua")] = {c: MAPS[("en","ua")].get(MAPS[("ru","en")].get(c,c),c) for c in RU}
MAPS[("ua","ru")] = {c: MAPS[("en","ru")].get(MAPS[("ua","en")].get(c,c),c) for c in UA}
LANG_CODE = {"en":"en","ru":"ru","ua":"uk"}
MODEL_FILES = {"en":"en_bigrams_50k.txt","ru":"ru_bigrams_50k.txt","ua":"uk_bigrams_50k.txt"}
WORD_RE = re.compile(r"^[A-Za-zА-Яа-яЁёІіЇїЄєҐґ,]+$")

def convert(word, src, dst):
    m = MAPS.get((src,dst), {})
    return "".join(m.get(c.lower(),c).upper() if c.isupper() else m.get(c,c) for c in word)

def script_of(word):
    latin = any("a" <= c.lower() <= "z" for c in word)
    cyr = any(("а" <= c.lower() <= "я") or c.lower() in "ёіїєґ" for c in word)
    if latin and cyr: return "mixed"
    if latin: return "en"
    if cyr: return "cyr"
    return "other"

class BigramModel:
    def __init__(self, path):
        self.counts = {}
        self.outgoing = defaultdict(int)
        if path.exists():
            with path.open(encoding="utf-8") as stream:
                for line in stream:
                    p = line.rstrip("\n").split("\t")
                    if len(p) != 3: continue
                    try: n = int(p[2])
                    except ValueError: continue
                    if n > 0:
                        self.counts[(p[0],p[1])] = n
                        self.outgoing[p[0]] += n
    def pair_strength(self, left, right):
        n = self.counts.get((left,right),0)
        if not n: return 0.0
        return max(-2.0,min(3.0,math.log10(n/max(1,self.outgoing[left]))+2.0))

class LayoutEngine:
    def __init__(self, model_dir=None):
        self.model_dir = Path(model_dir) if model_dir else Path(__file__).resolve().parent/"models"
        self.models = {lang:BigramModel(self.model_dir/name) for lang,name in MODEL_FILES.items()}

    @staticmethod
    @lru_cache(maxsize=50000)
    def word_score(word, lang):
        if zipf_frequency is None: return 0.0
        try: return float(zipf_frequency(word.lower(),LANG_CODE[lang]))
        except Exception: return 0.0

    def phrase_score(self, words, lang, custom_words=None):
        if not words: return 0.0
        lexical=[]
        for word in words:
            score=self.word_score(word,lang)
            if custom_words and word.lower() in custom_words.get(lang,set()):
                score=max(score,3.0)
            lexical.append(score)
        if sum(x>=1.5 for x in lexical) < max(1,math.ceil(len(words)*0.6)):
            return -100.0
        model=self.models.get(lang)
        context=0.0
        if model:
            context=sum(model.pair_strength(a.lower(),b.lower()) for a,b in zip(words,words[1:]))
        return sum(lexical)+0.65*context

    def candidate_words(self, raw_words, lang):
        out=[]
        for raw in raw_words:
            script=script_of(raw)
            if script in ("mixed","other"): return None
            if script==lang: candidate=raw.lower()
            elif script=="en" and lang in ("ru","ua"): candidate=convert(raw,"en",lang).lower()
            elif script=="cyr" and lang=="en":
                a=convert(raw,"ru","en").lower(); b=convert(raw,"ua","en").lower()
                candidate=max((a,b),key=lambda w:self.word_score(w,"en"))
            elif script=="cyr" and lang in ("ru","ua"): candidate=raw.lower()
            else: return None
            if not candidate or not candidate.replace(",","").isalpha(): return None
            out.append(candidate)
        return out

    def suggest_phrase(self, phrase, custom_words=None):
        raw=phrase.strip().split()
        if not raw or any(not WORD_RE.match(w) for w in raw): return None
        if len(raw)==1 and len(raw[0])<3: return None
        scripts={script_of(w) for w in raw}
        if len(scripts)!=1 or scripts & {"mixed","other"}: return None
        source=next(iter(scripts))
        baselines=("en",) if source=="en" else ("ru","ua")
        baseline=max(self.phrase_score([w.lower() for w in raw],l,custom_words) for l in baselines)
        ranked=[]
        for lang in ("en","ru","ua"):
            if source=="en" and lang=="en": continue
            if source=="cyr" and lang in ("ru","ua"): continue
            words=self.candidate_words(raw,lang)
            if words: ranked.append((self.phrase_score(words,lang,custom_words),lang,words))
        if not ranked: return None
        score,lang,words=max(ranked,key=lambda x:x[0])
        improvement=score-baseline
        required=1.35 if len(raw)>=2 else 1.8
        if score < 2.2*len(raw) or improvement < required: return None
        corrected_words=[]
        for raw_word, candidate_word in zip(raw, words):
            if raw_word.isupper(): candidate_word=candidate_word.upper()
            elif raw_word[:1].isupper(): candidate_word=candidate_word.capitalize()
            corrected_words.append(candidate_word)
        corrected=" ".join(corrected_words)
        if corrected.lower()==phrase.lower(): return None
        return corrected,lang,score,baseline

_DEFAULT_ENGINE=None
def get_engine(model_dir=None):
    global _DEFAULT_ENGINE
    if model_dir is not None: return LayoutEngine(model_dir)
    if _DEFAULT_ENGINE is None:
        root=Path(getattr(sys,"_MEIPASS",Path(__file__).resolve().parent))
        _DEFAULT_ENGINE=LayoutEngine(root/"models")
    return _DEFAULT_ENGINE

def suggest_correction(word,custom_words=None,context=None):
    phrase=" ".join((context or [])[-4:]+[word])
    result=get_engine().suggest_phrase(phrase,custom_words)
    if not result: return None
    corrected,lang,score,baseline=result
    return corrected.split()[-1],lang,score,baseline
