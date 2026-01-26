import os
import subprocess
import sys
from datetime import datetime

# Definition der Log-Dateien
PIPELINE_LOG = "pipeline_log.txt"
ERROR_LOG = "validation_errors.txt"

def write_log(file, message, is_error=False):
    """Hängt Nachrichten mit Zeitstempel an die Log-Dateien an."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = "[FEHLER]" if is_error else "[INFO]"
    with open(file, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} {prefix} {message}\n")

def run_script(script_name):
    """Führt eine Python-Datei aus und loggt alles, was das Skript ausgibt."""
    if not os.path.exists(script_name):
        msg = f"Datei nicht gefunden: {script_name}"
        write_log(ERROR_LOG, msg, is_error=True)
        print(f"❌ {msg}")
        return False

    write_log(PIPELINE_LOG, f">>> STARTE SKRIPT: {script_name}")
    try:
        # Führt das Skript aus und fängt Terminal-Ausgaben ab
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            check=True
        )
        # Logge die normalen Prints des Skripts
        if result.stdout:
            write_log(PIPELINE_LOG, f"Output {script_name}:\n{result.stdout.strip()}")
        
        write_log(PIPELINE_LOG, f"✅ {script_name} erfolgreich beendet.")
        print(f"✅ {script_name} erledigt.")
        return True

    except subprocess.CalledProcessError as e:
        # Logge Fehlermeldungen (stderr)
        err_msg = f"Crash in {script_name}!\nFehler: {e.stderr}"
        write_log(ERROR_LOG, err_msg, is_error=True)
        write_log(PIPELINE_LOG, f"❌ {script_name} fehlgeschlagen.", is_error=True)
        print(f"❌ Fehler in {script_name}. Siehe validation_errors.txt")
        return False

def main():
    # Markierung für einen neuen Durchlauf
    header = f"\n{'='*50}\nSTART PIPELINE RUN: {datetime.now()}\n{'='*50}"
    write_log(PIPELINE_LOG, header)

    # Hier definieren wir ALLE Dateien, die ausgeführt werden sollen
    scripts_to_run = [
        "update_scrapper.py",
        "torschuetzenscrapper.py",
        "rekordspieler.py",
        "suender.py",
        "zuschauer.py"
    ]

    for script in scripts_to_run:
        run_script(script)

    write_log(PIPELINE_LOG, f"\nPIPELINE BEENDET AM: {datetime.now()}\n{'-'*50}")

if __name__ == "__main__":
    main()