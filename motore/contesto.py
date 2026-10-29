"""Statistiche 'a colpo d'occhio', come quelle che si guardano a mano su Sportradar."""
import pandas as pd

def _partite_squadra(df, t, prima):
    s = df[((df.casa == t) | (df.ospite == t)) & (df.data < prima)].sort_values("data")
    gf = s.gc.where(s.casa == t, s.go); gs = s.go.where(s.casa == t, s.gc)
    return pd.DataFrame({"data": s.data, "casa": s.casa == t, "gf": gf, "gs": gs,
                         "avv": s.ospite.where(s.casa == t, s.casa), "comp": s.comp,
                         "gialli": s.gialli_c.where(s.casa == t, s.gialli_o) if "gialli_c" in s else None,
                         "g1t": s.htc.where(s.casa == t, s.hto) if "htc" in s else None,
                         "s1t": s.hto.where(s.casa == t, s.htc) if "htc" in s else None})

def scheda(df, casa, ospite, quando):
    out = {}
    for lato, t in (("casa", casa), ("ospite", ospite)):
        p = _partite_squadra(df, t, quando)
        u5, u10 = p.tail(5), p.tail(10)
        forma = "".join("V" if a > b else ("N" if a == b else "P") for a, b in zip(u5.gf, u5.gs))
        sede = p[p.casa == (lato == "casa")].tail(8)
        out[f"Forma {lato} (ult.5)"] = forma
        out[f"Punti ult.5 {lato}"] = int(sum(3 if a > b else (1 if a == b else 0) for a, b in zip(u5.gf, u5.gs)))
        out[f"Gol fatti/subiti ult.10 {lato}"] = f"{u10.gf.mean():.1f} / {u10.gs.mean():.1f}" if len(u10) else "-"
        out[f"% Over2.5 ult.10 {lato}"] = round(((u10.gf + u10.gs) > 2.5).mean() * 100) if len(u10) else None
        out[f"% Gol ult.10 {lato}"] = round(((u10.gf > 0) & (u10.gs > 0)).mean() * 100) if len(u10) else None
        y = u10.gialli.dropna() if "gialli" in u10 else []
        out[f"Gialli medi ult.10 {lato}"] = round(float(y.mean()), 1) if len(y) else None
        h1 = u10.dropna(subset=["g1t"]) if "g1t" in u10 else u10.iloc[:0]
        out[f"% gol nel 1T ult.10 {lato}"] = round(((h1.g1t + h1.s1t) > 0).mean() * 100) if len(h1) else None
        out[f"Rendimento {'in casa' if lato == 'casa' else 'in trasferta'} ult.8 {lato}"] = (
            "".join("V" if a > b else ("N" if a == b else "P") for a, b in zip(sede.gf, sede.gs)))
    h2h = df[(((df.casa == casa) & (df.ospite == ospite)) | ((df.casa == ospite) & (df.ospite == casa))) & (df.data < quando)].tail(5)
    out["Precedenti (ult.5)"] = " | ".join(f"{r.data:%d/%m/%y} {r.casa} {int(r.gc)}-{int(r.go)} {r.ospite}" for r in h2h.itertuples()) or "nessuno nel database"
    return out
