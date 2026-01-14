import streamlit as st
import os
from main import load_data_from_db

def show_mobile_startseite():
    st.markdown("<h1 style='text-align: center; color: darkred;'>⚽Bundesliga-Dashboard</h1>", unsafe_allow_html=True)
    if os.path.exists("bundesliga.jpg"):
        st.image("bundesliga.jpg", use_container_width=True)
        st.caption("Bildquelle: Pixabay")

def run_mobile_main():
    #Zentrieres Layout für die Handyansicht
    st.set_page_config(page_title="Bundesligadashboard", layout="centered")

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
        st.subheader("Spieltag")
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


