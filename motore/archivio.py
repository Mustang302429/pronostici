"""Archivio dei pronostici e verifica automatica a partita giocata."""
import numpy as np, pandas as pd
from .config import BASE

ARCHIVIO = BASE / "dati" / "archivio_pronostici.csv"
CHIAVE = ["giorno", "comp", "casa", "ospite"]

def salva(righe):
    """righe: DataFrame con data, comp, casa, ospite (nomi interni) e probabilità R1/R2.
    Per ogni partita si tiene l'ULTIMO pronostico emesso prima del calcio d'inizio."""
    nuovo = righe.copy()
    nuovo["giorno"] = pd.to_datetime(nuovo.data).dt.strftime("%Y-%m-%d")
    nuovo["emesso"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
    if ARCHIVIO.exists():
        vecchio = pd.read_csv(ARCHIVIO)
        tutto = pd.concat([vecchio, nuovo], ignore_index=True)
    else:
        tutto = nuovo
    tutto = tutto.drop_duplicates(CHIAVE, keep="last")
    ARCHIVIO.parent.mkdir(parents=True, exist_ok=True)
    tutto.to_csv(ARCHIVIO, index=False)
    return len(tutto)

def verifica(risultati):
    """Confronta l'archivio con i risultati reali. Ritorna (dettaglio, riepilogo)."""
    if not ARCHIVIO.exists(): return None, None
    a = pd.read_csv(ARCHIVIO)
    r = risultati.copy(); r["giorno"] = pd.to_datetime(r.data).dt.strftime("%Y-%m-%d")
    d = a.merge(r[CHIAVE + ["gc", "go"]], on=CHIAVE, how="inner")
    if d.empty: return d, None
    d["esito"] = np.where(d.gc > d.go, "1", np.where(d.gc == d.go, "X", "2"))
    d["over25"] = (d.gc + d.go) > 2.5; d["gol"] = (d.gc > 0) & (d.go > 0)
    riep = []
    for ramo in ("R1", "R2"):
        P = d[[f"{ramo}_1", f"{ramo}_X", f"{ramo}_2"]].values
        y = np.stack([(d.esito == k).values for k in "1X2"], 1)
        riep.append({"Ramo": "1 - solo statistica" if ramo == "R1" else "2 - statistica + presente",
                     "Partite verificate": len(d),
                     "Favorito 1X2 indovinato": np.mean(P.argmax(1) == y.argmax(1)),
                     "Over/Under 2.5 indovinato": np.mean((d[f"{ramo}_O25"] > .5) == d.over25),
                     "Gol/NoGol indovinato": np.mean((d[f"{ramo}_GG"] > .5) == d.gol),
                     "Log-loss 1X2 (più basso = meglio)": -np.mean(np.log(np.clip((P * y).sum(1), 1e-9, 1)))})
    return d, pd.DataFrame(riep)
