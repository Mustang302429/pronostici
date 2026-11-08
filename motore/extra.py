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

# ---------------------------------------------------------------- conteggi (cartellini, corner, tiri)
class Conteggio:
    """Modello generico per statistiche "contabili" della partita (gialli, corner, tiri, tiri in porta).
    Per ogni squadra: quanto ne produce (own) e quanto ne concede/fa produrre all'avversario (prov),
    più un livello base per campionato e un effetto casa. Dispersione: binomiale negativa."""
    col = "gialli"; nome = "Gialli"
    linee_tot = (2.5, 3.5, 4.5, 5.5, 6.5); linee_sq = (0.5, 1.5, 2.5, 3.5)
    etichetta_1x2 = "1X2 ammonizioni"

    def __init__(self, emivita=400, ridge=3.0):
        self.emivita, self.ridge = emivita, ridge

    def fit(self, df, al, giorni=1100):
        al = pd.Timestamp(al); cc, co = self.col + "_c", self.col + "_o"
        d = df[(df.data < al) & (df.data >= al - pd.Timedelta(days=giorni)) & df[cc].notna() & df[co].notna() & (df.tipo == "lega")].copy()
        w = 0.5 ** ((al - d.data).dt.days.values / self.emivita)
        sq = sorted(set(d.casa) | set(d.ospite)); ti = {t: i for i, t in enumerate(sq)}
        comps = sorted(set(d.comp)); ci = {c: i for i, c in enumerate(comps)}
        h, a, c = d.casa.map(ti).values, d.ospite.map(ti).values, d.comp.map(ci).values
        yh, ya = d[cc].values.astype(float), d[co].values.astype(float)
        nT, nC = len(sq), len(comps); lam = self.ridge
        sl = np.cumsum([0, nC, 1, nT, nT])
        def f(p):
            base, hf, own, prov = p[sl[0]:sl[1]], p[sl[1]], p[sl[2]:sl[3]], p[sl[3]:sl[4]]
            eh = base[c] + own[h] + prov[a]          # valore della squadra di casa
            ea = base[c] + hf + own[a] + prov[h]     # valore della squadra ospite (+ effetto trasferta)
            mh, ma = np.exp(eh), np.exp(ea)
            ll = np.sum(w * (yh * eh - mh + ya * ea - ma)) - lam * (own @ own + prov @ prov)
            rh, ra = w * (yh - mh), w * (ya - ma); g = np.zeros_like(p)
            g[sl[0]:sl[1]] = np.bincount(c, rh + ra, nC); g[sl[1]] = ra.sum()
            g[sl[2]:sl[3]] = np.bincount(h, rh, nT) + np.bincount(a, ra, nT) - 2 * lam * own
            g[sl[3]:sl[4]] = np.bincount(a, rh, nT) + np.bincount(h, ra, nT) - 2 * lam * prov
            return -ll, -g
        p0 = np.zeros(sl[-1]); p0[:nC] = np.log(max(1.0, np.mean(yh)))
        p = minimize(f, p0, jac=True, method="L-BFGS-B").x
        self.base = dict(zip(comps, p[:nC])); self.hf = p[sl[1]]
        self.own = dict(zip(sq, p[sl[2]:sl[3]])); self.prov = dict(zip(sq, p[sl[3]:sl[4]]))
        mh = np.exp(p[:nC][c] + p[sl[2]:sl[3]][h] + p[sl[3]:sl[4]][a])
        ma = np.exp(p[:nC][c] + self.hf + p[sl[2]:sl[3]][a] + p[sl[3]:sl[4]][h])
        mu, y = mh + ma, yh + ya
        disp = lambda yy, m, ww: float(max(0.005, (np.average((yy - m) ** 2, weights=ww) - np.average(m, weights=ww)) / np.average(m ** 2, weights=ww)))
        self.alpha = disp(y, mu, w)
        self.alpha_sq = disp(np.r_[yh, ya], np.r_[mh, ma], np.r_[w, w])
        self._dopo_fit(d, mu)
        self.lega_squadra = pd.concat([d[["casa", "comp"]].rename(columns={"casa": "t"}),
                                       d[["ospite", "comp"]].rename(columns={"ospite": "t"})]).groupby("t").comp.last().to_dict()
        return self

    def _dopo_fit(self, d, mu): pass

    def _leghe(self, casa, ospite, comp):
        if comp in self.base: return [comp]
        cs = [self.lega_squadra.get(t) for t in (casa, ospite)]   # coppe: campionati delle due squadre
        return [x for x in cs if x in self.base] or list(self.base)

    def attesi(self, casa, ospite, comp):
        b = float(np.mean([self.base[x] for x in self._leghe(casa, ospite, comp)]))
        mh = np.exp(b + self.own.get(casa, 0) + self.prov.get(ospite, 0))
        ma = np.exp(b + self.hf + self.own.get(ospite, 0) + self.prov.get(casa, 0))
        return float(mh), float(ma)

    @staticmethod
    def _nb(mu, alpha, k):
        n = 1 / alpha; return nbinom.pmf(np.arange(k), n, n / (n + mu))

    def mercati(self, casa, ospite, comp):
        mh, ma = self.attesi(casa, ospite, comp); mu = mh + ma; N = self.nome
        n = 1 / self.alpha; pr = n / (n + mu); cdf = lambda k: nbinom.cdf(k, n, pr)
        out = {f"{N} attesi": mu, f"{N} casa attesi": mh, f"{N} ospite attesi": ma}
        for s in self.linee_tot:
            out[f"{N} Over {s}"] = 1 - cdf(int(s)); out[f"{N} Under {s}"] = cdf(int(s))
        for nome, m in (("casa", mh), ("ospite", ma)):
            n2 = 1 / self.alpha_sq; p2 = n2 / (n2 + m)
            for s in self.linee_sq:
                out[f"{N} {nome} Over {s}"] = 1 - nbinom.cdf(int(s), n2, p2)
                out[f"{N} {nome} Under {s}"] = nbinom.cdf(int(s), n2, p2)
        K = int(max(mh, ma) * 4 + 15)
        J = np.outer(self._nb(mh, self.alpha_sq, K), self._nb(ma, self.alpha_sq, K)); J /= J.sum()
        i, j = np.indices(J.shape)
        e = self.etichetta_1x2
        out[f"{e} 1"], out[f"{e} X"], out[f"{e} 2"] = J[i > j].sum(), J[i == j].sum(), J[i < j].sum()
        out[f"{e} 1X"] = out[f"{e} 1"] + out[f"{e} X"]; out[f"{e} X2"] = out[f"{e} X"] + out[f"{e} 2"]
        out[f"{e} 12"] = out[f"{e} 1"] + out[f"{e} 2"]
        return out


