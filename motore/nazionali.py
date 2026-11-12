"""
Nazionali (sezione Speciali). Fonti gratuite:
- storico risultati internazionali dal 2019 (github.com/martj42/international_results, con i minuti dei gol);
- calendario, ultimi risultati e quote DraftKings da ESPN.

Il modello è lo stesso Dixon-Coles dei club. Il "gruppo" di ogni nazionale è la sua confederazione
(UEFA, CONMEBOL, CAF...), così il modello impara anche quanto valgono le confederazioni tra loro.

Uso: py -m motore.nazionali   (normalmente lo chiama motore.mondo)
"""
import io, time, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, requests
from concurrent.futures import ThreadPoolExecutor
from .config import RAW
from .modello import Modello
from .extra import Tempi

URL = "https://raw.githubusercontent.com/martj42/international_results/master/"
H = {"User-Agent": "Mozilla/5.0"}
DAL = "2019-01-01"
# competizioni ESPN seguite (calendario + risultati recenti)
LEGHE = {
    "uefa.nations": ("Nations League", "UEFA"),
    "fifa.friendly": ("Amichevoli", "Nazionali"),
    "concacaf.nations.league": ("Nations League", "CONCACAF"),
    "caf.nations_qual": ("Qualificazioni Coppa d'Africa", "CAF"),
    "fifa.worldq.uefa": ("Qualificazioni Mondiali", "UEFA"),
    "uefa.euroq": ("Qualificazioni Europei", "UEFA"),
    "afc.asian.cup.qual": ("Qualificazioni Coppa d'Asia", "AFC"),
    "conmebol.america": ("Copa América", "CONMEBOL"),
}
ESPN_NOMI = {"Bosnia-Herzegovina": "Bosnia and Herzegovina", "Chinese Taipei": "Taiwan", "Congo DR": "DR Congo",
             "Czechia": "Czech Republic", "Kyrgyz Republic": "Kyrgyzstan", "St. Kitts and Nevis": "Saint Kitts and Nevis",
             "St. Lucia": "Saint Lucia", "St. Martin": "Saint Martin", "St. Vincent and the Grenadines": "Saint Vincent and the Grenadines",
             "Türkiye": "Turkey", "US Virgin Islands": "United States Virgin Islands", "USA": "United States",
             "Korea Republic": "South Korea", "Korea DPR": "North Korea", "IR Iran": "Iran", "Cabo Verde": "Cape Verde",
             "Côte d'Ivoire": "Ivory Coast", "Republic of Ireland": "Republic of Ireland", "China PR": "China PR"}
