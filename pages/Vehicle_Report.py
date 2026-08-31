import streamlit as st
import pandas as pd
from datetime import datetime
import base64
import gspread

# util.py එකෙන් Connection ලබාගැනීම
try:
    from util import connect_to_sheets
except ImportError:
    st.error("⚠️ Error: Could not import connection functions from util.py")

def show():
    # ==========================================
    # 1. Custom CSS Theme & KPI Cards Design
    # ==========================================
    st.markdown("""
        <style>
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            max-width: 98% !important;
            overflow-x: hidden !important;
            min-height: 85vh !important;
        }
        [data-testid="stHeader"] { background: transparent !important; }
        
        div[data-testid="stDateInput"] label p {
            font-family: 'Arial', sans-serif !important;
            font-weight: 800 !important;
            font-size: 15px !important;
            color: #03045E !important;
        }
        div[data-baseweb="input"] {
            border: 2px solid #0096C7 !important; 
            border-radius: 8px !important;        
            background-color: #F8FDFF !important; 
            transition: all 0.3s ease-in-out;
        }
        div[data-baseweb="input"]:focus-within {
            border: 2px solid #03045E !important;
            box-shadow: 0 0 8px rgba(3, 4, 94, 0.4) !important;
        }
        
        /* 🚀 Custom KPI Cards Design */
        .kpi-container {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 25px;
            margin-top: 10px;
        }
        .kpi-card {
            flex: 1;
            min-width: 150px;
            background: linear-gradient(135deg, #F8FDFF 0%, #EAF8FF 100%);
            border: 2px solid #0096C7;
            border-radius: 16px;
            padding: 20px 15px;
            text-align: center;
            box-shadow: 0 6px 16px rgba(3, 4, 94, 0.08);
            transition: all 0.3s ease-in-out;
        }
        .kpi-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 12px 24px rgba(3, 4, 94, 0.15);
        }
        .kpi-title {
            color: #03045E;
            font-size: 15px;
            font-weight: 800;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .kpi-value {
            color: #0096C7;
            font-size: 32px;
            font-weight: 900;
        }
        
        /* Specific Colors for Status Cards */
        .card-success {
            background: linear-gradient(135deg, #F4FFF6 0%, #D4EDDA 100%);
            border-color: #28a745;
        }
        .card-success .kpi-value { color: #155724; }
        
        .card-danger {
            background: linear-gradient(135deg, #FFF4F4 0%, #FFD1D1 100%);
            border-color: #dc3545;
        }
        .card-danger .kpi-value { color: #900000; }
        
        /* 🚀 Table CSS */
        .table-container {
            max-height: 550px;
            overflow-y: auto;
            overflow-x: auto;
            border-radius: 12px;
            border: 2px solid #0096C7;
            box-shadow: 0 8px 24px rgba(3, 4, 94, 0.1);
            background-color: #FFFFFF;
            margin-bottom: 15px;
        }
        .table-container::-webkit-scrollbar { width: 8px; height: 8px; }
        .table-container::-webkit-scrollbar-track { background: transparent; }
        .table-container::-webkit-scrollbar-thumb { background: #0096C7; border-radius: 10px; }
        .table-container table {
            width: 100%;
            border-collapse: collapse !important;
            border-spacing: 0;
            font-family: 'Arial', sans-serif;
            font-size: 13px;
            border: 1px solid #ADE8F4 !important;
        }
        .table-container th {
            position: sticky;
            top: 0;
            z-index: 2;
            padding: 12px 8px;
            text-align: center !important;
            color: #FFFFFF !important;
            font-weight: 900;
            background-color: #00245e !important;
            border: 1px solid #ADE8F4 !important;
            border-bottom: 2px solid #0096C7 !important;
        }
        .table-container td {
            border: 1px solid #ADE8F4 !important;
            padding: 10px 8px;
            text-align: center;
            white-space: nowrap;
        }
        .table-container td:first-child {
            text-align: left !important;
            font-weight: bold;
            color: #03045E;
        }
        .table-container tbody tr:nth-child(even) { background-color: #F8FDFF !important; }
        .table-container tbody tr:nth-child(odd) { background-color: #FFFFFF !important; }
        .table-container tbody tr:hover td { background-color: #EAF8FF !important; transition: 0.2s; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='text-align: center; color: #03045E; font-weight: 800;'>🚛 Vehicle Operations Report</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #0077B6; font-weight: 600;'>Daily overview of Vehicle Routes, Capacities, and Status.</p>", unsafe_allow_html=True)
    st.write("")

    sheet = connect_to_sheets()

    # ==========================================
    # 2. Fetch Data from Google Sheets
    # ==========================================
    @st.cache_data(ttl=60, show_spinner=False)
    def load_vehicle_data():
        try:
            ws = sheet.worksheet("Vehicle_Data")
            df = pd.DataFrame(ws.get_all_records(default_blank=""))
            if not df.empty and "Date" in df.columns:
                df.columns = df.columns.astype(str).str.strip()
                df["Date_Formatted"] = pd.to_datetime(df["Date"], errors='coerce').dt.date
                return df
            return pd.DataFrame()
        except Exception as e:
            st.error(f"⚠️ Error fetching data: {e}")
            return pd.DataFrame()

    with st.spinner("Loading Data..."):
        df = load_vehicle_data()

    if df.empty:
        st.warning("⚠️ No valid data found in 'Vehicle_Data' worksheet.")
        return

    # ==========================================
    # 3. UI Filters (Single Date)
    # ==========================================
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        selected_date = st.date_input("Select Date:", value=datetime.today().date())
    
    st.divider()

    # Filtering Data by Selected Date
    filtered_df = df[df["Date_Formatted"] == selected_date].copy()
    filtered_df = filtered_df.drop(columns=["Date_Formatted"])

    if filtered_df.empty:
        st.info(f"ℹ️ No data available for **{selected_date}**.")
        return

    # ==========================================
    # 4. Summary Metrics Calculation & Beautiful Cards
    # ==========================================
    total_vehicles = len(filtered_df)
    filtered_df['Capacity(Kg)'] = pd.to_numeric(filtered_df.get('Capacity(Kg)', 0), errors='coerce').fillna(0)
    total_capacity = filtered_df['Capacity(Kg)'].sum()
    
    on_route_count = len(filtered_df[filtered_df.get('Status', '') == 'On Route'])
    not_on_route_count = total_vehicles - on_route_count

    # 🚀 Injecting Custom HTML for KPI Cards
    kpi_cards_html = f"""
    <div class="kpi-container">
        <div class="kpi-card">
            <div class="kpi-title">🚛 Total Vehicles</div>
            <div class="kpi-value">{total_vehicles}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">⚖️ Total Capacity</div>
            <div class="kpi-value">{total_capacity:,.0f} <span style="font-size: 16px;">Kg</span></div>
        </div>
        <div class="kpi-card card-success">
            <div class="kpi-title">✅ On Route</div>
            <div class="kpi-value">{on_route_count}</div>
        </div>
        <div class="kpi-card card-danger">
            <div class="kpi-title">❌ Not on Route</div>
            <div class="kpi-value">{not_on_route_count}</div>
        </div>
    </div>
    """
    st.markdown(kpi_cards_html, unsafe_allow_html=True)
    st.write("")

    # ==========================================
    # 5. Styling the DataFrame for HTML Table
    # ==========================================
    def style_summary(df):
        styler = df.style
        
        def highlight_cells(row):
            styles = [''] * len(row)
            # Highlight Status Column (Green / Red)
            if "Status" in row.index:
                stat_idx = row.index.get_loc("Status")
                val = str(row["Status"]).strip()
                if val == "On Route":
                    styles[stat_idx] = 'background-color: #D4EDDA; color: #155724; font-weight: bold;'
                elif val == "Not on Route":
                    styles[stat_idx] = 'background-color: #FFD1D1; color: #900000; font-weight: bold;'
            return styles

        styler = styler.apply(highlight_cells, axis=1)
        
        # Format Capacity correctly if exists
        if "Capacity(Kg)" in df.columns:
            styler = styler.format({"Capacity(Kg)": "{:,.2f}"})
            
        try: 
            styler = styler.hide(axis="index")
        except: 
            pass
            
        return styler

    styled_df = style_summary(filtered_df)

    # Display in Web App
    st.markdown(f"<div class='table-container'>{styled_df.to_html()}</div>", unsafe_allow_html=True)
    st.write("")

    # ==========================================
    # 6. PDF and CSV Generation Functions
    # ==========================================
    def generate_pdf_or_html(styler, title, date_str):
        try: import pdfkit
        except ImportError: pdfkit = None
            
        try:
            with open("logo.png", "rb") as image_file:
                logo_base64 = base64.b64encode(image_file.read()).decode()
            img_tag = f'<img src="data:image/png;base64,{logo_base64}" style="height: 55px;" />'
        except: 
            img_tag = ''

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{title}</title>
            <style>
                @page {{ size: A4 landscape; margin: 10mm; }}
                body {{ font-family: 'Helvetica', 'Arial', sans-serif; color: #03045E; margin: 0; background-color: #ffffff; }}
                table.header-table {{ width: 100%; background-color: #00245E; color: white; border-bottom: 5px solid #DE9C40; border-radius: 8px 8px 0 0; margin-bottom: 15px; border-collapse: collapse; }}
                table.header-table td {{ border: none; padding: 15px; background-color: #00245E; text-align: left; vertical-align: middle; }}
                .info-section {{ background-color: #CAF0F8; padding: 12px 20px; border-left: 6px solid #0096C7; margin-bottom: 15px; border-radius: 4px; }}
                .info-section h3 {{ margin: 0; color: #023E8A; font-size: 14px; }}
                table {{ width: 100%; border-collapse: collapse; font-size: 12px !important; table-layout: auto; }}
                th, td {{ border: 1px solid #ADE8F4; padding: 8px 10px; text-align: center; white-space: nowrap; }}
                td:first-child {{ text-align: left; font-weight: bold; }}
                th {{ background-color: #03045E !important; color: white !important; text-align: center; font-weight: bold; }}
            </style>
        </head>
        <body>
            <table class="header-table">
                <tr>
                    <td style="width: 70px;">{img_tag}</td>
                    <td><h1 style="margin: 0; font-size: 24px; font-weight: 800; letter-spacing: 1px; color: white;">Imo Chicken & Agro (Pvt) Ltd</h1></td>
                </tr>
            </table>
            <div class="info-section">
                <table style="width: 100%; border: none;">
                    <tr>
                        <td style="text-align: left; border: none; padding: 0;"><h3>Department: Sales & Admin</h3></td>
                        <td style="text-align: center; border: none; padding: 0;"><h3>Report: {title}</h3></td>
                        <td style="text-align: right; border: none; padding: 0;"><h3>Date: {date_str}</h3></td>
                    </tr>
                </table>
            </div>
            {styler.to_html()}
        </body>
        </html>
        """
        
        options = {
            'page-size': 'A4', 'orientation': 'Landscape', 'margin-top': '0.3in', 'margin-right': '0.3in',
            'margin-bottom': '0.3in', 'margin-left': '0.3in', 'encoding': "UTF-8", 'enable-local-file-access': None,
            'zoom': 1.0, 'dpi': 300, 'no-outline': None
        }
        
        if pdfkit:
            try:
                pdf_bytes = pdfkit.from_string(html_content, False, options=options)
                return pdf_bytes, "pdf", "application/pdf"
            except Exception: pass 
        
        return html_content.encode('utf-8'), "html", "text/html"

    c1, c2 = st.columns(2)
    with c1:
        # Download CSV
        csv_df = filtered_df.copy()
        csv_bytes = csv_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="⬇ Download Report CSV",
            data=csv_bytes,
            file_name=f"Vehicle_Report_{selected_date}.csv",
            mime="text/csv",
            use_container_width=True
        )
    with c2:
        # Download HTML/PDF
        export_data, ext, mime = generate_pdf_or_html(styled_df, "Vehicle Operations Summary", str(selected_date))
        st.download_button(
            label=f"🖨️ Download as PDF/HTML",
            data=export_data,
            file_name=f"Vehicle_Report_{selected_date}.{ext}",
            mime=mime,
            use_container_width=True
        )

if __name__ == "__main__":
    show()