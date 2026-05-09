import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import requests
import io
import time

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
            "Zomato Limited (ZOMATO)": {
                'Ticker': 'ZOMATO.NS', 'Name': 'Zomato Limited', 'Symbol': 'ZOMATO',
                'ISIN': 'INE758T01015', 'Listing_Date': '23-JUL-2021', 'Face_Value': '1'
            },
            "Reliance Industries Limited (RELIANCE)": {
                'Ticker': 'RELIANCE.NS', 'Name': 'Reliance Industries Limited', 'Symbol': 'RELIANCE',
                'ISIN': 'INE002A01018', 'Listing_Date': '29-NOV-1995', 'Face_Value': '10'
            }
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
with col1:
    time_period = st.selectbox("Period", ["1d", "5d", "1mo", "3mo", "6mo", "1y"], index=0)
with col2:
    time_interval = st.selectbox("Candle", ["1m", "5m", "15m", "30m", "1h", "1d"], index=0)

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
    except:
        return pd.DataFrame()

data = load_data(ticker_symbol, time_period, time_interval)

# --- 4. PERFECT MARGIN & WALLET ENGINE ---
import streamlit as st

st.sidebar.markdown("---")
st.sidebar.header("💼 Hashim Egod Wallet")

# 1. Initialize Capital & State Variables
if 'initial_capital' not in st.session_state:
    st.session_state['initial_capital'] = 100000.0
if 'balance' not in st.session_state:
    st.session_state['balance'] = 100000.0  
if 'portfolio' not in st.session_state:
    st.session_state['portfolio'] = {} 

# Ensure safe price extraction
current_live_price = data['Close'].iloc[-1] if (not data.empty and 'Close' in data.columns) else 0.0

# 2. Safely initialize and fetch the current ticker's position
if ticker_symbol not in st.session_state['portfolio']:
    st.session_state['portfolio'][ticker_symbol] = {'qty': 0, 'entry': 0.0, 'margin': 0.0, 'type': None}

pos = st.session_state['portfolio'][ticker_symbol]

# 3. Calculate Unrealized P&L
unrealized_pnl = 0.0
if pos['qty'] > 0:
    if pos['type'] == 'BUY':
        unrealized_pnl = (current_live_price - pos['entry']) * pos['qty']
    elif pos['type'] == 'SHORT':
        unrealized_pnl = (pos['entry'] - current_live_price) * pos['qty']

# Calculate Wealth Metrics
net_wealth = st.session_state['balance'] + pos['margin'] + unrealized_pnl
total_pnl = net_wealth - st.session_state['initial_capital']

# Display Metrics
st.sidebar.metric("Total Net Worth", f"₹{net_wealth:,.2f}", delta=f"Total P/L: ₹{total_pnl:,.2f}")

with st.sidebar.expander("🔍 View Cash Breakdown"):
    st.write(f"💵 **Available Funds:** ₹{st.session_state['balance']:,.2f}")
    st.write(f"🔒 **Margin Locked:** ₹{pos['margin']:,.2f}")
    st.write(f"📈 **Live Trade P&L:** ₹{unrealized_pnl:,.2f}")

# 4. Trading Controls
st.sidebar.markdown("---")

# Protect against missing data / zero pricing
if current_live_price > 0:
    trade_qty = st.sidebar.number_input("Quantity", min_value=1, value=10, step=1)
    cost = current_live_price * trade_qty

    if pos['qty'] == 0:
        # If no position, show BUY and SHORT buttons
        col_buy, col_sell = st.sidebar.columns(2)
        
        with col_buy:
            if st.button("🟢 BUY", use_container_width=True):
                if st.session_state['balance'] >= cost:
                    st.session_state['balance'] -= cost
                    st.session_state['portfolio'][ticker_symbol] = {
                        'qty': trade_qty, 
                        'entry': current_live_price, 
                        'margin': cost, 
                        'type': 'BUY'
                    }
                    st.rerun() 
                else:
                    st.sidebar.error("Not enough funds!")

        with col_sell:
            if st.button("🔴 SHORT", use_container_width=True):
                if st.session_state['balance'] >= cost:
                    # Deduct cost as margin so cash goes DOWN
                    st.session_state['balance'] -= cost
                    st.session_state['portfolio'][ticker_symbol] = {
                        'qty': trade_qty, 
                        'entry': current_live_price, 
                        'margin': cost, 
                        'type': 'SHORT'
                    }
                    st.rerun() 
                else:
                    st.sidebar.error("Not enough funds!")
    else:
        # If position exists, show SQUARE OFF button
        st.sidebar.info(f"Open **{pos['type']}** position: {pos['qty']} shares @ ₹{pos['entry']:,.2f}")
        
        if st.sidebar.button("⏹️ SQUARE OFF (Close Trade)", use_container_width=True, type="primary"):
            # Return margin + profit (or minus loss)
            st.session_state['balance'] += pos['margin'] + unrealized_pnl
            # Reset position
            st.session_state['portfolio'][ticker_symbol] = {'qty': 0, 'entry': 0.0, 'margin': 0.0, 'type': None}
            st.rerun()
