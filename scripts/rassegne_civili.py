#!/usr/bin/env python3
"""
rassegne_civili.py — giurisprudenza-db, settore civile

Tiene aggiornata la parte CITABILE della Knowledge Base civile: le **Rassegne mensili
della giurisprudenza civile** dell'Ufficio del Massimario, che contengono le massime con
il numero Rv e sono cio' che un avvocato mette in un atto.

Perche' serve un passo dedicato
-------------------------------
La Rassegna ANNUALE (l'orientamento consolidato) esce con 12-18 mesi di ritardo: al 2026
l'ultima disponibile e' quella del 2024. Il periodo scoperto lo coprono le rassegne
MENSILI, pubblicate con ~4-5 mesi di ritardo. Senza questo passo la Knowledge Base
invecchia in silenzio: nessuno si accorge che manca il mese nuovo finche' non serve.

Cosa fa, in ordine
------------------
1. scorre la pagina "Relazioni e documenti" del settore civile (prefisso `RLC`) e apre le
   schede di dettaglio: i nomi dei PDF non seguono uno schema stabile (`rev.2`, `rev02`,
   un `mnesile` con refuso, `Rassegna_mensile_della_giurisprudenza_di_FEBBRAIO_2026`),
   quindi i link si LEGGONO, non si costruiscono;
2. riconosce le rassegne mensili del settore civile e ne ricava periodo e anno **dal
   contenuto del PDF**, non dal nome del file: la Corte ha pubblicato la mensile di
   ottobre 2025 con "OTTOBRE_2026" nel nome (refuso verificato sul contenuto);
3. scarica solo i PDF non ancora presenti in archivio;
4. converte in Markdown con marcatori di pagina e genera l'indice citazionale (Rv -> pagina
   -> massima), lo stesso formato usato dal kit;
5. **oscura i nominativi dei difensori** presenti nella riga delle parti prima di pubblicare;
6. aggiorna INDICE e manifest.

Cosi' l'avvocato riceve materiale gia' convertito e gia' oscurato: non deve convertire
nulla in locale.

Uso:
  python3 scripts/rassegne_civili.py [--dry-run] [--max-nuove N] [--tieni-pdf]

Dipendenze: requests, beautifulsoup4, pdfplumber.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time

import requests
from bs4 import BeautifulSoup

BASE = "https://www.cortedicassazione.it"
URL_LISTA = BASE + "/it/relazioni_documenti_civile.page"
UA = ("giurisprudenza-db/2.0 "
      "(+https://github.com/Synthos-Logic/giurisprudenza-db; aggiornamento settimanale)")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "CIVILE", "RASSEGNE")
TMP = os.path.join(ROOT, ".tmp_rassegne")
LOG = os.path.join(DIR, "LOG_ERRORI.md")
SCRIPTS = os.path.dirname(os.path.abspath(__file__))

MESI = {"GENNAIO": 1, "FEBBRAIO": 2, "MARZO": 3, "APRILE": 4, "MAGGIO": 5, "GIUGNO": 6,
        "LUGLIO": 7, "AGOSTO": 8, "SETTEMBRE": 9, "OTTOBRE": 10, "NOVEMBRE": 11, "DICEMBRE": 12}

OGGI = datetime.date.today().isoformat()
ERRORI = []


def log_errore(msg):
    ERRORI.append(f"- {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} — {msg}")
    print(f"[ERRORE] {msg}", file=sys.stderr)


def fetch(url, binario=False):
    r = requests.get(url, headers={"User-Agent": UA,
                                   "Accept": "*/*" if binario else "text/html,application/xhtml+xml"},
                     timeout=90)
    r.raise_for_status()
    return r.content if binario else r.text


# ----------------------------------------------------------------------------- scoperta

def pagine_lista(max_pagine):
    """Restituisce i contentId RLC di tutte le pagine della lista."""
    voci, visti = [], set()
    for n in range(1, max_pagine + 1):
        url = URL_LISTA if n == 1 else f"{URL_LISTA}?frame3_item={n}"
        try:
            html = fetch(url)
        except Exception as e:
            log_errore(f"pagina lista {n} non raggiungibile: {e}")
            break
        nuovi = [c for c in dict.fromkeys(re.findall(r"contentId=(RLC\d+)", html)) if c not in visti]
        if not nuovi:
            break
        visti |= set(nuovi)
        voci += nuovi
        time.sleep(0.8)
    return voci


def pdf_di_scheda(cid):
    """Apre il dettaglio e restituisce (titolo_pagina, url_pdf) — il link si legge, non si costruisce."""
    url = f"{BASE}/it/rlc_dettaglio.page?contentId={cid}"
    html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup
    pdfs = [a["href"] for a in main.find_all("a", href=True)
            if "/resources/cms/documents/" in a["href"] and a["href"].lower().endswith(".pdf")]
    if not pdfs:
        return None, None
    href = pdfs[0]
    return url, (href if href.startswith("http") else BASE + href)


def e_mensile_civile(nome_file):
    n = nome_file.lower()
    return ("mensile" in n or "mnesile" in n) and "civile" in n


def periodo_dal_pdf(path):
    """Ricava mese e anno leggendo la prima pagina del PDF: il nome del file non e'
    affidabile (la mensile di ottobre 2025 e' pubblicata come 'OTTOBRE_2026')."""
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        testo = " ".join((p.extract_text() or "") for p in pdf.pages[:2])
    # la testata riporta il periodo, talvolta con i caratteri ruotati/spezzati
    piatto = re.sub(r"[^A-Za-z0-9]", "", testo.upper())
    anni = re.findall(r"(20\d{2})", testo)
    mesi_trovati = [m for m in MESI if m in piatto or m in testo.upper()]
    # fallback: cerca le date dei provvedimenti nel corpo (del gg/mm/aaaa)
    if not mesi_trovati or not anni:
        with pdfplumber.open(path) as pdf:
            corpo = "\n".join((p.extract_text() or "") for p in pdf.pages[2:12])
        date = re.findall(r"del (\d{2})/(\d{2})/(\d{4})", corpo)
        if date:
            from collections import Counter
            mm, aa = Counter((d[1], d[2]) for d in date).most_common(1)[0][0]
            return int(mm), int(aa)
        return None, None
    mese = MESI[mesi_trovati[0]]
    # l'anno corretto e' quello coerente con le date dei provvedimenti, non quello del titolo
    with pdfplumber.open(path) as pdf:
        corpo = "\n".join((p.extract_text() or "") for p in pdf.pages[2:12])
    date = re.findall(r"del \d{2}/(\d{2})/(\d{4})", corpo)
    if date:
        from collections import Counter
        mm, aa = Counter(date).most_common(1)[0][0]
        return int(mm), int(aa)
    return mese, int(anni[0])


# ----------------------------------------------------------------------------- archivio

def gia_presenti():
    """Chiavi 'AAAA-MM' gia' in archivio, lette dal manifest."""
    man = os.path.join(DIR, "manifest.json")
    if os.path.isfile(man):
        try:
            return set(json.load(open(man)).get("periodi", []))
        except Exception:
            pass
    presenti = set()
    for dirpath, _, files in os.walk(DIR):
        for f in files:
            m = re.match(r"(\d{4})_(\d{2})", f)
            if m:
                presenti.add(f"{m.group(1)}-{m.group(2)}")
    return presenti


def converti(pdf_path, out_dir, etichetta):
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "converti_indicizza.py"),
                        pdf_path, out_dir, "--titolo", etichetta],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return False, (r.stderr or r.stdout).strip()[:300]
    return True, (r.stdout or "").strip().splitlines()[-1] if r.stdout else ""


