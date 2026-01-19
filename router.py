import streamlit as st
from streamlit_javascript import st_javascript

#================================================================
# Diese Datei prüft beim Start die Bildschirmbreite des Nutzers.
# - Breite < 800px -> Mobile Version (mobile_app.py)
# - Breite >= 800px -> Desktop Version (main.py)
#================================================================

def starter_router():
    # Page-config einmalig setzen
    st.set_page_config(page_title="Bundesligadashboard", layout="wide")
    #JavaScript wird im Browser ausgeführt, um die Fensterbreite zu ermitteln
    width = st_javascript("window.innerWidth")

    #Falls die Breite noch ermittelt wird, wird ein Ladekreis angezeigt. 
    if width is None:
        #solange Javascript lädt, wird hier kurz gestoppt
        return

    if width < 800:
        # Import erst hier, damit nicht beide Apps gleichzeitig geladen werden
        import mobile_app
        mobile_app.run_mobile_main()
    else:
        import main
        main.main()
        
if __name__ == "__main__":
    starter_router()

