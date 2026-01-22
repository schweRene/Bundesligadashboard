import os
import subprocess
import sys

def run_script(script_name):
    print(f"\n--- Starte: {script_name} ---")
    try:
        # Führt das Skript aus und wartet, bis es fertig ist
        subprocess.run([sys.executable, script_name], check=True)
        print(f"✅ {script_name} erfolgreich beendet.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Fehler in {script_name}: {e}")

def main():
    print("🚀 Starte tägliches Bundesliga-Update...")

    # 1. Ergebnisse scannen (Das ist die update_scrapper.py)
    run_script("update_scrapper.py")

    # 2. Torschützen aktualisieren
    run_script("torschuetzenscrapper.py")

    # 3. Rekordspieler aktualisieren
    run_script("rekordspieler.py")

    # 4. Sünderkartei aktualisieren
    run_script("suender.py")

    # 5. Zuschauerzahlen aktualisieren
    run_script("zuschauer.py")

    print("\n✨ Alle Updates abgeschlossen!")

if __name__ == "__main__":
    main()