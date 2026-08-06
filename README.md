# giurisprudenza-db

**Banca dati aperta di giurisprudenza penale con fonti verificabili**: le pronunce penali
segnalate dall'Ufficio del Massimario della Corte Suprema di Cassazione, l'**archivio completo
della Corte costituzionale dal 1956** (open data ufficiale) e il radar del merito dalle riviste
open access.

> *Nota sul nome*: il repository è nato per le sole segnalate della Cassazione e ne conserva
> il nome; il perimetro si è esteso (Corte costituzionale, merito). Un'eventuale ridenominazione
> è rinviata a valle dei test in corso per non rompere le integrazioni esistenti.

Una scheda Markdown per pronuncia: massima ufficiale (campo "Oggetto"), "L'esito in sintesi",
estremi completi e link diretto alla scheda ufficiale e al PDF autentico sul sito della Corte.
**Nessuna riformulazione**: solo testo ufficiale, verificabile con un clic.


## Settore CIVILE (dal 5 agosto 2026)

Il repository non è più solo penale. Le pronunce civili segnalate dall'Ufficio del Massimario
(pagina "Giurisprudenza Civile", schede `SZC`) vivono in **`CIVILE/SEGNALATE/<anno>/`**, con lo
stesso formato di scheda, lo stesso indice e lo stesso manifest del settore penale.

```
SEGNALATE/            ← settore penale (invariato: i kit già installati continuano a funzionare)
CIVILE/SEGNALATE/     ← settore civile
CONSULTA/             ← Corte costituzionale, condivisa tra le due materie
```

La Corte costituzionale resta **una sola copia**: i suoi open data non sono segmentati per materia,
e duplicarli significherebbe far scaricare due volte lo stesso archivio agli utenti.

Il motore è lo stesso script, con `--materia penale|civile`:

```bash
python3 scripts/aggiorna_banca_dati.py --materia civile [--dry-run] [--backfill]
```

Differenze reali della fonte civile, gestite dal parser: intestazione con data numerica
(`Sentenza Numero: 24044, del 26/07/2026`), campo "Materia" su riga successiva, codici di
classificazione per materia separati dall'oggetto (campo `classificazione`), ordinanze
interlocutorie e decreti del Primo Presidente, e le pronunce **gemelle** pubblicate su un'unica
scheda (`Sentenze Nr. 23488 e Nr. 23489`) che generano una scheda sola con il campo
`numeri_collegati`. Nel civile **non esiste** l'equivalente delle questioni SU pendenti (`QSP`):
l'analogo funzionale sono i rinvii pregiudiziali ex art. 363-bis c.p.c. (prefisso `RPC`), non
ancora acquisiti.

### Rinvii pregiudiziali ex art. 363-bis c.p.c. (`CIVILE/RPC/`)

Nel civile non esiste l'equivalente delle questioni SU pendenti del penale: l'analogo funzionale e'
il **rinvio pregiudiziale**, con cui il giudice di merito sospende il giudizio e rimette alla Corte
una questione di diritto nuova, di particolare importanza e seriale.

```bash
python3 scripts/rinvii_pregiudiziali.py [--dry-run] [--backfill]
```

Archivio iniziale: **103 schede** (2023: 30 · 2024: 32 · 2025: 31 · 2026: 10), zero quarantena.
Ogni scheda porta data dell'ordinanza, ufficio remittente, R.G. del giudizio a quo, materia e il
**PDF ufficiale dell'ordinanza di rimessione**. Il quesito integrale non e' esposto sulla pagina
della Corte e **non viene riassunto**: sta nel PDF, ed e' li' che va letto.

⚠️ Sono questioni **pendenti**: non si citano come precedente. La pagina della Corte raccoglie anche
rinvii provenienti da TAR, Corte dei conti e Corti di giustizia tributaria: l'ufficio remittente e'
sempre riportato nella scheda, senza inferenze sulla giurisdizione.

### Rassegne mensili civili (`CIVILE/RASSEGNE/`)

La parte **citabile** della Knowledge Base: le Rassegne mensili dell'Ufficio del Massimario, che
riportano le massime con il numero **Rv**. La Rassegna annuale consolida l'anno ma esce con 12-18
mesi di ritardo: senza le mensili la Knowledge Base invecchia in silenzio.

