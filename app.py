import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import requests
import io
import time
import json
import os
elif app_mode == "💯 100% PROFIT":
    # --- PAGE 2: STRATEGIC INTELLIGENCE ---
    st.title("💯 100% PROFIT: Deep Market Intelligence")
    st.markdown("---")

    # 1. Record of Current Company
    st.subheader(f"🏢 Active Target: {current_stock_info['Name']}")
    st.write(f"**NSE Ticker:** {current_stock_info['Symbol']} | **ISIN:** {current_stock_info['ISIN']}")
    
    st.markdown("---")
    col_vol, col_google = st.columns(2)

    # 2. Volume & Buy/Sell Pressure
    with col_vol:
        st.markdown("### 🌊 Live Market Flow")
        if not data.empty:
            current_volume = int(data['Volume'].iloc[-1])
            open_price = data['Open'].iloc[-1]
            close_price = data['Close'].iloc[-1]
            
            # Estimating Buy vs Sell pressure based on candle strength
            if close_price >= open_price:
                buy_est = int(current_volume * 0.65)  # Bullish candle = more buyers
                sell_est = current_volume - buy_est
            else:
                sell_est = int(current_volume * 0.65) # Bearish candle = more sellers
                buy_est = current_volume - sell_est

            st.metric("Current Total Volume", f"{current_volume:,}")
            st.write(f"🟢 **Shares Bought (Est):** {buy_est:,}")
            st.write(f"🔴 **Shares Sold (Est):** {sell_est:,}")
        else:
            st.write("Awaiting live volume data...")

    # 3. Google Opinion (AI Sentiment)
    with col_google:
        st.markdown("### 🧠 Google / AI Opinion")
        if not data.empty:
            # Calculating a fast algorithm for the "Opinion"
            price_above_sma = data['Close'].iloc[-1] > data['SMA20'].iloc[-1]
            rsi_value = data['RSI'].iloc[-1]
            
            if price_above_sma and rsi_value < 70:
                st.markdown("""
                <div style="background-color:rgba(0, 200, 83, 0.1); border-left: 5px solid #00C853; padding: 10px;">
                    <h4 style="color: #00C853; margin:0;">🟢 GOOGLE VERDICT: BUY</h4>
                    <p style="margin:0; font-size: 14px;">Algorithm detects positive momentum and safe entry levels.</p>
                </div>
                """, unsafe_allow_html=True)
            elif not price_above_sma and rsi_value > 30:
                st.markdown("""
                <div style="background-color:rgba(255, 82, 82, 0.1); border-left: 5px solid #FF5252; padding: 10px;">
                    <h4 style="color: #FF5252; margin:0;">🔴 GOOGLE VERDICT: SELL</h4>
                    <p style="margin:0; font-size: 14px;">Algorithm detects negative momentum. High risk.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="background-color:rgba(255, 167, 38, 0.1); border-left: 5px solid #FFA726; padding: 10px;">
                    <h4 style="color: #FFA726; margin:0;">⚖️ GOOGLE VERDICT: NEUTRAL</h4>
                    <p style="margin:0; font-size: 14px;">Market is consolidating. Wait for clearer signals.</p>
                </div>
                """, unsafe_allow_html=True)

    # 4. Live News (Text Only)
    st.markdown("---")
    st.markdown("### 📰 Market News Wire (Text Only)")
    
    try:
        stock_ticker = yf.Ticker(ticker_symbol)
        news_data = stock_ticker.news
        
        if news_data:
            for article in news_data[:5]:  # Display top 5 news items
                title = article.get('title', 'No Title')
                publisher = article.get('publisher', 'Unknown Source')
                
                st.markdown(f"**▪️ {title}**")
                st.caption(f"Source: {publisher}")
                st.write("") # Adds a small space between text blocks
        else:
            st.info("No recent news found for this company.")
    except Exception as e:
        st.warning("News feed is currently offline or unreachable.")
# --- PERSISTENT STORAGE ---
WALLET_FILE = "hashim_wallet_data.json"

def load_wallet():
    if os.path.exists(WALLET_FILE):
        with open(WALLET_FILE, "r") as f:
            return json.load(f)
    return None

def save_wallet():
    data_to_save = {
        'initial_capital': st.session_state['initial_capital'],
        'balance': st.session_state['balance'],
        'portfolio': st.session_state['portfolio']
    }
    with open(WALLET_FILE, "w") as f:
        json.dump(data_to_save, f)

# 1. Page Configuration
st.set_page_config(page_title="Hashim Egod Trading Terminal", layout="wide")
st.title("👑 Hashim Egod Trading Terminal V26 (Perfect Paper Trading)")

