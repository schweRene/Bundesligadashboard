import streamlit as st
from streamlit_javascript import st_javascript


def start_router():
    # Session State initialisieren
    if "device_width" not in st.session_state:
        st.session_state.device_width = None
    try:
        curr_width = st_javascript("window.innerWidth")
    except:
        width = None

    if curr_width is not None and curr_width > 0:
        if st.session_state.device_width != curr_width:
            st.session_state.device_width = curr_width
            st.rerun()

    # Breite nur abfragen, wenn wir sie noch nicht haben
    if st.session_state.device_width is None:
        import main
        main.main()

    # Jetzt entscheiden wir basierend auf dem gespeicherten Wert
    if st.session_state.device_width is not None and st.session_state.device_width < 768:
        import mobile_app
        mobile_app.run_mobile_main()
    else:
        import main
        main.main()

if __name__ == "__main__":
    start_router()