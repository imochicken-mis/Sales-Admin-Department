import streamlit as st
import pandas as pd
import datetime
import time
import calendar
from gspread_dataframe import set_with_dataframe
import gspread

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
            border: 2px solid #0096C7 !important; border-radius: 8px !important; background-color: #F8FDFF !important; transition: all 0.3s ease-in-out;
        }
        div[data-baseweb="select"]:focus-within {
            border: 2px solid #03045E !important; box-shadow: 0 0 8px rgba(3, 4, 94, 0.4) !important;
        }
        
        /* File Uploader Styles */
        div[data-testid="stFileUploader"] label p {
            font-family: 'Arial', sans-serif !important; font-weight: 800 !important; font-size: 16px !important; color: #03045E !important;
        }
        div[data-testid="stFileUploaderDropzone"] {
            border: 2px dashed #0096C7 !important; border-radius: 8px !important; background-color: #F8FDFF !important; transition: all 0.3s ease-in-out;
        }
        div[data-testid="stFileUploaderDropzone"]:hover {
            border: 2px dashed #03045E !important; background-color: #EAF8FF !important;
        }
        
        [data-testid="stDataFrame"] {
            border: 2px solid #0096C7 !important; border-radius: 8px !important; overflow: hidden !important; box-shadow: 0 4px 15px rgba(3, 4, 94, 0.08) !important;
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

    st.markdown("<h2 style='text-align: center; color: #03045E; font-weight: 800;'>📊 Rep Variance Data Entry</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #0077B6; font-weight: 600;'>Upload CSV/Excel or Manually enter the variance amounts for each route & rep.</p>", unsafe_allow_html=True)
    st.write("")

    sheet2 = connect_to_sheets2()

    def section_banner(text):
        st.markdown(f'<div style="background-color:#052b6c;color:white;padding:10px;border-radius:5px;font-weight:bold;margin-bottom:15px;">{text}</div>', unsafe_allow_html=True)

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
            st.error(f"Error loading MasterData_adjust: {e}")
            return pd.DataFrame(columns=["Route - Rep Name"])

    @st.cache_data(ttl=10, show_spinner=False)
    def load_existing_variance(year, month):
        try:
            ws = sheet2.worksheet("Rep_Variance")
            df = pd.DataFrame(ws.get_all_records(default_blank=""))
            if not df.empty:
                filtered = df[(df["Year"].astype(str) == str(year)) & (df["Month"].astype(str) == str(month))]
                if not filtered.empty:
                    return filtered[["Route - Rep Name", "Variance Amount"]]
            return pd.DataFrame()
        except gspread.exceptions.WorksheetNotFound:
            sheet2.add_worksheet(title="Rep_Variance", rows=2000, cols=10)
            return pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    def clear_caches():
        load_existing_variance.clear()
        load_master_data.clear()
        try: clear_sheet_cache()
        except: pass

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
    existing_data_df = load_existing_variance(selected_year, selected_month)

    if not master_reps_df.empty:
        base_df = master_reps_df.copy()
        base_df["Variance Amount"] = 0.0
    else:
        st.warning("⚠️ No valid data found in 'MasterData_adjust' tab.")
        base_df = pd.DataFrame(columns=["Route - Rep Name", "Variance Amount"])

    has_data = not existing_data_df.empty

    c1, c2 = st.columns([8, 2], vertical_alignment="bottom")
    with c1:
        if has_data:
            st.success(f"✅ Existing variance data loaded for **{selected_month_year}**.")
        else:
            st.info(f"ℹ️ No existing data found for **{selected_month_year}**. You can enter new data.")
    with c2:
        if st.button("🗑️ Delete Data", use_container_width=True, disabled=not has_data, key="del_btn_var"):
            st.session_state["confirm_del_var"] = True
            
    if st.session_state.get("confirm_del_var") and has_data:
        st.error(f"Are you sure you want to permanently delete data for {selected_month_year}?")
        dc1, dc2 = st.columns(2)
        with dc1:
            st.markdown('<span class="delete-target"></span>', unsafe_allow_html=True)
            if st.button("✅ Yes, Delete", use_container_width=True):
                with st.spinner("Deleting..."):
                    ws = sheet2.worksheet("Rep_Variance")
                    full_db_df = pd.DataFrame(ws.get_all_records(default_blank=""))
                    remaining_df = full_db_df[~((full_db_df["Year"].astype(str) == str(selected_year)) & (full_db_df["Month"].astype(str) == str(selected_month)))]
                    ws.clear()
                    set_with_dataframe(ws, remaining_df)
                    st.session_state["confirm_del_var"] = False
                    clear_caches()
                    st.rerun()
        with dc2:
            st.markdown('<span class="cancel-target"></span>', unsafe_allow_html=True)
            if st.button("Cancel", use_container_width=True):
                st.session_state["confirm_del_var"] = False
                st.rerun()
    
    if has_data:
        existing_dict = dict(zip(existing_data_df["Route - Rep Name"], existing_data_df["Variance Amount"]))
        base_df["Variance Amount"] = base_df["Route - Rep Name"].map(existing_dict).fillna(0.0)

    c1, c2 = st.columns([1, 1], vertical_alignment="bottom")
    with c1: section_banner("1. Upload Data or Edit Manually")
    with c2:
        template_csv = base_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("⬇️ Download Entry Template (CSV)", data=template_csv, file_name=f"Rep_Variance_Template_{selected_month_year.replace(' ', '_')}.csv", mime="text/csv", use_container_width=True)

    uploaded_file = st.file_uploader("Upload filled CSV or Excel file", type=["csv", "xlsx"])
    if uploaded_file is not None:
        try:
            up_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            if "Route - Rep Name" in up_df.columns and "Variance Amount" in up_df.columns:
                up_df["Variance Amount"] = pd.to_numeric(up_df["Variance Amount"].astype(str).str.replace(',', ''), errors='coerce').fillna(0.0)
                upload_dict = dict(zip(up_df["Route - Rep Name"], up_df["Variance Amount"]))
                base_df["Variance Amount"] = base_df["Route - Rep Name"].map(upload_dict).fillna(0.0)
                st.success("✅ File loaded successfully! Check the table below and click 'Save to Database'.")
            else:
                st.error("⚠️ The uploaded file must contain 'Route - Rep Name' and 'Variance Amount' columns.")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    st.write("The calculated Variance Amounts per Rep are shown below.")
    
    # Table Styling (Green for Positive, Red for Negative)
    def highlight_variance(val):
        try:
            v = float(val)
            if v > 0: return 'background-color: #D4EDDA; color: #155724; font-weight: bold;'
            elif v < 0: return 'background-color: #FFD1D1; color: #900000; font-weight: bold;'
        except: pass
        return ''

    if hasattr(base_df.style, 'map'):
        styled_df = base_df.style.map(highlight_variance, subset=["Variance Amount"])
    else:
        styled_df = base_df.style.applymap(highlight_variance, subset=["Variance Amount"])

    styled_df = styled_df.format({"Variance Amount": "{:.2f}"})
    try: styled_df = styled_df.hide(axis="index")
    except: pass

    st.markdown(f"<div class='table-container'>{styled_df.to_html()}</div>", unsafe_allow_html=True)

    st.write("")
    if st.button("💾 Save Variance to Database", type="primary", use_container_width=True):
        with st.spinner("Saving Data to Google Sheets..."):
            try:
                ws = sheet2.worksheet("Rep_Variance")
                full_db_df = pd.DataFrame(ws.get_all_records(default_blank=""))
                if full_db_df.empty:
                    full_db_df = pd.DataFrame(columns=["Year", "Month", "Route - Rep Name", "Variance Amount"])
                
                remaining_df = full_db_df[~((full_db_df["Year"].astype(str) == str(selected_year)) & (full_db_df["Month"].astype(str) == str(selected_month)))].copy()
                
                save_df = base_df.copy()
                save_df.insert(0, "Year", selected_year)
                save_df.insert(1, "Month", selected_month)
                
                final_df = pd.concat([remaining_df, save_df], ignore_index=True)
                ws.clear()
                set_with_dataframe(ws, final_df)
                
                clear_caches()
                msg_placeholder = st.empty()
                msg_placeholder.success(f"✅ Variance Data for {selected_month_year} saved successfully!")
                time.sleep(2)
                msg_placeholder.empty()
                st.rerun()
            except Exception as e:
                st.error(f"An error occurred while saving: {e}")

if __name__ == "__main__":
    show()