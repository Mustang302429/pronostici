"""Unisce campionati e coppe in un'unica tabella con nomi squadra coerenti."""
import pandas as pd
from .config import RAW, CAMPIONATI
from .nomi import mappa

def carica():
    c = pd.read_csv(RAW / "campionati.csv", parse_dates=["data"])
    c["tipo"] = "lega"; c["neutro"] = False
    k = pd.read_csv(RAW / "coppe.csv", parse_dates=["data"])
    nomi_fd = set(c.casa) | set(c.ospite)
    m = mappa(sorted(set(k.casa) | set(k.ospite)), nomi_fd)
    k["casa"] = k.casa.map(lambda x: m.get(x) or x)
    k["ospite"] = k.ospite.map(lambda x: m.get(x) or x)
    k["tipo"] = "coppa"
    k["neutro"] = k["neutro"].fillna(False).astype(bool)
    giocate = k[k.gc.notna()].copy()
    future = k[k.gc.isna()].copy()
    tutto = pd.concat([c, giocate], ignore_index=True).sort_values("data").reset_index(drop=True)
    return tutto, future
