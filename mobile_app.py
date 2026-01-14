import streamlit as st
import os
import pandas as pd


def show_mobile_startseite():
    st.markdown("<h1 style='text-align: center; color: darkred;'>⚽Bundesliga-Dashboard</h1>", unsafe_allow_html=True)
    if os.path.exists("bundesliga.jpg"):
        st.image("bundesliga.jpg", use_container_width=True)
        st.caption("Bildquelle: Pixabay")

def show_mobile_spieltage(df):
    # 1. Auswahl-Logik
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

    # 4. Cards anzeigen
    for _, row in current_df.iterrows():
        tore_h = int(row['tore_heim']) if pd.notna(row['tore_heim']) else "-"
        tore_g = int(row['tore_gast']) if pd.notna(row['tore_gast']) else "-"
        
        # Wir bauen den HTML-String in einer Variable zusammen (sauberer)
        card_html = (
            f'<div style="border: 2px solid #8B0000; border-radius: 10px; padding: 15px; '
            f'margin-bottom: 12px; background-color: white; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);">'
            f'<div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">'
            f'<div style="flex: 1; text-align: left; font-weight: bold; color: black !important; font-size: 14px;">{row["heim"]}</div>'
            f'<div style="flex: 0.5; text-align: center; background-color: #8B0000; color: white !important; '
            f'border-radius: 5px; padding: 5px 10px; font-weight: bold; font-size: 16px; margin: 0 10px; min-width: 65px;">'
            f'{tore_h} : {tore_g}</div>'
            f'<div style="flex: 1; text-align: right; font-weight: bold; color: black !important; font-size: 14px;">{row["gast"]}</div>'
            f'</div></div>'
        )
        
        # WICHTIG: Das unsafe_allow_html muss hier stehen!
        st.markdown(card_html, unsafe_allow_html=True)

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


