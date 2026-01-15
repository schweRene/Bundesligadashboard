import streamlit as st
import os
import pandas as pd
from sqlalchemy import text

def show_mobile_startseite():
    st.markdown("<h3 style='text-align: center; color: darkred;'>⚽Bundesliga-Dashboard</h1>", unsafe_allow_html=True)
    if os.path.exists("bundesliga.jpg"):
        st.image("bundesliga.jpg", use_container_width=True)
        st.caption("Bildquelle: Pixabay")

def show_mobile_spieltage(df):
    # 1. Auswahl der Saison
    saisons = sorted(df["saison"].unique(), reverse=True)
    selected_saison = st.selectbox("Saison wählen:", saisons, key="sb_saison")

    # Filter für die gewählte Saison
    saison_df = df[df["saison"] == selected_saison]
    
    # --- LOGIK AUS DER main.py (Desktop-Version) ---
    # Wir suchen den letzten Spieltag mit Ergebnissen (dropna wie in main.py)
    played_matches = saison_df.dropna(subset=["tore_heim", "tore_gast"])
    
    if not played_matches.empty:
        # Höchster Spieltag mit Toren
        current_st = int(played_matches["spieltag"].max())
    else:
        # Falls noch keine Tore gefallen sind (Saisonstart)
        current_st = 1

    spieltage = sorted(saison_df["spieltag"].unique())
    
    # Index berechnen
    try:
        default_index = spieltage.index(current_st)
    except ValueError:
        default_index = 0

    # FIX: Dynamischer Key (st_sb_{selected_saison}) verhindert das Cache-Problem
    # beim Wechsel zwischen den Saisons.
    selected_st = st.selectbox(
        "Spieltag wählen:", 
        spieltage, 
        index=default_index, 
        key=f"st_sb_mobile_{selected_saison}"
    )

    # 2. Überschrift
    st.markdown(f"<h2 style='text-align: center; color: #8B0000;'>⚽ {selected_st}. Spieltag</h2>", unsafe_allow_html=True)

    # 3. Spiele für den gewählten Spieltag filtern
    mask = (df["saison"] == selected_saison) & (df["spieltag"] == selected_st)
    current_df = df[mask].copy()

    # Sicherheitsscheck: Falls der Sync kurzzeitig hakt
    if current_df.empty:
        st.info("Lade Daten für den gewählten Spieltag...")
        return

    for _, row in current_df.iterrows():
        # Tore formatieren (Desktop-Logik: int wenn vorhanden, sonst "-")
        tore_h = int(row['tore_heim']) if pd.notna(row['tore_heim']) else "-"
        tore_g = int(row['tore_gast']) if pd.notna(row['tore_gast']) else "-"
        
        with st.container(border=True):
            col_heim, col_score, col_gast = st.columns([4, 2, 4])
            with col_heim:
                st.write(f"**{row['heim']}**")
            with col_score:
                st.markdown(f"""
                    <div style='background-color: #8B0000; color: white; text-align: center; 
                    border-radius: 5px; font-weight: bold; padding: 2px;'>
                        {tore_h}:{tore_g}
                    </div>
                """, unsafe_allow_html=True)
            with col_gast:
                st.markdown(f"<div style='text-align: right;'><b>{row['gast']}</b></div>", unsafe_allow_html=True)

