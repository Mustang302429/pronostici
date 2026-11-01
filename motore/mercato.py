"""
Quote dei bookmaker e allineamento del modello al mercato.

- Quote gratuite: DraftKings via ESPN (copre campionati e coppe, anche giorni prima)
  + media bookmaker di football-data (campionati, dal venerdì/martedì).
- Le quote vengono "pulite" dal margine del bookmaker (somma delle probabilità = 100%).
- Il modello e il mercato vengono mescolati (peso stimato nel backtest), poi si cercano i
  gol attesi di casa e ospite che riproducono quelle probabilità: così TUTTI i mercati
  (risultati esatti, gruppi, tempi, combo) diventano coerenti tra loro e con le quote.
  Esempio: una X2 non potrà mai avere una quota equa più alta del solo 2.
"""
import numpy as np, requests
from concurrent.futures import ThreadPoolExecutor
from scipy.optimize import minimize

# peso del mercato nella media modello/mercato (stimato con backtest_mercato.py, stagione 2025/26)
PESO_MERCATO_1X2 = 0.9
PESO_MERCATO_OU = 0.9


def americana(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    if x == 0: return None
    return 1 + x / 100 if x > 0 else 1 + 100 / abs(x)


def senza_margine(*quote):
    if any(q is None or not np.isfinite(q) or q <= 1 for q in quote): return None
    inv = np.array([1 / q for q in quote]); return inv / inv.sum()


def _espn_una(args):
    lega, eid = args
    try:
        j = requests.get(f"https://sports.core.api.espn.com/v2/sports/soccer/leagues/{lega}/events/{eid}/competitions/{eid}/odds",
                         timeout=15).json()
    except Exception:
        return eid, None
    for it in j.get("items", []) or []:
        h, a = it.get("homeTeamOdds") or {}, it.get("awayTeamOdds") or {}
        q1, q2 = americana(h.get("moneyLine")), americana(a.get("moneyLine"))
        qx = americana((it.get("drawOdds") or {}).get("moneyLine"))
        out = {"q1": q1, "qx": qx, "q2": q2, "fonte_quote": it.get("provider", {}).get("name", "ESPN")}
        if it.get("overUnder") is not None:
            out.update(linea=float(it["overUnder"]), qover=americana(it.get("overOdds")), qunder=americana(it.get("underOdds")))
        if q1 and qx and q2: return eid, out
    return eid, None


def quote_espn(cal, leghe):
    """cal con colonne comp, id (ESPN). Ritorna {id: quote}."""
    jobs = [(leghe[c], i) for c, i in zip(cal.comp, cal.id) if c in leghe]
    with ThreadPoolExecutor(8) as ex:
        return {i: q for i, q in ex.map(_espn_una, jobs) if q}


def _prob(M):
    i, j = np.indices(M.shape)
    return M, i, j


def allinea(modello, lh, la, t1x2=None, tou=None):
    """Trova (lh, la) vicini a quelli del modello che riproducono le probabilità obiettivo.
    t1x2 = array [p1, px, p2]; tou = (linea, p_over)."""
    if t1x2 is None and tou is None: return lh, la

    def err(x):
        a, b = np.exp(x)
        M = modello.matrice(a, b); i, j = np.indices(M.shape)
        e = 0.0
        if t1x2 is not None:
            p = np.array([M[i > j].sum(), M[i == j].sum(), M[i < j].sum()])
            e += np.sum((p - t1x2) ** 2)
        if tou is not None:
            e += (M[(i + j) > tou[0]].sum() - tou[1]) ** 2
        # piccolo ancoraggio ai valori del modello (evita soluzioni strane)
        return e + 1e-4 * np.sum((x - np.log([lh, la])) ** 2)

    r = minimize(err, np.log([lh, la]), method="Nelder-Mead", options={"xatol": 1e-4, "fatol": 1e-9, "maxiter": 400})
    a, b = np.exp(r.x)
    return float(a), float(b)


def obiettivi(p_mod, quote, w1=PESO_MERCATO_1X2, wo=PESO_MERCATO_OU):
    """Probabilità obiettivo = media pesata modello / mercato (senza margine)."""
    t1x2 = tou = None
    if quote:
        m = senza_margine(quote.get("q1"), quote.get("qx"), quote.get("q2"))
        if m is not None:
            t1x2 = w1 * m + (1 - w1) * np.array([p_mod["1"], p_mod["X"], p_mod["2"]])
        lin = quote.get("linea")
        mo = senza_margine(quote.get("qover"), quote.get("qunder")) if lin is not None else None
        if mo is not None and float(lin) % 1 == 0.5:
            M = p_mod["_M"]; i, j = np.indices(M.shape)
            tou = (float(lin), wo * mo[0] + (1 - wo) * M[(i + j) > lin].sum())
    return t1x2, tou
