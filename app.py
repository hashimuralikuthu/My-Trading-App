import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import requests
import io

# 1. Set up the web page
st.set_page_config(page_title="Intraday Trading Dashboard", layout="wide")
st.title("📈 My Trading Dashboard V5 (Ultimate Settings)")

# --- Fetch ALL NSE Stocks ---
@st.cache_data(ttl=86400)
def get_all_nse_tickers():
    try:
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        df = pd.read_csv(io.StringIO(response.text))
        df = df[df['SERIES'] == 'EQ']
        tickers = df['SYMBOL'].astype(str) + ".NS"
        return tickers.tolist()
    except Exception as e:
        return ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ZOMATO.NS"]

all_stocks = get_all_nse_tickers()
# ----------------------------------

# 2. Sidebar for user inputs
st.sidebar.header("1. Choose Stock & Time")
ticker_symbol = st.sidebar.selectbox(
    "Search & Select Any NSE Stock", 
    all_stocks, 
    index=all_stocks.index("RELIANCE.NS") if "RELIANCE.NS" in all_stocks else 0
)

col1, col2 = st.sidebar.columns(2)
with col1:
    time_period = st.selectbox("Period", ["1d", "5d", "1mo", "3mo", "6mo", "1y", "5y"], index=2)
with col2:
    time_interval = st.selectbox("Candle", ["1m", "5m", "15m", "30m", "1h", "1d", "1wk"], index=5)

st.sidebar.markdown("---")

# NEW: Pro Trading Settings
st.sidebar.header("2. Chart Indicators")
chart_type = st.sidebar.radio("Chart Type", ["Candlestick", "Line"])
show_sma = st.sidebar.checkbox("Show 20 SMA (Simple)", value=True)
show_ema = st.sidebar.checkbox("Show 50 EMA (Exponential)", value=False)
show_bb = st.sidebar.checkbox("Show Bollinger Bands", value=False)

# 3. Fetch Market Data
@st.cache_data
def load_data(ticker, period, interval):
    data = yf.download(tickers=ticker, period=period, interval=interval)
    return data

st.write(f"Analyzing data for **{ticker_symbol}**...")
data = load_data(ticker_symbol, time_period, time_interval)

# 4. Display the Pro Dashboard
if not data.empty:
    current_price = data['Close'].iloc[-1].item() 
    st.metric(label="Latest Price", value=f"₹{current_price:.2f}")

    st.subheader("Advanced Technical Chart")

    # Calculate Indicators
    data['SMA_20'] = data['Close'].rolling(window=20).mean()
    data['EMA_50'] = data['Close'].ewm(span=50, adjust=False).mean()
    
    # Calculate Bollinger Bands
    data['BB_std'] = data['Close'].rolling(window=20).std()
    data['BB_upper'] = data['SMA_20'] + (data['BB_std'] * 2)
    data['BB_lower'] = data['SMA_20'] - (data['BB_std'] * 2)

    # Setup Chart Layout
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, subplot_titles=('Price Action', 'Volume'),
                        row_width=[0.2, 0.7])

    # Add Price Chart (Candle or Line)
    if chart_type == "Candlestick":
        fig.add_trace(go.Candlestick(x=data.index,
                        open=data['Open'].squeeze(),
                        high=data['High'].squeeze(),
                        low=data['Low'].squeeze(),
                        close=data['Close'].squeeze(),
                        name='Price',
                        increasing_line_color='#00ff00', 
                        decreasing_line_color='#ff0000'  
                        ), row=1, col=1)
    else:
        fig.add_trace(go.Scatter(x=data.index, y=data['Close'].squeeze(), 
                                 mode='lines', line=dict(color='#00ff00', width=2), name='Close Price'), row=1, col=1)

    # Add Indicators based on Sidebar Toggles
    if show_sma:
        fig.add_trace(go.Scatter(x=data.index, y=data['SMA_20'].squeeze(), 
                                 line=dict(color='#fdb631', width=2), name='20 SMA'), row=1, col=1)
    if show_ema:
        fig.add_trace(go.Scatter(x=data.index, y=data['EMA_50'].squeeze(), 
                                 line=dict(color='#00bfff', width=2), name='50 EMA'), row=1, col=1)
    if show_bb:
        # Upper Band
        fig.add_trace(go.Scatter(x=data.index, y=data['BB_upper'].squeeze(), 
                                 line=dict(color='rgba(255, 255, 255, 0.3)', width=1, dash='dash'), name='BB Upper'), row=1, col=1)
        # Lower Band
        fig.add_trace(go.Scatter(x=data.index, y=data['BB_lower'].squeeze(), fill='tonexty', fillcolor='rgba(255, 255, 255, 0.05)',
                                 line=dict(color='rgba(255, 255, 255, 0.3)', width=1, dash='dash'), name='BB Lower'), row=1, col=1)

    # Add Volume
    colors = ['#00ff00' if close >= open_price else '#ff0000' for close, open_price in zip(data['Close'].squeeze(), data['Open'].squeeze())]
    fig.add_trace(go.Bar(x=data.index, y=data['Volume'].squeeze(), 
                         marker_color=colors, name='Volume'), row=2, col=1)

    # Clean up Chart Design
    fig.update_layout(
        xaxis_rangeslider_visible=False, 
        xaxis2_rangeslider_visible=False,
        height=800, 
        template="plotly_dark",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("No data found. Please check the ticker symbol.")
