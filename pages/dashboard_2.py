import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder
from datetime import datetime
import json
import time

try:
    from util import connect_to_sheets
except ImportError:
    st.error("Error: Could not import connection functions from util.py")

# ==========================================
# 🎨 CUSTOM CSS & THEME CONFIGURATION
# ==========================================
def apply_custom_css():
    st.markdown("""
        <style>
        /* Color Palette Variables */
        :root {
            --c-900: #03045E;
            --c-800: #023E8A;
            --c-700: #0077B6;
            --c-600: #0096C7;
            --c-500: #00B4D8;
            --c-400: #48CAE4;
            --c-300: #90E0EF;
            --c-200: #ADE8F4;
            --c-100: #CAF0F8;
        }

        /* App Background */
        .stApp {
            background: linear-gradient(135deg, var(--c-100) 0%, #FFFFFF 100%);
            color: var(--c-900);
        }

        /* Hide Header background */
        [data-testid="stHeader"] {
            background: transparent !important;
        }

        /* Page spacing and overflow fixes */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            max-width: 98% !important;
            overflow-x: hidden !important;
            min-height: 85vh !important;
        }

        /* 🚀 Date Input සහ Selectbox සඳහා නිල් පාට Border එක (Blue Border Fix) */
        div[data-testid="stDateInput"] label p, div[data-testid="stSelectbox"] label p {
            font-family: 'Arial', sans-serif !important;
            font-weight: 800 !important;
            font-size: 15px !important;
            color: #03045E !important;
        }
        
        div[data-testid="stDateInput"] div[data-baseweb="input"], 
        div[data-testid="stSelectbox"] div[data-baseweb="select"] {
            border: 2px solid #0096C7 !important; /* light blue border */
            border-radius: 8px !important;        /* boarder radious */
            background-color: #F8FDFF !important; /* white bg */
            transition: all 0.3s ease-in-out;
            padding-left: 5px;
        }

        /* Click කළ විට (Focus වෙද්දී) තද නිල් පාට වීම */
        div[data-testid="stDateInput"] div[data-baseweb="input"]:focus-within, 
        div[data-testid="stSelectbox"] div[data-baseweb="select"]:focus-within {
            border: 2px solid #03045E !important;
            box-shadow: 0 0 8px rgba(3, 4, 94, 0.4) !important;
        }

        /* 🚀 MASTER FIX: Complete Scrollbar Removal for Charts */
        [data-testid="stPlotlyChart"] {
            box-sizing: border-box !important;
            overflow: hidden !important;
        }
        [data-testid="stPlotlyChart"] > div, 
        [data-testid="stPlotlyChart"] iframe {
            overflow: hidden !important;
            box-sizing: border-box !important;
        }
        /* Completely hide scrollbars in all inner elements */
        [data-testid="stPlotlyChart"] *::-webkit-scrollbar {
            display: none !important;
            width: 0 !important;
            height: 0 !important;
        }
        [data-testid="stPlotlyChart"] * {
            scrollbar-width: none !important;
            -ms-overflow-style: none !important;
        }

        /* 🚀 CHART ANIMATION (Fade-in & Slide-up only) */
        @keyframes slideUpFade {
            0% { opacity: 0; transform: translateY(40px); }
            100% { opacity: 1; transform: translateY(0); }
        }
        
        /* Chart & Table Card Styling */
        [data-testid="stPlotlyChart"], iframe, [data-testid="stHtml"], .stDataFrame {
            background-color: rgba(255, 255, 255, 0.85) !important;
            border-radius: 12px !important;
            box-shadow: 0 8px 24px rgba(2, 62, 138, 0.08) !important;
            border: 1px solid var(--c-200) !important;
            padding: 10px !important;
            margin-bottom: 1rem !important;
            animation: slideUpFade 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards;
            backdrop-filter: blur(10px);
            display: block;
            width: 100%;
            box-sizing: border-box !important; /* 🚀 Added to fix scroll */
            overflow: hidden !important; /* 🚀 Added to fix scroll */
        }

        /* KPI Cards */
        .kpi-container {
            display: flex;
            gap: 1.5rem;
            margin-bottom: 1.5rem;
            flex-wrap: wrap;
        }
        .kpi-card {
            flex: 1;
            min-width: 200px;
            background: rgba(255, 255, 255, 0.9);
            padding: 1.5rem;
            border-radius: 16px;
            box-shadow: 0 10px 30px rgba(3, 4, 94, 0.06);
            border-left: 1px solid var(--c-200);
            border-right: 1px solid var(--c-200);
            border-bottom: 1px solid var(--c-200);
            position: relative;
            overflow: hidden;
            transition: transform 0.3s ease;
        }
        .kpi-card:hover {
            transform: translateY(-5px);
        }
        .kpi-card::before {
            content: "";
            position: absolute;
            top: -50px;
            right: -50px;
            width: 100px;
            height: 100px;
            background: var(--c-100);
            border-radius: 50%;
            opacity: 0.5;
            z-index: 0;
        }
        .kpi-title {
            color: var(--c-800);
            font-size: 0.90rem;
            font-weight: 700;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
            letter-spacing: 0.5px;
            z-index: 1;
            position: relative;
        }
        .kpi-value {
            color: var(--c-900);
            font-size: 2.2rem;
            font-weight: 800;
            z-index: 1;
            position: relative;
        }
        .kpi-sub {
            font-size: 0.85rem;
            margin-top: 0.25rem;
            font-weight: 600;
            z-index: 1;
            position: relative;
        }
        </style>
    """, unsafe_allow_html=True)

