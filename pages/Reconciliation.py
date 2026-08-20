import streamlit as st
import pandas as pd
import datetime
import time
from gspread_dataframe import set_with_dataframe
import gspread
from util import connect_to_sheets, clear_sheet_cache
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode

def show():
    # STREAMLIT CHUNK: Styling the UI...
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
            font-weight: 800 !important;
            font-size: 15px !important;
            color: #03045E !important;
        }
        div[data-baseweb="input"], div[data-baseweb="select"] {
            border: 2px solid #0096C7 !important; 
            border-radius: 8px !important;        
            background-color: #F8FDFF !important; 
        }
        div[data-testid="stCheckbox"] label p {
            font-weight: bold !important;
            color: #023E8A !important;
        }

        /* 🔽 Brand Color Styling - AgGrid wrapper + Save button */
        div[data-testid="stForm"], div.ag-theme-alpine {
            border: 2px solid #00245E !important;
            border-radius: 10px !important;
            padding: 6px !important;
        }
        .ag-header {
            background-color: #00245E !important;
            color: #FFFFFF !important;
        }
        .ag-header-cell-text {
            color: #FFFFFF !important;
            font-weight: 800 !important;
        }
        .ag-root-wrapper {
            background-color: #D4F3FA !important;
        }
        /* 🔼 Brand Color Styling ends here */

        </style>
    """, unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: #03045E; font-weight: 800;'>✅ Data Reconciliation</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #0077B6; font-weight: 600;'>Fast edit collections, update balances, and mark records as reconciled.</p>", unsafe_allow_html=True)
    st.write("")
    # STREAMLIT CHUNK: Loading Google Sheets Data...
    sh = connect_to_sheets()
    try:
        ws_cc = sh.worksheet("Cash_Collection")
    except Exception as e:
        st.error("⚠️ 'Cash_Collection' sheet not found!")
        return
    @st.cache_data(ttl=10, show_spinner=False)
    def get_cc_data():
        try:
            return pd.DataFrame(ws_cc.get_all_records(default_blank=""))
        except:
            return pd.DataFrame()
    df_cc = get_cc_data()
        
    if df_cc.empty:
        st.info("No data available to reconcile.")
        return

    if "grid_version" not in st.session_state:
        st.session_state.grid_version = 0

    if "Reconciled" not in df_cc.columns:
        df_cc["Reconciled"] = "FALSE"
        
    df_cc["__row_num__"] = df_cc.index + 2
    # STREAMLIT CHUNK: Rendering Filters...
    st.markdown("### 🔍 Filter Records")
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1], vertical_alignment="bottom")
    
    with col1:
        enable_date = st.checkbox("Filter by Date", value=True)
        if enable_date:
            filter_date = st.date_input("Collection Date:", value=datetime.date.today())
            
    with col2:
        routes = ["All"] + sorted([str(r) for r in df_cc["Route"].unique() if str(r).strip() != "" and str(r).strip() != "99"])
        filter_route = st.selectbox("Route:", routes)

    with col3:
        bank_types = ["All"] + sorted([str(b) for b in df_cc.get("Type", pd.Series(["BOC", "COM", "H/O"])).unique() if str(b).strip() != ""])
        filter_bank = st.selectbox("Bank (Type):", bank_types)

    filtered_df = df_cc.copy()
    if enable_date:
        filtered_df = filtered_df[filtered_df["Date"].astype(str) == filter_date.strftime('%Y-%m-%d')]
    if filter_route != "All":
        filtered_df = filtered_df[filtered_df["Route"].astype(str) == filter_route]
    if filter_bank != "All":
        filtered_df = filtered_df[filtered_df["Type"].astype(str) == filter_bank]
    if filtered_df.empty:
        st.info("No records found for the selected filters.")
        return
    # STREAMLIT CHUNK: Preparing DataFrame for Editor...
    display_df = filtered_df.copy()
    display_df["Reconciled"] = display_df["Reconciled"].astype(str).str.upper() == 'TRUE'
    
    # 0 අගයන් හිස් කිරීම (Total Cash Collection සඳහා)
    def fmt_collection(x):
        try:
            if pd.isna(x) or str(x).strip() == "": return ""
            v = float(str(x).replace(',', ''))
            if v == 0: return "" # 0 අගය හිස්ව පෙන්වයි
            return f"{v:,.2f}"
        except:
            return ""
    # Balance සඳහා හිස්තැන් හිස්ව පෙන්වා අනිත්වා 0.00 ලෙස හෝ පෙන්වීම
    def fmt_balance(x):
        try:
            if pd.isna(x) or str(x).strip() == "": return ""
            v = float(str(x).replace(',', ''))
            return f"{v:,.2f}"
        except:
            return ""
    display_df["Total Cash Collection"] = display_df["Total Cash Collection"].apply(fmt_collection)
    display_df["Balance"] = display_df["Balance"].apply(fmt_balance)
    
    # Format Amount & Date
    display_df["Amount"] = pd.to_numeric(display_df["Amount"].astype(str).str.replace(',', ''), errors='coerce').fillna(0.0)
    display_df["Deposit Date"] = pd.to_datetime(display_df["Deposit Date"], errors='coerce').dt.strftime('%Y-%m-%d').fillna("")
    st.divider()
    
    # STREAMLIT CHUNK: Rendering Editable + Color-Coded AgGrid Table...
    st.markdown("### 📝 Editable Records")
    
    select_all = st.checkbox("✅ Select All / Deselect All Filtered Rows (Tick to mark all as reconciled)")
    if select_all:
        display_df["Reconciled"] = True

    cols_to_show = ["Reconciled", "Date", "Route", "Total Cash Collection", "Deposit Date", "Type", "Amount", "Remark", "Balance", "__row_num__"]
    grid_df = display_df[cols_to_show].copy()

    # 🚀 JS-based conditional cell style: Reconciled True -> Green, False -> Red
    # Applied only to: Deposit Date, Type, Amount
    recon_cell_style = JsCode("""
        function(params) {
            if (params.data.Reconciled === true) {
                return {
                    'backgroundColor': '#D4EDDA',
                    'color': '#0F5132',
                    'fontWeight': 'bold'
                };
            } else {
                return {
                    'backgroundColor': '#F8D7DA',
                    'color': '#842029',
                    'fontWeight': 'bold'
                };
            }
        }
    """)

    gb = GridOptionsBuilder.from_dataframe(grid_df)
    gb.configure_default_column(editable=False, resizable=True, filter=False)

    gb.configure_column("Reconciled", header_name="Reconciled?", editable=True, cellRenderer="agCheckboxCellRenderer",
                         cellEditor="agCheckboxCellEditor", singleClickEdit=True)
    gb.configure_column("Date", editable=False)
    gb.configure_column("Route", editable=False)
    gb.configure_column("Total Cash Collection", editable=False)
    gb.configure_column("Deposit Date", editable=True, cellStyle=recon_cell_style)
    gb.configure_column("Type", editable=True, cellEditor="agSelectCellEditor",
                         cellEditorParams={"values": ["", "BOC", "COM", "H/O"]}, cellStyle=recon_cell_style)
    gb.configure_column("Amount", editable=True, type=["numericColumn"], cellStyle=recon_cell_style)
    gb.configure_column("Remark", editable=False)
    gb.configure_column("Balance", editable=False)
    gb.configure_column("__row_num__", hide=True)

    grid_options = gb.build()

    st.caption("💡 *Tick 'Reconciled' to see Total Cash Collection / Deposit Date / Status turn Green (reconciled) or Red (not reconciled) live in the same table.*")

    grid_response = AgGrid(
        grid_df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        data_return_mode=DataReturnMode.AS_INPUT,
        allow_unsafe_jscode=True,
        fit_columns_on_grid_load=True,
        theme="alpine",
        height=450,
        key=f"aggrid_{select_all}_{st.session_state.grid_version}"
    )

    edited_df = pd.DataFrame(grid_response["data"])

    st.write("")
    submit_btn = st.button("💾 Save Reconciliations & Update Balances", type="primary", use_container_width=True)
    
    # STREAMLIT CHUNK: Processing and Saving Updates...
    if submit_btn:
        with st.spinner("Saving changes and recalculating balances..."):
            
            full_df = get_cc_data().copy()
            
            # 1. සංස්කරණය කළ දත්ත මුල් DataFrame එකට යාවත්කාලීන කිරීම
            for idx, row in edited_df.iterrows():
                row_num = int(row["__row_num__"])
                df_idx = row_num - 2 
                
                full_df.at[df_idx, "Reconciled"] = str(row["Reconciled"]).upper()
                
                dep_d = row["Deposit Date"]
                full_df.at[df_idx, "Deposit Date"] = str(dep_d) if pd.notnull(dep_d) and str(dep_d).strip() != "" else ""
                
                # 🚀 3. "Type" එක මත පදනම්ව Status එක සැකසීම
                type_val = row["Type"]
                full_df.at[df_idx, "Type"] = type_val
                full_df.at[df_idx, "Status"] = "Cash" if type_val == "H/O" else "Bank"
                full_df.at[df_idx, "Amount"] = float(row["Amount"])

            # 2. BULK RECALCULATE REMARKS (INDEX)
            full_df['ParsedDate'] = pd.to_datetime(full_df['Date'], errors='coerce')
            full_df['Month'] = full_df['ParsedDate'].dt.month
            full_df['Year'] = full_df['ParsedDate'].dt.year
            
            # 🚀 4. Remark එක හැදෙන විදිහ "Type" එකට අදාළව වෙනස් කර ඇත
            full_df['Rank'] = full_df.groupby(['Route', 'Type', 'Month', 'Year']).cumcount() + 1
            full_df['Remark'] = full_df['Type'] + " " + full_df['Rank'].apply(lambda x: f"{x:02d}")
            
            # 🚀 Balance අලුතින් ගණනය කිරීම (අවසාන පේළියට පමණක් යෙදීම)
            full_df['Total Cash Collection Numeric'] = pd.to_numeric(full_df['Total Cash Collection'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            full_df['Amount Numeric'] = pd.to_numeric(full_df['Amount'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            
            # 🚀 ERROR FIX: String ගැටළුව මඟහරවා ගැනීමට තීරුව Object ලෙස හිස් කිරීම
            full_df['Balance'] = None
            full_df['Balance'] = full_df['Balance'].astype(object)
            
            # Date සහ Route අනුව Group කර අවසාන (Recent) පේළියට පමණක් Balance එක සෙවීම
            grouped = full_df.groupby(['Date', 'Route'])
            for (d, r), group in grouped:
                tot_col = group['Total Cash Collection Numeric'].sum()
                tot_amt = group['Amount Numeric'].sum()
                final_bal = float(tot_col - tot_amt)
                
                # අවසාන පේළියේ Index එක අරගෙන ඒකට පමණක් අගය යෙදීම
                last_idx = group.index[-1]
                full_df.at[last_idx, 'Balance'] = final_bal
            
            # ඉතිරි හිස් තැන් (None) සඳහා හිස් අගයක් ("") යෙදීම
            full_df['Balance'] = full_df['Balance'].fillna("")
            
            # අනවශ්‍ය තීරු ඉවත් කිරීම
            full_df = full_df.drop(columns=['ParsedDate', 'Month', 'Year', 'Rank', 'Total Cash Collection Numeric', 'Amount Numeric'])
                
            # යාවත්කාලීන කළ දත්ත Google Sheet එකට Overwrite කිරීම
            ws_cc.clear()
            set_with_dataframe(ws_cc, full_df)
            
            clear_sheet_cache()
            get_cc_data.clear()

            # 🚀 Grid version increment - AgGrid key එක වෙනස් කරලා, sheet එකෙන්
            # අලුතෙන් load වෙන data එකට අනුව color condition ඇත්තටම refresh වෙන්නට
            st.session_state.grid_version += 1
            
            st.success("✅ Reconciliations & Balances saved successfully!")
            time.sleep(2)
            st.rerun()
if __name__ == "__main__":
    show()