def show_mobile_saisontabelle(df):
    st.markdown(f"<h2 style='text-align: center; color: #8B0000;'>📊 Saisontabelle</h2>", unsafe_allow_html=True)
    
    # 1. Saison-Auswahl
    saisons = sorted(df["saison"].unique(), reverse=True)
    selected_saison = st.selectbox("Saison wählen:", saisons, key="sb_tabelle_saison")
    
    # 2. Daten filtern und Tabelle berechnen
    saison_df = df[df["saison"] == selected_saison]
    stats = []
    teams = pd.concat([saison_df["heim"], saison_df["gast"]]).unique()
    
    for team in teams:
        h_games = saison_df[saison_df["heim"] == team]
        g_games = saison_df[saison_df["gast"] == team]
        h_played = h_games[h_games["tore_heim"].notna()]
        g_played = g_games[g_games["tore_gast"].notna()]
        
        sp = len(h_played) + len(g_played)
        if sp == 0: continue
        
        s = (len(h_played[h_played["tore_heim"] > h_played["tore_gast"]]) + 
             len(g_played[g_played["tore_gast"] > g_played["tore_heim"]]))
        u = (len(h_played[h_played["tore_heim"] == h_played["tore_gast"]]) + 
             len(g_played[g_played["tore_gast"] == g_played["tore_heim"]]))
        
        diff = int((h_played["tore_heim"].sum() + g_played["tore_gast"].sum()) - 
                   (h_played["tore_gast"].sum() + g_played["tore_heim"].sum()))
        pkt = int(s * 3 + u)
        stats.append({"Team": team, "Sp": sp, "Diff": diff, "Pkt": pkt})
    
    table_df = pd.DataFrame(stats).sort_values(by=["Pkt", "Diff"], ascending=False).reset_index(drop=True)

    # 3. HTML-Tabelle sicher zusammenbauen
    # Wir definieren den Style separat als EINEN String ohne f-String-Variablen
    table_style = (
        "<style>"
        ".m-tab { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; margin-top: 10px; }"
        ".m-tab th { background-color: #8B0000; color: white !important; padding: 10px 5px; text-align: left; }"
        ".m-tab td { padding: 12px 5px; border-bottom: 1px solid #eee; color: black !important; background-color: white; }"
        "</style>"
    )

    # Header-Zeile
    table_html = table_style + (
        "<table class='m-tab'>"
        "<tr>"
        "<th style='width: 10%;'>#</th>"
        "<th style='width: 60%;'>Verein</th>"
        "<th style='width: 15%; text-align: center;'>Sp</th>"
        "<th style='width: 15%; text-align: center;'>Pkt</th>"
        "</tr>"
    )

    # Zeilen hinzufügen
    for i, row in table_df.iterrows():
        table_html += (
            f"<tr>"
            f"<td>{i+1}</td>"
            f"<td style='font-weight: bold;'>{row['Team']}</td>"
            f"<td style='text-align: center;'>{row['Sp']}</td>"
            f"<td style='text-align: center; font-weight: bold; color: #8B0000 !important;'>{row['Pkt']}</td>"
            f"</tr>"
        )
    
    table_html += "</table>"
    
    # 4. Ausgabe mit explizitem unsafe_allow_html
    st.markdown(table_html, unsafe_allow_html=True)  

def show_mobile_ewige_tabelle(df):
    st.markdown(f"<h2 style='text-align: center; color: #8B0000;'>🏆 Ewige Tabelle</h2>", unsafe_allow_html=True)

    # Daten berechnen (Logik für alle Saisons)
    stats = []
    teams = pd.concat([df["heim"], df["gast"]]).unique()

    for team in teams:
        h_played = df[(df["heim"] == team) & (df["tore_heim"].notna())]
        g_played = df[(df["gast"] == team) & (df["tore_gast"].notna())]

        sp = len(h_played) + len(g_played)
        if sp == 0: continue

        # KORREKTUR: Anführungszeichen bei Spaltennamen hinzugefügt
        s = (len(h_played[h_played["tore_heim"] > h_played["tore_gast"]]) +
             len(g_played[g_played["tore_gast"] > g_played["tore_heim"]]))
        
        u = (len(h_played[h_played["tore_heim"] == h_played["tore_gast"]]) +
             len(g_played[g_played["tore_gast"] == g_played["tore_heim"]]))
        
        pkt = int(s * 3 + u)
        stats.append({"Team": team, "Sp": sp, "Pkt": pkt})

    # Sortieren nach Punkten
    ewige_df = pd.DataFrame(stats).sort_values(by="Pkt", ascending=False).reset_index(drop=True)

    # Suchfunktion für Mobile
    search_term = st.text_input("Verein suchen...", "").lower()
    if search_term:
        # KORREKTUR: .contains() zu .str.contains() geändert für Pandas
        ewige_df = ewige_df[ewige_df["Team"].str.lower().str.contains(search_term)]

    # HTML-Tabelle (Robustes Mobile-Design)
    table_style = (
        "<style>"
        ".e-tab { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; }"
        ".e-tab th { background-color: #8B0000; color: white !important; padding: 10px 5px; text-align: left; }"
        ".e-tab td { padding: 12px 5px; border-bottom: 1px solid #eee; color: black !important; background-color: white; }"
        ".top3 { background-color: #fff7e6 !important; font-weight: bold; }"
        "</style>"
    )

    # KORREKTUR: Breite der Spalten angepasst, damit 'Verein' mehr Platz hat (55% statt 15%)
    table_html = table_style + (
        "<table class='e-tab'>"
        "<tr>"
        "<th style='width: 15%;'>Platz</th>"
        "<th style='width: 55%;'>Verein</th>"
        "<th style='width: 15%; text-align: center;'>Sp</th>"
        "<th style='width: 15%; text-align: center;'>Pkt</th>"
        "</tr>"
    )

    for i, row in ewige_df.iterrows():
        rank = i + 1
        special_class = "class='top3'" if rank <= 3 else ""

        table_html += (
            f"<tr {special_class}>"
            f"<td>{rank}.</td>"
            f"<td>{row['Team']}</td>"
            f"<td style='text-align: center;'>{row['Sp']}</td>"
            f"<td style='text-align: center; font-weight: bold; color: #8B0000 !important;'>{row['Pkt']}</td>"
            f"</tr>"
        )

    table_html += "</table>"
    st.markdown(table_html, unsafe_allow_html=True)

