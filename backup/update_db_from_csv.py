#!/usr/bin/env python3
# coding: utf-8
"""
update_csv_from_scrape.py
Ändert deine vorhandene CSV (spieltag, home, away, result):
- vorhandene Zeilen (gleiches spieltag+home+away) -> update result (wenn neues Ergebnis ein Score ist)
- neue Zeilen -> anhängen
- dedupliziert am Ende (bevorzugt Zeilen mit Ergebnis)
- atomic write (tmp -> backup -> replace)
- dry-run möglich (schreibt nichts, nur Logging)

Benutzung (Beispiel):
python update_csv_from_scrape.py --season-end 2026 --matchday 5 --csv "F:\Workspace\Bundesligadashboard\bundesliga_2026.csv" --dry-run
"""
import argparse
import logging
import re
import shutil
import time
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

# --- Konfig ---
BASE_URL_TEMPLATE = "https://www.fussballdaten.de/bundesliga/{season_end}/{matchday}/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
RESULT_RE = re.compile(r"^\s*(\d{1,2})\s*[:\-]\s*(\d{1,2})\s*$")
INLINE_SCORE_RE = re.compile(r"\b(\d{1,2}[:\-]\d{1,2})\b")

# --- Hilfsfunktionen ---
def is_score(s: str) -> bool:
    if not isinstance(s, str):
        return False
    m = RESULT_RE.match(s.strip())
    if not m:
        return False
    a, b = int(m.group(1)), int(m.group(2))
    # großzügige Plausibilitätsgrenze
    return 0 <= a <= 30 and 0 <= b <= 30

def clean(text) -> str:
    """Trim + normalize whitespace."""
    return " ".join(str(text).split()).strip()

def fetch_html(url: str) -> str:
    logging.info("Hole URL: %s", url)
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    r.encoding = r.apparent_encoding
    return r.text

def collect_matches_from_soup(soup: BeautifulSoup, spieltag: int):
    """
    Heuristik wie dein Original: suche div.spiele-row, extrahiere erstes Score-Match,
    home = text vor score, away = text nach score.
    Liefert Liste von dicts: {'spieltag': int, 'home': str, 'away': str, 'result': 'x:y'}
    """
    matches = []
    containers = soup.find_all("div", class_="spiele-row")
    if not containers:
        logging.debug("Keine div.spiele-row - versuche Textscan.")
        # Fallback: Textscan (sehr defensiv)
        for t in soup.find_all(text=True):
            txt = clean(t)
            if not txt:
                continue
            m = INLINE_SCORE_RE.search(txt)
            if m:
                score = m.group(1).replace(" ", "")
                prev = t.previous_element
                nxt = t.next_element
                home = clean(prev if isinstance(prev, str) else getattr(prev, "get_text", lambda: "")())
                away = clean(nxt if isinstance(nxt, str) else getattr(nxt, "get_text", lambda: "")())
                if home and away and home != away:
                    matches.append({"spieltag": spieltag, "home": home, "away": away, "result": score})
        return matches

    for cont in containers:
        text = clean(cont.get_text(" ", strip=True))
        m = INLINE_SCORE_RE.search(text)
        if not m:
            continue
        score = m.group(1).replace(" ", "")
        parts = text.split(m.group(1))
        if len(parts) < 2:
            continue
        heim = clean(parts[0])
        gast = clean(parts[-1])
        if heim and gast and heim != gast:
            matches.append({"spieltag": spieltag, "home": heim, "away": gast, "result": score})
    return matches

