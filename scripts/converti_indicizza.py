#!/usr/bin/env python3
"""
converti_indicizza.py — Kit Civilista Italia (v1, derivato dal kit penale)
Converte un PDF a TESTO NATIVO in Markdown pulito con marcatori di pagina e genera
un indice a due livelli affidabili:
  - STRUTTURALE : PARTE / SEZIONE / CAPITOLO -> pagina d'inizio nel corpo
  - CITAZIONALE : ogni massima Cassazione (Rv.) -> pagina + citazione testuale (grounding)
La ricerca fine per concetto si fa con grep sul .md (i titoli di SEZIONE/CAPITOLO
contengono gia' i concetti). NON fa OCR: se il PDF e' scansionato si ferma.
Uso: python3 converti_indicizza.py <input.pdf> <out_dir> [--titolo "Etichetta"]
"""
import sys, re, os, json, argparse

def _inferisci_tipo(path):
    pl = path.lower()
    if "massimario" in pl or "rassegna" in pl: return "massimario"
    if "fascicol" in pl or "/atti" in pl: return "atto-causa"
    if "dottrina" in pl: return "dottrina"
    if "prassi" in pl or "studio" in pl: return "nota-studio"
    if "sentenz" in pl: return "sentenza"
    return "documento"

def estrai_pagine(path):
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        return [(i + 1, p.extract_text() or "") for i, p in enumerate(pdf.pages)]

RE_PARTE   = re.compile(r'^(PARTE\s+[A-ZÀ-Ù]+)\b')
RE_SEZIONE = re.compile(r'^(SEZIONE\s+[IVXLC]+)\b')
RE_CAPITOLO= re.compile(r'^(CAPITOLO\s+[IVXLC]+)\b')
# --- CIVILE ---------------------------------------------------------------
# Il massimario CIVILE cita in forma "Sez. 2, n. 13949/2024, Varrone, Rv. 671693-01"
# (numero/anno), il PENALE in forma "Sez. 3, n. 23006 del 22/06/2026, Rossi, Rv. 123456".
# Questa regex copre ENTRAMBE, piu' le varianti reali riscontrate nei volumi:
# "Sez. U." con punto, "S.U. n.", sezioni miste "Sez. 6 - L", relatore andato a capo,
# "n. 32696 del 2024" (anno senza giorno). Tarata su Rassegna Sezioni Civili 2024
# vol. I: 1178 citazioni catturate su 1207 occorrenze "Rv." (97,6%); le residue sono
# in prevalenza "Rv." orfani riferiti alla decisione citata subito prima
# ("la medesima decisione (Rv. ...)"), che non sono citazioni autonome.
RE_CIT = re.compile(
    r'(?:Sez[.,]?\s*(?:U|L|T|F|\d+)(?:\s*-\s*(?:[A-Z]|\d+))?\.?|S\.\s*U\.)'   # organo
    r'[,\s]*(?:Sentenza|Ordinanza(?:\s+interlocutoria)?|Decreto|sent\.|ord\.)?[,\s]*'  # tipo (opz.)
    r'(?:n\.\s*)?\d{1,6}\s*'                                                     # numero
    r'(?:/\s*\d{4}|del\s+(?:\d{1,2}/\d{1,2}/)?\d{4})'                          # /anno | del [gg/mm/]aaaa
    r'[\s\S]{0,80}?Rv\.\s*\d+(?:\s*-\s*\d+)?')                                # coda fino a Rv
RE_RV = re.compile(r'Rv\.\s*(\d+(?:-\d+)?)')
RE_TOCLEADER = re.compile(r'(?:\.\s*){4,}\d*\s*$')  # sommario: puntini anche spaziati

def running_headers(pagine):
    from collections import Counter
    c = Counter()
    for _, t in pagine:
        for ln in t.split("\n")[:1]:
            s = ln.strip()
            if s and s.isupper() and len(s) > 6: c[s] += 1
    soglia = max(5, int(len(pagine) * 0.04))
    return {h for h, n in c.items() if n >= soglia}

def is_scansione(pagine):
    return sum(1 for _, t in pagine if t.strip()) < max(1, len(pagine) * 0.4)

def is_toc_page(txt):
    lines = [l.strip() for l in txt.split("\n") if l.strip()]
    if not lines: return False
    if lines[0].upper().startswith("INDICE"): return True
    return sum(1 for l in lines if RE_TOCLEADER.search(l)) >= 3

