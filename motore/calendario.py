"""Calendario reale delle prossime partite (ESPN, gratuito) + quote medie (football-data)."""
import io, requests, pandas as pd
from concurrent.futures import ThreadPoolExecutor
from .config import CAMPIONATI, COPPE, RAW
from .nomi import mappa

ESPN_LEGHE = {"E0": "eng.1", "SP1": "esp.1", "I1": "ita.1", "D1": "ger.1", "F1": "fra.1",
              "B1": "bel.1", "N1": "ned.1", "P1": "por.1", **{k: k for k in COPPE}}

def _giorno(args):
    cod, lega, d = args
    try:
        r = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lega}/scoreboard?dates={d:%Y%m%d}", timeout=20).json()
    except Exception:
        return []
    out = []
    for e in r.get("events", []):
        c = e["competitions"][0]; st = c["status"]["type"]
        if st["completed"] or st["state"] != "pre": continue
        t = {x["homeAway"]: x["team"]["displayName"] for x in c["competitors"]}
        out.append({"data": pd.to_datetime(e["date"]).tz_convert("Europe/Rome").tz_localize(None),
                    "comp": cod, "casa_espn": t["home"], "ospite_espn": t["away"],
                    "neutro": bool(c.get("neutralSite", False)), "id": e["id"]})
    return out

def prossime(giorni=10, oggi=None):
    oggi = pd.Timestamp(oggi or pd.Timestamp.now(tz="Europe/Rome").date())
    jobs = [(cod, lega, d) for cod, lega in ESPN_LEGHE.items() for d in pd.date_range(oggi, oggi + pd.Timedelta(days=giorni))]
    with ThreadPoolExecutor(12) as ex:
        rows = [r for lst in ex.map(_giorno, jobs) for r in lst]
    df = pd.DataFrame(rows).drop_duplicates("id")
    if df.empty: return df
    c = pd.read_csv(RAW / "campionati.csv")
    nomi = set(c.casa) | set(c.ospite)
    m = mappa(sorted(set(df.casa_espn) | set(df.ospite_espn)), nomi)
    df["casa"] = df.casa_espn.map(lambda x: m.get(x) or x)
    df["ospite"] = df.ospite_espn.map(lambda x: m.get(x) or x)
    # quote medie dei bookmaker (solo campionati, da football-data fixtures.csv)
    try:
        q = pd.read_csv(RAW / "calendario.csv")
        df = df.merge(q[["casa", "ospite", "q1", "qx", "q2", "qo25", "qu25"]], on=["casa", "ospite"], how="left")
    except Exception:
        pass
    return df.sort_values("data").reset_index(drop=True)
