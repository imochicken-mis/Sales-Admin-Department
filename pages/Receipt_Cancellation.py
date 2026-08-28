import streamlit as st
import pandas as pd
import gspread
import numpy as np
from datetime import datetime
import time

# 🚀 util.py එකෙන් connection එක ලබාගැනීම
try:
    from util import connect_to_sheets
except ImportError:
    st.error("⚠️ 'connect_to_sheets' import error. Please check util.py.")

def show():
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
            font-weight: 600 !important;
            font-size: 16px !important;
            color: #03045E !important;
        }
        div[data-baseweb="select"] {
            border: 2px solid #0096C7 !important; 
            border-radius: 8px !important;        
            background-color: #F8FDFF !important; 
        }
        div[data-testid="stSelectbox"] div[data-baseweb="select"]:focus-within {
            border: 2px solid #03045E !important; 
            box-shadow: 0 0 8px rgba(3, 4, 94, 0.4) !important;
        }
        
        .table-container {
            max-height: 450px;
            overflow-y: auto;
            border-radius: 12px;
            border: 2px solid #0096C7;
            box-shadow: 0 8px 24px rgba(3, 4, 94, 0.1);
            background-color: #FFFFFF;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("🧾 Receipt Cancellation Upload")
    
    # Uploader එක Clear කිරීම සඳහා අලුත් Session State Key එකක්
    if "rec_uploader_key" not in st.session_state:
        st.session_state["rec_uploader_key"] = 0

    # ==========================================
    # 1. Year සහ Month එකට තේරීම (Single Dropdown)
    # ==========================================
    current_year = datetime.today().year
    current_month_name = datetime.today().strftime("%B")
    current_selection = f"{current_year} - {current_month_name}"
    
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    
    month_year_options = []
    for y in range(2020, 2035):
        for m in months:
            month_year_options.append(f"{y} - {m}")
            
    selected_month_year = st.selectbox(
        "🗓️ Select Year & Month:", 
        options=month_year_options, 
        index=month_year_options.index(current_selection) if current_selection in month_year_options else 0
    )
    
    selected_year_str, selected_month = selected_month_year.split(" - ")
    selected_year = int(selected_year_str)
        
    sheet = connect_to_sheets() 
    
    # ==========================================
    # 2. දැනටමත් තියෙන Data පෙන්වීම සහ මකා දැමීම
    # ==========================================
    with st.spinner("Checking for existing records..."):
        try:
            ws = sheet.worksheet("receipt_cancellation")
            all_values = ws.get_all_values()
            
            if len(all_values) > 1:
                headers = all_values[0]
                df_existing = pd.DataFrame(all_values[1:], columns=headers)
                df_existing.columns = df_existing.columns.astype(str).str.strip()
                
                if "Year" in df_existing.columns and "Month" in df_existing.columns:
                    df_existing = df_existing[
                        (df_existing["Year"].astype(str) == str(selected_year)) & 
                        (df_existing["Month"].astype(str) == selected_month)
                    ]
                else:
                    df_existing = pd.DataFrame() 
            else:
                df_existing = pd.DataFrame()
                
        except gspread.exceptions.WorksheetNotFound:
            df_existing = pd.DataFrame() 
            all_values = []
            
    if not df_existing.empty:
        col_ex1, col_ex2 = st.columns([4, 1], vertical_alignment="bottom")
        
        with col_ex1:
            st.markdown(f"### 🗃️ Existing Data for **{selected_month} {selected_year}**")
            
        with col_ex2:
            if st.button("🗑️ Delete Data", use_container_width=True):
                st.session_state["confirm_rec_delete"] = True
                
        if st.session_state.get("confirm_rec_delete", False):
            st.warning(f"Are you sure you want to delete all existing data for {selected_month} {selected_year}?")
            col_c1, col_c2, _ = st.columns([1, 1, 3])
            
            with col_c1:
                if st.button("✅ Yes, Delete", use_container_width=True):
                    with st.spinner("Deleting Data..."):
                        try:
                            year_col_idx = headers.index("Year")
                            month_col_idx = headers.index("Month")
                            
                            rows_to_delete = []
                            for idx, row in enumerate(all_values, start=1):
                                if idx > 1 and len(row) > max(year_col_idx, month_col_idx):
                                    sheet_year = str(row[year_col_idx]).strip()
                                    sheet_month = str(row[month_col_idx]).strip()
                                    
                                    if sheet_year == str(selected_year) and sheet_month == selected_month:
                                        rows_to_delete.append(idx)
                            
                            for r_idx in sorted(rows_to_delete, reverse=True):
                                ws.delete_rows(r_idx)
                                
                            st.session_state["confirm_rec_delete"] = False
                            st.success("Data deleted successfully!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting data: {e}")
            with col_c2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state["confirm_rec_delete"] = False
                    st.rerun()
                    
        st.dataframe(df_existing, height=350, use_container_width=True)
    else:
        st.info(f"ℹ️ No existing records found for **{selected_month} {selected_year}**.")

    st.divider()

    # ==========================================
    # 3. CSV Upload කිරීම
    # ==========================================
    st.write(f"Upload your **CSV** file to enter/update data for **{selected_month} {selected_year}**.")
    
    uploaded_file = st.file_uploader(
        "Upload CSV File (.csv)", 
        type=["csv"], 
        key=f"uploader_{st.session_state['rec_uploader_key']}"
    )

    if uploaded_file is not None:
        with st.spinner("Reading and Filtering CSV Data..."):
            try:
                df = pd.read_csv(uploaded_file)
                
                # 🚀 අලුත් Headers ලැයිස්තුව
                expected_cols = [
                    "Reference Number", "Receipt No", "Reason Code", "Reason", 
                    "Customer ID", "Customer Name", "Previous Balance", 
                    "New Balance", "Ledger Adjustment", "Cancelled By", "Cancelled At"
                ]
                
                missing_cols = [col for col in expected_cols if col not in df.columns]
                if missing_cols:
                    st.warning(f"⚠️ The following expected columns are missing in your CSV: {', '.join(missing_cols)}")
                    available_cols = [col for col in expected_cols if col in df.columns]
                    df = df[available_cols]
                else:
                    df = df[expected_cols]

                df = df.dropna(how='all').copy()

                st.success(f"✅ Data for {selected_month} {selected_year} Extracted Successfully!")
                
                st.markdown("### 🆕 New Data Preview")
                st.dataframe(df, height=350, use_container_width=True)

                if st.button("💾 Save to Google Sheets", type="primary"):
                    with st.spinner("Saving data to Google Sheets..."):
                        
                        try:
                            # 🚀 අලුත් Sheet එකේ නම
                            ws = sheet.worksheet("receipt_cancellation") 
                            if not ws.get_all_values():
                                ws.append_row(["Year", "Month"] + df.columns.tolist())
                        except gspread.exceptions.WorksheetNotFound:
                            ws = sheet.add_worksheet(title="receipt_cancellation", rows="1000", cols="20")
                            ws.append_row(["Year", "Month"] + df.columns.tolist())

                        clean_df = df.copy()
                        clean_df = clean_df.replace([np.nan, np.inf, -np.inf], "")
                        clean_df = clean_df.fillna("")
                        
                        clean_df.insert(0, "Month", selected_month)
                        clean_df.insert(0, "Year", selected_year)

                        all_values = ws.get_all_values()
                        if len(all_values) > 1:
                            header = all_values[0]
                            if "Year" in header and "Month" in header:
                                year_col_idx = header.index("Year")
                                month_col_idx = header.index("Month")
                                rows_to_delete = []
                                
                                for idx, row in enumerate(all_values, start=1):
                                    if idx > 1 and len(row) > max(year_col_idx, month_col_idx):
                                        sheet_year = str(row[year_col_idx]).strip()
                                        sheet_month = str(row[month_col_idx]).strip()
                                        
                                        if sheet_year == str(selected_year) and sheet_month == selected_month:
                                            rows_to_delete.append(idx)
                                
                                for r_idx in sorted(rows_to_delete, reverse=True):
                                    ws.delete_rows(r_idx)

                        final_data = clean_df.astype(str).replace("nan", "").values.tolist()
                        ws.append_rows(final_data, value_input_option="USER_ENTERED")
                        
                        st.success(f"🎉 Data for {selected_month} {selected_year} successfully saved!")
                        
                        time.sleep(2)
                        st.session_state["rec_uploader_key"] += 1
                        st.rerun()

            except Exception as e:
                st.error(f"⚠️ Error Processing File: {e}")

if __name__ == "__main__":
    show()