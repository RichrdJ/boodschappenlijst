"""
Productherkenning: verbetert tikfouten in productnamen ('komkomer' -> 'komkommer',
'advokado' -> 'avocado') door ze te vergelijken met bekende producten.

Bekende woorden komen uit de trefwoorden in categories.py, uit producten die je zelf aan
een categorie hebt gekoppeld, en uit woorden die je bewust hebt behouden ("Toch ...").
Er wordt alleen verbeterd als er precies één duidelijke kandidaat is; bij twijfel blijft
de naam zoals je hem typte.
"""
import re

# woorden die vaak in productnamen staan maar zelf geen product zijn: nooit "verbeteren"
MODIFIERS = {
    "rood", "rode", "wit", "witte", "groen", "groene", "geel", "gele", "zwart", "zwarte",
    "bruin", "bruine", "blauw", "blauwe", "vers", "verse", "halfvol", "halfvolle", "vol",
    "volle", "mager", "magere", "light", "zero", "bio", "biologisch", "biologische", "groot",
    "grote", "klein", "kleine", "jong", "jonge", "belegen", "oud", "oude", "extra", "zoet",
    "zoete", "zout", "zoute", "gezouten", "ongezouten", "gerookt", "gerookte", "gesneden",
    "geraspt", "geraspte", "gemalen", "heel", "hele", "half", "halve", "zak", "pak", "fles",
    "blik", "pot", "doos", "rol", "bos", "net", "stuk", "stuks", "voor", "met", "zonder",
    "van", "de", "het", "een", "en", "in", "of", "naturel", "original", "classic", "mini",
    "maxi", "multipack", "voordeel", "huismerk", "spa", "rood", "blauw", "plat", "bruis",
}

_WORD = re.compile(r"[a-zà-ÿ'-]+", re.I)


def _sound(w: str) -> str:
    """Grove 'klinkt als'-vorm voor Nederlandse tikfouten: c/k, v/f, z/s, ij/ei, dubbele letters."""
    w = w.replace("ph", "f").replace("ch", "g").replace("ck", "k").replace("ij", "ei").replace("y", "i")
    w = w.replace("dt", "t").replace("c", "k").replace("v", "f").replace("z", "s").replace("au", "ou")
    w = w.replace("q", "k").replace("x", "ks")
    return re.sub(r"(.)\1+", r"\1", w)


def _dist(a: str, b: str, limit: int) -> int:
    """Damerau-Levenshtein (omgewisselde letters tellen als één fout), stopt vroeg boven limit."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev2, prev = None, list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cost = a[i - 1] != b[j - 1]
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if prev2 and i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                cur[j] = min(cur[j], prev2[j - 2] + 1)
        if min(cur) > limit:
            return limit + 1
        prev2, prev = prev, cur
    return prev[-1]


def _limit(n: int) -> int:
    return 0 if n < 4 else 1 if n < 7 else 2


def _is_known(w: str, vocab: set) -> bool:
    if w in vocab or w in MODIFIERS or any(ch.isdigit() for ch in w):
        return True
    # meervoud of verkleinwoord van een bekend woord
    for suf in ("s", "'s", "en", "jes", "tjes", "je", "tje"):
        if w.endswith(suf) and w[: -len(suf)] in vocab:
            return True
    # samenstelling met een bekend woord: 'tomatenpuree', 'sinaasappelsap', 'kipfilets'
    return any(len(k) >= 4 and (w.startswith(k) or w.endswith(k)) for k in vocab)


def _correct_word(w: str, vocab: set, sounds: dict, max_limit: int = 2) -> str | None:
    """Beste kandidaat over alle meervoudsvormen ('komkomers' -> 'komkommers'); bij gelijkspel
    tussen verschillende woorden geen verbetering."""
    found = []  # (afstand, voorkeur, resultaat)
    for pref, suf in enumerate(("", "s", "en")):
        if suf and not w.endswith(suf):
            continue
        stem = w[: -len(suf)] if suf else w
        limit = min(_limit(len(stem)), max_limit)
        if not limit:
            continue
        s_stem = _sound(stem)
        best, best_d, tie = None, limit + 1, False
        for k in vocab:
            # korte woorden: eerste letter moet kloppen ('rood' is geen 'brood')
            if len(stem) <= 5 and k[0] != stem[0]:
                continue
            d = _dist(stem, k, limit)
            if len(stem) >= 6:  # 'klinkt als' alleen bij langere woorden ('mayo' is geen 'mais')
                d = min(d, _dist(s_stem, sounds[k], limit))
            if d < best_d:
                best, best_d, tie = k, d, False
            elif d == best_d and k != best:
                tie = True
        if best and not tie:
            found.append((best_d, -pref, best + suf))
    if not found:
        return None
    found.sort()  # kleinste afstand eerst; bij gelijke afstand de vorm die het meervoud bewaart
    return found[0][2]


def correct(name: str, vocab: set) -> str:
    """Geeft de verbeterde naam terug (of dezelfde naam als er niets te verbeteren is).
    Hoeveelheden, hoofdletter aan het begin en woorden die al kloppen blijven staan."""
    vocab = {v for v in vocab if v and " " not in v and len(v) >= 2}
    sounds = {v: _sound(v) for v in vocab}
    changed = False

    def fix(m):
        nonlocal changed
        orig = m.group(0)
        w = orig.lower()
        if w in vocab or w in MODIFIERS or any(ch.isdigit() for ch in w):
            return orig
        if _is_known(w, vocab):
            # lijkt een samenstelling ('tomatenpuree'); alleen een duidelijk bijna-identiek
            # lang woord verbeteren ('sinasappel' -> 'sinaasappel', 'bloemkol' -> 'bloemkool')
            if len(w) < 8:
                return orig
            new = _correct_word(w, vocab, sounds, max_limit=1)
        else:
            new = _correct_word(w, vocab, sounds)
        if not new or new == w:
            return orig
        changed = True
        return new.capitalize() if orig[:1].isupper() else new

    out = _WORD.sub(fix, name)
    return out if changed else name