# --- ADVANCED NSE TICKER & DATA FETCHING ---
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
                'Ticker': row['Yahoo Ticker'],
                'Name': row['NAME OF COMPANY'],
                'Symbol': row['SYMBOL'],
                'ISIN': row['ISIN NUMBER'],
                'Listing_Date': row['DATE OF LISTING'],
                'Face_Value': row['FACE VALUE']
            }
        return stock_data
    except Exception as e:
        return {
            "Zomato Limited (ZOMATO)": {'Ticker': 'ZOMATO.NS', 'Name': 'Zomato Limited', 'Symbol': 'ZOMATO', 'ISIN': 'INE758T01015', 'Listing_Date': '23-JUL-2021', 'Face_Value': '1'},
            "Reliance Industries Limited (RELIANCE)": {'Ticker': 'RELIANCE.NS', 'Name': 'Reliance Industries Limited', 'Symbol': 'RELIANCE', 'ISIN': 'INE002A01018', 'Listing_Date': '29-NOV-1995', 'Face_Value': '10'}
        }

stock_data = get_all_nse_data()
stock_display_names = list(stock_data.keys())

default_index = 0
for i, name in enumerate(stock_display_names):
    if "ZOMATO" in name:
        default_index = i
        break

# 2. Sidebar Settings
st.sidebar.header("🎯 Market Explorer")
selected_display_name = st.sidebar.selectbox("Search Company Name", stock_display_names, index=default_index)
current_stock_info = stock_data[selected_display_name]
ticker_symbol = current_stock_info['Ticker']

col1, col2 = st.sidebar.columns(2)
with col1: time_period = st.selectbox("Period", ["1d", "5d", "1mo", "3mo", "6mo", "1y"], index=0)
with col2: time_interval = st.selectbox("Candle", ["1m", "5m", "15m", "30m", "1h", "1d"], index=0)

st.sidebar.markdown("---")
st.sidebar.header("🎨 App Theme")
theme_choice = st.sidebar.radio("Choose Chart Theme", ["Ultra Dark", "Clean White"])

st.sidebar.markdown("---")
st.sidebar.header("🛠️ Technical Tools")
show_sma = st.sidebar.checkbox("20 SMA (Trend)", value=True)
show_ema = st.sidebar.checkbox("50 EMA (Support)", value=False)
show_rsi = st.sidebar.checkbox("RSI (Overbought/Oversold)", value=True)
show_macd = st.sidebar.checkbox("MACD (Momentum)", value=True) 

st.sidebar.markdown("---")
st.sidebar.header("🤖 AI Trade Assistant")
show_signals = st.sidebar.toggle("Enable Big Verdict Box", value=True)

st.sidebar.markdown("---")
st.sidebar.header("⚡ Live Engine")
live_mode = st.sidebar.toggle("🟢 Enable Live Auto-Update", value=False)

# 3. Data Fetching Logic
@st.cache_data(ttl=30)
def load_data(ticker, period, interval):
    try:
        data = yf.download(tickers=ticker, period=period, interval=interval, progress=False)
        if data.empty: return pd.DataFrame()
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data
    except: return pd.DataFrame()

data = load_data(ticker_symbol, time_period, time_interval)

# --- 4. PERFECT MARGIN & WALLET ENGINE ---
st.sidebar.markdown("---")
st.sidebar.header("💼 Hashim Egod Wallet")

saved_wallet = load_wallet()
if 'initial_capital' not in st.session_state: st.session_state['initial_capital'] = saved_wallet['initial_capital'] if saved_wallet else 100000.0
if 'balance' not in st.session_state: st.session_state['balance'] = saved_wallet['balance'] if saved_wallet else 100000.0  
if 'portfolio' not in st.session_state: st.session_state['portfolio'] = saved_wallet['portfolio'] if saved_wallet else {} 

current_live_price = data['Close'].iloc[-1] if not data.empty else 0
pos = st.session_state['portfolio'].get(ticker_symbol, {'qty': 0, 'entry': 0, 'margin': 0, 'type': None})

unrealized_pnl = 0
if pos['qty'] != 0:
    if pos['type'] == 'BUY': unrealized_pnl = (current_live_price - pos['entry']) * pos['qty']
    elif pos['type'] == 'SHORT': unrealized_pnl = (pos['entry'] - current_live_price) * pos['qty']

net_wealth = st.session_state['balance'] + pos['margin'] + unrealized_pnl
total_pnl = net_wealth - st.session_state['initial_capital']

