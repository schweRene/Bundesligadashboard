import streamlit as st
import os
import pandas as pd


def show_mobile_startseite():
    st.markdown("<h1 style='text-align: center; color: darkred;'>⚽Bundesliga-Dashboard</h1>", unsafe_allow_html=True)
    if os.path.exists("bundesliga.jpg"):
        st.image("bundesliga.jpg", use_container_width=True)
        st.caption("Bildquelle: Pixabay")

def show_mobile_spieltage(df):
    # 1. ERST die Auswahlmöglichkeiten definieren
    saisons = sorted(df["saison"].unique(), reverse=True)
    selected_saison = st.selectbox("Saison wählen:", saisons, key="sb_saison")

    spieltage = sorted(df[df["saison"] == selected_saison]["spieltag"].unique())
    default_st = int(df[df["saison"] == selected_saison]["spieltag"].max())
    
    # Hier wird die Variable 'selected_st' erst erschaffen:
    selected_st = st.selectbox("Spieltag wählen:", spieltage, index=spieltage.index(default_st))

    # 2. JETZT erst die Überschrift anzeigen (jetzt ist 'selected_st' bekannt)
    st.markdown(f"<h2 style='text-align: center; color: darkred;'>⚽ {selected_st}. Spieltag</h2>", unsafe_allow_html=True)

    # 3. Spiele filtern und Cards anzeigen (mit dem Desktop-Design)
    mask = (df["saison"] == selected_saison) & (df["spieltag"] == selected_st)
    current_df = df[mask].copy()

    for _, row in current_df.iterrows():
        with st.container():
            st.markdown(f"""
                <div style="border: 2px solid #8B0000; border-radius: 10px; padding: 10px; margin-bottom: 10px; background-color: #ffffff; color: #333333 !important;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="flex: 1; text-align: left; font-weight: bold; font-size: 0.9em; color: #333333 !important;">
                            {row['heim']}
                        </div>
                        <div style="flex: 0.6; text-align: center; font-size: 1.1em; background-color: #8B0000; color: white !important; border-radius: 5px; padding: 4px 8px; font-weight: bold; min-width: 60px;">
                            {int(row['tore_heim']) if pd.notna(row['tore_heim']) else '-'} : {int(row['tore_gast']) if pd.notna(row['tore_gast']) else '-'}
                        </div>
                        <div style="flex: 1; text-align: right; font-weight: bold; font-size: 0.9em; color: #333333 !important;">
                            {row['gast']}
                        </div>
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


