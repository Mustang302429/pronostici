"""Scarica dati gratuiti: football-data.co.uk (campionati) + ESPN (coppe)."""
import io, json, time, datetime as dt
import requests, pandas as pd
from concurrent.futures import ThreadPoolExecutor
from .config import *

S = requests.Session(); S.headers["User-Agent"] = "Mozilla/5.0"

def _get(url, tries=3):
    for i in range(tries):
        try:
            r = S.get(url, timeout=15)
            if r.status_code == 200: return r
        except Exception: pass
        time.sleep(1 + i)
    return None

def _stagione(s):  # "2526" -> "2025/26"
    return f"20{s[:2]}/{s[2:]}"

def campionati():
    righe = []
    for s in STAGIONI:
        print(f"  stagione {_stagione(s)}...", flush=True)
        for cod in list(CAMPIONATI) + list(SUPPORTO_MAIN):
            r = _get(f"https://www.football-data.co.uk/mmz4281/{s}/{cod}.csv")
            if r is None: print("manca", s, cod); continue
            df = pd.read_csv(io.StringIO(r.content.decode("utf-8-sig", "ignore")))
            df = df.dropna(subset=["HomeTeam", "FTHG"])
            out = pd.DataFrame({
                "data": pd.to_datetime(df["Date"], dayfirst=True),
                "comp": cod, "stagione": _stagione(s),
                "casa": df["HomeTeam"].str.strip(), "ospite": df["AwayTeam"].str.strip(),
                "gc": df["FTHG"].astype(int), "go": df["FTAG"].astype(int),
                "xgc": df.get("HxG"), "xgo": df.get("AxG"),
                "q1": df.get("AvgH"), "qx": df.get("AvgD"), "q2": df.get("AvgA"),
                "qo25": df.get("Avg>2.5"), "qu25": df.get("Avg<2.5"),
                "q1c": df.get("AvgCH"), "qxc": df.get("AvgCD"), "q2c": df.get("AvgCA"),
            })
            righe.append(out)
    print("  campionati di supporto...", flush=True)
    for cod in SUPPORTO_EXTRA:
        r = _get(f"https://www.football-data.co.uk/new/{cod}.csv")
        if r is None: continue
        df = pd.read_csv(io.StringIO(r.content.decode("utf-8-sig", "ignore")))
        df["data"] = pd.to_datetime(df["Date"], dayfirst=True)
        df = df[df["data"] >= "2022-07-01"].dropna(subset=["HG"])
        righe.append(pd.DataFrame({"data": df["data"], "comp": cod,
            "stagione": df["Season"].astype(str), "casa": df["Home"].str.strip(),
            "ospite": df["Away"].str.strip(), "gc": df["HG"].astype(int),
            "go": df["AG"].astype(int), "q1c": df.get("AvgCH"),
            "qxc": df.get("AvgCD"), "q2c": df.get("AvgCA")}))
    return pd.concat(righe, ignore_index=True)

def _espn_mese(args):
    lega, y, m = args
    r = _get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lega}/scoreboard?dates={y}{m:02d}&limit=500")
    if r is None: return []
    out = []
    for e in r.json().get("events", []):
        c = e["competitions"][0]
        t = {x["homeAway"]: x for x in c["competitors"]}
        if "home" not in t: continue
        st = c["status"]["type"]
        neutro = c.get("neutralSite", False)
        out.append({"data": pd.to_datetime(e["date"]).tz_convert("Europe/Rome").tz_localize(None),
            "comp": lega, "casa": t["home"]["team"]["displayName"],
            "ospite": t["away"]["team"]["displayName"],
            "gc": int(t["home"]["score"]) if st["completed"] else None,
            "go": int(t["away"]["score"]) if st["completed"] else None,
            "stato": st["name"], "neutro": neutro, "id_espn": e["id"]})
    return out

def coppe():
    oggi = dt.date.today(); jobs = []
    for lega in COPPE:
        y, m = INIZIO_COPPE
        while (y, m) <= (oggi.year + (oggi.month + 2 > 12), (oggi.month + 2 - 1) % 12 + 1):
            jobs.append((lega, y, m)); m += 1
            if m > 12: y, m = y + 1, 1
    with ThreadPoolExecutor(8) as ex:
        rows = [r for lst in ex.map(_espn_mese, jobs) for r in lst]
    df = pd.DataFrame(rows).drop_duplicates("id_espn")
    return df

def calendario_campionati():
    r = _get("https://www.football-data.co.uk/fixtures.csv")
    df = pd.read_csv(io.StringIO(r.content.decode("utf-8-sig", "ignore")))
    df = df[df["Div"].isin(CAMPIONATI)]
    return pd.DataFrame({"data": pd.to_datetime(df["Date"] + " " + df["Time"], dayfirst=True),
        "comp": df["Div"], "casa": df["HomeTeam"].str.strip(), "ospite": df["AwayTeam"].str.strip(),
        "q1": df["AvgH"], "qx": df["AvgD"], "q2": df["AvgA"],
        "qo25": df["Avg>2.5"], "qu25": df["Avg<2.5"]})

if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    c = campionati(); c.to_csv(RAW / "campionati.csv", index=False); print("campionati", len(c))
    k = coppe(); k.to_csv(RAW / "coppe.csv", index=False); print("coppe", len(k))
    f = calendario_campionati(); f.to_csv(RAW / "calendario.csv", index=False); print("calendario", len(f))
