#!/usr/bin/env python3
"""
radar_civile.py — giurisprudenza-db, settore civile

Radar delle riviste giuridiche civilistiche: raccoglie SOLO titolo, autore quando esposto,
data e link degli articoli pubblicati, per far sapere all'avvocato di che cosa si sta
discutendo. E' il gemello civile di `radar_merito.py`.

Regole vincolanti
-----------------
- si indicizzano SOLO metadati (titolo, data, link): mai il testo degli articoli, che e'
  opera protetta dei singoli autori;
- le voci del radar NON sono citabili in un atto: segnalano, non provano. Chi vuole usare
  un contenuto apre il link e legge la fonte;
- dedup via `visti.json`: una voce gia' segnalata non ricompare;
- passo NON bloccante nella pipeline: se una testata non risponde si logga e si prosegue.

Fonti: cinque testate con feed RSS verificato funzionante al 6 agosto 2026. Altre riviste
civilistiche importanti non hanno feed o rispondono con protezioni anti-bot: si aggiungono
quando e se espongono un feed, non forzando l'accesso.

Uso:
  python3 scripts/radar_civile.py [--dry-run] [--max-voci N]

Dipendenze: requests.
"""
import argparse
import datetime
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "CIVILE", "RADAR")
OUT = os.path.join(DIR, "RADAR_CIVILE.md")
VISTI = os.path.join(DIR, "visti.json")
LOG = os.path.join(DIR, "LOG_ERRORI.md")

UA = ("giurisprudenza-db/2.0 "
      "(+https://github.com/Synthos-Logic/giurisprudenza-db; radar civile)")
HDRS = {"User-Agent": UA,
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
        "Accept-Language": "it-IT,it;q=0.9"}

FONTI = [
    ("Judicium", "https://www.judicium.it/feed/", "processo civile"),
    ("Il Diritto Processuale Civile", "https://www.ildirittoprocessualecivile.it/feed", "processo civile"),
    ("Diritto Bancario", "https://www.dirittobancario.it/feed/", "bancario e finanziario"),
    ("Diritto.it", "https://www.diritto.it/feed/", "generalista"),
    ("Ius in Itinere", "https://www.iusinitinere.it/feed", "generalista"),
]

OGGI = datetime.date.today().isoformat()
ERRORI = []


def log_errore(msg):
    ERRORI.append(f"- {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} — {msg}")
    print(f"[ERRORE] {msg}", file=sys.stderr)


def voci_rss(nome, url, max_voci):
    """Lettore RSS/Atom tollerante: alcuni feed non sono XML ben formato,
    in quel caso si ripiega su una lettura per espressioni regolari."""
    r = requests.get(url, headers=HDRS, timeout=45)
    r.raise_for_status()
    testo = r.text
    voci = []
    try:
        root = ET.fromstring(re.sub(r"^\s+", "", testo))
        items = root.iter("item")
        for it in items:
            t = (it.findtext("title") or "").strip()
            l = (it.findtext("link") or "").strip()
            d = (it.findtext("pubDate") or "").strip()
            if t and l:
                voci.append({"titolo": t, "url": l, "data": d[:16] or "s.d."})
        if not voci:  # Atom
            ns = "{http://www.w3.org/2005/Atom}"
            for e in root.iter(f"{ns}entry"):
                t = (e.findtext(f"{ns}title") or "").strip()
                le = e.find(f"{ns}link")
                l = le.get("href") if le is not None else ""
                d = (e.findtext(f"{ns}updated") or "")[:10]
                if t and l:
                    voci.append({"titolo": t, "url": l, "data": d or "s.d."})
    except ET.ParseError:
        for m in re.finditer(r"<item>(.*?)</item>", testo, re.S):
            blocco = m.group(1)
            t = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", blocco, re.S)
            l = re.search(r"<link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>", blocco, re.S)
            d = re.search(r"<pubDate>(.*?)</pubDate>", blocco, re.S)
            if t and l:
                voci.append({"titolo": re.sub(r"\s+", " ", t.group(1)).strip(),
                             "url": l.group(1).strip(),
                             "data": (d.group(1)[:16] if d else "s.d.")})
    return voci[:max_voci]


def carica_visti():
    if os.path.isfile(VISTI):
        try:
            return set(json.load(open(VISTI)))
        except Exception:
            return set()
    return set()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-voci", type=int, default=40, help="tetto per singola testata")
    a = ap.parse_args()

    print(f"== giurisprudenza-db · radar civile · {OGGI} · dry_run={a.dry_run} ==")
    visti = carica_visti()
    raccolte, nuove = {}, 0

    for nome, url, taglio in FONTI:
        try:
            voci = voci_rss(nome, url, a.max_voci)
        except Exception as e:
            log_errore(f"{nome}: feed non raggiungibile ({url}): {e}")
            print(f"  {nome}: errore")
            continue
        fresche = [v for v in voci if v["url"] not in visti]
        raccolte[nome] = (taglio, fresche)
        nuove += len(fresche)
        print(f"  {nome}: {len(voci)} voci lette, {len(fresche)} nuove")
        time.sleep(1.0)

    if not raccolte:
        log_errore("nessuna fonte del radar ha risposto")

    righe = ["# RADAR CIVILE — segnalazioni dalle riviste giuridiche", "",
             f"> Aggiornato il {OGGI} · fonti interrogate: {len(FONTI)} · voci nuove in questa esecuzione: {nuove}",
             ">",
             "> **A che cosa serve.** A sapere di che cosa si discute: dottrina, commenti a sentenza,",
             "> note a prima lettura. Sono **solo segnalazioni**: titolo, data e link alla fonte.",
             ">",
             "> **Che cosa NON e'.** Non e' giurisprudenza e **non si cita in un atto**. Per citare",
             "> serve la massima ufficiale: `SEGNALATE/` e le Rassegne del Massimario in Knowledge Base.", ""]
    for nome, (taglio, fresche) in raccolte.items():
        righe += [f"## {nome} _({taglio})_", ""]
        if not fresche:
            righe += ["*Nessuna voce nuova.*", ""]
            continue
        for v in fresche:
            righe.append(f"- **{v['titolo']}** · {v['data']} → [apri]({v['url']})")
        righe.append("")

    if not a.dry_run:
        os.makedirs(DIR, exist_ok=True)
        open(OUT, "w", encoding="utf-8").write("\n".join(righe) + "\n")
        for _, (_, fresche) in raccolte.items():
            visti |= {v["url"] for v in fresche}
        json.dump(sorted(visti), open(VISTI, "w"), ensure_ascii=False, indent=1)
        if ERRORI:
            testo = open(LOG, encoding="utf-8").read() if os.path.exists(LOG) else \
                "# LOG ERRORI — radar civile\n"
            open(LOG, "w", encoding="utf-8").write(testo.rstrip() + "\n\n" + "\n".join(ERRORI) + "\n")

    print(f"\n== RIEPILOGO ==\nvoci nuove: {nuove} | voci gia' viste in archivio: {len(visti)}"
          + ("\n(dry-run: nessun file scritto)" if a.dry_run else ""))


if __name__ == "__main__":
    main()
