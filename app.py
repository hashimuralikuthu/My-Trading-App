import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import requests
import io
import time
from streamlit_gsheets import GSheetsConnection

# 1. Page Configuration
st.set_page_config(page_title="Hashim Egod Cloud Terminal", layout="wide")
st.title("👑 Hashim Egod Trading Terminal V28 (The Complete Masterpiece)")

# --- 2. CLOUD DATABASE CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_cloud_data():
    try:
        wallet_df = conn.read(worksheet="Wallet", usecols=[0])
        balance = float(wallet_df.iloc[0, 0])
        portfolio_df = conn.read(worksheet="Portfolio")
        portfolio_df = portfolio_df.dropna(subset=['Symbol'])
        return balance, portfolio_df
    except:
        return 100000.0, pd.DataFrame(columns=['Symbol', 'Qty', 'Entry', 'Margin', 'Type'])

def save_to_cloud(balance, portfolio_df):
    conn.update(worksheet="Wallet", data=pd.DataFrame({"balance": [balance]}))
    conn.update(worksheet="Portfolio", data=portfolio_df)

if 'cloud_init' not in st.session_state:
    st.session_state.balance, st.session_state.portfolio_df = load_cloud_data()
    st.session_state.initial_capital = 100000.0
    st.session_state.cloud_init = True

# --- 3. THE 100 MISSING LINES (NSE DATA ENGINE) ---
@st.cache_data(ttl=86400)
def get_all_nse_data():
    try:
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=15)
        df = pd.read_csv(io.StringIO(r.text))
        df.columns = df.columns.str.strip()
        df = df[df['SERIES'] == 'EQ']
        df['Display Name'] = df['NAME OF COMPANY'] + " (" + df['SYMBOL'] + ")"
        df['Yahoo Ticker'] = df['SYMBOL'].astype(str) + ".NS"
        stock_data = {}
        for _, row in df.iterrows():
            stock_data[row['Display Name']] = {
                'Ticker': row['Yahoo Ticker'], 'Name': row['NAME OF COMPANY'],
                'Symbol': row['SYMBOL'], 'ISIN': row['ISIN NUMBER'],
                'Listing_Date': row['DATE OF LISTING'], 'Face_Value': row['FACE VALUE']
            }
        return stock_data
    except:
        return {"Zomato Limited (ZOMATO)": {'Ticker': 'ZOMATO.NS', 'Name': 'Zomato Limited', 'Symbol': 'ZOMATO', 'ISIN': 'INE758T01015', 'Listing_Date': '23-JUL-2021', 'Face_Value': '1'}}

stock_data = get_all_nse_data()
stock_display_names = list(stock_data.keys())

# --- 4. SIDEBAR SETTINGS ---
st.sidebar.header("🎯 Market Explorer")
selected_display_name = st.sidebar.selectbox("Search Company Name", stock_display_names)
current_stock_info = stock_data[selected_display_name]
ticker_symbol = current_stock_info['Ticker']
symbol_key = current_stock_info['Symbol']

col1, col2 = st.sidebar.columns(2)
with col1: time_period = st.selectbox("Period", ["1d", "5d", "1mo", "1y"], index=0)
with col2: time_interval = st.selectbox("Candle", ["1m", "5m", "15m", "1h"], index=1)

st.sidebar.markdown("---")
theme_choice = st.sidebar.radio("Theme", ["Ultra Dark", "Clean White"])
show_tools = st.sidebar.multiselect("Tools", ["SMA", "EMA", "RSI", "MACD"], ["SMA", "RSI", "MACD"])
show_signals = st.sidebar.toggle("Enable AI Verdict Box", value=True)
live_mode = st.sidebar.toggle("🟢 Live Auto-Update", value=True)

# --- 5. DATA FETCHING ---
data = yf.download(ticker_symbol, period=time_period, interval=time_interval, progress=False)
if not data.empty and isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)

# --- 6. CLOUD WALLET ENGINE ---
st.sidebar.markdown("---")
st.sidebar.header("💼 Hashim Egod Wallet")