# --- NEW PAIN SENSOR CALCULATION ---
PAIN_THRESHOLD_PCT = 5.0
current_drawdown_pct = (abs(total_pnl) / st.session_state['initial_capital']) * 100 if total_pnl < 0 else 0
trade_pain_threshold = -2000
is_in_pain = False
pain_message = ""

if current_drawdown_pct >= PAIN_THRESHOLD_PCT:
    is_in_pain = True
    pain_message = f"CRITICAL WEALTH PAIN: {current_drawdown_pct:.2f}% Drawdown detected."
elif unrealized_pnl <= trade_pain_threshold:
    is_in_pain = True
    pain_message = "ACUTE TRADE PAIN: Stop-loss limit reached."

# Display Metrics and Pain Warning
if is_in_pain:
    st.sidebar.markdown(f"""<div style="background-color:rgba(255, 0, 0, 0.2); border: 2px solid #FF0000; padding: 10px; border-radius: 5px; text-align: center;">
        <h3 style="color: #FF0000; margin:0;">⚠️ PAIN DETECTED</h3><p style="margin:0; font-size: 12px;">{pain_message}</p>
        <p style="margin:0; font-weight: bold;">SURVIVAL MODE ACTIVE</p></div>""", unsafe_allow_html=True)

st.sidebar.metric("Total Net Worth", f"₹{net_wealth:,.2f}", delta=f"Total P/L: ₹{total_pnl:.2f}")

with st.sidebar.expander("🔍 View Cash Breakdown"):
    st.write(f"💵 **Available Funds:** ₹{st.session_state['balance']:,.2f}")
    st.write(f"🔒 **Margin Locked:** ₹{pos['margin']:,.2f}")
    st.write(f"📈 **Live Trade P&L:** ₹{unrealized_pnl:,.2f}")

# Trading Controls
st.sidebar.markdown("---")
trade_qty = st.sidebar.number_input("Quantity", min_value=1, value=10, step=1)

if not data.empty:
    if pos['qty'] == 0:
        if is_in_pain:
            st.sidebar.warning("🚫 Trading Locked: Recover from pain first.")
        else:
            col_buy, col_sell = st.sidebar.columns(2)
            with col_buy:
                if st.button("🟢 BUY", use_container_width=True):
                    cost = current_live_price * trade_qty
                    if st.session_state['balance'] >= cost:
                        st.session_state['balance'] -= cost
                        st.session_state['portfolio'][ticker_symbol] = {'qty': trade_qty, 'entry': current_live_price, 'margin': cost, 'type': 'BUY'}
                        save_wallet(); st.rerun()
                    else: st.sidebar.error("Not enough funds!")
            with col_sell:
                if st.button("🔴 SHORT", use_container_width=True):
                    cost = current_live_price * trade_qty
                    if st.session_state['balance'] >= cost:
                        st.session_state['balance'] -= cost
                        st.session_state['portfolio'][ticker_symbol] = {'qty': trade_qty, 'entry': current_live_price, 'margin': cost, 'type': 'SHORT'}
                        save_wallet(); st.rerun()
                    else: st.sidebar.error("Not enough funds!")
    else:
        st.sidebar.info(f"Open {pos['type']} position of {pos['qty']} shares.")
        if st.sidebar.button("⏹️ SQUARE OFF (Kill the Pain)", use_container_width=True, type="primary"):
            st.session_state['balance'] += pos['margin'] + unrealized_pnl
            st.session_state['portfolio'][ticker_symbol] = {'qty': 0, 'entry': 0, 'margin': 0, 'type': None}
            save_wallet(); st.rerun()

