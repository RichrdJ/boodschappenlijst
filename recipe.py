"""
Ingrediënten uit een receptpagina halen.
Bijna elke receptsite (Allerhande, Leukerecepten, 24Kitchen, Jumbo, WordPress-blogs) zet het
recept als schema.org/Recipe in de pagina, voor Google. Dat lezen we uit; lukt dat niet, dan
zoeken we naar elementen met itemprop="recipeIngredient".
"""
import html
import ipaddress
import json
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

MAX_BYTES = 4_000_000
TIMEOUT = 12
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")

# meestal al in huis: wel tonen, maar standaard niet aangevinkt
PANTRY = {"zout", "peper", "zwarte peper", "zout en peper", "peper en zout", "water", "ijsblokjes",
          "kokend water", "lauw water", "warm water", "koud water", "versgemalen zwarte peper"}


class RecipeError(Exception):
    pass


# ---------- veilig ophalen ----------

def _check_host(host):
    """Alleen openbare adressen: de app draait vaak thuis, en mag niet de router of NAS gaan bevragen."""
    if not host:
        raise RecipeError("Dat lijkt geen geldige link.")
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise RecipeError("Die website kon ik niet vinden. Klopt de link?")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if not ip.is_global:
            raise RecipeError("Alleen openbare websites kunnen worden opgehaald.")


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parts = urllib.parse.urlsplit(newurl)
        if parts.scheme not in ("http", "https"):
            raise RecipeError("De website stuurde door naar een ongeldige link.")
        _check_host(parts.hostname)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_opener = urllib.request.build_opener(_SafeRedirect)


def clean_url(url):
    url = (url or "").strip()
    m = re.search(r"https?://\S+", url)  # ook als er tekst omheen staat, zoals bij delen vanuit een app
    url = m.group(0) if m else url
    if not re.match(r"^[a-z][a-z0-9+.-]*://", url, re.I):
        url = "https://" + url
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname or "." not in parts.hostname:
        raise RecipeError("Dat lijkt geen geldige link.")
    return url


