import requests
from bs4 import BeautifulSoup
import re
import csv
import time

BASE_URL = "https://www.fussballdaten.de/bundesliga/2026/{sd}/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}

# Dein Mapping bleibt das Herzstück
TEAM_MAP = {
    "Bayern": "FC Bayern München", "Leipzig": "RB Leipzig",
    "Dortmund": "Borussia Dortmund", "St. Pauli": "FC St Pauli",
    "St Pauli": "FC St Pauli", "Leverkusen": "Bayer 04 Leverkusen",
    "Frankfurt": "Eintracht Frankfurt", "Stuttgart": "VfB Stuttgart",
    "Heidenheim": "1. FC Heidenheim", "M'gladbach": "Borussia Mönchengladbach",
    "Wolfsburg": "VfL Wolfsburg", "Augsburg": "1.FC Augsburg",
    "Freiburg": "SC Freiburg", "Mainz": "FSV Mainz 05",
    "Union Berlin": "1. FC Union Berlin", "Hoffenheim": "TSG Hoffenheim",
    "Kiel": "Holstein Kiel", "Bochum": "VfL Bochum",
    "Hamburg": "Hamburger SV", "Köln": "1. FC Köln", "Bremen": "SV Werder Bremen"
}

def get_clean_team_name(text):
    for key, full_name in TEAM_MAP.items():
        if key.lower() in text.lower():
            return full_name
    return None

def scrape_spieltag(spieltag_nr):
    url = BASE_URL.format(sd=spieltag_nr)
    print(f"Hole Spieltag {spieltag_nr}...", end=" ", flush=True)
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        matches = []

        # Wir suchen nach den Containern, die ein einzelnes Spiel enthalten
        # Auf fussballdaten.de sind das oft <a> Tags mit der Klasse 'ergebnis-link'
        spiel_links = soup.find_all('a', class_=re.compile(r'ergebnis-link|spiele-row'))

        for link in spiel_links:
            # Wir suchen das Eltern-Element, das Heim, Gast und Ergebnis umschließt
            parent = link.find_parent(['div', 'tr'])
            if not parent: continue
            
            # Wir holen alle Textelemente innerhalb dieses Spiel-Containers
            # Das Ergebnis (z.B. 4:1) ist unser Ankerpunkt
            all_text = parent.get_text(" | ", strip=True)
            parts = all_text.split(" | ")
            
            res_val = "-:-"
            heim = None
            gast = None
            
            # 1. Ergebnis/Uhrzeit finden
            for i, p in enumerate(parts):
                if re.match(r'^\d{1,2}:\d{1,2}$', p):
                    res_val = p
                    # Alles links vom Ergebnis ist Heim
                    for left in parts[:i]:
                        name = get_clean_team_name(left)
                        if name: heim = name; break
                    # Alles rechts vom Ergebnis ist Gast
                    for right in parts[i+1:]:
                        name = get_clean_team_name(right)
                        if name: gast = name; break
                    break
            
            if heim and gast:
                # Zeit-Filter
                if spieltag_nr > 15 or res_val in ["15:30", "18:30", "20:30", "17:30", "20:45"]:
                    res_val = "-:-"
                
                matches.append([spieltag_nr, heim, gast, res_val])

        # Duplikate filtern
        unique = []
        seen = set()
        for m in matches:
            key = f"{m[1]}-{m[2]}"
            if key not in seen:
                unique.append(m)
                seen.add(key)

        print(f"-> {len(unique[:9])} Spiele.")
        return unique[:9]
    except Exception as e:
        print(f"Fehler: {e}")
        return []

def main():
    all_data = []
    for sd in range(1, 35):
        res = scrape_spieltag(sd)
        all_data.extend(res)
        time.sleep(0.5)
    
    with open("bundesliga_2026.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["spieltag", "home", "away", "result"])
        writer.writerows(all_data)
    print("\nCSV fertig erstellt.")

if __name__ == "__main__":
    main()