if not data.empty:
    curr_p = data['Close'].iloc[-1]
    active_pos = st.session_state.portfolio_df[st.session_state.portfolio_df['Symbol'] == symbol_key]
    
    live_pnl = 0
    if not active_pos.empty:
        row = active_pos.iloc[0]
        live_pnl = (curr_p - row['Entry']) * row['Qty'] if row['Type'] == 'BUY' else (row['Entry'] - curr_p) * row['Qty']

    net_worth = st.session_state.balance + (active_pos['Margin'].sum() if not active_pos.empty else 0) + live_pnl
    st.sidebar.metric("Total Net Worth", f"₹{net_worth:,.2f}", delta=f"P/L: ₹{live_pnl:.2f}")

    trade_qty = st.sidebar.number_input("Quantity", min_value=1, value=10)
    if active_pos.empty:
        b_col, s_col = st.sidebar.columns(2)
        with b_col:
            if st.button("🟢 BUY", use_container_width=True):
                cost = curr_p * trade_qty
                if st.session_state.balance >= cost:
                    st.session_state.balance -= cost
                    new_row = pd.DataFrame([[symbol_key, trade_qty, curr_p, cost, 'BUY']], columns=['Symbol', 'Qty', 'Entry', 'Margin', 'Type'])
                    st.session_state.portfolio_df = pd.concat([st.session_state.portfolio_df, new_row], ignore_index=True)
                    save_to_cloud(st.session_state.balance, st.session_state.portfolio_df)
                    st.rerun()
        with s_col:
            if st.button("🔴 SHORT", use_container_width=True):
                cost = curr_p * trade_qty
                if st.session_state.balance >= cost:
                    st.session_state.balance -= cost
                    new_row = pd.DataFrame([[symbol_key, trade_qty, curr_p, cost, 'SHORT']], columns=['Symbol', 'Qty', 'Entry', 'Margin', 'Type'])
                    st.session_state.portfolio_df = pd.concat([st.session_state.portfolio_df, new_row], ignore_index=True)
                    save_to_cloud(st.session_state.balance, st.session_state.portfolio_df)
                    st.rerun()
    else:
        if st.sidebar.button("⏹️ SQUARE OFF (Cloud Sync)", use_container_width=True, type="primary"):
            st.session_state.balance += active_pos.iloc[0]['Margin'] + live_pnl
            st.session_state.portfolio_df = st.session_state.portfolio_df[st.session_state.portfolio_df['Symbol'] != symbol_key]
            save_to_cloud(st.session_state.balance, st.session_state.portfolio_df)
            st.rerun()

# --- 7. DASHBOARD & AI VERDICT ---
if not data.empty:
    # Calculations
    data['SMA20'] = data['Close'].rolling(20).mean()
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    data['RSI'] = 100 - (100 / (1 + (gain/loss)))

    if show_signals:
        rsi_now = data['RSI'].iloc[-1]
        verdict = "🟢 BUY" if rsi_now < 35 else ("🔴 SELL" if rsi_now > 65 else "⚖️ HOLD")
        v_col = "rgba(0,255,0,0.1)" if rsi_now < 35 else ("rgba(255,0,0,0.1)" if rsi_now > 65 else "rgba(255,255,255,0.05)")
        st.markdown(f'<div style="background-color:{v_col}; padding:30px; border-radius:15px; text-align:center; border:1px solid white;"><h1>{verdict}</h1><p>Hashim Egod AI Verdict</p></div>', unsafe_allow_html=True)

    # Advanced Multi-Plotly Chart
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='Price'), row=1, col=1)
    if "SMA" in show_tools: fig.add_trace(go.Scatter(x=data.index, y=data['SMA20'], line=dict(color='orange'), name='SMA 20'), row=1, col=1)
    fig.add_trace(go.Bar(x=data.index, y=data['Volume'], name='Volume'), row=2, col=1)
    fig.update_layout(height=800, template="plotly_dark" if theme_choice == "Ultra Dark" else "plotly_white", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # Global Portfolio Display
    st.subheader("📋 Cloud Global Portfolio")
    st.dataframe(st.session_state.portfolio_df, use_container_width=True)

if live_mode:
    time.sleep(10)
    st.rerun()