# 5. Dashboard Visuals & AI Calculations
if not data.empty:
    last_price = data['Close'].iloc[-1]
    prev_price = data['Close'].iloc[-2]
    change = last_price - prev_price
    pct_change = (change / prev_price) * 100

    data['SMA20'] = data['Close'].rolling(window=20).mean()
    data['EMA50'] = data['Close'].ewm(span=50, adjust=False).mean()
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))
    exp1 = data['Close'].ewm(span=12, adjust=False).mean()
    exp2 = data['Close'].ewm(span=26, adjust=False).mean()
    data['MACD'] = exp1 - exp2
    data['Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()

    if show_signals:
        latest = data.iloc[-1]
        buy_score, sell_score = 0, 0
        reasons = []
        if pd.notna(latest['RSI']):
            if latest['RSI'] < 30: buy_score += 3; reasons.append("🟢 RSI is Oversold (<30)")
            elif latest['RSI'] > 70: sell_score += 3; reasons.append("🔴 RSI is Overbought (>70)")
        if pd.notna(latest['MACD']) and pd.notna(latest['Signal']):
            if latest['MACD'] > latest['Signal']: buy_score += 4; reasons.append("🟢 MACD Bullish Cross")
            elif latest['MACD'] < latest['Signal']: sell_score += 4; reasons.append("🔴 MACD Bearish Cross")
        if pd.notna(latest['SMA20']):
            if latest['Close'] > latest['SMA20']: buy_score += 3; reasons.append("🟢 Price above 20 SMA")
            elif latest['Close'] < latest['SMA20']: sell_score += 3; reasons.append("🔴 Price below 20 SMA")

        st.markdown("### 🤖 Live AI Verdict")
        if buy_score >= 6:
            st.markdown(f'<div style="background-color:rgba(0, 200, 83, 0.15); border: 2px solid #00C853; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;"><h1 style="color: #00C853; margin:0; font-size: 40px;">🟢 BUY NOW</h1><p style="margin:0; font-size: 18px;">Score: {buy_score}/10</p></div>', unsafe_allow_html=True)
        elif sell_score >= 6:
            st.markdown(f'<div style="background-color:rgba(255, 82, 82, 0.15); border: 2px solid #FF5252; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;"><h1 style="color: #FF5252; margin:0; font-size: 40px;">🔴 SELL NOW</h1><p style="margin:0; font-size: 18px;">Score: {sell_score}/10</p></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="background-color:rgba(255, 167, 38, 0.15); border: 2px solid #FFA726; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;"><h1 style="color: #FFA726; margin:0; font-size: 40px;">⚖️ HOLD / WAIT</h1><p style="margin:0; font-size: 18px;">Signals Mixed</p></div>', unsafe_allow_html=True)
        with st.expander("See AI Logic Breakdown"):
            for r in reasons: st.write(r)

    st.subheader(f"📊 {current_stock_info['Name']} ({current_stock_info['Symbol']})")
    with st.expander("ℹ️ Official Company Details"):
        i1, i2, i3, i4 = st.columns(4)
        i1.write(f"**NSE Symbol:** {current_stock_info['Symbol']}")
        i2.write(f"**ISIN:** {current_stock_info['ISIN']}")
        i3.write(f"**Listing Date:** {current_stock_info['Listing_Date']}")
        i4.write(f"**Face Value:** ₹{current_stock_info['Face_Value']}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Current Price", f"₹{last_price:.2f}", f"{change:.2f} ({pct_change:.2f}%)")
    c2.metric("Day High", f"₹{data['High'].max():.2f}")
    c3.metric("Day Low", f"₹{data['Low'].min():.2f}")

    active_subplots = 2 
    if show_rsi: active_subplots += 1
    if show_macd: active_subplots += 1
    row_heights = [0.5] + [0.5 / (active_subplots - 1)] * (active_subplots - 1)
    fig = make_subplots(rows=active_subplots, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=row_heights)
    
    current_row = 1
    bull_color, bear_color, bg_color, grid_color, template = ('#00FF00', '#FF0033', '#000000', '#1A1A1A', "plotly_dark") if theme_choice == "Ultra Dark" else ('#00C853', '#FF5252', '#FFFFFF', '#E0E0E0', "plotly_white")
    
    fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='Price', increasing_line_color=bull_color, decreasing_line_color=bear_color), row=current_row, col=1)
    if show_sma: fig.add_trace(go.Scatter(x=data.index, y=data['SMA20'], line=dict(color='#FFD700', width=2), name='SMA 20'), row=current_row, col=1)
    if show_ema: fig.add_trace(go.Scatter(x=data.index, y=data['EMA50'], line=dict(color='#00E5FF', width=2), name='EMA 50'), row=current_row, col=1)
    current_row += 1

    fig.add_trace(go.Bar(x=data.index, y=data['Volume'], marker_color='#888888', name='Volume'), row=current_row, col=1)
    current_row += 1

    if show_rsi:
        fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], line=dict(color='#B026FF', width=2), name='RSI'), row=current_row, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color=bear_color, row=current_row, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color=bull_color, row=current_row, col=1)
        current_row += 1
    if show_macd:
        fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], line=dict(color='#2962FF', width=2), name='MACD'), row=current_row, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['Signal'], line=dict(color='#FF8C00', width=2), name='Signal'), row=current_row, col=1)

    fig.update_layout(height=900, template=template, xaxis_rangeslider_visible=False, plot_bgcolor=bg_color, paper_bgcolor=bg_color)
    st.plotly_chart(fig, use_container_width=True)

if live_mode:
    time.sleep(30); st.rerun()
