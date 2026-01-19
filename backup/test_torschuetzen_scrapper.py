import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
import io
import time

def run_test():
    print("---Starte Test scrappen der Torschützenlise")
    url = "https://www.fussballdaten.de/bundesliga/historie/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

    try:
        # 1. Webseite laden
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print("Erfolgreich: Webseite geladen")

        # 2. HTML parsen
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table') 
        
        if table is None:
            print("Fehler: Tabelle nicht gefunden!")
            return

        # 3. Tabelle einlesen mit StringIO
        table_html = io.StringIO(str(table))
        df_list = pd.read_html(table_html)
        df = df_list[0]
        
        # 4. Spalten präzise auswählen (#, Spieler, Spiele, Tore)
        df = df.iloc[:, :4] 
        df.columns = ["platz", "spieler", "spiele", "tore"]

        # 5. Datenreinigung
        # Wir filtern Zeilen, die im Feld 'platz' keine Ziffern haben
        df = df[df['platz'].astype(str).str.contains(r'^\d+$', na=False)].copy()
        
        # Typen konvertieren
        df['platz'] = df['platz'].astype(int)
        df['spiele'] = df['spiele'].astype(int)
        df['tore'] = df['tore'].astype(int)

        df_top50 = df.head(50)

        print(f"--- Daten-Vorschau (Platz {df_top50['platz'].min()} bis {df_top50['platz'].max()}) ---")
        print(df_top50.to_string(index=False))

        # 6. Als CSV speichern
        csv_name = "torschuetzen.csv"
        df.to_csv(csv_name, index=False, encoding="utf-8")
        
        print(f"\nErfolg! '{csv_name}' wurde mit {len(df_top50)} Einträgen erstellt.")
        
    except Exception as e:
        print(f"Fehler: {e}")

if __name__ == "__main__":
    run_test()