class Cartellini(Conteggio):
    def _dopo_fit(self, d, mu):
        d["mu"] = mu; d["rossi"] = (d.rossi_c.fillna(0) + d.rossi_o.fillna(0)) > 0
        g = d.groupby("comp").agg(r=("rossi", "mean"), m=("mu", "mean"))
        self.rossi = g.r.to_dict(); self.media_mu = g.m.to_dict()

    def mercati(self, casa, ospite, comp):
        out = super().mercati(casa, ospite, comp)
        cs = self._leghe(casa, ospite, comp)
        rr = float(np.mean([self.rossi[x] for x in cs])); mm = float(np.mean([self.media_mu[x] for x in cs]))
        # rossi: frequenza del campionato, scalata su quanto è "calda" la partita
        tasso = -np.log(1 - min(rr, 0.6)) * (out["Gialli attesi"] / mm)
        out["Almeno un rosso"] = 1 - np.exp(-tasso)
        return out


class Corner(Conteggio):
    col = "corner"; nome = "Corner"; etichetta_1x2 = "1X2 corner"
    linee_tot = (7.5, 8.5, 9.5, 10.5, 11.5); linee_sq = (2.5, 3.5, 4.5, 5.5, 6.5)
    def __init__(self, emivita=400, ridge=25.0): super().__init__(emivita, ridge)   # ridge alto: scelto col backtest

    # quota dei corner battuti nel 1° tempo (FotMob, 3.447 partite 2025/26 e 2026/27)
    QUOTA_1T = {"B1": 0.462, "D1": 0.453, "E0": 0.484, "F1": 0.467, "I1": 0.46, "N1": 0.474, "P1": 0.48, "SP1": 0.473}
    HANDICAP = ((1, 0), (0, 1), (2, 0), (0, 2))

    def _diff(self, mh, ma, K=40):
        """Distribuzione di (corner casa - corner ospite), indice spostato di K."""
        ph, pa = self._nb(mh, self.alpha_sq, K), self._nb(ma, self.alpha_sq, K)
        return np.convolve(ph, pa[::-1])          # posizione k -> differenza k-(K-1)

    def mercati_tempi(self, casa, ospite, comp):
        """1X2 corner 1° tempo, 1X2 handicap corner 1° tempo, parziale/finale corner."""
        mh, ma = self.attesi(casa, ospite, comp)
        cs = self._leghe(casa, ospite, comp)
        s = float(np.mean([self.QUOTA_1T.get(x, 0.47) for x in cs])); K = 40
        d1 = self._diff(mh * s, ma * s, K); d2 = self._diff(mh * (1 - s), ma * (1 - s), K)
        v = np.arange(len(d1)) - (K - 1)
        out = {"1T 1X2 corner 1": d1[v > 0].sum(), "1T 1X2 corner X": d1[v == 0].sum(), "1T 1X2 corner 2": d1[v < 0].sum(),
               "Corner 1T attesi": (mh + ma) * s}
        for hc, ho in self.HANDICAP:
            k = hc - ho; t = f"1T handicap corner ({hc}:{ho})"
            out[f"{t} 1"], out[f"{t} X"], out[f"{t} 2"] = d1[v + k > 0].sum(), d1[v + k == 0].sum(), d1[v + k < 0].sum()
        J = np.outer(d1, d2); a, b = np.meshgrid(v, v, indexing="ij"); ft = a + b
        seg = lambda x: np.where(x > 0, "1", np.where(x == 0, "X", "2"))
        S1, S2 = seg(a), seg(ft)
        for x in "1X2":
            for y in "1X2":
                out[f"Corner parziale/finale {x}/{y}"] = float(J[(S1 == x) & (S2 == y)].sum())
        return {k: float(val) for k, val in out.items()}


