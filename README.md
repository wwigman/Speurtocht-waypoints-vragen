# Route-alarm teamdag

De telefoon piept zodra een team bij een vraagpunt is. De vragen zelf staan op papier.
Installeren hoeft niet: de deelnemers openen een URL en laten die openstaan.

Er zijn twee routes met elk tien punten. Het team kiest bij de start zijn route,
zodat de punten van de andere route nooit kunnen meevuren.

## Bestanden

| Bestand | Waar | Wat |
|---|---|---|
| `web/index.html` | statisch, `/opt/alarm/` | de deelnemerspagina |
| `web/sw.js` | statisch, `/opt/alarm/` | offline-cache, geen installatieprompt |
| `server/app.py` | container | routeconfiguratie, teamstatus, jurypagina |
| `server/routes.json` | server | coördinaten en meldstralen, met nano aan te passen |
| `server/docker-compose.yml` | server | draait op 127.0.0.1:8050 |

De pagina haalt de coördinaten bij elke start van de server. Een wijziging in
`routes.json` is dus meteen actief, ook op telefoons die de pagina al eens open hebben gehad.

## Neerzetten

Dit zet het naast je bestaande `/speurtocht/` in plaats van eroverheen, zodat je de oude
versie kunt laten staan tot alles werkt.

Op de packetlab-server:

```
sudo mkdir -p /opt/alarm /opt/alarm-server/data
sudo cp web/* /opt/alarm/
sudo cp server/* /opt/alarm-server/
cd /opt/alarm-server
sudo cp env.voorbeeld .env
sudo nano .env
```

In `.env` zet je de teamcodes en het jurywachtwoord. Daarna:

```
sudo docker compose up -d --build
curl -s localhost:8050/api/gezond
```

Die laatste regel moet `{"ok":true,...}` teruggeven met beide routes erin.

## nginx

Op de packetlab-server, in `/etc/nginx/sites-available/ipsentry`, binnen hetzelfde
serverblok als IPSentry:

```
sudo nano /etc/nginx/sites-available/ipsentry
```

Voeg toe:

```nginx
location /alarm/ {
    root /opt;
    try_files $uri $uri/ /alarm/index.html;
}

location /alarm/api/ {
    proxy_pass http://127.0.0.1:8050/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /alarm/jury {
    proxy_pass http://127.0.0.1:8050/jury;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

`root /opt` en niet `alias`, omdat het URL-pad gelijk is aan de mapnaam. Daarna:

```
sudo nginx -t && sudo systemctl reload nginx
```

Deelnemers gaan naar `https://packetlab.nl/alarm/`, de jury naar
`https://packetlab.nl/alarm/jury`.

## Coördinaten aanpassen

```
sudo nano /opt/alarm-server/routes.json
```

Opslaan is genoeg, de container leest het bestand bij elke aanvraag opnieuw. Herstarten
hoeft alleen als je de container zelf wijzigt.

Over de stralen: twee punten liggen kort op elkaar en hebben daarom een kleinere straal
gekregen. In route 1 liggen vraag 8 en 9 maar 139 meter uit elkaar, dus staan ze allebei
op 50 meter. In route 2 geldt hetzelfde voor vraag 1 en 2, die 173 meter uit elkaar liggen
en op 60 meter staan. Alle andere punten staan op 100 meter, de finish op 120. Ga niet
onder de 40 meter zitten: een telefoon is in open veld op 5 tot 15 meter nauwkeurig en bij
20 km/u rij je door een straal van 50 meter heen in een seconde of vijftien.

## Wat de teams doen

1. URL openen, teamcode invullen, route kiezen.
2. Op **Geluid aan en beginnen** tikken. Die tik is nodig, want een browser mag pas geluid
   afspelen na een handmatige actie.
3. Locatietoestemming geven.
4. Pagina open laten staan. De pagina houdt het scherm zelf wakker.

Bij een punt gaat het alarm af met geluid en trillen, met een gele pagina en het
vraagnummer erop. Dat blijft doorgaan tot iemand op **Gezien** tikt.

Twee uitwijkmogelijkheden onderaan het scherm: **Wij staan bij het punt** vinkt met de hand
af als de GPS niet meewerkt, en **Punt overslaan** markeert een punt als niet gedaan. De
jury ziet allebei terug in het overzicht.

## Wanneer gaat het alarm af

Drie stappen, zodat niemand een punt voorbij rijdt en niemand te vroeg stopt:

1. Op 300 meter klinkt één korte piep. Meer niet, maar genoeg om gas terug te nemen.
2. Zodra je binnen de straal komt, springt het scherm op geel met het vraagnummer, het
   piept en trilt tot iemand op Gezien tikt.
3. Op dat gele scherm staat de resterende afstand, die blijft meelopen. Bij 100 meter
   straal sta je dus nog niet op het punt zelf, maar je ziet precies hoeveel er nog
   tussen zit. Onder de 25 meter zegt hij dat je er bovenop staat.

Een GPS-fix met meer dan 100 meter onzekerheid wordt genegeerd voor het alarm. Zo gaat hij
niet af op een wilde meting terwijl je nog een straat verderop bent. Zo'n fix wordt wel
gewoon getoond, zodat je ziet dat het signaal slecht is.

## Meerdere telefoons per team

Dat mag en het werkt beter dan met één. Elke telefoon meet zelf, dus iedereen in de groep
hoort het alarm, ook wie achteraan rijdt. Op de server worden de afgevinkte punten van alle
telefoons van een team samengevoegd in plaats van overschreven, en elke telefoon krijgt de
stand van het team terug. Dat betekent:

- één persoon tikt op Gezien en de telefoons van de rest gaan ook uit;
- valt een telefoon uit of loopt hij leeg, dan gaat het team gewoon door;
- een vervangend toestel pakt de stand op zodra iemand dezelfde teamcode invoert.

De jury ziet per team hoeveel telefoons er de laatste tien minuten hebben gesynchroniseerd.
Staat daar plotseling 1 waar er 4 hoorden te zijn, dan zit dat team zonder bereik of met
schermen op slot.

Verschillende teams zitten elkaar sowieso niet in de weg: elk team heeft zijn eigen
bestand op de server.

## Grenzen waar je op moet rekenen

Een webpagina mag alleen je positie volgen zolang hij open en zichtbaar is. Gaat het scherm
op slot of schakelt iemand naar WhatsApp, dan stopt het volgen. Dat geldt ook als iemand de
pagina wél installeert, dus op dat punt mist een niet-installeerder niets. Zeg bij de start
dus vooral: scherm aan, pagina open.

Daarom blijft Komoot de betrouwbaarste waarschuwing. De vraagpunten zijn daar al waypoints
en die navigatie draait wél in de achtergrond met het scherm op slot. Het alarm hier is de
tweede laag, het papieren blad met de coördinaten erop is de derde. Geen enkele vraag mag
afhangen van een melding.

Geluid kan na een lange pauze stilvallen op een iPhone, omdat de audio dan niet meer vanzelf
mag starten. Het trillen werkt dan nog wel. Wie het zeker wil weten, tikt na een lange stop
even op **Gezien** in een testalarm of herlaadt de pagina en drukt opnieuw op de startknop.

## Testen vóór de dag

Zet in `routes.json` tijdelijk een punt op je eigen adres met een straal van 100 meter,
en loop een rondje. Zo weet je of geluid, trillen en het gele scherm doen wat ze moeten
doen op de toestellen die meegaan. Zet daarna het echte punt terug.

Controleer op de verkenningsrit ook of de Komoot-melding hoorbaar is en of de regio op
minstens één telefoon per team is vrijgespeeld, want zonder dat werkt navigeren niet.
