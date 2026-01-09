import pandas as pd
import os
from datetime import datetime

# === Konfig ===
CSV_FILE = "bundesliga_2026.csv"
LOG_FILE = "validation_errors.txt"

def validate_csv():
    if not os.path.exists(CSV_FILE):
        print(f"Fehler: {CSV_FILE} wurde nicht gefunden.")
        return

    try:
        df = pd.read_csv(CSV_FILE)
        df.columns = [c.lower() for c in df.columns]
        errors = []
        
        # --- Fortschritts-Analyse ---
        total_games = len(df)
        # Spiele mit Ergebnis zählen (alles außer -:-)
        played_games = df[df['result'] != "-:-"].shape[0]
        upcoming_games = df[df['result'] == "-:-"].shape[0]
        progress_percent = (played_games / total_games) * 100 if total_games > 0 else 0

        # --- Die bisherigen Checks ---
        # 1. Spieltag-Vollständigkeit
        st_counts = df.groupby('spieltag').size()
        for st, count in st_counts.items():
            if count != 9:
                errors.append(f"Spieltag {st}: Unvollständig ({count}/9 Spiele).")

        # 2. Team-Doppelbelegung pro Spieltag
        for st in df['spieltag'].unique():
            st_df = df[df['spieltag'] == st]
            teams = pd.concat([st_df['home'], st_df['away']])
            dupes = teams[teams.duplicated()].unique()
            if len(dupes) > 0:
                for team in dupes:
                    errors.append(f"Spieltag {st}: Team '{team}' ist doppelt belegt!")

        # 3. Symmetrie (Hin-/Rückrunde)
        df['pair'] = df.apply(lambda x: tuple(sorted([str(x['home']).strip(), str(x['away']).strip()])), axis=1)
        pair_counts = df['pair'].value_counts()
        for pair, count in pair_counts.items():
            if count != 2:
                errors.append(f"Paarung {pair}: {count} statt 2 Spiele gefunden.")

        # 4. Heim/Auswärts-Balance (17/17)
        all_teams = set(df['home']).union(set(df['away']))
        for team in all_teams:
            h = (df['home'] == team).sum()
            a = (df['away'] == team).sum()
            if h != 17 or a != 17:
                errors.append(f"Balance '{team}': {h} Heim / {a} Auswärts (Soll: 17/17).")

        # Log schreiben
        stats = {
            "total": total_games,
            "played": played_games,
            "upcoming": upcoming_games,
            "percent": round(progress_percent, 1)
        }
        write_log(errors, stats)
        return len(errors) == 0

    except Exception as e:
        print(f"Technischer Fehler: {e}")

def write_log(errors, stats):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"PRÜFUNG VOM: {timestamp}\n")
        f.write(f"SAISON-FORTSCHRITT: {stats['played']} gespielt / {stats['upcoming']} offen (Gesamt: {stats['total']})\n")
        f.write(f"STATUS: {stats['percent']}% der Saison absolviert.\n")
        f.write(f"{'-'*60}\n")
        
        if not errors:
            f.write("✅ VALIDIERUNG: Keine logischen Fehler gefunden.\n")
            print(f"[{timestamp}] Audit erfolgreich (Fortschritt: {stats['percent']}%).")
        else:
            f.write(f"❌ VALIDIERUNG: {len(errors)} Fehler gefunden:\n")
            for error in errors:
                f.write(f"  - {error}\n")
            print(f"[{timestamp}] {len(errors)} Fehler dokumentiert.")
        f.write(f"{'='*60}\n")

if __name__ == "__main__":
    validate_csv()
    