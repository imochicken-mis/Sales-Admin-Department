import streamlit as st
import calendar
import re
import time
import base64
import datetime
import platform
import gspread
import numpy as np
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

def show():
    # ============================================================
    # 1. CONNECTION
    # ============================================================
    SCOPE = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    @st.cache_resource
    def get_client():
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            "service_account.json", SCOPE
        )
        return gspread.authorize(creds)

    @st.cache_resource
    def get_sheets():
        client = get_client()
        sheet2 = client.open("Sales data2")
        return sheet2

    # ============================================================
    # 2. LOAD RAW DATA (cached, refreshed based on ttl)
    # ============================================================
    @st.cache_data(ttl=600, show_spinner=False)
    def load_raw_data():
        sheet2 = get_sheets()

        master_ws = sheet2.worksheet("MasterData")
        targets_ws = sheet2.worksheet("MonthlyTargets")
        sales_ws = sheet2.worksheet("Sales_day_book")
        working_days_ws = sheet2.worksheet("Working_Days")

        master_df = pd.DataFrame(master_ws.get_all_records())
        targets_df = pd.DataFrame(targets_ws.get_all_records())
        sales_df = pd.DataFrame(sales_ws.get_all_records())
        working_days_df = pd.DataFrame(working_days_ws.get_all_records())

        return master_df, targets_df, sales_df, working_days_df

    def clear_raw_cache():
        st.cache_data.clear()

    def _normalize_name(name):
        if not isinstance(name, str): 
            return ""
        parts = str(name).strip().split()
        return parts[0].lower() if parts else ""

    # ============================================================
    # 3. CALCULATION - MASTER TABLE
    # ============================================================
    def build_master_table(selected_date_str: str):
        master_df, targets_df, sales_df, working_days_df = load_raw_data()

        select_date_obj = pd.to_datetime(selected_date_str)
        selected_year = select_date_obj.year
        selected_month_name = select_date_obj.strftime("%B")
        selected_month_str = select_date_obj.strftime("%Y-%m")
        alt_month_str = select_date_obj.strftime("%Y-%b")

        # ---- Working Days ----
        working_days_filtered = working_days_df[
            (working_days_df["Year"].astype(str) == str(selected_year)) & 
            (working_days_df["Month"].astype(str).str.lower() == selected_month_name.lower())
        ]
        
        wd, worked_days = 0, 0
        if not working_days_filtered.empty:
            wd = pd.to_numeric(working_days_filtered["Working Days"].iloc[0], errors='coerce')
            worked_days = pd.to_numeric(working_days_filtered.get("Worked Days", pd.Series([0])).iloc[0], errors='coerce')
        
        wd = wd if pd.notna(wd) else 0
        worked_days = worked_days if pd.notna(worked_days) else 0

        # ---- Targets Filter ----
        targets_filtered = targets_df[
            (targets_df["Month"].astype(str) == selected_month_str) | 
            (targets_df["Month"].astype(str) == alt_month_str)
        ].copy()
        
        if targets_filtered.empty:
            targets_filtered = targets_df[targets_df["Month"].astype(str).str.lower() == selected_month_name.lower()].copy()

        # 🚀 Google Sheet alignment fix: "No" column is included here
        if targets_filtered.empty:
            base_df = master_df[["No", "Manager", "Route", "Representative", "Status"]].copy()
            base_df["Target"] = 0
        else:
            base_df = targets_filtered[["No", "Manager", "Route", "Representative", "Status", "Target"]].copy()
            base_df["Target"] = pd.to_numeric(base_df["Target"], errors='coerce').fillna(0)

        base_df["rep_key"] = base_df["Representative"].apply(_normalize_name)

        # ---- Sales ----
        date_col = "New_date" if "New_date" in sales_df.columns else "new_date" if "new_date" in sales_df.columns else None

        if date_col and not sales_df.empty:
            sales_df["_parsed_date"] = pd.to_datetime(sales_df[date_col], errors="coerce")
            sales_month = sales_df[
                (sales_df["_parsed_date"].dt.year == selected_year) & 
                (sales_df["_parsed_date"].dt.month == select_date_obj.month) &
                (sales_df["_parsed_date"] <= select_date_obj)
            ].copy()
            
            sales_month["Qty"] = pd.to_numeric(sales_month["Qty"], errors='coerce').fillna(0)
            sales_month["rep_key"] = sales_month["Agent"].apply(_normalize_name)
            
            sales_grouped = sales_month.groupby("rep_key")["Qty"].sum().reset_index()
            sales_grouped.rename(columns={"Qty": "Sales"}, inplace=True)
        else:
            sales_grouped = pd.DataFrame(columns=["rep_key", "Sales"])
            
        # ---- Merge ----
        master_table = pd.merge(base_df, sales_grouped, on="rep_key", how="left")
        master_table["Sales"] = master_table["Sales"].fillna(0)
        
        # ---- Calculations ----
        master_table["Day Target"] = np.where(wd > 0, master_table["Target"] / wd, 0)
        master_table["Balance"] = master_table["Sales"] - master_table["Target"]
        master_table["Achievement %"] = np.where(master_table["Target"] > 0, (master_table["Sales"] / master_table["Target"]) * 100, 0)
        master_table["Day Target 2"] = master_table["Day Target"] * worked_days
        master_table["Day Achievement %"] = np.where(master_table["Day Target 2"] > 0, (master_table["Sales"] / master_table["Day Target 2"]) * 100, 0)
        
        # 🚀 Google Sheet alignment fix: "No" column is placed exactly at the start
        cols_order = [
            "No", "Manager", "Route", "Representative", "Status", 
            "Day Target", "Sales", "Target", "Balance", "Achievement %", 
            "Day Target 2", "Day Achievement %"
        ]
        master_table = master_table[cols_order]
        master_table = master_table.replace([np.inf, -np.inf], 0)
        return master_table

    # ============================================================
    # 4. CALCULATION - WEEKLY BREAKDOWN
    # ============================================================
    def build_weekly_breakdown(selected_date_str: str) -> pd.DataFrame:
        master_df, targets_df, sales_df, working_days_df = load_raw_data()
        
        select_date_obj = pd.to_datetime(selected_date_str)
        selected_year, selected_month = select_date_obj.year, select_date_obj.month
        selected_month_name = select_date_obj.strftime("%B")
        selected_month_str = select_date_obj.strftime("%Y-%m")
        alt_month_str = select_date_obj.strftime("%Y-%b")

        # ---- Targets Filter ----
        targets_filtered = targets_df[
            (targets_df["Month"].astype(str) == selected_month_str) | 
            (targets_df["Month"].astype(str) == alt_month_str)
        ].copy()

        if targets_filtered.empty:
            targets_filtered = targets_df[targets_df["Month"].astype(str).str.lower() == selected_month_name.lower()].copy()
            
        # 🚀 Google Sheet alignment fix: "No" column is included here
        if targets_filtered.empty:
            base_df = master_df[["No", "Manager", "Route", "Representative", "Status"]].copy()
            base_df["Target"] = 0
        else:
            base_df = targets_filtered[["No", "Manager", "Route", "Representative", "Status", "Target"]].copy()
            base_df["Target"] = pd.to_numeric(base_df["Target"], errors='coerce').fillna(0)

        base_df["rep_key"] = base_df["Representative"].apply(_normalize_name)
        
        # ---- Weeks Calculation (Monday Start) ----
        days_in_month = calendar.monthrange(selected_year, selected_month)[1]
        first_weekday = datetime.datetime(selected_year, selected_month, 1).weekday() 
        total_weeks = ((days_in_month - 1 + first_weekday) // 7) + 1
        week_cols = [f"Week {i}" for i in range(1, total_weeks + 1)]
        
        # ---- Sales Day Book ----
        date_col = "New_date" if "New_date" in sales_df.columns else "new_date" if "new_date" in sales_df.columns else None

        if date_col and not sales_df.empty:
            sales_df["_parsed_date"] = pd.to_datetime(sales_df[date_col], errors="coerce")
            df = sales_df[
                (sales_df["_parsed_date"].dt.year == selected_year) & 
                (sales_df["_parsed_date"].dt.month == selected_month) &
                (sales_df["_parsed_date"] <= select_date_obj)
            ].copy()
            
            df["Qty"] = pd.to_numeric(df.get("Qty", 0), errors="coerce").fillna(0)
            df["rep_key"] = df["Agent"].apply(_normalize_name)
            
            df["day"] = df["_parsed_date"].dt.day
            df["week_num"] = ((df["day"] - 1 + first_weekday) // 7) + 1
            df["week_label"] = "Week " + df["week_num"].astype(int).astype(str)
            
            weekly_pivot = (
                df.groupby(["rep_key", "week_label"])["Qty"]
                .sum().reset_index()
                .pivot(index="rep_key", columns="week_label", values="Qty").reset_index()
            )
        else:
            weekly_pivot = pd.DataFrame(columns=["rep_key"] + week_cols)
            
        # ---- Merge & Finalize ----
        weekly_table = base_df.merge(weekly_pivot, on="rep_key", how="left")
        
        for c in week_cols:
            if c not in weekly_table.columns:
                weekly_table[c] = 0
        weekly_table[week_cols] = weekly_table[week_cols].fillna(0)
        weekly_table["Total Sales"] = weekly_table[week_cols].sum(axis=1)
        
        # 🚀 Google Sheet alignment fix: "No" column is included here
        cols_order = ["No", "Manager", "Route", "Representative", "Status", "Target", "Total Sales"] + week_cols
        weekly_table = weekly_table[cols_order]
        
        return weekly_table

    # ============================================================
    # 5. STYLING, FORMATTING & PDF EXPORT
    # ============================================================
    def style_dataframe(df: pd.DataFrame, is_weekly=False):
        df_display = df.copy()
        
        # 🚀 1. Remove "No" column completely from Web UI and HTML Print!
        if "No" in df_display.columns:
            df_display = df_display.drop(columns=["No"])
            
        def safe_formatter(val, is_pct):
            if pd.isna(val) or val == "": return "-"
            try:
                num = float(val)
                return f"{num:,.2f}%" if is_pct else f"{num:,.2f}"
            except:
                return str(val)
                
        format_dict = {}
        exclude_cols = ["Manager", "Route", "Representative", "Status"]
        for c in df_display.columns:
            if c not in exclude_cols:
                is_pct_col = "%" in c or ("Target" in c and "Daily" in c)
                format_dict[c] = lambda x, p=is_pct_col: safe_formatter(x, p)
                
        styler = df_display.style.format(format_dict)
        
        def safe_get_float(val):
            try:
                if pd.isna(val) or val == "": return None
                if isinstance(val, str):
                    val = val.replace(',', '').replace('%', '').strip()
                return float(val)
            except: return None

        if not is_weekly:
            def highlight_rows(row):
                styles = [''] * len(row)
                
                if 'Achievement %' in row.index:
                    ach_idx = row.index.get_loc('Achievement %')
                    ach_val = safe_get_float(row['Achievement %'])
                    if ach_val is not None:
                        if ach_val >= 100: styles[ach_idx] = 'background-color: #D4EDDA !important; color: #155724 !important; font-weight: bold;'
                        elif ach_val >= 75: styles[ach_idx] = 'background-color: #FFF3CD !important; color: #856404 !important; font-weight: bold;'
                        elif ach_val >= 50: styles[ach_idx] = 'background-color: #FFE8CC !important; color: #A04000 !important; font-weight: bold;'
                        elif ach_val >= 0: styles[ach_idx] = 'background-color: #F8D7DA !important; color: #721C24 !important; font-weight: bold;'
                        else: styles[ach_idx] = 'background-color: #F5C6CB !important; color: #721C24 !important; font-weight: bold;'
                
                if 'Day Achievement %' in row.index:
                    adt_idx = row.index.get_loc('Day Achievement %')
                    adt_val = safe_get_float(row['Day Achievement %'])
                    if adt_val is not None:
                        if adt_val >= 100: styles[adt_idx] = 'background-color: #D4EDDA !important; color: #155724 !important; font-weight: bold;'
                        elif adt_val >= 75: styles[adt_idx] = 'background-color: #FFF3CD !important; color: #856404 !important; font-weight: bold;'
                        elif adt_val >= 50: styles[adt_idx] = 'background-color: #FFE8CC !important; color: #A04000 !important; font-weight: bold;'
                        elif adt_val >= 0: styles[adt_idx] = 'background-color: #F8D7DA !important; color: #721C24 !important; font-weight: bold;'
                        else: styles[adt_idx] = 'background-color: #F5C6CB !important; color: #721C24 !important; font-weight: bold;'
                
                if 'Balance' in row.index:
                    bal_idx = row.index.get_loc('Balance')
                    bal_val = safe_get_float(row['Balance'])
                    if bal_val is not None:
                        if bal_val >= 0: styles[bal_idx] = 'background-color: #E2F0CB !important; color: #2D5A27 !important; font-weight: bold;'
                        else: styles[bal_idx] = 'background-color: #FFD1D1 !important; color: #900000 !important; font-weight: bold;'
                
                if 'Sales' in row.index and 'Target' in row.index:
                    qty_idx = row.index.get_loc('Sales')
                    qty_val = safe_get_float(row['Sales'])
                    fq_val = safe_get_float(row['Target'])
                    if qty_val is not None and fq_val is not None and fq_val > 0:
                        pct = (qty_val / fq_val) * 100
                        if pct >= 100: styles[qty_idx] = 'background-color: #D4EDDA !important; color: #155724 !important; font-weight: bold;'
                        elif pct >= 75: styles[qty_idx] = 'background-color: #FFF3CD !important; color: #856404 !important; font-weight: bold;'
                        elif pct >= 50: styles[qty_idx] = 'background-color: #FFE8CC !important; color: #A04000 !important; font-weight: bold;'
                        elif pct >= 0: styles[qty_idx] = 'background-color: #F8D7DA !important; color: #721C24 !important; font-weight: bold;'
                        else: styles[qty_idx] = 'background-color: #F5C6CB !important; color: #721C24 !important; font-weight: bold;'
                return styles
            styler = styler.apply(highlight_rows, axis=1)

        # 🚀 Grid Design and Header Colors for Web and HTML
        styler = styler.set_table_styles([
            {'selector': 'table', 'props': [('width', '100%'), ('border-collapse', 'collapse')]},
            {'selector': 'th', 'props': [('background-color', '#00245E'), ('color', '#FFFFFF'), ('text-align', 'center'), ('padding', '10px'), ('border', '1px solid #ADE8F4'), ('white-space', 'nowrap')]},
            {'selector': 'td', 'props': [('border', '1px solid #ADE8F4'), ('padding', '8px'), ('text-align', 'right'), ('white-space', 'nowrap')]},
            {'selector': 'tr:nth-child(even)', 'props': [('background-color', '#F8FDFF')]},
            {'selector': 'tr:nth-child(odd)', 'props': [('background-color', '#FFFFFF')]}
        ])
        
        try: styler = styler.hide(axis="index")
        except: pass
            
        return styler

    # ============================================================
    # 🌟 GENERATE HTML (Replaces PDF generation)
    # ============================================================
    def generate_pdf_or_html(styler, title, date_str):
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
                body {{ font-family: 'Helvetica', 'Arial', sans-serif; color: #03045E; margin: 20px; background-color: #ffffff; }}
                table.header-table {{ width: 100%; background-color: #00245E; color: white; border-bottom: 5px solid #DE9C40; border-radius: 8px 8px 0 0; margin-bottom: 15px; border-collapse: collapse; }}
                table.header-table td {{ border: none; padding: 15px; background-color: #00245E; text-align: left; vertical-align: middle; }}
                .info-section {{ background-color: #CAF0F8; padding: 15px 20px; border-left: 6px solid #0096C7; margin-bottom: 15px; border-radius: 4px; }}
                
                .info-section h3 {{ margin: 0; color: #023E8A; font-size: 18px; }}
                
                /* HTML Table Styles */
                table.dataframe {{ width: 100%; border-collapse: collapse; font-size: 11px !important; table-layout: fixed; margin-top: 10px; font-family: 'Arial', sans-serif; }}
                table.dataframe th, table.dataframe td {{ border: 1px solid #ADE8F4 !important; padding: 8px 6px; text-align: right; white-space: normal; word-wrap: break-word; overflow-wrap: break-word; }}
                table.dataframe th {{ background-color: #00245E !important; color: white !important; text-align: center !important; font-weight: bold; }}
                table.dataframe tbody tr:nth-child(even) {{ background-color: #F8FDFF !important; }}
                table.dataframe tbody tr:nth-child(odd) {{ background-color: #FFFFFF !important; }}
                
                * {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
            </style>
        </head>
        <body style="zoom: 0.85;">
            <table class="header-table">
                <tr>
                    <td style="width: 70px;">{img_tag}</td>
                    <td><h1 style="margin: 0; font-size: 26px; font-weight: 800; letter-spacing: 1px; color: white;">Imo Chicken & Agro (Pvt) Ltd</h1></td>
                </tr>
            </table>
            <div class="info-section">
                <table style="width: 100%; border: none;">
                    <tr>
                        <td style="text-align: left; border: none; padding: 0;"><h3>Department: Sales & Marketing</h3></td>
                        <td style="text-align: center; border: none; padding: 0;"><h3>Report: {title}</h3></td>
                        <td style="text-align: right; border: none; padding: 0;"><h3>Date: {date_str}</h3></td>
                    </tr>
                </table>
            </div>
            
            <!-- HTML Legend Table -->
            <table style="width: 100%; border: none; margin-bottom: 15px; font-size: 14px; font-weight: bold; color: #03045E;">
                <tr>
                    <td style="text-align: right; border: none; padding: 0;">
                        <span style="display: inline-block; width: 14px; height: 14px; background-color: #D4EDDA; border: 1px solid #155724; vertical-align: middle;"></span><span style="vertical-align: middle;"> Target &ge; 100% &nbsp;&nbsp;&nbsp;</span>
                        <span style="display: inline-block; width: 14px; height: 14px; background-color: #FFF3CD; border: 1px solid #856404; vertical-align: middle;"></span><span style="vertical-align: middle;"> 75% - 99% &nbsp;&nbsp;&nbsp;</span>
                        <span style="display: inline-block; width: 14px; height: 14px; background-color: #FFE8CC; border: 1px solid #A04000; vertical-align: middle;"></span><span style="vertical-align: middle;"> 50% - 74% &nbsp;&nbsp;&nbsp;</span>
                        <span style="display: inline-block; width: 14px; height: 14px; background-color: #F8D7DA; border: 1px solid #721C24; vertical-align: middle;"></span><span style="vertical-align: middle;"> &lt; 50% &nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;</span>
                        <span style="display: inline-block; width: 14px; height: 14px; background-color: #E2F0CB; border: 1px solid #2D5A27; vertical-align: middle;"></span><span style="vertical-align: middle;"> Balance &ge; 0 &nbsp;&nbsp;&nbsp;</span>
                        <span style="display: inline-block; width: 14px; height: 14px; background-color: #FFD1D1; border: 1px solid #900000; vertical-align: middle;"></span><span style="vertical-align: middle;"> Balance &lt; 0</span>
                    </td>
                </tr>
            </table>
            
            {styler.to_html()}
        </body>
        </html>
        """
        
        options = {
            'page-size': 'A4', 'orientation': 'Landscape', 'margin-top': '0.3in', 'margin-right': '0.3in',
            'margin-bottom': '0.3in', 'margin-left': '0.3in', 'encoding': "UTF-8", 'enable-local-file-access': None
        }

        if platform.system() == "Windows":
            try:
                import pdfkit
                path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
                config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
                pdf_bytes = pdfkit.from_string(html_content, False, options=options, configuration=config)
                return pdf_bytes, "pdf", "application/pdf"
            except Exception as e:
                pass
        else:
            try:
                from xhtml2pdf import pisa
                from io import BytesIO
                result = BytesIO()
                pisa_status = pisa.CreatePDF(BytesIO(html_content.encode("utf-8")), dest=result)
                if not pisa_status.err:
                    return result.getvalue(), "pdf", "application/pdf"
            except Exception as e:
                pass

        # 🚀 Fallback to HTML Export
        return html_content.encode('utf-8'), "html", "text/html"

    # ============================================================
    # 6. SAVE / LOAD helpers for Google Sheet tabs
    # ============================================================
    def _get_or_create_ws(sheet, tab_name, headers=None, rows=2000, cols=30):
        try:
            ws = sheet.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound:
            ws = sheet.add_worksheet(title=tab_name, rows=rows, cols=cols)
            if headers:
                ws.append_row(headers)
        return ws

    def _save_df_to_tab(sheet, tab_name: str, df: pd.DataFrame, key_col_name: str, key_value: str):
        df = df.copy()
        df = df.replace([np.inf, -np.inf], 0).fillna(0)
        df.insert(0, key_col_name, key_value)

        headers = df.columns.tolist()
        ws = _get_or_create_ws(sheet, tab_name, headers=headers)

        all_values = ws.get_all_values()
        if not all_values:
            ws.append_row(headers)
            all_values = [headers]

        header = all_values[0]
        if key_col_name not in header:
            raise ValueError(f"The '{tab_name}' tab is missing a '{key_col_name}' column. Clear the tab and try again.")

        key_col_idx = header.index(key_col_name)
        rows_to_delete = []
        match_val = str(key_value).strip()
        
        for idx, row in enumerate(all_values, start=1):
            if idx > 1 and len(row) > key_col_idx:
                sheet_val = str(row[key_col_idx]).strip()
                if key_col_name == "Date":
                    try: sheet_val = pd.to_datetime(sheet_val).strftime("%Y-%m-%d")
                    except: pass
                elif key_col_name == "Month":
                    try: sheet_val = pd.to_datetime(sheet_val).strftime("%Y-%m")
                    except: pass
                if sheet_val == match_val:
                    rows_to_delete.append(idx)

        if rows_to_delete:
            rows_to_delete.sort()
            ranges = []
            start = prev = rows_to_delete[0]
            for r in rows_to_delete[1:]:
                if r == prev + 1: prev = r
                else:
                    ranges.append((start, prev))
                    start = prev = r
            ranges.append((start, prev))

            sheet_id = ws.id
            requests = []
            for (start_row, end_row) in reversed(ranges):
                requests.append({
                    "deleteDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "ROWS",
                            "startIndex": start_row - 1,
                            "endIndex": end_row,
                        }
                    }
                })
            ws.spreadsheet.batch_update({"requests": requests})

        values = df.astype(str).values.tolist()
        ws.append_rows(values, value_input_option="USER_ENTERED")
        return True

    def _load_df_from_tab(sheet, tab_name: str, key_col_name: str, key_value: str):
        try: ws = sheet.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound: return None

        all_values = ws.get_all_values()
        if len(all_values) < 2: return None

        header = all_values[0]
        if key_col_name not in header: return None

        key_col_idx = header.index(key_col_name)
        match_val = str(key_value).strip()
        rows = []
        
        for row in all_values[1:]:
            if len(row) > key_col_idx:
                sheet_val = str(row[key_col_idx]).strip()
                if key_col_name == "Date":
                    try: sheet_val = pd.to_datetime(sheet_val).strftime("%Y-%m-%d")
                    except: pass
                elif key_col_name == "Month":
                    try: sheet_val = pd.to_datetime(sheet_val).strftime("%Y-%m")
                    except: pass
                
                if sheet_val == match_val: rows.append(row)
                    
        if not rows: return None

        fixed_rows = [row + [""] * (len(header) - len(row)) for row in rows]
        return pd.DataFrame(fixed_rows, columns=header)

    def _delete_records(sheet, tab_name, key_col_name, key_value):
        try:
            ws = sheet.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound:
            return
            
        all_values = ws.get_all_values()
        if not all_values or len(all_values) < 2:
            return
            
        header = all_values[0]
        if key_col_name not in header:
            return
            
        key_col_idx = header.index(key_col_name)
        match_val = str(key_value).strip()
        rows_to_delete = []
        
        for idx, row in enumerate(all_values, start=1):
            if len(row) > key_col_idx:
                sheet_val = str(row[key_col_idx]).strip()
                if key_col_name == "Date":
                    try: sheet_val = pd.to_datetime(sheet_val).strftime("%Y-%m-%d")
                    except: pass
                elif key_col_name == "Month":
                    try: sheet_val = pd.to_datetime(sheet_val).strftime("%Y-%m")
                    except: pass
                if sheet_val == match_val:
                    rows_to_delete.append(idx)
                    
        if rows_to_delete:
            rows_to_delete.sort()
            ranges = []
            start = prev = rows_to_delete[0]
            for r in rows_to_delete[1:]:
                if r == prev + 1: prev = r
                else:
                    ranges.append((start, prev))
                    start = prev = r
            ranges.append((start, prev))
            sheet_id = ws.id
            requests = []
            for (start_row, end_row) in reversed(ranges):
                requests.append({
                    "deleteDimension": {
                        "range": { "sheetId": sheet_id, "dimension": "ROWS", "startIndex": start_row - 1, "endIndex": end_row }
                    }
                })
            ws.spreadsheet.batch_update({"requests": requests})

    def save_report_to_sheet(sheet, df_report: pd.DataFrame, selected_date_str: str):
        return _save_df_to_tab(sheet, "Rep_Report", df_report, "Date", selected_date_str)

    def load_report_for_date(sheet, selected_date_str: str):
        return _load_df_from_tab(sheet, "Rep_Report", "Date", selected_date_str)

    def save_weekly_report_to_sheet(sheet, df_weekly: pd.DataFrame, month_str: str):
        return _save_df_to_tab(sheet, "Rep_Weekly", df_weekly, "Month", month_str)

    def load_weekly_report_for_month(sheet, month_str: str):
        return _load_df_from_tab(sheet, "Rep_Weekly", "Month", month_str)

    def enforce_numeric_types(df: pd.DataFrame) -> pd.DataFrame:
        """Normalize report values and safely remove duplicate spreadsheet headers."""
        df = df.copy()
        df.columns = [str(col).strip() for col in df.columns]
        df = df.loc[:, ~df.columns.duplicated(keep="first")].copy()

        # 🚀 Google Sheet එකෙන් එන "No" තීරුවත් මෙතනදි අංකයක් නෙවෙයි, Text විදිහට තියාගන්නවා
        text_cols = [
            "Date", "Month", "No", "Manager", "Route", "Representative", "Status"
        ]

        for col in df.columns:
            if col not in text_cols:
                cleaned = (
                    df[col]
                    .astype(str)
                    .str.replace(",", "", regex=False)
                    .str.replace("%", "", regex=False)
                    .str.strip()
                )
                df[col] = pd.to_numeric(cleaned, errors="coerce").fillna(0.0)

        if "Date" in df.columns:
            df = df.drop(columns=["Date"])
        if "Month" in df.columns:
            df = df.drop(columns=["Month"])

        return df

    # ============================================================
    # 7. STREAMLIT UI
    # ============================================================
    try:
        st.set_page_config(page_title="Rep Sales Report", layout="wide")
    except:
        pass
        
    st.markdown("""
        <style>
        :root {
            --c-900: #03045E;
            --c-800: #023E8A;
            --c-700: #0077B6;
            --c-600: #0096C7;
            --c-500: #00B4D8;
            --c-400: #48CAE4;
            --c-300: #90E0EF;
            --c-200: #ADE8F4;
            --c-100: #CAF0F8;
            --accent: #DE9C40;
        }

        /* App Background */
        .stApp {
            background: linear-gradient(135deg, var(--c-100) 0%, #FFFFFF 100%);
            color: var(--c-900);
        }

        /* Hide Header background */
        [data-testid="stHeader"] {
            background: transparent !important;
        }

        /* Hide Top Padding & Overflow fixes */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            max-width: 98% !important;
            overflow-x: hidden !important;
            min-height: 85vh !important;
        }

        h1, h2, h3 { color: var(--c-900) !important; }

        div[data-testid="stDateInput"] label p {
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
        div[data-testid="stDateInput"] div[data-baseweb="input"]:focus-within {
            border: 2px solid #03045E !important;
            box-shadow: 0 0 8px rgba(3, 4, 94, 0.4) !important;
        }

        /* Save and Calculate Buttons Styling */
        button[kind="primary"] {
            background-color: #03045E !important;
            color: white !important;
            border-radius: 6px !important;
            font-weight: 600 !important;
        }
        button[kind="primary"]:hover {
            background-color: #0077B6 !important;
        }
        
        /* Secondary Buttons Styling */
        button[kind="secondary"] {
            background-color: #0096C7 !important;
            color: white !important;
            border-color: #0096C7 !important;
            border-radius: 6px !important;
        }
        button[kind="secondary"]:hover {
            background-color: #023E8A !important;
            border-color: #023E8A !important;
        }

        /* 🚀 අලුත් Table CSS එක (UI එකට) */
        .table-container {
            max-height: 500px;
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
        }
        .table-container td {
            border: 1px solid #ADE8F4 !important;
            padding: 10px 8px;
            white-space: nowrap;
        }
        .table-container tbody tr:nth-child(even) {
            background-color: #F8FDFF !important;
        }
        .table-container tbody tr:nth-child(odd) {
            background-color: #FFFFFF !important;
        }
        .table-container tbody tr:hover td {
            background-color: #EAF8FF !important;
            transition: 0.2s;
        }

        /* Delete / Cancel confirm buttons */
        div.element-container:has(.delete-target), div.element-container:has(.cancel-target) { display: none; }
        div.element-container:has(.delete-target) + div.element-container button {
            background-color: #D90429 !important; color: white !important; border: 1px solid #D90429 !important;
        }
        div.element-container:has(.delete-target) + div.element-container button:hover {
            background-color: #B20322 !important; border: 1px solid #B20322 !important; color: white !important;
        }
        div.element-container:has(.cancel-target) + div.element-container button {
            background-color: #28a745 !important; color: white !important; border: 1px solid #28a745 !important;
        }
        div.element-container:has(.cancel-target) + div.element-container button:hover {
            background-color: #218838 !important; border: 1px solid #218838 !important; color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("Rep Sales & Targets Report")
    
    col1, col2 = st.columns([2, 5], vertical_alignment="bottom")
    with col1:
        selected_date = st.date_input("Select Date:", value=datetime.date.today())
        
    selected_date_str = selected_date.strftime("%Y-%m-%d")
    selected_month_str = pd.to_datetime(selected_date_str).strftime("%Y-%m")
    
    st.divider()

    @st.cache_data(ttl=60, show_spinner=False)
    def fetch_existing_reports(date_str, month_str):
        sheet2 = get_sheets()
        df = load_report_for_date(sheet2, date_str)
        wk = load_weekly_report_for_month(sheet2, month_str)
        return df, wk

    existing_df, existing_weekly = fetch_existing_reports(selected_date_str, selected_month_str)

    if existing_df is not None and not existing_df.empty:
        st.session_state["rep_master_table"] = existing_df
        st.session_state["rep_report_date"] = selected_date_str
        st.session_state["rep_source"] = "saved"
        if existing_weekly is not None and not existing_weekly.empty:
            st.session_state["rep_weekly_table"] = existing_weekly
            st.session_state["rep_weekly_month"] = selected_month_str
            st.session_state["rep_weekly_source"] = "saved"
        else:
            st.session_state.pop("rep_weekly_table", None)
            st.session_state["rep_weekly_source"] = None

        st.info(f"✅ A previously generated report already exists for **{selected_date_str}**.")
    else:
        st.session_state.pop("rep_master_table", None)
        st.session_state.pop("rep_report_date", None)
        st.session_state.pop("rep_weekly_table", None)
        st.session_state["rep_source"] = None
        st.session_state["rep_weekly_source"] = None
        st.session_state["confirm_delete_rep_report"] = False

        st.info("No report exists for the selected date. Click the button below to generate and save one.")

        if st.button("▶ Calculate & Save Report", type="primary"):
            with st.spinner("Calculating and saving to Google Sheet..."):
                try:
                    clear_raw_cache()
                    master_table = build_master_table(selected_date_str)
                    weekly_table = build_weekly_breakdown(selected_date_str)

                    sheet2 = get_sheets()
                    save_report_to_sheet(sheet2, master_table, selected_date_str)
                    save_weekly_report_to_sheet(sheet2, weekly_table, selected_month_str)

                    st.session_state["rep_master_table"] = master_table
                    st.session_state["rep_report_date"] = selected_date_str
                    st.session_state["rep_weekly_table"] = weekly_table
                    st.session_state["rep_weekly_month"] = selected_month_str
                    st.session_state["rep_source"] = "saved"
                    st.session_state["rep_weekly_source"] = "saved"

                    fetch_existing_reports.clear()
                    st.success(f"Report for '{selected_date_str}' and its weekly breakdown were saved!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error during calculation/saving: {e}")

    if "rep_master_table" in st.session_state:
        st.divider()
        st.subheader(f"Report for {st.session_state['rep_report_date']}")
        
        report_df = enforce_numeric_types(st.session_state["rep_master_table"])
        
        st.markdown("""
        <div style="display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 15px; font-size: 16px; font-weight: 600; color: #03045E; background: white; padding: 12px; border-radius: 6px; border: 1px solid #D1E5EB;">
            <span style="color: #666; font-size: 16px;">Targets:</span>
            <div style="display: flex; align-items: center; gap: 6px;"><div style="width: 18px; height: 18px; background-color: #D4EDDA; border: 1px solid #155724; border-radius: 4px;"></div> &ge; 100%</div>
            <div style="display: flex; align-items: center; gap: 6px;"><div style="width: 18px; height: 18px; background-color: #FFF3CD; border: 1px solid #856404; border-radius: 4px;"></div> 75% - 99%</div>
            <div style="display: flex; align-items: center; gap: 6px;"><div style="width: 18px; height: 18px; background-color: #FFE8CC; border: 1px solid #A04000; border-radius: 4px;"></div> 50% - 74%</div>
            <div style="display: flex; align-items: center; gap: 6px;"><div style="width: 18px; height: 18px; background-color: #F8D7DA; border: 1px solid #721C24; border-radius: 4px;"></div> &lt; 50%</div>
            <span style="color: #ccc; margin: 0 10px;">|</span>
            <span style="color: #666; font-size: 16px;">Balance:</span>
            <div style="display: flex; align-items: center; gap: 6px;"><div style="width: 18px; height: 18px; background-color: #E2F0CB; border: 1px solid #2D5A27; border-radius: 4px;"></div> &ge; 0 (Good)</div>
            <div style="display: flex; align-items: center; gap: 6px;"><div style="width: 18px; height: 18px; background-color: #FFD1D1; border: 1px solid #900000; border-radius: 4px;"></div> &lt; 0 (Short)</div>
        </div>
        """, unsafe_allow_html=True)

        styled_master = style_dataframe(report_df, is_weekly=False)
        
        # 🚀 HTML Container (Web App Grid View)
        st.markdown(f"<div class='table-container'>{styled_master.to_html()}</div>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            # 🚀 CSV එක Download කරද්දිත් "No" තීරුව අයින් වෙනවා
            csv_df = report_df.drop(columns=["No"], errors="ignore")
            csv_bytes = csv_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="⬇ Download Report CSV",
                data=csv_bytes,
                file_name=f"rep_sales_report_{st.session_state['rep_report_date']}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with c2:
            export_data, ext, mime = generate_pdf_or_html(styled_master, "Representative Sales & Targets", st.session_state['rep_report_date'])
            st.download_button(
                label=f"🖨️ Download HTML Report",
                data=export_data,
                file_name=f"rep_sales_report_{st.session_state['rep_report_date']}.{ext}",
                mime=mime,
                use_container_width=True
            )

        st.divider()
        st.subheader(f"Weekly Breakdown — {pd.to_datetime(st.session_state['rep_report_date']).strftime('%B %Y')}")

        if "rep_weekly_table" not in st.session_state:
            with st.spinner("Building weekly breakdown..."):
                try:
                    st.session_state["rep_weekly_table"] = build_weekly_breakdown(st.session_state["rep_report_date"])
                    st.session_state["rep_weekly_month"] = selected_month_str
                    st.session_state["rep_weekly_source"] = "calculated"
                except Exception as e:
                    st.error(f"Could not build weekly breakdown: {e}")

        if "rep_weekly_table" in st.session_state:
            weekly_df = enforce_numeric_types(st.session_state["rep_weekly_table"])
            styled_weekly = style_dataframe(weekly_df, is_weekly=True)
            
            # 🚀 Wrap the Weekly table in HTML Container too
            st.markdown(f"<div class='table-container'>{styled_weekly.to_html()}</div>", unsafe_allow_html=True)

            wc1, wc2 = st.columns(2)
            with wc1:
                # 🚀 CSV එක Download කරද්දිත් "No" තීරුව අයින් වෙනවා
                weekly_csv_df = weekly_df.drop(columns=["No"], errors="ignore")
                weekly_csv_bytes = weekly_csv_df.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    label="⬇ Download Weekly Breakdown CSV",
                    data=weekly_csv_bytes,
                    file_name=f"rep_weekly_breakdown_{selected_month_str}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with wc2:
                w_export_data, w_ext, w_mime = generate_pdf_or_html(styled_weekly, "Weekly Sales Breakdown", selected_month_str)
                st.download_button(
                    label=f"🖨️ Download Weekly HTML Report",
                    data=w_export_data,
                    file_name=f"rep_weekly_breakdown_{selected_month_str}.{w_ext}",
                    mime=w_mime,
                    use_container_width=True
                )

        # ---- DELETE REPORT ----
        st.divider()
        if st.button("🗑️ Delete this Report", key="delete_rep_report_btn"):
            st.session_state["confirm_delete_rep_report"] = True

        if st.session_state.get("confirm_delete_rep_report"):
            st.error(f"Are you sure you want to permanently delete the report for {st.session_state['rep_report_date']}?")
            dc1, dc2 = st.columns([1, 6], vertical_alignment="bottom")
            with dc1:
                st.markdown('<span class="delete-target"></span>', unsafe_allow_html=True)
                if st.button("✅ Yes, delete it"):
                    with st.spinner("Deleting..."):
                        sheet2 = get_sheets()
                        _delete_records(sheet2, "Rep_Report", "Date", st.session_state["rep_report_date"])
                        _delete_records(sheet2, "Rep_Weekly", "Month", selected_month_str)

                        st.session_state.pop("rep_master_table", None)
                        st.session_state.pop("rep_report_date", None)
                        st.session_state.pop("rep_weekly_table", None)
                        st.session_state["rep_source"] = None
                        st.session_state["rep_weekly_source"] = None
                        st.session_state["confirm_delete_rep_report"] = False

                        fetch_existing_reports.clear()

                        msg_placeholder = st.empty()
                        msg_placeholder.success(f"🗑️ Report for {selected_date_str} successfully deleted!")
                        time.sleep(2)
                        msg_placeholder.empty()
                        st.rerun()
            with dc2:
                st.markdown('<span class="cancel-target"></span>', unsafe_allow_html=True)
                if st.button("Cancel"):
                    st.session_state["confirm_delete_rep_report"] = False
                    st.rerun()

if __name__ == "__main__":
    show()