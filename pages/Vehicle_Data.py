import streamlit as st
import pandas as pd
import gspread
import numpy as np
from datetime import datetime
import re
import time

# 🚀 util.py එකෙන් connection එක ලබාගැනීම
try:
    from util import connect_to_sheets
except ImportError:
    st.error("⚠️ 'connect_to_sheets' import error.")

# ==========================================
# 1. Location එක Format කිරීම සහ Route එක සෙවීම
# ==========================================
def format_location(loc):
    if pd.isna(loc) or str(loc).strip() in ["", "nan", "NaN"]:
        return ""
    parts = str(loc).split('-')
    return " - ".join([p.strip().title() for p in parts])

def get_route_code(location):
    if pd.isna(location) or str(location).strip() in ["", "nan", "NaN"]:
        return ""
    
    route_mapping = {
        "bandulla - ampara": "BA",
        "badulla - ampara": "BA", 
        "monaragala - ampara": "MA",
        "matara - embilipitiya": "ME",
        "kandy - mahiyangana": "KM",
        "horana - beruwala": "HB",
        "colombo 03": "C3",
        "gampola - badulla": "NE",
        "monaragala - kahawaththa": "MK",
        "kandy - katugasthota": "KK",
        "kalutara - matara": "KT",
        "horeca": "HC",
        "avissawella - balangoda": "AB",
        "dambulla - trinco": "DT",
        "anuradapura - polonnaruwa": "AP",
        "kandy 02": "K2",
        "negambo - chilaw": "NC",
        "negambo - kuliyapitiya": "NK",
        "maharagama - horana": "MH",
        "homagama - nugegoda": "HN",
        "gampaha - kirindiwela": "GK",
        "gampaha 02": "G2",
        "avissawella - kurunegala": "AK",
        "kurunegala - galgamuwa": "KG"
    }
    
    clean_loc = str(location).lower().strip()
    clean_loc = re.sub(r'\s*-\s*', ' - ', clean_loc)
    
    if clean_loc in route_mapping:
        return route_mapping[clean_loc]
    else:
        return str(location).title()

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
        div[data-testid="stDateInput"] div[data-baseweb="input"]:focus-within, 
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
        
        .table-container::-webkit-scrollbar { width: 6px; }
        .table-container::-webkit-scrollbar-track { background: transparent; }
        .table-container::-webkit-scrollbar-thumb { background: #0096C7; border-radius: 10px; }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("🚛 Vehicle Data Upload & Sync")
    
    # Uploader එක Clear කිරීම සඳහා Session State Key එක
    if "uploader_key" not in st.session_state:
        st.session_state["uploader_key"] = 0

    selected_date = st.date_input("Select Date for Data Entry:", value=datetime.today())
    selected_date_str = selected_date.strftime("%Y-%m-%d")
    
    sheet = connect_to_sheets() 
    
    # ==========================================
    # 2. දැනටමත් තියෙන Data පෙන්වීම සහ මකා දැමීම
    # ==========================================
    with st.spinner("Checking for existing records..."):
        try:
            ws = sheet.worksheet("Vehicle_Data")
            all_values = ws.get_all_values()
            
            if len(all_values) > 1:
                headers = all_values[0]
                df_existing = pd.DataFrame(all_values[1:], columns=headers)
                
                df_existing.columns = df_existing.columns.astype(str).str.strip()
                
                if "Date" in df_existing.columns:
                    df_existing["Date_Formatted"] = pd.to_datetime(df_existing["Date"].astype(str).str.strip(), errors='coerce').dt.strftime("%Y-%m-%d")
                    df_existing = df_existing[df_existing["Date_Formatted"] == selected_date_str]
                    df_existing = df_existing.drop(columns=["Date_Formatted"]) 
                else:
                    df_existing = pd.DataFrame() 
            else:
                df_existing = pd.DataFrame()
                
        except gspread.exceptions.WorksheetNotFound:
            df_existing = pd.DataFrame() 
            
    if not df_existing.empty:
        st.markdown(f"### 🗃️ Existing Data for **{selected_date_str}**")
        
        # 🚀 මුලින්ම Table එක පෙන්වීම
        st.dataframe(df_existing, height=380, use_container_width=True)
        
        # 🚀 Table එකට යටින් Delete Button එක දකුණු පැත්තට වෙන්න දැමීම
        col_del1, col_del2 = st.columns([5, 1])
        with col_del2:
            if st.button("🗑️ Delete Data", use_container_width=True):
                st.session_state["confirm_delete"] = True
                
        # 🚀 මකා දැමීම තහවුරු කිරීම (Confirmation Options)
        if st.session_state.get("confirm_delete", False):
            st.warning(f"Are you sure you want to delete all existing data for {selected_date_str}?")
            col_c1, col_c2, _ = st.columns([1, 1, 3])
            
            with col_c1:
                if st.button("✅ Yes, Delete", use_container_width=True):
                    with st.spinner("Deleting Data..."):
                        try:
                            date_col_idx = headers.index("Date")
                            rows_to_delete = []
                            for idx, row in enumerate(all_values, start=1):
                                if idx > 1 and len(row) > date_col_idx:
                                    sheet_date = str(row[date_col_idx]).strip()
                                    try:
                                        sheet_date = pd.to_datetime(sheet_date).strftime("%Y-%m-%d")
                                    except:
                                        pass
                                    if sheet_date == selected_date_str:
                                        rows_to_delete.append(idx)
                            
                            for r_idx in sorted(rows_to_delete, reverse=True):
                                ws.delete_rows(r_idx)
                                
                            st.session_state["confirm_delete"] = False
                            st.success("Data deleted successfully!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting data: {e}")
            with col_c2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state["confirm_delete"] = False
                    st.rerun()
                    
    else:
        st.info(f"ℹ️ No existing records found for **{selected_date_str}**.")

    st.divider()

    # ==========================================
    # 3. Excel Upload කිරීම
    # ==========================================
    st.write(f"Upload your Excel file to enter/update data for **{selected_date_str}**. Data starting from **C3** will be extracted.")
    
    uploaded_file = st.file_uploader(
        "Upload Excel File (.xlsx)", 
        type=["xlsx", "xls"], 
        key=f"uploader_{st.session_state['uploader_key']}"
    )

    if uploaded_file is not None:
        with st.spinner("Reading and Filtering Excel Data..."):
            try:
                # C3 සිට කියවීම
                df = pd.read_excel(uploaded_file, header=2, usecols="C:J")
                
                expected_cols = ["No", "Vehicle Number", "Driver", "Capacity(Kg)", "Tank Qty", "Location", "Officer", "Helper"]
                df.columns = expected_cols

                statuses = []
                is_active = True
                for val in df['No']:
                    if pd.isna(val) or str(val).strip() == "":
                        is_active = False 
                        statuses.append(None) 
                    else:
                        statuses.append("On Route" if is_active else "Not on Route")
                
                df['Status'] = statuses
                df = df.dropna(subset=['Status']).copy() 

                # Data Formatting
                df['No'] = pd.to_numeric(df['No'], errors='coerce').fillna(0).astype(int)
                df['Vehicle Number'] = df['Vehicle Number'].astype(str).str.replace(' ', '', regex=False).str.upper()
                df['Driver'] = df['Driver'].astype(str).str.strip().str.title()
                df['Capacity(Kg)'] = pd.to_numeric(df['Capacity(Kg)'], errors='coerce').fillna(0)
                df['Tank Qty'] = pd.to_numeric(df['Tank Qty'], errors='coerce').fillna(0)
                df['Location'] = df['Location'].apply(format_location)
                df['Route'] = df['Location'].apply(get_route_code)
                df['Officer'] = df['Officer'].astype(str).str.strip().replace("nan", "").replace("Nan", "")
                df['Helper'] = df['Helper'].astype(str).str.strip().replace("nan", "").replace("Nan", "")

                st.success(f"✅ Data for {selected_date_str} Filtered & Cleaned Successfully!")
                
                st.markdown("### 🆕 New Data Preview")
                st.dataframe(df, height=380, use_container_width=True)

                if st.button("💾 Save to Google Sheets", type="primary"):
                    with st.spinner("Saving data to Google Sheets..."):
                        
                        try:
                            ws = sheet.worksheet("Vehicle_Data") 
                            if not ws.get_all_values():
                                ws.append_row(["Date"] + df.columns.tolist())
                        except gspread.exceptions.WorksheetNotFound:
                            ws = sheet.add_worksheet(title="Vehicle_Data", rows="1000", cols="20")
                            ws.append_row(["Date"] + df.columns.tolist())

                        clean_df = df.copy()
                        clean_df = clean_df.replace([np.nan, np.inf, -np.inf], "")
                        clean_df = clean_df.fillna("")
                        
                        clean_df.insert(0, "Date", selected_date_str)

                        # තෝරපු දවසට අදාළ පරණ Data මකා දැමීම
                        all_values = ws.get_all_values()
                        if len(all_values) > 1:
                            header = all_values[0]
                            if "Date" in header:
                                date_col_idx = header.index("Date")
                                rows_to_delete = []
                                
                                for idx, row in enumerate(all_values, start=1):
                                    if idx > 1 and len(row) > date_col_idx:
                                        sheet_date = str(row[date_col_idx]).strip()
                                        try:
                                            sheet_date = pd.to_datetime(sheet_date).strftime("%Y-%m-%d")
                                        except:
                                            pass
                                        
                                        if sheet_date == selected_date_str:
                                            rows_to_delete.append(idx)
                                
                                for r_idx in sorted(rows_to_delete, reverse=True):
                                    ws.delete_rows(r_idx)

                        # අලුත් Data Append කිරීම
                        final_data = clean_df.astype(str).replace("nan", "").values.tolist()
                        ws.append_rows(final_data, value_input_option="USER_ENTERED")
                        
                        st.success(f"🎉 Data for {selected_date_str} successfully saved!")
                        
                        time.sleep(2)
                        st.session_state["uploader_key"] += 1
                        st.rerun()

            except Exception as e:
                st.error(f"⚠️ Error Processing File: {e}")

if __name__ == "__main__":
    show()