def show_mobile_meisterschaften(df):
    st.markdown(f"<h2 style='text-align: center; color: #8B0000;'>🏆 Meisterschaften</h2>", unsafe_allow_html=True)

    # 1. Titelträger pro Saison ermitteln
    titel_liste = []
    # Wichtig: Saisons sortieren, damit die Berechnung sauber durchläuft
    saisons = sorted(df["saison"].unique())

    for saison in saisons:
        saison_df = df[df["saison"] == saison].copy()
        
        # Nur Spiele berücksichtigen, die ein Ergebnis haben
        saison_df = saison_df.dropna(subset=["tore_heim", "tore_gast"])
        
        if saison_df.empty:
            continue

        stats = []
        teams = pd.concat([saison_df["heim"], saison_df["gast"]]).unique()

        for team in teams:
            # Heim- und Gastspiele filtern
            h_games = saison_df[saison_df["heim"] == team]
            g_games = saison_df[saison_df["gast"] == team]
            
            # Siege, Unentschieden, Tore berechnen
            s = (len(h_games[h_games["tore_heim"] > h_games["tore_gast"]]) + 
                 len(g_games[g_games["tore_gast"] > g_games["tore_heim"]]))
            u = (len(h_games[h_games["tore_heim"] == h_games["tore_gast"]]) + 
                 len(g_games[g_games["tore_gast"] == g_games["tore_heim"]]))
            
            t_erz = h_games["tore_heim"].sum() + g_games["tore_gast"].sum()
            t_erh = h_games["tore_gast"].sum() + g_games["tore_heim"].sum()
            diff = t_erz - t_erh
            pkt = s * 3 + u
            
            stats.append({"Team": team, "Pkt": pkt, "Diff": diff, "Tore": t_erz})
        
        # Sortierung wie in der Bundesliga: Punkte, dann Differenz, dann erzielte Tore
        temp_table = pd.DataFrame(stats).sort_values(by=["Pkt", "Diff", "Tore"], ascending=False)
        
        if not temp_table.empty:
            meister = temp_table.iloc[0]["Team"]
            titel_liste.append(meister)

    if not titel_liste:
        st.warning("Keine abgeschlossenen Saisons zur Berechnung gefunden.")
        return

    # 2. Zählen und Sortieren
    meister_counts = pd.Series(titel_liste).value_counts().reset_index()
    meister_counts.columns = ["Verein", "Titel"]

    # 3. HTML-Tabelle für Mobile
    table_style = (
        "<style>"
        ".m-tab { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 16px; }"
        ".m-tab th { background-color: #8B0000; color: white !important; padding: 12px; text-align: left; }"
        ".m-tab td { padding: 15px 12px; border-bottom: 1px solid #eee; color: black !important; background-color: white; }"
        ".count-badge { background-color: #8B0000; color: white; padding: 4px 10px; border-radius: 50%; font-weight: bold; }"
        "</style>"
    )

    table_html = table_style + (
        "<table class='m-tab'>"
        "<tr>"
        "<th style='width: 70%;'>Verein</th>"
        "<th style='width: 30%; text-align: center;'>Titel</th>"
        "</tr>"
    )

    for _, row in meister_counts.iterrows():
        table_html += (
            f"<tr>"
            f"<td style='font-weight: bold;'>{row['Verein']}</td>"
            f"<td style='text-align: center;'><span class='count-badge'>{row['Titel']}</span></td>"
            f"</tr>"
        )
    
    table_html += "</table>"
    st.markdown(table_html, unsafe_allow_html=True)