def _is_titolo_line(s):
    al=[c for c in s if c.isalpha()]
    if not al: return False
    up=sum(1 for c in al if c.isupper())/len(al)
    if RE_TOCLEADER.search(s): return False
    return up>0.7 and not s.upper().startswith("SOMMARIO") and not s.upper().startswith("(DI ")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf"); ap.add_argument("out_dir"); ap.add_argument("--titolo", default=None)
    ap.add_argument("--tipo", default=None, help="massimario|sentenza|dottrina|nota-studio|atto-causa|documento")
    a = ap.parse_args()
    base = os.path.splitext(os.path.basename(a.pdf))[0]
    titolo = a.titolo or base
    tipo = a.tipo or _inferisci_tipo(a.pdf)
    os.makedirs(a.out_dir, exist_ok=True)
    pagine = estrai_pagine(a.pdf)
    if is_scansione(pagine):
        print(f"[STOP] '{base}' sembra scansionato: serve OCR. Non convertito."); sys.exit(3)
    running = running_headers(pagine)

    md = [f"# {titolo}", "",
          f"> Conversione automatica da `{os.path.basename(a.pdf)}`. "
          f"`<!-- pag. N -->` = pagina del PDF originale.", ""]
    strutturale = []          # (livello, etichetta, titolo, pagina)
    seen = set(); cur_parte = ""
    pend = None                # (idx_in_strutturale, righe_titolo_raccolte)
    def chiudi():
        nonlocal pend
        if pend is not None:
            i, parts = pend
            tit = " ".join(parts).strip()
            liv, et, _, pg = strutturale[i]
            strutturale[i] = (liv, et, tit, pg)
            pend = None
    for pno, txt in pagine:
        if not txt.strip(): continue
        toc = is_toc_page(txt)
        md.append(f"\n<!-- pag. {pno}{' (sommario)' if toc else ''} -->")
        for ln in txt.split("\n"):
            s = ln.strip()
            if not s: md.append(""); continue
            if toc or RE_TOCLEADER.search(s):
                md.append(s); continue
            mp, ms, mc = RE_PARTE.match(s), RE_SEZIONE.match(s), RE_CAPITOLO.match(s)
            if mp or ms or mc:
                chiudi()
                liv = "PARTE" if mp else ("SEZIONE" if ms else "CAPITOLO")
                qual = s if mp else f"{cur_parte} > {s}"
                if qual in seen:
                    continue
                seen.add(qual)
                if mp: cur_parte = s
                md.append(("\n# " if mp else "\n## ") + s)
                strutturale.append((liv, s, "", pno))
                pend = (len(strutturale)-1, [])     # apri raccolta titolo
            else:
                if pend is not None and len(pend[1]) < 3 and _is_titolo_line(s):
                    pend[1].append(s); md.append(s); continue
                chiudi()
                if s in running: continue
                md.append(s)
    chiudi()
    md_path = os.path.join(a.out_dir, base + ".md")
    open(md_path, "w").write("\n".join(md))

    cits = {}
    for pno, txt in pagine:
        flat = re.sub(r'\s+', ' ', txt.replace("\n", " "))
        for m in RE_CIT.finditer(flat):
            s = m.group(0).strip(); rv = RE_RV.search(s).group(1)
            cits.setdefault(rv, {"rv": rv, "cit": s, "pagine": set()})["pagine"].add(pno)
    for c in cits.values(): c["pagine"] = sorted(c["pagine"])

    meta = {"fonte": titolo, "tipo": tipo, "file_md": os.path.basename(md_path),
            "file_pdf": os.path.basename(a.pdf), "pagine_totali": len(pagine),
            "pagine_con_testo": sum(1 for _, t in pagine if t.strip()),
            "voci_strutturali": len(strutturale), "sentenze_rv": len(cits),
            "strutturale": [list(x) for x in strutturale], "citazioni": list(cits.values())}
    json.dump(meta, open(os.path.join(a.out_dir, base + ".index.json"), "w"),
              ensure_ascii=False, indent=1)
    print(f"[OK] [{tipo}] {titolo}: {meta['pagine_con_testo']}/{meta['pagine_totali']} pag. testo | "
          f"{meta['voci_strutturali']} voci strutturali | {meta['sentenze_rv']} sentenze (Rv)")

if __name__ == "__main__": main()
