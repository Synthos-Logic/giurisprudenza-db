#!/usr/bin/env python3
"""
rinvii_pregiudiziali.py — giurisprudenza-db, settore civile

Acquisisce i RINVII PREGIUDIZIALI ex art. 363-bis c.p.c. dalla pagina dedicata del sito
della Corte di cassazione (prefisso contentId `RPC`).

Perche' esistono, e perche' NON sono precedenti
-----------------------------------------------
Nel penale la banca dati raccoglie le "questioni SU pendenti" (QSP): il segnale che un
contrasto e' stato rimesso alle Sezioni Unite. Nel civile quell'istituto non esiste in
quella forma; l'analogo funzionale e' il rinvio pregiudiziale ex art. 363-bis c.p.c., con
cui il giudice di merito sospende il giudizio e rimette alla Corte una questione di diritto
nuova, di particolare importanza e seriale.

Un rinvio PENDENTE non e' un precedente citabile come autorita': serve a sapere che il punto
e' controverso e che la Corte sta per pronunciarsi — utile per istanze di sospensione, motivi
in subordine, scelte di strategia. Il principio di diritto arrivera' con la pronuncia, che
comparira' tra le pronunce segnalate (schede SZC).

Regole vincolanti (come per il resto della banca dati)
-----------------------------------------------------
- ogni campo e' copiato TESTUALMENTE dalla pagina della Corte; campo assente = null;
- NESSUN nome di parte viene estratto: la scheda porta solo l'ufficio remittente e il R.G.
  del giudizio a quo, che sono dati del procedimento, non delle persone;
- il quesito integrale NON e' esposto sulla pagina: sta nell'ordinanza di sospensione, il
  cui PDF ufficiale e' linkato nella scheda. Non si riassume cio' che non si e' letto;
- scheda con campi obbligatori mancanti -> _QUARANTENA/ + LOG_ERRORI.md, mai pubblicata.

Uso:
  python3 scripts/rinvii_pregiudiziali.py [--dry-run] [--force] [--backfill]

Dipendenze: requests, beautifulsoup4.
"""
import argparse
import datetime
import json
import os
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

BASE = "https://www.cortedicassazione.it"
URL_LISTA = BASE + "/it/rinvii_pregiudiziali_ex_art.page"
UA = ("giurisprudenza-db/2.0 "
      "(+https://github.com/Synthos-Logic/giurisprudenza-db; aggiornamento settimanale)")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "CIVILE", "RPC")
QUAR = os.path.join(DIR, "_QUARANTENA")
LOG = os.path.join(DIR, "LOG_ERRORI.md")

OGGI = datetime.date.today().isoformat()
ERRORI = []


def log_errore(msg):
    ERRORI.append(f"- {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} — {msg}")
    print(f"[ERRORE] {msg}", file=sys.stderr)


def fetch(url):
    r = requests.get(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"},
                     timeout=45)
    r.raise_for_status()
    return r.text


def pulisci(t):
    if not t:
        return None
    t = re.sub(r"[ \t]+", " ", t.replace(" ", " "))
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip() or None


def q(v):
    return "null" if v in (None, "") else '"' + str(v).replace('"', "'") + '"'


def data_iso(gg_mm_aaaa):
    gg, mm, aa = gg_mm_aaaa.split("/")
    return f"{aa}-{int(mm):02d}-{int(gg):02d}"


# ----------------------------------------------------------------------------- lista

def parse_lista(html):
    """Dalla lista servono contentId e URL: qui gli href sono slug parlanti,
    non `*_dettaglio.page?contentId=` come nelle altre sezioni del sito."""
    trovati, visti = [], set()
    for m in re.finditer(r'href="(https://www\.cortedicassazione\.it/page/it/[^"]*?contentId=(RPC\d+))"', html):
        url, cid = m.group(1), m.group(2)
        if cid in visti:
            continue
        visti.add(cid)
        trovati.append({"content_id": cid, "url": url})
    return trovati


# ----------------------------------------------------------------------------- dettaglio