def show_mobile_vereinsanalyse(df):
    st.markdown(f"<h2 style='text-align: center; color: #8B0000;'>🔍 Vereinsanalyse</h2>", unsafe_allow_html=True)

    # VEREINS-AUSWAHL: Wir starten mit einer leeren Auswahl (""), 
    # damit du beim Tippen nichts löschen musst.
    alle_teams = sorted(pd.concat([df["heim"], df["gast"]]).unique().tolist())
    options = [""] + alle_teams
    
    # Kein Textfeld mehr, keine Aufforderung "Bitte wählen" in der Liste
    selected_team = st.selectbox("Verein suchen:", options, index=0, key="va_select")

    if selected_team == "":
        st.stop() # Beendet die Ausführung hier, bis ein Verein gewählt wird

    # Logik für Gegner-Statistik
    gegner_stats = []
    for gegner in [t for t in alle_teams if t != selected_team]:
        duelle = df[((df["heim"] == selected_team) & (df["gast"] == gegner)) | 
                    ((df["heim"] == gegner) & (df["gast"] == selected_team))].dropna(subset=["tore_heim", "tore_gast"])
        
        sp = len(duelle)
        if sp == 0: continue

        s, u, n = 0, 0, 0
        for _, row in duelle.iterrows():
            if row["tore_heim"] == row["tore_gast"]: u += 1
            elif (row["heim"] == selected_team and row["tore_heim"] > row["tore_gast"]) or \
                 (row["gast"] == selected_team and row["tore_gast"] > row["tore_heim"]): s += 1
            else: n += 1
        gegner_stats.append({"Gegner": gegner, "Sp": sp, "S": s, "U": u, "N": n})

    analysis_df = pd.DataFrame(gegner_stats).sort_values(by="Sp", ascending=False)

    table_style = (
        "<style>"
        ".v-tab { width: 100%; border-collapse: collapse; font-size: 12px; }"
        ".v-tab th { background-color: #8B0000; color: white !important; padding: 5px; text-align: center; }"
        ".v-tab td { padding: 8px 4px; border-bottom: 1px solid #eee; color: black !important; background-color: white; text-align: center; }"
        ".v-tab td:first-child { text-align: left; font-weight: bold; width: 40%; }"
        "</style>"
    )

    table_html = table_style + "<table class='v-tab'><tr><th>Gegner</th><th>Sp</th><th>S</th><th>U</th><th>N</th></tr>"
    for _, row in analysis_df.iterrows():
        table_html += (
            f"<tr><td>{row['Gegner']}</td><td>{row['Sp']}</td>"
            f"<td style='color: green;'>{row['S']}</td><td>{row['U']}</td>"
            f"<td style='color: red;'>{row['N']}</td></tr>"
        )
    table_html += "</table>"
    st.markdown(table_html, unsafe_allow_html=True)

import pandas as pd
import streamlit as st

