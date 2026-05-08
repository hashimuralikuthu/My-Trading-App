import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import requests
import io

# 1. Set up the web page
st.set_page_config(page_title="Intraday Trading Dashboard", layout="wide")
st.title("📈 My Trading Dashboard V4 (All NSE Stocks)")

# --- NEW: Fetch ALL NSE Stocks ---
@st.cache_data(ttl=86400) # Cache for 24 hours so it doesn't slow down your app
def get_all_nse_tickers():
    try:
        # Download the official live equity list from the NSE India website
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        df = pd.read_csv(io.StringIO(response.text))
        
        # Keep only pure stocks (Series = EQ), filtering out bonds/ETFs
        df = df[df['SERIES'] == 'EQ']
        
        # Get symbols and add .NS for Yahoo Finance compatibility
        tickers = df['SYMBOL'].astype(str) + ".NS"
        return tickers.tolist()
    except Exception as e:
        # Emergency backup list just in case the NSE website is down
        return ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ZOMATO.NS"]

# Load the massive list of stocks!
all_stocks = get_all_nse_tickers()
# ----------------------------------

# 2. Sidebar for user inputs
st.sidebar.header("Trading Settings")

# The dropdown is now searchable! Just click and type.
ticker_symbol = st.sidebar.selectbox(
    "Search & Select Any NSE Stock", 
    all_stocks, 
    index=all_stocks.index("RELIANCE.NS") if "RELIANCE.NS" in all_stocks else 0
)

time_period = st.sidebar.selectbox("Time Period", ["1d", "5d", "1mo", "3mo", "6mo", "1y", "5y"], index=2)
time_interval = st.sidebar.selectbox("Candle Interval", ["1m", "5m", "15m", "30m", "1h", "1d", "1wk"], index=5)

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

    st.subheader("Advanced Price Action & Volume")

    data['SMA_20'] = data['Close'].rolling(window=20).mean()

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, subplot_titles=('Price & 20 SMA', 'Volume'),
                        row_width=[0.2, 0.7])

    fig.add_trace(go.Candlestick(x=data.index,
                    open=data['Open'].squeeze(),
                    high=data['High'].squeeze(),
                    low=data['Low'].squeeze(),
                    close=data['Close'].squeeze(),
                    name='Price',
                    increasing_line_color='#00ff00', 
                    decreasing_line_color='#ff0000'  
                    ), row=1, col=1)

    fig.add_trace(go.Scatter(x=data.index, y=data['SMA_20'].squeeze(), 
                             line=dict(color='#fdb631', width=2), 
                             name='20 SMA'), row=1, col=1)

    colors = ['#00ff00' if close >= open_price else '#ff0000' for close, open_price in zip(data['Close'].squeeze(), data['Open'].squeeze())]
    
    fig.add_trace(go.Bar(x=data.index, y=data['Volume'].squeeze(), 
                         marker_color=colors, name='Volume'), row=2, col=1)

    fig.update_layout(
        xaxis_rangeslider_visible=False, 
        xaxis2_rangeslider_visible=False,
        height=750, 
        template="plotly_dark",
        showlegend=False,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Raw Market Data")
    st.dataframe(data.tail())
else:
    st.error("No data found for this stock. It might be delisted or inactive.")