CONF_TORNEI = {
    "UEFA": ["UEFA Nations League", "UEFA Euro qualification", "UEFA Euro"],
    "CAF": ["African Cup of Nations qualification", "African Cup of Nations", "COSAFA Cup", "African Nations Championship",
            "African Nations Championship qualification"],
    "CONCACAF": ["CONCACAF Nations League", "Gold Cup", "Gold Cup qualification", "CONCACAF Nations League qualification", "CONCACAF Series"],
    "AFC": ["AFC Asian Cup qualification", "AFC Asian Cup", "Gulf Cup", "AFF Championship", "ASEAN Championship", "SAFF Cup",
            "EAFF Championship", "WAFF Championship", "CAFA Nations Cup", "FIFA ASEAN Cup"],
    "OFC": ["Oceania Nations Cup", "Pacific Games", "MSG Prime Minister's Cup", "Pacific Mini Games"],
}
CONMEBOL = ["Argentina", "Brazil", "Uruguay", "Colombia", "Ecuador", "Paraguay", "Peru", "Chile", "Venezuela", "Bolivia"]
ESCLUSI = ("CONIFA", "Island Games", "Inter Games", "Viva World Cup")   # non FIFA
IT = {"Italy": "Italia", "Germany": "Germania", "France": "Francia", "Spain": "Spagna", "England": "Inghilterra", "Portugal": "Portogallo",
      "Netherlands": "Olanda", "Belgium": "Belgio", "Croatia": "Croazia", "Switzerland": "Svizzera", "Austria": "Austria",
      "Denmark": "Danimarca", "Sweden": "Svezia", "Norway": "Norvegia", "Finland": "Finlandia", "Iceland": "Islanda",
      "Poland": "Polonia", "Czech Republic": "Rep. Ceca", "Slovakia": "Slovacchia", "Hungary": "Ungheria", "Romania": "Romania",
      "Bulgaria": "Bulgaria", "Greece": "Grecia", "Turkey": "Turchia", "Serbia": "Serbia", "Slovenia": "Slovenia",
      "Bosnia and Herzegovina": "Bosnia", "Montenegro": "Montenegro", "North Macedonia": "Macedonia del Nord", "Albania": "Albania",
      "Kosovo": "Kosovo", "Ukraine": "Ucraina", "Russia": "Russia", "Belarus": "Bielorussia", "Moldova": "Moldavia",
      "Georgia": "Georgia", "Armenia": "Armenia", "Azerbaijan": "Azerbaigian", "Kazakhstan": "Kazakistan", "Cyprus": "Cipro",
      "Malta": "Malta", "Scotland": "Scozia", "Wales": "Galles", "Northern Ireland": "Irlanda del Nord", "Republic of Ireland": "Irlanda",
      "Israel": "Israele", "Estonia": "Estonia", "Latvia": "Lettonia", "Lithuania": "Lituania", "Luxembourg": "Lussemburgo",
      "Faroe Islands": "Far Oer", "Andorra": "Andorra", "San Marino": "San Marino", "Liechtenstein": "Liechtenstein",
      "Gibraltar": "Gibilterra", "Brazil": "Brasile", "Argentina": "Argentina", "Uruguay": "Uruguay", "Colombia": "Colombia",
      "Mexico": "Messico", "United States": "Stati Uniti", "Canada": "Canada", "Japan": "Giappone", "South Korea": "Corea del Sud",
      "Morocco": "Marocco", "Egypt": "Egitto", "Algeria": "Algeria", "Tunisia": "Tunisia", "Senegal": "Senegal", "Nigeria": "Nigeria",
      "Ghana": "Ghana", "Cameroon": "Camerun", "Ivory Coast": "Costa d'Avorio", "South Africa": "Sudafrica", "DR Congo": "RD Congo",
      "Cape Verde": "Capo Verde", "Saudi Arabia": "Arabia Saudita", "Australia": "Australia", "New Zealand": "Nuova Zelanda",
      "Uzbekistan": "Uzbekistan", "Iran": "Iran", "Qatar": "Qatar", "Chile": "Cile", "Peru": "Perù", "Ecuador": "Ecuador",
      "Paraguay": "Paraguay", "Venezuela": "Venezuela", "Bolivia": "Bolivia", "China PR": "Cina", "India": "India"}


def _get(url, tent=3):
    for k in range(tent):
        try:
            r = requests.get(url, headers=H, timeout=40)
            if r.status_code == 200: return r
        except Exception:
            pass
        time.sleep(1 + k)
    return None


def storico():
    """Risultati internazionali dal 2019 con gol del 1° tempo (quando ci sono tutti i minuti)."""
    f = RAW / "nazionali.csv"
    r, g = _get(URL + "results.csv"), _get(URL + "goalscorers.csv")
    if r is None:
        if f.exists(): return pd.read_csv(f, parse_dates=["data"])
        raise RuntimeError("storico nazionali non disponibile")
    d = pd.read_csv(io.StringIO(r.text)).dropna(subset=["home_score", "away_score"])
    d = d[(d.date >= DAL) & ~d.tournament.str.contains("|".join(ESCLUSI))]
    d = pd.DataFrame({"data": pd.to_datetime(d.date), "casa": d.home_team, "ospite": d.away_team,
                      "gc": d.home_score.astype(int), "go": d.away_score.astype(int), "torneo": d.tournament,
                      "neutro": d.neutral.astype(str).str.upper().eq("TRUE")})
    d["htc"] = np.nan
    if g is not None:
        s = pd.read_csv(io.StringIO(g.text)); s = s[s.date >= DAL]
        s["m"] = pd.to_numeric(s.minute, errors="coerce")
        k = s.groupby(["date", "home_team", "away_team"]).agg(n=("m", "size"), nan=("m", lambda x: x.isna().sum()), ht=("m", lambda x: (x <= 45).sum()))
        key = list(zip(d.data.dt.strftime("%Y-%m-%d"), d.casa, d.ospite))
        tot = (d.gc + d.go).values
        ht = [k.ht.get(x, np.nan) if (x in k.index and k.nan.get(x, 1) == 0 and k.n.get(x, -1) == t) else (0 if t == 0 else np.nan)
              for x, t in zip(key, tot)]
        d["htc"] = ht
    d["hto"] = np.where(d.htc.notna(), 0, np.nan)
    RAW.mkdir(parents=True, exist_ok=True); d.to_csv(f, index=False)
    return d


