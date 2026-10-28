"""Configurazione: campionati, coppe, stagioni, fonti gratuite."""
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "dati" / "raw"
DB = BASE / "dati" / "partite.csv"
OUT = BASE / "output"

# Campionati su cui produciamo pronostici (codici football-data.co.uk)
CAMPIONATI = {
    "E0": "Premier League", "SP1": "La Liga", "I1": "Serie A",
    "D1": "Bundesliga", "F1": "Ligue 1", "B1": "Jupiler Pro League (BEL)",
    "N1": "Eredivisie (NED)", "P1": "Primeira Liga (POR)",
}
# Campionati "di supporto": servono SOLO a valutare gli avversari esteri nelle coppe
SUPPORTO_MAIN = {"SC0": "Scozia", "T1": "Turchia", "G1": "Grecia",
                 "E1": "Championship", "SP2": "Segunda", "I2": "Serie B", "D2": "2. Bundesliga", "F2": "Ligue 2"}
SUPPORTO_EXTRA = {"AUT": "Austria", "SWZ": "Svizzera", "DNK": "Danimarca",
                  "NOR": "Norvegia", "SWE": "Svezia", "POL": "Polonia",
                  "ROU": "Romania"}
# Coppe europee (codici ESPN)
COPPE = {"uefa.champions": "Champions League", "uefa.europa": "Europa League",
         "uefa.europa.conf": "Conference League"}

STAGIONI = ["2223", "2324", "2425", "2526", "2627"]   # football-data
INIZIO_COPPE = (2022, 7)                              # ESPN, mese per mese
