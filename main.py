#!/usr/bin/env python3
# coding: utf-8

import streamlit as st
import pandas as pd
from sqlalchemy import text

# ==========================================
# 1. DATENBANK-VERBINDUNG & TEST
# ==========================================

def get_conn():
    """Erstellt eine Verbindung mit expliziten Projekt-Optionen."""
    # Wir holen die Daten aus den Secrets
    creds = st.secrets["connections"]["postgresql"]
    
    # Wir bauen die URL manuell zusammen
    # Das Format für den Pooler ist: user.project:pass@host:port/db
    user_with_project = f"{creds['username']}.{creds['project']}"
    conn_url = f"postgresql://{user_with_project}:{creds['password']}@{creds['host']}:{creds['port']}/{creds['database']}"
    
    return st.connection("postgresql", type="sql", url=conn_url)

def check_connection():
    """Testet die Verbindung mit einer einfachen SQL-Abfrage."""
    try:
        conn = get_conn()
        # Wir führen eine echte SQL-Abfrage aus, um sicherzugehen
        with conn.session as s:
            result = s.execute(text("SELECT current_user, current_database();"))
            row = result.fetchone()
        return True, f"✅ Verbunden als: {row[0]} auf DB: {row[1]}"
    except Exception as e:
        return False, f"❌ Verbindung fehlgeschlagen: {str(e)}"

def load_data_from_db():
    """Lädt die Spieldaten aus der Tabelle 'spiele'."""
    try:
        conn = get_conn()
        df = conn.query("SELECT * FROM spiele", ttl=0)
        if df.empty:
            return pd.DataFrame()
        df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception:
        return pd.DataFrame()

# ==========================================
# 2. TIPPSPIEL LOGIK (Originale Namen)
# ==========================================

def save_tipp(user, saison, spieltag, heim, gast, th, tg):
    """Speichert den Tipp. Punkte bleiben NULL (werden später berechnet)."""
    conn = get_conn()
    with conn.session as session:
        # 'user' ist ein SQL-Keywort, daher in Anführungszeichen
        # Wir lassen 'punkte' hier weg, da sie erst später berechnet werden
        sql = text("""
            INSERT INTO tipps ("user", saison, spieltag, heim, gast, tipp_heim, tipp_gast)
            VALUES (:u, :s, :st, :h, :g, :th, :tg)
        """)
        session.execute(sql, {
            "u": user, "s": saison, "st": int(spieltag), 
            "h": heim, "g": gast, "th": int(th), "tg": int(tg)
        })
        session.commit()

def evaluate_tipps(df_spiele, user):
    """Berechnet Punkte für offene Tipps (wo punkte IS NULL)."""
    conn = get_conn()
    try:
        with conn.session as session:
            sql_tipps = text('SELECT * FROM tipps WHERE "user" = :u AND punkte IS NULL')
            tipps = conn.query(sql_tipps, params={"u": user}, ttl=0)
            
            for _, tipp in tipps.iterrows():
                match = df_spiele[
                    (df_spiele['saison'] == tipp['saison']) & 
                    (df_spiele['heim'] == tipp['heim']) & 
                    (df_spiele['gast'] == tipp['gast'])
                ]
                
                if not match.empty and pd.notna(match.iloc[0]['tore_heim']):
                    t_h_echt, t_g_echt = int(match.iloc[0]['tore_heim']), int(match.iloc[0]['tore_gast'])
                    t_h_tipp, t_g_tipp = int(tipp['tipp_heim']), int(tipp['tipp_gast'])
                    
                    pkt = 0
                    if t_h_echt == t_h_tipp and t_g_echt == t_g_tipp: pkt = 3
                    elif (t_h_echt - t_g_echt) == (t_h_tipp - t_g_tipp): pkt = 2
                    elif (t_h_echt > t_g_echt and t_h_tipp > t_g_tipp) or (t_h_echt < t_g_echt and t_h_tipp < t_g_tipp): pkt = 1
                    
                    session.execute(text('UPDATE tipps SET punkte = :p WHERE id = :tid'), 
                                    {"p": pkt, "tid": tipp['id']})
            session.commit()
    except Exception as e:
        st.error(f"Fehler bei Auswertung: {e}")

# ==========================================
# 3. SEITEN-ANZEIGE
# ==========================================

def show_tippspiel(df):
    st.title("🎯 Tippspiel")
    
    aktuelle_saison = sorted(df["saison"].unique(), reverse=True)[0]
    zukunft_spiele = df[(df['saison'] == aktuelle_saison) & (df['tore_heim'].isna())].copy()
    
    if zukunft_spiele.empty:
        st.info("Keine offenen Spiele zum Tippen gefunden.")
        return

    spieltag_tippen = st.selectbox("Wähle den Spieltag:", sorted(zukunft_spiele['spieltag'].unique()))
    spiele_auswahl = zukunft_spiele[zukunft_spiele['spieltag'] == spieltag_tippen]

    # Tipps in einer Liste sammeln (ohne st.form)
    tipp_sammler = []
    for idx, zeile in spiele_auswahl.iterrows():
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{zeile['heim']}** - **{zeile['gast']}**")
        h = c2.number_input("H", 0, 20, 0, key=f"h_{idx}")
        g = c3.number_input("G", 0, 20, 0, key=f"g_{idx}")
        tipp_sammler.append({"h": h, "g": g, "heim": zeile['heim'], "gast": zeile['gast']})
    
    nutzer_name = st.text_input("Dein Name:", key="user_input_name")
    
    if st.button("🚀 Tipps jetzt speichern"):
        # Rückmeldung, dass der Button-Klick erkannt wurde
        st.info("Verbindung wird geprüft und Daten werden übertragen...")
        
        if not nutzer_name.strip():
            st.warning("Bitte gib einen Namen ein!")
        else:
            try:
                for t in tipp_sammler:
                    save_tipp(nutzer_name.strip(), aktuelle_saison, spieltag_tippen, t['heim'], t['gast'], t['h'], t['g'])
                st.success(f"✅ Tipps für {nutzer_name} erfolgreich gespeichert!")
                st.balloons()
            except Exception as e:
                st.error(f"❌ FEHLER BEIM SPEICHERN: {e}")

# ==========================================
# 4. HAUPTPROGRAMM (MAIN)
# ==========================================

def main():
    st.set_page_config(page_title="Bundesliga Cloud Dashboard", layout="wide")
    
    # --- VERBINDUNGSTEST ---
    success, message = check_connection()
    if success:
        st.sidebar.success(message)
    else:
        st.sidebar.error(message)
        st.error("Datenbankverbindung fehlgeschlagen! Bitte die Streamlit Secrets prüfen.")
        return # App stoppen, wenn keine DB da ist

    # Daten laden
    df = load_data_from_db()
    if df.empty:
        st.warning("Keine Daten in der Tabelle 'spiele' gefunden.")
        return

    seite = st.sidebar.radio("Navigation", ["Startseite", "Tippspiel"])

    if seite == "Startseite":
        st.title("⚽ Dashboard Startseite")
        st.write("Verbindung zur Cloud-DB steht.")
    elif seite == "Tippspiel":
        show_tippspiel(df)

if __name__ == "__main__":
    main()
