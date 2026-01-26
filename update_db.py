import os
import subprocess
import sys
from datetime import datetime

# Dateien definieren
PIPELINE_LOG = "pipeline_log.txt"
ERROR_LOG = "validation_errors.txt"
ISSUE_BODY = "issue_body.md"

def write_log(file, message, is_error=False):
    """Schreibt Logs mit Zeitstempel und hängt sie an."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = "[FEHLER]" if is_error else "[INFO]"
    with open(file, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} {prefix} {message}\n")

def run_script(script_name):
    """Führt ein Skript aus und fängt dessen Ausgaben für das Log ab."""
    write_log(PIPELINE_LOG, f"Starte Skript: {script_name}")
    try:
        # env=os.environ.copy() stellt sicher, dass Secrets (DB_URL) an Unterprozesse gehen
        result = subprocess.run(
            [sys.executable, script_name], 
            capture_output=True, 
            text=True, 
            check=True,
            env=os.environ.copy()
        )
        if result.stdout:
            write_log(PIPELINE_LOG, f"Output {script_name}: {result.stdout.strip()}")
        write_log(PIPELINE_LOG, f"✅ {script_name} erfolgreich beendet.")
        return True
    except subprocess.CalledProcessError as e:
        error_msg = f"Abbruch in {script_name}.\nStderr: {e.stderr}\nStdout: {e.stdout}"
        write_log(ERROR_LOG, error_msg, is_error=True)
        write_log(PIPELINE_LOG, f"❌ {script_name} fehlgeschlagen.", is_error=True)
        return False

def main():
    # 1. Neuen Run im Log markieren
    write_log(PIPELINE_LOG, "\n" + "="*40)
    write_log(PIPELINE_LOG, f"🚀 START PIPELINE: {datetime.now()}")
    
    scripts = [
        "update_scrapper.py",
        "torschuetzenscrapper.py",
        "rekordspieler.py",
        "suender.py",
        "zuschauer.py"
    ]
    
    success_count = 0
    for script in scripts:
        if run_script(script):
            success_count += 1

    # 2. Issue Bericht erstellen (mit Kürzung der Logs gegen den "Body too long" Fehler)
    with open(ISSUE_BODY, "w", encoding="utf-8") as f:
        f.write(f"# 📊 Bundesliga Pipeline Bericht\n")
        f.write(f"**Zeitstempel:** {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n")
        f.write(f"### Status Übersicht\n")
        f.write(f"- ✅ Erfolgreiche Skripte: `{success_count}/{len(scripts)}`\n")
        
        # Fehler-Log auslesen (nur letzte 50 Zeilen)
        f.write("\n### ⚠️ Letzte Fehler\n")
        if os.path.exists(ERROR_LOG) and os.path.getsize(ERROR_LOG) > 0:
            f.write("```text\n")
            with open(ERROR_LOG, "r", encoding="utf-8") as err_f:
                lines = err_f.readlines()
                f.write("".join(lines[-50:]))
            f.write("```\n")
        else:
            f.write("✅ Keine neuen Fehler gefunden.\n")

        # Pipeline-Log auslesen (nur letzte 50 Zeilen)
        f.write("\n### 📄 Letzte Log-Einträge\n")
        if os.path.exists(PIPELINE_LOG):
            f.write("```text\n")
            with open(PIPELINE_LOG, "r", encoding="utf-8") as log_f:
                lines = log_f.readlines()
                f.write("".join(lines[-50:]))
            f.write("```\n")

    write_log(PIPELINE_LOG, f"🏁 PIPELINE BEENDET: {datetime.now()}")

if __name__ == "__main__":
    main()