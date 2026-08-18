import streamlit as st
import streamlit.components.v1 as components

def show():
    # Oyage Vercel link eka methanata danna
    VERCEL_LINK = "https://kpi-vercel-app.vercel.app/"
    
    st.write("Redirecting to Dashboard...")
    
    # Ekama tab eke (current tab) Vercel link eka load wena code eka
    redirect_html = f'<meta http-equiv="refresh" content="0; url={VERCEL_LINK}">'
    st.markdown(redirect_html, unsafe_allow_html=True)