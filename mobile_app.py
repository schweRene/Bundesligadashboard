import streamlit as st
import os
import pandas as pd


def show_mobile_startseite():
    st.markdown("<h1 style='text-align: center; color: darkred;'>⚽Bundesliga-Dashboard</h1>", unsafe_allow_html=True)
    if os.path.exists("bundesliga.jpg"):
        st.image("bundesliga.jpg", use_container_width=True)
        st.caption("Bildquelle: Pixabay")

def show_mobile_spieltage(df):
    # 1. Auswahl-Logik (Saison und Spieltag)
    saisons = sorted(df["saison"].unique(), reverse=True)
    selected_saison = st.selectbox("Saison wählen:", saisons, key="sb_saison")

    spieltage = sorted(df[df["saison"] == selected_saison]["spieltag"].unique())
    default_st = int(df[df["saison"] == selected_saison]["spieltag"].max())
    selected_st = st.selectbox("Spieltag wählen:", spieltage, index=spieltage.index(default_st))

    # 2. Überschrift (Zentriert & Darkred)
    st.markdown(f"<h2 style='text-align: center; color: #8B0000;'>⚽ {selected_st}. Spieltag</h2>", unsafe_allow_html=True)

    # 3. Spiele filtern
    mask = (df["saison"] == selected_saison) & (df["spieltag"] == selected_st)
    current_df = df[mask].copy()

    # 4. Anzeige der Spiele (Karten-Layout mit Spalten)
    for _, row in current_df.iterrows():
        tore_h = int(row['tore_heim']) if pd.notna(row['tore_heim']) else "-"
        tore_g = int(row['tore_gast']) if pd.notna(row['tore_gast']) else "-"
        
        # Ein Container mit Rahmen erzeugt die "Card"
        with st.container(border=True):
            # Wir teilen die Karte in 3 Spalten auf: [Heim | Ergebnis | Gast]
            col_heim, col_score, col_gast = st.columns([4, 2, 4])
            
            with col_heim:
                # Heimteam: Linksbündig, Fett
                # Wir nutzen hier st.write/st.markdown ohne CSS für die Namen,
                # damit Streamlit die Farbe (Schwarz/Weiß) passend zum Modus wählt.
                st.markdown(f"**{row['heim']}**")
            
            with col_score:
                # Ergebnis-Box: Hintergrund Dunkelrot wie Desktop
                st.markdown(f"""
                    <div style='background-color: #8B0000; color: white; text-align: center; 
                    border-radius: 5px; font-weight: bold; padding: 2px;'>
                        {tore_h}:{tore_g}
                    </div>
                """, unsafe_allow_html=True)
            
            with col_gast:
                # Gastteam: Rechtsbündig, Fett
                st.markdown(f"<div style='text-align: right;'><b>{row['gast']}</b></div>", unsafe_allow_html=True)

def show_mobile_saisontabelle(df):
    st.markdown(f"<h2 style='text-align: center; color: #8B0000;'>📊 Saisontabelle</h2>", unsafe_allow_html=True)
    
    # 1. Saison-Auswahl
    saisons = sorted(df["saison"].unique(), reverse=True)
    selected_saison = st.selectbox("Saison wählen:", saisons, key="sb_tabelle_saison")
    
    # 2. Daten filtern und Tabelle berechnen (Logik wie Desktop)
    saison_df = df[df["saison"] == selected_saison]
    
    stats = []
    teams = pd.concat([saison_df["heim"], saison_df["gast"]]).unique()
    
    for team in teams:
        h_games = saison_df[saison_df["heim"] == team]
        g_games = saison_df[saison_df["gast"] == team]
        
        # Nur abgeschlossene Spiele zählen
        h_played = h_games[h_games["tore_heim"].notna()]
        g_played = g_games[g_games["tore_gast"].notna()]
        
        sp = len(h_played) + len(g_played)
        if sp == 0: continue
        
        s = (len(h_played[h_played["tore_heim"] > h_played["tore_gast"]]) + 
             len(g_played[g_played["tore_gast"] > g_played["tore_heim"]]))
        u = (len(h_played[h_played["tore_heim"] == h_played["tore_gast"]]) + 
             len(g_played[g_played["tore_gast"] == g_played["tore_heim"]]))
        n = sp - s - u
        
        t_erz = h_played["tore_heim"].sum() + g_played["tore_gast"].sum()
        t_erh = h_played["tore_gast"].sum() + g_played["tore_heim"].sum()
        diff = int(t_erz - t_erh)
        pkt = int(s * 3 + u)
        
        stats.append({"Team": team, "Sp": sp, "Diff": diff, "Pkt": pkt})
    
    # Sortieren: Punkte, dann Differenz
    table_df = pd.DataFrame(stats).sort_values(by=["Pkt", "Diff"], ascending=False).reset_index(drop=True)
    table_df.index += 1 # Platzierung ab 1
    
    # 3. Anzeige als kompakte Liste (statt breiter Tabelle)
    # Header
    cols = st.columns([1, 4, 1, 1, 1])
    cols[0].write("**#**")
    cols[1].write("**Verein**")
    cols[2].write("**Sp**")
    cols[3].write("**+/-**")
    cols[4].write("**Pkt**")
    st.divider()

    for i, row in table_df.iterrows():
        # Jede Zeile bekommt einen leichten Hintergrund für bessere Lesbarkeit
        with st.container():
            c1, c2, c3, c4, c5 = st.columns([1, 4, 1, 1, 1])
            c1.write(f"{i}")
            c2.write(f"**{row['Team']}**")
            c3.write(f"{row['Sp']}")
            # Differenz farblich (grün/rot) markieren
            diff_color = "green" if row['Diff'] > 0 else "red" if row['Diff'] < 0 else "gray"
            c4.markdown(f"<span style='color:{diff_color};'>{row['Diff']}</span>", unsafe_allow_html=True)
            c5.write(f"**{row['Pkt']}**")
        st.divider()    

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
        st.subheader("Ewige Tabelle")
    elif menu == "Meisterschaften":
        st.subheader("Meisterschaften")
    elif menu == "Vereinsanalyse":
        st.subheader("Vereinsanalyse")
    elif menu == "Tippspiel":
        st.subheader("Tippspiel")
    elif menu == "Highscore":
        st.subheader("Highscore")    

if __name__ == "__main__":
    run_mobile_main()


