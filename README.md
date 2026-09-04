# Speurtocht PWA

Digitaal deelnemersblad voor de Teamdag BB OT (rondje IJssel): opent per locatie de opdrachten zodra de telefoon binnen de straal komt, teams vullen antwoorden en foto's in en leveren aan het eind een HTML-rapport in.

`index.v1.html` is de oorspronkelijke één-vraag-per-punt versie, als referentie.

## Bestanden
- `index.html`  – de hele app; routeconfiguratie staat bovenin in `const ROUTE`
- `sw.js`       – service worker, maakt de app offline bruikbaar
- `manifest.webmanifest`, `icon.svg` – nodig voor "Toevoegen aan beginscherm"

## Route aanpassen
Pas `ROUTE.locaties` in `index.html` aan (per locatie een lijst `opdrachten`):
- `lat`, `lon`: decimale graden (rechtsklik op een kaart in Komoot/OSM → coördinaten kopiëren)
- `straal`: meters; 25–30 m is realistisch voor telefoon-GPS
- `lat`/`lon` = `null`: locatie zonder GPS, teams openen hem met de hand
- `invoer`: `tekst`, `getal` (met `eenheid`), `tijd` of `foto`
- `controleer: true` markeert coördinaten die nog op de verkenningsrit bevestigd moeten worden
- `volgordeVast`: `true` = punten alleen in volgorde; `false` = willekeurige volgorde

## Hosten
Zet de map op een HTTPS-webserver (bijv. achter je Caddy/nginx). Geolocation en service
workers werken alleen via HTTPS (of op `localhost`). Lokaal testen:

    python3 -m http.server 8000     # → http://localhost:8000

## Testen zonder te lopen
Knop "Testmodus" onderaan → "Simuleer aankomst" zet een neppositie 5 m naast het volgende punt.
"Wis voortgang" reset de opgeslagen antwoorden (localStorage).

## Bekende beperkingen
- iOS: de pagina moet op de voorgrond staan; achtergrond-GPS voor websites stopt na enkele seconden.
- Android: achtergrond werkt langer maar niet gegarandeerd. Houd de app open of open hem bij elke halte.
- Voortgang staat alleen op het toestel zelf (localStorage). Voor scores over meerdere spelers is een backend nodig.
