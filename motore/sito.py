"""Scrive i dati per la web app (cartella docs/) a partire dai risultati di genera."""
import json, math, pandas as pd, numpy as np
from .config import BASE, OUT

DOCS = BASE / "docs"

def _pulisci(v):
    if v is None: return None
    if isinstance(v, (pd.Timestamp,)): return v.strftime("%Y-%m-%dT%H:%M")
    if isinstance(v, (np.floating, float)):
        return None if math.isnan(v) else round(float(v), 4)
    if isinstance(v, (np.integer,)): return int(v)
    if isinstance(v, (np.bool_,)): return bool(v)
    if isinstance(v, dict): return {k: _pulisci(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)): return [_pulisci(x) for x in v]
    return v

def scrivi(prev, sch, riep, bt_metriche=None):
    DOCS.mkdir(exist_ok=True)
    partite = []
    for (_, p), (_, s) in zip(prev.iterrows(), sch.iterrows()):
        d = {k: _pulisci(v) for k, v in p.items()}
        d["scheda"] = {k: _pulisci(v) for k, v in s.items() if k not in ("Data", "Partita", "Competizione")}
        partite.append(d)
    out = {"aggiornato": pd.Timestamp.now(tz="Europe/Rome").strftime("%Y-%m-%dT%H:%M"),
           "partite": partite,
           "verifica": [] if riep is None else [{k: _pulisci(v) for k, v in r.items()} for _, r in riep.iterrows()],
           "backtest": bt_metriche or {}, "backtest_extra": _extra()}
    (DOCS / "data.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return DOCS / "data.json"

def riepilogo_backtest():
    """Numeri del backtest salvati in piccolo (così non serve il CSV grande online)."""
    f = BASE / "dati" / "backtest_riepilogo.json"
    if f.exists(): return json.loads(f.read_text(encoding="utf-8"))
    csv = OUT / "backtest_2025_26.csv"
    if not csv.exists(): return {}
    from .backtest import metriche, calibrazione
    bt = pd.read_csv(csv); m = metriche(bt); cal = calibrazione(bt).reset_index()
    r = {"partite": int(m["partite"]), "favorito": float(m["accuratezza_favorito"]),
         "over25": float(m["accuratezza_over25"]), "gg": float(m["accuratezza_GG/NG"]),
         "ll_modello": float(m["logloss_1X2_modello_(stesse partite)"]), "ll_book": float(m["logloss_1X2_bookmaker"]),
         "calibrazione": [{"fascia": str(x.fascia), "previsto": float(x.previsto), "reale": float(x.reale), "n": int(x.n)} for x in cal.itertuples()]}
    f.write_text(json.dumps(r), encoding="utf-8"); return r

def _extra():
    f = BASE / "dati" / "backtest_extra.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
