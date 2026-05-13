import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import requests
import io
import time
import json
import os
import urllib.parse
import xml.etree.ElementTree as ET

# --- 1. PERSISTENT STORAGE (CRASH-PROOF) ---
WALLET_FILE = "hashim_wallet_data.json"

def load_wallet():
    if os.path.exists(WALLET_FILE):
        try:
            with open(WALLET_FILE, "r") as f:
                return json.load(f)
        except:
            return None 
    return None

def save_wallet():
    clean_portfolio = {k: v for k, v in st.session_state['portfolio'].items() if v['qty'] > 0}
    st.session_state['portfolio'] = clean_portfolio
    data_to_save = {
        'initial_capital': st.session_state['initial_capital'],
        'balance': st.session_state['balance'],
        'portfolio': clean_portfolio
    }
    with open(WALLET_FILE, "w") as f:
        json.dump(data_to_save, f)

# --- 2. PAGE CONFIGURATION & NAVIGATION ---
st.set_page_config(page_title="Hashim Egod Trading Terminal", layout="wide")

st.sidebar.title("👑 Terminal Menu")
app_mode = st.sidebar.selectbox("Select Page", ["📈 Trading Terminal", "💯 100% PROFIT", "🏛️ 200 MEMBER COUNCIL", "🔮 THE FUTURE", "🤖 GEMINI SYNTHESIS"])

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

# --- 3. SIDEBAR SETTINGS (GLOBAL) ---
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

# Data Fetching Logic
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

# Initialize Session State for Wallet
saved_wallet = load_wallet()
if 'initial_capital' not in st.session_state: st.session_state['initial_capital'] = saved_wallet['initial_capital'] if saved_wallet else 100000.0
if 'balance' not in st.session_state: st.session_state['balance'] = saved_wallet['balance'] if saved_wallet else 100000.0  
if 'portfolio' not in st.session_state: st.session_state['portfolio'] = saved_wallet['portfolio'] if saved_wallet else {} 


# ==========================================
# PAGE 1: TRADING TERMINAL
# ==========================================
if app_mode == "📈 Trading Terminal":
    st.title("👑 Hashim Egod Trading Terminal V26")

    st.sidebar.markdown("---")
    st.sidebar.header("💼 Hashim Egod Wallet")

    current_live_price = data['Close'].iloc[-1] if not data.empty and len(data) > 0 else 0
    
    global_unrealized_pnl = 0.0
    global_margin = 0.0
    
    for t, p_data in list(st.session_state['portfolio'].items()):
        if p_data['qty'] <= 0: continue
        
        global_margin += p_data['margin']
        
        if t == ticker_symbol and current_live_price > 0:
            live_p = current_live_price
        else:
            try:
                bg_data = yf.Ticker(t).history(period="1d", interval="1m")
                live_p = bg_data['Close'].iloc[-1] if not bg_data.empty else p_data['entry']
            except:
                live_p = p_data['entry']
                
        if p_data['type'] == 'BUY': global_unrealized_pnl += (live_p - p_data['entry']) * p_data['qty']
        elif p_data['type'] == 'SHORT': global_unrealized_pnl += (p_data['entry'] - live_p) * p_data['qty']

    net_wealth = st.session_state['balance'] + global_margin + global_unrealized_pnl
    total_pnl = net_wealth - st.session_state['initial_capital']

    pos = st.session_state['portfolio'].get(ticker_symbol, {'qty': 0, 'entry': 0, 'margin': 0, 'type': None})
    local_pnl = 0.0
    if pos['qty'] > 0:
        if pos['type'] == 'BUY': local_pnl = (current_live_price - pos['entry']) * pos['qty']
        elif pos['type'] == 'SHORT': local_pnl = (pos['entry'] - current_live_price) * pos['qty']

    PAIN_THRESHOLD_PCT = 5.0
    current_drawdown_pct = (abs(total_pnl) / st.session_state['initial_capital']) * 100 if total_pnl < 0 else 0
    trade_pain_threshold = -2000
    is_in_pain = False
    pain_message = ""

    if current_drawdown_pct >= PAIN_THRESHOLD_PCT:
        is_in_pain, pain_message = True, f"CRITICAL WEALTH PAIN: {current_drawdown_pct:.2f}% Drawdown."
    elif local_pnl <= trade_pain_threshold:
        is_in_pain, pain_message = True, "ACUTE TRADE PAIN: Stop-loss reached on active chart."

    if is_in_pain:
        st.sidebar.markdown(f'<div style="background-color:rgba(255, 0, 0, 0.2); border: 2px solid #FF0000; padding: 10px; border-radius: 5px; text-align: center;"><h3 style="color: #FF0000; margin:0;">⚠️ PAIN DETECTED</h3><p style="margin:0; font-size: 12px;">{pain_message}</p><p style="margin:0; font-weight: bold;">SURVIVAL MODE ACTIVE</p></div>', unsafe_allow_html=True)

    st.sidebar.metric("Total Net Worth", f"₹{net_wealth:,.2f}", delta=f"Total P/L: ₹{total_pnl:.2f}")

    with st.sidebar.expander("🔍 View Cash Breakdown"):
        st.write(f"💵 **Available Cash:** ₹{st.session_state['balance']:,.2f}")
        st.write(f"🔒 **Global Margin:** ₹{global_margin:,.2f}")
        st.write(f"🌍 **Global Open P&L:** ₹{global_unrealized_pnl:,.2f}")
        if pos['qty'] > 0:
            st.markdown("---")
            st.write(f"📈 **Active ({current_stock_info['Symbol']}) P&L:** ₹{local_pnl:,.2f}")

    st.sidebar.markdown("---")
    trade_qty = st.sidebar.number_input("Quantity", min_value=1, value=10, step=1)

    if not data.empty and current_live_price > 0:
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
                st.session_state['balance'] += pos['margin'] + local_pnl
                del st.session_state['portfolio'][ticker_symbol] 
                save_wallet(); st.rerun()

    if not data.empty and len(data) > 1:
        last_price = data['Close'].iloc[-1]
        prev_price = data['Close'].iloc[-2]
        change = last_price - prev_price
        pct_change = (change / prev_price) * 100

        data['SMA20'] = data['Close'].rolling(window=20).mean()
        data['EMA50'] = data['Close'].ewm(span=50, adjust=False).mean()
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        data['RSI'] = 100 - (100 / (1 + (gain/loss)))
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

        fig.update_layout(
            height=900, 
            template=template, 
            xaxis_rangeslider_visible=False, 
            plot_bgcolor=bg_color, 
            paper_bgcolor=bg_color,
            dragmode='zoom', 
            hovermode='x unified',
            uirevision=ticker_symbol 
        )
        
        st.plotly_chart(fig, use_container_width=True, config={
            'scrollZoom': True,      
            'displayModeBar': True,  
            'displaylogo': False,
            'modeBarButtonsToAdd': ['drawline', 'drawcircle', 'eraseshape']
        })

