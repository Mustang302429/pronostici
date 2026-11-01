"""Backtest walk-forward dei mercati aggiuntivi (primo/secondo tempo, cartellini)."""
import json, numpy as np, pandas as pd
from .dati import carica
from .modello import Modello
from .extra import Tempi, Cartellini, Corner, Tiri, TiriPorta
from .gruppi import gruppi
from .config import CAMPIONATI, BASE

MERC = ["1T Over 0.5", "1T Over 1.5", "1T X", "2T Over 0.5", "2T Over 1.5", "Gialli Over 3.5", "Gialli Over 4.5", "Gialli Over 5.5",
        "Corner Over 8.5", "Corner Over 9.5", "Corner Over 10.5", "1X2 corner 1", "1X2 corner 2", "Corner casa Over 4.5",
        "Tiri Over 22.5", "Tiri Over 24.5", "Tiri Over 26.5", "Tiri in porta Over 7.5", "Tiri in porta Over 8.5", "1X2 tiri in porta 1",
        "Multigol 2-4", "Multigol 1-3", "ME4 0-0/1-1/0-1/1-0", "ME4 2-0/2-1/3-0/3-1", "Cluster 1-0/2-0/3-0", "Top3 esatti"]

def esegui(da="2025-08-01", a="2026-06-30"):
    df, _ = carica()
    test = df[(df.data >= da) & (df.data <= a) & df.comp.isin(list(CAMPIONATI)) & df.htc.notna() & df.gialli_c.notna() & df.corner_c.notna() & df.tip_c.notna()]
    rows = []
    for _, b in test.groupby(test.data.dt.to_period("W-SUN")):
        t0 = b.data.min().normalize()
        m = Modello(emivita=400, ridge=2).fit(df, t0); T = Tempi().fit(df, t0); C = Cartellini().fit(df, t0)
        K = Corner().fit(df, t0); S = Tiri().fit(df, t0); P = TiriPorta().fit(df, t0)
        for r in b.itertuples():
            p = m.mercati(r.casa, r.ospite, r.comp)
            e = {**T.mercati(p["xG_casa"], p["xG_ospite"], T.q(r.comp)), **C.mercati(r.casa, r.ospite, r.comp),
                 **K.mercati(r.casa, r.ospite, r.comp), **S.mercati(r.casa, r.ospite, r.comp), **P.mercati(r.casa, r.ospite, r.comp)}
            G = gruppi(p["_M"]); gp = lambda m, e: next(x["p"] for x in G[m] if x["esito"] == e)
            e.update({"Multigol 2-4": gp("Multigol", "Multigol 2-4"), "Multigol 1-3": gp("Multigol", "Multigol 1-3"),
                      "ME4 0-0/1-1/0-1/1-0": gp("Multi Esiti 4", "0-0/1-1/0-1/1-0"), "ME4 2-0/2-1/3-0/3-1": gp("Multi Esiti 4", "2-0/2-1/3-0/3-1"),
                      "Cluster 1-0/2-0/3-0": gp("Cluster risultati esatti", "1-0/2-0/3-0"), "Top3 esatti": G["Cluster personalizzato"][2]["p"]})
            ris = f"{int(r.gc)}-{int(r.go)}"; top3 = G["Cluster personalizzato"][2]["esito"].split("/")
            k, t, ct, cto = r.corner_c + r.corner_o, r.tiri_c + r.tiri_o, r.tip_c, r.tip_o; tg = r.gc + r.go
            g1, g2 = r.htc + r.hto, (r.gc + r.go) - (r.htc + r.hto); y = r.gialli_c + r.gialli_o
            real = {"1T Over 0.5": g1 > 0, "1T Over 1.5": g1 > 1, "1T X": r.htc == r.hto, "2T Over 0.5": g2 > 0,
                    "2T Over 1.5": g2 > 1, "Gialli Over 3.5": y > 3.5, "Gialli Over 4.5": y > 4.5, "Gialli Over 5.5": y > 5.5,
                    "Corner Over 8.5": k > 8.5, "Corner Over 9.5": k > 9.5, "Corner Over 10.5": k > 10.5, "1X2 corner 1": r.corner_c > r.corner_o,
                    "1X2 corner 2": r.corner_c < r.corner_o, "Corner casa Over 4.5": r.corner_c > 4.5, "Tiri Over 22.5": t > 22.5, "Tiri Over 24.5": t > 24.5,
                    "Tiri Over 26.5": t > 26.5, "Tiri in porta Over 7.5": ct + cto > 7.5, "Tiri in porta Over 8.5": ct + cto > 8.5, "1X2 tiri in porta 1": ct > cto,
                    "Multigol 2-4": 2 <= tg <= 4, "Multigol 1-3": 1 <= tg <= 3, "ME4 0-0/1-1/0-1/1-0": r.gc <= 1 and r.go <= 1,
                    "ME4 2-0/2-1/3-0/3-1": r.gc in (2, 3) and r.go in (0, 1), "Cluster 1-0/2-0/3-0": ris in ("1-0", "2-0", "3-0"), "Top3 esatti": ris in top3}
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
