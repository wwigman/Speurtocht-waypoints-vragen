"""Route-alarm backend.

Doet drie dingen:
  1. de routeconfiguratie uitserveren (met nano aan te passen, direct actief)
  2. de status van elk team ontvangen en wegschrijven
  3. een jurypagina met een live overzicht

De telefoon bepaalt zelf wanneer het alarm afgaat, want dat moet werken
zonder bereik. Deze server houdt alleen de administratie bij.
"""

import json
import math
import os
import re
import secrets
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field

BASIS = Path(__file__).parent
DATA = Path(os.environ.get("DATA_DIR", BASIS / "data"))
ROUTES = Path(os.environ.get("ROUTES_FILE", BASIS / "routes.json"))
TEAMS = [t.strip().upper() for t in os.environ.get("TEAMS", "").split(",") if t.strip()]
JURY_GEBRUIKER = os.environ.get("JURY_GEBRUIKER", "jury")
JURY_WACHTWOORD = os.environ.get("JURY_WACHTWOORD", "")

DATA.mkdir(parents=True, exist_ok=True)
app = FastAPI(title="Route-alarm", docs_url=None, redoc_url=None)
basic = HTTPBasic()


# ---------------------------------------------------------------- hulpjes

def routes() -> dict:
    """Elke keer van schijf lezen, zodat een nano-wijziging meteen telt."""
    return json.loads(ROUTES.read_text(encoding="utf-8"))


def pad(code: str) -> Path:
    if not re.fullmatch(r"[A-Z0-9_-]{1,24}", code):
        raise HTTPException(400, "ongeldige teamcode")
    return DATA / f"{code}.json"


def afstand_m(a: dict, b: dict) -> float:
    R = 6371000.0
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dp = math.radians(b["lat"] - a["lat"])
    dl = math.radians(b["lon"] - a["lon"])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def jury_toegang(c: HTTPBasicCredentials = Depends(basic)) -> str:
    goed = JURY_WACHTWOORD and secrets.compare_digest(
        c.username, JURY_GEBRUIKER
    ) and secrets.compare_digest(c.password, JURY_WACHTWOORD)
    if not goed:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "geen toegang",
            headers={"WWW-Authenticate": "Basic"},
        )
    return c.username


# ---------------------------------------------------------------- model

class Positie(BaseModel):
    lat: float
    lon: float
    acc: float | None = None
    t: str | None = None


class Ping(BaseModel):
    code: str = Field(max_length=24)
    route: str = Field(max_length=24)
    gestart: str | None = None
    klaar: dict[str, dict] = {}
    positie: Positie | None = None
    apparaat: str = Field(default="", max_length=32)


# ---------------------------------------------------------------- api

@app.get("/api/routes")
def api_routes():
    return JSONResponse(routes(), headers={"Cache-Control": "no-store"})


def samenvoegen(oud: dict, nieuw: dict) -> dict:
    """Twee telefoons van hetzelfde team mogen elkaar niet overschrijven.

    Een punt dat er eenmaal in zit, blijft erin. Bij dubbele meldingen wint de
    eerste, behalve als die 'overgeslagen' was en er later alsnog echt is
    afgevinkt.
    """
    uit = dict(oud)
    for nr, k in nieuw.items():
        if nr not in uit:
            uit[nr] = k
            continue
        a, b = uit[nr], k
        if a.get("hoe") == "overgeslagen" and b.get("hoe") != "overgeslagen":
            uit[nr] = b
        elif b.get("hoe") != "overgeslagen" and str(b.get("t", "")) < str(a.get("t", "")):
            uit[nr] = b
    return uit


@app.post("/api/ping")
def api_ping(p: Ping):
    code = p.code.strip().upper()
    if TEAMS and code not in TEAMS:
        raise HTTPException(403, "onbekende teamcode")

    f = pad(code)
    oud = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    nu = time.time()

    rec = p.model_dump()
    rec["code"] = code
    rec["klaar"] = samenvoegen(oud.get("klaar") or {}, p.klaar)
    rec["gestart"] = oud.get("gestart") or p.gestart
    rec["ontvangen"] = nu

    # laatste positie van welk toestel dan ook, plus wie er allemaal meedoet
    app_id = p.apparaat or "onbekend"
    toestellen = oud.get("apparaten") or {}
    toestellen[app_id] = {"t": nu, "positie": rec.get("positie")}
    rec["apparaten"] = {k: v for k, v in toestellen.items() if nu - v.get("t", 0) < 3600}
    verst = max(rec["apparaten"].values(), key=lambda v: v.get("t", 0))
    rec["positie"] = verst.get("positie") or rec.get("positie")

    f.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    # de stand van het team terug, zodat elke telefoon bijtrekt
    return {"ok": True, "ontvangen": nu, "klaar": rec["klaar"]}


