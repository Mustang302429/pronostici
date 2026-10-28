"""Backtest walk-forward: il modello prevede ogni partita usando SOLO i dati precedenti."""
import numpy as np, pandas as pd
from .dati import carica
from .modello import Modello
from .config import CAMPIONATI, COPPE

def esegui(da="2025-08-01", a="2026-06-30", **kw):
    df, _ = carica()
    test = df[(df.data >= da) & (df.data <= a) & (df.comp.isin(list(CAMPIONATI) + list(COPPE)))]
    righe = []
    for lun, blocco in test.groupby(test.data.dt.to_period("W-SUN")):
        m = Modello(**kw).fit(df, blocco.data.min().normalize())
        for _, r in blocco.iterrows():
            p = m.mercati(r.casa, r.ospite, r.comp, bool(r.neutro))
            esito = "1" if r.gc > r.go else ("X" if r.gc == r.go else "2")
            righe.append({**r.to_dict(), **{k: p[k] for k in ["1", "X", "2", "Over 2.5", "Gol", "affidabilita"]},
                          "esito": esito, "over": (r.gc + r.go) > 2.5, "gg": (r.gc > 0) & (r.go > 0)})
    return pd.DataFrame(righe)

def metriche(bt):
    out = {}
    y = np.stack([(bt.esito == k).values for k in "1X2"], 1).astype(float)
    P = bt[["1", "X", "2"]].values
    out["partite"] = len(bt)
    out["logloss_1X2_modello"] = -np.mean(np.log(np.sum(P * y, 1)))
    out["brier_1X2_modello"] = np.mean(np.sum((P - y) ** 2, 1))
    q = bt[["q1c", "qxc", "q2c"]].copy()
    q = q.fillna(bt[["q1", "qx", "q2"]].rename(columns={"q1": "q1c", "qx": "qxc", "q2": "q2c"}))
    ok = q.notna().all(1).values
    if ok.any():
        imp = 1 / q.values[ok]; imp /= imp.sum(1, keepdims=True)
        out["partite_con_quote"] = int(ok.sum())
        out["logloss_1X2_modello_(stesse partite)"] = -np.mean(np.log(np.sum(P[ok] * y[ok], 1)))
        out["logloss_1X2_bookmaker"] = -np.mean(np.log(np.sum(imp * y[ok], 1)))
    out["accuratezza_favorito"] = np.mean(np.argmax(P, 1) == np.argmax(y, 1))
    po = bt["Over 2.5"].values; yo = bt.over.values.astype(float)
    out["brier_over25"] = np.mean((po - yo) ** 2)
    out["accuratezza_over25"] = np.mean((po > .5) == yo)
    pg = bt["Gol"].values; yg = bt.gg.values.astype(float)
    out["accuratezza_GG/NG"] = np.mean((pg > .5) == yg)
    return out

def calibrazione(bt):
    """Quando il modello dice 70%, succede davvero il 70% delle volte?"""
    rows = []
    for k in "1X2":
        rows.append(pd.DataFrame({"p": bt[k], "y": (bt.esito == k).astype(float)}))
    rows.append(pd.DataFrame({"p": bt["Over 2.5"], "y": bt.over.astype(float)}))
    rows.append(pd.DataFrame({"p": 1 - bt["Over 2.5"], "y": 1 - bt.over.astype(float)}))
    d = pd.concat(rows)
    d["fascia"] = pd.cut(d.p, [0, .2, .3, .4, .5, .6, .7, .8, 1.0])
    return d.groupby("fascia", observed=True).agg(previsto=("p", "mean"), reale=("y", "mean"), n=("y", "size"))

if __name__ == "__main__":
    from .config import OUT
    bt = esegui(emivita=400, ridge=2)
    bt.to_csv(OUT / "backtest_2025_26.csv", index=False)
    for k, v in metriche(bt).items(): print(f"{k}: {v:.4f}" if isinstance(v, float) else f"{k}: {v}")
    print(calibrazione(bt).round(3))
