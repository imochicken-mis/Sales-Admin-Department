import streamlit as st
import streamlit.components.v1 as components

def show():
    VERCEL_LINK = "https://kpi-dashboard-gold-rho.vercel.app/"

    # Page eke default padding/margin adu kara, iframe ekata pura idama denna CSS eka
    st.markdown("""
        <style>
            .block-container {
                padding-top: 3.5rem !important;
                padding-bottom: 0rem !important;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
                max-width: 100% !important;
            }
            /* Awashya nathi footer/toolbar hide karanna (sidebar ekata gena hena naha) */
            footer { display: none !important; }
            

            iframe {
                display: block;
            }
        </style>
    """, unsafe_allow_html=True)

    iframe_html = f'''
    <iframe src="{VERCEL_LINK}"
            style="width: 100%; height: calc(100vh - 70px); border: none; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.4);"
            allow="fullscreen">
    </iframe>
    '''

    st.markdown(iframe_html, unsafe_allow_html=True)

    # 3. Sidebar eka open/close wena eka detect karala Vercel ekata msg yawana Javascript eka
    sidebar_detector = """
    <script>
        const parentDoc = window.parent.document;
        function checkSidebar() {
            const sidebar = parentDoc.querySelector('[data-testid="stSidebar"]');
            const iframe = parentDoc.querySelector('iframe[src*="vercel.app"]');
            if (sidebar && iframe) {
                // Sidebar eka open wela thiyenawa nam 'isOpen' eka True wenawa
                const isOpen = sidebar.getBoundingClientRect().right > 0;
                // Vercel ekata signal eka yawanawa
                iframe.contentWindow.postMessage({ sidebarOpen: isOpen }, '*');
            }
        }
        // Hema thathpara kaalakatama (200ms) check karanawa
        setInterval(checkSidebar, 200);
    </script>
    """
    components.html(sidebar_detector, height=0, width=0)