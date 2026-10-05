"""
Uitgebreide woordenlijst met gangbare supermarktproducten, per categorie.
Wordt gebruikt voor productherkenning (tikfouten verbeteren) én voor de indeling.
Alles in kleine letters en in enkelvoud waar dat kan; meervoud ('-s', '-en') en
verkleinwoorden worden vanzelf herkend. Voeg gerust woorden toe.
"""

EXTRA = {
    "kruiden": """
        kruidenmix kruidenmengsel specerijen specerij kerriepoeder currypoeder garam masala
        kurkuma geelwortel chilipoeder chilivlokken cayennepeper sambal sambal oelek
        paprikapoeder gerookt paprikapoeder knoflookpoeder uienpoeder laurier laurierblad
        kruidnagel steranijs anijs kardemom venkelzaad karwijzaad mosterdzaad komijnzaad
        korianderzaad fenegriek saffraan vanille vanillestokje vanillesuiker vanille-extract
        majoraan marjolein kervel lavas kruidenbouillon bouillon bouillonblokje bouillonblokjes
        bouillonpoeder fond kippenbouillon groentebouillon runderbouillon zeezout grof zout
        peper en zout zwarte peper witte peper peperkorrels citroenpeper italiaanse kruiden
        provençaalse kruiden kipkruiden gehaktkruiden shoarmakruiden gyroskruiden fajitakruiden
        tacokruiden nasikruiden bamikruiden ras el hanout za'atar sumak dukkah ketjap ketjap manis
        sojasaus sojasaus zout tamari vissaus oestersaus worcestersaus tabasco sriracha
        harissa wasabi miso misopasta gembersiroop gemberpoeder verse gember knoflookpasta
        gemberpasta tomatenpuree kerriepasta currypasta rode currypasta groene currypasta
        boemboe pindasaus pindasausmix sate kruiden mosterdpoeder nootmuskaatpoeder
        foelie piment jeneverbes jeneverbessen kruidenbuiltjes verse kruiden potkruiden
        basilicumplant peterselieplant bladpeterselie krulpeterselie thaise basilicum
        kaffirlimoenblad limoenblad pandan zoethout
    """,
    "groente_fruit": """
        groentemix roerbakgroente roerbakmix wokgroente soepgroente soepgroenten stamppotgroente
        andijviestamppot hutspot hutspotmix zuurkool snijbonen tuinbonen kapucijners
        kidneybonen kikkererwten linzen rode linzen edamame peultjes peulen sugarsnaps
        sugar snaps knolselderij bleekselderij stengel selderij rabarber postelein veldsla
        romaine romaine sla kropsla eikenbladsla lollo rosso little gem babyspinazie
        boerenkoolmix rucolamix slamix salademix spitskool savooiekool witte kool groene kool
        chinese kool paksoi pak choi taugé raapstelen spinaziemix sperzieboon kousenband
        bospeen bospeentjes worteltjes snoepgroente snoeptomaat snoeptomaatjes cherrytomaat
        cherrytomaatjes trostomaat trostomaten vleestomaat roma tomaat pruimtomaat
        komkommer mini komkommer augurk augurken zilveruitjes uitjes sjalot sjalotten
        bosui bosuien lente-ui lenteuitjes rode uien gele uien knoflookteen knoflookbol
        paprika rood paprika groen puntpaprika snackpaprika peper rode peper chilipeper
        jalapeño jalapeno spaanse peper madame jeanette groene peper courgettes aubergines
        pompoenen butternut flespompoen hokkaido zoete aardappelen bataat yam cassave
        aardappelpartjes kruimige aardappelen vastkokende aardappelen aardappelschijfjes
        roseval nicola opperdoezer frieten krieltjes rettich mierikswortel schorseneren
        koolrabi artisjok artisjokken palmharten okra olijven olijf groene olijven zwarte olijven
        kappertjes zongedroogde tomaten paddenstoelen kastanjechampignons oesterzwammen
        shiitake portobello cantharellen boschampignons truffel maïs maiskolf maiskolven
        doperwtjes erwten erwtjes spinazie a la creme bietjes gekookte bieten rode biet
        appel elstar jonagold goudrenet pink lady granny smith braeburn kanzi junami
        handappel stoofpeer stoofperen conference doyenne sinaasappelen perssinaasappel
        perssinaasappels handsinaasappel clementine clementines mandarijnen grapefruit
        pomelo citroenen limoenen bloedsinaasappel kumquat banaantje bananen
        kiwi's kiwis gele kiwi blauwe bessen bosbes bosbessen braam bramen rode bessen
        zwarte bessen kruisbes kruisbessen veenbes cranberry cranberries aalbes aalbessen
        kers kersen krieken pruim pruimen perzik perziken nectarine nectarines abrikoos
        abrikozen mango's mangos papaja papaya passievrucht passievruchten granaatappel
        granaatappelpitjes lychee lychees litchi kaki sharonfruit vijg vijgen dadel dadels
        medjool kokosnoot kokos ananassen watermeloen galiameloen honingmeloen cantaloupe
        meloenen druiven wit druiven rood pitloze druiven avocado's avocados rijpe avocado
        fruitsalade fruitbakje fruitmix gesneden fruit appelmoes appelmoes pot
        rozijnen krenten sultanarozijnen gedroogde abrikozen gedroogde vijgen gedroogd fruit
        noten notenmix studentenhaver walnoot walnoten hazelnoot hazelnoten amandel amandelen
        cashew cashewnoten pinda pinda's pindas pistache pistachenoten paranoot paranoten
        pecannoot pecannoten macadamia pijnboompitten zonnebloempitten pompoenpitten
        lijnzaad chiazaad sesamzaad sesam kokosrasp tofu tempeh seitan
        pannenkoekenmix groenteburger
    """,
    "vlees": """
        gehakt half om half rundergehakt varkensgehakt kipgehakt lamsgehakt gehaktballen
        gehaktbal balletjes soepballetjes slavink slavinken blinde vink blinde vinken
        hamlap hamlappen varkenslap varkensfilet varkensrollade rollade runderrollade
        procureur varkensribben spareribs spare ribs ribbetjes krabbetjes buikspek
        ontbijtspek baconreepjes spekreepjes katenspek ontbijtkoek-spek rauwe ham gekookte ham
        beenham achterham schouderham serranoham prosciutto parmaham chorizo pepperoni
        cervelaat boterhamworst leverworst grillworst gelderse rookworst knakworst
        knakworsten frankfurter hotdog hotdogworst saucijs saucijzen saucijzenbroodje
        chipolata merguez boerenworst runderworst kipworst kippenworst ontbijtworst
        kipfilets kipreepjes kipblokjes kippenpoten kippenvleugels kipvleugels kippenbouten
        kippendijen kippendijfilet hele kip scharrelkip kipschnitzel kipgyros kipshoarma
        kipnuggets kipburger kipdrumsticks kalkoenfilet kalkoenspies eendenborst eend
        biefstukken entrecote ribeye ossenhaas tournedos runderlappen sukadelappen
        riblappen stoofvlees runderstoof hachee hacheevlees rundertartaar tartaar
        carpaccio rosbief runderburger runderreepjes runderhaas kalfsvlees kalfsoester
        lamsrack lamskotelet lamskoteletten lamsbout lamsvlees konijn wild hertenbiefstuk
        varkenshaasje varkensreepjes varkenspoulet poulet shoarmavlees gyrosvlees
        saté satévlees kipsaté babi pangang filet americain americain paté pate
        rookvlees pastrami kipfilet beleg kipfiletplakjes kalkoenplakjes vegaburger
        vegetarisch gehakt vegaballetjes vegetarische schijf vleesvervanger kipstuckjes
        vegetarische kipstukjes visstick vissticks lekkerbekje kibbeling zalmfilet
        zalmmoten gerookte zalm zalmsnippers tonijnsteak tonijn in blik tonijnstukken
        kabeljauwfilet koolvis schol tong pangasiusfilet tilapia forel gerookte forel
        makreelfilet gerookte makreel paling gerookte paling sardines sardientjes ansjovis
        haringen hollandse nieuwe zure haring rolmops rolmopsen garnaal gamba gamba's
        scampi scampi's grote garnalen hollandse garnalen noordzeekrab krab krabsticks
        surimi inktvis calamaris octopus sint-jakobsschelp coquilles oesters mossel
        kreeft zeevruchten zeebaars dorade zeebrasem heek wijting victoriabaars
        vispakket visburger tonijnsalade zalmsalade kipkerriesalade eiersalade
        vleessalade huzarensalade filet american
    """,
    "zuivel": """
        volle melk halfvolle melk magere melk lactosevrije melk sojamelk havermelk amandelmelk
        rijstmelk kokosmelk haverdrank sojadrink amandeldrink plantaardige melk
        chocolademelk koffiemelk koffiecreamer creamer slagroom spuitbus spuitroom
        vanillevla chocoladevla vla flip vlaflip griesmeelpudding rijstepap rijstpap
        karnemelkpap brinta griesmeel kwarktaart yoghurtdrank drinkyoghurt fruityoghurt
        griekse yoghurt turkse yoghurt volle yoghurt magere yoghurt kokosyoghurt
        sojayoghurt plantaardige yoghurt yoghurt naturel optimel fristi yakult actimel
        vifit kefir lassi kwark naturel magere kwark volle kwark verse kwark
        mascarpone ricotta cottage cheese huttenkase hüttenkäse zuivelspread smeerkaas
        kaasspread roomkaas naturel philadelphia boursin geitenkaasje burrata halloumi
        jonge kaas jong belegen belegen kaas oude kaas extra belegen goudse kaas
        goudse edammer leerdammer maasdammer emmentaler gruyère gruyere comté parmigiano
        grana padano pecorino manchego gorgonzola roquefort camembert blauwe kaas
        geraspte kaas kaasplakken plakjes kaas kaasblokjes geitenkaas plakken komijnekaas
        nagelkaas kruidenkaas mozzarella di bufala raclette raclettekaas fondue fonduekaas
        smeltkaas cheddar plakken zachte kaas harde kaas kaasje vegan kaas
        eieren scharreleieren vrije uitloop eieren biologische eieren kippeneieren
        eiwit eidooier gekookte eieren ei's room kookroom crème fraîche zure room
        roomboter ongezouten roomboter gezouten boter bakboter braadboter halvarine
        margarine blueband becel bak en braad vloeibare margarine plantaardige boter
        ghee kruidenboter knoflookboter
        diepvriespizza ijs ijsje roomijs schepijs ijsjes waterijsje raketje magnum
        cornetto sorbetijs vanille-ijs diepvriesgroente diepvriesspinazie diepvriesfruit
        diepvriesfrites diepvriesfriet bevroren erwten bladerdeeg pizzadeeg kruimeldeeg
        taartdeeg filodeeg loempia loempia's bitterballen kroket kroketten frikandel
        frikandellen kaassoufflé kaassouffles mini loempia's ovenfrites aardappelkroketjes
        rösti aardappelrösti
    """,
    "brood": """
        tijgerbrood waldkorn meergranenbrood speltbrood roggebrood zuurdesembrood
        zuurdesem desembrood maisbrood vloerbrood boerenbrood volkorenbol bolletje
        kaiserbroodje kaiserbroodjes harde broodjes zachte broodjes witte bollen bruine bollen
        puntbroodje puntjes mueslibol mueslibollen krentenbrood rozijnenbrood suikerbrood
        suikerbol paasbrood kerststol stol afbakbroodjes afbakstokbrood stokbroodjes
        knoflookstokbrood kruidenstokbrood petit pain pistolet hamburgerbroodjes
        hamburgerbrood hotdogbroodjes hotdogbrood wrap tortilla's tortillas tacoschelpen
        taco's pitabroodje pitabroodjes naanbrood naan turks brood turkse pide
        sandwich sandwiches toastbrood tosti tostibrood beschuiten rijstwafels
        rijstwafel maiswafels cracottes knäckebröd crackers volkoren crackers toastjes
        soepstengels grissini paneermeel broodkruim croutons kruidkoek ontbijtkoek
        peperkoek eierkoek eierkoeken ontbijtkoekjes muffin muffins cake
        cakeje cakejes appeltaart taart taartje gebak gebakjes tompouce tompoucen
        stroopwafel stroopwafels donut donuts brownie brownies croissant roomboter
        chocoladebroodje chocoladebroodjes saucijzenbroodje worstenbroodje kaasbroodje
        appelflap appelflappen oliebol oliebollen pannenkoek pannenkoeken pannenkoekjes
        poffertjes wafels wafel luikse wafels flensjes crêpes crepes
        pancakes pancake bagels engelse muffins
    """,
    "drinken": """
        mineraalwater spa blauw spa rood bronwater koolzuurhoudend water plat water
        sinaasappelsap appelsap druivensap multivitaminesap tomatensap cranberrysap
        ananassap grapefruitsap perssap verse jus smoothies vruchtensap
        cola zero cola light pepsi pepsi max 7up seven up sinas fanta orange
        cassis rivella dubbelfriss dubbel friss ginger ale ginger beer bitter lemon tonic water
        ijsthee ice tea green ice tea lipton fuze tea arizona sportdrank aa drink
        isostar red bull monster energydrink limonadesiroop siroop aardbei
        diksap vruchtensiroop roosvicee karvan cevitam priklimonade spa fruit
        kokoswater koffiebonen koffiepads koffiecups capsules nespresso cups senseo pads
        filterkoffie gemalen koffie oploskoffie instant koffie espressobonen cappuccino
        koffiefilters theezakjes losse thee groene thee zwarte thee muntthee kamillethee
        rooibos earl grey bosvruchtenthee ijsthee siroop chai warme chocolademelk
        cacao cacaopoeder chocomel chocolademelk anijsmelk
        pils speciaalbier witbier ipa alcoholvrij bier 0.0 bier radler blikken bier
        krat bier kratje heineken grolsch hertog jan amstel brand bavaria hoegaarden
        rode wijn witte wijn rosé wijn mousserende wijn cava champagne port sherry
        likeur jenever vodka whisky rum gin advocaat baileys martini aperol campari
        cider sangria glühwein alcoholvrije wijn
    """,
    "overig": """
        penne fusilli macaroni farfalle tagliatelle lasagne lasagnebladen ravioli tortellini
        tortelloni gnocchi orzo vermicelli volkoren pasta verse pasta mie mienestjes
        mie nestjes udon ramen rijstnoedels glasnoedels wokkenoedels basmati basmatirijst
        jasmijnrijst zilvervliesrijst risottorijst sushirijst pandanrijst nasi bami
        couscous bulgur quinoa gierst parelgort polenta havermout havervlokken muesli
        cruesli granola cornflakes ontbijtgranen brinta rice krispies kellogg's
        pastasaus tomatensaus pesto groene pesto rode pesto knoflooksaus currysaus
        barbecuesaus bbq saus satésaus pindasaus fritessaus joppiesaus cocktailsaus
        whiskeysaus sweet chili saus ketjap sojasaus slasaus dressing vinaigrette
        mayonaise yoghurtsaus tzatziki hummus guacamole salsa tapenade aioli
        mosterd grove mosterd dijonmosterd azijn balsamico balsamicoazijn wijnazijn
        appelazijn zonnebloemolie arachideolie frituurolie frituurvet bakolie
        kokosolie sesamolie olijfolie extra vierge bloem zelfrijzend bakmeel tarwebloem
        speltbloem maizena maïzena custard bakpoeder gist droge gist baksoda
        kristalsuiker basterdsuiker poedersuiker rietsuiker kandijsuiker zoetstof
        stevia honing ahornsiroop agavesiroop stroop appelstroop schenkstroop
        jam aardbeienjam frambozenjam abrikozenjam marmelade appelstroop chocopasta
        nutella hagelslag pure hagelslag melk hagelslag vlokken chocoladevlokken
        muisjes gestampte muisjes vruchtenhagel speculoospasta pindakaas met stukjes
        notenpasta tahin sandwichspread smeerworst leverpastei zalmsalade
        tomatenblokjes gepelde tomaten passata tomatenpuree kidneybonen in blik
        bruine bonen witte bonen in tomatensaus kikkererwten in blik linzen in blik
        maïs in blik doperwten en worteltjes champignons in blik ananas in blik
        perziken op siroop knakworstjes in blik soep in blik tomatensoep
        groentesoep kippensoep erwtensoep snert kippenbouillon cup-a-soup
        noedelsoep pasta mix maaltijdmix wereldkeuken tacomix mexicaanse mix nasi mix
        bami mix kroepoek kroepoek emping atjar seroendeng sambal badjak
        chips paprikachips naturel chips ribbelchips nachos tortillachips popcorn
        zoutjes pretzels borrelnootjes nootjes pinda's gezouten cashewnoten zoute stengels
        tuc mergpijpjes koekjes biscuit biscuitjes speculaas speculaasjes kruidnoten
        pepernoten stroopwafels mariabiscuit liga evergreen sultana bastogne
        chocoladereep reep chocolade melkchocolade pure chocolade witte chocolade
        bonbons pralines drop dropjes winegums zuurtjes kauwgom pepermunt
        marshmallows spekjes lolly lolly's snoepjes tumtum haribo m&m's twix mars
        snickers kitkat bounty sultana's mueslireep mueslirepen proteïnereep
        rijstwafels gevuld diepvries diepvriesmaaltijd kant-en-klaarmaaltijd maaltijdsalade
        pizza margherita pizzabodem pizzasaus tortilla chips
        kattenvoer kattenbrokken kattenbak kattenbakvulling hondenvoer hondenbrokken
        hondensnacks vogelzaad visvoer
        luiers billendoekjes babyvoeding flesvoeding babyhapje knijpfruit
        toiletpapier wc-papier wcpapier keukenpapier tissues zakdoekjes servetten
        vuilniszakken afvalzakken pedaalemmerzakken diepvrieszakjes boterhamzakjes
        aluminiumfolie aluminium folie huishoudfolie bakpapier vershoudfolie
        sandwichzakjes afwasmiddel vaatwastabletten vaatwasblokjes vaatwaszout
        glansspoelmiddel afwasborstel sponsjes schuursponsjes vaatdoekjes theedoeken
        wasmiddel vloeibaar wasmiddel waspoeder wascapsules wasverzachter
        vlekverwijderaar allesreiniger schoonmaakmiddel badkamerreiniger wc-reiniger
        wc-blokjes toiletblok ontkalker azijnreiniger glasreiniger chloor bleek
        groene zeep schoonmaakazijn ontstopper dweil dweilen microvezeldoek stofdoek
        handzeep zeep douchegel shampoo conditioner haarmasker deodorant deo
        tandpasta tandenborstel tandenborstels flosdraad mondwater scheerschuim
        scheermesjes scheermes bodylotion handcrème zonnebrand zonnebrandcrème
        dagcrème nachtcrème lippenbalsem wattenschijfjes wattenstaafjes maandverband
        tampons inlegkruisjes paracetamol ibuprofen pleisters vitamines vitamine d
        batterijen lampen gloeilamp led lamp kaarsen theelichtjes waxinelichtjes
        lucifers aansteker bloemen bos bloemen plant potgrond
    """,
}


