"""
Risultati esatti a gruppi (mercati standard ADM, uguali su Sisal, Lottomatica, Snai...):
Multi Esiti 1-5, Cluster risultati esatti, Multigol. Le probabilità si sommano dalla
matrice dei risultati esatti (già allineata alle quote del mercato quando disponibili).
"""
import numpy as np

ME = {
 "Multi Esiti 1": ["0-0/1-1", "2-2/3-3/4-4", "1-0/2-0/2-1", "0-1/0-2/1-2", "3-0/3-1/3-2", "0-3/1-3/2-3",
                   "4-1/4-2/4-3", "1-4/2-4/3-4", "4-0/0-4/ALTRO"],
 "Multi Esiti 2": ["0-0/1-0", "2-0/3-0", "1-1/2-1", "3-1/3-2/2-2", "4-0/4-1", "4-2/4-3", "0-1/0-2", "1-2/0-3",
                   "1-3/2-3", "0-4/1-4", "2-4/3-4", "3-3/4-4/ALTRO"],
 "Multi Esiti 3": ["0-0/0-1", "0-2/0-3", "1-1/1-2", "1-3/2-3/2-2", "0-4/3-4", "1-4/2-4", "1-0/2-0", "3-0/2-1",
                   "3-1/3-2", "4-0/4-3", "4-1/4-2", "3-3/4-4/ALTRO"],
 "Multi Esiti 4": ["0-0/1-1/0-1/1-0", "2-0/2-1/3-0/3-1", "0-2/1-2/0-3/1-3", "2-2/2-3/3-2/3-3",
                   "4-0/4-1/4-2/4-3", "0-4/1-4/2-4/3-4", "4-4/ALTRO"],
 "Multi Esiti 5": ["0-0/1-0/0-1", "2-0/3-0/4-0", "0-2/0-3/0-4", "1-1/2-1/1-2/2-2", "3-1/3-2/4-1/4-2",
                   "1-3/2-3/1-4/2-4", "3-3/4-3/3-4/4-4/ALTRO"],
}
CLUSTER = ["1-0/2-0/3-0", "0-1/0-2/0-3", "4-0/5-0/6-0", "0-4/0-5/0-6", "2-1/3-1/4-1", "1-2/1-3/1-4",
           "3-2/4-2/4-3/5-1", "2-3/2-4/3-4/1-5", "1 ALTRO", "2 ALTRO", "X (pareggio)"]
MULTIGOL = [(1, 2), (1, 3), (1, 4), (1, 5), (2, 3), (2, 4), (2, 5), (2, 6), (3, 4), (3, 5), (3, 6), (4, 5), (4, 6)]


def _celle(txt):
    return [tuple(map(int, x.split("-"))) for x in txt.split("/") if x != "ALTRO"]


def gruppi(M):
    n = M.shape[0]; i, j = np.indices(M.shape); out = {}
    for mercato, esiti in ME.items():
        usati = set(c for e in esiti for c in _celle(e))
        r = []
        for e in esiti:
            p = sum(M[a, b] for a, b in _celle(e))
            if "ALTRO" in e: p += M.sum() - sum(M[a, b] for a, b in usati)
            r.append({"esito": e, "p": float(p)})
        out[mercato] = r
    r = []; usati = set(c for e in CLUSTER[:8] for c in _celle(e))
    for e in CLUSTER[:8]: r.append({"esito": e, "p": float(sum(M[a, b] for a, b in _celle(e)))})
    r.append({"esito": "1 ALTRO", "p": float(sum(M[a, b] for a in range(n) for b in range(n) if a > b and (a, b) not in usati))})
    r.append({"esito": "2 ALTRO", "p": float(sum(M[a, b] for a in range(n) for b in range(n) if a < b and (a, b) not in usati))})
    r.append({"esito": "X (pareggio)", "p": float(M[i == j].sum())})
    out["Cluster risultati esatti"] = r
    t = i + j
    out["Multigol"] = [{"esito": f"Multigol {a}-{b}", "p": float(M[(t >= a) & (t <= b)].sum())} for a, b in MULTIGOL] + \
                      [{"esito": "Multigol 7+", "p": float(M[t >= 7].sum())}]
    for nome, g in (("casa", i), ("ospite", j)):
        out[f"Multigol {nome}"] = [{"esito": f"Multigol {nome} {a}-{b}", "p": float(M[(g >= a) & (g <= b)].sum())}
                                   for a, b in ((1, 2), (1, 3), (2, 3), (1, 4), (2, 4))]
    # risultati esatti singoli più probabili e "cluster personalizzato" (i k più probabili insieme)
    flat = sorted(((float(M[a, b]), f"{a}-{b}") for a in range(min(n, 7)) for b in range(min(n, 7))), reverse=True)
    out["Esatti"] = [{"esito": r, "p": p} for p, r in flat[:12]]
    cum = 0; pers = []
    for k, (p, r) in enumerate(flat[:6], 1):
        cum += p; pers.append({"esito": "/".join(x[1] for x in flat[:k]), "p": cum, "k": k})
    out["Cluster personalizzato"] = pers
    return out
