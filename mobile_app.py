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
        st.subheader("Saisontabelle")
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


