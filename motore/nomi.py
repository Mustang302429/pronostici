"""Collega i nomi squadra ESPN (coppe) ai nomi football-data (campionati)."""
import re, unicodedata, difflib
import pandas as pd

# Alias manuali ESPN -> football-data (verificati a mano)
ALIAS = {
 "Athletic Club": "Ath Bilbao", "Atlético Madrid": "Ath Madrid", "Atletico Madrid": "Ath Madrid",
 "Real Betis": "Betis", "Real Sociedad": "Sociedad", "Celta Vigo": "Celta",
 "Rayo Vallecano": "Vallecano", "Bayern Munich": "Bayern Munich",
 "Bayer Leverkusen": "Leverkusen", "Borussia Dortmund": "Dortmund",
 "Eintracht Frankfurt": "Ein Frankfurt", "Borussia Mönchengladbach": "M'gladbach",
 "VfB Stuttgart": "Stuttgart", "SC Freiburg": "Freiburg", "TSG Hoffenheim": "Hoffenheim",
 "1. FC Union Berlin": "Union Berlin", "FC Union Berlin": "Union Berlin", "RB Leipzig": "RB Leipzig",
 "VfL Wolfsburg": "Wolfsburg", "1. FSV Mainz 05": "Mainz", "Mainz": "Mainz",
 "Internazionale": "Inter", "Inter Milan": "Inter", "AC Milan": "Milan", "AS Roma": "Roma",
 "Paris Saint-Germain": "Paris SG", "AS Monaco": "Monaco", "Olympique Marseille": "Marseille",
 "Olympique Lyonnais": "Lyon", "Lille": "Lille", "Stade Rennais": "Rennes", "Stade Brestois 29": "Brest",
 "Brest": "Brest", "Nice": "Nice", "OGC Nice": "Nice", "Strasbourg": "Strasbourg", "RC Lens": "Lens",
 "Manchester City": "Man City", "Manchester United": "Man United", "Tottenham Hotspur": "Tottenham",
 "Newcastle United": "Newcastle", "West Ham United": "West Ham", "Nottingham Forest": "Nott'm Forest",
 "Brighton & Hove Albion": "Brighton", "Aston Villa": "Aston Villa", "Crystal Palace": "Crystal Palace",
 "Sporting CP": "Sp Lisbon", "Sporting Lisbon": "Sp Lisbon", "SC Braga": "Sp Braga", "Braga": "Sp Braga",
 "Vitória de Guimarães": "Guimaraes", "Vitoria Guimaraes": "Guimaraes", "FC Porto": "Porto",
 "Benfica": "Benfica", "PSV Eindhoven": "PSV Eindhoven", "Feyenoord Rotterdam": "Feyenoord",
 "AZ Alkmaar": "AZ Alkmaar", "FC Twente": "Twente", "FC Utrecht": "Utrecht", "Ajax Amsterdam": "Ajax",
 "Go Ahead Eagles": "Go Ahead Eagles", "Club Brugge": "Club Brugge", "Royal Antwerp": "Antwerp",
 "Union St.-Gilloise": "St. Gilloise", "Union Saint-Gilloise": "St. Gilloise", "KAA Gent": "Gent",
 "Gent": "Gent", "KRC Genk": "Genk", "Genk": "Genk", "Anderlecht": "Anderlecht", "Cercle Brugge": "Cercle Brugge",
 "Standard Liege": "Standard", "Celtic": "Celtic", "Rangers": "Rangers", "Heart of Midlothian": "Hearts",
 "Aberdeen": "Aberdeen", "Hibernian": "Hibernian", "Galatasaray": "Galatasaray", "Fenerbahce": "Fenerbahce",
 "Besiktas": "Besiktas", "Trabzonspor": "Trabzonspor", "Basaksehir": "Buyuksehyr", "Istanbul Basaksehir": "Buyuksehyr",
 "Olympiacos": "Olympiakos", "PAOK Salonika": "PAOK", "PAOK": "PAOK", "AEK Athens": "AEK", "Panathinaikos": "Panathinaikos",
 "Red Bull Salzburg": "Salzburg", "Sturm Graz": "Sturm Graz", "LASK Linz": "LASK", "LASK": "LASK",
 "Rapid Vienna": "Rapid Vienna", "SK Rapid": "Rapid Vienna", "Austria Vienna": "Austria Vienna", "Wolfsberger AC": "Wolfsberger AC",
 "Young Boys": "Young Boys", "BSC Young Boys": "Young Boys", "FC Basel": "Basel", "Basel": "Basel",
 "Servette": "Servette", "FC Lugano": "Lugano", "Lugano": "Lugano", "FC Zurich": "Zurich", "St. Gallen": "St. Gallen",
 "FC Copenhagen": "FC Copenhagen", "FC Midtjylland": "Midtjylland", "Midtjylland": "Midtjylland", "Brondby": "Brondby",
 "FC Nordsjaelland": "Nordsjaelland", "Silkeborg": "Silkeborg", "AGF Aarhus": "Aarhus",
 "Bodo/Glimt": "Bodo/Glimt", "Molde": "Molde", "Brann": "Brann", "Rosenborg": "Rosenborg",
 "Malmo FF": "Malmo FF", "BK Hacken": "Hacken", "Hacken": "Hacken", "Djurgarden": "Djurgarden", "IF Elfsborg": "Elfsborg",
 "Elfsborg": "Elfsborg", "AIK": "AIK",
 "Lech Poznan": "Lech Poznan", "Legia Warsaw": "Legia", "Rakow Czestochowa": "Rakow", "Jagiellonia Bialystok": "Jagiellonia",
 "Pogon Szczecin": "Pogon Szczecin",
 "FCSB": "FCSB", "CFR Cluj": "CFR Cluj", "CFR Cluj-Napoca": "CFR Cluj", "Universitatea Craiova": "Univ. Craiova",
 "CSU Craiova": "Univ. Craiova", "1. FC Heidenheim 1846": "Heidenheim", "AGF": "Aarhus",
 "F.C. København": "FC Copenhagen", "FC Cologne": "FC Koln", "NEC Nijmegen": "Nijmegen",
 "Racing Genk": "Genk", "Raków Czestochowa": "Rakow", "Rapid Vienna": "SK Rapid",
 "Sint-Truidense": "St Truiden", "Vitória de Guimaraes": "Guimaraes", "Mjällby AIF": "Mjallby",
 "Lausanne Sports": "Lausanne",
 "Coventry City": "Coventry", "Hull City": "Hull", "Ipswich Town": "Ipswich", "Leeds United": "Leeds",
 "Deportivo": "La Coruna", "Racing Santander": "Santander", "KVC Westerlo": "Westerlo",
 "OH Leuven": "Oud-Heverlee Leuven", "Royal Charleroi SC": "Charleroi", "Waasland-Beveren": "Beveren",
 "Zulte-Waregem": "Waregem", "ADO Den Haag": "Den Haag", "Fortuna Sittard": "For Sittard", "PEC Zwolle": "Zwolle",
 "Espanyol": "Espanol", "Alavés": "Alaves", "Málaga": "Malaga",
}

def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(fc|cf|sc|ac|as|afc|fk|sk|cd|ud|rc|rcd|ss|ssc|sv|vfl|vfb|tsg|1\.|bk|if|ff|club|de|real)\b", " ", s)
    return re.sub(r"[^a-z0-9]", "", s)

def mappa(espn_names, fd_names, cutoff=0.86):
    fd_names = list(fd_names); fdn = {norm(n): n for n in fd_names}
    out = {}
    for e in espn_names:
        if e in ALIAS and ALIAS[e] in fd_names: out[e] = ALIAS[e]; continue
        if e in fd_names: out[e] = e; continue
        n = norm(e)
        if n in fdn: out[e] = fdn[n]; continue
        m = difflib.get_close_matches(n, list(fdn), n=1, cutoff=cutoff)
        out[e] = fdn[m[0]] if m else None
    return out