def show_mobile_tippspiel(df):
    st.markdown("<h2 style='text-align: center; color: #8B0000;'>⚽ Tippspiel</h2>", unsafe_allow_html=True)
    
    # 1. LOGIK (Bleibt identisch zu deiner Desktop-Version)
    aktuelle_saison = str(df["saison"].max())
    offene_spieltage = sorted(df[(df["saison"] == aktuelle_saison) & (df["tore_heim"].isna())]["spieltag"].unique())

    if offene_spieltage:
        selected_st = st.selectbox("Spieltag auswählen:", offene_spieltage, key="mob_st_select")
        
        mask = (df["saison"] == aktuelle_saison) & (df["spieltag"] == selected_st) & (df["tore_heim"].isna())
        current_st_df = df[mask].sort_values("heim")

        st.subheader(f"Tipps für den {selected_st}. Spieltag")

        # FORMULAR START
        with st.form("mobile_tipp_form"):
            tipps_data = {} 
            
            for idx, row in current_st_df.iterrows():
                # Karte für jedes Spiel
                with st.container(border=True):
                    # Teams zentriert anzeigen
                    st.markdown(f"<div style='text-align: center; font-weight: bold;'>{row['heim']} - {row['gast']}</div>", unsafe_allow_html=True)
                    
                    # Eingabe-Layout: [Heim-Zahl, Trenner, Gast-Zahl]
                    # Nur 3 Spalten sind mobil stabil
                    c1, c2, c3 = st.columns([2, 1, 2])
                    with c1:
                        th = st.number_input("Heim", 0, 20, 0, 1, key=f"mh_{idx}", label_visibility="collapsed")
                    with c2:
                        st.markdown("<h3 style='text-align: center; margin: 0;'>:</h3>", unsafe_allow_html=True)
                    with c3:
                        tg = st.number_input("Gast", 0, 20, 0, 1, key=f"mg_{idx}", label_visibility="collapsed")
                    
                    tipps_data[idx] = (th, tg)

            st.markdown("---")
            user_name = st.text_input("Dein Name:", placeholder="Pflichtfeld", key="mob_user_name")
            
            # Button nutzt volle Breite auf Mobile
            submit = st.form_submit_button("Tipps speichern", use_container_width=True)

            if submit:
                if not user_name:
                    st.error("Bitte gib deinen Namen ein!")
                else:
                    from main import save_tipp
                    erfolgreich = True
                    for idx, (th, tg) in tipps_data.items():
                        row = current_st_df.loc[idx]
                        status, msg = save_tipp(user_name, aktuelle_saison, selected_st, row["heim"], row["gast"], th, tg)
                        if not status: erfolgreich = False
                    
                    if erfolgreich:
                        st.success("Gespeichert!")
                        st.rerun()
    else:
        st.info("Keine Spiele verfügbar.")

    # 2. AUSWERTUNG (Karten statt Tabelle für Mobile)
    st.markdown("---")
    st.subheader("📊 Deine Auswertung")
    check_user = st.text_input("Name für Check:", key="mob_check_user")
    
    if check_user:
        from main import get_conn
        conn = get_conn()
        # SQL Logik bleibt gleich, aber wir nutzen LOWER/TRIM für Handy-Tastaturen (Autokorrektur-Leerzeichen)
        query = """
            SELECT t.spieltag, t.heim, t.gast, t.tipp_heim, t.tipp_gast, t.punkte, s.tore_heim, s.tore_gast
            FROM tipps t
            JOIN spiele s ON t.saison = s.saison AND t.spieltag = s.spieltag AND t.heim = s.heim
            WHERE LOWER(TRIM(t."user")) = LOWER(TRIM(:u)) AND t.saison = :s
            ORDER BY t.spieltag DESC, t.heim ASC
        """
        user_tipps = conn.query(query, params={"u": str(check_user), "s": str(aktuelle_saison)}, ttl=0)
        
        if not user_tipps.empty:
            st.metric("Gesamtpunkte", f"{int(user_tipps['punkte'].sum())} Pkt.")
            
            for _, row in user_tipps.iterrows():
                with st.container(border=True):
                    # Kopfzeile Karte
                    c_header_1, c_header_2 = st.columns([1, 1])
                    c_header_1.write(f"**ST {row['spieltag']}**")
                    p_color = "#28a745" if row['punkte'] > 0 else "#6c757d"
                    c_header_2.markdown(f"<div style='text-align:right;'><span style='background-color:{p_color}; color:white; padding:2px 8px; border-radius:5px;'>{int(row['punkte'])} Pkt</span></div>", unsafe_allow_html=True)
                    
                    # Spiel & Ergebnis
                    st.write(f"{row['heim']} vs. {row['gast']}")
                    tipp_erg = f"{int(row['tipp_heim'])}:{int(row['tipp_gast'])}"
                    real_erg = f"{int(row['tore_heim'])}:{int(row['tore_gast'])}" if pd.notna(row['tore_heim']) else "-"
                    
                    st.caption(f"Dein Tipp: {tipp_erg} | Real: {real_erg}")
        else:
            st.info("Keine Tipps gefunden. Prüfe die Schreibweise.")

def run_mobile_main():
    #Zentrieres Layout für die Handyansicht
    st.set_page_config(page_title="Bundesliga Dashboard", layout="centered")

    from main import load_data_from_db

    #Laden der Daten aus der Hauptdatei
    df = load_data_from_db()
    if df.empty:
        st.error("Daten konnten nicht geladen werden.")
        return
    
    #Navigation oben
    menu = st.selectbox("Navigation", ["Startseite", "Spieltage", "Saisontabelle", "Ewige Tabelle", "Meisterschaften", "Vereinsanalyse", "Tippspiel", "Highscore"])

    if menu == "Startseite":
        show_mobile_startseite()
    elif menu == "Spieltage":
        show_mobile_spieltage(df)
    elif menu == "Saisontabelle":
        show_mobile_saisontabelle(df)
    elif menu == "Ewige Tabelle":
        show_mobile_ewige_tabelle(df)
    elif menu == "Meisterschaften":
        show_mobile_meisterschaften(df)
    elif menu == "Vereinsanalyse":
        show_mobile_vereinsanalyse(df)
    elif menu == "Tippspiel":
        show_mobile_tippspiel(df)
    elif menu == "Highscore":
        st.subheader("Highscore")    

if __name__ == "__main__":
    run_mobile_main()


   