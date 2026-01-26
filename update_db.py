import os
import subprocess
import sys
from datetime import datetime

PIPELINE_LOG = "pipeline_log.txt"
ERROR_LOG = "validation_errors.txt"

def write_log(file, message, is_error=False):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = "[FEHLER]" if is_error else "[INFO]"
    with open(file, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} {prefix} {message}\n")

def run_script(script_name):
    write_log(PIPELINE_LOG, f"Starte Skript: {script_name}")
    try:
        # Wir geben die Umgebungsvariablen explizit an den Unterprozess weiter
        result = subprocess.run(
            [sys.executable, script_name], 
            capture_output=True, 
            text=True, 
            check=True,
            env=os.environ.copy() 
        )
        if result.stdout:
            write_log(PIPELINE_LOG, f"Output {script_name}: {result.stdout.strip()}")
        write_log(PIPELINE_LOG, f"✅ {script_name} erfolgreich.")
        return True
    except subprocess.CalledProcessError as e:
        error_msg = f"Abbruch in {script_name}.\nStderr: {e.stderr}\nStdout: {e.stdout}"
        write_log(ERROR_LOG, error_msg, is_error=True)
        write_log(PIPELINE_LOG, f"❌ {script_name} fehlgeschlagen.", is_error=True)
        return False

def main():
    # Logs für diesen Run vorbereiten
    with open(PIPELINE_LOG, "a") as f: f.write(f"\n\n{'='*30}\nRUN {datetime.now()}\n")
    
    scripts = ["update_scrapper.py", "torschuetzenscrapper.py", "rekordspieler.py", "suender.py", "zuschauer.py"]
    
    success_count = 0
    for script in scripts:
        if run_script(script):
            success_count += 1

    # Erstelle eine Zusammenfassung für das GitHub Issue
    with open("issue_body.md", "w", encoding="utf-8") as f:
        f.write(f"## Pipeline Bericht {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
        f.write(f"- ✅ Erfolgreiche Skripte: {success_count}/{len(scripts)}\n")
        if os.path.exists(ERROR_LOG) and os.path.getsize(ERROR_LOG) > 0:
            f.write("\n### ⚠️ Gefundene Fehler:\n```\n")
            with open(ERROR_LOG, "r") as err_f:
                f.write(err_f.read())
            f.write("\n```")
        else:
            f.write("\n✅ Keine Fehler in der Validierung gefunden.")

if __name__ == "__main__":
    main()