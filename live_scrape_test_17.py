from update_scrapper import run_scrapper, update_csv_from_db

def live_test():
    print("🏟️ Starte Live-Test für Spieltag 17...")
    
    # Wir rufen deine Funktion auf, die wir gerade umgebaut haben
    # Sie wird versuchen, die aktuellen Spielstände zu lesen und zu speichern
    anzahl = run_scrapper(17)
    
    if anzahl > 0:
        print(f"✅ Erfolg! Es wurden {anzahl} Partien/Ergebnisse gefunden.")
        print("🚀 Diese sollten nun in deiner bundesliga.db UND in Supabase stehen.")
    else:
        print("❓ Keine Spiele gefunden. Prüfe, ob die URL im Scrapper korrekt ist.")

if __name__ == "__main__":
    live_test()