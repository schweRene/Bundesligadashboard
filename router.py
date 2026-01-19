import streamlit as st
from streamlit_javascript import st_javascript

def start_router():
    params = st.query_params
    
    # 1. Initialisierung: Wir gehen standardmäßig von Desktop aus (z.B. 1200)
    if 'device_width' not in st.session_state:
        st.session_state.device_width = 1200 

    # 2. Breite messen
    width = st_javascript("window.innerWidth")

    # 3. Validierung: Nur bei echtem Wert updaten
    if width is not None and width > 0:
        if st.session_state.device_width != width:
            st.session_state.device_width = width
            
            # Falls am Desktop fälschlicherweise die Mobile-URL aktiv ist -> Säubern
            if width > 1000 and params.get("view") == "mobile":
                st.query_params.clear()
            
            st.rerun()

    # 4. Entscheidung (Schwellenwert 768px für Mobile)
    if st.session_state.device_width < 768:
        import mobile_app
        mobile_app.run_mobile_main()
    else:
        import main
        main.main()

if __name__ == "__main__":
    start_router()