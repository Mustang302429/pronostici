"""Backtest walk-forward dei mercati aggiuntivi (primo/secondo tempo, cartellini)."""
import json, numpy as np, pandas as pd
from .dati import carica
from .modello import Modello
from .extra import Tempi, Cartellini
from .config import CAMPIONATI, BASE

MERC = ["1T Over 0.5", "1T Over 1.5", "1T X", "2T Over 0.5", "2T Over 1.5", "Gialli Over 3.5", "Gialli Over 4.5", "Gialli Over 5.5"]

def esegui(da="2025-08-01", a="2026-06-30"):
    df, _ = carica()
    test = df[(df.data >= da) & (df.data <= a) & df.comp.isin(list(CAMPIONATI)) & df.htc.notna() & df.gialli_c.notna()]
    rows = []
    for _, b in test.groupby(test.data.dt.to_period("W-SUN")):
        t0 = b.data.min().normalize()
        m = Modello(emivita=400, ridge=2).fit(df, t0); T = Tempi().fit(df, t0); C = Cartellini().fit(df, t0)
        for r in b.itertuples():
            p = m.mercati(r.casa, r.ospite, r.comp)
            e = {**T.mercati(p["xG_casa"], p["xG_ospite"], T.q(r.comp)), **C.mercati(r.casa, r.ospite, r.comp)}
            g1, g2 = r.htc + r.hto, (r.gc + r.go) - (r.htc + r.hto); y = r.gialli_c + r.gialli_o
            real = {"1T Over 0.5": g1 > 0, "1T Over 1.5": g1 > 1, "1T X": r.htc == r.hto, "2T Over 0.5": g2 > 0,
                    "2T Over 1.5": g2 > 1, "Gialli Over 3.5": y > 3.5, "Gialli Over 4.5": y > 4.5, "Gialli Over 5.5": y > 5.5}
            rows += [{"mercato": k, "p": float(e[k]), "y": float(real[k])} for k in MERC]
    return pd.DataFrame(rows)

def riepilogo(bt):
    out = {}
    for k, g in bt.groupby("mercato"):
        base = g.y.mean()
        out[k] = {"partite": len(g), "frequenza_reale": base, "previsto_medio": g.p.mean(),
                  "brier_modello": float(np.mean((g.p - g.y) ** 2)), "brier_media_fissa": float(np.mean((base - g.y) ** 2)),
                  "accuratezza": float(np.mean((g.p > .5) == (g.y > .5))),
                  "calibrazione": [{"fascia": str(f), "previsto": float(x.p.mean()), "reale": float(x.y.mean()), "n": len(x)}
                                   for f, x in g.groupby(pd.cut(g.p, [0, .2, .35, .5, .65, .8, 1]), observed=True)]}
    return out

if __name__ == "__main__":
    bt = esegui(); r = riepilogo(bt)
    (BASE / "dati" / "backtest_extra.json").write_text(json.dumps(r), encoding="utf-8")
    for k, v in r.items():
        print(f"{k:16s} n={v['partite']} reale={v['frequenza_reale']:.3f} prev={v['previsto_medio']:.3f} "
              f"brier={v['brier_modello']:.4f} vs fisso={v['brier_media_fissa']:.4f} acc={v['accuratezza']:.3f}")
        print("   ", [(c['fascia'], round(c['previsto'], 2), round(c['reale'], 2), c['n']) for c in v['calibrazione']])