def oscura(out_dir):
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "oscura_difensori.py"), out_dir],
                       capture_output=True, text=True)
    n = re.search(r"(\d+) nominativi", r.stdout or "")
    return int(n.group(1)) if n else 0


def rigenera_indice(dry, periodi):
    fonti = []
    for f in sorted(os.listdir(DIR)) if os.path.isdir(DIR) else []:
        if f.endswith(".index.json"):
            try:
                fonti.append(json.load(open(os.path.join(DIR, f))))
            except Exception:
                pass
    righe = ["# INDICE — Rassegne mensili della giurisprudenza civile", "",
             f"> Ultimo aggiornamento: {OGGI} · Rassegne in archivio: {len(fonti)}",
             "> Fonte: Ufficio del Massimario della Corte Suprema di Cassazione, settore civile.",
             ">",
             "> I Markdown sono gia' convertiti con marcatori di pagina e gia' privi dei nominativi",
             "> dei difensori. Ogni massima resta ancorabile: numero Rv, file, pagina.", "",
             "| Periodo | Pagine | Massime (Rv) | File |", "|---|---|---|---|"]
    for v in sorted(fonti, key=lambda x: x.get("fonte", ""), reverse=True):
        righe.append(f"| {v.get('fonte')} | {v.get('pagine_totali','?')} | "
                     f"{v.get('sentenze_rv','?')} | `{v.get('file_md')}` |")
    manifest = {"schema": "giurisprudenza-db/rassegne-civili/1", "generato_il": OGGI,
                "tipo_fonte": "massimario-rassegne", "totale_rassegne": len(fonti),
                "periodi": sorted(periodi)}
    if not dry:
        os.makedirs(DIR, exist_ok=True)
        open(os.path.join(DIR, "INDICE.md"), "w", encoding="utf-8").write("\n".join(righe) + "\n")
        open(os.path.join(DIR, "manifest.json"), "w", encoding="utf-8").write(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return len(fonti)


def scrivi_log():
    if not ERRORI:
        return
    os.makedirs(DIR, exist_ok=True)
    testo = open(LOG, encoding="utf-8").read() if os.path.exists(LOG) else \
        "# LOG ERRORI — rassegne mensili civili\n"
    open(LOG, "w", encoding="utf-8").write(testo.rstrip() + "\n\n" + "\n".join(ERRORI) + "\n")


# ----------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-nuove", type=int, default=3,
                    help="tetto di rassegne nuove per esecuzione (la conversione e' lenta)")
    ap.add_argument("--max-pagine", type=int, default=3,
                    help="pagine della lista da scorrere: le rassegne recenti stanno in testa")
    ap.add_argument("--tieni-pdf", action="store_true", help="non cancella i PDF scaricati")
    ap.add_argument("--da-anno", type=int, default=2025,
                    help="acquisisce solo le mensili da questo anno in poi. Default 2025: le annate "
                         "precedenti sono gia' coperte dalle Rassegne ANNUALI, che riportano le stesse "
                         "massime in forma consolidata e con il numero Rv definitivo; prenderle due "
                         "volte duplicherebbe le massime nell'indice.")
    a = ap.parse_args()

    print(f"== giurisprudenza-db · rassegne mensili civili · {OGGI} · dry_run={a.dry_run} ==")
    presenti = gia_presenti()
    print(f"Periodi gia' in archivio: {len(presenti)}")

    cids = pagine_lista(a.max_pagine)
    if not cids:
        log_errore("nessun contentId RLC trovato: struttura della pagina cambiata?")
        scrivi_log() if not a.dry_run else None
        sys.exit(1)
    print(f"Schede documentali esaminate: {len(cids)}")

    os.makedirs(TMP, exist_ok=True)
    nuove = 0
    for cid in cids:
        if nuove >= a.max_nuove:
            print(f"raggiunto il tetto di {a.max_nuove} rassegne nuove per questa esecuzione")
            break
        try:
            url_scheda, url_pdf = pdf_di_scheda(cid)
        except Exception as e:
            log_errore(f"{cid}: dettaglio non raggiungibile: {e}")
            continue
        time.sleep(0.8)
        if not url_pdf or not e_mensile_civile(os.path.basename(url_pdf)):
            continue

        locale = os.path.join(TMP, os.path.basename(url_pdf))
        try:
            if not os.path.isfile(locale):
                open(locale, "wb").write(fetch(url_pdf, binario=True))
        except Exception as e:
            log_errore(f"{cid}: PDF non scaricabile ({url_pdf}): {e}")
            continue

        try:
            mese, anno = periodo_dal_pdf(locale)
        except Exception as e:
            log_errore(f"{cid}: PDF illeggibile: {e}")
            continue
        if not mese or not anno:
            log_errore(f"{cid}: periodo non ricavabile dal contenuto di {os.path.basename(url_pdf)}")
            continue

        chiave = f"{anno}-{mese:02d}"
        if chiave in presenti:
            continue
        if anno < a.da_anno:
            continue   # gia' coperta dalla Rassegna annuale: niente doppia indicizzazione

        etichetta = f"{anno} {mese:02d} Rassegna Mensile Civile"
        print(f"[NUOVA] {chiave} ← {os.path.basename(url_pdf)}")
        if a.dry_run:
            nuove += 1
            presenti.add(chiave)
            continue

        os.makedirs(DIR, exist_ok=True)
        dest_pdf = os.path.join(TMP, f"{anno}_{mese:02d}_Rassegna_Mensile_Civile.pdf")
        os.replace(locale, dest_pdf)
        ok, msg = converti(dest_pdf, DIR, etichetta)
        if not ok:
            log_errore(f"{chiave}: conversione fallita — {msg}")
            continue
        n_osc = oscura(DIR)
        print(f"          convertita e indicizzata · {n_osc} nominativi oscurati")
        presenti.add(chiave)
        nuove += 1
        if not a.tieni_pdf and os.path.isfile(dest_pdf):
            os.remove(dest_pdf)

    tot = rigenera_indice(a.dry_run, presenti)
    if not a.dry_run:
        scrivi_log()
        if os.path.isdir(TMP) and not a.tieni_pdf:
            for f in os.listdir(TMP):
                try:
                    os.remove(os.path.join(TMP, f))
                except OSError:
                    pass
            try:
                os.rmdir(TMP)
            except OSError:
                pass
    print(f"\n== RIEPILOGO ==\nrassegne nuove: {nuove} | rassegne in archivio: {tot}"
          + ("\n(dry-run: nessun file scritto)" if a.dry_run else ""))


if __name__ == "__main__":
    main()