# --- Core: CSV Update Logik ---
def update_csv(csv_path: Path, scraped_matches: list, dry_run: bool = True):
    csv_path = csv_path.resolve()
    logging.info("Ziel-CSV: %s", csv_path)
    # Lade bestehende CSV (oder lege leeres DataFrame an)
    if csv_path.exists():
        df = pd.read_csv(csv_path, dtype=str).fillna("")
        logging.info("Bestehende CSV geladen: %d Zeilen", len(df))
    else:
        df = pd.DataFrame(columns=["spieltag","home","away","result"])
        logging.info("CSV existiert nicht - neue DataFrame wird verwendet (wird nur geschrieben bei non-dry-run).")

    # Sicherstellen, dass die 4 Spalten existieren
    for c in ["spieltag","home","away","result"]:
        if c not in df.columns:
            df[c] = ""

    # Normalisierte Vergleichsschlüssel (case-insensitive, trimmed)
    df["__sd"] = df["spieltag"].astype(str).str.strip()
    df["__home_key"] = df["home"].astype(str).str.strip().str.lower()
    df["__away_key"] = df["away"].astype(str).str.strip().str.lower()

    updates = []
    inserts = []

    # Bearbeite Einträge
    for m in scraped_matches:
        sd = str(m["spieltag"]).strip()
        home = clean(m["home"])
        away = clean(m["away"])
        result = clean(m["result"])
        hk = home.lower().strip()
        ak = away.lower().strip()

        mask = (df["__sd"] == sd) & (df["__home_key"] == hk) & (df["__away_key"] == ak)

        if mask.any():
            # Update alle gefundenen (meistens ist es genau 1)
            idxs = df[mask].index.tolist()
            for idx in idxs:
                old = str(df.at[idx, "result"])
                # Wenn das neue Ergebnis ein Score ist und sich unterscheidet, dann update
                if result != old and is_score(result):
                    updates.append((idx, home, away, old, result))
                    if not dry_run:
                        df.at[idx, "result"] = result
        else:
            inserts.append((sd, home, away, result))
            if not dry_run:
                df = pd.concat([df, pd.DataFrame([{"spieltag": sd, "home": home, "away": away, "result": result}])], ignore_index=True)

    # Dry-run -> nur logging
    if dry_run:
        logging.info("DRY-RUN: %d Updates, %d Inserts (es wird nichts geschrieben)", len(updates), len(inserts))
        for u in updates[:50]:
            logging.info("Would UPDATE idx=%s: %s vs %s | %s -> %s", u[0], u[1], u[2], u[3], u[4])
        for ins in inserts[:50]:
            logging.info("Would INSERT: spieltag=%s | %s vs %s -> %s", ins[0], ins[1], ins[2], ins[3])
        return {"updated": len(updates), "inserted": len(inserts), "before": len(df), "after": len(df)}

    # Nicht dry-run: mache Dedup & atomic write
    df["_has_score"] = df["result"].astype(str).str.match(RESULT_RE)
    # Sortiere so, dass Zeilen mit Score bevorzugt werden
    df.sort_values(by=["spieltag","__home_key","__away_key","_has_score"], ascending=[True,True,True,False], inplace=True)
    df = df.drop_duplicates(subset=["spieltag","__home_key","__away_key"], keep="first").drop(columns=["__sd","__home_key","__away_key","_has_score"])

    # Schreibe atomar
    tmp = csv_path.with_suffix(".tmp")
    df.to_csv(tmp, index=False, encoding="utf-8")
    bak = csv_path.parent / (csv_path.name + f".bak.{int(time.time())}")
    if csv_path.exists():
        shutil.copy2(csv_path, bak)
        logging.info("Backup der Original-CSV: %s", bak)
    tmp.replace(csv_path)
    logging.info("CSV aktualisiert: vorher %d Zeilen, jetzt %d Zeilen", len(pd.read_csv(bak)) if bak.exists() else 0, len(df))
    return {"updated": len(updates), "inserted": len(inserts), "before": None, "after": len(df), "backup": str(bak)}

# --- Main Laufwerk ---
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--season-end", type=int, default=2026, help="Endjahr für URL (z.B. 2026 für Saison 2025/26)")
    p.add_argument("--matchday", type=int, default=None, help="Nummer Spieltag (wenn None: alle 1..34)")
    p.add_argument("--start", type=int, default=1, help="Start-Spieltag (nur bei matchday==None)")
    p.add_argument("--end", type=int, default=34, help="End-Spieltag (nur bei matchday==None)")
    p.add_argument("--csv", default="bundesliga_2026.csv", help="Pfad zur CSV")
    p.add_argument("--dry-run", action="store_true", help="Nur simulieren, nichts schreiben")
    args = p.parse_args()

    csv_path = Path(args.csv)
    scraped_all = []

    spieltage = [args.matchday] if args.matchday else list(range(args.start, args.end+1))
    for sd in spieltage:
        try:
            html = fetch_html(BASE_URL_TEMPLATE.format(season_end=args.season_end, matchday=sd))
            soup = BeautifulSoup(html, "html.parser")
            scraped = collect_matches_from_soup(soup, sd)
            logging.info("Spieltag %d: %d Matches gescrapt", sd, len(scraped))
            scraped_all.extend(scraped)
            # kurze Pause, sei nett zum Server
            time.sleep(1.2)
        except Exception as e:
            logging.error("Fehler beim Scrapen Spieltag %s: %s", sd, e)

    if not scraped_all:
        logging.error("Keine Matches gescrapt. Abbruch.")
        return

    res = update_csv(csv_path, scraped_all, dry_run=args.dry_run)
    logging.info("Fertig: %s", res)

if __name__ == "__main__":
    main()
