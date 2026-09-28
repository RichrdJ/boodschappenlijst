# Boodschappenlijst (self-hosted)

Sorteert automatisch op looproute: Kruiden → Groente & fruit → Vlees & vis → Zuivel → Brood → Drinken → Overig.

## Starten
    docker compose up -d --build
Open daarna http://<ip-van-je-server>:8080 op je telefoon en kies "Zet op beginscherm".

## Gebruik
- Typ een product en druk op +. Hoeveelheden mogen ("2 kg aardappelen").
- Tik op een product om af te vinken.
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
