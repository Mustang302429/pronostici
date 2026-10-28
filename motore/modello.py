"""
Ramo 1 - Modello statistico (Poisson / Dixon-Coles con decadimento temporale).

Ogni squadra ha una forza d'attacco e una di difesa. Ogni campionato ha un
proprio livello, stimato grazie alle partite di coppa (che mettono a confronto
squadre di campionati diversi). Le partite recenti pesano di più.
"""
import numpy as np, pandas as pd
from scipy.optimize import minimize, minimize_scalar
from scipy.stats import poisson

class Modello:
    def __init__(self, emivita=240, ridge=4.0, peso_xg=0.4, max_giorni=1100):
        self.emivita, self.ridge, self.peso_xg, self.max_giorni = emivita, ridge, peso_xg, max_giorni

    # ---------- addestramento ----------
    def fit(self, df, al):
        al = pd.Timestamp(al)
        d = df[(df.data < al) & (df.data >= al - pd.Timedelta(days=self.max_giorni))].copy()
        eta = (al - d.data).dt.days.values
        w = 0.5 ** (eta / self.emivita)
        # gruppo (campionato) di appartenenza di ciascuna squadra = campionato più giocato nell'ultimo anno
        rec = d[(d.tipo == "lega") & (d.data >= al - pd.Timedelta(days=365))]
        app = pd.concat([rec[["casa", "comp", "data"]].rename(columns={"casa": "t"}),
                         rec[["ospite", "comp", "data"]].rename(columns={"ospite": "t"})])
        self.gruppo = app.groupby("t").comp.agg(lambda s: s.value_counts().index[0]).to_dict()
        squadre = sorted(set(d.casa) | set(d.ospite))
        for t in squadre: self.gruppo.setdefault(t, "ALTRO")
        gruppi = sorted(set(self.gruppo[t] for t in squadre))
        hfa_keys = sorted(set(d.loc[d.tipo == "lega", "comp"])) + ["COPPA"]
        self.squadre, self.gruppi, self.hfa_keys = squadre, gruppi, hfa_keys
        ti = {t: i for i, t in enumerate(squadre)}; gi = {g: i for i, g in enumerate(gruppi)}
        hi = {h: i for i, h in enumerate(hfa_keys)}
        h = d.casa.map(ti).values; a = d.ospite.map(ti).values
        gh = np.array([gi[self.gruppo[t]] for t in d.casa]); ga = np.array([gi[self.gruppo[t]] for t in d.ospite])
        hk = np.where(d.tipo == "lega", d.comp.map(hi).fillna(0).values, hi["COPPA"]).astype(int)
        neutro = d.neutro.fillna(False).astype(bool).values
        # obiettivo: gol, mescolati con gli xG quando disponibili
        yh = d.gc.values.astype(float); ya = d.go.values.astype(float)
        if self.peso_xg > 0 and "xgc" in d:
            m = d.xgc.notna().values & d.xgo.notna().values
            yh[m] = (1 - self.peso_xg) * yh[m] + self.peso_xg * d.xgc.values[m]
            ya[m] = (1 - self.peso_xg) * ya[m] + self.peso_xg * d.xgo.values[m]
        nT, nG, nH = len(squadre), len(gruppi), len(hfa_keys)
        sl = np.cumsum([0, 1, nH, nT, nT, nG, nG])
        lam = self.ridge

        def unpack(p):
            return [p[sl[i]:sl[i + 1]] for i in range(6)]

        def f(p):
            c, hfa, at, de, A, D = unpack(p)
            hf = np.where(neutro, 0.0, hfa[hk])
            eh = c[0] + hf + at[h] + A[gh] - de[a] - D[ga]
            ea = c[0] + at[a] + A[ga] - de[h] - D[gh]
            mh, ma = np.exp(eh), np.exp(ea)
            ll = np.sum(w * (yh * eh - mh + ya * ea - ma))
            pen = lam * (at @ at + de @ de) + 1e-3 * (A @ A + D @ D)
            rh, ra = w * (yh - mh), w * (ya - ma)
            g = np.zeros_like(p)
            g[0] = rh.sum() + ra.sum()
            g[sl[1]:sl[2]] = np.bincount(hk, weights=np.where(neutro, 0, rh), minlength=nH)
            g[sl[2]:sl[3]] = np.bincount(h, rh, nT) + np.bincount(a, ra, nT) - 2 * lam * at
            g[sl[3]:sl[4]] = -np.bincount(a, rh, nT) - np.bincount(h, ra, nT) - 2 * lam * de
            g[sl[4]:sl[5]] = np.bincount(gh, rh, nG) + np.bincount(ga, ra, nG) - 2e-3 * A
            g[sl[5]:sl[6]] = -np.bincount(ga, rh, nG) - np.bincount(gh, ra, nG) - 2e-3 * D
            return -(ll - pen), -g
        p0 = np.zeros(sl[-1]); p0[0] = np.log(1.3)
        r = minimize(f, p0, jac=True, method="L-BFGS-B", options={"maxiter": 2000})
        c, hfa, at, de, A, D = unpack(r.x)
        self.c, self.hfa = c[0], dict(zip(hfa_keys, hfa))
        self.att = dict(zip(squadre, at)); self.dif = dict(zip(squadre, de))
        self.A, self.D = dict(zip(gruppi, A)), dict(zip(gruppi, D))
        # correzione Dixon-Coles per i risultati bassi (0-0, 1-0, 0-1, 1-1)
        gH, gA = d.gc.values.astype(int), d.go.values.astype(int)
        lh = np.exp(c[0] + np.where(neutro, 0, hfa[hk]) + at[h] + A[gh] - de[a] - D[ga])
        la = np.exp(c[0] + at[a] + A[ga] - de[h] - D[gh])
        def nll(rho):
            t = np.ones(len(gH))
            m00 = (gH == 0) & (gA == 0); m10 = (gH == 1) & (gA == 0)
            m01 = (gH == 0) & (gA == 1); m11 = (gH == 1) & (gA == 1)
            t[m00] = 1 - lh[m00] * la[m00] * rho; t[m10] = 1 + la[m10] * rho
            t[m01] = 1 + lh[m01] * rho; t[m11] = 1 - rho
            return -np.sum(w * np.log(np.clip(t, 1e-9, None)))
        self.rho = minimize_scalar(nll, bounds=(-0.25, 0.25), method="bounded").x
        self.n_partite = len(d)
        return self

    # ---------- previsione ----------
    def lambdas(self, casa, ospite, comp, neutro=False):
        gc_, go_ = self.gruppo.get(casa, "ALTRO"), self.gruppo.get(ospite, "ALTRO")
        hf = 0.0 if neutro else self.hfa.get(comp if comp in self.hfa else "COPPA", self.hfa["COPPA"])
        Ah, Dh = self.A.get(gc_, self.A.get("ALTRO", 0)), self.D.get(gc_, self.D.get("ALTRO", 0))
        Aa, Da = self.A.get(go_, self.A.get("ALTRO", 0)), self.D.get(go_, self.D.get("ALTRO", 0))
        lh = np.exp(self.c + hf + self.att.get(casa, 0) + Ah - self.dif.get(ospite, 0) - Da)
        la = np.exp(self.c + self.att.get(ospite, 0) + Aa - self.dif.get(casa, 0) - Dh)
        return lh, la

    def matrice(self, lh, la, n=11):
        M = np.outer(poisson.pmf(np.arange(n), lh), poisson.pmf(np.arange(n), la))
        r = self.rho
        M[0, 0] *= 1 - lh * la * r; M[1, 0] *= 1 + la * r; M[0, 1] *= 1 + lh * r; M[1, 1] *= 1 - r
        return M / M.sum()

    def mercati(self, casa, ospite, comp, neutro=False, corr_casa=1.0, corr_ospite=1.0):
        lh, la = self.lambdas(casa, ospite, comp, neutro)
        lh, la = lh * corr_casa, la * corr_ospite
        M = self.matrice(lh, la); i, j = np.indices(M.shape); tot = i + j
        p = {"xG_casa": lh, "xG_ospite": la,
             "1": M[i > j].sum(), "X": M[i == j].sum(), "2": M[i < j].sum()}
        p["1X"], p["X2"], p["12"] = p["1"] + p["X"], p["X"] + p["2"], p["1"] + p["2"]
        for s in (1.5, 2.5, 3.5):
            p[f"Over {s}"] = M[tot > s].sum(); p[f"Under {s}"] = 1 - p[f"Over {s}"]
        p["Gol"] = M[(i > 0) & (j > 0)].sum(); p["NoGol"] = 1 - p["Gol"]
        flat = sorted(((M[a, b], f"{a}-{b}") for a in range(6) for b in range(6)), reverse=True)[:3]
        p["Risultati probabili"] = ", ".join(f"{s} ({q:.0%})" for q, s in flat)
        p["affidabilita"] = self.affidabilita(casa, ospite)
        return p

    def affidabilita(self, casa, ospite):
        """Quanto conosciamo le squadre: ALTA se entrambe hanno storico nei campionati coperti."""
        noti = [self.gruppo.get(t, "ALTRO") != "ALTRO" for t in (casa, ospite)]
        return "ALTA" if all(noti) else ("MEDIA" if any(noti) else "BASSA")
