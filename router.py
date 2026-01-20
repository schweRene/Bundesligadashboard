import streamlit as st
from streamlit_javascript import st_javascript

import streamlit as st
from streamlit_javascript import st_javascript

def start_router():
    # 1. Sofortiger Desktop-Standard
    if 'device_width' not in st.session_state:
        st.session_state.device_width = 1200 

    # 2. Breite messen
    width = st_javascript("window.innerWidth")

    # 3. Validierung und URL-Cleanup
    if width is not None and width > 0:
        if st.session_state.device_width != width:
            st.session_state.device_width = width
            # Falls am Desktop noch "?view=mobile" in der URL steht -> weg damit
            if width > 1000 and st.query_params.get("view") == "mobile":
                st.query_params.clear()
            st.rerun()

    # 4. Routing (Nur unter 768px wird es Mobile)
    if st.session_state.device_width < 768:
        import mobile_app
        mobile_app.run_mobile_main()
    else:
        import main
        main.main()

if __name__ == "__main__":
    start_router()