import streamlit as st
import pandas as pd
import datetime
import time
from gspread_dataframe import set_with_dataframe
import gspread

# 'util' එකෙන් අවශ්‍ය Functions Import කරගැනීම
from util import connect_to_sheets, clear_sheet_cache

def show():
    # STREAMLIT CHUNK: Rendering the page header...
    st.markdown("<h2 style='text-align: center; color: #03045E; font-weight: 800;'>📥 Daily Sales Report (DSR)</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #0077B6; font-weight: 600;'>Upload and manage daily cash collections based on location.</p>", unsafe_allow_html=True)
    st.write("Welcome, Susen...! This is your private area.")
    st.write("Here you can enter DSR Report.")

    # --- 1. SHEET CONNECTION ---
    # STREAMLIT CHUNK: Connecting to Google Sheets...
    sh = connect_to_sheets()  # "Sales data" sheet එකට Connect වීම
    try:
        ws_dsr = sh.worksheet("DSR")
    except gspread.exceptions.WorksheetNotFound:
        # DSR Tab එක නැත්නම් අලුතින් සෑදීම
        ws_dsr = sh.add_worksheet(title="DSR", rows=3000, cols=10)

    # 🚀 1. DSR2 Tab එකත් සම්බන්ධ කරගැනීම හෝ අලුතින් සෑදීම
    try:
        ws_dsr2 = sh.worksheet("DSR2")
    except gspread.exceptions.WorksheetNotFound:
        ws_dsr2 = sh.add_worksheet(title="DSR2", rows=3000, cols=10)

    # --- 2. UNIQUE LOCAL CACHE ---
    @st.cache_data(ttl=600, show_spinner=False)
    def get_local_dsr_data(unique_key):
        try:
            return ws_dsr.get_all_records(default_blank="")
        except Exception:
            return []

    # --- 3. HELPER FUNCTIONS ---
    def save_and_refresh(message, seconds=2):
        clear_sheet_cache()
        get_local_dsr_data.clear() 
        msg_placeholder = st.empty()
        msg_placeholder.success(message)
        time.sleep(seconds)
        msg_placeholder.empty()
        st.rerun()

    def get_rows_for_date(date_str):
        records = get_local_dsr_data("DSR_data_cache")
        df = pd.DataFrame(records)
        if df.empty or "Date" not in df.columns:
            return pd.DataFrame()
            
        standardized_dates = pd.to_datetime(df["Date"], errors="coerce").dt.strftime('%Y-%m-%d')
        standardized_dates = standardized_dates.fillna(df["Date"].astype(str).str.strip())
        
        return df[standardized_dates == date_str]

    def delete_rows_for_date(date_str):
        records = get_local_dsr_data("DSR_data_cache")
        df = pd.DataFrame(records)
        if df.empty or "Date" not in df.columns:
            return
            
        standardized_dates = pd.to_datetime(df["Date"], errors="coerce").dt.strftime('%Y-%m-%d')
        standardized_dates = standardized_dates.fillna(df["Date"].astype(str).str.strip())
            
        remaining = df[standardized_dates != date_str]
        ws_dsr.clear()
        set_with_dataframe(ws_dsr, remaining if not remaining.empty else pd.DataFrame(columns=df.columns))
        
        # 🚀 1. DSR2 Tab එකෙන් අදාළ දිනට අදාළ දත්ත වෙනමම මකා දැමීම
        try:
            records_2 = ws_dsr2.get_all_records(default_blank="")
            df_2 = pd.DataFrame(records_2)
            if not df_2.empty and "Date" in df_2.columns:
                std_dates_2 = pd.to_datetime(df_2["Date"], errors="coerce").dt.strftime('%Y-%m-%d')
                std_dates_2 = std_dates_2.fillna(df_2["Date"].astype(str).str.strip())
                remaining_2 = df_2[std_dates_2 != date_str]
                ws_dsr2.clear()
                set_with_dataframe(ws_dsr2, remaining_2 if not remaining_2.empty else pd.DataFrame(columns=df_2.columns))
        except Exception:
            pass
        
        clear_sheet_cache() 
        get_local_dsr_data.clear()

    def section_banner(text):
        st.markdown(f'<div class="section-banner" style="background-color:#052b6c;color:white;padding:10px;border-radius:5px;font-weight:bold;">{text}</div>', unsafe_allow_html=True)

    def styled_table(df, gradient_cols=None, cmap="Blues"):
        if df.empty:
            return df
        
        styler = df.style
        if gradient_cols:
            gradient_cols = [c for c in gradient_cols if c in df.columns]
            if gradient_cols:
                styler = styler.background_gradient(subset=gradient_cols, cmap=cmap)
        
        styler = styler.set_table_styles([
            {'selector': 'table', 'props': [('width', '100%'), ('border-collapse', 'collapse'), ('table-layout', 'fixed')]},
            {'selector': 'th', 'props': [('background-color', '#03045E'), ('color', 'white'), ('font-weight', 'bold'), ('text-align', 'center'), ('border', '1px solid #ADE8F4'), ('padding', '10px'), ('position', 'sticky'), ('top', '0'), ('z-index', '2')]},
            {'selector': 'td', 'props': [('border', '1px solid #ADE8F4'), ('padding', '8px'), ('text-align', 'center')]},
            {'selector': 'tr:nth-child(even)', 'props': [('background-color', '#F8FDFF')]},
            {'selector': 'tr:nth-child(odd)', 'props': [('background-color', '#FFFFFF')]}
        ])
        
        styler = styler.hide(axis="index")
        if "Cash Amount" in df.columns:
            styler = styler.format({"Cash Amount": "{:,.2f}"})
        return styler

    # --- 4. STYLING (CSS) ---
    # STREAMLIT CHUNK: Applying custom CSS styling...
    st.markdown("""
        <style>
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            max-width: 98% !important;
            overflow-x: hidden !important;
            min-height: 85vh !important;
        }
        [data-testid="stHeader"] {
            background: transparent !important;
        }
        div[data-testid="stDateInput"] label p { font-family: 'Arial', sans-serif !important; font-weight: 800 !important; font-size: 16px !important; color: #03045E !important; }
        div[data-testid="stDateInput"] div[data-baseweb="input"] { border: 2px solid #0096C7 !important; border-radius: 8px !important; background-color: #F8FDFF !important; transition: all 0.3s ease-in-out; padding-left: 5px; }
        div[data-testid="stDateInput"] div[data-baseweb="input"]:focus-within { border: 2px solid #03045E !important; box-shadow: 0 0 8px rgba(3, 4, 94, 0.4) !important; }
        div[data-testid="stFileUploader"] label p { font-family: 'Arial', sans-serif !important; font-weight: 800 !important; font-size: 16px !important; color: #03045E !important; }
        div[data-testid="stFileUploaderDropzone"] { border: 2px dashed #0096C7 !important; border-radius: 8px !important; background-color: #F8FDFF !important; transition: all 0.3s ease-in-out; }
        div[data-testid="stFileUploaderDropzone"]:hover { border: 2px dashed #03045E !important; background-color: #EAF8FF !important; }
        div.element-container:has(.delete-target), div.element-container:has(.cancel-target) { display: none; }
        div.element-container:has(.delete-target) + div.element-container button { background-color: #D90429 !important; color: white !important; border: 1px solid #D90429 !important; }
        div.element-container:has(.delete-target) + div.element-container button:hover { background-color: #B20322 !important; border: 1px solid #B20322 !important; color: white !important; }
        div.element-container:has(.cancel-target) + div.element-container button { background-color: #28a745 !important; color: white !important; border: 1px solid #28a745 !important; }
        div.element-container:has(.cancel-target) + div.element-container button:hover { background-color: #218838 !important; border: 1px solid #218838 !important; color: white !important; }
        
        .table-wrapper::-webkit-scrollbar { width: 8px; height: 8px; }
        .table-wrapper::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 4px; }
        .table-wrapper::-webkit-scrollbar-thumb { background: #0096C7; border-radius: 4px; }
        .table-wrapper::-webkit-scrollbar-thumb:hover { background: #03045E; }
        
        .table-wrapper table { width: 100% !important; table-layout: fixed !important; margin: 0 !important; }
        </style>
    """, unsafe_allow_html=True)
    
    # --- 5. MAIN UI ---
    # STREAMLIT CHUNK: Rendering primary UI and table actions...
    col1, col2, col3 = st.columns([1.8, 1, 3],vertical_alignment="bottom")
    with col1:
        selected_date = st.date_input("Select Date:", value=datetime.date.today())
        selected_date_str = selected_date.strftime('%Y-%m-%d')
    st.divider()

    section_banner("📥 Upload Customer DSR")

    existing_dsr = get_rows_for_date(selected_date_str)
    
    if not existing_dsr.empty:
        if "Location" in existing_dsr.columns:
            existing_dsr = existing_dsr[existing_dsr["Location"].astype(str).str.strip() != "99"]
            
        st.warning(f"⚠️ DSR data already exists for **{selected_date_str}**.")
        
        my_styled_table = styled_table(existing_dsr, gradient_cols=["Cash Amount"], cmap="Blues")
        
        table_html = '<div class="table-wrapper" style="max-height: 400px; overflow-y: auto; border-radius: 8px; border: 2px solid #0096C7; background-color: white;">' + my_styled_table.to_html() + '</div>'
        st.markdown(table_html, unsafe_allow_html=True)
        st.write("") 

        if st.button("🗑️ Delete DSR data for this date", key="delete_dsr_btn"):
            st.session_state["confirm_delete_dsr"] = True

        if st.session_state.get("confirm_delete_dsr"):
            st.error(f"Permanently delete DSR records for {selected_date_str}?")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown('<span class="delete-target"></span>', unsafe_allow_html=True)
                if st.button("✅ Yes, delete it", key="confirm_delete_dsr_yes"):
                    delete_rows_for_date(selected_date_str)
                    st.session_state["confirm_delete_dsr"] = False
                    save_and_refresh(f"🗑️ DSR data for {selected_date_str} deleted.")
            with c2:
                st.markdown('<span class="cancel-target"></span>', unsafe_allow_html=True)
                if st.button("Cancel", key="confirm_delete_dsr_no"):
                    st.session_state["confirm_delete_dsr"] = False
                    st.rerun()

    else:
        # STREAMLIT CHUNK: Processing uploaded CSV and updating Rep Names...
        st.info("Upload DSR CSV File. The system will automatically extract Location and Cash Amount.")
        
        if "dsr_uploader_key" not in st.session_state:
            st.session_state["dsr_uploader_key"] = 0
            
        uploaded_file = st.file_uploader(
            "Upload CSV File", 
            type=["csv"], 
            key=f"dsr_uploader_{st.session_state['dsr_uploader_key']}"
        )
        
        if uploaded_file is not None:
            try:
                df_csv = pd.read_csv(uploaded_file)
                
                if len(df_csv.columns) < 10:
                    st.error("⚠️ Uploaded CSV does not have the required columns. It must have at least 10 columns.")
                else:
                    if st.button("Processing and Submit", type="primary", key="dsr_submit"):
                        with st.spinner("Processing Data..."):
                            df_filtered = df_csv.iloc[:, [3, 9]].copy()
                            df_filtered.columns = ["Location", "Cash Amount"]
                            
                            df_filtered = df_filtered[df_filtered["Location"].astype(str).str.strip() != "99"]
                            
                            df_filtered["Cash Amount"] = pd.to_numeric(df_filtered["Cash Amount"], errors='coerce').fillna(0)
                            
                            df_grouped = df_filtered.groupby("Location", as_index=False)["Cash Amount"].sum()
                            
                            # Sales_Reps_Master_data ශීට් එකෙන් නියෝජිතයන්ගේ නම් (Rep Names) ලබා ගැනීම
                            try:
                                ws_reps = sh.worksheet("Sales_Reps_Master_data")
                                df_reps = pd.DataFrame(ws_reps.get_all_records(default_blank=""))
                                if not df_reps.empty and "Route" in df_reps.columns and "Rep_Name" in df_reps.columns:
                                    rep_mapping = dict(zip(df_reps["Route"].astype(str).str.strip(), df_reps["Rep_Name"].astype(str).str.strip()))
                                else:
                                    rep_mapping = {}
                            except Exception:
                                rep_mapping = {}
                                
                            # Location තීරුව "Location - Mr.Rep_Name" ලෙස Format කිරීම
                            def format_location(loc):
                                rep_name = rep_mapping.get(str(loc).strip(), "Unknown")
                                
                                if rep_name.lower().startswith("mr."):
                                    rep_name = rep_name[3:].strip()
                                elif rep_name.lower().startswith("mr "):
                                    rep_name = rep_name[3:].strip()
                                    
                                return f"{loc} - Mr.{rep_name}"
                                
                            df_grouped["Location"] = df_grouped["Location"].apply(format_location)
                            
                            df_grouped.insert(0, "Date", selected_date_str)
                            
                            all_existing_data = ws_dsr.get_all_values()
                            if not all_existing_data:
                                ws_dsr.append_row(df_grouped.columns.tolist())
                            
                            data_to_upload = df_grouped.values.tolist()
                            ws_dsr.append_rows(data_to_upload)
                        
                            # 🚀 2. DSR2 Tab එකට CSV එකේ ඔරිජිනල් දත්ත (Raw Data) ඒ විදිහටම ඇතුළත් කිරීම
                            df_dsr2 = df_csv.copy()
                            # Delete කිරීමට පහසු වීමට පමණක් 'Date' තීරුව මුලට එක් කරමු
                            if "Date" not in df_dsr2.columns:
                                df_dsr2.insert(0, "Date", selected_date_str)
                            
                            df_dsr2 = df_dsr2.fillna("") # හිස්තැන් මගහැරීම
                            
                            all_existing_data_2 = ws_dsr2.get_all_values()
                            if not all_existing_data_2:
                                ws_dsr2.append_row(df_dsr2.columns.tolist())
                            
                            data_to_upload_2 = df_dsr2.values.tolist()
                            ws_dsr2.append_rows(data_to_upload_2)

                        st.session_state["dsr_uploader_key"] += 1
                        save_and_refresh("✅ DSR successfully processed! Saved to DSR (Grouped) and DSR2 (Raw Format)!")

            except Exception as e:
                st.error(f"Error processing file: {e}")