"""
Ramo 2 - Il presente: infortuni, squalifiche e formazioni probabili (FotMob, gratuito).

Idea: si confronta la "migliore formazione possibile" di una squadra (rosa al completo)
con quella che scenderà davvero in campo (formazione probabile, oppure rosa senza
gli indisponibili). La perdita di qualità in attacco abbassa i gol attesi della squadra,
la perdita in difesa alza i gol attesi dell'avversario.
"""
import re, time, unicodedata, difflib, threading
import requests, numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36"}
FOTMOB = "https://www.fotmob.com/api/data"
# id competizione FotMob
LEGHE_FM = {"E0": 47, "SP1": 87, "I1": 55, "D1": 54, "F1": 53, "B1": 40, "N1": 57, "P1": 61,
            "uefa.champions": 42, "uefa.europa": 73, "uefa.europa.conf": 10216}
K_ELASTICITA = 0.35      # quanto la qualità schierata incide sui gol (da ricalibrare con l'archivio)
MAX_CORR = 0.25          # correzione massima ±25% sui gol attesi
_lock = threading.Lock(); _cache = {}

def _get(url):
    with _lock:
        if url in _cache: return _cache[url]
    for i in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=20)
            if r.status_code == 200:
                j = r.json()
                with _lock: _cache[url] = j
                return j
        except Exception:
            pass
        time.sleep(1.5 * (i + 1))
    return None

