"""
Mercati aggiuntivi:
- Primo e secondo tempo: i gol attesi della partita vengono divisi tra i due tempi
  secondo la quota storica di gol segnati nel primo tempo in quel campionato.
- Cartellini: modello Poisson (come per i gol) su quanti gialli prende ogni squadra
  e quanti ne fa prendere agli avversari, con dispersione stimata (binomiale negativa).
- Combo: probabilità congiunte calcolate dalla matrice dei risultati esatti
  (tengono conto della correlazione, es. 1X + Under 2.5).
"""
import numpy as np, pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson, nbinom

# ---------------------------------------------------------------- tempi
class Tempi:
    def fit(self, df, al, giorni=730):
        al = pd.Timestamp(al)
        d = df[(df.data < al) & (df.data >= al - pd.Timedelta(days=giorni)) & df.htc.notna()]
        g = d.groupby("comp")[["htc", "hto", "gc", "go"]].sum()
        quota = (g.htc + g.hto) / (g.gc + g.go)
        self.quota = quota.to_dict()
        tot = g.sum(); self.media = float((tot.htc + tot.hto) / (tot.gc + tot.go))
        return self

    def q(self, comp, comp_casa=None, comp_ospite=None):
        if comp in self.quota: return self.quota[comp]
        vals = [self.quota[c] for c in (comp_casa, comp_ospite) if c in self.quota]
        return float(np.mean(vals)) if vals else self.media

    @staticmethod
    def _mat(lh, la, n=8):
        return np.outer(poisson.pmf(np.arange(n), lh), poisson.pmf(np.arange(n), la))

    def mercati(self, lh, la, s):
        out = {}
        for nome, f in (("1T", s), ("2T", 1 - s)):
            M = self._mat(lh * f, la * f); i, j = np.indices(M.shape); t = i + j
            out[f"{nome} 1"], out[f"{nome} X"], out[f"{nome} 2"] = M[i > j].sum(), M[i == j].sum(), M[i < j].sum()
            out[f"{nome} 1X"] = out[f"{nome} 1"] + out[f"{nome} X"]; out[f"{nome} X2"] = out[f"{nome} X"] + out[f"{nome} 2"]
            out[f"{nome} Over 0.5"] = 1 - M[0, 0]; out[f"{nome} Under 0.5"] = M[0, 0]
            out[f"{nome} Over 1.5"] = M[t > 1.5].sum(); out[f"{nome} Under 1.5"] = 1 - out[f"{nome} Over 1.5"]
            out[f"{nome} Gol"] = M[(i > 0) & (j > 0)].sum()
            if nome == "1T":
                flat = sorted(((M[a, b], f"{a}-{b}") for a in range(4) for b in range(4)), reverse=True)[:3]
                out["1T risultati probabili"] = ", ".join(f"{r} ({p:.0%})" for p, r in flat)
        L = lh + la
        a = poisson.pmf(np.arange(12), L * s); b = poisson.pmf(np.arange(12), L * (1 - s))
        J = np.outer(a, b); i, j = np.indices(J.shape)
        out["Tempo più gol: 1°"] = J[i > j].sum(); out["Tempo più gol: 2°"] = J[i < j].sum(); out["Tempo più gol: pari"] = J[i == j].sum()
        return out