# ==========================================
# PAGE 2: 100% PROFIT (COUNCIL OF 10)
# ==========================================
elif app_mode == "💯 100% PROFIT":
    st.title("💯 100% PROFIT: Advanced Council of 10")
    st.markdown("---")

    st.subheader(f"🏢 Active Target: {current_stock_info['Name']}")
    st.write(f"**NSE Ticker:** {current_stock_info['Symbol']} | **ISIN:** {current_stock_info['ISIN']}")
    st.markdown("---")

    col_vol, col_google = st.columns(2)
    
    with col_vol:
        st.markdown("### 🌊 Live Market Flow")
        if not data.empty and len(data) > 0:
            current_volume = int(data['Volume'].iloc[-1])
            open_price = data['Open'].iloc[-1]
            close_price = data['Close'].iloc[-1]
            buy_est = int(current_volume * 0.65) if close_price >= open_price else int(current_volume * 0.35)
            sell_est = current_volume - buy_est
            st.metric("Current Total Volume", f"{current_volume:,}")
            st.write(f"🟢 **Shares Bought (Est):** {buy_est:,}")
            st.write(f"🔴 **Shares Sold (Est):** {sell_est:,}")

    with col_google:
        st.markdown("### 💡 Quick Pulse")
        if not data.empty and len(data) > 1:
            pulse_chg = data['Close'].iloc[-1] - data['Open'].iloc[-1]
            if pulse_chg >= 0:
                st.success(f"Session is currently Bullish (Up ₹{pulse_chg:.2f})")
            else:
                st.error(f"Session is currently Bearish (Down ₹{abs(pulse_chg):.2f})")
    
    st.markdown("---")

    st.markdown("### 🏛️ The Council of 10 Decision Makers")
    
    if not data.empty and len(data) > 20:
        close = data['Close']
        high = data['High']
        low = data['Low']
        open_pr = data['Open']
        volume = data['Volume']
        
        sma20 = close.rolling(window=20).mean()
        ema50 = close.ewm(span=50, adjust=False).mean()
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss + 1e-9)))
        
        exp12 = close.ewm(span=12, adjust=False).mean()
        exp26 = close.ewm(span=26, adjust=False).mean()
        macd = exp12 - exp26
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        
        vwap = (volume * (high + low + close) / 3).cumsum() / (volume.cumsum() + 1e-9)
        obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
        obv_sma = obv.rolling(window=20).mean()
        
        stoch_ll = low.rolling(window=14).min()
        stoch_hh = high.rolling(window=14).max()
        stoch_k = 100 * ((close - stoch_ll) / (stoch_hh - stoch_ll + 1e-9))
        
        atr = (high - low).rolling(window=14).mean()
        current_range = high.iloc[-1] - low.iloc[-1]
        
        c_close = close.iloc[-1]
        c_high = high.iloc[-1]
        c_low = low.iloc[-1]
        
        votes = 0
        council_logic = []

        if c_close > (c_high - ((c_high - c_low) * 0.25)): 
            votes += 1; council_logic.append("🟢 Candlestick Expert: Strong Closing Price / Bullish Wick Rejection (Buy)")
        else: council_logic.append("🔴 Candlestick Expert: Weak Closing Price (Sell)")
        
        if c_close > sma20.iloc[-1]: votes += 1; council_logic.append("🟢 SMA Expert: Price above 20 SMA (Buy)")
        else: council_logic.append("🔴 SMA Expert: Price below 20 SMA (Sell)")

        if c_close > ema50.iloc[-1]: votes += 1; council_logic.append("🟢 EMA Expert: Price above 50 EMA Macro Trend (Buy)")
        else: council_logic.append("🔴 EMA Expert: Price below 50 EMA Macro Trend (Sell)")

        if 40 < rsi.iloc[-1] < 75: votes += 1; council_logic.append("🟢 RSI Expert: Momentum is rising safely (Buy)")
        elif rsi.iloc[-1] >= 75: council_logic.append("🔴 RSI Expert: DANGER! Asset is Overbought > 75 (Sell)")
        else: council_logic.append("🔴 RSI Expert: Momentum is dead < 40 (Sell)")

        if macd.iloc[-1] > macd_signal.iloc[-1]: votes += 1; council_logic.append("🟢 MACD Expert: Bullish Crossover Maintained (Buy)")
        else: council_logic.append("🔴 MACD Expert: Bearish Crossover (Sell)")

        if c_close > vwap.iloc[-1]: votes += 1; council_logic.append("🟢 VWAP Expert: Trading above institutional daily average (Buy)")
        else: council_logic.append("🔴 VWAP Expert: Trading below institutional average (Sell)")

        if obv.iloc[-1] > obv_sma.iloc[-1]: votes += 1; council_logic.append("🟢 Volume Expert: Smart Money is Accumulating (Buy)")
        else: council_logic.append("🔴 Volume Expert: Smart Money is Distributing (Sell)")

        if 20 < stoch_k.iloc[-1] < 80: votes += 1; council_logic.append("🟢 Stochastic Expert: Room to grow safely (Buy)")
        else: council_logic.append("🔴 Stochastic Expert: Extreme Zone/Dangerous (Sell)")

        if c_close > sma20.iloc[-1] and current_range > atr.iloc[-1]: votes += 1; council_logic.append("🟢 Volatility Expert: Breakout with Expanding Range (Buy)")
        else: council_logic.append("🔴 Volatility Expert: Price Action is Choppy/Contracting (Sell)")

        if sma20.iloc[-1] > ema50.iloc[-1]: votes += 1; council_logic.append("🟢 Cross Expert: Short trend is beating Long trend (Buy)")
        else: council_logic.append("🔴 Cross Expert: Short trend is failing (Sell)")

        st.markdown("### ⚖️ The Final Verdict")
        
        if votes > 5:
            verdict_color = "#00C853"
            verdict_text = "BUY TIME"
            sub_text = "The majority of the Advanced Council agrees."
        elif votes == 5:
            verdict_color = "#FFA726"
            verdict_text = "HOLD"
            sub_text = "The Council is deadlocked 5 to 5."
        else:
            verdict_color = "#FF5252"
            verdict_text = "SELL / DO NOT BUY"
            sub_text = "The Council has rejected this asset."

        st.markdown(f"""
        <div style="background-color:rgba({verdict_color.lstrip('#')}, 0.15); border: 3px solid {verdict_color}; padding: 30px; border-radius: 15px; text-align: center;">
            <h1 style="color: {verdict_color}; font-size: 60px; margin: 0;">{votes} / 10</h1>
            <h2 style="color: {verdict_color}; margin: 0;">{verdict_text}</h2>
            <p style="margin: 10px 0 0 0; font-size: 18px;">{sub_text}</p>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("🔍 See The Advanced Council's Debate (Individual Votes)"):
            for logic in council_logic:
                st.write(logic)
    else:
        st.warning("Not enough data to convene the Council. Waiting for live market feed...")

# ==========================================
# PAGE 3: 200 MEMBER COUNCIL (ALL 100 INDICATORS)
# ==========================================
elif app_mode == "🏛️ 200 MEMBER COUNCIL":
    st.title("🏛️ The Grand Council of 200 (100 Indicators)")
    st.markdown("---")
    
    st.subheader(f"🏢 Active Target: {current_stock_info['Name']}")
    st.info("Live calculating EXACTLY 100 unique, crash-proof indicators.")

    timeframes = ['1min', '2min', '3min', '5min', '10min', '15min', '30min']
    display_tf = ['1m', '2m', '3m', '5m', '10m', '15m', '30m']
    
    with st.spinner("Summoning the 200 Members... Fetching & Vectorizing Live Data..."):
        try:
            base_1m_data = yf.download(tickers=ticker_symbol, period="7d", interval="1m", progress=False)
            if isinstance(base_1m_data.columns, pd.MultiIndex):
                base_1m_data.columns = base_1m_data.columns.get_level_values(0)
        except Exception as e:
            base_1m_data = pd.DataFrame()

    if not base_1m_data.empty:
        st.markdown("### ⏱️ Multi-Timeframe Matrix (Exact Votes out of 100)")
        tf_cols = st.columns(len(timeframes))
        
        detailed_buy_list = []
        detailed_sell_list = []
        
        for i, tf in enumerate(timeframes):
            with tf_cols[i]:
                try:
                    df = base_1m_data.resample(tf).agg({
                        'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
                    }).dropna()
                    
                    if len(df) > 5:
                        close = df['Close']
                        high = df['High']
                        low = df['Low']
                        vol = df['Volume']
                        
                        buy_inds = []
                        sell_inds = []
                        
                        periods_10 = [3, 5, 7, 9, 12, 15, 20, 25, 30, 35]
                        
                        for p in periods_10:
                            sma = close.rolling(window=p, min_periods=1).mean().fillna(0)
                            if close.iloc[-1] > sma.iloc[-1]: buy_inds.append(f"SMA Breakout ({p})")
                            else: sell_inds.append(f"SMA Breakdown ({p})")

                        for p in periods_10:
                            ema = close.ewm(span=p, adjust=False, min_periods=1).mean().fillna(0)
                            if close.iloc[-1] > ema.iloc[-1]: buy_inds.append(f"EMA Trend ({p})")
                            else: sell_inds.append(f"EMA Trend Drop ({p})")

                        for p in periods_10:
                            fast = close.ewm(span=p, adjust=False, min_periods=1).mean().fillna(0)
                            slow = close.ewm(span=p*2, adjust=False, min_periods=1).mean().fillna(0)
                            if fast.iloc[-1] > slow.iloc[-1]: buy_inds.append(f"MACD Bull Cross ({p}/{p*2})")
                            else: sell_inds.append(f"MACD Bear Cross ({p}/{p*2})")

                        delta = close.diff().fillna(0)
                        gain = delta.where(delta > 0, 0)
                        loss = -delta.where(delta < 0, 0)
                        for p in periods_10:
                            rs = gain.rolling(window=p, min_periods=1).mean() / (loss.rolling(window=p, min_periods=1).mean() + 1e-9)
                            rsi = 100 - (100 / (1 + rs))
                            rsi = rsi.fillna(50)
                            if 40 < rsi.iloc[-1] < 75: buy_inds.append(f"RSI Healthy ({p})")
                            else: sell_inds.append(f"RSI Overbought/Dead ({p})")

                        for p in periods_10:
                            stoch_ll = low.rolling(window=p, min_periods=1).min().fillna(0)
                            stoch_hh = high.rolling(window=p, min_periods=1).max().fillna(0)
                            stoch = 100 * ((close - stoch_ll) / (stoch_hh - stoch_ll + 1e-9))
                            stoch = stoch.fillna(50)
                            if 20 < stoch.iloc[-1] < 80: buy_inds.append(f"Stoch Active ({p})")
                            else: sell_inds.append(f"Stoch Exhausted/Risk ({p})")

                        for p in periods_10:
                            shifted = close.shift(p)
                            roc = ((close - shifted) / (shifted + 1e-9)) * 100
                            roc = roc.fillna(0)
                            if roc.iloc[-1] > 0: buy_inds.append(f"ROC Positive ({p})")
                            else: sell_inds.append(f"ROC Negative ({p})")

                        for p in periods_10:
                            sma = close.rolling(window=p, min_periods=1).mean().fillna(0)
                            std = close.rolling(window=p, min_periods=1).std().fillna(0)
                            upper = sma + (std * 2)
                            if close.iloc[-1] > sma.iloc[-1] and close.iloc[-1] < upper.iloc[-1]: 
                                buy_inds.append(f"Bollinger Push ({p})")
                            else: 
                                sell_inds.append(f"Bollinger Drag/Exhaustion ({p})")

                        for p in periods_10:
                            hh = high.rolling(window=p, min_periods=1).max().fillna(0)
                            ll = low.rolling(window=p, min_periods=1).min().fillna(0)
                            mid = (hh + ll) / 2
                            if close.iloc[-1] > mid.iloc[-1]: buy_inds.append(f"Donchian Bull ({p})")
                            else: sell_inds.append(f"Donchian Bear ({p})")

                        obv = (np.sign(close.diff().fillna(0)) * vol).fillna(0).cumsum()
                        for p in periods_10:
                            obv_sma = obv.rolling(window=p, min_periods=1).mean().fillna(0)
                            if obv.iloc[-1] > obv_sma.iloc[-1]: buy_inds.append(f"OBV Inflow ({p})")
                            else: sell_inds.append(f"OBV Outflow ({p})")

                        typ_price = (high + low + close) / 3
                        for p in periods_10:
                            vp = typ_price * vol
                            vwap_p = vp.rolling(window=p, min_periods=1).sum() / (vol.rolling(window=p, min_periods=1).sum() + 1e-9)
                            vwap_p = vwap_p.fillna(0)
                            if close.iloc[-1] > vwap_p.iloc[-1]: buy_inds.append(f"VWAP Bull ({p})")
                            else: sell_inds.append(f"VWAP Bear ({p})")
                        
                        if tf == '1min':
                            detailed_buy_list = buy_inds
                            detailed_sell_list = sell_inds

                        buy_count = len(buy_inds)
                        sell_count = len(sell_inds)
                        
                        if buy_count > sell_count:
                            bg_col, bord_col = "rgba(0, 200, 83, 0.15)", "#00C853"
                        elif sell_count > buy_count:
                            bg_col, bord_col = "rgba(255, 82, 82, 0.15)", "#FF5252"
                        else:
                            bg_col, bord_col = "rgba(255, 167, 38, 0.15)", "#FFA726"
                        
                        st.markdown(f'''
                        <div style="background-color:{bg_col}; border: 2px solid {bord_col}; padding: 10px; border-radius: 10px; text-align: center; margin-bottom: 10px;">
                            <h4 style="margin:0; color: {bord_col};">{display_tf[i]}</h4>
                            <p style="margin:5px 0; font-size: 14px; font-weight: bold;">Buy: <span style="color:#00C853">{buy_count}</span> | Sell: <span style="color:#FF5252">{sell_count}</span></p>
                        </div>
                        ''', unsafe_allow_html=True)
                        
                    else:
                        st.warning(f"Wait {display_tf[i]}")
                except Exception as e:
                    st.error(f"Error on {display_tf[i]}: {str(e)}")
        
        st.markdown("---")
        st.markdown("### ⚖️ The 100 Indicator Breakdown (1-Minute Engine)")
        
        col_buy_side, col_sell_side = st.columns(2)
        
        with col_buy_side:
            st.markdown(f'''
            <div style="background-color:rgba(0, 200, 83, 0.1); border: 2px solid #00C853; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
                <h2 style="color: #00C853; margin:0;">🟢 BUY SIDE</h2>
                <h1 style="color: #00C853; margin:0; font-size: 50px;">{len(detailed_buy_list)} <span style="font-size:20px;">Members</span></h1>
            </div>
            ''', unsafe_allow_html=True)
            
            with st.container(height=600):
                for ind in detailed_buy_list:
                    st.markdown(f"✅ {ind}")

        with col_sell_side:
            st.markdown(f'''
            <div style="background-color:rgba(255, 82, 82, 0.1); border: 2px solid #FF5252; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
                <h2 style="color: #FF5252; margin:0;">🔴 SELL SIDE</h2>
                <h1 style="color: #FF5252; margin:0; font-size: 50px;">{len(detailed_sell_list)} <span style="font-size:20px;">Members</span></h1>
            </div>
            ''', unsafe_allow_html=True)
            
            with st.container(height=600):
                for ind in detailed_sell_list:
                    st.markdown(f"❌ {ind}")

    else:
        st.error("Market Data Unavailable right now. The market may be closed or offline.")

# ==========================================
# PAGE 4: THE FUTURE (ALL 100 INDICATORS)
# ==========================================
elif app_mode == "🔮 THE FUTURE":
    st.title("🔮 The Future: 100-Point Predictive Horizon")
    st.markdown("---")
    
    st.subheader(f"🏢 Active Target: {current_stock_info['Name']}")
    st.info("Calculating 100 Forward-looking crash-proof probabilities across 8 timeframes.")

    timeframes = ['1min', '2min', '3min', '5min', '10min', '15min', '30min', '60min']
    display_tf = ['1m', '2m', '3m', '5m', '10m', '15m', '30m', '60m']
    
    with st.spinner("Calculating the Predictive Horizon... Fetching Live Data..."):
        try:
            base_1m_data = yf.download(tickers=ticker_symbol, period="7d", interval="1m", progress=False)
            if isinstance(base_1m_data.columns, pd.MultiIndex):
                base_1m_data.columns = base_1m_data.columns.get_level_values(0)
        except Exception as e:
            base_1m_data = pd.DataFrame()

    if not base_1m_data.empty:
        st.markdown("### 📈 Probability of Next Candle Trend (Out of 100)")
        tf_cols = st.columns(len(timeframes))
        
        detailed_bull_future = []
        detailed_bear_future = []
        
        for i, tf in enumerate(timeframes):
            with tf_cols[i]:
                try:
                    df = base_1m_data.resample(tf).agg({
                        'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
                    }).dropna()
                    
                    if len(df) > 5:
                        close = df['Close']
                        high = df['High']
                        low = df['Low']
                        vol = df['Volume']
                        
                        bull_momentum = []
                        bear_pressure = []
                        
                        periods_10 = [3, 5, 7, 9, 12, 15, 20, 25, 30, 35]
                        
                        for p in periods_10:
                            sma = close.rolling(window=p, min_periods=1).mean().fillna(0)
                            if close.iloc[-1] > sma.iloc[-1]: bull_momentum.append(f"Future SMA Bias ({p})")
                            else: bear_pressure.append(f"Future SMA Drop ({p})")

                        for p in periods_10:
                            ema = close.ewm(span=p, adjust=False, min_periods=1).mean().fillna(0)
                            if close.iloc[-1] > ema.iloc[-1]: bull_momentum.append(f"Future EMA Bias ({p})")
                            else: bear_pressure.append(f"Future EMA Drop ({p})")

                        for p in periods_10:
                            fast = close.ewm(span=p, adjust=False, min_periods=1).mean().fillna(0)
                            slow = close.ewm(span=p*2, adjust=False, min_periods=1).mean().fillna(0)
                            if fast.iloc[-1] > slow.iloc[-1]: bull_momentum.append(f"Future MACD Push ({p}/{p*2})")
                            else: bear_pressure.append(f"Future MACD Pull ({p}/{p*2})")

                        delta = close.diff().fillna(0)
                        gain = delta.where(delta > 0, 0)
                        loss = -delta.where(delta < 0, 0)
                        for p in periods_10:
                            rs = gain.rolling(window=p, min_periods=1).mean() / (loss.rolling(window=p, min_periods=1).mean() + 1e-9)
                            rsi = 100 - (100 / (1 + rs))
                            rsi = rsi.fillna(50)
                            if 40 < rsi.iloc[-1] < 75: bull_momentum.append(f"Future RSI Velocity ({p})")
                            else: bear_pressure.append(f"Future RSI Exhaustion ({p})")

                        for p in periods_10:
                            stoch_ll = low.rolling(window=p, min_periods=1).min().fillna(0)
                            stoch_hh = high.rolling(window=p, min_periods=1).max().fillna(0)
                            stoch = 100 * ((close - stoch_ll) / (stoch_hh - stoch_ll + 1e-9))
                            stoch = stoch.fillna(50)
                            if 20 < stoch.iloc[-1] < 80: bull_momentum.append(f"Future Stoch Arc ({p})")
                            else: bear_pressure.append(f"Future Stoch Danger ({p})")

                        for p in periods_10:
                            shifted = close.shift(p)
                            roc = ((close - shifted) / (shifted + 1e-9)) * 100
                            roc = roc.fillna(0)
                            if roc.iloc[-1] > 0: bull_momentum.append(f"Future ROC Push ({p})")
                            else: bear_pressure.append(f"Future ROC Pull ({p})")

                        for p in periods_10:
                            sma = close.rolling(window=p, min_periods=1).mean().fillna(0)
                            std = close.rolling(window=p, min_periods=1).std().fillna(0)
                            upper = sma + (std * 2)
                            if close.iloc[-1] > sma.iloc[-1] and close.iloc[-1] < upper.iloc[-1]: 
                                bull_momentum.append(f"Future Bollinger Launch ({p})")
                            else: 
                                bear_pressure.append(f"Future Bollinger Wall ({p})")

                        for p in periods_10:
                            hh = high.rolling(window=p, min_periods=1).max().fillna(0)
                            ll = low.rolling(window=p, min_periods=1).min().fillna(0)
                            mid = (hh + ll) / 2
                            if close.iloc[-1] > mid.iloc[-1]: bull_momentum.append(f"Future Channel Support ({p})")
                            else: bear_pressure.append(f"Future Channel Resistance ({p})")

                        obv = (np.sign(close.diff().fillna(0)) * vol).fillna(0).cumsum()
                        for p in periods_10:
                            obv_sma = obv.rolling(window=p, min_periods=1).mean().fillna(0)
                            if obv.iloc[-1] > obv_sma.iloc[-1]: bull_momentum.append(f"Future Volume Growth ({p})")
                            else: bear_pressure.append(f"Future Volume Decay ({p})")

                        typ_price = (high + low + close) / 3
                        for p in periods_10:
                            vp = typ_price * vol
                            vwap_p = vp.rolling(window=p, min_periods=1).sum() / (vol.rolling(window=p, min_periods=1).sum() + 1e-9)
                            vwap_p = vwap_p.fillna(0)
                            if close.iloc[-1] > vwap_p.iloc[-1]: bull_momentum.append(f"Future Inst. Flow Up ({p})")
                            else: bear_pressure.append(f"Future Inst. Flow Down ({p})")

                        if tf == '5min':
                            detailed_bull_future = bull_momentum
                            detailed_bear_future = bear_pressure

                        bull_prob = len(bull_momentum)
                        bear_prob = len(bear_pressure)
                        total = bull_prob + bear_prob
                        bull_pct = int((bull_prob / total) * 100) if total > 0 else 50
                        
                        if bull_pct > 55:
                            bg_col, bord_col, arrow = "rgba(0, 200, 83, 0.15)", "#00C853", "📈 UP"
                        elif bull_pct < 45:
                            bg_col, bord_col, arrow = "rgba(255, 82, 82, 0.15)", "#FF5252", "📉 DOWN"
                        else:
                            bg_col, bord_col, arrow = "rgba(255, 167, 38, 0.15)", "#FFA726", "⚖️ NEUTRAL"
                        
                        st.markdown(f'''
                        <div style="background-color:{bg_col}; border: 2px solid {bord_col}; padding: 10px; border-radius: 10px; text-align: center; margin-bottom: 10px;">
                            <h4 style="margin:0; color: {bord_col};">{display_tf[i]}</h4>
                            <h2 style="margin:5px 0; font-size: 24px; color: {bord_col};">{bull_pct}%</h2>
                            <p style="margin:0; font-size: 10px; font-weight: bold;">{arrow}</p>
                        </div>
                        ''', unsafe_allow_html=True)
                        
                    else:
                        st.warning(f"Wait {display_tf[i]}")
                except Exception as e:
                    st.error(f"Error on {display_tf[i]}: {str(e)}")
        
        st.markdown("---")
        st.markdown("### ⚖️ The 100-Point Future Horizon (5-Minute Engine)")
        
        col_bull_side, col_bear_side = st.columns(2)
        
        with col_bull_side:
            st.markdown(f'''
            <div style="background-color:rgba(0, 200, 83, 0.1); border: 2px solid #00C853; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
                <h2 style="color: #00C853; margin:0;">📈 BULLISH PROBABILITY</h2>
                <h1 style="color: #00C853; margin:0; font-size: 50px;">{len(detailed_bull_future)}%</h1>
            </div>
            ''', unsafe_allow_html=True)
            
            with st.container(height=600):
                for ind in detailed_bull_future:
                    st.markdown(f"⬆️ {ind}")

        with col_bear_side:
            st.markdown(f'''
            <div style="background-color:rgba(255, 82, 82, 0.1); border: 2px solid #FF5252; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
                <h2 style="color: #FF5252; margin:0;">📉 BEARISH PROBABILITY</h2>
                <h1 style="color: #FF5252; margin:0; font-size: 50px;">{len(detailed_bear_future)}%</h1>
            </div>
            ''', unsafe_allow_html=True)
            
            with st.container(height=600):
                for ind in detailed_bear_future:
                    st.markdown(f"⬇️ {ind}")

    else:
        st.error("Market Data Unavailable right now. The market may be closed or offline.")

# ==========================================
# PAGE 5: GEMINI SYNTHESIS ENGINE
# ==========================================
elif app_mode == "🤖 GEMINI SYNTHESIS":
    st.title("🧠 Gemini Synthesis Engine")
    st.markdown("---")
    
    st.subheader(f"🎯 Target Acquired: {current_stock_info['Name']} ({current_stock_info['Symbol']})")
    st.info("I am analyzing the live tape. Synthesizing Volume, Volatility, and Macro Trend to deliver my final trading verdict.")

    with st.spinner("Gemini is reading the market data..."):
        try:
            # We fetch 7 days of 1-minute data for deep analysis
            g_data = yf.download(tickers=ticker_symbol, period="7d", interval="1m", progress=False)
            if isinstance(g_data.columns, pd.MultiIndex):
                g_data.columns = g_data.columns.get_level_values(0)
        except:
            g_data = pd.DataFrame()

    if not g_data.empty and len(g_data) > 50:
        # --- GEMINI AI MATH ENGINE ---
        close = g_data['Close']
        high = g_data['High']
        low = g_data['Low']
        vol = g_data['Volume']
        
        c_price = close.iloc[-1]
        
        # Calculate AI proprietary metrics
        ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
        sma200 = close.rolling(window=200).mean().fillna(0).iloc[-1]
        
        delta = close.diff().fillna(0)
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        rsi = 100 - (100 / (1 + rs)).fillna(50).iloc[-1]
        
        typ_price = (high + low + close) / 3
        vwap = (typ_price * vol).rolling(window=100).sum() / (vol.rolling(window=100).sum() + 1e-9)
        current_vwap = vwap.fillna(0).iloc[-1]
        
        vol_sma = vol.rolling(window=20).mean().iloc[-1]
        current_vol = vol.iloc[-1]

        # Calculate a core base score (starts at 50 Neutral)
        ai_score = 50
        
        # Trend Influence
        if c_price > ema50: ai_score += 10
        else: ai_score -= 10
        if c_price > sma200: ai_score += 10
        else: ai_score -= 10
            
        # Institutional VWAP Influence
        if c_price > current_vwap: ai_score += 15
        else: ai_score -= 15
            
        # Volume Confirmation
        if current_vol > vol_sma and c_price > close.iloc[-2]: ai_score += 10
        elif current_vol > vol_sma and c_price < close.iloc[-2]: ai_score -= 10
            
        # RSI Mean Reversion Guard
        if rsi > 75: ai_score -= 20 # Overbought danger
        elif rsi < 30: ai_score += 20 # Oversold bounce potential
        elif 50 < rsi <= 75: ai_score += 5 # Healthy momentum
        
        # Hard caps
        ai_score = max(0, min(100, ai_score))
        
        # --- VERDICT LOGIC ---
        gemini_color = "#8A2BE2" # Deep AI Purple
        
        if ai_score >= 75:
            v_text, v_color = "STRONG BUY", "#00C853"
            f_text = "Mathematical probability suggests a heavy upward breakout. Institutional buyers are active."
        elif ai_score >= 55:
            v_text, v_color = "CAUTIOUS BUY", "#00E5FF"
            f_text = "Trend is shifting upwards, but momentum is not yet locked. Good entry for early scalping."
        elif ai_score <= 25:
            v_text, v_color = "STRONG SELL", "#FF0000"
            f_text = "Extreme bearish pressure. Institutions are dumping. Do not catch a falling knife."
        elif ai_score <= 45:
            v_text, v_color = "CAUTIOUS SELL", "#FF5252"
            f_text = "Momentum is decaying. Price is slipping below VWAP. Better to exit or short."
        else:
            v_text, v_color = "NEUTRAL / HOLD", "#FFA726"
            f_text = "The market is trapped in consolidation (Squeeze). Wait for the algorithmic breakout."

        # --- TOP UI: THE SCORE ---
        st.markdown(f"""
        <div style="background: linear-gradient(145deg, rgba(138,43,226,0.2) 0%, rgba(0,0,0,0.8) 100%); border: 3px solid {gemini_color}; padding: 30px; border-radius: 15px; text-align: center; box-shadow: 0 0 20px {gemini_color};">
            <h2 style="color: #FFFFFF; margin: 0; font-weight: 300; letter-spacing: 2px;">GEMINI CONVICTION SCORE</h2>
            <h1 style="color: {gemini_color}; font-size: 80px; margin: 0; font-weight: 900; text-shadow: 0 0 10px {gemini_color};">{int(ai_score)}%</h1>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- MIDDLE UI: CURRENT VS FUTURE ---
        col_now, col_future = st.columns(2)
        
        with col_now:
            st.markdown(f'''
            <div style="background-color:rgba(0, 0, 0, 0.4); border-left: 5px solid {v_color}; padding: 20px; border-radius: 5px; height: 180px;">
                <p style="color: #AAAAAA; margin:0; font-size: 14px; text-transform: uppercase;">Current Market Verdict</p>
                <h1 style="color: {v_color}; margin: 5px 0;">{v_text}</h1>
                <p style="color: #FFFFFF; margin:0; font-size: 16px;">Action: Execute order based on current alignment.</p>
            </div>
            ''', unsafe_allow_html=True)
            
        with col_future:
            st.markdown(f'''
            <div style="background-color:rgba(0, 0, 0, 0.4); border-left: 5px solid {gemini_color}; padding: 20px; border-radius: 5px; height: 180px;">
                <p style="color: #AAAAAA; margin:0; font-size: 14px; text-transform: uppercase;">Predictive Horizon (Next 60 Min)</p>
                <h3 style="color: {gemini_color}; margin: 5px 0;">{f_text}</h3>
            </div>
            ''', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # --- BOTTOM UI: CHAIN OF THOUGHT ---
        st.markdown("### 🧬 Gemini's Chain of Thought (Analysis Log)")
        
        # Dynamic Text Generation
        trend_log = f"Price (₹{c_price:.2f}) is currently **{'above' if c_price > ema50 else 'below'}** the 50 EMA macro line. Long term structure is {'Bullish' if c_price > sma200 else 'Bearish'}."
        
        vwap_log = f"Institutional Baseline (VWAP) sits at ₹{current_vwap:.2f}. The asset is trading **{'above' if c_price > current_vwap else 'below'}** this liquidity zone, showing smart money is {'accumulating' if c_price > current_vwap else 'distributing'}."
        
        rsi_log = f"Momentum Engine (RSI) is reading **{rsi:.1f}**. This indicates the asset is {'dangerously overbought and due for a crash' if rsi > 75 else 'oversold and primed for a bounce' if rsi < 30 else 'in a healthy channel with room to move'}."

        st.markdown(f'''
        <div style="background-color:rgba(20, 20, 20, 0.8); border: 1px solid #333333; padding: 20px; border-radius: 10px;">
            <p style="font-family: monospace; color: #00E5FF; margin-bottom: 5px;">> Analyzing Macro Trend...</p>
            <p style="color: #CCCCCC; margin-bottom: 15px;">{trend_log}</p>
            
            <p style="font-family: monospace; color: #00E5FF; margin-bottom: 5px;">> Analyzing Order Flow & VWAP...</p>
            <p style="color: #CCCCCC; margin-bottom: 15px;">{vwap_log}</p>
            
            <p style="font-family: monospace; color: #00E5FF; margin-bottom: 5px;">> Calculating Velocity & Reversion...</p>
            <p style="color: #CCCCCC; margin-bottom: 0;">{rsi_log}</p>
        </div>
        ''', unsafe_allow_html=True)

    else:
        st.error("Market Data Unavailable. Waiting for connection to the exchange...")

# ==========================================
# LIVE ENGINE TRIGGER
# ==========================================
if live_mode:
    time.sleep(10)
    st.rerun()