def parse_rpc(html, cid, url):
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup
    txt = main.get_text("\n")
    txt = re.sub(r"[ \t]+", " ", txt.replace(" ", " "))
    piatto = re.sub(r"\s+", " ", txt)

    d = {"content_id": cid, "url_scheda": url}

    # Due formati reali:
    #   "Ordinanza di rinvio pregiudiziale del 30/07/2026 con n. 18/2026 - Tribunale di Viterbo - RG 1998/2025"
    #   "Ordinanza di rinvio pregiudiziale del 12/05/2026 - TAR Sicilia, RG. 1640/2017"   (senza numero)
    # Il "n." e' quello attribuito dalla Corte al rinvio: si riporta com'e', senza interpretarlo.
    m = re.search(r"Ordinanza di rinvio pregiudiziale (?:del )?(\d{1,2}/\d{1,2}/\d{4})", piatto)
    if not m:
        return None, "data dell'ordinanza di rimessione non trovata"
    d["data_ordinanza"] = data_iso(m.group(1))
    mn = re.search(r"Ordinanza di rinvio pregiudiziale (?:del )?\d{1,2}/\d{1,2}/\d{4}\s*"
                   r"con n\.?\s*(\d+)\s*/\s*(\d{4})", piatto)
    d["numero"] = int(mn.group(1)) if mn else None
    d["anno"] = int(mn.group(2)) if mn else int(d["data_ordinanza"][:4])

    # "Ufficio di Merito: Tribunale di Venezia, RG. 5343/2025" oppure " - RG 1998/2025"
    mu = re.search(r"Ufficio di Merito:\s*\n?\s*([^\n]+)", txt)
    grezzo = pulisci(mu.group(1)) if mu else None
    if not grezzo:
        mu2 = re.search(r"\d{1,2}/\d{1,2}/\d{4}[^-\n]*-\s*([^\n]+)", piatto)
        grezzo = pulisci(mu2.group(1)) if mu2 else None
    d["ufficio_remittente"], d["rg_giudizio_a_quo"] = grezzo, None
    if grezzo:
        mrg = re.search(r"^(.*?)[,\s-]+R\.?G\.?\s*n?\.?\s*([\d/]+)\s*$", grezzo)
        if mrg:
            d["ufficio_remittente"] = pulisci(mrg.group(1).rstrip(" ,-"))
            d["rg_giudizio_a_quo"] = mrg.group(2)

    mm = re.search(r"Materia:\s*\n?\s*([^\n]+)", txt)
    d["materia"] = pulisci(mm.group(1)) if mm else None
    mi = re.search(r"Data inserimento:\s*([^\n]+)", txt)
    d["data_inserimento"] = pulisci(mi.group(1)) if mi else None

    d["url_pdf"] = None
    for a in main.find_all("a", href=True):
        if "/resources/cms/documents/" in a["href"] and a["href"].lower().endswith(".pdf"):
            d["url_pdf"] = a["href"] if a["href"].startswith("http") else BASE + a["href"]
            break

    obbligatori = ["anno", "data_ordinanza", "ufficio_remittente", "url_pdf"]
    mancanti = [k for k in obbligatori if not d.get(k)]
    return d, (f"campi mancanti: {', '.join(mancanti)}" if mancanti else None)


def scheda(d):
    # quando la Corte non attribuisce un numero al rinvio, il content_id garantisce
    # un nome file stabile (mai due schede per la stessa pagina)
    nome = (f"RPC_{d['numero']}_{d['anno']}.md" if d.get("numero")
            else f"RPC_{d['anno']}_{d['content_id']}.md")
    rg = f" · R.G. {d['rg_giudizio_a_quo']}" if d.get("rg_giudizio_a_quo") else ""
    corpo = f"""---
tipo: rinvio-pregiudiziale
stato: pendente
numero: {d['numero'] if d.get('numero') else 'null'}
anno: {d['anno']}
data_ordinanza: {d['data_ordinanza']}
data_inserimento: {q(d.get('data_inserimento'))}
ufficio_remittente: {q(d.get('ufficio_remittente'))}
rg_giudizio_a_quo: {q(d.get('rg_giudizio_a_quo'))}
materia: {q(d.get('materia'))}
norma: art. 363-bis c.p.c.
deciso_da: null
content_id: {q(d['content_id'])}
url_scheda: {q(d['url_scheda'])}
url_pdf: {q(d['url_pdf'])}
fonte: rinvio-pregiudiziale
estratto_il: {OGGI}
---

# Rinvio pregiudiziale {"n. " + str(d['numero']) + "/" + str(d['anno']) if d.get('numero') else "(senza numero attribuito)"} — {d.get('ufficio_remittente') or 'ufficio non indicato'}{rg}

**Ordinanza di rimessione del {d['data_ordinanza']}** · materia: {d.get('materia') or '*non indicata dalla Corte*'}

## Quesito

*Il testo della questione rimessa non e' esposto sulla scheda della Corte: si trova
nell'ordinanza di sospensione, il cui PDF ufficiale e' linkato qui sotto. Va letto li'.*

## Nota d'uso

Rinvio pregiudiziale **pendente**: non e' un precedente e non si cita come autorita'.
Serve a sapere che la questione e' controversa e che la Corte si pronuncera' — utile per
istanze di sospensione, motivi in subordine e scelte di strategia. Il principio di diritto,
quando arrivera', sara' **vincolante nel procedimento** in cui la questione e' sorta
(art. 363-bis, ultimo comma, c.p.c.) e comparira' tra le pronunce segnalate.

## Fonte autentica

- Scheda ufficiale: {d['url_scheda']}
- Ordinanza di rimessione (PDF): {d['url_pdf']}
"""
    return nome, corpo