# Common Layout function for Plotly Charts
def apply_plotly_layout(fig, title=""):
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=18, color="#03045E"), x=0.02, y=0.95),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_family="'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
        font_color="#023E8A",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        dragmode=False,
        margin=dict(t=60, b=40, l=15, r=15)
    )
    fig.update_xaxes(showgrid=False, linecolor="#ADE8F4", tickfont=dict(color="#023E8A"), fixedrange=True)
    fig.update_yaxes(showgrid=True, gridcolor="#CAF0F8", linecolor="#ADE8F4", tickfont=dict(color="#023E8A"), fixedrange=True)
    return fig

plotly_config = {'displayModeBar': False, 'displaylogo': False, 'staticPlot': False, 'responsive': True}

# ==========================================
# 🚀 INTERACTIVE CHART ANIMATION COMPONENT
# ==========================================
def render_animated_chart(fig, height, animation_kind="default"):
    """Render a Plotly chart without scrollbars, animate smoothly, and replay on click."""
    def as_list(values):
        return [] if values is None else list(values)

    target = json.loads(fig.to_json())

    for index, trace in enumerate(target.get("data", [])):
        source_trace = fig.data[index]
        for axis in ("x", "y", "values"):
            source_values = getattr(source_trace, axis, None)
            if source_values is not None:
                trace[axis] = as_list(source_values)

    initial = json.loads(json.dumps(target, cls=PlotlyJSONEncoder))

    for index, trace in enumerate(initial.get("data", [])):
        source_trace = fig.data[index]
        trace_type = trace.get("type")
        
        if trace_type == "indicator":
            trace["value"] = 0
        elif trace_type == "pie":
            trace["opacity"] = 0
            trace["rotation"] = -90
        elif trace_type == "bar":
            value_axis = "x" if trace.get("orientation") == "h" else "y"
            values = as_list(getattr(source_trace, value_axis, None))
            trace[value_axis] = [0] * len(values)
        elif trace_type == "scatter":
            if animation_kind == "line":
                values = as_list(getattr(source_trace, "y", None))
                if values:
                    trace["y"] = [values[0]] + [None] * (len(values) - 1)
            elif "y" in trace:
                values = as_list(getattr(source_trace, "y", None))
                trace["y"] = [0] * len(values)

    chart_html = f"""
    <style>
        html, body {{ margin: 0; padding: 0; overflow: hidden; background: transparent; cursor: pointer; }}
        #animated-chart {{ 
            width: 100%; height: {height}px; overflow: hidden; 
            transition: transform 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
            border-radius: 12px;
        }}
        .chart-clicked {{
            transform: scale(0.98);
            box-shadow: 0px 0px 20px rgba(0, 150, 199, 0.4) inset;
        }}
    </style>
    <div id="animated-chart"></div>
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
    <script>
        const chart = document.getElementById("animated-chart");
        const initialRaw = {json.dumps(initial, cls=PlotlyJSONEncoder)};
        const targetRaw = {json.dumps(target, cls=PlotlyJSONEncoder)};
        const config = {json.dumps(plotly_config)};
        let animTimer = null;

        function playAnimation() {{
            if (animTimer) clearInterval(animTimer);
            const initialData = JSON.parse(JSON.stringify(initialRaw.data));
            Plotly.react(chart, initialData, initialRaw.layout, config).then(() => {{
                const steps = 30;
                let currentStep = 0;
                animTimer = setInterval(() => {{
                    currentStep += 1;
                    const progress = currentStep / steps;
                    const ease = 1 - Math.pow(1 - progress, 3); 

                    const frameData = JSON.parse(JSON.stringify(targetRaw.data)).map(trace => {{
                        if (trace.type === "pie") {{
                            trace.opacity = ease; 
                            trace.rotation = (trace.rotation || 0) - 90 * (1 - ease); 
                        }} else if (trace.type === "indicator") {{
                            trace.value = trace.value * ease;
                        }} else if (trace.type === "bar") {{
                            const axis = trace.orientation === "h" ? "x" : "y";
                            trace[axis] = trace[axis].map(v => v * ease);
                        }} else if (trace.type === "scatter") {{
                            if ("{animation_kind}" === "line") {{
                                const totalPoints = trace.x ? trace.x.length : 1;
                                const pointCount = Math.max(1, Math.ceil(totalPoints * progress));
                                trace.y = trace.y.map((v, i) => i < pointCount ? v : null);
                            }} else {{
                                trace.y = trace.y.map(v => v * ease);
                            }}
                        }}
                        return trace;
                    }});

                    Plotly.react(chart, frameData, targetRaw.layout, config);

                    if (currentStep >= steps) {{
                        clearInterval(animTimer);
                        Plotly.react(chart, JSON.parse(JSON.stringify(targetRaw.data)), targetRaw.layout, config);
                    }}
                }}, 35);
            }});
        }}

        Plotly.newPlot(chart, JSON.parse(JSON.stringify(initialRaw.data)), initialRaw.layout, config).then(() => {{
            playAnimation();
        }});

        document.body.addEventListener("click", () => {{
            chart.classList.add("chart-clicked");
            setTimeout(() => {{ chart.classList.remove("chart-clicked"); }}, 150);
            playAnimation();
        }});
    </script>
    """
    components.html(chart_html, height=height, scrolling=False)

