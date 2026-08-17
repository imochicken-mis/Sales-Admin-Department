import streamlit as st
import pandas as pd
import datetime
import calendar
import base64
import time
import gspread

# util.py එකෙන් Connection ලබාගැනීම
try:
    from util import connect_to_sheets2
except ImportError:
    st.error("Error: Could not import connection functions from util.py")

def show():
    # STREAMLIT_CHUNK:Styling the layout...
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
        
        div[data-testid="stSelectbox"] label p {
            font-family: 'Arial', sans-serif !important;
            font-weight: 800 !important;
            font-size: 15px !important;
            color: #03045E !important;
        }
        div[data-baseweb="select"] {
            border: 2px solid #0096C7 !important; 
            border-radius: 8px !important;        
            background-color: #F8FDFF !important; 
            transition: all 0.3s ease-in-out;
        }
        div[data-baseweb="select"]:focus-within {
            border: 2px solid #03045E !important;
            box-shadow: 0 0 8px rgba(3, 4, 94, 0.4) !important;
        }
        
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
            text-align: right;
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

    st.markdown("<h2 style='text-align: center; color: #03045E; font-weight: 800;'>📊 Rep Summary Report</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #0077B6; font-weight: 600;'>Monthly overview of Issued Qty, Returns, and Variance per Representative.</p>", unsafe_allow_html=True)
    st.write("")

    sheet2 = connect_to_sheets2()

    # STREAMLIT_CHUNK:Loading Data functions...
    @st.cache_data(ttl=60, show_spinner=False)
    def load_master_data():
        try:
            ws = sheet2.worksheet("MasterData_adjust")
            df = pd.DataFrame(ws.get_all_records(default_blank=""))
            if not df.empty and "Rep_Name" in df.columns and "Route" in df.columns:
                df = df[(df["Rep_Name"].astype(str).str.strip() != "") & (df["Route"].astype(str).str.strip() != "")]
                df["Route - Rep Name"] = df["Route"].astype(str).str.strip() + " - " + df["Rep_Name"].astype(str).str.strip()
                return df[["Route - Rep Name"]].drop_duplicates().reset_index(drop=True)
            return pd.DataFrame(columns=["Route - Rep Name"])
        except Exception as e:
            return pd.DataFrame(columns=["Route - Rep Name"])

    @st.cache_data(ttl=60, show_spinner=False)
    def load_monthly_data(tab_name, year, month, value_col):
        try:
            ws = sheet2.worksheet(tab_name)
            df = pd.DataFrame(ws.get_all_records(default_blank=""))
            if not df.empty:
                filtered = df[(df["Year"].astype(str) == str(year)) & (df["Month"].astype(str) == str(month))]
                if not filtered.empty and "Route - Rep Name" in filtered.columns and value_col in filtered.columns:
                    return filtered[["Route - Rep Name", value_col]]
            return pd.DataFrame(columns=["Route - Rep Name", value_col])
        except gspread.exceptions.WorksheetNotFound:
            return pd.DataFrame(columns=["Route - Rep Name", value_col])
        except Exception:
            return pd.DataFrame(columns=["Route - Rep Name", value_col])

    # STREAMLIT_CHUNK:Rendering UI...
    col1, col2, col3, col4 = st.columns([1, 2, 1, 1], vertical_alignment="bottom")
    
    month_year_options = []
    for y in range(2024, 2031):
        for m in range(1, 13):
            month_year_options.append(f"{y} - {calendar.month_name[m]}")

    current_month_str = datetime.date.today().strftime("%Y - %B")
    
    with col2:
        selected_month_year = st.selectbox(
            "Select Year & Month:", 
            month_year_options, 
            index=month_year_options.index(current_month_str) if current_month_str in month_year_options else 0
        )

    selected_year, selected_month = selected_month_year.split(" - ")
    st.divider()

    # STREAMLIT_CHUNK:Building the Summary Table...
    with st.spinner("Generating Summary Report..."):
        master_df = load_master_data()
        
        if master_df.empty:
            st.warning("⚠️ No valid master data found to generate the report.")
            return

        issued_df = load_monthly_data("Issued_Qty", selected_year, selected_month, "Issued Qty")
        shop_rtn_df = load_monthly_data("Shop_Return", selected_year, selected_month, "Return Amount")
        # Rename column for clarity in final report
        shop_rtn_df.rename(columns={"Return Amount": "Shop Return Qty"}, inplace=True)
        
        sales_rtn_df = load_monthly_data("Sales_Return", selected_year, selected_month, "Return Amount")
        sales_rtn_df.rename(columns={"Return Amount": "Sales Return Qty"}, inplace=True)
        
        variance_df = load_monthly_data("Rep_Variance", selected_year, selected_month, "Variance Amount")

        # Merge all dataframes on "Route - Rep Name"
        summary_df = master_df.copy()
        
        summary_df = pd.merge(summary_df, issued_df, on="Route - Rep Name", how="left")
        summary_df = pd.merge(summary_df, shop_rtn_df, on="Route - Rep Name", how="left")
        summary_df = pd.merge(summary_df, sales_rtn_df, on="Route - Rep Name", how="left")
        summary_df = pd.merge(summary_df, variance_df, on="Route - Rep Name", how="left")
        
        # Fill NaN with 0 and convert to numeric
        for col in ["Issued Qty", "Shop Return Qty", "Sales Return Qty", "Variance Amount"]:
            summary_df[col] = pd.to_numeric(summary_df[col], errors='coerce').fillna(0.0)

        # Filter out reps who have absolutely 0 in all 4 columns (Optional: Keep it clean)
        summary_df["RowSum"] = summary_df[["Issued Qty", "Shop Return Qty", "Sales Return Qty", "Variance Amount"]].abs().sum(axis=1)
        summary_df = summary_df[summary_df["RowSum"] > 0].drop(columns=["RowSum"]).reset_index(drop=True)

    if summary_df.empty:
        st.info(f"ℹ️ No data available for **{selected_month_year}** across any of the tracking categories.")
        return

    # Add a Total Row
    total_row = pd.DataFrame([{
        "Route - Rep Name": "TOTAL",
        "Issued Qty": summary_df["Issued Qty"].sum(),
        "Shop Return Qty": summary_df["Shop Return Qty"].sum(),
        "Sales Return Qty": summary_df["Sales Return Qty"].sum(),
        "Variance Amount": summary_df["Variance Amount"].sum()
    }])
    summary_df = pd.concat([summary_df, total_row], ignore_index=True)

    # STREAMLIT_CHUNK:Styling the DataFrame...
    def style_summary(df):
        styler = df.style
        
        def highlight_cells(row):
            styles = [''] * len(row)
            
            # Highlight Returns (Light Blue)
            for col in ["Shop Return Qty", "Sales Return Qty"]:
                if col in row.index:
                    idx = row.index.get_loc(col)
                    try:
                        if float(row[col]) > 0 and row['Route - Rep Name'] != "TOTAL":
                            styles[idx] = 'background-color: #EAF8FF; color: #023E8A; font-weight: bold;'
                    except: pass
            
            # Highlight Variance (Green/Red)
            if "Variance Amount" in row.index:
                var_idx = row.index.get_loc("Variance Amount")
                try:
                    val = float(row["Variance Amount"])
                    if row['Route - Rep Name'] != "TOTAL":
                        if val > 0: styles[var_idx] = 'background-color: #D4EDDA; color: #155724; font-weight: bold;'
                        elif val < 0: styles[var_idx] = 'background-color: #FFD1D1; color: #900000; font-weight: bold;'
                except: pass
                
            # Total Row Styling
            if row['Route - Rep Name'] == "TOTAL":
                styles = ['background-color: #03045E; color: #FFFFFF; font-weight: 900; font-size: 14px;'] * len(row)
                
            return styles

        styler = styler.apply(highlight_cells, axis=1)
        styler = styler.format({
            "Issued Qty": "{:,.2f}",
            "Shop Return Qty": "{:,.2f}",
            "Sales Return Qty": "{:,.2f}",
            "Variance Amount": "{:,.2f}"
        })
        try: styler = styler.hide(axis="index")
        except: pass
        
        return styler

    styled_df = style_summary(summary_df)

    # Display in Web App
    st.markdown(f"<div class='table-container'>{styled_df.to_html()}</div>", unsafe_allow_html=True)
    st.write("")

    # STREAMLIT_CHUNK:PDF and CSV Generation...
    def generate_pdf_or_html(styler, title, date_str):
        try: import pdfkit
        except ImportError: pdfkit = None
            
        try:
            with open("logo.png", "rb") as image_file:
                logo_base64 = base64.b64encode(image_file.read()).decode()
            img_tag = f'<img src="data:image/png;base64,{logo_base64}" style="height: 55px;" />'
        except: img_tag = ''

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{title}</title>
            <style>
                @page {{ size: A4 portrait; margin: 10mm; }}
                body {{ font-family: 'Helvetica', 'Arial', sans-serif; color: #03045E; margin: 0; background-color: #ffffff; }}
                table.header-table {{ width: 100%; background-color: #00245E; color: white; border-bottom: 5px solid #DE9C40; border-radius: 8px 8px 0 0; margin-bottom: 15px; border-collapse: collapse; }}
                table.header-table td {{ border: none; padding: 15px; background-color: #00245E; text-align: left; vertical-align: middle; }}
                .info-section {{ background-color: #CAF0F8; padding: 12px 20px; border-left: 6px solid #0096C7; margin-bottom: 15px; border-radius: 4px; }}
                .info-section h3 {{ margin: 0; color: #023E8A; font-size: 14px; }}
                table {{ width: 100%; border-collapse: collapse; font-size: 12px !important; table-layout: auto; }}
                th, td {{ border: 1px solid #ADE8F4; padding: 8px 10px; text-align: right; white-space: nowrap; }}
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
                        <td style="text-align: left; border: none; padding: 0;"><h3>Department: <Sales & Admin/h3></td>
                        <td style="text-align: center; border: none; padding: 0;"><h3>Report: {title}</h3></td>
                        <td style="text-align: right; border: none; padding: 0;"><h3>Month: {date_str}</h3></td>
                    </tr>
                </table>
            </div>
            {styler.to_html()}
        </body>
        </html>
        """
        
        options = {
            'page-size': 'A4', 'orientation': 'Portrait', 'margin-top': '0.3in', 'margin-right': '0.3in',
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
        csv_df = summary_df.copy()
        csv_bytes = csv_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="⬇ Download Report CSV",
            data=csv_bytes,
            file_name=f"Rep_Summary_{selected_month_year.replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    with c2:
        # Download HTML/PDF
        export_data, ext, mime = generate_pdf_or_html(styled_df, "Rep Operations Summary", selected_month_year)
        st.download_button(
            label=f"🖨️ Download as PDF/HTML",
            data=export_data,
            file_name=f"Rep_Summary_{selected_month_year.replace(' ', '_')}.{ext}",
            mime=mime,
            use_container_width=True
        )

if __name__ == "__main__":
    show()
