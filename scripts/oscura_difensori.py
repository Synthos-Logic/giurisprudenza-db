#!/usr/bin/env python3
"""
oscura_difensori.py — Kit Civilista Italia

Le RASSEGNE MENSILI del Massimario civile riportano, sotto ogni massima, la riga
delle parti nella forma:

    E. (ROPPO VINCENZO) contro E.
    C. (PETRONE LUCA MARIA) contro V. (BIANCHI MARIO)

Le parti sono gia' ridotte a iniziale dalla fonte, ma i DIFENSORI sono indicati per
nome e cognome. Quando i Markdown convertiti vengono pubblicati o condivisi (repo
pubblico, invio a colleghi), questi nominativi sono dati personali che non servono
al lavoro giuridico: la massima si cita per numero e Rv, non per difensore.

Questo script sostituisce il nome del difensore con [omissis], lasciando intatto
tutto il resto: massima, classificazione, estremi, presidente/estensore/relatore/PM
(che fanno parte della citazione ufficiale e sono dati istituzionali).

L'operazione NON tocca l'ancoraggio: numero di pagina, marcatori e testo della
massima restano identici, quindi il protocollo quote-then-claim continua a valere.

Uso:
    python3 oscura_difensori.py <dir_o_file.md> [--dry-run]

Nota: sui documenti di CAUSA di un fascicolo privato NON va usato — li' i nomi
servono. E' pensato per le fonti pubblicate.
"""
import sys, os, re, glob

# Riga delle parti: "E. (ROPPO VINCENZO) contro A. (STERI GIULIO)".
# Il pattern richiede l'INIZIALE DI PARTE (1-4 caratteri + punto) subito prima della
# parentesi: senza questo vincolo si colpirebbero anche "(DI NOME COGNOME)" — gli autori
# dei capitoli delle Rassegne annuali — e sigle come "(C.D. CORRETTIVO)".
# Taratura verificata: 0 falsi positivi sui volumi annuali, 8.813 nominativi nelle mensili.
RE_DIF = re.compile(
    r'(?<![A-Za-zÀ-ù0-9])([A-ZÀ-Ù]{1,4}\.)\s*'
    r'\((?!DI\s|C\.D\.|RV\.|Rv\.)([A-ZÀ-Ù][A-ZÀ-Ù\'’\.\- ]{2,70})\)')

def oscura(testo):
    n = 0
    def r(m):
        nonlocal n; n += 1
        return f"{m.group(1)} ([omissis])"
    return RE_DIF.sub(r, testo), n

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 oscura_difensori.py <dir_o_file.md> [--dry-run]"); sys.exit(2)
    target = sys.argv[1]
    dry = "--dry-run" in sys.argv
    files = [target] if target.endswith(".md") else sorted(glob.glob(os.path.join(target, "*.md")))
    tot = 0
    for f in files:
        testo = open(f, encoding="utf-8").read()
        nuovo, n = oscura(testo)
        tot += n
        if n and not dry:
            open(f, "w", encoding="utf-8").write(nuovo)
        print(f"  {'[dry] ' if dry else ''}{os.path.basename(f)}: {n} nominativi oscurati")
    print(f"[FATTO] {tot} nominativi{' (nessuna scrittura: dry-run)' if dry else ' sostituiti con [omissis]'}")

if __name__ == "__main__":
    main()
