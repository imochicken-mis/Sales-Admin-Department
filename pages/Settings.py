import streamlit as st
import pandas as pd
import time
from gspread_dataframe import set_with_dataframe
import gspread

try:
    from util import connect_to_sheets2, clear_sheet_cache
except ImportError:
    st.error("Error: Could not import connection functions from util.py")

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
        
        div[data-testid="stSelectbox"] label p, div[data-testid="stTextInput"] label p {
            font-family: 'Arial', sans-serif !important;
            font-weight: 800 !important;
            font-size: 15px !important;
            color: #03045E !important;
        }
        div[data-baseweb="select"], div[data-baseweb="input"] {
            border: 2px solid #0096C7 !important; 
            border-radius: 8px !important;        
            background-color: #F8FDFF !important; 
            transition: all 0.3s ease-in-out;
        }
        div[data-baseweb="select"]:focus-within, div[data-baseweb="input"]:focus-within {
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

    st.markdown("<h2 style='text-align: center; color: #03045E; font-weight: 800;'>⚙️ Master Data Management</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #0077B6; font-weight: 600;'>Manage Sales Representatives, Routes, and Dealers.</p>", unsafe_allow_html=True)
    st.write("")

    # STREAMLIT CHUNK: Loading Google Sheets Data...
    sh2 = connect_to_sheets2()
    try:
        ws_master = sh2.worksheet("MasterData")
    except gspread.exceptions.WorksheetNotFound:
        # Sheet එක නැත්නම් අලුතින් සාදයි
        ws_master = sh2.add_worksheet(title="MasterData", rows=1000, cols=10)
        ws_master.append_row(["No", "Manager", "Route", "Representative", "Status"])

    @st.cache_data(ttl=10, show_spinner=False)
    def get_master_data():
        try:
            return pd.DataFrame(ws_master.get_all_records(default_blank=""))
        except:
            return pd.DataFrame(columns=["No", "Manager", "Route", "Representative", "Status"])

    df_master = get_master_data()

    if df_master.empty and "Manager" not in df_master.columns:
        df_master = pd.DataFrame(columns=["No", "Manager", "Route", "Representative", "Status"])

    # STREAMLIT CHUNK: Filtering by Manager & Global Search...
    col1, col2 = st.columns([1, 1], vertical_alignment="bottom")
    
    with col1:
        managers = ["All"] + sorted([str(m) for m in df_master["Manager"].unique() if str(m).strip() != ""])
        selected_manager = st.selectbox("Filter by Manager:", managers)
        
    with col2:
        search_query = st.text_input("🔍 Global Search (Manager, Route, Rep, Status):", "")

    # DataFrame එක හැසිරවීම සඳහා හැඳුනුම් අංකයක් (Row Num) සැඟවීම
    df_display = df_master.copy()
    df_display["__row_num__"] = df_display.index + 2 # Google Sheet rows start at 2 (1 is header)

    # 1. Manager Filter එක Apply කිරීම
    if selected_manager != "All":
        df_display = df_display[df_display["Manager"] == selected_manager]

    # 2. Global Search එක Apply කිරීම
    if search_query:
        search_cols = ["Manager", "Route", "Representative", "Status"]
        mask = df_display[search_cols].apply(lambda x: x.astype(str).str.contains(search_query, case=False, na=False)).any(axis=1)
        df_display = df_display[mask]

    st.divider()

    # STREAMLIT CHUNK: Rendering Editable DataGrid...
    st.markdown("### 📝 Edit Records")
    st.caption("💡 *Tip: To **Delete**, tick the built-in checkbox on the far left, press the **Delete key** on your keyboard (or the Trash icon 🗑️), and click Save. To **Add**, type in the empty row at the bottom.*")

    with st.form("master_data_form", clear_on_submit=False):
        # තීරු පිළිවෙළ (Column Order) සැකසීම
        cols_order = ["No", "Manager", "Route", "Representative", "Status", "__row_num__"]
        df_display = df_display[[c for c in cols_order if c in df_display.columns]]
        
        edited_df = st.data_editor(
            df_display,
            hide_index=True,
            num_rows="dynamic", # අලුත් පේළි එකතු කිරීමට ඉඩදෙයි
            use_container_width=True,
            column_config={
                "No": st.column_config.NumberColumn("No", disabled=True), # 'No' එක ඉබේම ගණනය වේ
                "Manager": st.column_config.TextColumn("Manager", required=True),
                "Route": st.column_config.TextColumn("Route"),
                "Representative": st.column_config.TextColumn("Representative"),
                "Status": st.column_config.SelectboxColumn(
                    "Status", 
                    options=["Rep", "Dealer", "HORECA"],
                    required=True
                ),
                "__row_num__": None # මෙය සැඟවුණු තීරුවකි (Hidden Column)
            },
            key=f"editor_{selected_manager}_{search_query}"
        )

        st.write("")
        submit_btn = st.form_submit_button("💾 Save Changes to Master Data", type="primary", use_container_width=True)

    # STREAMLIT CHUNK: Processing and Saving Updates...
    if submit_btn:
        with st.spinner("Saving master data updates..."):
            full_df = get_master_data().copy()
            
            original_row_nums = df_display["__row_num__"].dropna().tolist()
            edited_row_nums = edited_df["__row_num__"].dropna().tolist()
            
            # 🚀 Streamlit Native Delete මගින් මකා දැමූ පේළි අල්ලා ගැනීම
            deleted_row_nums = set(original_row_nums) - set(edited_row_nums)

            # 1. පවතින දත්ත යාවත්කාලීන කිරීම (Update existing rows)
            for idx, row in edited_df.dropna(subset=["__row_num__"]).iterrows():
                if row["__row_num__"] in deleted_row_nums:
                    continue 
                    
                sheet_idx = int(row["__row_num__"]) - 2 
                full_df.at[sheet_idx, "Manager"] = str(row["Manager"]).strip()
                full_df.at[sheet_idx, "Route"] = str(row["Route"]).strip()
                full_df.at[sheet_idx, "Representative"] = str(row["Representative"]).strip()
                full_df.at[sheet_idx, "Status"] = str(row["Status"]).strip()

            # 2. මකා දැමූ දත්ත ප්‍රධාන DataFrame එකෙන් ඉවත් කිරීම (Delete removed rows)
            if deleted_row_nums:
                indices_to_drop = [int(r) - 2 for r in deleted_row_nums]
                full_df = full_df.drop(index=indices_to_drop, errors="ignore")

            # 3. අලුතින් එකතු කළ දත්ත ප්‍රධාන DataFrame එකට දැමීම (Add new rows)
            new_rows = edited_df[edited_df["__row_num__"].isna()].copy()
            
            if not new_rows.empty:
                new_rows = new_rows.drop(columns=["__row_num__"], errors="ignore") 
                # හිස්ව තැබූ Manager තීරු වලට පමණක් තෝරාගත් Manager ව ආදේශ කිරීම (නැත්නම් අලුත් Manager ව තබාගැනීම)
                if selected_manager != "All":
                    new_rows["Manager"] = new_rows["Manager"].apply(lambda x: selected_manager if pd.isna(x) or str(x).strip() == "" else x)
                    
                full_df = pd.concat([full_df, new_rows], ignore_index=True)

            # 4. 'No' තීරුව 1 සිට පිළිවෙළට නැවත සකස් කිරීම (Reset 'No' column sequentially)
            full_df = full_df.reset_index(drop=True)
            full_df["No"] = range(1, len(full_df) + 1)

            # අවසාන දත්ත Google Sheet එකට Overwrite කිරීම
            save_cols = ["No", "Manager", "Route", "Representative", "Status"]
            save_df = full_df[save_cols].copy()
            
            ws_master.clear()
            set_with_dataframe(ws_master, save_df)
            
            clear_sheet_cache()
            get_master_data.clear()
            
            st.success("✅ Master Data successfully updated!")
            time.sleep(2)
            st.rerun()

if __name__ == "__main__":
    show()