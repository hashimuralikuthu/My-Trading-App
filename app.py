import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import requests
import io

# 1. Page Configuration
st.set_page_config(page_title="Pro Trading Terminal", layout="wide")
st.title("🚀 My Pro Trading Terminal V7 (Pro Zoom)")

# --- Robust NSE Ticker Fetching ---
@st.cache_data(ttl=86400)
def get_all_nse_tickers():
    try:
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        r = requests.get(url, headers=headers, timeout=15)
        df = pd.read_csv(io.StringIO(r.text))
        
        df = df[df['SERIES'] == 'EQ']
        tickers = sorted((df['SYMBOL'].astype(str) + ".NS").tolist())
        return tickers
    except Exception as e:
        return ["RELIANCE.NS", "TCS.NS", "ZOMATO.NS", "HDFCBANK.NS", "INFY.NS", "TATAMOTORS.NS"]

all_stocks = get_all_nse_tickers()

# 2. Sidebar Settings
st.sidebar.header("🎯 Market Explorer")
ticker_symbol = st.sidebar.selectbox("Search Stock Name (Type here)", all_stocks, index=all_stocks.index("ZOMATO.NS") if "ZOMATO.NS" in all_stocks else 0)

col1, col2 = st.sidebar.columns(2)
with col1:
    time_period = st.selectbox("Period", ["1d", "5d", "1mo", "3mo", "6mo", "1y", "5y"], index=2)
with col2:
    time_interval = st.selectbox("Candle", ["1m", "5m", "15m", "30m", "1h", "1d"], index=4)

st.sidebar.markdown("---")
st.sidebar.header("🛠️ Technical Tools")
show_sma = st.sidebar.checkbox("20 SMA (Trend)", value=True)
show_ema = st.sidebar.checkbox("50 EMA (Support)", value=True)
show_rsi = st.sidebar.checkbox("RSI (Overbought/Oversold)", value=True)

# 3. Data Fetching Logic
@st.cache_data
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

    fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='Price'), row=1, col=1)

    if show_sma:
        fig.add_trace(go.Scatter(x=data.index, y=data['SMA20'], line=dict(color='#FFA500', width=1.5), name='SMA 20'), row=1, col=1)
    if show_ema:
        fig.add_trace(go.Scatter(x=data.index, y=data['EMA50'], line=dict(color='#00FFFF', width=1.5), name='EMA 50'), row=1, col=1)

    colors = ['green' if c >= o else 'red' for o, c in zip(data['Open'], data['Close'])]
    fig.add_trace(go.Bar(x=data.index, y=data['Volume'], marker_color=colors, name='Volume'), row=2, col=1)

    if show_rsi:
        fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], line=dict(color='#FF00FF', width=2), name='RSI'), row=3, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

    # Clean up layout
    fig.update_layout(
        height=900, 
        template="plotly_dark", 
        xaxis_rangeslider_visible=False, 
        showlegend=True,
        dragmode='zoom' # Allows box drawing to zoom
    )
    
    # NEW: Advanced Chart Configuration for Zooming!
    chart_config = {
        'scrollZoom': True,          # Enables mouse wheel / pinch zooming
        'displayModeBar': True,      # Keeps the zoom toolbar permanently visible
        'modeBarButtonsToAdd': ['drawline', 'eraseshape'], # Adds line drawing tools!
        'displaylogo': False         # Removes the Plotly logo
    }
    
    st.plotly_chart(fig, use_container_width=True, config=chart_config)

else:
    st.error(f"Error fetching data for {ticker_symbol}. Please try a different timeframe or check if the market is open.")
