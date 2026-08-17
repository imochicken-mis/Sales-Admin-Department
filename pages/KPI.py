import streamlit as st
import streamlit.components.v1 as components

def show():
    st.write("") # පොඩි ඉඩක් තැබීමට
    
    # 🚀 ඔයාට Vercel එකෙන් හම්බවුණු අලුත් ලින්ක් එක මෙතනට දාන්න
    VERCEL_URL = "https://vercel-html-kappa-cyan.vercel.app/" 
    
    # Vercel සයිට් එක Streamlit ඇතුළට ගෙන ඒම
    # height එක 900px දීලා තියෙන්නේ scrollbar එක පේන එක නවත්තන්න.
    components.iframe(VERCEL_URL, width=None, height=900, scrolling=True)

if __name__ == "__main__":
    show()