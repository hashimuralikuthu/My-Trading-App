import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import requests
import io
import time

# 1. Page Configuration
st.set_page_config(page_title="Pro Trading Terminal", layout="wide")
st.title("🔴 My Pro Trading Terminal V11 (Smart Search)")

# --- SMART NSE TICKER FETCHING (LIKE GROWW) ---
@st.cache_data(ttl=86400)
def get_all_nse_tickers():
    try:
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=15)
        df = pd.read_csv(io.StringIO(r.text))
        df = df[df['SERIES'] == 'EQ']
        
        # NEW: Combine Company Name and Symbol (e.g., "Zomato Limited (ZOMATO)")
        df['Display Name'] = df['NAME OF COMPANY'] + " (" + df['SYMBOL'] + ")"
        df['Yahoo Ticker'] = df['SYMBOL'].astype(str) + ".NS"
        
        # Create a dictionary mapping the beautiful display name to the Yahoo ticker
        stock_dict = dict(zip(df['Display Name'], df['Yahoo Ticker']))
        return stock_dict
    except Exception as e:
        # Fallback dictionary if NSE website is slow
        return {
            "Reliance Industries Limited (RELIANCE)": "RELIANCE.NS",
            "Tata Consultancy Services Limited (TCS)": "TCS.NS",
            "Zomato Limited (ZOMATO)": "ZOMATO.NS",
            "HDFC Bank Limited (HDFCBANK)": "HDFCBANK.NS",
            "Infosys Limited (INFY)": "INFY.NS"
        }

stock_dict = get_all_nse_tickers()
stock_display_names = list(stock_dict.keys())

# Find Zomato to use as the default starting stock
default_index = 0
for i, name in enumerate(stock_display_names):
    if "ZOMATO" in name:
        default_index = i
        break

# 2. Sidebar Settings
st.sidebar.header("🎯 Market Explorer")
# NEW: The selectbox now uses the beautiful Company Names!
selected_display_name = st.sidebar.selectbox("Search Company Name or Symbol", stock_display_names, index=default_index)

# Automatically extract the actual symbol for the code to use
ticker_symbol = stock_dict[selected_display_name]

col1, col2 = st.sidebar.columns(2)
with col1:
    time_period = st.selectbox("Period", ["1d", "5d", "1mo", "3mo"], index=0)
with col2:
    time_interval = st.selectbox("Candle", ["1m", "5m", "15m", "30m"], index=0)

st.sidebar.markdown("---")
st.sidebar.header("🛠️ Technical Tools")
show_sma = st.sidebar.checkbox("20 SMA (Trend)", value=True)
show_ema = st.sidebar.checkbox("50 EMA (Support)", value=False)
show_rsi = st.sidebar.checkbox("RSI (Overbought)", value=False)

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

    # Show the clean Company Name at the top instead of just the ticker
    st.subheader(f"📊 {selected_display_name}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Current Price", f"₹{last_price:.2f}", f"{change:.2f} ({pct_change:.2f}%)")
    c2.metric("Day High", f"₹{data['High'].max():.2f}")
    c3.metric("Day Low", f"₹{data['Low'].min():.2f}")

    data['SMA20'] = data['Close'].rolling(window=20).mean()
    data['EMA50'] = data['Close'].ewm(span=50, adjust=False).mean()
    
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))

    rows = 3 if show_rsi else 2
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, 
                        row_width=[0.2, 0.2, 0.6] if show_rsi else [0.3, 0.7])

    bull_color = '#00FF00' 
    bear_color = '#FF0033' 

    fig.add_trace(go.Candlestick(
        x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], 
        name='Price',
        increasing_line_color=bull_color, decreasing_line_color=bear_color,
        increasing_fillcolor=bull_color, decreasing_fillcolor=bear_color,
        line=dict(width=2)
    ), row=1, col=1)

    if show_sma:
        fig.add_trace(go.Scatter(x=data.index, y=data['SMA20'], line=dict(color='#FFD700', width=2), name='SMA 20'), row=1, col=1)
    if show_ema:
        fig.add_trace(go.Scatter(x=data.index, y=data['EMA50'], line=dict(color='#00E5FF', width=2), name='EMA 50'), row=1, col=1)

    colors = [bull_color if c >= o else bear_color for o, c in zip(data['Open'], data['Close'])]
    fig.add_trace(go.Bar(x=data.index, y=data['Volume'], marker_color=colors, name='Volume', opacity=0.8), row=2, col=1)

    if show_rsi:
        fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], line=dict(color='#B026FF', width=2), name='RSI'), row=3, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color=bear_color, row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color=bull_color, row=3, col=1)

    fig.update_layout(
        height=850, 
        template="plotly_dark", 
        xaxis_rangeslider_visible=False, 
        showlegend=True,
        dragmode='pan',          
        hovermode='x unified',   
        plot_bgcolor='#000000',  
        paper_bgcolor='#000000', 
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#1A1A1A') 
    
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