# ---------------------------------------------------------------- cartellini
class Cartellini:
    def __init__(self, emivita=400, ridge=3.0):
        self.emivita, self.ridge = emivita, ridge

    def fit(self, df, al, giorni=1100):
        al = pd.Timestamp(al)
        d = df[(df.data < al) & (df.data >= al - pd.Timedelta(days=giorni)) & df.gialli_c.notna() & (df.tipo == "lega")].copy()
        w = 0.5 ** ((al - d.data).dt.days.values / self.emivita)
        sq = sorted(set(d.casa) | set(d.ospite)); ti = {t: i for i, t in enumerate(sq)}
        comps = sorted(set(d.comp)); ci = {c: i for i, c in enumerate(comps)}
        h, a, c = d.casa.map(ti).values, d.ospite.map(ti).values, d.comp.map(ci).values
        yh, ya = d.gialli_c.values.astype(float), d.gialli_o.values.astype(float)
        nT, nC = len(sq), len(comps); lam = self.ridge
        sl = np.cumsum([0, nC, 1, nT, nT])
        def f(p):
            base, hf, own, prov = p[sl[0]:sl[1]], p[sl[1]], p[sl[2]:sl[3]], p[sl[3]:sl[4]]
            eh = base[c] + own[h] + prov[a]          # gialli alla squadra di casa
            ea = base[c] + hf + own[a] + prov[h]     # gialli alla squadra ospite (+ effetto trasferta)
            mh, ma = np.exp(eh), np.exp(ea)
            ll = np.sum(w * (yh * eh - mh + ya * ea - ma)) - lam * (own @ own + prov @ prov)
            rh, ra = w * (yh - mh), w * (ya - ma); g = np.zeros_like(p)
            g[sl[0]:sl[1]] = np.bincount(c, rh + ra, nC); g[sl[1]] = ra.sum()
            g[sl[2]:sl[3]] = np.bincount(h, rh, nT) + np.bincount(a, ra, nT) - 2 * lam * own
            g[sl[3]:sl[4]] = np.bincount(a, rh, nT) + np.bincount(h, ra, nT) - 2 * lam * prov
            return -ll, -g
        p0 = np.zeros(sl[-1]); p0[:nC] = np.log(2.0)
        r = minimize(f, p0, jac=True, method="L-BFGS-B")
        p = r.x
        self.base = dict(zip(comps, p[:nC])); self.hf = p[sl[1]]
        self.own = dict(zip(sq, p[sl[2]:sl[3]])); self.prov = dict(zip(sq, p[sl[3]:sl[4]]))
        # dispersione del totale (binomiale negativa) e frequenza dei rossi per campionato
        mh = np.exp(p[:nC][c] + p[sl[2]:sl[3]][h] + p[sl[3]:sl[4]][a])
        ma = np.exp(p[:nC][c] + self.hf + p[sl[2]:sl[3]][a] + p[sl[3]:sl[4]][h])
        mu, y = mh + ma, yh + ya
        self.alpha = float(max(0.01, (np.average((y - mu) ** 2, weights=w) - np.average(mu, weights=w)) / np.average(mu ** 2, weights=w)))
        d["mu"] = mu; d["rossi"] = (d.rossi_c.fillna(0) + d.rossi_o.fillna(0)) > 0
        g = d.groupby("comp").agg(r=("rossi", "mean"), m=("mu", "mean"))
        self.rossi = g.r.to_dict(); self.media_mu = g.m.to_dict()
        self.lega_squadra = pd.concat([d[["casa", "comp"]].rename(columns={"casa": "t"}),
                                       d[["ospite", "comp"]].rename(columns={"ospite": "t"})]).groupby("t").comp.last().to_dict()
        return self

    def mercati(self, casa, ospite, comp):
        if comp not in self.base:   # coppe: media dei campionati delle due squadre
            cs = [self.lega_squadra.get(t) for t in (casa, ospite)]
            cs = [x for x in cs if x in self.base] or list(self.base)
            b = float(np.mean([self.base[x] for x in cs])); rr = float(np.mean([self.rossi[x] for x in cs]))
            mm = float(np.mean([self.media_mu[x] for x in cs]))
        else:
            b, rr, mm = self.base[comp], self.rossi[comp], self.media_mu[comp]
        mh = np.exp(b + self.own.get(casa, 0) + self.prov.get(ospite, 0))
        ma = np.exp(b + self.hf + self.own.get(ospite, 0) + self.prov.get(casa, 0))
        mu = mh + ma
        n = 1 / self.alpha; pr = n / (n + mu)
        cdf = lambda k: nbinom.cdf(k, n, pr)
        out = {"Gialli attesi": mu, "Gialli casa attesi": mh, "Gialli ospite attesi": ma}
        for s in (3.5, 4.5, 5.5):
            out[f"Gialli Over {s}"] = 1 - cdf(int(s)); out[f"Gialli Under {s}"] = cdf(int(s))
        for nome, m in (("casa", mh), ("ospite", ma)):
            n2 = 1 / self.alpha; p2 = n2 / (n2 + m)
            out[f"Gialli {nome} Over 1.5"] = 1 - nbinom.cdf(1, n2, p2)
            out[f"Gialli {nome} Over 2.5"] = 1 - nbinom.cdf(2, n2, p2)
        # rossi: frequenza del campionato, scalata su quanto è "calda" la partita
        tasso = -np.log(1 - min(rr, 0.6)) * (mu / mm)
        out["Almeno un rosso"] = 1 - np.exp(-tasso)
        return out

# ---------------------------------------------------------------- combo
ESITI = ["1", "X", "2", "1X", "X2", "12"]
GOL = ["Over 1.5", "Over 2.5", "Under 2.5", "Under 3.5", "Gol", "NoGol"]

def combo(M):
    i, j = np.indices(M.shape); t = i + j
    E = {"1": i > j, "X": i == j, "2": i < j, "1X": i >= j, "X2": i <= j, "12": i != j}
    G = {"Over 1.5": t > 1.5, "Over 2.5": t > 2.5, "Under 2.5": t < 2.5, "Under 3.5": t < 3.5,
         "Gol": (i > 0) & (j > 0), "NoGol": (i == 0) | (j == 0)}
    out = {f"{e} + {g}": float(M[E[e] & G[g]].sum()) for e in ESITI for g in GOL}
    out["Gol + Over 2.5"] = float(M[G["Gol"] & G["Over 2.5"]].sum())
    out["NoGol + Under 2.5"] = float(M[G["NoGol"] & G["Under 2.5"]].sum())
    return out