def _mese(args):
    lg, mese = args
    r = _get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard?dates={mese}&limit=500")
    if r is None: return []
    out = []
    for e in r.json().get("events", []):
        c = e["competitions"][0]; st = c["status"]["type"]
        t = {x["homeAway"]: x for x in c["competitors"]}
        if "home" not in t or "away" not in t: continue
        n = lambda x: ESPN_NOMI.get(x["team"]["displayName"], x["team"]["displayName"])
        row = {"id": e["id"], "lg": lg, "data": pd.to_datetime(e["date"]).tz_convert("Europe/Rome").tz_localize(None),
               "casa": n(t["home"]), "ospite": n(t["away"]), "neutro": bool(c.get("neutralSite", False)), "stato": st.get("state")}
        if st.get("completed"):
            try: row["gc"], row["go"] = int(t["home"]["score"]), int(t["away"]["score"])
            except (TypeError, ValueError, KeyError): continue
        out.append(row)
    return out


def espn(oggi, mesi_indietro=2):
    mesi = pd.period_range(oggi - pd.DateOffset(months=mesi_indietro), oggi + pd.DateOffset(months=1), freq="M")
    with ThreadPoolExecutor(8) as ex:
        rows = [r for lst in ex.map(_mese, [(lg, m.strftime("%Y%m")) for lg in LEGHE for m in mesi]) for r in lst]
    return pd.DataFrame(rows).drop_duplicates("id") if rows else pd.DataFrame(columns=["id", "lg", "data", "casa", "ospite", "neutro", "stato", "gc", "go"])


def confederazioni(d):
    conf = {t: "CONMEBOL" for t in CONMEBOL}
    for c, tornei in CONF_TORNEI.items():
        x = d[d.torneo.isin(tornei)]
        for t, n in pd.concat([x.casa, x.ospite]).value_counts().items():
            if t not in conf and n >= 3: conf[t] = c
    return conf


def prepara_dati(oggi):
    d = storico()
    e = espn(oggi)
    rec = e[e.gc.notna() & (e.data > d.data.max() + pd.Timedelta(days=1))].copy()   # risultati non ancora nello storico
    if len(rec):
        rec["torneo"] = rec.lg.map(lambda x: LEGHE[x][0]); rec["htc"] = np.nan; rec["hto"] = np.nan
        d = pd.concat([d, rec[d.columns.intersection(rec.columns)]], ignore_index=True)
    conf = confederazioni(d)
    d["comp"] = d.casa.map(conf).fillna("ALTRO"); d["tipo"] = "lega"
    return d.sort_values("data").reset_index(drop=True), e, conf


def modello(d, al):
    m = Modello(emivita=EMIVITA, ridge=RIDGE, peso_xg=0, max_giorni=MAX_GIORNI).fit(d, al)
    return m


CAL_1X2, PESO_OVER = 1.15, 0.6
EMIVITA, RIDGE, MAX_GIORNI = 730, 1.5, 2200   # scelti col backtest 2024-2026


def statistiche(d, oggi):
    """Quanto escono gli esiti nelle partite tra nazionali dell'ultimo anno, per confederazione."""
    out = {}
    x = d[d.data >= oggi - pd.Timedelta(days=365)]
    for c, g in [("TUTTE", x)] + list(x.groupby("comp")):
        if len(g) < 30: continue
        t = g.gc + g.go; h = (g.htc + g.hto).dropna()
        s = {"n": int(len(g)), "gol": float(t.mean()), "O15": float((t > 1.5).mean()), "O25": float((t > 2.5).mean()),
             "O35": float((t > 3.5).mean()), "GG": float(((g.gc > 0) & (g.go > 0)).mean()),
             "1": float((g.gc > g.go).mean()), "X": float((g.gc == g.go).mean()), "2": float((g.gc < g.go).mean())}
        if len(h) >= 30: s.update(T1O05=float((h > 0.5).mean()), n_1t=int(len(h)))
        out[c] = s
    return out