# ==========================================
# 🚀 KPI CARDS ANIMATION (0 සිට වැඩිවීම)
# ==========================================
def render_kpi_cards(total_cash, total_deposit, variance, avg_delay, collection_efficiency):
    placeholder = st.empty()
    steps = 15
    var_color = "#146c2e" if variance <= 0 else "#D90429"
    
    for step in range(steps + 1):
        progress = step / steps
        ease = 1 - pow(1 - progress, 3) # Smooth easing
        
        placeholder.markdown(f"""
            <div class="kpi-container">
                <div class="kpi-card" style="border-top: 5px solid #03045E;">
                    <div class="kpi-title">💵 Total Cash Collected</div>
                    <div class="kpi-value">Rs {total_cash * ease:,.0f}</div>
                    <div class="kpi-sub" style="color: #0077B6;">Total Cash Inflow</div>
                </div>
                <div class="kpi-card" style="border-top: 5px solid #0077B6;">
                    <div class="kpi-title">🏦 Total Deposit (Bank + H/O)</div>
                    <div class="kpi-value">Rs {total_deposit * ease:,.0f}</div>
                    <div class="kpi-sub" style="color: #0096C7;">Efficiency: {collection_efficiency * ease:.1f}%</div>
                </div>
                <div class="kpi-card" style="border-top: 5px solid #00B4D8;">
                    <div class="kpi-title">⚖️ Variance (Balance)</div>
                    <div class="kpi-value"><span style="color: {var_color};">Rs {variance * ease:,.0f}</span></div>
                    <div class="kpi-sub" style="color: {var_color};">Pending to be Settled</div>
                </div>
                <div class="kpi-card" style="border-top: 5px solid #48CAE4;">
                    <div class="kpi-title">⏱️ Average Deposit Delay</div>
                    <div class="kpi-value">{avg_delay * ease:.1f} Days</div>
                    <div class="kpi-sub" style="color: #0077B6;">Speed of Cash Flow</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        if step < steps:
            time.sleep(0.03)

@st.cache_data(ttl=300, show_spinner=False)
def load_data():
    try:
        sh = connect_to_sheets()
        ws = sh.worksheet("Cash_Collection")
        df = pd.DataFrame(ws.get_all_records(default_blank=""))
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

def show():
    apply_custom_css()
    st.markdown("<h2 style='text-align: center; color: #03045E; font-weight: 800;'>💵 Cash Collection Dashboard</h2>", unsafe_allow_html=True)
    
    with st.spinner("Loading Dashboard Analytics..."):
        df = load_data()

    if df.empty:
        st.info("No Cash Collection data available to build the dashboard.")
        return

    # Clean Numeric and Date Columns Safely
    date_col = "Date" if "Date" in df.columns else "new_date"
    df["Parsed_Date"] = pd.to_datetime(df[date_col], errors='coerce')
    df["Parsed_Dep_Date"] = pd.to_datetime(df["Deposit Date"], errors='coerce')
    
    # 🚀 Dynamic Column Naming Fix (To prevent KeyError)
    tot_col_name = next((col for col in df.columns if "Total Cash Colle" in col), "Total Cash Collection")
    
    for col in [tot_col_name, "Amount"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '', regex=False).replace(r'^\s*-\s*$', '0', regex=True)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # STREAMLIT CHUNK: Render Date and Rep Filters...
    today = datetime.now()
    first_day = today.replace(day=1)
    min_db_date = df["Parsed_Date"].min() if not df["Parsed_Date"].isna().all() else first_day
    
    col1, col2, col3 = st.columns([1, 1, 1], vertical_alignment="bottom")
    with col1:
        start_date = st.date_input("Start Date:", value=first_day)
    with col2:
        end_date = st.date_input("End Date:", value=today)
    with col3:
        routes = ["All"] + sorted([str(r) for r in df["Route"].dropna().unique() if str(r).strip() != ""])
        selected_rep = st.selectbox("Filter by Sales Rep:", routes)

    st.divider()

    if start_date > end_date:
        st.error("Start Date cannot be after End Date.")
        return

    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)
    
    # 🚀 1. Check for valid dates and show latest snapshot info
    valid_dates = df[df["Parsed_Date"].dt.date <= end_date]["Parsed_Date"]
    
    if valid_dates.empty:
        st.warning(f"No collection records found on or before {end_date.strftime('%Y-%m-%d')}.")
        return
        
    latest_date = valid_dates.max()
    if latest_date.date() != end_date:
        st.info(f"💡 Showing latest snapshot up to **{latest_date.strftime('%Y-%m-%d')}**")

    # Date Filtered Data
    df_date_filtered = df[(df["Parsed_Date"] >= start_ts) & (df["Parsed_Date"] <= end_ts)].copy()
    
    # Rep Filtered Data
    if selected_rep != "All":
        df_filtered = df_date_filtered[df_date_filtered["Route"].astype(str).str.contains(selected_rep, case=False, na=False, regex=False)].copy()
    else:
        df_filtered = df_date_filtered.copy()

    if df_filtered.empty:
        st.warning("No data found for the selected filters.")
        return

    # STREAMLIT CHUNK: KPI Calculations...
    total_cash_collected = df_filtered[tot_col_name].sum() if tot_col_name in df_filtered.columns else 0
    total_deposit = df_filtered["Amount"].sum()
    
    # 🚀 ACCURATE BANK vs H/O DEPOSIT CALCULATION (Fix for 0 H/O Amount)
    # Check both 'Status' and 'Type' columns to be 100% sure
    is_ho = (df_filtered.get("Status", pd.Series("")).astype(str).str.strip().str.upper() == "H/O") | \
            (df_filtered.get("Type", pd.Series("")).astype(str).str.strip().str.upper() == "H/O") | \
            (df_filtered.get("Status", pd.Series("")).astype(str).str.strip().str.upper() == "CASH") | \
            (df_filtered.get("Type", pd.Series("")).astype(str).str.strip().str.upper() == "CASH")
    
    ho_deposit = df_filtered.loc[is_ho, "Amount"].sum()
    bank_deposit = total_deposit - ho_deposit # Fail-proof matching
    
    variance = total_cash_collected - total_deposit
    collection_efficiency = (total_deposit / total_cash_collected * 100) if total_cash_collected > 0 else 0
    
    df_filtered["Delay_Days"] = (df_filtered["Parsed_Dep_Date"] - df_filtered["Parsed_Date"]).dt.days
    valid_delays = df_filtered[df_filtered["Amount"] > 0]["Delay_Days"].dropna()
    avg_delay = valid_delays.mean() if not valid_delays.empty else 0

    # 🚀 KPI CARDS (Animate from 0)
    render_kpi_cards(total_cash_collected, total_deposit, variance, avg_delay, collection_efficiency)

    # STREAMLIT CHUNK: Radial Charts & Summary Chart...
    r1c1, r1c2 = st.columns(2)
    
    with r1c1:
        # --- 3 RADIAL CHARTS (Replacing Funnel) ---
        valid_deposits = df_filtered[df_filtered["Amount"] > 0].copy()
        total_dep_amt = valid_deposits["Amount"].sum()
        
        day_1 = valid_deposits[valid_deposits["Delay_Days"] <= 1]["Amount"].sum()
        day_2 = valid_deposits[valid_deposits["Delay_Days"] == 2]["Amount"].sum()
        day_3_plus = valid_deposits[valid_deposits["Delay_Days"] >= 3]["Amount"].sum()
        
        pct_1 = (day_1 / total_dep_amt * 100) if total_dep_amt > 0 else 0
        pct_2 = (day_2 / total_dep_amt * 100) if total_dep_amt > 0 else 0
        pct_3 = (day_3_plus / total_dep_amt * 100) if total_dep_amt > 0 else 0

        fig_radial = go.Figure()

        # 1. Fast Deposit (≤ 1 Day)
        fig_radial.add_trace(go.Indicator(
            mode="gauge+number",
            value=pct_1,
            number={'suffix': "%", 'font': {'size': 26, 'color': '#03045E', 'family': 'Arial Black'}},
            title={'text': "Within 1 Day<br><span style='font-size:12px;color:#00B4D8'>Rs {:,.0f}</span>".format(day_1), 'font': {'size': 14}},
            gauge={
                'axis': {'range': [None, 100], 'visible': False},
                'bar': {'color': "#00B4D8", 'thickness': 0.75}, 
                'bgcolor': "#EAF8FF",
                'shape': "angular"
            },
            domain={'x': [0, 0.30], 'y': [0, 1]}
        ))

        # 2. Moderate (1 to 2 Days)
        fig_radial.add_trace(go.Indicator(
            mode="gauge+number",
            value=pct_2,
            number={'suffix': "%", 'font': {'size': 26, 'color': '#03045E', 'family': 'Arial Black'}},
            title={'text': "1 to 2 Days<br><span style='font-size:12px;color:#FFC100'>Rs {:,.0f}</span>".format(day_2), 'font': {'size': 14}},
            gauge={
                'axis': {'range': [None, 100], 'visible': False},
                'bar': {'color': "#FFC100", 'thickness': 0.75}, 
                'bgcolor': "#FFF8E1",
                'shape': "angular"
            },
            domain={'x': [0.35, 0.65], 'y': [0, 1]}
        ))

        # 3. Delayed (3+ Days)
        fig_radial.add_trace(go.Indicator(
            mode="gauge+number",
            value=pct_3,
            number={'suffix': "%", 'font': {'size': 26, 'color': '#03045E', 'family': 'Arial Black'}},
            title={'text': "On or After 3 Days<br><span style='font-size:12px;color:#D90429'>Rs {:,.0f}</span>".format(day_3_plus), 'font': {'size': 14}},
            gauge={
                'axis': {'range': [None, 100], 'visible': False},
                'bar': {'color': "#D90429", 'thickness': 0.75}, 
                'bgcolor': "#FFEAED",
                'shape': "angular"
            },
            domain={'x': [0.70, 1.0], 'y': [0, 1]}
        ))

        fig_radial = apply_plotly_layout(fig_radial, "🔻 Cash Deposit Timeframe (Efficiency)")
        fig_radial.update_layout(height=400, margin=dict(t=70, b=20, l=10, r=10))
        
        # 🚀 Interactive Animation Render
        render_animated_chart(fig_radial, height=400)

    with r1c2:
        # --- Summary Column Chart ---
        summary_labels = ['Total Cash Collected', 'Bank Deposit', 'H/O Deposit', 'Variance']
        summary_values = [total_cash_collected, bank_deposit, ho_deposit, variance]
        summary_colors = ['#03045E', '#0077B6', '#00B4D8', '#D90429' if variance > 0 else '#146c2e']
        
        fig_summary = go.Figure(data=[
            go.Bar(
                x=summary_labels, 
                y=summary_values,
                text=[f"Rs {v:,.0f}" for v in summary_values],
                textposition='outside',
                marker_color=summary_colors,
                marker_line_color='#023E8A',
                marker_line_width=1,
                opacity=0.9,
                textfont=dict(size=12, family="Arial Black", color="#03045E")
            )
        ])
        
        fig_summary = apply_plotly_layout(fig_summary, "Overall Financial Summary")
        # 🚀 l=20 වෙනුවට l=60 ලබා දී වම්පස ඉඩ වැඩි කර ඇත
        fig_summary.update_layout(height=400, margin=dict(t=60, b=30, l=60, r=20), yaxis=dict(title="Amount (Rs)"))
        st.plotly_chart(fig_summary, use_container_width=True, config=plotly_config)

    # STREAMLIT CHUNK: Rep Wise Comparison Chart...
    # This chart always shows ALL reps (ignores the selectbox filter)
    if not df_date_filtered.empty:
        rep_collections = df_date_filtered.groupby('Route')[tot_col_name].sum().reset_index()
        rep_deposits = df_date_filtered.groupby('Route')['Amount'].sum().reset_index()
        
        rep_perf = pd.merge(rep_collections, rep_deposits, on='Route', how='outer').fillna(0)
        rep_perf = rep_perf.sort_values(tot_col_name, ascending=False).head(15) 
        
        fig_rep = go.Figure()
        
        fig_rep.add_trace(go.Bar(
            x=rep_perf['Route'],
            y=rep_perf[tot_col_name],
            name='Total Cash Collected',
            marker_color='#0077B6',
            opacity=0.85,
            # 🚀 1. Column එක ඇතුළට Data Label එක දැමීම (සුදු පාටින්)
            text=rep_perf[tot_col_name].apply(lambda x: f"{x/1000:,.0f}k" if x > 0 else ""),
            textposition="outside", # Label එක Column එකට උඩින් පෙන්වීමට
            insidetextanchor="start",
            textfont=dict(color="#0077B6", size=12, family="Arial Black")
        ))
        
        fig_rep.add_trace(go.Bar(
            x=rep_perf['Route'],
            y=rep_perf['Amount'],
            name='Total Deposited',
            marker_color='#1c1d6e', 
            opacity=0.9,
            text=rep_perf['Amount'].apply(lambda x: f"{x/1000:,.0f}k" if x > 0 else ""),
            textposition="outside", # Label එක Column එකට උඩින් පෙන්වීමට
            textfont=dict(color="#1c1d6e", size=12, family="Arial Black")
        ))
        
        fig_rep = apply_plotly_layout(fig_rep, "Rep Wise: Cash Collection vs Deposits (All Reps)")
        
        fig_rep.update_layout(
            height=450,
            barmode='group',
            hovermode="x unified",
            xaxis=dict(tickangle=-45),
            yaxis=dict(title="Amount (Rs)"),
            # 🚀 l=20 වෙනුවට l=60 ලබා දී වම්පස ඉඩ වැඩි කර ඇත
            margin=dict(t=60, b=80, l=60, r=20)
        )
        st.plotly_chart(fig_rep, use_container_width=True, config=plotly_config)

if __name__ == "__main__":
    show()