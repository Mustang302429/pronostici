"""
Sezioni speciali (fonte unica e gratuita: ESPN).

1) "Solo 1X2 – campionati serali": Sudamerica, Messico, MLS. Si gioca di sera o di notte in Italia.
2) "Campionati da gol": campionati dove Over 1.5 / Over 2.5 / 1° tempo Over 0.5 escono più spesso.

Per ogni campionato: storico dei risultati (con minuto dei gol, per ricavare il 1° tempo),
modello Dixon-Coles come per i campionati principali, quote DraftKings (ESPN) quando ci sono,
allineamento modello/mercato. Scrive docs/mondo.json.

Uso: py -m motore.mondo
"""
import json, re, time, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, requests
from concurrent.futures import ThreadPoolExecutor
from .config import RAW, BASE
from .modello import Modello
from .extra import Tempi
from .sito import _pulisci
from .mercato import quote_espn, obiettivi, allinea, senza_margine

# codice ESPN: (nome, paese, sezioni)   N = solo 1X2 serali, G = campionati da gol
LEGHE = {
    "arg.1": ("Liga Profesional", "Argentina", "N"),
    "bra.1": ("Brasileirão Serie A", "Brasile", "N"),
    "bra.2": ("Brasileirão Serie B", "Brasile", "N"),
    "col.1": ("Primera A", "Colombia", "N"),
    "chi.1": ("Primera División", "Cile", "N"),
    "uru.1": ("Primera División", "Uruguay", "N"),
    "per.1": ("Liga 1", "Perù", "N"),
    "ecu.1": ("LigaPro", "Ecuador", "N"),
    "par.1": ("División Profesional", "Paraguay", "N"),
    "bol.1": ("División Profesional", "Bolivia", "NG"),
    "mex.1": ("Liga MX", "Messico", "N"),
    "usa.1": ("MLS", "USA", "NG"),
    "nor.1": ("Eliteserien", "Norvegia", "G"),
    "ned.2": ("Eerste Divisie", "Olanda (B)", "G"),
    "den.1": ("Superliga", "Danimarca", "G"),
    "chn.1": ("Super League", "Cina", "G"),
    "aus.1": ("A-League", "Australia", "G"),
    "ksa.1": ("Saudi Pro League", "Arabia Saudita", "G"),
    "aut.1": ("Bundesliga", "Austria", "G"),
    "ger.2": ("2. Bundesliga", "Germania (B)", "G"),
}
# campionati principali (già nel sistema) che entrano anche nella sezione gol
PRINCIPALI_GOL = {"D1": ("Bundesliga", "Germania"), "N1": ("Eredivisie", "Olanda")}
MESI_STORICO = 30
FILE = RAW / "mondo.csv"
H = {"User-Agent": "Mozilla/5.0"}


def _get(url, tent=3):
    for k in range(tent):
        try:
            r = requests.get(url, headers=H, timeout=30)
            if r.status_code == 200: return r.json()
        except Exception:
            pass
        time.sleep(1 + k)
    return None


def _mese(args):
    lg, mese = args
    d = _get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard?dates={mese}&limit=1000")
    if not d: return []
    out = []
    for e in d.get("events", []):
        c = e["competitions"][0]; st = c["status"]["type"]
        t = {x["homeAway"]: x for x in c["competitors"]}
        if "home" not in t or "away" not in t: continue
        r = {"id": e["id"], "comp": lg, "data": pd.to_datetime(e["date"]).tz_convert("Europe/Rome").tz_localize(None),
             "casa": t["home"]["team"]["displayName"], "ospite": t["away"]["team"]["displayName"],
             "neutro": bool(c.get("neutralSite", False)), "stato": st.get("state")}
        if st.get("completed"):
            try:
                r["gc"], r["go"] = int(t["home"]["score"]), int(t["away"]["score"])
            except (TypeError, ValueError, KeyError):
                continue
            gol = [x for x in c.get("details", []) if x.get("scoringPlay")]
            ht, ok = 0, len(gol) == r["gc"] + r["go"]
            for x in gol:
                m = re.match(r"(\d+)'", (x.get("clock") or {}).get("displayValue", "") or "")
                if not m: ok = False; continue
                if int(m.group(1)) <= 45: ht += 1
            r["htc"], r["hto"] = (ht, 0) if ok else (np.nan, np.nan)   # serve solo il totale del 1° tempo
        out.append(r)
    return out


