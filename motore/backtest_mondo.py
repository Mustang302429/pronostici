"""Backtest delle sezioni speciali: ogni partita prevista usando SOLO i dati precedenti (rifit ogni 14 giorni).
Confronto con la "media del campionato" (stessa probabilità per tutte le partite). Uso: py -m motore.backtest_mondo"""
import json, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from .config import BASE
from .modello import Modello
from .extra import Tempi
from .mondo import FILE, LEGHE, prepara

MERCATI = {"1X2": None, "Over 1.5": lambda d: d.gc + d.go > 1.5, "Over 2.5": lambda d: d.gc + d.go > 2.5,
           "1T Over 0.5": lambda d: d.htc + d.hto > 0.5}


def esegui(giorni=180, passo=14):
    df = pd.read_csv(FILE, parse_dates=["data"]); df["tipo"] = "lega"; df["neutro"] = df.neutro.fillna(False)
    g = df[df.gc.notna()].reset_index(drop=True)
    fine = g.data.max().normalize(); inizio = fine - pd.Timedelta(days=giorni)
    righe = []
    for t in pd.date_range(inizio, fine, freq=f"{passo}D"):
        m = Modello(emivita=400, ridge=2, peso_xg=0).fit(g, t); T = Tempi().fit(g, t)
        storia = g[(g.data < t) & (g.data >= t - pd.Timedelta(days=365))]
        base = storia.groupby("comp").apply(lambda d: pd.Series({
            "b1": (d.gc > d.go).mean(), "bX": (d.gc == d.go).mean(), "b2": (d.gc < d.go).mean(),
            "bO15": (d.gc + d.go > 1.5).mean(), "bO25": (d.gc + d.go > 2.5).mean(),
            "bT1": (d.htc + d.hto).dropna().gt(0.5).mean()}))
        b_o25 = base.bO25.to_dict()
        for r in g[(g.data >= t) & (g.data < t + pd.Timedelta(days=passo))].itertuples():
            if r.comp not in base.index: continue
            _, p = prepara(m, r, None, b_o25.get(r.comp))
            tt = T.mercati(p["xG_casa"], p["xG_ospite"], T.q(r.comp)); b = base.loc[r.comp]
            righe.append({"comp": r.comp, "esito": "1" if r.gc > r.go else ("X" if r.gc == r.go else "2"),
                          "p1": p["1"], "pX": p["X"], "p2": p["2"], "b1": b.b1, "bX": b.bX, "b2": b.b2,
                          "pO15": p["Over 1.5"], "bO15": b.bO15, "yO15": r.gc + r.go > 1.5,
                          "pO25": p["Over 2.5"], "bO25": b.bO25, "yO25": r.gc + r.go > 2.5,
                          "pT1": tt["1T Over 0.5"], "bT1": b.bT1, "yT1": (r.htc + r.hto > 0.5) if pd.notna(r.htc) else np.nan})
    return pd.DataFrame(righe)


def _brier(p, y): return float(np.mean((p - y) ** 2))


def riassunto(bt):
    out = {}
    def blocco(d):
        y = np.stack([(d.esito == k).values for k in "1X2"], 1).astype(float)
        P = d[["p1", "pX", "p2"]].values; B = d[["b1", "bX", "b2"]].values
        fav = P.argmax(1); conf = P.max(1)
        r = {"n": int(len(d)),
             "ll_modello": float(-np.mean(np.log(np.clip((P * y).sum(1), 1e-9, 1)))),
             "ll_media": float(-np.mean(np.log(np.clip((B * y).sum(1), 1e-9, 1)))),
             "favorito": float((y[np.arange(len(d)), fav] == 1).mean()),
             "fav60_n": int((conf >= 0.6).sum()), "fav60": float((y[np.arange(len(d)), fav][conf >= 0.6] == 1).mean()) if (conf >= 0.6).sum() else None}
        for k, (pc, bc, yc) in {"O15": ("pO15", "bO15", "yO15"), "O25": ("pO25", "bO25", "yO25"), "T1": ("pT1", "bT1", "yT1")}.items():
            e = d[d[yc].notna()]; yy = e[yc].astype(float)
            r[f"{k}_brier_mod"] = _brier(e[pc], yy); r[f"{k}_brier_media"] = _brier(e[bc], yy)
            alto = e[e[pc] >= 0.7]
            r[f"{k}_sopra70_n"] = int(len(alto)); r[f"{k}_sopra70_prev"] = float(alto[pc].mean()) if len(alto) else None
            r[f"{k}_sopra70_reale"] = float(alto[yc].astype(float).mean()) if len(alto) else None
        return r
    out["tutti"] = blocco(bt)
    for c, d in bt.groupby("comp"):
        if len(d) >= 40: out[c] = blocco(d)
    return out


if __name__ == "__main__":
    bt = esegui(); r = riassunto(bt)
    (BASE / "dati" / "backtest_mondo.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    t = r["tutti"]; print(json.dumps(t, indent=1))
