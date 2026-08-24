# LOG ERRORI — pipeline di aggiornamento

> Qui la pipeline registra anomalie (fonte non raggiungibile, struttura HTML cambiata, campi mancanti). Regola: mai contenuti inventati — in caso di anomalia si logga e ci si ferma.

- 2026-07-07 10:01 UTC — [radar] Sistema Penale: 415 Client Error: Unsupported Media Type for url: https://www.sistemapenale.it/it/osservatorio-giurisprudenza-di-merito

- 2026-07-07 10:56 UTC — SZP46536: scheda in quarantena — campi mancanti: url_pdf
- 2026-07-07 10:58 UTC — SZP42916: scheda in quarantena — campi mancanti: url_pdf
- 2026-07-07 10:58 UTC — SZP42192: scheda in quarantena — campi mancanti: url_pdf

- 2026-07-07 22:38 UTC — [radar] Sistema Penale: nessuna voce estratta: struttura pagina cambiata?

- 2026-08-03 10:05 UTC — SZP51691: scheda in quarantena — campi mancanti: oggetto

- 2026-08-03 10:10 UTC — [radar] La Legislazione Penale: HTTPSConnectionPool(host='www.lalegislazionepenale.eu', port=443): Max retries exceeded with url: /feed/ (Caused by ConnectTimeoutError(<HTTPSConnection(host='www.lalegislazionepenale.eu', port=443) at 0x7fc659e0bd70>, 'Connection to www.lalegislazionepenale.eu timed out. (connect timeout=60)'))

- 2026-08-10 08:04 UTC — SZP51691: scheda in quarantena — campi mancanti: oggetto

- 2026-08-17 07:16 UTC — SZP51691: scheda in quarantena — campi mancanti: oggetto

- 2026-08-17 07:22 UTC — [radar] La Legislazione Penale: HTTPSConnectionPool(host='www.lalegislazionepenale.eu', port=443): Max retries exceeded with url: /feed/ (Caused by ConnectTimeoutError(<HTTPSConnection(host='www.lalegislazionepenale.eu', port=443) at 0x7fc6756e50d0>, 'Connection to www.lalegislazionepenale.eu timed out. (connect timeout=60)'))

- 2026-08-24 07:20 UTC — SZP51691: scheda in quarantena — campi mancanti: oggetto

- 2026-08-24 07:24 UTC — [radar] DisCrimen: HTTPSConnectionPool(host='discrimen.it', port=443): Max retries exceeded with url: /feed/ (Caused by SSLError(SSLCertVerificationError(1, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: Hostname mismatch, certificate is not valid for 'discrimen.it'. (_ssl.c:1010)")))