def scarica(oggi):
    mesi = pd.period_range(oggi - pd.DateOffset(months=MESI_STORICO), oggi + pd.DateOffset(months=1), freq="M")
    vecchio = pd.read_csv(FILE, parse_dates=["data"]) if FILE.exists() else pd.DataFrame()
    if len(vecchio):   # riscarico solo gli ultimi 2 mesi + il prossimo
        da_fare = [m for m in mesi if m >= pd.Period(oggi, "M") - 1]
        noti = set(vecchio.comp)
        jobs = [(lg, m.strftime("%Y%m")) for lg in LEGHE for m in (mesi if lg not in noti else da_fare)]
    else:
        jobs = [(lg, m.strftime("%Y%m")) for lg in LEGHE for m in mesi]
    with ThreadPoolExecutor(12) as ex:
        nuovi = pd.DataFrame([r for lst in ex.map(_mese, jobs) for r in lst])
    df = pd.concat([vecchio, nuovi], ignore_index=True) if len(vecchio) else nuovi
    df["id"] = df["id"].astype(str)
    df = df.drop_duplicates("id", keep="last")
    df = df[df.data >= oggi - pd.DateOffset(months=MESI_STORICO)].sort_values("data").reset_index(drop=True)
    RAW.mkdir(parents=True, exist_ok=True); df.to_csv(FILE, index=False)
    return df


PESO_MEDIA_GOL = 0.5   # backtest: il modello "squadra per squadra" sugli Over va mescolato 50/50 con la media del campionato


def prepara(m, r, quote, base_o25):
    """Probabilità finali: modello + quote (se ci sono). Senza linea Over/Under del bookmaker,
    il totale gol viene avvicinato alla media del campionato (corregge l'eccesso di fiducia del modello)."""
    p0 = m.mercati(r.casa, r.ospite, r.comp, r.neutro)
    t1x2, tou = obiettivi(p0, quote)
    if tou is None and base_o25 is not None:
        tou = (2.5, PESO_MEDIA_GOL * p0["Over 2.5"] + (1 - PESO_MEDIA_GOL) * base_o25)
        if t1x2 is None: t1x2 = np.array([p0["1"], p0["X"], p0["2"]])
    if t1x2 is None and tou is None: return p0, p0
    return p0, m.mercati(r.casa, r.ospite, r.comp, forza=allinea(m, p0["xG_casa"], p0["xG_ospite"], t1x2, tou))


def statistiche(d, comp, giorni=365, oggi=None):
    """Quanto spesso escono gli Over nell'ultimo anno (dati reali)."""
    d = d[(d.comp == comp) & d.gc.notna() & (d.data >= oggi - pd.Timedelta(days=giorni))]
    if len(d) < 30: return None
    g = d.gc + d.go; h = (d.htc + d.hto).dropna()
    s = {"n": int(len(d)), "gol": float(g.mean()), "O15": float((g > 1.5).mean()), "O25": float((g > 2.5).mean()),
         "O35": float((g > 3.5).mean()), "GG": float(((d.gc > 0) & (d.go > 0)).mean()),
         "1": float((d.gc > d.go).mean()), "X": float((d.gc == d.go).mean()), "2": float((d.gc < d.go).mean())}
    if len(h) >= 30:
        s.update(T1O05=float((h > 0.5).mean()), T1O15=float((h > 1.5).mean()), n_1t=int(len(h)))
    return s


