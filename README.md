# Sistema Pronostici – Ramo 1 (statistica) + Ramo 2 (presente)

Analizza lo storico di 8 campionati (Premier, Liga, Serie A, Bundesliga, Ligue 1,
Belgio, Olanda, Portogallo) e di Champions, Europa e Conference League, e
restituisce per ogni partita dei prossimi 11 giorni le probabilità di 1X2,
doppia chance, Over/Under, Gol/NoGol e i risultati esatti più probabili.
Tutto gratuito.

## Ramo 2 – il presente (FotMob, gratuito)
Per ogni partita legge infortuni, squalifiche e formazioni probabili/ufficiali.
Ogni giocatore pesa in base al valore di mercato (radice quadrata) e al voto
stagionale. Si confronta la migliore formazione possibile con quella che andrà
in campo: meno qualità in attacco = meno gol attesi; meno qualità in difesa =
più gol attesi per l'avversario. Correzione massima ±25%. La formazione
probabile pesa al 50%, quella ufficiale al 100%.

## Archivio e verifica
Ogni esecuzione salva i pronostici in `dati/archivio_pronostici.csv`. Dopo le
partite, il foglio "Verifica pronostici" confronta Ramo 1 e Ramo 2 con i
risultati reali.

## Avvio (Windows)
1. Installa Python 3.11+ da python.org (spunta "Add to PATH").
2. Doppio clic su `INSTALLA.bat` (oppure `py -m pip install -r requirements.txt`).
3. Doppio clic su `AGGIORNA.bat` (oppure `py -m motore.genera`).
4. Il report Excel compare in `output/`.

Backtest (verifica affidabilità): `py -m motore.backtest`

## Fonti gratuite
- football-data.co.uk: risultati dal 2022, xG (stagione corrente), quote medie.
- ESPN (API pubblica): calendario reale e partite delle coppe europee.
- Campionati di supporto (Scozia, Turchia, Grecia, Austria, Svizzera, Danimarca,
  Norvegia, Svezia, Polonia, Romania, serie B dei top 5): usati SOLO per
  valutare la forza delle squadre estere e delle neopromosse.

## Modello
Poisson / Dixon-Coles: ogni squadra ha forza d'attacco e di difesa, le partite
recenti pesano di più (emivita 400 giorni), ogni campionato ha un proprio
livello stimato dagli scontri nelle coppe europee, vantaggio campo per
competizione. Gli xG, quando presenti, pesano il 40%.

## File
- motore/scarica.py     download dati
- motore/nomi.py        collegamento nomi squadre tra fonti
- motore/modello.py     modello statistico
- motore/contesto.py    forma, medie gol, % Over, precedenti
- motore/calendario.py  prossime partite reali
- motore/backtest.py    verifica sulla stagione 2025/26
- motore/presente.py    ramo 2: assenze e formazioni
- motore/archivio.py    archivio e verifica
- motore/genera.py      report Excel

## Web app online
La cartella `docs/` contiene la web app (index.html + data.json). Su GitHub il
file `.github/workflows/aggiorna.yml` la rigenera e pubblica 3 volte al giorno.
Istruzioni passo passo: GUIDA_GITHUB.md
