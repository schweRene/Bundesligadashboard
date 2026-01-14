import streamlit as st
import os
import pandas as pd


def show_mobile_startseite():
    st.markdown("<h1 style='text-align: center; color: darkred;'>⚽Bundesliga-Dashboard</h1>", unsafe_allow_html=True)
    if os.path.exists("bundesliga.jpg"):
        st.image("bundesliga.jpg", use_container_width=True)
        st.caption("Bildquelle: Pixabay")

def show_mobile_spieltage(df):
    st.markdown("<h2 style='text-align: center;'>⚽ {selected_st}. Spieltag</h2>", unsafe_allow_html=True)

    # Saison- Und Spieltagsauswahl
    saisons = sorted(df["saison"].unique(), reverse=True)
    selected_saison = st.selectbox("Saison wählen:", saisons, key="sb_saison")

    spieltage = sorted(df[df["saison"] == selected_saison]["spieltag"].unique())
    #Standardmäßig den aktuellesten/letzten Spieltag wählen
    default_st = int(df[df["saison"] == selected_saison]["spieltag"].max())
    selected_st = st.selectbox("Spieltag wählen:", spieltage, index=spieltage.index(default_st))

    #Spiele filtern
    mask = (df["saison"] == selected_saison) & (df["spieltag"] == selected_st)
    current_df = df[mask].copy()

    st.markdown(f"<h3 style='text-align: center;'>{selected_st}. Spieltag</h3>", unsafe_allow_html=True)

    #Spiele als "Cards" anzeigen
    for _, row in current_df.iterrows():
        with st.container():
            #ein schmaler Rahmen um jedes Spiel
            st.markdown(f"""
                <div style="border: 1px solid #ddd; border-radius: 10px; padding: 10px; margin-bottom: 10px; background-color: #f9f9f9; color: #333 !important;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="flex: 1; text-align: left; font-weight: bold; color: #333 !important;">{row['heim']}</div>
                        <div style="flex: 0.6; text-align: center; font-size: 1.2em; background: #333; color: white; border-radius: 5px; padding: 2px 5px; font-weight: bold;">
                            {int(row['tore_heim']) if pd.notna(row['tore_heim']) else '-'} : {int(row['tore_gast']) if pd.notna(row['tore_gast']) else '-'}
                        </div>
                        <div style="flex: 1; text-align: right; font-weight: bold; color: #333 !important;">{row['gast']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

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


