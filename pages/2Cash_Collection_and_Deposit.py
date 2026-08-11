import streamlit as st
import pandas as pd
import datetime
import time
from gspread_dataframe import set_with_dataframe
import gspread

from util import connect_to_sheets, clear_sheet_cache

def show():
    # --- CSS Styling ---
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
        
        div[data-testid="stDateInput"] label p, div[data-testid="stSelectbox"] label p, div[data-testid="stNumberInput"] label p {
            font-family: 'Arial', sans-serif !important;
            font-weight: 800 !important;
            font-size: 15px !important;
            color: #03045E !important;
        }
        div[data-baseweb="input"], div[data-baseweb="select"] {
            border: 2px solid #0096C7 !important; 
            border-radius: 8px !important;        
            background-color: #F8FDFF !important; 
        }
        div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within {
            border: 2px solid #03045E !important; 
            box-shadow: 0 0 8px rgba(3, 4, 94, 0.4) !important;
        }
        
        /* Hide number input arrows (+ / -) */
        input[type="number"]::-webkit-inner-spin-button, 
        input[type="number"]::-webkit-outer-spin-button { 
            -webkit-appearance: none; 
            margin: 0; 
        }
        input[type="number"] {
            -moz-appearance: textfield;
        }
        /* Streamlit හි අලුත් +/- බොත්තම් සම්පූර්ණයෙන්ම සැඟවීම */
        [data-testid="stNumberInputStepUp"],
        [data-testid="stNumberInputStepDown"] {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='text-align: center; color: #03045E; font-weight: 800;'>💰 Daily Cash Collection</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #0077B6; font-weight: 600;'>Manage collections, bank deposits, and cash in hand per route.</p>", unsafe_allow_html=True)
    st.write("")

    # --- 1. SHEET CONNECTION ---
    sh = connect_to_sheets()
    
    # DSR Data Load කරගැනීම
    @st.cache_data(ttl=300, show_spinner=False)
    def get_dsr_data():
        try:
            ws_dsr = sh.worksheet("DSR")
            return pd.DataFrame(ws_dsr.get_all_records(default_blank=""))
        except:
            return pd.DataFrame()

    # Cash Collection Sheet එක Load කරගැනීම (Headers පරිශීලකයා විසින් සකසා ඇත)
    try:
        ws_cc = sh.worksheet("Cash_Collection")
    except gspread.exceptions.WorksheetNotFound:
        st.error("⚠️ 'Cash_Collection' sheet not found! Please create it and add headers manually.")
        st.stop()

    @st.cache_data(ttl=10, show_spinner=False)
    def get_cc_data():
        try:
            return pd.DataFrame(ws_cc.get_all_records(default_blank=""))
        except:
            return pd.DataFrame()

    # --- 2. MAIN UI: FILTERING ---
    df_dsr = get_dsr_data()
    
    col1, col2, col3 = st.columns([1.5, 2, 2], vertical_alignment="bottom")
    with col1:
        selected_date = st.date_input("Filter Date:", value=datetime.date.today())
        selected_date_str = selected_date.strftime('%Y-%m-%d')
    
    # "99" ඉවත් කර Route ලැයිස්තුව ලබා ගැනීම
    available_routes = []
    if not df_dsr.empty and "Date" in df_dsr.columns and "Location" in df_dsr.columns:
        dsr_filtered = df_dsr[df_dsr["Date"].astype(str) == selected_date_str]
        available_routes = dsr_filtered["Location"].dropna().unique().tolist()
        available_routes = sorted([str(r) for r in available_routes if str(r).strip() != "" and str(r).strip() != "99"])

    with col2:
        if not available_routes:
            selected_route = st.selectbox("Select Route:", ["No data available for this date"], disabled=True)
        else:
            selected_route = st.selectbox("Select Route:", ["-- Select --"] + available_routes)

    total_cash = 0.0
    if selected_route and selected_route != "-- Select --" and selected_route != "No data available for this date":
        route_data = dsr_filtered[dsr_filtered["Location"].astype(str) == selected_route]
        if "Cash Amount" in route_data.columns:
            route_data["Cash Amount"] = pd.to_numeric(route_data["Cash Amount"].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            total_cash = route_data["Cash Amount"].sum()

    with col3:
        st.markdown(f"""
            <div style="background-color: #03045E; padding: 10px; border-radius: 8px; text-align: center; border: 2px solid #00B4D8;">
                <span style="color: #90E0EF; font-size: 13px; font-weight: bold;">TOTAL CASH COLLECTION</span><br>
                <span style="color: #FFFFFF; font-size: 20px; font-weight: 900;">Rs. {total_cash:,.2f}</span>
            </div>
        """, unsafe_allow_html=True)

    st.divider()

    # --- 3. DATA ENTRY SECTION ---
    if selected_route and selected_route != "-- Select --" and selected_route != "No data available for this date":
        
        with st.form("cash_collection_form", clear_on_submit=True):
            st.markdown("<h4 style='color: #0077B6; margin-bottom: 15px;'>📝 Enter Collection Details</h4>", unsafe_allow_html=True)
            
            f_col1, f_col2, f_col3 = st.columns(3)
            
            with f_col1:
                deposit_date = st.date_input("Deposit Date", value=datetime.date.today())
            with f_col2:
                remark_selected = st.selectbox("Status", ["BOC", "COM", "H/O"])
            with f_col3:
                amount_str = st.text_input("Amount", placeholder="Enter Amount")

            submit_btn = st.form_submit_button("💾 Save Collection Data", type="primary", use_container_width=True)

            if submit_btn:
                try:
                    amount = float(amount_str.replace(',', '').strip())
                except ValueError:
                    amount = 0.0
                
                if amount <= 0:
                    st.error("⚠️ අනිවාර්යයෙන්ම 'Amount' අගයක් ඇතුළත් කළ යුතුයි.")
                else:
                    with st.spinner("Generating Index and Saving..."):
                        type_val = "Cash" if remark_selected == "H/O" else "Bank"
                        deposit_date_str = deposit_date.strftime('%Y-%m-%d')
                        
                        df_cc = get_cc_data()
                        
                        past_tot_col, past_tot_amt = 0, 0
                        has_past_records = False
                        
                        if not df_cc.empty and "Date" in df_cc.columns and "Route" in df_cc.columns:
                            mask_bal = (df_cc["Date"].astype(str) == selected_date_str) & (df_cc["Route"].astype(str) == selected_route)
                            past_records_bal = df_cc[mask_bal]
                            
                            if len(past_records_bal) > 0:
                                has_past_records = True
                                
                            # 'Total Cash Colle' ලෙස තීරුව නම් වී ඇත්නම් එය පරීක්ෂා කිරීම
                            tot_col_name = "Total Cash Colle" if "Total Cash Colle" in df_cc.columns else "Total Cash Collection"
                            if tot_col_name in df_cc.columns:
                                past_tot_col = pd.to_numeric(past_records_bal[tot_col_name].astype(str).str.replace(',', ''), errors='coerce').fillna(0).sum()
                                
                            if "Amount" in df_cc.columns:
                                past_tot_amt = pd.to_numeric(past_records_bal["Amount"].astype(str).str.replace(',', ''), errors='coerce').fillna(0).sum()
                            
                        final_total_cash = 0.0 if has_past_records else total_cash
                        balance = (past_tot_col + final_total_cash) - (past_tot_amt + amount)

                        next_num = 1
                        if not df_cc.empty and "Date" in df_cc.columns and "Route" in df_cc.columns and "Status" in df_cc.columns:
                            df_cc["ParsedDate"] = pd.to_datetime(df_cc["Date"], errors='coerce')
                            current_month = selected_date.month
                            current_year = selected_date.year
                            
                            mask_idx = (
                                (df_cc["Route"].astype(str) == selected_route) & 
                                (df_cc["Status"].astype(str) == remark_selected) & 
                                (df_cc["ParsedDate"].dt.month == current_month) & 
                                (df_cc["ParsedDate"].dt.year == current_year)
                            )
                            past_records_idx = df_cc[mask_idx]
                            next_num = len(past_records_idx) + 1
                        
                        entry_index = f"{remark_selected} {next_num:02d}"

                        # අලුත් පේළිය සැකසීම (අගටම Reconciled තීරුව සඳහා False)
                        new_row = [
                            selected_date_str,
                            selected_route,
                            final_total_cash,
                            deposit_date_str,
                            remark_selected, # Status
                            type_val,        # Type
                            amount,          # Amount
                            entry_index,     # Remark
                            balance,         # Balance
                            False            # Reconciled (Hidden from web view)
                        ]
                        
                        # 🚀 අලුත් පේළිය දාන්න කලින්, පරණ පේළියේ Balance එක Google Sheet එකෙන්ම මකා දැමීම
                        if has_past_records and "Balance" in df_cc.columns:
                            try:
                                last_record_idx = past_records_bal.index[-1]
                                sheet_row = int(last_record_idx) + 2 # DataFrame index 0 = Sheet row 2
                                balance_col_idx = df_cc.columns.get_loc("Balance") + 1
                                ws_cc.update_cell(sheet_row, balance_col_idx, "")
                            except Exception as e:
                                pass
                        
                        ws_cc.append_row(new_row)
                        
                        clear_sheet_cache()
                        get_cc_data.clear()
                        
                    st.success(f"✅ Data Saved Successfully! Generated Index: **{entry_index}** | Balance: **{balance:,.2f}**")
                    time.sleep(2.0)
                    st.rerun()

    # --- 4. RECENT ENTRIES TABLE ---
    st.write("")
    if selected_route and selected_route != "-- Select --" and selected_route != "No data available for this date":
        st.markdown(f"<h4 style='color: #03045E;'>📋 Cash Collections for Route: {selected_route}</h4>", unsafe_allow_html=True)
        
        df_cc_show = get_cc_data()
        if not df_cc_show.empty and "Date" in df_cc_show.columns and "Route" in df_cc_show.columns:
            df_cc_show = df_cc_show[
                (df_cc_show["Date"].astype(str) == selected_date_str) & 
                (df_cc_show["Route"].astype(str) == selected_route)
            ].copy()
            
            if not df_cc_show.empty:
                # 🚀 Reconciled තීරුව වෙබ් ඇප් එකේ පෙන්වීම වැළැක්වීමට එය ඉවත් කිරීම
                if "Reconciled" in df_cc_show.columns:
                    df_cc_show = df_cc_show.drop(columns=["Reconciled"])
                    
                tot_col_name = "Total Cash Colle" if "Total Cash Colle" in df_cc_show.columns else "Total Cash Collection"
                
                tot_col = pd.to_numeric(df_cc_show.get(tot_col_name, pd.Series([0])).astype(str).str.replace(',', ''), errors='coerce').fillna(0).sum()
                tot_amt = pd.to_numeric(df_cc_show.get("Amount", pd.Series([0])).astype(str).str.replace(',', ''), errors='coerce').fillna(0).sum()
                final_display_bal = tot_col - tot_amt
                
                # 0 අගයන් හිස් (Empty) බවට පත් කිරීමේ Function එක
                def fmt_currency(x):
                    try:
                        v = float(str(x).replace(',', ''))
                        if v == 0: return ""
                        return f"{v:,.2f}"
                    except:
                        return ""
                
                # Total Cash Collection සහ Amount හි ඇති බිංදු (0) හිස් කිරීම
                for col in [tot_col_name, "Amount"]:
                    if col in df_cc_show.columns:
                        df_cc_show[col] = df_cc_show[col].apply(fmt_currency)
                
                # 🚀 Balance තීරුවේ යටම පේළියට පමණක් අගය ලබා දීම, ඉතුරු ඒවා හිස් කිරීම
                if "Balance" in df_cc_show.columns:
                    balances = [""] * len(df_cc_show)
                    balances[-1] = fmt_currency(final_display_bal)
                    df_cc_show["Balance"] = balances
                
                styler = df_cc_show.style.set_table_styles([
                    {'selector': 'table', 'props': [('width', '100%'), ('border-collapse', 'collapse')]},
                    {'selector': 'th', 'props': [('background-color', '#0077B6'), ('color', 'white'), ('text-align', 'center'), ('padding', '8px')]},
                    {'selector': 'td', 'props': [('border', '1px solid #ADE8F4'), ('padding', '6px'), ('text-align', 'center')]},
                ]).hide(axis="index")
                
                st.markdown(f'<div style="border: 2px solid #0096C7; border-radius: 8px; overflow: hidden; width: 100%;">{styler.to_html()}</div>', unsafe_allow_html=True)
            else:
                st.info("No cash collection records found for the selected Date and Route.")
        else:
            st.info("No cash collection records found.")
    else:
        st.info("Please select a Route to view records.")

if __name__ == "__main__":
    show()