def costruisci(oggi=None, giorni=11):
    """Ritorna (partite, leghe) nel formato di docs/mondo.json."""
    from .mercato import quote_espn, obiettivi, allinea
    oggi = pd.Timestamp(oggi or pd.Timestamp.now(tz="Europe/Rome").date())
    print("[nazionali] scarico storico e calendario...", flush=True)
    d, e, conf = prepara_dati(oggi)
    fut = e[e.gc.isna() & (e.stato == "pre") & (e.data >= oggi) & (e.data < oggi + pd.Timedelta(days=giorni))].copy()
    t1 = oggi + pd.Timedelta(days=1)
    m = modello(d, t1)
    T = Tempi().fit(d.dropna(subset=["htc"]), t1, giorni=1500)
    try:
        dk = quote_espn(fut.assign(comp=fut.lg), {k: k for k in LEGHE})
    except Exception:
        dk = {}
    rec = d[d.data >= oggi - pd.Timedelta(days=730)]
    base_o25 = float(((rec.gc + rec.go) > 2.5).mean())
    n_part = pd.concat([rec.casa, rec.ospite]).value_counts()
    partite = []
    for r in fut.itertuples():
        comp = conf.get(r.casa, "ALTRO")
        quote = dk.get(r.id)
        p0 = m.mercati(r.casa, r.ospite, comp, r.neutro)
        t1x2, tou = obiettivi(p0, quote)
        if t1x2 is None:   # senza quote: correzione trovata col backtest (i favoriti vincono un po' più di quanto dice il modello)
            q = np.array([p0["1"], p0["X"], p0["2"]]) ** CAL_1X2; t1x2 = q / q.sum()
        if tou is None: tou = (2.5, PESO_OVER * p0["Over 2.5"] + (1 - PESO_OVER) * base_o25)
        p = m.mercati(r.casa, r.ospite, comp, forza=allinea(m, p0["xG_casa"], p0["xG_ospite"], t1x2, tou))
        tt = T.mercati(p["xG_casa"], p["xG_ospite"], T.q(comp, conf.get(r.casa), conf.get(r.ospite)))
        noti = sum(n_part.get(s, 0) >= 8 for s in (r.casa, r.ospite))
        pp = {"1": p["1"], "X": p["X"], "2": p["2"], "1X": p["1X"], "X2": p["X2"], "12": p["12"],
              "Over 1.5": p["Over 1.5"], "Over 2.5": p["Over 2.5"], "Over 3.5": p["Over 3.5"],
              "Under 2.5": p["Under 2.5"], "Under 3.5": p["Under 3.5"], "Gol": p["Gol"], "NoGol": p["NoGol"],
              "1T Over 0.5": tt["1T Over 0.5"], "1T Over 1.5": tt["1T Over 1.5"]}
        partite.append({
            "id": r.id, "data": r.data.strftime("%Y-%m-%dT%H:%M"), "comp": "naz." + r.lg,
            "casa": IT.get(r.casa, r.casa), "ospite": IT.get(r.ospite, r.ospite),
            "xg": [round(float(p["xG_casa"]), 2), round(float(p["xG_ospite"]), 2)],
            "p": {k: round(float(v), 4) for k, v in pp.items()},
            "ris": p["Risultati probabili"], "neutro": bool(r.neutro),
            "modello": [round(float(p0[k]), 4) for k in ("1", "X", "2")],
            "quote": {k: round(float(v), 2) for k, v in (quote or {}).items() if k in ("q1", "qx", "q2", "linea", "qover", "qunder") and v},
            "fonte": "DraftKings" if quote else "", "affidabilita": ["BASSA", "MEDIA", "ALTA"][noti]})
    st = statistiche(d, oggi)
    leghe = {"naz." + k: {"nome": v[0], "paese": v[1], "sez": "Z", "stats": st.get(v[1], st.get("TUTTE"))} for k, v in LEGHE.items()}
    leghe["naz.TUTTE"] = {"nome": "Tutte le nazionali", "paese": "Mondo", "sez": "", "stats": st.get("TUTTE")}
    print(f"[nazionali] {len(partite)} partite in programma (modello su {m.n_partite} partite)", flush=True)
    ris = e[e.gc.notna()][["id", "gc", "go"]].assign(id=lambda x: "naz." + x.id.astype(str))
    return partite, leghe, ris


if __name__ == "__main__":
    P, L, _ = costruisci()
    for p in P[:15]: print(p["data"], p["casa"], "-", p["ospite"], p["p"]["1"], p["p"]["X"], p["p"]["2"], p["fonte"], p["affidabilita"])
