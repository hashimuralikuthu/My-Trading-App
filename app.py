import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import requests
import io
import time

# 1. Page Configuration
st.set_page_config(page_title="Master Trading Terminal", layout="wide")
st.title("👑 My Master Terminal V12 (The Ultimate Combo)")

# --- SMART NSE TICKER FETCHING ---
@st.cache_data(ttl=86400)
def get_all_nse_tickers():
    try:
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=15)
        df = pd.read_csv(io.StringIO(r.text))
        df = df[df['SERIES'] == 'EQ']
        
        df['Display Name'] = df['NAME OF COMPANY'] + " (" + df['SYMBOL'] + ")"
        df['Yahoo Ticker'] = df['SYMBOL'].astype(str) + ".NS"
        
        stock_dict = dict(zip(df['Display Name'], df['Yahoo Ticker']))
        return stock_dict
    except Exception as e:
        return {
            "Reliance Industries Limited (RELIANCE)": "RELIANCE.NS",
            "Tata Consultancy Services Limited (TCS)": "TCS.NS",
            "Zomato Limited (ZOMATO)": "ZOMATO.NS",
            "HDFC Bank Limited (HDFCBANK)": "HDFCBANK.NS"
        }

stock_dict = get_all_nse_tickers()
stock_display_names = list(stock_dict.keys())

default_index = 0
for i, name in enumerate(stock_display_names):
    if "ZOMATO" in name:
        default_index = i
        break

# 2. Sidebar Settings
st.sidebar.header("🎯 Market Explorer")
selected_display_name = st.sidebar.selectbox("Search Company Name", stock_display_names, index=default_index)
ticker_symbol = stock_dict[selected_display_name]

col1, col2 = st.sidebar.columns(2)
with col1:
    time_period = st.selectbox("Period", ["1d", "5d", "1mo", "3mo", "6mo", "1y"], index=0)
with col2:
    time_interval = st.selectbox("Candle", ["1m", "5m", "15m", "30m", "1h", "1d"], index=0)

st.sidebar.markdown("---")
# NEW: THEME TOGGLE
st.sidebar.header("🎨 App Theme")
theme_choice = st.sidebar.radio("Choose Chart Theme", ["Ultra Dark", "Clean White"])

st.sidebar.markdown("---")
st.sidebar.header("🛠️ Technical Tools")
show_sma = st.sidebar.checkbox("20 SMA (Trend)", value=True)
show_ema = st.sidebar.checkbox("50 EMA (Support)", value=False)
show_rsi = st.sidebar.checkbox("RSI (Overbought/Oversold)", value=False)
show_macd = st.sidebar.checkbox("MACD (Momentum)", value=False) # NEW INDICATOR!

st.sidebar.markdown("---")
st.sidebar.header("⚡ Live Engine")
live_mode = st.sidebar.toggle("🟢 Enable Live Auto-Update", value=False)
if live_mode:
    st.sidebar.success("Live Mode Active: Updating every 30s")

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

# 4. Dashboard Visuals
if not data.empty:
    last_price = data['Close'].iloc[-1]
    prev_price = data['Close'].iloc[-2]
    change = last_price - prev_price
    pct_change = (change / prev_price) * 100

    st.subheader(f"📊 {selected_display_name}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Current Price", f"₹{last_price:.2f}", f"{change:.2f} ({pct_change:.2f}%)")
    c2.metric("Day High", f"₹{data['High'].max():.2f}")
    c3.metric("Day Low", f"₹{data['Low'].min():.2f}")

    # Calculations
    data['SMA20'] = data['Close'].rolling(window=20).mean()
    data['EMA50'] = data['Close'].ewm(span=50, adjust=False).mean()
    
    # RSI
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))

    # MACD
    exp1 = data['Close'].ewm(span=12, adjust=False).mean()
    exp2 = data['Close'].ewm(span=26, adjust=False).mean()
    data['MACD'] = exp1 - exp2
    data['Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()

    # Dynamic Layout based on chosen indicators
    active_subplots = 2 # Price + Volume are always on
    if show_rsi: active_subplots += 1
    if show_macd: active_subplots += 1

    row_heights = [0.5] + [0.5 / (active_subplots - 1)] * (active_subplots - 1)
    
    fig = make_subplots(rows=active_subplots, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, row_heights=row_heights)

    current_row = 1

    # Colors based on Theme
    if theme_choice == "Ultra Dark":
        bull_color = '#00FF00'
        bear_color = '#FF0033'
        bg_color = '#000000'
        grid_color = '#1A1A1A'
        template = "plotly_dark"
    else:
        bull_color = '#00C853'
        bear_color = '#FF5252'
        bg_color = '#FFFFFF'
        grid_color = '#E0E0E0'
        template = "plotly_white"

    # 1. Price Chart
    fig.add_trace(go.Candlestick(
        x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], 
        name='Price',
        increasing_line_color=bull_color, decreasing_line_color=bear_color,
        increasing_fillcolor=bull_color, decreasing_fillcolor=bear_color
    ), row=current_row, col=1)

    if show_sma:
        fig.add_trace(go.Scatter(x=data.index, y=data['SMA20'], line=dict(color='#FFD700', width=2), name='SMA 20'), row=current_row, col=1)
    if show_ema:
        fig.add_trace(go.Scatter(x=data.index, y=data['EMA50'], line=dict(color='#00E5FF', width=2), name='EMA 50'), row=current_row, col=1)
    
    current_row += 1

    # 2. Volume Chart
    colors = [bull_color if c >= o else bear_color for o, c in zip(data['Open'], data['Close'])]
    fig.add_trace(go.Bar(x=data.index, y=data['Volume'], marker_color=colors, name='Volume'), row=current_row, col=1)
    current_row += 1

    # 3. RSI Chart
    if show_rsi:
        fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], line=dict(color='#B026FF', width=2), name='RSI'), row=current_row, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color=bear_color, row=current_row, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color=bull_color, row=current_row, col=1)
        current_row += 1

    # 4. MACD Chart
    if show_macd:
        fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], line=dict(color='#2962FF', width=2), name='MACD'), row=current_row, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['Signal'], line=dict(color='#FF8C00', width=2), name='Signal'), row=current_row, col=1)
        # MACD Histogram
        macd_hist = data['MACD'] - data['Signal']
        hist_colors = [bull_color if val >= 0 else bear_color for val in macd_hist]
        fig.add_trace(go.Bar(x=data.index, y=macd_hist, marker_color=hist_colors, name='Histogram'), row=current_row, col=1)

    # Layout Updates
    fig.update_layout(
        height=900 if active_subplots > 2 else 700, 
        template=template, 
        xaxis_rangeslider_visible=False, 
        showlegend=False,
        dragmode='pan',          
        hovermode='x unified',   
        plot_bgcolor=bg_color,  
        paper_bgcolor=bg_color, 
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor=grid_color) 
    
    chart_config = {
        'scrollZoom': True,      
        'displayModeBar': True,  
        'modeBarButtonsToAdd': ['drawline', 'eraseshape'], 
        'displaylogo': False     
    }
    
    st.plotly_chart(fig, use_container_width=True, config=chart_config)

else:
    st.error(f"Error fetching data for {selected_display_name}. Please try a different timeframe.")

if live_mode:
    time.sleep(30)
    st.rerun()
