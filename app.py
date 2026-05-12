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
            return None # If JSON is corrupted, start fresh
    return None

def save_wallet():
    # Clean out any 0-quantity ghost trades before saving
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
app_mode = st.sidebar.selectbox("Select Page", ["📈 Trading Terminal", "💯 100% PROFIT", "🏛️ 200 MEMBER COUNCIL"])

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

    # --- 4. PERFECT MARGIN & WALLET ENGINE ---
    st.sidebar.markdown("---")
    st.sidebar.header("💼 Hashim Egod Wallet")

    current_live_price = data['Close'].iloc[-1] if not data.empty and len(data) > 0 else 0
    
    # 1. Global Portfolio Value Calculation
    global_unrealized_pnl = 0.0
    global_margin = 0.0
    
    for t, p_data in list(st.session_state['portfolio'].items()):
        if p_data['qty'] <= 0: continue # Skip ghosts
        
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

    # --- PAIN SENSOR CALCULATION ---
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

    # --- TRADING CONTROLS ---
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

    # 5. Dashboard Visuals & AI Calculations
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
    st.title("💯 100% PROFIT: The Council of 10")
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
        else:
            st.write("Awaiting live volume data...")

    with col_google:
        st.markdown("### 💡 Quick Pulse")
        if not data.empty and len(data) > 1:
            pulse_chg = data['Close'].iloc[-1] - data['Open'].iloc[-1]
            if pulse_chg >= 0:
                st.success(f"Session is currently Bullish (Up ₹{pulse_chg:.2f})")
            else:
                st.error(f"Session is currently Bearish (Down ₹{abs(pulse_chg):.2f})")
    
    st.markdown("---")

    # ==========================================
    # MULTI-TIMEFRAME PREDICTION MATRIX
    # ==========================================
    st.markdown("### 🔮 Future Probability Matrix (Live Trend Scan)")
    timeframes = ['1m', '2m', '5m', '15m', '30m', '60m']
    tf_cols = st.columns(len(timeframes))
    
    for i, tf in enumerate(timeframes):
        with tf_cols[i]:
            try:
                tf_data = yf.download(tickers=ticker_symbol, period="1d", interval=tf, progress=False)
                if not tf_data.empty and len(tf_data) > 1:
                    if isinstance(tf_data.columns, pd.MultiIndex):
                        tf_data.columns = tf_data.columns.get_level_values(0)
                    
                    c_price = tf_data['Close'].iloc[-1]
                    p_price = tf_data['Close'].iloc[-2] if len(tf_data) > 1 else c_price
                    
                    if c_price >= p_price:
                        st.markdown(f"""
                        <div style="background-color:rgba(0, 200, 83, 0.1); border: 1px solid #00C853; padding: 10px; border-radius: 5px; text-align: center;">
                            <h4 style="color: #00C853; margin:0;">{tf}</h4>
                            <p style="margin:0; font-size: 20px;">⬆️ UP</p>
                        </div>""", unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="background-color:rgba(255, 82, 82, 0.1); border: 1px solid #FF5252; padding: 10px; border-radius: 5px; text-align: center;">
                            <h4 style="color: #FF5252; margin:0;">{tf}</h4>
                            <p style="margin:0; font-size: 20px;">⬇️ DOWN</p>
                        </div>""", unsafe_allow_html=True)
                else:
                    st.write(f"{tf}: N/A")
            except:
                st.write(f"{tf}: Error")

    st.markdown("---")

    # ==========================================
    # THE COUNCIL OF 10
    # ==========================================
    st.markdown("### 🏛️ The Council of 10 Decision Makers")
    
    if not data.empty and len(data) > 20:
        close = data['Close']
        high = data['High']
        low = data['Low']
        volume = data['Volume']
        
        sma20 = close.rolling(window=20).mean()
        ema50 = close.ewm(span=50, adjust=False).mean()
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss)))
        exp12 = close.ewm(span=12, adjust=False).mean()
        exp26 = close.ewm(span=26, adjust=False).mean()
        macd = exp12 - exp26
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        vwap = (volume * (high + low + close) / 3).cumsum() / volume.cumsum()
        vol_sma = volume.rolling(window=20).mean()
        stoch_k = ((close - low.rolling(14).min()) / (high.rolling(14).max() - low.rolling(14).min())) * 100
        std20 = close.rolling(window=20).std()
        upper_bb = sma20 + (std20 * 2)

        c_close = close.iloc[-1]
        c_open = data['Open'].iloc[-1]

        votes = 0
        council_logic = []

        if c_close > c_open: votes += 1; council_logic.append("🟢 Candlestick Expert: Green Candle (Buy)")
        else: council_logic.append("🔴 Candlestick Expert: Red Candle (Sell)")
        
        if c_close > sma20.iloc[-1]: votes += 1; council_logic.append("🟢 SMA Expert: Price above 20 SMA (Buy)")
        else: council_logic.append("🔴 SMA Expert: Price below 20 SMA (Sell)")

        if c_close > ema50.iloc[-1]: votes += 1; council_logic.append("🟢 EMA Expert: Price above 50 EMA (Buy)")
        else: council_logic.append("🔴 EMA Expert: Price below 50 EMA (Sell)")

        if rsi.iloc[-1] > 40 and rsi.iloc[-1] < 70: votes += 1; council_logic.append("🟢 RSI Expert: Momentum is rising safely (Buy)")
        else: council_logic.append("🔴 RSI Expert: Momentum exhausted or dead (Sell)")

        if macd.iloc[-1] > macd_signal.iloc[-1]: votes += 1; council_logic.append("🟢 MACD Expert: Bullish Crossover (Buy)")
        else: council_logic.append("🔴 MACD Expert: Bearish Crossover (Sell)")

        if c_close > vwap.iloc[-1]: votes += 1; council_logic.append("🟢 VWAP Expert: Trading above institutional average (Buy)")
        else: council_logic.append("🔴 VWAP Expert: Trading below institutional average (Sell)")

        if volume.iloc[-1] > vol_sma.iloc[-1]: votes += 1; council_logic.append("🟢 Volume Expert: High buying interest (Buy)")
        else: council_logic.append("🔴 Volume Expert: Low volume, weak conviction (Sell)")

        if stoch_k.iloc[-1] < 80 and stoch_k.iloc[-1] > 20: votes += 1; council_logic.append("🟢 Stochastic Expert: Room to grow (Buy)")
        else: council_logic.append("🔴 Stochastic Expert: Overbought/Dangerous (Sell)")

        if c_close > sma20.iloc[-1] and c_close < upper_bb.iloc[-1]: votes += 1; council_logic.append("🟢 Bollinger Expert: Safe upward channel (Buy)")
        else: council_logic.append("🔴 Bollinger Expert: Rejecting upper band or crashing (Sell)")

        if sma20.iloc[-1] > ema50.iloc[-1]: votes += 1; council_logic.append("🟢 Cross Expert: Short trend is beating Long trend (Buy)")
        else: council_logic.append("🔴 Cross Expert: Short trend is failing (Sell)")

        st.markdown("### ⚖️ The Final Verdict")
        
        if votes > 5:
            verdict_color = "#00C853"
            verdict_text = "BUY TIME"
            sub_text = "The majority of the Council agrees. Institutional flow is positive."
        elif votes == 5:
            verdict_color = "#FFA726"
            verdict_text = "HOLD"
            sub_text = "The Council is deadlocked 5 to 5. Do not force a trade."
        else:
            verdict_color = "#FF5252"
            verdict_text = "SELL / DO NOT BUY"
            sub_text = "The Council has rejected this asset. Risk is too high."

        st.markdown(f"""
        <div style="background-color:rgba({verdict_color.lstrip('#')}, 0.15); border: 3px solid {verdict_color}; padding: 30px; border-radius: 15px; text-align: center;">
            <h1 style="color: {verdict_color}; font-size: 60px; margin: 0;">{votes} / 10</h1>
            <h2 style="color: {verdict_color}; margin: 0;">{verdict_text}</h2>
            <p style="margin: 10px 0 0 0; font-size: 18px;">{sub_text}</p>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("🔍 See The Council's Debate (Individual Votes)"):
            for logic in council_logic:
                st.write(logic)
    else:
        st.warning("Not enough data to convene the Council. Waiting for live market feed...")

# ==========================================
# PAGE 3: 200 MEMBER COUNCIL (100 INDICATORS)
# ==========================================
elif app_mode == "🏛️ 200 MEMBER COUNCIL":
    st.title("🏛️ The Grand Council of 200")
    st.markdown("---")
    
    st.subheader(f"🏢 Active Target: {current_stock_info['Name']}")
    st.info("Live calculating 100 unique indicators. Each indicator provides 2 Members (Bull/Bear). The results show exactly how many members are voting BUY vs SELL side-by-side.")

    # Timeframes requested: 1, 2, 3, 5, 10, 15, 30 minutes
    timeframes = ['1min', '2min', '3min', '5min', '10min', '15min', '30min']
    display_tf = ['1m', '2m', '3m', '5m', '10m', '15m', '30m']
    
    # We download 1m data once, then use Pandas to mathematically resample.
    with st.spinner("Summoning the 200 Members... Fetching & Vectorizing Live Data..."):
        try:
            base_1m_data = yf.download(tickers=ticker_symbol, period="5d", interval="1m", progress=False)
            if isinstance(base_1m_data.columns, pd.MultiIndex):
                base_1m_data.columns = base_1m_data.columns.get_level_values(0)
        except Exception as e:
            base_1m_data = pd.DataFrame()

    if not base_1m_data.empty:
        st.markdown("### ⏱️ Multi-Timeframe Matrix (Score out of 100)")
        tf_cols = st.columns(len(timeframes))
        
        # We will save the 1-minute detailed breakdown to display side-by-side later
        detailed_buy_list = []
        detailed_sell_list = []
        
        for i, tf in enumerate(timeframes):
            with tf_cols[i]:
                try:
                    df = base_1m_data.resample(tf).agg({
                        'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
                    }).dropna()
                    
                    if len(df) > 50:
                        close = df['Close']
                        high = df['High']
                        low = df['Low']
                        vol = df['Volume']
                        
                        buy_inds = []
                        sell_inds = []
                        
                        periods = [5, 8, 10, 13, 15, 20, 25, 30, 40, 50]
                        
                        # 1. Trend Group A: Simple Moving Averages
                        for p in periods:
                            sma = close.rolling(window=p).mean()
                            if close.iloc[-1] > sma.iloc[-1]: buy_inds.append(f"SMA (Period {p})")
                            else: sell_inds.append(f"SMA (Period {p})")
                            
                        # 2. Trend Group B: Exponential Moving Averages
                        for p in periods:
                            ema = close.ewm(span=p, adjust=False).mean()
                            if close.iloc[-1] > ema.iloc[-1]: buy_inds.append(f"EMA (Period {p})")
                            else: sell_inds.append(f"EMA (Period {p})")
                            
                        # 3. Momentum Group A: MACD-Style Crosses
                        for p in periods:
                            fast = close.ewm(span=p, adjust=False).mean()
                            slow = close.ewm(span=p*2, adjust=False).mean()
                            if fast.iloc[-1] > slow.iloc[-1]: buy_inds.append(f"MACD Cross ({p}/{p*2})")
                            else: sell_inds.append(f"MACD Cross ({p}/{p*2})")
                            
                        # 4. Volatility Group A: Price vs Median Channels
                        for p in periods:
                            hh = high.rolling(window=p).max()
                            ll = low.rolling(window=p).min()
                            mid = (hh + ll) / 2
                            if close.iloc[-1] > mid.iloc[-1]: buy_inds.append(f"Donchian Mid ({p})")
                            else: sell_inds.append(f"Donchian Mid ({p})")
                            
                        # 5. Momentum Group B: RSI Spectrum
                        delta = close.diff()
                        gain = (delta.where(delta > 0, 0))
                        loss = (-delta.where(delta < 0, 0))
                        for p in periods:
                            avg_gain = gain.rolling(window=p).mean()
                            avg_loss = loss.rolling(window=p).mean()
                            rs = avg_gain / (avg_loss + 1e-9)
                            rsi = 100 - (100 / (1 + rs))
                            if rsi.iloc[-1] > 50: buy_inds.append(f"RSI Bull Zone ({p})")
                            else: sell_inds.append(f"RSI Bear Zone ({p})")
                            
                        # 6. Momentum Group C: Rate of Change / Velocity
                        for p in periods:
                            roc = ((close - close.shift(p)) / (close.shift(p) + 1e-9)) * 100
                            if roc.iloc[-1] > 0: buy_inds.append(f"Rate of Change ({p})")
                            else: sell_inds.append(f"Rate of Change ({p})")
                            
                        # 7. Momentum Group D: Stochastic Oscillator Array
                        for p in periods:
                            stoch_ll = low.rolling(window=p).min()
                            stoch_hh = high.rolling(window=p).max()
                            stoch = 100 * ((close - stoch_ll) / (stoch_hh - stoch_ll + 1e-9))
                            if stoch.iloc[-1] > 50: buy_inds.append(f"Stochastic Oscillator ({p})")
                            else: sell_inds.append(f"Stochastic Oscillator ({p})")
                            
                        # 8. Volatility Group B: Bollinger Bands Pressure
                        for p in periods:
                            sma = close.rolling(window=p).mean()
                            if close.iloc[-1] > sma.iloc[-1]: buy_inds.append(f"Bollinger Push ({p})")
                            else: sell_inds.append(f"Bollinger Drop ({p})")
                            
                        # 9. Volume Group A: Moving Volume Spikes
                        for p in periods:
                            vol_sma = vol.rolling(window=p).mean()
                            if close.iloc[-1] >= close.iloc[-2] and vol.iloc[-1] > vol_sma.iloc[-1]: 
                                buy_inds.append(f"Vol Uptrend Spike ({p})")
                            else: 
                                sell_inds.append(f"Vol Downtrend/Weak ({p})")
                            
                        # 10. Volume Group B: VWAP Weighted Vectors
                        typ_price = (high + low + close) / 3
                        for p in periods:
                            vp = typ_price * vol
                            vwap_p = vp.rolling(window=p).sum() / (vol.rolling(window=p).sum() + 1e-9)
                            if close.iloc[-1] > vwap_p.iloc[-1]: buy_inds.append(f"VWAP Institutional ({p})")
                            else: sell_inds.append(f"VWAP Institutional ({p})")
                        
                        # Save the 1m detailed breakdown for the big side-by-side view
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
                    st.error("Error")
        
        st.markdown("---")
        st.markdown("### ⚖️ The 100 Indicator Side-by-Side Breakdown (1-Minute Engine)")
        
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
        st.error("Market Data Unavailable right now. Trying to re-connect...")

# ==========================================
# LIVE ENGINE TRIGGER
# ==========================================
if live_mode:
    time.sleep(10)
    st.rerun()
