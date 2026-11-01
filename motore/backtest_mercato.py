"""Backtest: quanto pesare il mercato rispetto al modello (stagione 2025/26, walk-forward)."""
import pickle, numpy as np, pandas as pd
from concurrent.futures import ProcessPoolExecutor
from .dati import carica
from .modello import Modello
from .mercato import senza_margine, allinea
from .config import CAMPIONATI, BASE

def raccogli(da="2025-08-01", a="2026-06-30"):
    df, _ = carica()
    t = df[(df.data >= da) & (df.data <= a) & df.comp.isin(list(CAMPIONATI)) & df.q1.notna() & df.qo25.notna()]
    R = []
    for _, b in t.groupby(t.data.dt.to_period("W-SUN")):
        m = Modello(emivita=400, ridge=2).fit(df, b.data.min().normalize())
        for r in b.itertuples():
            lh, la = m.lambdas(r.casa, r.ospite, r.comp)
            R.append(dict(comp=r.comp, gc=r.gc, go=r.go, lh=lh, la=la, rho=m.rho,
                          mk=senza_margine(r.q1, r.qx, r.q2), mo=senza_margine(r.qo25, r.qu25)[0],
                          mkc=senza_margine(r.q1c, r.qxc, r.q2c)))
    return R

class _M:  # matrice Dixon-Coles con rho fisso (per i processi paralleli)
    def __init__(s, rho): s.rho = rho
    def matrice(s, lh, la, n=11): return Modello.matrice(s, lh, la, n)

def _valuta(args):
    r, w1, wo = args
    m = _M(r["rho"]); M = m.matrice(r["lh"], r["la"]); i, j = np.indices(M.shape)
    pm = np.array([M[i > j].sum(), M[i == j].sum(), M[i < j].sum()]); om = M[(i + j) > 2.5].sum()
    t = w1 * r["mk"] + (1 - w1) * pm; to = wo * r["mo"] + (1 - wo) * om
    a, b = allinea(m, r["lh"], r["la"], t, (2.5, to)) if (w1 or wo) else (r["lh"], r["la"])
    M2 = m.matrice(a, b); gc, go = int(min(r["gc"], 10)), int(min(r["go"], 10))
    return float(M2[gc, go])

if __name__ == "__main__":
    f = BASE / "output" / "bt_mercato.pkl"
    R = pickle.load(open(f, "rb")) if f.exists() else raccogli()
    pickle.dump(R, open(f, "wb"))
    y = np.array([0 if r["gc"] > r["go"] else 1 if r["gc"] == r["go"] else 2 for r in R])
    ov = np.array([(r["gc"] + r["go"]) > 2.5 for r in R])
    M = []
    for r in R:
        Mx = _M(r["rho"]).matrice(r["lh"], r["la"]); i, j = np.indices(Mx.shape)
        M.append((np.array([Mx[i > j].sum(), Mx[i == j].sum(), Mx[i < j].sum()]), Mx[(i + j) > 2.5].sum()))
    pm = np.array([m[0] for m in M]); om = np.array([m[1] for m in M])
    mk = np.array([r["mk"] for r in R]); mo = np.array([r["mo"] for r in R])
    print("partite", len(R))
    for w in [0, .3, .5, .6, .7, .8, .9, 1]:
        p = w * mk + (1 - w) * pm; o = w * mo + (1 - w) * om
        ll = -np.mean(np.log(p[np.arange(len(y)), y])); llo = -np.mean(np.log(np.where(ov, o, 1 - o)))
        print(f"w={w:.1f}  logloss 1X2={ll:.4f}  O/U2.5={llo:.4f}")
    for w in [0, .9]:
        with ProcessPoolExecutor(8) as ex:
            ps = list(ex.map(_valuta, [(r, w, w) for r in R], chunksize=50))
        print(f"risultato esatto w={w}: logloss={-np.mean(np.log(ps)):.4f}")
