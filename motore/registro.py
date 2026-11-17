"""Registro delle partite pubblicate: quota di apertura (prima vista dal sistema) e risultato finale.

Serve a due cose nella web app:
- Movimento quote: confronta la quota attuale con quella di apertura (una quota che scende molto
  di solito vuol dire notizie o soldi "informati" su quell'esito).
- Verifica dei tipster: dopo la partita l'app trova il risultato e chiude da sola le giocate salvate.
"""
import json
import pandas as pd
from .config import BASE

FILE = BASE / "dati" / "registro_partite.json"
CHIAVI = ("q1", "qx", "q2", "linea", "qover", "qunder")


def carica():
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def salva(reg, giorni=21):
    """Tiene le partite fino a 3 settimane dopo il calcio d'inizio."""
    lim = (pd.Timestamp.now(tz="Europe/Rome").tz_localize(None) - pd.Timedelta(days=giorni)).strftime("%Y-%m-%dT%H:%M")
    reg = {k: v for k, v in reg.items() if v.get("data", "") >= lim}
    FILE.parent.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(reg, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def registra(reg, chiave, data, quote, fonte, **info):
    """Aggiorna una partita; ritorna la quota di apertura (dict) se esiste ed è della stessa fonte."""
    ora = pd.Timestamp.now(tz="Europe/Rome").strftime("%Y-%m-%dT%H:%M")
    q = {k: round(float(v), 2) for k, v in (quote or {}).items() if k in CHIAVI and v is not None and pd.notna(v)}
    r = reg.get(chiave) or {"data": data}
    r["data"] = data; r.update(info)
    if q and fonte:
        if r.get("fonte") != fonte or "q0" not in r:      # nuova fonte: riparte l'apertura
            r["fonte"], r["q0"], r["t0"] = fonte, q, ora
        else:
            q0 = r["q0"]
            for k in ("q1", "qx", "q2"):                  # se all'apertura mancava un esito lo aggiunge
                if k in q and k not in q0: q0[k] = q[k]
            if q.get("linea") is not None and q0.get("linea") is None:
                q0.update({k: q[k] for k in ("linea", "qover", "qunder") if k in q})
        r["q"], r["t"] = q, ora
    reg[chiave] = r
    if r.get("q0") and r.get("t0") != r.get("t"):
        return {**r["q0"], "da": r["t0"]}
    return None
