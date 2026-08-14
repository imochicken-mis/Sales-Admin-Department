import streamlit as st
import pandas as pd
import datetime
import time
import numpy as np
from sqlalchemy import create_engine, text

# 🚀 Cloud PostgreSQL (Neon.tech) Database Connection එක
@st.cache_resource
def get_db_engine():
    try:
        db_url = st.secrets["DATABASE_URL"]
        # SQLAlchemy නවතම සංස්කරණ සඳහා "postgres://" යන්න "postgresql://" ලෙස වෙනස් විය යුතුය
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
            
        # Connection Pooling සමගින් Engine එක සෑදීම
        engine = create_engine(db_url, pool_size=5, max_overflow=10)
        return engine
    except KeyError:
        st.error("⚠️ 'DATABASE_URL' not found in Streamlit secrets. Please configure your Neon.tech URL in .streamlit/secrets.toml")
        st.stop()
    except Exception as e:
        st.error(f"⚠️ Database connection error: {e}")
        st.stop()

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
        
        .table-wrapper table { width: 100% !important; margin: 0 !important; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='text-align: center; color: #03045E; font-weight: 800;'>📊 Outstanding Data Upload</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #0077B6; font-weight: 600;'>Upload outstanding CSV. Processed very fast and stored securely in Cloud SQL database.</p>", unsafe_allow_html=True)
    st.write("")

    # STREAMLIT CHUNK: Cloud SQL Helper Functions...
    def save_and_refresh(message, seconds=2):
        msg_placeholder = st.empty()
        msg_placeholder.success(message)
        time.sleep(seconds)
        msg_placeholder.empty()
        st.rerun()

    def get_rows_for_date(date_str):
        engine = get_db_engine()
        try:
            # 🚀 Cloud SQL මගින් දත්ත ලබා ගැනීම (Parameterized queries භාවිතයෙන් ආරක්ෂිතව)
            with engine.connect() as conn:
                query = text('SELECT * FROM outstanding WHERE "Selected_Date" = :date')
                df = pd.read_sql(query, conn, params={"date": date_str})
            return df
        except Exception:
            # මුල්ම වතාවේ Table එක හැදිලා නැත්නම් හිස් Dataframe එකක් ලබාදෙයි
            return pd.DataFrame()

    def delete_rows_for_date(date_str):
        engine = get_db_engine()
        try:
            # 🚀 Cloud SQL මගින් දත්ත මකා දැමීම
            with engine.begin() as conn:
                query = text('DELETE FROM outstanding WHERE "Selected_Date" = :date')
                conn.execute(query, {"date": date_str})
        except Exception as e:
            pass

    def section_banner(text):
        st.markdown(f'<div class="section-banner" style="background-color:#052b6c;color:white;padding:10px;border-radius:5px;font-weight:bold;">{text}</div>', unsafe_allow_html=True)

    def styled_table(df):
        if df.empty:
            return df
        
        styler = df.style.set_table_styles([
            {'selector': 'table', 'props': [('width', '100%'), ('border-collapse', 'collapse')]},
            {'selector': 'th', 'props': [('background-color', '#03045E'), ('color', 'white'), ('font-weight', 'bold'), ('text-align', 'center'), ('border', '1px solid #ADE8F4'), ('padding', '10px'), ('position', 'sticky'), ('top', '0'), ('z-index', '2')]},
            {'selector': 'td', 'props': [('border', '1px solid #ADE8F4'), ('padding', '8px'), ('text-align', 'center'), ('white-space', 'nowrap')]},
            {'selector': 'tr:nth-child(even)', 'props': [('background-color', '#F8FDFF')]},
            {'selector': 'tr:nth-child(odd)', 'props': [('background-color', '#FFFFFF')]}
        ])
        styler = styler.hide(axis="index")
        return styler

    # STREAMLIT CHUNK: Main UI and Date Picker...
    col1, col2, col3 = st.columns([1.8, 1, 3], vertical_alignment="bottom")
    with col1:
        selected_date = st.date_input("Select Upload Date:", value=datetime.date.today())
        selected_date_str = selected_date.strftime('%Y-%m-%d')
    st.divider()

    section_banner("📥 Upload Outstanding Data")

    existing_data = get_rows_for_date(selected_date_str)
    
    if not existing_data.empty:
        st.warning(f"⚠️ Outstanding data has already been uploaded for **{selected_date_str}**.")
        
        my_styled_table = styled_table(existing_data.head(10))
        table_html = '<div class="table-wrapper" style="max-height: 400px; overflow-y: auto; overflow-x: auto; border-radius: 8px; border: 2px solid #0096C7; background-color: white;">' + my_styled_table.to_html() + '</div>'
        st.markdown(table_html, unsafe_allow_html=True)
        st.caption(f"Showing preview of 10 rows. Total {len(existing_data)} records uploaded for this date.")
        st.write("") 

        if st.button("🗑️ Delete Data for this date", key="delete_out_btn"):
            st.session_state["confirm_delete_out"] = True

        if st.session_state.get("confirm_delete_out"):
            st.error(f"Permanently delete records uploaded for {selected_date_str} from the Cloud SQL database?")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown('<span class="delete-target"></span>', unsafe_allow_html=True)
                if st.button("✅ Yes, delete it"):
                    delete_rows_for_date(selected_date_str)
                    st.session_state["confirm_delete_out"] = False
                    save_and_refresh(f"🗑️ Data for {selected_date_str} deleted from Cloud Database.")
            with c2:
                st.markdown('<span class="cancel-target"></span>', unsafe_allow_html=True)
                if st.button("Cancel"):
                    st.session_state["confirm_delete_out"] = False
                    st.rerun()

    else:
        # STREAMLIT CHUNK: Data Dictionaries...
        exclude_list = [
            "INV0000002615", "R0000003551", "INV0000004279", "R0000003975", "I01-001128",
            "I01-002430", "R0000000412", "R0000000413", "INV0000002808", "R0000002625",
            "I06-003482", "R0000001109", "I13-001995", "R0000001588", "I13-001977",
            "I13-001975", "R0000001523", "INV0000000013", "R0000000007", "I12-001060",
            "R0000000141", "INV0000002325", "R0000002198", "INV0000018412", "R0000016974",
            "INV0000011362", "R0000010500", "I02-002862", "R0000000808", "INV0000005045",
            "R0000004726", "I09-003239", "R0000001363"
        ]

        rep_mapping = {
            "I04-003381": "Rajitha  Dikkumbura", "I04-003369": "Udaya Rathnayake", "I04-003156": "Rajitha  Dikkumbura",
            "I04-003336": "Rajitha  Dikkumbura", "I04-003466": "Rajitha  Dikkumbura", "ICTN-000768": "Asela Munasinghe Rep",
            "ICTN-000770": "Asela Munasinghe Rep", "ICTN-000769": "Asela Munasinghe Rep", "CRTN-000095": "Asela Munasinghe Rep",
            "CRTN-000114": "Asela Munasinghe Rep", "CRTN-000295_803451": "Asela Munasinghe Rep", "I01-001128": "Asela Munasinghe Rep",
            "I01-002430": "Asela Munasinghe Rep", "I11-001583": "Anura Anura", "I11-001702": "Anura Anura",
            "I11-002718": "Anura Anura", "I11-003075": "Ranjith Fernando", "ICIN-022935": "Dealer",
            "I11-002866": "Anura Anura", "I11-002892": "Anura Anura", "I11-003023": "Anura Anura",
            "I06-00202": "Infaz M", "I06-003482": "Infaz M", "I06-003417": "Infaz M",
            "I03-003646": "Bandara Vishwa sales rep", "ICIN-022986": "Dealer", "ICIN-023005": "Dealer",
            "ICIN-004491": "Dealer", "ICIN-005071": "Dealer", "ICIN-006532": "Dealer",
            "ICIN-008617": "Dealer", "ICIN-008629": "Dealer", "ICIN-009007": "Dealer",
            "ICIN-009635": "Dealer", "ICIN-012036": "Dealer", "ICIN-013028": "Dealer",
            "ICIN-014153": "Dealer", "ICIN-016235": "Dealer", "ICIN-016236": "Dealer",
            "ICIN-016846": "Dealer", "ICOB-000313": "Chirantha Madumadawa", "ICOB-001155": "Chirantha Madumadawa",
            "ICOB-001150": "Chirantha Madumadawa", "ICIN-000104": "Chirantha Madumadawa", "ICOB-001144": "Chirantha Madumadawa",
            "I13-001995": "Chirantha Madumadawa", "I13-002049": "Chirantha Madumadawa", "CRTN-000181": "Chirantha Madumadawa",
            "ICTN-000841": "Chirantha Madumadawa", "CRTN-000211": "Chirantha Madumadawa", "I13-001977": "Chirantha Madumadawa",
            "I13-001975": "Chirantha Madumadawa", "I13-001515": "Chirantha Madumadawa", "I13-001677": "Chirantha Madumadawa",
            "I13-001895": "Chirantha Madumadawa", "I13-002051": "Chirantha Madumadawa", "I13-001834": "Chirantha Madumadawa",
            "I13-001990": "Chirantha Madumadawa", "I13-002027": "Chirantha Madumadawa", "I07-001479": "Sudath Kumara",
            "I07-001639": "Sudath Kumara", "I13-001787": "Chirantha Madumadawa", "I07-001283": "Sudath Kumara",
            "I07-001314": "Sudath Kumara", "I07-001354": "Sudath Kumara", "I07-002600": "Sudath Kumara",
            "INV0000036252": "Sudath Kumara", "I13-001780": "Chirantha Madumadawa", "I13-001972": "Chirantha Madumadawa",
            "ICOB-001192": "Chirantha Madumadawa", "I13-001840": "Chirantha Madumadawa", "I07-002062": "Sudath Kumara",
            "I07-002300": "Sudath Kumara", "I07-002740": "Sudath Kumara", "I13-001994": "Chirantha Madumadawa",
            "ICOB-000828": "Sudath Kumara", "I07-002835": "Sudath Kumara", "I13-002064": "Chirantha Madumadawa",
            "I08-002256": "Gayan Madhushanka", "I08-002370": "Gayan Madhushanka", "I08-002473": "Gayan Madhushanka",
            "I08-002376": "Gayan Madhushanka", "I08-002185": "Gayan Madhushanka", "I13-001832": "Chirantha Madumadawa",
            "I08-002104": "Gayan Madhushanka", "I08-002137": "Gayan Madhushanka", "I08-002236": "Gayan Madhushanka",
            "I08-002360": "Gayan Madhushanka", "I08-002168": "Gayan Madhushanka", "I08-002193": "Gayan Madhushanka",
            "I08-002198": "Gayan Madhushanka", "I08-002207": "Gayan Madhushanka", "I08-002218": "Gayan Madhushanka",
            "I08-002225": "Gayan Madhushanka", "I08-002242": "Gayan Madhushanka", "I08-002253": "Gayan Madhushanka",
            "I08-002263": "Gayan Madhushanka", "I08-002280": "Gayan Madhushanka", "I07-002367": "Sudath Kumara",
            "I07-002533": "Sudath Kumara", "I08-002432": "Gayan Madhushanka", "I08-002063": "Gayan Madhushanka",
            "I08-002316": "Gayan Madhushanka", "I08-002351": "Gayan Madhushanka", "I08-002155": "Gayan Madhushanka",
            "I08-002014": "Gayan Madhushanka", "I08-002466": "Gayan Madhushanka", "ICIN-022444": "Sudath Kumara",
            "ICIN-022445": "Sudath Kumara", "I08-002374": "Gayan Madhushanka", "I08-002349": "Gayan Madhushanka",
            "I08-002118": "Gayan Madhushanka", "I08-002227": "Gayan Madhushanka", "I08-002162": "Gayan Madhushanka",
            "I08-002195": "Gayan Madhushanka", "I08-002255": "Gayan Madhushanka", "I14-002417": "Niroshan Kumara",
            "I14-002019": "Niroshan Kumara", "I14-002265": "Niroshan Kumara", "I14-001120": "Niroshan Kumara",
            "ICIN-017497": "Niroshan Kumara", "I14-002286": "Niroshan Kumara", "I14-002409": "Niroshan Kumara",
            "I14-002293": "Niroshan Kumara", "I12-001060": "Pasindu Dananjaya Rep", "I12-001072": "Pasindu Dananjaya Rep",
            "I12-001089": "Pasindu Dananjaya Rep", "I12-001103": "Pasindu Dananjaya Rep", "I12-001068": "Pasindu Dananjaya Rep",
            "I12-001004": "Pasindu Dananjaya Rep", "I12-000877": "Pasindu Dananjaya Rep", "ICOB-001035": "Pasindu Dananjaya Rep",
            "ICOB-001038": "Pasindu Dananjaya Rep", "ICOB-001037": "Pasindu Dananjaya Rep", "ICIN-000379": "Pasindu Dananjaya Rep",
            "ICIN-000392": "Pasindu Dananjaya Rep", "ICIN-000394": "Pasindu Dananjaya Rep", "ICIN-000718": "Pasindu Dananjaya Rep",
            "ICIN-001130": "Pasindu Dananjaya Rep", "ICIN-001131": "Pasindu Dananjaya Rep", "ICIN-001399": "Pasindu Dananjaya Rep",
            "ICIN-003233": "Pasindu Dananjaya Rep", "ICIN-002118": "Pasindu Dananjaya Rep", "ICIN-002117": "Pasindu Dananjaya Rep",
            "ICIN-002343": "Pasindu Dananjaya Rep", "ICIN-003167": "Pasindu Dananjaya Rep", "CRTN-000264": "Pasindu Dananjaya Rep",
            "I12-001034": "Pasindu Dananjaya Rep", "I12-001052": "Pasindu Dananjaya Rep", "I12-001069": "Pasindu Dananjaya Rep",
            "I12-001075": "Pasindu Dananjaya Rep", "I21-002485": "Sahan Sandaruwan sales rep", "I21-002508": "Sahan Sandaruwan sales rep",
            "I21-002607": "Sahan Sandaruwan sales rep", "I21-002462": "Sahan Sandaruwan sales rep", "I21-002495": "Sahan Sandaruwan sales rep",
            "I21-002597": "Sahan Sandaruwan sales rep", "I21-002392": "Sahan Sandaruwan sales rep", "I21-002393": "Sahan Sandaruwan sales rep",
            "CRTN-000249": "Sahan Sandaruwan sales rep", "Rtn Chq No:104481 -30/01/2026)": "Sahan Sandaruwan sales rep",
            "I21-002505": "Sahan Sandaruwan sales rep", "I21-002553": "Sahan Sandaruwan sales rep", "I21-002630": "Sahan Sandaruwan sales rep",
            "I21-002486": "Sahan Sandaruwan sales rep", "I21-002663": "Sahan Sandaruwan sales rep", "I21-002618": "Sahan Sandaruwan sales rep",
            "I21-002185": "Sahan Sandaruwan sales rep", "I21-002671": "Sahan Sandaruwan sales rep", "I21-002564": "Sahan Sandaruwan sales rep",
            "I21-002666": "Sahan Sandaruwan sales rep", "I21-002141": "Sahan Sandaruwan sales rep", "I05-001869": "Rumesh Mirinnege sales rep",
            "I05-002008": "Rumesh Mirinnege sales rep", "I05-001791": "Rumesh Mirinnege sales rep", "I05-001878": "Rumesh Mirinnege sales rep",
            "I05-001909": "Rumesh Mirinnege sales rep", "I05-002006": "Rumesh Mirinnege sales rep", "I05-002020": "Rumesh Mirinnege sales rep",
            "I05-001834": "Rumesh Mirinnege sales rep", "I05-001978": "Rumesh Mirinnege sales rep", "I05-002054": "Rumesh Mirinnege sales rep",
            "I05-001942": "Rumesh Mirinnege sales rep", "I05-001912": "Rumesh Mirinnege sales rep", "I05-001486": "Rumesh Mirinnege sales rep",
            "CRTN-000271": "Rumesh Mirinnege sales rep", "CRTN-000275": "Rumesh Mirinnege sales rep", "I05-002109": "Rumesh Mirinnege sales rep",
            "I05-001955": "Rumesh Mirinnege sales rep", "I05-002033": "Rumesh Mirinnege sales rep", "I05-002102": "Rumesh Mirinnege sales rep",
            "I05-001839": "Rumesh Mirinnege sales rep", "I05-001950": "Rumesh Mirinnege sales rep", "I05-001935": "Rumesh Mirinnege sales rep",
            "I05-001892": "Rumesh Mirinnege sales rep", "I05-001749": "Rumesh Mirinnege sales rep", "I05-002030": "Rumesh Mirinnege sales rep",
            "I05-001906": "Rumesh Mirinnege sales rep", "I05-001708": "Rumesh Mirinnege sales rep", "I05-001908": "Rumesh Mirinnege sales rep",
            "I05-002003": "Rumesh Mirinnege sales rep", "I05-002089": "Rumesh Mirinnege sales rep", "I05-002127": "Rumesh Mirinnege sales rep",
            "I05-001875": "Rumesh Mirinnege sales rep", "I05-002136": "Rumesh Mirinnege sales rep", "I21-002500": "Sahan Sandaruwan sales rep",
            "I21-002227": "Sahan Sandaruwan sales rep", "I05-001963": "Rumesh Mirinnege sales rep", "I05-002045": "Rumesh Mirinnege sales rep",
            "I05-001775": "Rumesh Mirinnege sales rep", "ICIN-005501": "Nadeej  Liyanage", "I17-002793": "Suraj Jayawardana",
            "I17-003093": "Suraj Jayawardana", "CRTN-000232": "Suraj Jayawardana", "CRTN-000178": "Suraj Jayawardana",
            "INV0000008084": "Nisham Jothirathne", "I02-002869": "Dinuka (MH) Sales Rep", "I02-002870": "Dinuka (MH) Sales Rep",
            "I02-002862": "Dinuka (MH) Sales Rep", "I13-001116": "Chirantha Madumadawa", "I13-001744": "Chirantha Madumadawa",
            "I13-001823": "Chirantha Madumadawa", "I13-001882": "Chirantha Madumadawa", "I03-002829": "Bandara Vishwa sales rep",
            "I03-003385": "Bandara Vishwa sales rep", "I03-003255": "Bandara Vishwa sales rep", "I03-003598": "Bandara Vishwa sales rep",
            "I03-003159": "Bandara Vishwa sales rep", "I03-003676": "Bandara Vishwa sales rep", "I03-003197": "Bandara Vishwa sales rep",
            "I03-003671": "Bandara Vishwa sales rep", "I03-003365": "Bandara Vishwa sales rep", "I03-003292": "Bandara Vishwa sales rep",
            "I03-003522": "Bandara Vishwa sales rep", "I03-003689": "Bandara Vishwa sales rep", "I03-003701": "Bandara Vishwa sales rep",
            "I03-003299": "Bandara Vishwa sales rep", "I03-003515": "Bandara Vishwa sales rep", "I03-003222": "Bandara Vishwa sales rep",
            "I03-003666": "Bandara Vishwa sales rep", "I03-003623": "Bandara Vishwa sales rep", "I03-003693": "Bandara Vishwa sales rep",
            "I03-003544": "Bandara Vishwa sales rep", "I03-003237": "Bandara Vishwa sales rep", "I03-003305": "Bandara Vishwa sales rep",
            "I03-003371": "Bandara Vishwa sales rep", "I03-003441": "Bandara Vishwa sales rep", "I03-003519": "Bandara Vishwa sales rep",
            "I03-003364": "Bandara Vishwa sales rep", "I03-003373": "Bandara Vishwa sales rep", "I03-003402": "Bandara Vishwa sales rep",
            "I09-003081": "Dilshan Sampath sales rep", "I09-002932": "Dilshan Sampath sales rep", "I09-003239": "Dilshan Sampath sales rep",
            "I20-000639": "Chirantha Madumadawa", "I13-001936": "Chirantha Madumadawa", "I13-002009": "Chirantha Madumadawa",
            "I13-002054": "Chirantha Madumadawa", "I13-001906": "Chirantha Madumadawa", "I13-001368": "Chirantha Madumadawa",
            "CRTN-000204": "Chirantha Madumadawa", "I13-002002": "Chirantha Madumadawa", "I13-001914": "Chirantha Madumadawa",
            "I13-001903": "Chirantha Madumadawa", "I13-001937": "Chirantha Madumadawa", "I13-001935": "Chirantha Madumadawa",
            "I13-002046": "Chirantha Madumadawa", "I13-001844": "Chirantha Madumadawa", "I13-001870": "Chirantha Madumadawa"
        }

        # STREAMLIT CHUNK: Processing uploaded CSV...
        st.info("Upload CSV File. System will automatically remove excluded invoices and map exact Rep names.")
        
        uploaded_file = st.file_uploader("Upload CSV File", type=["csv"], key="outstanding_upload")
        
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                
                if "Document No" not in df.columns or "Rep" not in df.columns:
                    st.error("⚠️ Invalid CSV Format. Ensure 'Document No' and 'Rep' columns exist.")
                else:
                    if st.button("Process & Submit to Database", type="primary"):
                        with st.spinner("Filtering and Mapping Data..."):
                            
                            # 1. Clean the 'Document No' column for exact matching
                            df["Document No"] = df["Document No"].astype(str).str.strip()
                            
                            # 2. Filter OUT the excluded invoices
                            original_count = len(df)
                            df = df[~df["Document No"].isin(exclude_list)]
                            filtered_count = len(df)
                            removed_count = original_count - filtered_count
                            
                            # 🚀 3. High-Performance Vectorized Rep Mapping (Cloud SQL සමග)
                            mapped_reps = df["Document No"].map(rep_mapping)
                            df["Rep"] = np.where(mapped_reps.notna(), mapped_reps, df["Rep"])
                            
                            # Add identifier Date column
                            df.insert(0, "Selected_Date", selected_date_str)
                            df = df.fillna("")

                            # 🚀 4. Save directly to Cloud SQL Database (Neon.tech)
                            engine = get_db_engine()
                            with engine.begin() as conn:
                                df.to_sql("outstanding", conn, if_exists="append", index=False)
                            
                        save_and_refresh(f"✅ Success! Uploaded {filtered_count} records to Cloud SQL. (Removed {removed_count} excluded invoices).")

            except Exception as e:
                st.error(f"Error processing file: {e}")

if __name__ == "__main__":
    show()