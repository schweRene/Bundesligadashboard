import streamlit as st
from streamlit_javascript import st_javascript

def start_router():
    # 1. Wir löschen aktiv den 'view' Parameter, falls wir am Desktop sind
    params = st.query_params
    
    # Initialisierung: Wir starten IMMER mit Desktop-Breite im Speicher
    if 'device_width' not in st.session_state:
        st.session_state.device_width = 1200 

    # 2. Breite messen
    width = st_javascript("window.innerWidth")

    # 3. Nur wenn wir einen validen Wert > 0 bekommen, aktualisieren wir
    if width is not None and width > 0:
        if st.session_state.device_width != width:
            st.session_state.device_width = width
            # Wenn wir am Desktop sind (Breite > 1000) aber die URL 'mobile' sagt -> Säubern!
            if width > 1000 and params.get("view") == "mobile":
                st.query_params.clear()
            st.rerun()

    # 4. DAS ROUTING: Nur wenn wir EINDEUTIG unter 768px sind, laden wir Mobile
    if st.session_state.device_width is not None and st.session_state.device_width < 768:
        import mobile_app
        mobile_app.run_mobile_main()
    else:
        # In allen anderen Fällen (None, 0, oder > 768) laden wir Desktop
        import main
        main.main()

if __name__ == "__main__":
    start_router()