```bash
python3 scripts/rassegne_civili.py [--dry-run] [--da-anno 2025] [--max-nuove N]
```

La pipeline scarica il PDF, lo **converte in Markdown con marcatori di pagina**, genera l'indice
citazionale e **oscura i nominativi dei difensori** prima di pubblicare: l'utente riceve materiale
gia' pronto, senza dover convertire nulla in locale.

Due accorgimenti nati dai dati reali: il periodo si ricava **dal contenuto del PDF** e non dal nome
del file (la mensile di ottobre 2025 e' pubblicata come "OTTOBRE_2026"), e i link si leggono dalle
schede di dettaglio perche' i nomi non seguono uno schema (`rev.2`, `rev02`, un `mnesile` con refuso).
Default `--da-anno 2025`: le annate precedenti sono gia' coperte dalle Rassegne annuali e prenderle
due volte duplicherebbe le massime.

Archivio: **10 rassegne** (gennaio 2025 - febbraio 2026), **3.958 massime**.

### Radar civile (`CIVILE/RADAR/`)

`scripts/radar_civile.py` raccoglie titolo, data e link degli articoli di cinque riviste civilistiche
con feed verificato (Judicium, Il Diritto Processuale Civile, Diritto Bancario, Diritto.it, Ius in
Itinere). **Solo metadati, mai il testo**; le voci **non si citano negli atti**. Passo non bloccante.

Seed iniziale delle pronunce segnalate: **296 schede** (2023: 46 · 2024: 98 · 2025: 94 · 2026: 48), 4 in `_QUARANTENA`
per campi mancanti alla fonte o intestazioni fuori formato — mai completate a mano, mai inventate.

## Perimetro

**Incluso** — le pronunce che l'Ufficio del Massimario pubblica sulla pagina
["Giurisprudenza Penale"](https://www.cortedicassazione.it/it/giurisprudenza_penale.page)
del sito della Corte (3–5 a settimana, di rilievo nomofilattico):
sentenze e ordinanze di sezione segnalate, sentenze delle Sezioni Unite,
questioni rimesse alle Sezioni Unite (pendenti e decise).

**Escluso** — le circa 450 pronunce ordinarie settimanali non segnalate,
i provvedimenti di restituzione, il testo integrale dei provvedimenti
(linkato in ogni scheda, non copiato).

## Struttura

```
SEGNALATE/
├── 2026/                  ← una scheda per pronuncia, struttura piatta per anno
│   ├── Cass_23006_2026.md      (sentenze/ordinanze; prefisso SU_ per le Sezioni Unite)
│   └── QSP_9916_2026.md        (questioni SU; lo stato pendente/decisa è nel frontmatter)
├── INDICE.md              ← indice per materia + registro numero→scheda
├── RASSEGNE.md            ← link alle Rassegne mensili del Massimario
└── LOG_ERRORI.md          ← anomalie della pipeline (mai contenuti inventati)
```

Il formato delle schede è definito in [`SPEC_SCHEDA.md`](SPEC_SCHEDA.md).

## Corte costituzionale (open data ufficiale)

In `CONSULTA/` **tutte** le pronunce della Corte costituzionale dal 1956 a oggi (oltre 22.000), costruite dal
**servizio open data ufficiale** della Consulta ([dati.cortecostituzionale.it](https://dati.cortecostituzionale.it/),
licenza CC BY-SA 3.0, aggiornamento settimanale): per ogni pronuncia, **dispositivo
integrale**, **massime ufficiali** con i parametri normativi strutturati e link alla
scheda ufficiale. Le schede NON contengono epigrafe né testo integrale (riportano i
dati delle parti dei giudizi a quo): per il testo completo si segue il link.
Quando le massime di una pronuncia recente vengono pubblicate, la scheda si
aggiorna da sola alla run successiva.

Le decisioni che la Corte seleziona ogni anno nel proprio **Annuario** (la rassegna
ufficiale "Le decisioni dell'anno", pubblicata dal 2021) sono marcate nelle schede con i
campi frontmatter `annuario:` e `tema_annuario:` (voce tematica assegnata dalla Corte) e
con `★ Annuario (tema)` in `CONSULTA/INDICE_CONSULTA.md`. Dell'Annuario non viene copiato
alcun testo redazionale: solo il fatto della selezione, la voce tematica e il numero della
pronuncia (estratti persistiti in `CONSULTA/ANNUARIO/annuario_<anno>.json`; ogni edizione è
statica e viene letta una volta sola).

## Radar del merito (segnalazioni, non citazioni)

In `SEGNALATE/RADAR/RADAR_MERITO.md` la pipeline raccoglie ogni settimana le **segnalazioni
di giurisprudenza di merito e i contributi** pubblicati da riviste scientifiche open access
(v2: l'Osservatorio della giurisprudenza di merito di *Sistema Penale*, il feed di
*Giurisprudenza Penale* filtrato sul merito, e i feed integrali di *Diritto di Difesa* (UCPI),
*La Legislazione Penale*, *DisCrimen* e *Penale Diritto e Procedura*; v3: parser dedicato
per *Archivio Penale* — sezioni di giurisprudenza di legittimità, costituzionale, di merito
ed europea, più gli articoli open access; v4: parser dedicati per le riviste della
magistratura — *Giustizia Insieme*, aree tematiche penali, e *Questione Giustizia*,
categoria "giurisprudenza e documenti" con le Pillole di Sezioni Unite penali / CEDU / CGUE
più il tag diritto-penale).

Regole: si raccolgono **solo i fatti** — data, fonte, titolo, link — mai i contenuti redazionali,
che restano degli editori (Sistema Penale è CC BY-NC-ND). Il radar è **materiale informativo,
non citabile negli atti**: per usare un provvedimento segnalato, si apre il link, si scarica il
PDF del provvedimento (atto pubblico) e lo si ingerisce nella propria KB. Dedup per URL.

## Aggiornamento

Automatico, **settimanale**, via GitHub Action (in attivazione — vedi roadmap).
Ogni scheda riporta nel frontmatter la data di estrazione (`estratto_il`).
Principio vincolante: se la fonte non risponde o la struttura della pagina è cambiata,
la pipeline **non inventa nulla** — registra l'anomalia in `LOG_ERRORI.md` e si ferma.

## Regole dei dati

- Ogni campo proviene dalla pagina ufficiale della Corte ed è copiato **testualmente**;
  un campo assente alla fonte resta `null`, mai completato.
- **Nessun dato personale delle parti** (minimizzazione): il campo "Ricorrente" esposto
  dalla Corte non viene estratto. Presidente e relatore sì (magistrati nell'esercizio
  di funzione pubblica).
- Deduplicazione per chiave `(tipo, numero/R.G., anno)`; schede incomplete in quarantena,
  mai pubblicate.

## Uso con il Kit Penalista Italia

Questo repo è la sorgente dati del sistema di grounding giurisprudenziale del
[Kit Penalista Italia](https://github.com/Synthos-Logic/penalista-italia):
le schede si montano in `KNOWLEDGE_BASE/02_GIURISPRUDENZA/SEGNALATE/` e ogni citazione
prodotta dal kit porta il riferimento alla scheda e al PDF ufficiale (quote-then-claim).
Il repo resta comunque utilizzabile da chiunque, anche senza il kit.

## Note legali e licenze

- I testi dei provvedimenti e delle massime sono **atti ufficiali dello Stato**
  (art. 5 l. 633/1941): non soggetti a diritto d'autore. La fonte autentica è il sito
  della Corte di Cassazione, linkato in ogni scheda.
- **Schede e banca dati**: licenza [CC BY 4.0](LICENSE-SCHEDE.md) — riuso libero con attribuzione.
- **Script**: licenza [MIT](LICENSE).
- Materiale di lavoro professionale: la verifica finale sulla fonte ufficiale resta
  responsabilità del professionista.

## Roadmap

- [x] Specifica del formato scheda + prime schede validate
- [x] Pipeline di estrazione (`scripts/aggiorna_banca_dati.py`)
- [x] GitHub Action settimanale (`.github/workflows/aggiorna.yml`) — verifica mensile Rassegne: prossima
- [x] Radar del merito dalle riviste open access (`SEGNALATE/RADAR/`)
- [x] Backfill dello storico completo (295 schede: sentenze dal 2024, questioni SU dal 2023)
- [x] Fonte Corte costituzionale via open data ufficiale (`CONSULTA/`, archivio completo 1956-oggi: 22.357 pronunce con dispositivi e massime)
- [ ] Repo gemello per il civile (stessa specifica)
