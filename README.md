# Boodschappenlijst (self-hosted)

Sorteert automatisch op looproute: Kruiden → Groente & fruit → Vlees & vis → Zuivel → Brood → Drinken → Overig.

## Accounts en delen
- Inloggen gaat met **Google** of **Apple**. Er worden geen wachtwoorden bewaard, alleen naam en e-mailadres.
- Iedereen heeft eigen lijsten. Tik op de naam van de lijst bovenaan om te wisselen of een nieuwe lijst te maken.
- **Delen**: Aanpassen → *Iemand uitnodigen*. Je krijgt een link die één keer werkt en 7 dagen geldig is. Wie hem opent en inlogt, doet mee.
- Iedereen op een lijst ziet en wijzigt dezelfde producten, looproute, onthouden producten en historie.
- De eigenaar kan mensen van de lijst halen of de lijst verwijderen. Anderen kunnen zelf stoppen.
- Onder Aanpassen → Account kun je uitloggen of je account verwijderen.

## Publiek online zetten
De app moet via **https** bereikbaar zijn, anders werken inloggen en veilige cookies niet.
Zet er een reverse proxy voor, bijvoorbeeld:
- **Cloudflare Tunnel** (geen poorten openzetten op je router; gratis): wijs `boodschappen.jouwdomein.nl` naar `http://<server>:2020`.
- Of Caddy / Nginx Proxy Manager / Traefik met een Let's Encrypt-certificaat.

Zet daarna deze variabelen in `stack.yml` (Portainer: *Environment variables*) of in `.env` (zie `.env.example`):

| Variabele | Wat |
|---|---|
| `PUBLIC_URL` | Het publieke adres, bijv. `https://boodschappen.jouwdomein.nl` |
| `OWNER_EMAIL` | Jouw e-mailadres. Bij je eerste login krijg je de lijst van vóór de accounts. |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Inloggen met Google |
| `APPLE_CLIENT_ID`, `APPLE_TEAM_ID`, `APPLE_KEY_ID`, `APPLE_PRIVATE_KEY` of `APPLE_PRIVATE_KEY_FILE` | Inloggen met Apple (optioneel) |
| `ALLOWED_EMAILS` | Optioneel. Alleen deze accounts mogen erin, bijv. `jij@gmail.com,@familie.nl`. Leeg = iedereen. |
| `SECRET_KEY` | Optioneel. Anders wordt er één aangemaakt in `/data/secret_key`. |

### Google instellen (gratis, ± 10 minuten)
1. Ga naar https://console.cloud.google.com, maak een project aan.
2. *APIs & Services → OAuth consent screen*: kies **External**, vul app-naam en je e-mail in. Scopes: `openid`, `email`, `profile`. Zet de app daarna op **In production** (anders kunnen alleen testgebruikers inloggen).
3. *Credentials → Create credentials → OAuth client ID* → type **Web application**.
   - Authorized redirect URI: `https://boodschappen.jouwdomein.nl/auth/google/callback`
4. Kopieer Client ID en Client secret naar `GOOGLE_CLIENT_ID` en `GOOGLE_CLIENT_SECRET`.

### Apple instellen (optioneel; vereist een Apple Developer-account, € 99 per jaar)
1. https://developer.apple.com/account → *Certificates, Identifiers & Profiles*.
2. *Identifiers* → maak een **App ID** met *Sign in with Apple* aangevinkt.
3. *Identifiers* → maak een **Services ID** (bijv. `nl.jouwdomein.boodschappen`). Dit is `APPLE_CLIENT_ID`.
   Zet *Sign in with Apple* aan → *Configure*: kies je App ID, domein `boodschappen.jouwdomein.nl`,
   Return URL `https://boodschappen.jouwdomein.nl/auth/apple/callback`.
4. *Keys* → nieuwe key met *Sign in with Apple*. Download het `.p8`-bestand (kan maar één keer). De Key ID is `APPLE_KEY_ID`.
5. Je Team ID staat rechtsboven op de developer-site: `APPLE_TEAM_ID`.
6. Zet de inhoud van het `.p8`-bestand in `APPLE_PRIVATE_KEY`, of zet het bestand in het data-volume en gebruik `APPLE_PRIVATE_KEY_FILE=/data/AuthKey_XXXX.p8`.

### Overstappen vanaf versie 1 (zonder accounts)
Je bestaande lijst, historie, looproute en onthouden producten blijven bewaard. Zet `OWNER_EMAIL` op het e-mailadres waarmee je inlogt; bij je eerste login worden ze van jou. Maak eerst een backup van `boodschappen.db`.

### Beveiliging in het kort
- Alleen leden van een lijst kunnen die lijst zien of wijzigen; dat wordt bij elk verzoek gecontroleerd.
- Sessiecookie is `HttpOnly`, `Secure` (bij https) en `SameSite=Lax`; wijzigingen van andere sites worden geweigerd.
- Strikte Content-Security-Policy, geen wachtwoorden in de database.
- Lokaal testen zonder Google/Apple: `DEV_LOGIN=1` geeft een test-login zonder controle. **Nooit publiek aanzetten.**

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
- Meerdere telefoons en mensen op dezelfde lijst blijven vanzelf in sync.

## Aanpassen
- Volgorde of trefwoorden: `categories.py` (daarna `docker compose up -d --build`).
- Nieuwe categorie: voeg hem toe in `categories.py` en geef hem een kleur in `static/index.html` (`--c-<sleutel>`).
- Data staat in `./data/boodschappen.db`.

## Zelf aanpassen (knop "Aanpassen" rechtsboven)
- **Looproute**: zet categorieën met ↑ ↓ in je eigen volgorde, hernoem ze, geef ze een kleur, voeg nieuwe toe (bijv. Diepvries) of verwijder ze.
- **Onthouden producten**: zie welke producten je zelf een plek hebt gegeven, verander de categorie, vergeet ze, of leer vooraf een nieuw product aan.
- Vanuit de lijst kan het ook snel: ⋯ bij een product → kies categorie of maak direct een nieuwe.

## Versies
Elke release krijgt een eigen image, bijv. `ghcr.io/richrdj/boodschappenlijst:1.3.0`.
`latest` is altijd de nieuwste versie. Wil je niet automatisch meegaan, zet dan een vast versienummer in `stack.yml`.