class Tiri(Conteggio):
    col = "tiri"; nome = "Tiri"; etichetta_1x2 = "1X2 tiri totali"
    linee_tot = (20.5, 22.5, 24.5, 26.5, 28.5); linee_sq = (8.5, 10.5, 12.5, 14.5)
    def __init__(self, emivita=200, ridge=3.0): super().__init__(emivita, ridge)


class TiriPorta(Conteggio):
    col = "tip"; nome = "Tiri in porta"; etichetta_1x2 = "1X2 tiri in porta"
    linee_tot = (6.5, 7.5, 8.5, 9.5, 10.5); linee_sq = (2.5, 3.5, 4.5, 5.5)
    def __init__(self, emivita=200, ridge=3.0): super().__init__(emivita, ridge)

# ---------------------------------------------------------------- combo
ESITI = ["1", "X", "2", "1X", "X2", "12"]
GOL = ["Over 1.5", "Over 2.5", "Under 2.5", "Under 3.5", "Gol", "NoGol"]

def combo(M):
    i, j = np.indices(M.shape); t = i + j
    E = {"1": i > j, "X": i == j, "2": i < j, "1X": i >= j, "X2": i <= j, "12": i != j}
    G = {"Over 1.5": t > 1.5, "Over 2.5": t > 2.5, "Under 2.5": t < 2.5, "Under 3.5": t < 3.5,
         "Gol": (i > 0) & (j > 0), "NoGol": (i == 0) | (j == 0)}
    out = {f"{e} + {g}": float(M[E[e] & G[g]].sum()) for e in ESITI for g in GOL}
    X = {"Gol + Over 2.5": G["Gol"] & G["Over 2.5"], "Gol + Over 3.5": G["Gol"] & (t > 3.5), "Gol + Under 3.5": G["Gol"] & G["Under 3.5"],
         "Gol + Under 4.5": G["Gol"] & (t < 4.5), "NoGol + Over 1.5": G["NoGol"] & G["Over 1.5"], "NoGol + Over 2.5": G["NoGol"] & G["Over 2.5"],
         "NoGol + Under 2.5": G["NoGol"] & G["Under 2.5"], "NoGol + Under 3.5": G["NoGol"] & G["Under 3.5"]}
    out.update({k: float(M[v].sum()) for k, v in X.items()})
    for e in ("1", "2", "1X", "X2"):
        out[f"{e} + Gol + Over 2.5"] = float(M[E[e] & G["Gol"] & G["Over 2.5"]].sum())
    return out