def fetch(url):
    _check_host(urllib.parse.urlsplit(url).hostname)
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.6",
    })
    try:
        with _opener.open(req, timeout=TIMEOUT) as res:
            raw = res.read(MAX_BYTES)
            charset = res.headers.get_content_charset() or "utf-8"
    except RecipeError:
        raise
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 429):
            raise RecipeError("Deze website laat zich niet automatisch uitlezen. Kopieer de ingrediënten van de pagina en plak ze hieronder.")
        if e.code == 404:
            raise RecipeError("Die pagina bestaat niet (meer).")
        raise RecipeError(f"De website gaf een fout ({e.code}).")
    except (urllib.error.URLError, TimeoutError, OSError):
        raise RecipeError("De website reageerde niet. Probeer het later opnieuw.")
    try:
        return raw.decode(charset, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


# ---------- recept vinden in de pagina ----------

class _Scanner(HTMLParser):
    """Verzamelt JSON-LD-blokken, de paginatitel en de tekst van itemprop=recipeIngredient."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.jsonld, self.ingredients, self.title = [], [], ""
        self._ld = None
        self._in_title = False
        self._ing_depth = 0      # >0 terwijl we binnen een ingrediënt-element zitten
        self._ing_text = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "script" and "ld+json" in (a.get("type") or "").lower():
            self._ld = []
        elif tag == "title" and not self.title:
            self._in_title = True
        if self._ing_depth:
            if tag not in ("br", "img", "input", "meta", "link", "source", "wbr", "hr"):
                self._ing_depth += 1
        elif (a.get("itemprop") or "").lower() in ("recipeingredient", "ingredients"):
            if tag == "meta" and a.get("content"):
                self.ingredients.append(a["content"])
            elif tag not in ("meta", "link"):
                self._ing_depth, self._ing_text = 1, []

    def handle_endtag(self, tag):
        if tag == "script" and self._ld is not None:
            self.jsonld.append("".join(self._ld))
            self._ld = None
        elif tag == "title":
            self._in_title = False
        if self._ing_depth:
            self._ing_depth -= 1
            if not self._ing_depth:
                self.ingredients.append(" ".join("".join(self._ing_text).split()))

    def handle_data(self, data):
        if self._ld is not None:
            self._ld.append(data)
        elif self._in_title:
            self.title += data
        if self._ing_depth:
            self._ing_text.append(data)


def _types(node):
    t = node.get("@type", "")
    return {str(x).lower() for x in (t if isinstance(t, list) else [t])}


def _find_recipe(node):
    if isinstance(node, list):
        for x in node:
            found = _find_recipe(x)
            if found:
                return found
    elif isinstance(node, dict):
        if "recipe" in _types(node) and (node.get("recipeIngredient") or node.get("ingredients")):
            return node
        for key in ("@graph", "mainEntity", "mainEntityOfPage", "itemListElement", "item"):
            if key in node:
                found = _find_recipe(node[key])
                if found:
                    return found
    return None


def _load_json(text):
    text = text.strip().removeprefix("<!--").removesuffix("-->").strip()
    try:
        return json.loads(text, strict=False)
    except ValueError:
        # sommige sites zetten er een losse komma of puntkomma achter
        try:
            return json.loads(re.sub(r"[;,\s]+$", "", text), strict=False)
        except ValueError:
            return None


def _text(value):
    if isinstance(value, dict):
        value = value.get("text") or value.get("name") or ""
    value = html.unescape(html.unescape(str(value)))
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(value.split())


def extract(page):
    """Geeft (titel, [ingrediëntregels]) terug."""
    s = _Scanner()
    try:
        s.feed(page)
        s.close()
    except Exception:
        pass
    for block in s.jsonld:
        recipe = _find_recipe(_load_json(block))
        if recipe:
            lines = recipe.get("recipeIngredient") or recipe.get("ingredients") or []
            if isinstance(lines, str):
                lines = re.split(r"\n|<br\s*/?>", lines)
            lines = [_text(x) for x in lines if _text(x)]
            if lines:
                return _text(recipe.get("name") or s.title), lines
    lines = [x for x in (_text(i) for i in s.ingredients) if x]
    return _text(s.title), lines


# ---------- van "2 tenen knoflook, fijngehakt" naar "knoflook" ----------

_NUM = r"(?:\d+(?:[.,/]\d+)?|[½⅓⅔¼¾⅛⅜⅝⅞])"
_QTY = re.compile(
    rf"^(?:ca\.?|circa|ongeveer|±|~)?\s*(?:{_NUM}\s*)+(?:(?:-|–|tot|à|a|of)\s*(?:{_NUM}\s*)+)?", re.I)
_WORD_QTY = re.compile(r"^(?:een|één|twee|drie|vier|vijf|zes|zeven|acht|negen|tien|twaalf|"
                       r"half|halve|paar|enkele|wat|beetje|flink|flinke|klein|kleine|groot|grote|"
                       r"middelgroot|middelgrote|ruim|ruime|royaal|royale)\b\s*", re.I)
_UNITS = ("gram|gr|g|kilogram|kilo|kg|milligram|mg|milliliter|ml|centiliter|cl|deciliter|dl|liter|ltr|l|"
          "eetlepels?|el|eetl|theelepels?|tl|thl|koffielepels?|kl|dessertlepels?|lepels?|"
          "kopjes?|kop|bekers?|bekertjes?|glas|glazen|glaasjes?|mokken|mok|"
          "stuks?|st|stk|teentjes?|tenen|teen|bollen|bol|bolletjes?|"
          "blikken|blikjes?|blik|pakken|pakjes?|pak|zakken|zakjes?|zak|potten|potjes?|pot|"
          "flessen|flesjes?|fles|bakjes?|bak|doosjes?|doos|tubes?|netjes?|net|kuipjes?|"
          "bossen|bosjes?|bos|takken|takjes?|tak|stengels?|stelen|steeltjes?|"
          "plakken|plakjes?|plak|schijven|schijfjes?|schijf|sneden|sneetjes?|snee|"
          "blaadjes|blaadje|bladeren|blad|vellen|velletjes?|vel|"
          "repen|reepjes?|reep|stukken|stukjes?|stuk|partjes?|part|"
          "handjes?|handvol|hand|snufjes?|snuf|snufje|scheutjes?|scheut|"
          "druppels?|drupjes?|toefjes?|toef|klontjes?|klont|klodders?|klodder|"
          "porties|portie|personen|cups?|tbsp|tsp|tablespoons?|teaspoons?|oz|ounces?|lbs?|pounds?|"
          "pinch|dash|cloves?|cans?|slices?")
_UNIT = re.compile(rf"^(?:{_UNITS})\.?(?=\s|$)\s*(?:(?:à|a|van)\s+(?:{_NUM}\s*)+(?:{_UNITS})?\.?\s+)?", re.I)
_LEAD = re.compile(r"^(?:x|×|van|de|het|of|à)\s+", re.I)
_TAIL = re.compile(r"\s+(?:naar smaak|naar keuze|optioneel|eventueel|voor erbij|om te serveren|"
                   r"om in te bakken|om mee te bakken|voor het bakken|om te garneren|ter garnering|"
                   r"voor de garnering|ingevroren|op kamertemperatuur|uitgelekt|zonder pit|"
                   r"(?:fijn|grof)?(?:gesneden|gehakt|gesnipperd|geraspt)|in (?:stukjes|blokjes|reepjes|"
                   r"ringen|plakjes|partjes|parten|halve ringen|dunne plakjes|stukken)(?:\s+gesneden)?)$", re.I)


def product_name(line):
    """Haalt hoeveelheid, eenheid en bereiding weg: '2 el olijfolie (extra vierge)' -> 'olijfolie'."""
    s = " ".join(line.split())
    s = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", s)            # (ca. 400 g), [optioneel]
    s = re.sub(r"^[-–•*·▢□☐]\s*", "", s)                     # opsommingstekens
    s = re.split(r",|;|\s[-–]\s|\s+\bvoor\s+de\s+\w+$", s)[0]  # ', fijngesneden' / ' - in blokjes'
    s = s.strip()
    for _ in range(4):  # "1 blik à 400 g tomaten", "2 el (30 ml) olie", "een paar takjes tijm"
        before = s
        s = _QTY.sub("", s).strip()
        s = _WORD_QTY.sub("", s).strip()
        s = _UNIT.sub("", s).strip()
        s = _LEAD.sub("", s).strip()
        if s == before:
            break
    for _ in range(3):
        s = _TAIL.sub("", s).strip()
    s = s.strip(" .:*-–").lower()
    return s or " ".join(line.split()).lower()


def ingredients_from_url(url):
    url = clean_url(url)
    title, lines = extract(fetch(url))
    if not lines:
        raise RecipeError("Op deze pagina vond ik geen ingrediënten. Is het wel een receptpagina?")
    return {"url": url, "title": title.strip(), "ingredients": _to_items(lines)}


def _to_items(lines):
    seen, result = set(), []
    for line in lines:
        name = product_name(line)
        if name in seen:
            continue
        seen.add(name)
        result.append({"line": line, "name": name, "pantry": name in PANTRY})
    return result


def ingredients_from_text(text):
    """Geplakte ingrediëntenlijst (één per regel), voor sites die zich niet laten uitlezen."""
    lines = [l.strip() for l in re.split(r"[\r\n]+", text or "") if l.strip()]
    lines = [l for l in lines if not re.fullmatch(r"(?i)ingredi[eë]nten:?|voor \d+ personen:?", l)]
    return {"url": "", "title": "", "ingredients": _to_items(lines)}