def costruisci(oggi=None, giorni=11):
    oggi = pd.Timestamp(oggi or pd.Timestamp.now(tz="Europe/Rome").date())
    print("[mondo] scarico risultati e calendario (ESPN)...", flush=True)
    df = scarica(oggi)
    df["tipo"] = "lega"
    gioc = df[df.gc.notna()].copy()
    fut = df[(df.gc.isna()) & (df.stato == "pre") & (df.data >= oggi) & (df.data < oggi + pd.Timedelta(days=giorni))].copy()
    t1 = oggi + pd.Timedelta(days=1)
    print(f"[mondo] modello su {len(gioc)} partite, {len(fut)} partite in programma...", flush=True)
    m = Modello(emivita=400, ridge=2, peso_xg=0).fit(gioc, t1)
    T = Tempi().fit(gioc, t1)
    try:
        dk = quote_espn(fut, {k: k for k in LEGHE})
    except Exception:
        dk = {}
    rec = gioc[gioc.data >= oggi - pd.Timedelta(days=365)]
    base = ((rec.gc + rec.go) > 2.5).groupby(rec.comp).mean().to_dict()
    partite = []
    for r in fut.itertuples():
        quote = dk.get(r.id)
        p0, p = prepara(m, r, quote, base.get(r.comp))
        tt = T.mercati(p["xG_casa"], p["xG_ospite"], T.q(r.comp))
        noti = sum(((gioc.casa == s) | (gioc.ospite == s)).sum() >= 10 for s in (r.casa, r.ospite))
        partite.append({
            "id": r.id, "data": r.data.strftime("%Y-%m-%dT%H:%M"), "comp": r.comp, "casa": r.casa, "ospite": r.ospite,
            "xg": [round(float(p["xG_casa"]), 2), round(float(p["xG_ospite"]), 2)],
            "p": {k: round(float(v), 4) for k, v in {
                "1": p["1"], "X": p["X"], "2": p["2"], "Over 1.5": p["Over 1.5"], "Over 2.5": p["Over 2.5"],
                "Over 3.5": p["Over 3.5"], "Gol": p["Gol"], "1T Over 0.5": tt["1T Over 0.5"], "1T Over 1.5": tt["1T Over 1.5"]}.items()},
            "modello": [round(float(p0[k]), 4) for k in ("1", "X", "2")],
            "quote": {k: round(float(v), 2) for k, v in (quote or {}).items() if k in ("q1", "qx", "q2", "linea", "qover", "qunder") and v},
            "fonte": "DraftKings" if quote else "", "affidabilita": ["BASSA", "MEDIA", "ALTA"][noti]})
    leghe = {k: {"nome": v[0], "paese": v[1], "sez": v[2], "stats": statistiche(gioc, k, oggi=oggi),
                 "q1t": round(float(T.q(k)), 3)} for k, v in LEGHE.items()}
    # statistiche dei campionati principali da gol (football-data, già scaricato dal sistema principale)
    try:
        c = pd.read_csv(RAW / "campionati.csv", parse_dates=["data"])
        for k, (n, paese) in PRINCIPALI_GOL.items():
            leghe[k] = {"nome": n, "paese": paese, "sez": "G", "stats": statistiche(c, k, oggi=oggi), "principale": True}
    except Exception:
        pass
    try:   # nazionali (storico internazionale + ESPN)
        from .nazionali import costruisci as nazionali
        pn, ln = nazionali(oggi)
        partite += pn; leghe.update(ln)
    except Exception as ex:
        print(f"[mondo] nazionali non disponibili: {ex}", flush=True)
    out = {"aggiornato": pd.Timestamp.now(tz="Europe/Rome").strftime("%Y-%m-%dT%H:%M"),
           "leghe": leghe, "partite": sorted(partite, key=lambda x: x["data"])}
    f = BASE / "docs" / "mondo.json"
    f.write_text(json.dumps(_pulisci(out), ensure_ascii=False), encoding="utf-8")
    print(f"[mondo] FATTO: {len(partite)} partite in docs/mondo.json", flush=True)
    return out


if __name__ == "__main__":
    costruisci()