else:
    st.sidebar.warning("Waiting for valid market data...")
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

    # --- MASSIVE VERDICT BOX ---
    if show_signals:
        latest = data.iloc[-1]
        buy_score, sell_score = 0, 0
        reasons = []

        if pd.notna(latest['RSI']):
            if latest['RSI'] < 30: buy_score += 3; reasons.append("🟢 RSI is Oversold (<30) [+3 Points]")
            elif latest['RSI'] > 70: sell_score += 3; reasons.append("🔴 RSI is Overbought (>70) [+3 Points]")

        if pd.notna(latest['MACD']) and pd.notna(latest['Signal']):
            if latest['MACD'] > latest['Signal']: buy_score += 4; reasons.append("🟢 MACD crossed above Signal Line [+4 Points]")
            elif latest['MACD'] < latest['Signal']: sell_score += 4; reasons.append("🔴 MACD crossed below Signal Line [+4 Points]")

        if pd.notna(latest['SMA20']):
            if latest['Close'] > latest['SMA20']: buy_score += 3; reasons.append("🟢 Price is above 20 SMA (Uptrend) [+3 Points]")
            elif latest['Close'] < latest['SMA20']: sell_score += 3; reasons.append("🔴 Price is below 20 SMA (Downtrend) [+3 Points]")

        st.markdown("### 🤖 Live AI Verdict")
        if buy_score >= 6:
            st.markdown(f"""
            <div style="background-color:rgba(0, 200, 83, 0.15); border: 2px solid #00C853; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
                <h1 style="color: #00C853; margin:0; font-size: 40px;">🟢 BUY NOW</h1>
                <p style="margin:0; font-size: 18px; color: {'white' if theme_choice == 'Ultra Dark' else 'black'};">Score: {buy_score}/10 (Strong Bullish Momentum)</p>
            </div>
            """, unsafe_allow_html=True)
        elif sell_score >= 6:
            st.markdown(f"""
            <div style="background-color:rgba(255, 82, 82, 0.15); border: 2px solid #FF5252; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
                <h1 style="color: #FF5252; margin:0; font-size: 40px;">🔴 SELL NOW</h1>
                <p style="margin:0; font-size: 18px; color: {'white' if theme_choice == 'Ultra Dark' else 'black'};">Score: {sell_score}/10 (Strong Bearish Momentum)</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            max_score = max(buy_score, sell_score)
            st.markdown(f"""
            <div style="background-color:rgba(255, 167, 38, 0.15); border: 2px solid #FFA726; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
                <h1 style="color: #FFA726; margin:0; font-size: 40px;">⚖️ HOLD / WAIT</h1>
                <p style="margin:0; font-size: 18px; color: {'white' if theme_choice == 'Ultra Dark' else 'black'};">Highest Score is {max_score}/10. Mixed Market Signals. Wait for a clearer trend.</p>
            </div>
            """, unsafe_allow_html=True)
            
        with st.expander("See AI Logic Breakdown (Total: 10 Points)"):
            for r in reasons: st.write(r)
        st.markdown("---")

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
    st.markdown("---")

    active_subplots = 2 
    if show_rsi: active_subplots += 1
    if show_macd: active_subplots += 1

    row_heights = [0.5] + [0.5 / (active_subplots - 1)] * (active_subplots - 1)
    fig = make_subplots(rows=active_subplots, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=row_heights)

    current_row = 1
    bull_color, bear_color, bg_color, grid_color, template = ('#00FF00', '#FF0033', '#000000', '#1A1A1A', "plotly_dark") if theme_choice == "Ultra Dark" else ('#00C853', '#FF5252', '#FFFFFF', '#E0E0E0', "plotly_white")

    fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='Price', increasing_line_color=bull_color, decreasing_line_color=bear_color, increasing_fillcolor=bull_color, decreasing_fillcolor=bear_color), row=current_row, col=1)

    if show_sma: fig.add_trace(go.Scatter(x=data.index, y=data['SMA20'], line=dict(color='#FFD700', width=2), name='SMA 20'), row=current_row, col=1)
    if show_ema: fig.add_trace(go.Scatter(x=data.index, y=data['EMA50'], line=dict(color='#00E5FF', width=2), name='EMA 50'), row=current_row, col=1)
    current_row += 1

    colors = [bull_color if c >= o else bear_color for o, c in zip(data['Open'], data['Close'])]
    fig.add_trace(go.Bar(x=data.index, y=data['Volume'], marker_color=colors, name='Volume'), row=current_row, col=1)
    current_row += 1

    if show_rsi:
        fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], line=dict(color='#B026FF', width=2), name='RSI'), row=current_row, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color=bear_color, row=current_row, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color=bull_color, row=current_row, col=1)
        current_row += 1

    if show_macd:
        fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], line=dict(color='#2962FF', width=2), name='MACD'), row=current_row, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['Signal'], line=dict(color='#FF8C00', width=2), name='Signal'), row=current_row, col=1)
        macd_hist = data['MACD'] - data['Signal']
        hist_colors = [bull_color if val >= 0 else bear_color for val in macd_hist]
        fig.add_trace(go.Bar(x=data.index, y=macd_hist, marker_color=hist_colors, name='Histogram'), row=current_row, col=1)

    fig.update_layout(height=900 if active_subplots > 2 else 700, template=template, xaxis_rangeslider_visible=False, showlegend=False, dragmode='pan', hovermode='x unified', plot_bgcolor=bg_color, paper_bgcolor=bg_color, margin=dict(l=20, r=20, t=40, b=20))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor=grid_color) 
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': True, 'displaylogo': False})

if live_mode:
    time.sleep(30)
    st.rerun()