# ----------------------------------------------------------------------------- indice

def leggi_frontmatter(path):
    fm, dentro = {}, False
    for riga in open(path, encoding="utf-8"):
        if riga.strip() == "---":
            if dentro:
                break
            dentro = True
            continue
        if dentro and ":" in riga:
            k, v = riga.split(":", 1)
            v = v.strip().strip('"')
            fm[k.strip()] = None if v == "null" else v
    return fm


def rigenera_indice(dry):
    schede = []
    for dirpath, dirnames, filenames in os.walk(DIR):
        dirnames[:] = [x for x in dirnames if x != "_QUARANTENA"]
        for f in sorted(filenames):
            if f.endswith(".md") and f not in ("INDICE.md", "LOG_ERRORI.md"):
                p = os.path.join(dirpath, f)
                fm = leggi_frontmatter(p)
                fm["_rel"] = os.path.relpath(p, DIR)
                schede.append(fm)
    schede.sort(key=lambda s: s.get("data_ordinanza") or "", reverse=True)

    righe = ["# INDICE — Rinvii pregiudiziali ex art. 363-bis c.p.c.", "",
             f"> Ultimo aggiornamento: {OGGI} · Schede: {len(schede)}",
             "> Fonte: pagina \"Rinvii pregiudiziali\" del sito della Corte Suprema di Cassazione.",
             ">",
             "> ⚠️ Sono questioni **pendenti**: non si citano come precedente. Servono a segnalare",
             "> che il punto e' controverso e che la Corte si pronuncera'.", "",
             "| Rinvio | Ordinanza | Ufficio remittente | Materia | Scheda |",
             "|---|---|---|---|---|"]
    for s in schede:
        etich = f"n. {s.get('numero')}/{s.get('anno')}" if s.get('numero') else f"({s.get('anno')})"
        righe.append(f"| {etich} | {s.get('data_ordinanza','?')} | "
                     f"{s.get('ufficio_remittente') or '—'} | {s.get('materia') or '—'} | `{s['_rel']}` |")

    per_materia = {}
    for s in schede:
        per_materia.setdefault(s.get("materia") or "Materia non indicata dalla Corte", []).append(s)
    righe += ["", "## Per materia", ""]
    for mat in sorted(per_materia):
        righe.append(f"### {mat}\n")
        for s in per_materia[mat]:
            et = f"n. {s.get('numero')}/{s.get('anno')}" if s.get('numero') else f"rinvio {s.get('anno')}"
            righe.append(f"- **{et}** · ord. {s.get('data_ordinanza','?')} "
                         f"· {s.get('ufficio_remittente') or '—'} → [scheda]({s['_rel']})")
        righe.append("")

    manifest = {"schema": "giurisprudenza-db/rpc/1", "generato_il": OGGI,
                "tipo_fonte": "rinvio-pregiudiziale", "totale_schede": len(schede),
                "collezioni": {}}
    for s in schede:
        annodir = s["_rel"].split(os.sep)[0]
        c = manifest["collezioni"].setdefault(annodir, {"schede": 0, "files": []})
        c["schede"] += 1
        c["files"].append(s["_rel"])

    if not dry:
        os.makedirs(DIR, exist_ok=True)
        open(os.path.join(DIR, "INDICE.md"), "w", encoding="utf-8").write("\n".join(righe) + "\n")
        open(os.path.join(DIR, "manifest.json"), "w", encoding="utf-8").write(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return len(schede)


def scrivi_log():
    if not ERRORI:
        return
    os.makedirs(DIR, exist_ok=True)
    testo = open(LOG, encoding="utf-8").read() if os.path.exists(LOG) else "# LOG ERRORI — rinvii pregiudiziali\n"
    open(LOG, "w", encoding="utf-8").write(testo.rstrip() + "\n\n" + "\n".join(ERRORI) + "\n")


# ----------------------------------------------------------------------------- main

def esistenti():
    per_id = {}
    for dirpath, dirnames, filenames in os.walk(DIR):
        dirnames[:] = [x for x in dirnames if x != "_QUARANTENA"]
        for f in filenames:
            if f.endswith(".md") and f not in ("INDICE.md", "LOG_ERRORI.md"):
                fm = leggi_frontmatter(os.path.join(dirpath, f))
                if fm.get("content_id"):
                    per_id[fm["content_id"]] = os.path.join(dirpath, f)
    return per_id


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--backfill", action="store_true", help="scorre tutte le pagine della lista")
    ap.add_argument("--max-pagine", type=int, default=15)
    ap.add_argument("--max-schede", type=int, default=200)
    a = ap.parse_args()

    print(f"== giurisprudenza-db · rinvii pregiudiziali (art. 363-bis) · {OGGI} · dry_run={a.dry_run} ==")
    per_id = esistenti()
    print(f"Schede in archivio: {len(per_id)}")

    voci, visti = [], set()
    for n in range(1, (a.max_pagine if a.backfill else 1) + 1):
        url = URL_LISTA if n == 1 else f"{URL_LISTA}?frame3_item={n}"
        try:
            html = fetch(url)
        except Exception as e:
            log_errore(f"pagina lista {n} non raggiungibile: {e}")
            if n == 1:
                scrivi_log() if not a.dry_run else None
                sys.exit(1)
            break
        nuove = [v for v in parse_lista(html) if v["content_id"] not in visti]
        if not nuove:
            print(f"pagina {n}: nessuna voce nuova — fine archivio")
            break
        visti |= {v["content_id"] for v in nuove}
        voci += nuove
        if a.backfill:
            print(f"pagina {n}: +{len(nuove)} voci (totale {len(voci)})")
        time.sleep(1.0)

    if not voci:
        log_errore("nessun contentId RPC trovato nella pagina lista: struttura cambiata?")
        scrivi_log() if not a.dry_run else None
        sys.exit(1)
    print(f"Rinvii sulla lista: {len(voci)}")

    nuove = quar = saltate = 0
    for v in voci[: a.max_schede]:
        cid = v["content_id"]
        if cid in per_id and not a.force:
            saltate += 1
            continue
        try:
            html = fetch(v["url"])
        except Exception as e:
            log_errore(f"{cid}: dettaglio non raggiungibile: {e}")
            continue
        d, problema = parse_rpc(html, cid, v["url"])
        if d is None:
            log_errore(f"{cid}: parsing fallito — {problema}")
            quar += 1
            time.sleep(1.0)
            continue
        nome, corpo = scheda(d)
        if problema:
            log_errore(f"{cid}: scheda in quarantena — {problema}")
            dest = os.path.join(QUAR, nome)
            quar += 1
        else:
            dest = os.path.join(DIR, str(d["anno"]), nome)
            nuove += 1
        if not a.dry_run:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            open(dest, "w", encoding="utf-8").write(corpo)
        print(f"[{'QUARANTENA' if problema else 'NUOVA'}] {os.path.relpath(dest, ROOT)} "
              f"({d.get('ufficio_remittente') or '—'})")
        time.sleep(1.0)

    tot = rigenera_indice(a.dry_run)
    if not a.dry_run:
        scrivi_log()
    print(f"\n== RIEPILOGO ==\nnuove: {nuove} | saltate: {saltate} | quarantena: {quar} | "
          f"schede totali: {tot}" + ("\n(dry-run: nessun file scritto)" if a.dry_run else ""))


if __name__ == "__main__":
    main()