@app.get("/api/jury/overzicht")
def api_overzicht(_: str = Depends(jury_toegang)):
    cfg = {r["id"]: r for r in routes()["routes"]}
    codes = TEAMS or sorted(p.stem for p in DATA.glob("*.json"))
    uit = []
    for code in codes:
        f = pad(code)
        if not f.exists():
            uit.append({"code": code, "leeg": True})
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        rt = cfg.get(d.get("route") or "")
        punten = rt["punten"] if rt else []
        klaar = d.get("klaar") or {}
        volgende = next((p for p in punten if str(p["nr"]) not in klaar), None)
        pos = d.get("positie")
        uit.append({
            "code": code,
            "leeg": False,
            "route": rt["naam"] if rt else "?",
            "gehad": len(klaar),
            "totaal": len(punten),
            "overgeslagen": sum(1 for k in klaar.values() if k.get("hoe") == "overgeslagen"),
            "handmatig": sum(1 for k in klaar.values() if k.get("hoe") == "handmatig"),
            "volgende": volgende["nr"] if volgende else None,
            "tot_volgende": round(afstand_m(pos, volgende)) if (pos and volgende) else None,
            "positie": f"{pos['lat']:.5f},{pos['lon']:.5f}" if pos else None,
            "nauwkeurig": pos.get("acc") if pos else None,
            "stil_min": round((time.time() - d.get("ontvangen", 0)) / 60),
            "telefoons": sum(
                1 for v in (d.get("apparaten") or {}).values()
                if time.time() - v.get("t", 0) < 600
            ),
        })
    return uit


# ---------------------------------------------------------------- jury

JURY = r"""<!DOCTYPE html><html lang="nl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Jury</title>
<style>
:root{--papier:#F2F4EE;--inkt:#132A20;--bos:#1E4B3A;--paaltje:#C7452C;--lijn:#C8D2C6;--zacht:#5B6B62;--wit:#fff}
body{margin:0;background:var(--papier);color:var(--inkt);font-family:system-ui,sans-serif;font-variant-numeric:tabular-nums}
header{background:var(--bos);color:var(--papier);padding:16px 22px;display:flex;justify-content:space-between;
align-items:baseline;flex-wrap:wrap;gap:8px}h1{margin:0;font-size:1.15rem}
main{padding:18px 22px 44px;max-width:1100px;margin:0 auto}
table{width:100%;border-collapse:collapse;background:var(--wit);border-radius:12px;overflow:hidden}
th,td{padding:11px 12px;text-align:left;border-bottom:1px solid var(--lijn);font-size:.92rem}
th{background:#E9EDE4;color:var(--zacht);font-weight:600;font-size:.78rem}
tr.stil td:first-child{box-shadow:inset 4px 0 0 var(--paaltje)}
tr.af td:first-child{box-shadow:inset 4px 0 0 var(--bos)}
.balk{height:7px;border-radius:4px;background:var(--lijn);min-width:80px;overflow:hidden}
.balk i{display:block;height:100%;background:var(--bos)}
.mini{color:var(--zacht);font-size:.8rem}a{color:var(--bos)}
p.legenda{color:var(--zacht);font-size:.85rem;margin-top:14px;line-height:1.5}
</style></head><body>
<header><h1>Jury - route-alarm</h1><span id="klok">laden</span></header>
<main><table><thead><tr>
<th>Team</th><th>Route</th><th>Voortgang</th><th>Volgende</th><th>Afstand</th>
<th>Telefoons</th><th>Handmatig</th><th>Overgeslagen</th><th>Laatste sync</th><th>Positie</th>
</tr></thead><tbody id="rijen"></tbody></table>
<p class="legenda">Groene rand: alle punten gehad. Rode rand: meer dan 20 minuten geen contact, waarschijnlijk geen bereik of telefoon op slot.
Handmatig betekent dat het team zelf heeft afgevinkt zonder GPS-melding. Ververst elke 15 seconden.</p></main>
<script>
async function laad(){
  const basis = location.pathname.replace(/\/jury\/?$/, '/');
  const r = await fetch(basis + 'api/jury/overzicht',{cache:'no-store'});
  if(!r.ok){document.getElementById('klok').textContent='fout '+r.status;return;}
  const d = await r.json();
  document.getElementById('rijen').innerHTML = d.map(t=>{
    if(t.leeg) return `<tr><td>${t.code}</td><td colspan="9" class="mini">nog niet gestart</td></tr>`;
    const pct = t.totaal ? Math.round(100*t.gehad/t.totaal) : 0;
    const af = t.volgende === null;
    const stil = !af && t.stil_min > 20;
    const kaart = t.positie ? `<a href="https://www.google.com/maps?q=${t.positie}" target="_blank" rel="noopener">kaart</a>
      <span class="mini">&plusmn;${t.nauwkeurig ?? '?'} m</span>` : '<span class="mini">onbekend</span>';
    return `<tr class="${af?'af':stil?'stil':''}"><td><b>${t.code}</b></td><td class="mini">${t.route}</td>
      <td><div class="balk"><i style="width:${pct}%"></i></div><span class="mini">${t.gehad} van ${t.totaal}</span></td>
      <td>${af?'klaar':'vraag '+t.volgende}</td>
      <td>${t.tot_volgende===null?'<span class="mini">-</span>':(t.tot_volgende>=1000?(t.tot_volgende/1000).toFixed(1)+' km':t.tot_volgende+' m')}</td>
      <td>${t.telefoons||''}</td><td>${t.handmatig||''}</td><td>${t.overgeslagen||''}</td>
      <td class="mini">${t.stil_min} min geleden</td><td>${kaart}</td></tr>`;
  }).join('');
  document.getElementById('klok').textContent = new Date().toLocaleTimeString('nl-NL');
}
laad(); setInterval(laad, 15000);
</script></body></html>"""


@app.get("/jury", response_class=HTMLResponse)
def jury(_: str = Depends(jury_toegang)):
    return HTMLResponse(JURY)


@app.get("/api/gezond")
def gezond():
    return {"ok": True, "teams": len(TEAMS), "routes": [r["id"] for r in routes()["routes"]]}
