# Speurtocht PWA

Minimale web-app die een vraag toont zodra de telefoon binnen een straal van een GPS-punt komt.

## Bestanden
- `index.html`  – de hele app; routeconfiguratie staat bovenin in `const ROUTE`
- `sw.js`       – service worker, maakt de app offline bruikbaar
- `manifest.webmanifest`, `icon.svg` – nodig voor "Toevoegen aan beginscherm"

## Route aanpassen
Pas `ROUTE.punten` in `index.html` aan:
- `lat`, `lon`: decimale graden (rechtsklik op een kaart in Komoot/OSM → coördinaten kopiëren)
- `straal`: meters; 25–30 m is realistisch voor telefoon-GPS
- `antwoord`: lijst met geaccepteerde antwoorden (hoofdletterongevoelig) of `null` voor vrije invoer
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
