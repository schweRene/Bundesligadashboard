import streamlit as st
from streamlit_javascript import st_javascript


def start_router():
    # 1. URL-Parameter prüfen: Wenn ?view=mobile drin steht, erzwingt das oft die Ansicht
    params = st.query_params
    
    if 'device_width' not in st.session_state:
        st.session_state.device_width = None

    # 2. Breite messen
    width = st_javascript("window.innerWidth")

    if width is not None and width > 0:
        st.session_state.device_width = width
        
        # 3. AUTO-KORREKTUR: Wenn Desktop-Breite, aber Mobile-URL -> Parameter löschen!
        if width > 1000 and params.get("view") == "mobile":
            st.query_params.clear()
            st.rerun()

    # 4. Routing Entscheidung (Desktop-First)
    if st.session_state.device_width is not None and st.session_state.device_width < 768:
        import mobile_app
        mobile_app.run_mobile_main()
    else:
        import main
        main.main()

if __name__ == "__main__":
    start_router()