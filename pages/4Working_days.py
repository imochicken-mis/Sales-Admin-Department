import streamlit as st
from util import fetch_database_records, connect_to_sheets, connect_to_sheets2
import pandas as pd
from gspread_dataframe import set_with_dataframe
import gspread
import datetime
import calendar
import time

def show():
    st.title("Production Requirement")
    st.write("Welcome! This is your private area.")
    st.write("Here you can manage Working Days.")
    
    st.sidebar.markdown("---")
    
    if st.sidebar.button("🔄 Refresh All Data", key="home_refresh_btn_wd"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

    @st.cache_resource(show_spinner=False)
    def get_connection():
        sh = connect_to_sheets()
        sh2 = connect_to_sheets2()
        
        try:
            ws_working_days = sh.worksheet("Working_Days")
        except gspread.exceptions.WorksheetNotFound:
            ws_working_days = sh.add_worksheet(title="Working_Days", rows=3000, cols=15)
            
        try:
            ws_daily_sales = sh2.worksheet("Sales_day_book")
        except gspread.exceptions.WorksheetNotFound:
            ws_daily_sales = sh2.add_worksheet(title="Sales_day_book", rows=3000, cols=15)
            
        return ws_working_days, ws_daily_sales

    try:
        ws_working_days, ws_daily_sales = get_connection()
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        st.stop()

    st.markdown("""
        <style>
        div[data-testid="stSelectbox"] label p {
            font-family: 'Arial', sans-serif !important;
            font-weight: 600 !important;
            font-size: 16px !important;
            color: #03045E !important;
        }
        
        div[data-testid="stSelectbox"] div[data-baseweb="select"] {
            border: 2px solid #0096C7 !important; 
            border-radius: 8px !important;        
            background-color: #F8FDFF !important; 
            transition: all 0.3s ease-in-out;     
        }
        
        div[data-testid="stSelectbox"] div[data-baseweb="select"]:focus-within {
            border: 2px solid #03045E !important; 
            box-shadow: 0 0 8px rgba(3, 4, 94, 0.4) !important;
        }
        
        [data-testid="stDataFrame"] {
            border: 2px solid #0096C7 !important;
            border-radius: 8px !important;
            overflow: hidden !important;
        }
        </style>
    """, unsafe_allow_html=True)

    def section_banner(text):
        st.markdown(f'<div class="section-banner" style="background-color:#052b6c;color:white;padding:10px;border-radius:5px;font-weight:bold;">{text}</div>', unsafe_allow_html=True)

    section_banner("📅 Manage Working Days by Date")
    st.write("")

    with st.spinner("Syncing data..."):
        # 1. Read sheet data
        raw_working_days = ws_working_days.get_all_records(default_blank="")
        df_working = pd.DataFrame(raw_working_days)
        
        # 2. Date Auto-Fill Logic (Expand 1st date to the whole month)
        if not df_working.empty and "Date" in df_working.columns:
            df_working["Date"] = pd.to_datetime(df_working["Date"], errors="coerce")
            df_working = df_working.dropna(subset=["Date"])
            df_working["Working Days"] = pd.to_numeric(df_working["Working Days"], errors="coerce").fillna(0).astype(int)
            
            expanded_rows = []
            df_working['YearMonth'] = df_working['Date'].dt.to_period('M')
            
            for ym, group in df_working.groupby('YearMonth'):
                group = group.sort_values('Date')
                # Mase add karala thiyana mulma date eke 'Working Days' target eka gannawa
                base_wd = group.iloc[0]['Working Days'] 
                
                year = ym.year
                month = ym.month
                # E maseta adala mulu dawas gana gannawa
                num_days = calendar.monthrange(year, month)[1] 
                
                # User specifically wenas karapu dawas thiyanawanm ewa record karagannawa
                date_to_wd = dict(zip(group['Date'].dt.date, group['Working Days']))
                
                for day in range(1, num_days + 1):
                    current_date = datetime.date(year, month, day)
                    wd_val = date_to_wd.get(current_date, base_wd)
                    
                    expanded_rows.append({
                        "Date": current_date,
                        "Working Days": wd_val
                    })
                    
            df_expanded = pd.DataFrame(expanded_rows)
            df_expanded = df_expanded.sort_values("Date").reset_index(drop=True)
        else:
            df_expanded = pd.DataFrame(columns=["Date", "Working Days"])

        # 3. Calculate Worked Days based on Sales Book
        raw_sales = ws_daily_sales.get_all_records(default_blank="")
        df_sales = pd.DataFrame(raw_sales)

        valid_sales = pd.DataFrame()
        if not df_sales.empty:
            target_col = next((col for col in df_sales.columns if col.strip().lower() in ["new_date", "date"]), None)
            if target_col:
                df_sales['Date_obj'] = pd.to_datetime(df_sales[target_col], errors='coerce')
                valid_sales = df_sales.dropna(subset=['Date_obj']).copy()
                if not valid_sales.empty:
                    valid_sales['Just_Date'] = valid_sales['Date_obj'].dt.date

        worked_days_list = []
        days_to_work_list = []

        for idx, row in df_expanded.iterrows():
            row_date = row["Date"]
            wd = int(row.get("Working Days", 0))
            wkd = 0
            
            if not valid_sales.empty:
                # Sales book eken adala mase e date eka wenakal thiyana dawas gana gannawa
                mask = (
                    (valid_sales['Date_obj'].dt.year == row_date.year) &
                    (valid_sales['Date_obj'].dt.month == row_date.month) &
                    (valid_sales['Just_Date'] <= row_date)
                )
                wkd = valid_sales[mask]['Just_Date'].nunique()

            worked_days_list.append(wkd)
            days_to_work_list.append(max(0, wd - wkd))
            
        updated_df_working = df_expanded.copy()
        if not updated_df_working.empty:
            updated_df_working["Worked Days"] = worked_days_list
            updated_df_working["Days to Work"] = days_to_work_list
            updated_df_working["Working Days"] = updated_df_working["Working Days"].astype(str)
            updated_df_working["Date"] = pd.to_datetime(updated_df_working["Date"]).dt.strftime('%Y-%m-%d')
        else:
            updated_df_working = pd.DataFrame(columns=["Date", "Working Days", "Worked Days", "Days to Work"])

        # 4. Auto-Save Logic (Sheet eke thiyana data walatai expanded data walatai wenasak nam auto save wenawa)
        needs_auto_save = False
        
        if not df_working.empty:
            orig_compare = pd.DataFrame(raw_working_days)
            for col in ["Date", "Working Days", "Worked Days", "Days to Work"]:
                if col not in orig_compare.columns:
                    orig_compare[col] = ""
            orig_records = orig_compare[["Date", "Working Days", "Worked Days", "Days to Work"]].fillna("").astype(str).to_dict('records')
        else:
            orig_records = []
            
        if not updated_df_working.empty:
            new_records = updated_df_working[["Date", "Working Days", "Worked Days", "Days to Work"]].fillna("").astype(str).to_dict('records')
        else:
            new_records = []
            
        if orig_records != new_records:
            needs_auto_save = True

        save_cols = ["Date", "Working Days", "Worked Days", "Days to Work"]
        
        if needs_auto_save and not updated_df_working.empty:
            save_df = updated_df_working[save_cols].copy()
            ws_working_days.clear()
            set_with_dataframe(ws_working_days, save_df)
            st.toast("✅ Working Days auto-synced & dates auto-filled!", icon="🔄")

    # Change to standard date formats for the editor
    if not updated_df_working.empty:
        updated_df_working["Date"] = pd.to_datetime(updated_df_working["Date"], errors='coerce').dt.date

    edited_working_days = st.data_editor(
        updated_df_working,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        disabled=["Worked Days", "Days to Work"],
        column_config={
            "Date": st.column_config.DateColumn("Date", required=True, format="YYYY-MM-DD"),
            "Working Days": st.column_config.NumberColumn("Working Days", min_value=0, max_value=31, required=True),
            "Worked Days": st.column_config.NumberColumn("Worked Days (Auto)"),
            "Days to Work": st.column_config.NumberColumn("Days to Work (Auto)"),
        },
        key="working_days_editor",
    )

    st.write("")
    if st.button("Save Manual Changes", type="primary", key="save_wd_btn"):
        with st.spinner("Saving changes..."):
            # Editor eken dena data eka gannawa
            save_df = edited_working_days[save_cols].copy()
            save_df["Date"] = pd.to_datetime(save_df["Date"]).dt.strftime('%Y-%m-%d')
            save_df["Working Days"] = save_df["Working Days"].astype(str)
            
            # Save karama st.rerun() wela auto-fill logic eken ithuru dawas tika expand karanawa!
            ws_working_days.clear()
            if not save_df.empty:
                set_with_dataframe(ws_working_days, save_df)
            
        msg_placeholder = st.empty()
        msg_placeholder.success("✅ Working days successfully saved!")
        time.sleep(2)
        msg_placeholder.empty()
        st.rerun()