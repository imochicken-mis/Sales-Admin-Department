import streamlit as st
import pandas as pd
import datetime
import gspread
import base64
import platform

from util import connect_to_sheets

# ============================================================
# PDF/HTML GENERATOR FUNCTION
# ============================================================
def generate_pdf_or_html(table_html, date_str, kpi_data):
    try:
        import pdfkit
    except ImportError:
        pdfkit = None
        
    try:
        with open("logo.png", "rb") as image_file:
            logo_base64 = base64.b64encode(image_file.read()).decode()
        img_tag = f'<img src="data:image/png;base64,{logo_base64}" style="height: 55px;" />'
    except:
        img_tag = ''
        
    # KPI Section HTML for PDF (HTML Entities used to avoid syntax errors)
    kpi_html = f"""
    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; font-family: 'Helvetica', 'Arial', sans-serif;">
        <tr>
            <!-- Card 1 -->
            <td style="width: 31%; background-color: #004b87; padding: 18px 10px; border-radius: 10px; text-align: center; color: white; border: 1px solid #004b87;">
                <div style="color: #CAF0F8; font-size: 12px; font-weight: bold; text-transform: uppercase; margin-bottom: 6px;">Total Cash Collection</div>
                <div style="color: #FFFFFF; font-size: 22px; font-weight: 900;">Rs. {kpi_data['cash']:,.2f}</div>
            </td>
            
            <!-- Gap -->
            <td style="width: 3.5%; background-color: white; border: none;"></td> 
            
            <!-- Card 2 -->
            <td style="width: 31%; background-color: #0060a8; padding: 18px 10px; border-radius: 10px; text-align: center; color: white; border: 1px solid #0060a8;">
                <div style="color: #E0F7FA; font-size: 12px; font-weight: bold; text-transform: uppercase; margin-bottom: 6px;">Bank Deposit Amount</div>
                <div style="color: #FFFFFF; font-size: 22px; font-weight: 900;">Rs. {kpi_data['deposit']:,.2f}</div>
            </td>
            
            <!-- Gap -->
            <td style="width: 3.5%; background-color: white; border: none;"></td> 
            
            <!-- Card 3 -->
            <td style="width: 31%; background-color: #1e5c34; padding: 18px 10px; border-radius: 10px; text-align: center; color: white; border: 1px solid #1e5c34;">
                <div style="color: #D8F3DC; font-size: 12px; font-weight: bold; text-transform: uppercase; margin-bottom: 6px;">Total Balance</div>
                <div style="color: #FFFFFF; font-size: 22px; font-weight: 900;">Rs. {kpi_data['balance']:,.2f}</div>
            </td>
        </tr>
    </table>
    """

    # Full HTML Layout for PDF
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Collection Report</title>
        <style>
            @page {{ size: A4 portrait; margin: 10mm; }}
            body {{ font-family: 'Helvetica', 'Arial', sans-serif; color: #00245e; margin: 0; background-color: #ffffff; }}
            table.header-table {{ width: 100%; background-color: #00245E; color: white; border-bottom: 5px solid #DE9C40; border-radius: 8px 8px 0 0; margin-bottom: 15px; border-collapse: collapse; }}
            table.header-table td {{ border: none; padding: 15px; background-color: #00245E; text-align: left; vertical-align: middle; }}
            .info-section {{ background-color: #CAF0F8; padding: 12px 20px; border-left: 6px solid #0096C7; margin-bottom: 15px; border-radius: 4px; }}
            .info-section h3 {{ margin: 0; color: #023E8A; font-size: 18px; }}
            
            /* Table styling for PDF */
            table.report-table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px; }}
            table.report-table th, table.report-table td {{ border: 1px solid #ADE8F4; padding: 8px; text-align: right; }}
            table.report-table th {{ background-color: #00245e; color: white; text-align: center; font-weight: bold; }}
            table.report-table td.bg-amount {{ background-color: #F8FDFF; color: #023E8A; font-weight: bold; }}
            table.report-table td.bg-balance {{ background-color: #E2F0CB; color: #155724; font-weight: bold; }}
            table.report-table td.bg-white {{ background-color: #FFFFFF; color: #00245e; }}
            table.report-table td.dark-bottom-border {{ border-bottom: 3px solid #023E8A !important; }}
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
                    <td style="text-align: center; border: none; padding: 0;"><h3>Report: Cash Collection & Deposit</h3></td>
                    <td style="text-align: right; border: none; padding: 0;"><h3>Date: {date_str}</h3></td>
                </tr>
            </table>
        </div>
        {kpi_html}
        {table_html}
    </body>
    </html>
    """
    
    options = {
        'page-size': 'A4', 'orientation': 'Portrait', 'margin-top': '0.3in', 'margin-right': '0.3in',
        'margin-bottom': '0.3in', 'margin-left': '0.3in', 'encoding': "UTF-8", 'enable-local-file-access': None
    }
    
    if pdfkit:
        try:
            # Windows සඳහා සොෆ්ට්වෙයාර් එක තියෙන තැන කේතයට ලබා දීම
            config = None
            if platform.system() == "Windows":
                # ඔබ wkhtmltopdf Install කළ තැන වෙනස් නම් මෙතන Path එක වෙනස් කරන්න
                path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
                config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
            
            # config එක සමග PDF එක සෑදීම
            pdf_bytes = pdfkit.from_string(html_content, False, options=options, configuration=config)
            return pdf_bytes, "pdf", "application/pdf"
            
        except Exception as e:
            st.error(f"⚠️ PDF සෑදීමේ දෝෂයක්: {e}") 
    else:
        st.error("⚠️ 'pdfkit' library එක install කර නොමැත!")
        
    return html_content.encode('utf-8'), "html", "text/html"

# ============================================================
# MAIN UI FUNCTION
# ============================================================
def show():
    # STREAMLIT CHUNK: Styling the Report UI...
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
        
        div[data-testid="stDateInput"] label p, div[data-testid="stSelectbox"] label p {
            font-family: 'Arial', sans-serif !important;
            font-weight: 600 !important;
            font-size: 16px !important;
            color: #03045E !important;
        }
        div[data-testid="stDateInput"] div[data-baseweb="input"] {
            border: 2px solid #0096C7 !important; 
            border-radius: 8px !important;        
            background-color: #F8FDFF !important; 
            transition: all 0.3s ease-in-out;
            padding-left: 5px;
        }
        div[data-baseweb="input"], div[data-baseweb="select"] {
            border: 2px solid #0096C7 !important; 
            border-radius: 8px !important;        
            background-color: #F8FDFF !important; 
        }
        /* 3. Click කළාම (Focus වෙද්දි) දෙකේම බෝඩරය තද නිල් පාට වීම */
        div[data-testid="stDateInput"] div[data-baseweb="input"]:focus-within, 
        div[data-testid="stSelectbox"] div[data-baseweb="select"]:focus-within {
            border: 2px solid #03045E !important; 
            box-shadow: 0 0 8px rgba(3, 4, 94, 0.4) !important;
        }
        
        /* Table Container with Scroll & Radius */
        .table-container {
            max-height: 450px;
            overflow-y: auto;
            border-radius: 12px;
            border: 2px solid #0096C7;
            box-shadow: 0 8px 24px rgba(3, 4, 94, 0.1);
            background-color: #FFFFFF;
        }
        
        /* Scrollbar Styling */
        .table-container::-webkit-scrollbar { width: 6px; }
        .table-container::-webkit-scrollbar-track { background: transparent; }
        .table-container::-webkit-scrollbar-thumb { background: #0096C7; border-radius: 10px; }
        
        .report-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            font-family: 'Arial', sans-serif;
            font-size: 13px;
        }
        
        .report-table th {
            position: sticky;
            top: 0;
            z-index: 2;
            padding: 12px 8px;
            text-align: center;
            color: #FFFFFF;
            font-weight: 900;
            background-color: #00245e;
            border-bottom: 2px solid #0077B6;
            border-right: 1px solid #0077B6;
        }
        
        .report-table td {
            border-bottom: 1px solid #ADE8F4;
            border-right: 1px solid #ADE8F4;
            padding: 10px 8px;
        }
        
        .report-table th:last-child, .report-table td:last-child { border-right: none; }
        
        /* 🚀 Thick border at the end of each Rep's group */
        .dark-bottom-border { border-bottom: 3px solid #023E8A !important; }
        
        .bg-amount { background-color: #F8FDFF; color: #023E8A; font-weight: 600; }
        .bg-balance { background-color: #E2F0CB; color: #155724; font-weight: 800; }
        .bg-white { background-color: #FFFFFF; color: #00245e; }
        
        .report-table tbody tr:hover td {
            background-color: #EAF8FF;
            transition: 0.2s;
        }
        </style>
    """, unsafe_allow_html=True)

    # 🚀 HTML Entity used for the bar chart icon to avoid Unicode SyntaxError
    st.title("Daily Collection Report")
    st.write("")

    # STREAMLIT CHUNK: Loading Master Data for Filters...
    sh = connect_to_sheets()
    try:
        ws_reps = sh.worksheet("Sales_Reps_Master_data")
        df_reps = pd.DataFrame(ws_reps.get_all_records(default_blank=""))
        
        # 🚀 Route එක සහ Rep Name එක එකතු කර ලැයිස්තුව සැකසීම (Ex: AB - Mr.Udaya)
        combined_reps = []
        for _, row in df_reps.iterrows():
            route = str(row.get("Route", "")).strip()
            name = str(row.get("Rep_Name", "")).strip()
            
            if route and name:
                if not name.startswith("Mr."):
                    name = f"Mr.{name}"
                combined_reps.append(f"{route} - {name}")
            elif name:
                if not name.startswith("Mr."):
                    name = f"Mr.{name}"
                combined_reps.append(name)
            elif route:
                combined_reps.append(route)
                
        reps_list = ["All"] + sorted(list(set(combined_reps)))
    except:
        reps_list = ["All"]

    # STREAMLIT CHUNK: Rendering Filters...
    col1, col2, col3 = st.columns([1, 1.5, 2.5], vertical_alignment="bottom")
    with col1:
        if "cc_selected_date" not in st.session_state:
            st.session_state["cc_selected_date"] = datetime.date.today()
        selected_date = st.date_input("Select Date:", key="cc_selected_date")
    selected_date_str = selected_date.strftime("%Y-%m-%d")
    with col2:
        if "cc_selected_rep" not in st.session_state:
            st.session_state["cc_selected_rep"] = "All"
        selected_rep = st.selectbox("Sales Rep:", reps_list, key="cc_selected_rep")
    st.divider()

    # STREAMLIT CHUNK: Loading Google Sheets Data...
    with st.spinner("Generating Report..."):
        try:
            ws_cc = sh.worksheet("Cash_Collection")
            df_cc = pd.DataFrame(ws_cc.get_all_records(default_blank=""))
        except Exception as e:
            st.error("⚠️ 'Cash_Collection' sheet not found!")
            return
            
        if df_cc.empty:
            st.info("No data available.")
            return

        # STREAMLIT CHUNK: Processing Data...
        df_merged = df_cc[df_cc["Date"].astype(str) == selected_date_str].copy()
        
        # 🚀 Sales Rep අනුව Filter කිරීම
        if selected_rep != "All":
            # හරියටම Match වන දත්ත පමණක් පෙරා ගැනීම (Exact Match)
            df_merged = df_merged[df_merged["Route"].astype(str).str.strip() == selected_rep]
        
        if df_merged.empty:
            if selected_rep != "All":
                st.warning(f"⚠️ No collection data available for Sales Rep **'{selected_rep}'** on this date.")
            else:
                st.info(f"No collection records found for {selected_date_str}.")
            return

        df_merged["Route"] = df_merged["Route"].astype(str).str.strip()

        # STREAMLIT CHUNK: Calculating KPIs...
        grand_total_cash = pd.to_numeric(df_merged["Total Cash Collection"].astype(str).str.replace(',', ''), errors='coerce').fillna(0).sum()
        grand_total_amount = pd.to_numeric(df_merged["Amount"].astype(str).str.replace(',', ''), errors='coerce').fillna(0).sum()
        grand_total_balance = pd.to_numeric(df_merged["Balance"].astype(str).str.replace(',', ''), errors='coerce').fillna(0).sum()
        
        kpi_data = {
            'cash': grand_total_cash,
            'deposit': grand_total_amount,
            'balance': grand_total_balance
        }

        # Rendering KPI Cards in Web App (Using HTML entities for emojis to prevent crashes)
        st.markdown(f"""
            <div style="display: flex; gap: 20px; margin-bottom: 25px;">
                <div style="flex: 1; background: linear-gradient(135deg, #0077B6 0%, #00245e 100%); padding: 25px; border-radius: 16px; text-align: center; box-shadow: 0 10px 20px rgba(0, 36, 94, 0.2); color: white;">
                    <h4 style="margin: 0; color: #CAF0F8; font-size: 15px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">&#128181; Total Cash Collection</h4>
                    <h2 style="margin: 10px 0 0 0; color: #FFFFFF; font-size: 32px; font-weight: 900;">Rs. {grand_total_cash:,.2f}</h2>
                </div>
                <div style="flex: 1; background: linear-gradient(135deg, #0077B6 0%, #00245e 100%); padding: 25px; border-radius: 16px; text-align: center; box-shadow: 0 10px 20px rgba(0, 119, 182, 0.2); color: white;">
                    <h4 style="margin: 0; color: #E0F7FA; font-size: 15px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">&#127974; Bank Deposit Amount</h4>
                    <h2 style="margin: 10px 0 0 0; color: #FFFFFF; font-size: 32px; font-weight: 900;">Rs. {grand_total_amount:,.2f}</h2>
                </div>
                <div style="flex: 1; background: linear-gradient(135deg, #2D6A4F 0%, #155724 100%); padding: 25px; border-radius: 16px; text-align: center; box-shadow: 0 10px 20px rgba(21, 87, 36, 0.2); color: white;">
                    <h4 style="margin: 0; color: #D8F3DC; font-size: 15px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">&#9876;&#65039; Total Balance</h4>
                    <h2 style="margin: 10px 0 0 0; color: #FFFFFF; font-size: 32px; font-weight: 900;">Rs. {grand_total_balance:,.2f}</h2>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # STREAMLIT CHUNK: Generating HTML Table...
        table_inner_html = "<table class='report-table'>"
        table_inner_html += """
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Rep Name</th>
                    <th>Total</th>
                    <th>Bank Deposit Amount</th>
                    <th>Deposit Date</th>
                    <th>Bank</th>
                    <th>Balance</th>
                </tr>
            </thead>
            <tbody>
        """

        routes = df_merged["Route"].unique()
        
        for route in routes:
            group = df_merged[df_merged["Route"] == route].reset_index(drop=True)
            n_rows = len(group)
            
            total_cash = pd.to_numeric(group["Total Cash Collection"].astype(str).str.replace(',', ''), errors='coerce').fillna(0).sum()
            total_amount = pd.to_numeric(group["Amount"].astype(str).str.replace(',', ''), errors='coerce').fillna(0).sum()
            balance = total_cash - total_amount
            
            # 🚀 Rep Display Name is directly fetched from Route (e.g. "AB - Mr.Udaya")
            rep_display_name = str(route)
            
            border_class_group = "dark-bottom-border"
            
            for i in range(n_rows):
                row = group.iloc[i]
                
                amount = pd.to_numeric(str(row.get("Amount", 0)).replace(',', ''), errors='coerce')
                amount_str = f"{amount:,.2f}" if pd.notnull(amount) and amount != 0 else "-"
                
                dep_date = row.get("Deposit Date", "")
                
                bank = str(row.get("Status", ""))
                if bank.strip() == "" or bank == "nan":
                    bank = "-"

                table_inner_html += "<tr>"
                
                # 🚀 Apply the thick border to the LAST row of each group to complete the line
                border_class_last = "dark-bottom-border" if i == n_rows - 1 else ""
                
                if i == 0:
                    table_inner_html += f"<td rowspan='{n_rows}' class='bg-white {border_class_group}' style='vertical-align: middle; text-align: center;'>{selected_date_str}</td>"
                    table_inner_html += f"<td rowspan='{n_rows}' class='bg-white {border_class_group}' style='vertical-align: middle; text-align: center; font-weight: bold;'>{rep_display_name}</td>"
                    
                    total_str = f"{total_cash:,.2f}" if total_cash != 0 else "-"
                    table_inner_html += f"<td rowspan='{n_rows}' class='bg-white {border_class_group}' style='vertical-align: middle; text-align: right; font-weight: bold;'>{total_str}</td>"

                table_inner_html += f"<td class='bg-amount {border_class_last}' style='text-align: right;'>{amount_str}</td>"
                table_inner_html += f"<td class='bg-white {border_class_last}' style='text-align: center;'>{dep_date}</td>"
                table_inner_html += f"<td class='bg-white {border_class_last}' style='text-align: center;'>{bank}</td>"

                if i == 0:
                    bal_str = f"{balance:,.2f}" if balance != 0 else "0.00"
                    table_inner_html += f"<td rowspan='{n_rows}' class='bg-balance {border_class_group}' style='vertical-align: middle; text-align: right; font-weight: bold;'>{bal_str}</td>"

                table_inner_html += "</tr>"

        table_inner_html += "</tbody></table>"
        
        # Display Table in Web App
        st.markdown(f"<div class='table-container'>{table_inner_html}</div>", unsafe_allow_html=True)
        st.write("")

        # STREAMLIT CHUNK: Download Button...
        col_btn1, col_btn2 = st.columns([8, 2])
        with col_btn2:
            export_data, ext, mime = generate_pdf_or_html(table_inner_html, selected_date_str, kpi_data)
            # Streamlit shortcode for printer icon used here
            st.download_button(
                label=f":printer: Download Report",
                data=export_data,
                file_name=f"Collection_Report_{selected_date_str}.{ext}",
                mime=mime,
                use_container_width=True
            )

if __name__ == "__main__":
    show()