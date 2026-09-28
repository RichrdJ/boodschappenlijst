# Boodschappenlijst (self-hosted)

Sorteert automatisch op looproute: Kruiden → Groente & fruit → Vlees & vis → Zuivel → Brood → Drinken → Overig.

## Starten als stack (Portainer of docker compose)
Gebruik `stack.yml`: die haalt het kant-en-klare image op, bouwen is niet nodig.
In Portainer: Stacks → Add stack → plak de inhoud van `stack.yml` → Deploy.
Of op de server: `docker compose -f stack.yml up -d`

## Zelf bouwen
    docker compose up -d --build
Open daarna http://<ip-van-je-server>:2020 op je telefoon en kies "Zet op beginscherm".

## Gebruik
- Typ een product en druk op +. Hoeveelheden mogen ("2 kg aardappelen").
- Eerder getypte producten verschijnen als suggesties boven het invoerveld. Tik erop om ze meteen toe te voegen. Met een leeg veld zie je wat je vaak koopt. Met ✕ haal je een suggestie weg (handig bij typfouten).
- Tik op een product om af te vinken. Het verdwijnt van je lijst (even "Ongedaan maken" kan) en komt in de Historie.
- **Historie**: alles wat je hebt afgevinkt, per dag. Zet losse producten of een hele dag in één keer weer op je lijst.
- Staat iets verkeerd? Tik op ⋯ en kies de juiste categorie. Dat wordt onthouden.
- Meerdere telefoons blijven vanzelf in sync.

## Aanpassen
- Volgorde of trefwoorden: `categories.py` (daarna `docker compose up -d --build`).
- Nieuwe categorie: voeg hem toe in `categories.py` en geef hem een kleur in `static/index.html` (`--c-<sleutel>`).
- Data staat in `./data/boodschappen.db`.

## Zelf aanpassen (knop "Aanpassen" rechtsboven)
- **Looproute**: zet categorieën met ↑ ↓ in je eigen volgorde, hernoem ze, geef ze een kleur, voeg nieuwe toe (bijv. Diepvries) of verwijder ze.
- **Onthouden producten**: zie welke producten je zelf een plek hebt gegeven, verander de categorie, vergeet ze, of leer vooraf een nieuw product aan.
- Vanuit de lijst kan het ook snel: ⋯ bij een product → kies categorie of maak direct een nieuwe.

## Versies
Elke release krijgt een eigen image, bijv. `ghcr.io/richrdj/boodschappenlijst:1.2.0`.
`latest` is altijd de nieuwste versie. Wil je niet automatisch meegaan, zet dan een vast versienummer in `stack.yml`.
