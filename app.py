import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import os

# 1. Page Configuration
st.set_page_config(page_title="Pro Trading Terminal", layout="wide")
st.title("🔴 My Pro Trading Terminal V26 (Fixed & Stable)")

# --- V26: ROBUST CSV ENGINE ---
@st.cache_data
def get_local_stock_list():
    file_path = 'EQUITY_L.csv'
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            df.columns = df.columns.str.strip() # Clean column names
            df = df[df['SERIES'].str.strip() == 'EQ'].copy()
            df['Display Name'] = df['SYMBOL'] + " - " + df['NAME OF COMPANY']
            df['Yahoo Ticker'] = df['SYMBOL'].astype(str) + ".NS"
            return dict(zip(df['Display Name'], df['Yahoo Ticker']))
        except Exception as e:
            return {"RELIANCE - Reliance Industries": "RELIANCE.NS"}
    else:
        return {
            "IDEA - Vodafone Idea": "IDEA.NS",
            "TATASTEEL - Tata Steel": "TATASTEEL.NS",
            "RELIANCE - Reliance Industries": "RELIANCE.NS",
            "ZOMATO - Zomato Limited": "ZOMATO.NS"
        }

stock_dict = get_local_stock_list()
stock_display_names = sorted(list(stock_dict.keys()))

# 2. Sidebar Settings
st.sidebar.header("🎯 Market Explorer")
selected_display_name = st.sidebar.selectbox(
    f"Search {len(stock_display_names)} Stocks", 
    stock_display_names, 
    index=0
)
ticker_symbol = stock_dict[selected_display_name]

col1, col2 = st.sidebar.columns(2)
with col1:
    time_period = st.selectbox("Period", ["1d", "5d", "1mo", "3mo", "1y", "max"], index=0)
with col2:
    time_interval = st.selectbox("Candle", ["1m", "5m", "15m", "30m", "1h", "1d"], index=1)

st.sidebar.markdown("---")
show_sma = st.sidebar.checkbox("20 SMA (Trend)", value=True)
show_rsi = st.sidebar.checkbox("RSI (Overbought/Oversold)", value=True)

# 3. Data & Indicators Logic
def load_and_process_data(symbol, period, interval):
    data = yf.download(tickers=symbol, period=period, interval=interval, progress=False)
    if data.empty: return None
    
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    # Calculate SMA
    data['SMA20'] = data['Close'].rolling(window=20).mean()
    
    # Calculate RSI
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / (loss + 1e-10) # Avoid division by zero
    data['RSI'] = 100 - (100 / (1 + rs))
    
    return data

# 4. Main Display
data = load_and_process_data(ticker_symbol, time_period, time_interval)

if data is not None:
    last_price = float(data['Close'].iloc[-1])
    current_rsi = float(data['RSI'].iloc[-1])
    current_sma = float(data['SMA20'].iloc[-1])
    
    # --- AI TRADE SIGNAL IN SIDEBAR ---
    with st.sidebar:
        st.markdown("---")
        st.header("🤖 AI Trade Signal")
        if current_rsi > 70:
            st.error("### 🔴 STRONG SELL\n**RSI is Overbought.** Price is likely to drop.")
        elif current_rsi < 30:
            st.success("### 🟢 STRONG BUY\n**RSI is Oversold.** Price is likely to bounce.")
        elif last_price > current_sma:
            st.success("### 🟢 BUY\n**Bullish Trend:** Price is above 20-day Average.")
        else:
            st.warning("### 🔴 SELL\n**Bearish Trend:** Price is below 20-day Average.")

    st.subheader(f"📊 {selected_display_name}")
    c1, c2, c3 = st.columns(3)
    c1.metric("LTP", f"₹{last_price:.2f}")
    c2.metric("Day High", f"₹{data['High'].max():.2f}")
    c3.metric("RSI", f"{current_rsi:.1f}")

    # Plotly Chart
    rows = 2 if show_rsi else 1
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3] if show_rsi else [1])
    
    fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='Price'), row=1, col=1)
    
    if show_sma:
        fig.add_trace(go.Scatter(x=data.index, y=data['SMA20'], line=dict(color='yellow', width=1.5), name='SMA 20'), row=1, col=1)

    if show_rsi:
        fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], line=dict(color='magenta', width=1.5), name='RSI'), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    fig.update_layout(height=700, template="plotly_dark", xaxis_rangeslider_visible=False, dragmode='pan', uirevision=ticker_symbol)
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})
else:
    st.error("Market data unavailable. Try a larger 'Period' like 5d.")