# bijvoeglijke naamwoorden en losse stukjes van woordgroepen: zelf geen product
STOP = set("""
    alcoholvrij alcoholvrije biologisch biologische blauwe blinde bruine chinese droge engelse
    gedroogd gedroogde gekookte gelderse gele gepelde geraspte gerookt gerookte gestampte goudse
    griekse groen groene grof grote grove hele hollandse italiaanse jong jonge kruimige
    lactosevrije losse luikse madame magere mexicaanse mousserende nieuwe oude pitloze
    plantaardige provençaalse pure rauwe rijpe rood rode spaanse thaise turkse vastkokende
    vegetarisch vegetarische verse vierge vloeibaar vloeibare volle halfvolle vrije uitloop warme
    wit witte zachte harde zoete zongedroogde zoute zure zwarte little ice spare orange cottage
    cheese rice ale jeanette creme fuze ei's 0.0 up seven max light zero kleine gemalen plat
    instant volkoren mini extra naturel gezouten ongezouten belegen blauw spa bos pak pot blik
    met zout gesneden half dubbel friss sugar
""".split())

# woorden die in meer dan één categorie voorkomen: hier staat waar ze horen
OWNER = {
    "ketjap": "overig", "sojasaus": "overig", "sambal": "overig", "pindasaus": "overig",
    "kippenbouillon": "overig", "tomatenpuree": "overig", "cashewnoten": "overig",
    "pinda's": "overig", "kidneybonen": "overig", "kikkererwten": "overig", "linzen": "overig",
    "maïs": "groente_fruit", "worteltjes": "groente_fruit", "perziken": "groente_fruit",
    "erwten": "groente_fruit", "saucijzenbroodje": "brood", "zalmsalade": "vlees",
    "brinta": "overig", "chocolademelk": "drinken", "rijstwafels": "brood",
    "stroopwafels": "overig",
}


def extra_keywords(key: str, skip: set = frozenset()) -> list[str]:
    """Losse productwoorden voor een categorie (zonder stopwoorden, dubbelen en woorden in skip)."""
    out = set()
    for w in EXTRA.get(key, "").split():
        if len(w) < 3 or w in STOP or w in skip:
            continue
        if OWNER.get(w, key) != key:
            continue
        out.add(w)
    return sorted(out)
