import streamlit as st
# Page Config MUSS die erste Streamlit-Zeile sein
st.set_page_config(page_title="Bundesliga Dashboard", layout="wide")

from streamlit_javascript import st_javascript



def start_router():
    # Session State initialisieren
    if "device_width" not in st.session_state:
        st.session_state.device_width = None

    # Breite nur abfragen, wenn wir sie noch nicht haben
    if st.session_state.device_width is None:
        width = st_javascript("window.innerWidth")
        if width is not None and width > 0:
            st.session_state.device_width = width
            st.rerun()
        else:
            # Während er wartet, zeigen wir kurz was an
            st.info("Layout wird geladen")
            return

    # Jetzt entscheiden wir basierend auf dem gespeicherten Wert
    if st.session_state.device_width < 1000:
        import mobile_app
        mobile_app.run_mobile_main()
    else:
        import main
        main.main()

if __name__ == "__main__":
    start_router()