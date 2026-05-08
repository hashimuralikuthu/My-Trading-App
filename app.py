import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import requests
import io

# 1. Page Configuration
st.set_page_config(page_title="Pro Terminal V13", layout="wide")
st.title("🚀 Pro Trading Terminal V13 (Full NSE Access)")

# --- ADVANCED NSE DATA ENGINE ---
@st.cache_data(ttl=86400)  # Cache for 24 hours
def get_all_nse_tickers():
    try:
        # Step 1: Create a session and mimic a real browser visit to the NSE home page
        # This is CRITICAL to bypass the "403 Forbidden" error
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        
        # Step 2: Download the Equity List CSV
        csv_url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        response = session.get(csv_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            df = pd.read_csv(io.StringIO(response.text))
            # Filter for Equity (EQ) series only
            df = df[df['SERIES'] == 'EQ']
            
            # Step 3: Format the Display Name for the Search Bar
            # "COMPANY NAME (SYMBOL)"
            df['Display Name'] = df['NAME OF COMPANY'] + " (" + df['SYMBOL'] + ")"
            df['Yahoo Ticker'] = df['SYMBOL'] + ".NS"
            
            # Create the dictionary for mapping
            stock_dict = dict(zip(df['Display Name'], df['Yahoo Ticker']))
            return stock_dict
        else:
            raise Exception("Failed to fetch CSV")
            
    except Exception as e:
        st.sidebar.warning("Live NSE fetch failed. Using Top 50 fallback.")
        # Minimal Fallback List (Nifty 50 style)
        return {
            "Reliance Industries Ltd (RELIANCE)": "RELIANCE.NS",
            "TATA Consultancy Services (TCS)": "TCS.NS",
            "HDFC Bank Ltd (HDFCBANK)": "HDFCBANK.NS",
            "Zomato Limited (ZOMATO)": "ZOMATO.NS"
        }

# Load the dictionary
stock_dict = get_all_nse_tickers()
stock_list = sorted(list(stock_dict.keys()))

# 2. Sidebar Search & Settings
st.sidebar.header("🎯 Market Search")
# The search bar now contains 2000+ entries
selected_stock = st.sidebar.selectbox(
    "Search 2,000+ Stocks (Name or Symbol)", 
    stock_list, 
    index=stock_list.index([s for s in stock_list if "RELIANCE" in s][0]) if any("RELIANCE" in s for s in stock_list) else 0
)

ticker_symbol = stock_dict[selected_stock]

col1, col2 = st.sidebar.columns(2)
with col1:
    time_period = st.selectbox("Period", ["1d", "5d", "1mo", "1y", "5y"], index=0)
with col2:
    time_interval = st.selectbox("Interval", ["1m", "5m", "15m", "1h", "1d"], index=1)

# Technical Indicators Toggles
st.sidebar.markdown("---")
st.sidebar.header("🛠️ Analysis Tools")
show_rsi = st.sidebar.toggle("RSI (Relative Strength Index)", value=True)
show_volume = st.sidebar.toggle("Volume Chart", value=True)

# 3. Data Loading Logic
@st.cache_data(ttl=60) # Fast cache for stock data
def load_data(ticker, period, interval):
    data = yf.download(ticker, period=period, interval=interval, progress=False)
    if not data.empty and isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    return data

# 4. Charting Fragment (Live Refresh)
@st.fragment(run_every="30s")
def display_terminal(symbol, display_name):
    df = load_data(symbol, time_period, time_interval)
    
    if df.empty:
        st.error(f"No data found for {display_name}. Market might be closed.")
        return

    # Indicator Calculations
    # Wilder's RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0))
    loss = (-delta.where(delta < 0, 0))
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + (avg_gain / avg_loss)))

    # Subplot Logic
    rows = 1
    if show_volume: rows += 1
    if show_rsi: rows += 1
    
    row_heights = [0.6]
    if show_volume: row_heights.append(0.2)
    if show_rsi: row_heights.append(0.2)

    fig = make_subplots(
        rows=rows, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.04,
        row_width=row_heights[::-1]
    )

    # Main Price Chart
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name="Price"
    ), row=1, col=1)

    # Volume Chart
    if show_volume:
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volume", marker_color='gray', opacity=0.5), row=2, col=1)

    # RSI Chart
    if show_rsi:
        rsi_row = rows
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI", line=dict(color='#00E5FF')), row=rsi_row, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=rsi_row, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=rsi_row, col=1)

    # Styling
    fig.update_layout(
        height=800,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        showlegend=False,
        margin=dict(l=10, r=10, t=30, b=10)
    )
    
    st.subheader(display_name)
    st.plotly_chart(fig, use_container_width=True)

# Run Dashboard
display_terminal(ticker_symbol, selected_stock)
