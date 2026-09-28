"""
Categorieën in looproute-volgorde. Pas de volgorde aan door de lijst te herschikken.
Voeg gerust trefwoorden toe; alles in kleine letters.
"""
import re

CATEGORIES = [
    ("kruiden", "Kruiden", [
        "basilicum", "peterselie", "koriander", "bieslook", "dille", "munt", "rozemarijn",
        "tijm", "oregano", "salie", "dragon", "kruiden", "kruid", "gember", "citroengras",
        "kerrie", "paprikapoeder", "komijn", "kaneel", "nootmuskaat", "peper", "zout",
    ]),
    ("groente_fruit", "Groente & fruit", [
        "appel", "appels", "peer", "peren", "banaan", "bananen", "sinaasappel", "mandarijn",
        "citroen", "limoen", "druif", "druiven", "aardbei", "aardbeien", "framboos",
        "frambozen", "blauwe bes", "bessen", "kiwi", "mango", "ananas", "meloen", "avocado",
        "tomaat", "tomaten", "komkommer", "paprika", "courgette", "aubergine", "ui", "uien",
        "rode ui", "knoflook", "prei", "wortel", "wortels", "winterpeen", "sla", "ijsbergsla",
        "rucola", "spinazie", "andijvie", "boerenkool", "broccoli", "bloemkool", "spruitjes",
        "champignon", "champignons", "paddenstoel", "aardappel", "aardappelen", "krieltjes",
        "zoete aardappel", "bonen", "sperziebonen", "doperwten", "mais", "radijs", "biet",
        "bietjes", "selderij", "venkel", "asperge", "asperges", "pompoen", "groente",
        "groenten", "fruit", "salade", "taugé", "pastinaak", "witlof", "kool", "rodekool",
    ]),
    ("vlees", "Vlees & vis", [
        "vlees", "gehakt", "kip", "kipfilet", "kippendij", "drumstick", "filet", "biefstuk",
        "steak", "varken", "varkenshaas", "karbonade", "speklap", "spek", "spekjes", "bacon",
        "worst", "worstjes", "rookworst", "braadworst", "hamburger", "burger", "shoarma",
        "gyros", "schnitzel", "rundvlees", "stoofvlees", "lam", "ham", "salami", "kalkoen",
        "vis", "zalm", "tonijn", "kabeljauw", "pangasius", "garnalen", "mosselen", "haring",
        "makreel", "vleeswaren", "fricandeau", "rosbief", "kipsate", "sate",
    ]),
    ("zuivel", "Zuivel", [
        "melk", "karnemelk", "yoghurt", "kwark", "vla", "room", "slagroom", "kookroom",
        "creme fraiche", "crème fraîche", "zure room", "boter", "roomboter", "margarine",
        "kaas", "geitenkaas", "mozzarella", "feta", "parmezaan", "roomkaas", "eieren", "ei",
        "skyr", "pudding", "toetje", "kruidenboter", "halvarine", "cheddar", "brie",
    ]),
    ("brood", "Brood", [
        "brood", "volkorenbrood", "witbrood", "bruinbrood", "stokbrood", "baguette",
        "broodjes", "bolletjes", "pistolets", "croissant", "croissants", "krentenbol",
        "krentenbollen", "beschuit", "crackers", "knäckebröd", "wraps", "tortilla", "pita",
        "ciabatta", "focaccia", "afbakbrood", "toast", "ontbijtkoek", "bagel", "bagels",
    ]),
    ("drinken", "Drinken", [
        "water", "spa", "bruiswater", "cola", "fanta", "sprite", "frisdrank", "sap",
        "jus", "jus d'orange", "limonade", "siroop", "ranja", "ice tea", "icetea", "bier",
        "wijn", "rosé", "prosecco", "koffie", "thee", "energiedrank", "tonic", "cassis",
        "chocomel", "smoothie",
    ]),
    ("overig", "Overig", [
        "saus", "pasta", "spaghetti", "rijst", "noedels", "soep", "chips", "koek", "koekjes",
        "chocolade", "snoep", "wc-papier", "toiletpapier", "keukenrol", "afwasmiddel",
        "wasmiddel", "tandpasta", "shampoo", "olie", "olijfolie", "azijn", "ketchup",
        "mayonaise", "mosterd", "pindakaas", "hagelslag", "jam", "honing", "suiker", "meel",
        "bloem", "blik", "diepvries", "pizza", "friet", "patat",
    ]),
]

CATEGORY_KEYS = [c[0] for c in CATEGORIES]
DEFAULT_CATEGORY = "overig"

_QTY = re.compile(r"^\s*(\d+[.,]?\d*\s*(x|st|stuks|kg|g|gr|gram|l|liter|ml|pak|pakken|zak|zakken|bos)?\b\s*)", re.I)


def normalize(name: str) -> str:
    """Kleine letters, hoeveelheid vooraan weghalen: '2 kg Aardappelen' -> 'aardappelen'."""
    n = name.strip().lower()
    n = _QTY.sub("", n)
    return re.sub(r"\s+", " ", n).strip()


def guess_category(name: str) -> str:
    text = normalize(name)
    words = re.findall(r"[\wéèëïöüàâçñ'-]+", text)
    best, best_score = DEFAULT_CATEGORY, 0
    for key, _label, keywords in CATEGORIES:
        for kw in keywords:
            if " " in kw:
                score = 3000 + len(kw) if kw in text else 0
            else:
                score = 0
                for w in words:
                    if w == kw:
                        score = max(score, 4000 + len(kw))   # exact woord
                    elif w.endswith(kw) and len(kw) >= 3:
                        score = max(score, 2000 + len(kw))   # kern van samenstelling: 'sinaasappelsap' -> sap
                    elif w.startswith(kw) and len(kw) >= 3:
                        score = max(score, 1000 + len(kw))   # 'tomatenpuree' -> tomaten (zwakker)
            if score > best_score:
                best, best_score = key, score
    return best