def _n(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(fc|cf|sc|ac|as|afc|fk|sk|cd|ud|rc|ssc|sv|vfl|vfb|tsg|kv|krc|kaa|club|de|real)\b", " ", s)
    return re.sub(r"[^a-z0-9]", "", s)

def _sim(a, b):
    a, b = _n(a), _n(b)
    if not a or not b: return 0
    if a in b or b in a: return 0.95
    return difflib.SequenceMatcher(None, a, b).ratio()

# ---------------- trovare la partita su FotMob ----------------
def trova_partite(cal):
    """Aggiunge a ogni partita del calendario l'id FotMob e gli id delle squadre."""
    giorni = sorted({d.strftime("%Y%m%d") for d in cal.data})
    per_giorno = {}
    for g in giorni:
        j = _get(f"{FOTMOB}/matches?date={g}") or {}
        per_giorno[g] = [(lg.get("primaryId"), m) for lg in j.get("leagues", []) for m in lg.get("matches", [])]
    ids = []
    for r in cal.itertuples():
        cand = per_giorno.get(r.data.strftime("%Y%m%d"), [])
        pid = LEGHE_FM.get(r.comp)
        best, bs = None, 0
        for p, m in cand:
            if pid and p != pid: continue
            s = _sim(r.casa_espn, m["home"]["name"]) + _sim(r.ospite_espn, m["away"]["name"])
            if s > bs: best, bs = m, s
        ok = best is not None and bs >= 1.3
        ids.append((best["id"], best["home"]["id"], best["away"]["id"]) if ok else (None, None, None))
    cal = cal.copy()
    cal["fm_match"], cal["fm_casa"], cal["fm_ospite"] = zip(*ids) if ids else ([], [], [])
    return cal

# ---------------- qualità della rosa ----------------
REPARTO = {"GK": "POR", "CB": "DIF", "LB": "DIF", "RB": "DIF", "LWB": "DIF", "RWB": "DIF",
           "DM": "CEN", "CM": "CEN", "LM": "CEN", "RM": "CEN", "AM": "CEN",
           "LW": "ATT", "RW": "ATT", "ST": "ATT", "CF": "ATT"}
SLOT = {"POR": 1, "DIF": 4, "CEN": 3, "ATT": 3}
TITLE = {"keepers": "POR", "defenders": "DIF", "midfielders": "CEN", "attackers": "ATT"}

def rosa(team_id):
    j = _get(f"{FOTMOB}/teams?id={int(team_id)}") or {}
    out = []
    for gruppo in ((j.get("squad") or {}).get("squad") or []):
        if gruppo.get("title") == "coach": continue
        for p in gruppo.get("members") or []:
            pos = str(p.get("positionIdsDesc") or "").split(",")[0].strip()
            rep = REPARTO.get(pos, TITLE.get(gruppo.get("title"), "CEN"))
            val = float(p.get("transferValue") or 0)
            rat = p.get("rating")
            # qualità = valore di mercato corretto per il rendimento stagionale (voto FotMob)
            fatt = float(np.clip((rat or 6.9) / 6.9, 0.85, 1.15)) ** 2
            # radice quadrata: un giocatore da 40M non vale "4 volte" uno da 10M in campo
            out.append({"id": p["id"], "nome": p["name"], "reparto": rep, "qualita": np.sqrt(max(val, 2e5)) * fatt,
                        "voto": rat, "gol": p.get("goals") or 0, "assist": p.get("assists") or 0})
    return pd.DataFrame(out)

def _xi(df, slot=None):
    """Migliori 11 per reparto (di default 1 portiere, 4 difensori, 3 centrocampisti, 3 attaccanti)."""
    if df.empty: return df
    return pd.concat([df[df.reparto == r].nlargest(n, "qualita") for r, n in (slot or SLOT).items()])

def _forza(xi):
    q = xi.groupby("reparto").qualita.sum().reindex(list(SLOT), fill_value=0)
    attacco = q["ATT"] + 0.6 * q["CEN"]
    difesa = q["POR"] * 1.5 + q["DIF"] + 0.4 * q["CEN"]
    return attacco, difesa

RUOLO_IT = {"POR": "Portiere", "DIF": "Difensore", "CEN": "Centrocampista", "ATT": "Attaccante"}

def ultimi_titolari(team_id, n=3):
    """Titolari della squadra nelle ultime n partite giocate: {id_giocatore: presenze da titolare}, n partite lette."""
    j = _get(f"{FOTMOB}/teams?id={int(team_id)}") or {}
    fx = ((j.get("fixtures") or {}).get("allFixtures") or {}).get("fixtures") or []
    fatte = [x for x in fx if (x.get("status") or {}).get("finished") and not (x.get("status") or {}).get("cancelled")]
    fatte = sorted(fatte, key=lambda x: x["status"].get("utcTime", ""))[-n:]
    conta, lette = {}, 0
    for x in fatte:
        m = _get(f"{FOTMOB}/matchDetails?matchId={x['id']}") or {}
        lu = (m.get("content") or {}).get("lineup") or {}
        lato = next((lu.get(k) for k in ("homeTeam", "awayTeam") if (lu.get(k) or {}).get("id") == int(team_id)), None)
        if not lato or not lato.get("starters"): continue
        lette += 1
        for p in lato["starters"]:
            conta[p["id"]] = conta.get(p["id"], 0) + 1
    return conta, lette

def _etichetta(tit, lette, peso):
    if lette == 0: stato = "dato titolarità non disponibile"
    elif tit == lette: stato = f"Titolare ({tit}/{lette} ultime partite)"
    elif tit >= 1: stato = f"A volte titolare ({tit}/{lette})"
    else: stato = f"Non titolare nelle ultime {lette} (già fuori o riserva: la squadra è già abituata)"
    # impatto: conta soprattutto se giocava davvero (titolare) e quanto vale nella rosa
    t = tit / lette if lette else 0.5
    q = min(1, peso / 0.11)            # 0.11 ≈ un titolare di livello alto per la squadra
    score = t * (0.45 + 0.55 * q) + (1 - t) * 0.45 * q
    impatto = "Alto" if score >= 0.75 else "Medio" if score >= 0.35 else "Basso"
    return stato, impatto, score

def valuta_squadra(team_id, lineup_side):
    """Ritorna (fattore attacco, fattore difesa, assenti, tipo formazione, testo)."""
    R = rosa(team_id)
    if R.empty: return 1.0, 1.0, [], "n.d.", ""
    full_a, full_d = _forza(_xi(R))
    assenti, peso = [], {}
    for p in (lineup_side or {}).get("unavailable", []) or []:
        u = p.get("unavailability") or {}
        tipo = u.get("type", "")
        dubbio = "doubt" in str(u.get("expectedReturn", "")).lower()
        motivo = {"injury": "infortunio", "suspension": "squalifica", "international": "nazionale"}.get(tipo, tipo or "assente")
        assenti.append({"id": p["id"], "nome": p["name"], "motivo": motivo + (" (in dubbio)" if dubbio else ""),
                        "rientro": u.get("expectedReturn", "")})
        peso[p["id"]] = 0.5 if dubbio else 1.0
    titolari = [p["id"] for p in (lineup_side or {}).get("starters", []) or []]
    # 1) metodo indisponibili: rosa migliore senza infortunati/squalificati (in dubbio = metà)
    R2 = R.copy()
    for pid, w in peso.items():
        R2.loc[R2.id == pid, "qualita"] *= (1 - w)
    av_a, av_d = _forza(_xi(R2))
    fa = (av_a / full_a) if full_a else 1.0
    fd = (av_d / full_d) if full_d else 1.0
    tipo_form = "da indisponibili"
    # 2) se c'è la formazione (probabile o ufficiale) si usa anche quella: cattura il turnover
    xi = R[R.id.isin(titolari)]
    if len(xi) >= 10:
        ufficiale = (lineup_side or {}).get("_tipo") == "confirmed"
        slot = xi.reparto.value_counts().reindex(list(SLOT), fill_value=0).to_dict()
        fa_x, fd_x = _forza(_xi(R, slot)); xa, xd = _forza(xi)
        fa_x = xa / fa_x if fa_x else 1.0; fd_x = xd / fd_x if fd_x else 1.0
        w = 1.0 if ufficiale else 0.5          # la probabile è una previsione: pesa a metà
        fa = (1 - w) * fa + w * fa_x; fd = (1 - w) * fd + w * fd_x
        tipo_form = "ufficiale" if ufficiale else "probabile"
    fa, fd = float(np.clip(fa, 0.6, 1.0)), float(np.clip(fd, 0.6, 1.0))
    # testo: assenti ordinati per impatto (titolare nelle ultime partite + peso nel reparto)
    if assenti:
        Ri = R.set_index("id")
        try:
            conta, lette = ultimi_titolari(team_id)
        except Exception:
            conta, lette = {}, 0
        tot = max(1, _xi(R).qualita.sum())
        for a in assenti:
            x = Ri.loc[a["id"]] if a["id"] in Ri.index else None
            a["peso"] = float(x.qualita / tot) if x is not None else 0.0
            a["ruolo"] = RUOLO_IT.get(x.reparto, "") if x is not None else ""
            a["gol"] = int(x.gol) if x is not None and x.gol else 0
            a["assist"] = int(x.assist) if x is not None and x.assist else 0
            a["voto"] = float(x.voto) if x is not None and x.voto else None
            a["titolare"], a["impatto"], a["score"] = _etichetta(conta.get(a["id"], 0), lette, a["peso"])
        assenti.sort(key=lambda a: -a["score"])
        def riga(a):
            extra = f", {a['gol']} gol" if a["gol"] else ""
            return f"{a['nome']} ({a['ruolo'] or '?'}, {a['motivo']}, {a['titolare'].split(' (')[0].lower()}{extra}) – impatto {a['impatto'].lower()}"
        testo = "; ".join(riga(a) for a in assenti[:6])
    else:
        testo = "nessun assente segnalato"
    return float(fa), float(fd), assenti, tipo_form, testo

def analizza(cal, workers=4):
    """Per ogni partita: fattori di correzione dei gol attesi + elenco assenti."""
    cal = trova_partite(cal)
    def una(r):
        vuoto = {"fm_ok": False, "corr_casa": 1.0, "corr_ospite": 1.0, "assenti_casa": "", "assenti_ospite": "",
                 "formazione": "partita non trovata su FotMob", "qual_casa": None, "qual_ospite": None}
        if not r.fm_match or pd.isna(r.fm_match): return vuoto
        j = _get(f"{FOTMOB}/matchDetails?matchId={int(r.fm_match)}")
        if not j: return vuoto
        lu = (j.get("content") or {}).get("lineup") or {}
        tipo = lu.get("lineupType")
        h, a = lu.get("homeTeam") or {}, lu.get("awayTeam") or {}
        h["_tipo"] = a["_tipo"] = tipo
        fa_h, fd_h, ass_h, tf_h, tx_h = valuta_squadra(r.fm_casa, h)
        fa_a, fd_a, ass_a, tf_a, tx_a = valuta_squadra(r.fm_ospite, a)
        k = K_ELASTICITA
        # gol attesi casa: qualità attacco casa vs qualità difesa ospite
        cc = np.clip(fa_h ** k * fd_a ** (-k), 1 - MAX_CORR, 1 + MAX_CORR)
        co = np.clip(fa_a ** k * fd_h ** (-k), 1 - MAX_CORR, 1 + MAX_CORR)
        arb = (((j.get("content") or {}).get("matchFacts") or {}).get("infoBox") or {}).get("Referee") or {}
        pulisci = lambda L: [{k: a.get(k) for k in ("nome", "ruolo", "motivo", "rientro", "titolare", "impatto", "gol", "assist", "voto")} for a in L]
        return {"fm_ok": True, "corr_casa": float(cc), "corr_ospite": float(co), "arbitro": arb.get("text") if isinstance(arb, dict) else None,
                "lista_assenti_casa": pulisci(ass_h), "lista_assenti_ospite": pulisci(ass_a),
                "assenti_casa": tx_h, "assenti_ospite": tx_a, "formazione": tf_h if tf_h == tf_a else f"{tf_h}/{tf_a}",
                "qual_casa": (fa_h + fd_h) / 2, "qual_ospite": (fa_a + fd_a) / 2,
                "n_assenti_casa": len(ass_h), "n_assenti_ospite": len(ass_a)}
    def sicura(r):
        try:
            return una(r)
        except Exception as e:
            return {"fm_ok": False, "corr_casa": 1.0, "corr_ospite": 1.0, "assenti_casa": "", "assenti_ospite": "",
                    "formazione": f"errore lettura dati ({type(e).__name__})", "qual_casa": None, "qual_ospite": None}
    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(sicura, cal.itertuples()))
    return pd.concat([cal.reset_index(drop=True), pd.DataFrame(res)], axis=1)
