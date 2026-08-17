import streamlit as st
import pandas as pd
import datetime
import time
import calendar
import difflib
from gspread_dataframe import set_with_dataframe
import gspread

# util.py එකෙන් Connection ලබාගැනීම
try:
    from util import connect_to_sheets2, clear_sheet_cache
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
        
        /* File Uploader Styles */
        div[data-testid="stFileUploader"] label p {
            font-family: 'Arial', sans-serif !important;
            font-weight: 800 !important;
            font-size: 16px !important;
            color: #03045E !important;
        }
        div[data-testid="stFileUploaderDropzone"] {
            border: 2px dashed #0096C7 !important; 
            border-radius: 8px !important;
            background-color: #F8FDFF !important; 
            transition: all 0.3s ease-in-out;
        }
        div[data-testid="stFileUploaderDropzone"]:hover {
            border: 2px dashed #03045E !important;
            background-color: #EAF8FF !important;
        }
        
        [data-testid="stDataFrame"] {
            border: 2px solid #0096C7 !important;
            border-radius: 8px !important;
            overflow: hidden !important;
        }

        /* 🚀 Table CSS */
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
        .table-container tbody tr:nth-child(even) { background-color: #F8FDFF !important; }
        .table-container tbody tr:nth-child(odd) { background-color: #FFFFFF !important; }
        .table-container tbody tr:hover td { background-color: #EAF8FF !important; transition: 0.2s; }

        /* Delete Buttons CSS */
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

    st.markdown("<h2 style='text-align: center; color: #03045E; font-weight: 800;'>📦 Issued Qty Data Upload</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #0077B6; font-weight: 600;'>Upload system generated Excel/CSV to calculate total Issued Qty per Rep.</p>", unsafe_allow_html=True)
    st.write("")

    sheet2 = connect_to_sheets2()

    def section_banner(text):
        st.markdown(f'<div style="background-color:#052b6c;color:white;padding:10px;border-radius:5px;font-weight:bold;margin-bottom:15px;">{text}</div>', unsafe_allow_html=True)

    # STREAMLIT_CHUNK:Loading Master and Existing Data...
    @st.cache_data(ttl=60, show_spinner=False)
    def load_master_data():
        try:
            ws = sheet2.worksheet("MasterData_adjust")
            df = pd.DataFrame(ws.get_all_records(default_blank=""))
            if not df.empty and "Rep_Name" in df.columns and "Route" in df.columns:
                df = df[(df["Rep_Name"].astype(str).str.strip() != "") & (df["Route"].astype(str).str.strip() != "")]
                df["Route - Rep Name"] = df["Route"].astype(str).str.strip() + " - " + df["Rep_Name"].astype(str).str.strip()
                return df[["Rep_Name", "Route - Rep Name"]].drop_duplicates().reset_index(drop=True)
            return pd.DataFrame(columns=["Rep_Name", "Route - Rep Name"])
        except Exception as e:
            st.error(f"Error loading MasterData_adjust: {e}")
            return pd.DataFrame(columns=["Rep_Name", "Route - Rep Name"])

    @st.cache_data(ttl=10, show_spinner=False)
    def load_existing_issued_qty(year, month):
        try:
            ws = sheet2.worksheet("Issued_Qty")
            df = pd.DataFrame(ws.get_all_records(default_blank=""))
            if not df.empty:
                filtered = df[(df["Year"].astype(str) == str(year)) & (df["Month"].astype(str) == str(month))]
                if not filtered.empty:
                    return filtered[["Route - Rep Name", "Issued Qty"]]
            return pd.DataFrame()
        except gspread.exceptions.WorksheetNotFound:
            # Tab එක නැත්නම් අලුතින් හදනවා
            sheet2.add_worksheet(title="Issued_Qty", rows=2000, cols=10)
            return pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    def clear_caches():
        load_existing_issued_qty.clear()
        load_master_data.clear()
        try: clear_sheet_cache()
        except: pass

    # 🚀 NAME MAPPING FUNCTION (Word 1 -> Word 2 -> Fuzzy Match)
    def map_rep_name(agent_name, master_df):
        if pd.isna(agent_name) or not str(agent_name).strip():
            return "Unknown"
        agent_name = str(agent_name).strip()
        agent_parts = agent_name.split()
        master_names = master_df['Rep_Name'].astype(str).tolist()
        master_full = master_df['Route - Rep Name'].tolist()
        
        if len(agent_parts) > 0:
            word1 = agent_parts[0].lower()
            for idx, m_name in enumerate(master_names):
                if word1 == m_name.lower() or word1 in m_name.lower():
                    return master_full[idx]
        
        if len(agent_parts) > 1:
            word2 = agent_parts[1].lower()
            for idx, m_name in enumerate(master_names):
                if word2 == m_name.lower() or word2 in m_name.lower():
                    return master_full[idx]
                    
        matches = difflib.get_close_matches(agent_name.lower(), [m.lower() for m in master_names], n=1, cutoff=0.4)
        if matches:
            idx = [m.lower() for m in master_names].index(matches[0])
            return master_full[idx]
            
        return f"Unmapped: {agent_name}"

    # STREAMLIT_CHUNK:Rendering UI...
    col1, col2, col3 = st.columns([1, 2, 1], vertical_alignment="bottom")
    month_year_options = []
    for y in range(2024, 2031):
        for m in range(1, 13):
            month_year_options.append(f"{y} - {calendar.month_name[m]}")

    current_month_str = datetime.date.today().strftime("%Y - %B")
    with col2:
        selected_month_year = st.selectbox("Select Year & Month:", month_year_options, index=month_year_options.index(current_month_str) if current_month_str in month_year_options else 0)

    selected_year, selected_month = selected_month_year.split(" - ")
    st.divider()

    master_reps_df = load_master_data()
    existing_data_df = load_existing_issued_qty(selected_year, selected_month)

    # Base DataFrame එකක් හැදීම (ඔක්කොම Reps ලා ඇතුළත් කිරීමට)
    if not master_reps_df.empty:
        base_df = pd.DataFrame({"Route - Rep Name": master_reps_df["Route - Rep Name"]})
        base_df["Issued Qty"] = 0.0
    else:
        st.warning("⚠️ No valid data found in 'MasterData_adjust' tab.")
        base_df = pd.DataFrame(columns=["Route - Rep Name", "Issued Qty"])

    display_df = base_df.copy()
    has_data = not existing_data_df.empty

    c1, c2 = st.columns([8, 2], vertical_alignment="bottom")
    with c1:
        if has_data:
            st.success(f"✅ Existing Issued Qty data loaded for **{selected_month_year}**.")
        else:
            st.info(f"ℹ️ No existing data found for **{selected_month_year}**. Please upload a file.")
    with c2:
        if st.button("🗑️ Delete Data", use_container_width=True, disabled=not has_data, key="del_btn_issued"):
            st.session_state["confirm_del_issued"] = True
            
    if st.session_state.get("confirm_del_issued") and has_data:
        st.error(f"Are you sure you want to permanently delete data for {selected_month_year}?")
        dc1, dc2 = st.columns(2)
        with dc1:
            st.markdown('<span class="delete-target"></span>', unsafe_allow_html=True)
            if st.button("✅ Yes, Delete", use_container_width=True):
                with st.spinner("Deleting..."):
                    ws = sheet2.worksheet("Issued_Qty")
                    full_db_df = pd.DataFrame(ws.get_all_records(default_blank=""))
                    remaining_df = full_db_df[~((full_db_df["Year"].astype(str) == str(selected_year)) & (full_db_df["Month"].astype(str) == str(selected_month)))]
                    ws.clear()
                    set_with_dataframe(ws, remaining_df)
                    st.session_state["confirm_del_issued"] = False
                    clear_caches()
                    st.rerun()
        with dc2:
            st.markdown('<span class="cancel-target"></span>', unsafe_allow_html=True)
            if st.button("Cancel", use_container_width=True):
                st.session_state["confirm_del_issued"] = False
                st.rerun()

    if has_data:
        existing_dict = dict(zip(existing_data_df["Route - Rep Name"], existing_data_df["Issued Qty"]))
        display_df["Issued Qty"] = display_df["Route - Rep Name"].map(existing_dict).fillna(0.0)

    section_banner("1. Upload Raw Export Data")
    uploaded_file = st.file_uploader("Upload Excel or CSV (Must contain 'Sales Agent' and 'Issued Qty' columns)", type=["csv", "xlsx"])
    
    is_uploaded = False

    # STREAMLIT_CHUNK:Processing Uploaded File...
    if uploaded_file is not None:
        try:
            up_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            
            # Column headers වල හිස්තැන් තිබේ නම් ඒවා ඉවත් කර පරික්ෂා කිරීම
            up_df.columns = up_df.columns.str.strip()
            
            if "Sales Agent" in up_df.columns and "Issued Qty" in up_df.columns:
                up_df["Issued Qty"] = pd.to_numeric(up_df["Issued Qty"].astype(str).str.replace(',', ''), errors='coerce').fillna(0.0)
                
                with st.spinner("Mapping Agent Names to Routes..."):
                    up_df["Mapped_Rep"] = up_df["Sales Agent"].apply(lambda x: map_rep_name(x, master_reps_df))
                    grouped_df = up_df.groupby("Mapped_Rep")["Issued Qty"].sum().reset_index()
                    grouped_df.rename(columns={"Mapped_Rep": "Route - Rep Name"}, inplace=True)
                    
                    upload_dict = dict(zip(grouped_df["Route - Rep Name"], grouped_df["Issued Qty"]))
                    display_df["Issued Qty"] = display_df["Route - Rep Name"].map(upload_dict).fillna(0.0)
                    
                    unmapped = grouped_df[grouped_df["Route - Rep Name"].str.startswith("Unmapped", na=False)]
                    if not unmapped.empty:
                        display_df = pd.concat([display_df, unmapped], ignore_index=True)
                        st.warning("⚠️ Some names couldn't be mapped automatically. You can edit them manually below.")
                    
                    is_uploaded = True
                    st.success("✅ File processed successfully! Data has been grouped by Rep.")
            else:
                st.error("⚠️ The uploaded file must contain 'Sales Agent' and 'Issued Qty' columns. Please check your headers.")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    # STREAMLIT_CHUNK:Review and Save Data...
    if not display_df.empty and (is_uploaded or has_data):
        st.markdown("### 2. Review Data")
        st.write("The calculated Issued Qty per Rep is shown below.")
        
        def highlight_qty(val):
            try:
                if float(val) > 0: return 'background-color: #EAF8FF; color: #03045E; font-weight: bold;'
            except: pass
            return ''

        if hasattr(display_df.style, 'map'):
            styled_df = display_df.style.map(highlight_qty, subset=["Issued Qty"])
        else:
            styled_df = display_df.style.applymap(highlight_qty, subset=["Issued Qty"])

        styled_df = styled_df.format({"Issued Qty": "{:.2f}"})
        try: styled_df = styled_df.hide(axis="index")
        except: pass

        st.markdown(f"<div class='table-container'>{styled_df.to_html()}</div>", unsafe_allow_html=True)

        st.write("")
        if st.button("💾 Save Issued Qty to Database", type="primary", use_container_width=True):
            with st.spinner("Saving Data to Google Sheets..."):
                try:
                    ws = sheet2.worksheet("Issued_Qty")
                    full_db_df = pd.DataFrame(ws.get_all_records(default_blank=""))
                    if full_db_df.empty:
                        full_db_df = pd.DataFrame(columns=["Year", "Month", "Route - Rep Name", "Issued Qty"])
                    
                    remaining_df = full_db_df[~((full_db_df["Year"].astype(str) == str(selected_year)) & (full_db_df["Month"].astype(str) == str(selected_month)))].copy()
                    
                    save_df = display_df.copy()
                    save_df.insert(0, "Year", selected_year)
                    save_df.insert(1, "Month", selected_month)
                    
                    final_df = pd.concat([remaining_df, save_df], ignore_index=True)
                    ws.clear()
                    set_with_dataframe(ws, final_df)
                    
                    clear_caches()
                    msg_placeholder = st.empty()
                    msg_placeholder.success(f"✅ Issued Qty Data for {selected_month_year} saved successfully!")
                    time.sleep(2)
                    msg_placeholder.empty()
                    st.rerun()
                except Exception as e:
                    st.error(f"An error occurred while saving: {e}")

if __name__ == "__main__":
    show()