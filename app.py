import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 페이지 설정 (다크모드 인지용 레이아웃)
st.set_page_config(layout="wide", page_title="모바일 트레이딩 레이더")
st.title("📈 실시간 대응 주식 투자 대시보드")

# 2. 사이드바 - 제어 컨트롤러
st.sidebar.header("🕹️ 세팅 컨트롤러")
ticker = st.sidebar.text_input("종목 코드 입력 (삼성전자: 005930.KS)", value="005930.KS")
period = st.sidebar.selectbox("데이터 기간", ["5d", "1mo", "3mo", "1y"], index=1)
interval = st.sidebar.selectbox("데이터 봉 주기", ["1m", "5m", "15m", "1d"], index=3)

rsi_window = st.sidebar.slider("RSI 기간", 5, 30, 14)
bb_window = st.sidebar.slider("볼린저 밴드 기간", 5, 50, 20)

# 3. 데이터 로드 및 2차원 배열 강제 해결 (flatten 처리)
@st.cache_data(ttl=30)
def load_clean_data(symbol, p, i):
    # 주가 데이터 다운로드
    raw_data = yf.download(tickers=symbol, period=p, interval=i)
    if raw_data.empty:
        return pd.DataFrame()
    
    # [ValueError: Data must be 1-dimensional 완전히 방어]
    # 다차원 인덱스나 멀티인덱스로 들어오는 데이터를 완벽히 1차원 데이터프레임으로 재조립합니다.
    df_final = pd.DataFrame(index=raw_data.index)
    df_final['Open'] = raw_data['Open'].values.reshape(-1)
    df_final['High'] = raw_data['High'].values.reshape(-1)
    df_final['Low'] = raw_data['Low'].values.reshape(-1)
    df_final['Close'] = raw_data['Close'].values.reshape(-1)
    
    # 기술적 지표 안전하게 계산
    df_final['RSI'] = ta.momentum.rsi(df_final['Close'], window=rsi_window)
    
    bb = ta.volatility.BollingerBands(df_final['Close'], window=bb_window, window_dev=2)
    df_final['BB_High'] = bb.bollinger_hband()
    df_final['BB_Low'] = bb.bollinger_lband()
    
    adx = ta.trend.ADXIndicator(df_final['High'], df_final['Low'], df_final['Close'], window=14)
    df_final['ADX'] = adx.adx()
    
    return df_final

# 실행
df = load_clean_data(ticker, period, interval)

if df.empty:
    st.error("종목 코드가 올바르지 않거나 주가 데이터를 가져올 수 없습니다. (예: 005930.KS)")
else:
    # 4. 실시간 상태 판독기 (Metrics)
    c_price = float(df['Close'].iloc[-1])
    p_price = float(df['Close'].iloc[-2])
    diff = c_price - p_price
    c_rsi = float(df['RSI'].iloc[-1])
    c_adx = float(df['ADX'].iloc[-1])
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("현재가", f"{c_price:,.0f} 원", f"{diff:,.0f} 원")
    
    # RSI 신호등
    if c_rsi >= 70: rsi_sig = "⚠️ 과매수 (매도)"
    elif c_rsi <= 30: rsi_sig = "✅ 과매도 (매수)"
    else: rsi_sig = "⚖️ 중립"
    col2.metric("RSI 상태", f"{c_rsi:.1f}", rsi_sig, delta_color="off")
    
    # 볼린저 밴드 신호등
    b_high = float(df['BB_High'].iloc[-1])
    b_low = float(df['BB_Low'].iloc[-1])
    if c_price >= b_high: bb_sig = "🔥 상한선 돌파"
    elif c_price <= b_low: bb_sig = "🚨 하한선 이탈"
    else: bb_sig = "➡️ 밴드 내부"
    col3.metric("볼린저 밴드", bb_sig)
    
    # ADX 추세 강도
    if c_adx >= 25: adx_sig = "💪 강한 추세"
    else: adx_sig = "💤 횡보/박스권"
    col4.metric("추세 강도 (ADX)", f"{c_adx:.1f}", adx_sig, delta_color="off")

    # 5. 시각화 차트
    st.subheader("📊 실시간 차트 레이더")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.7, 0.3])
    
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="주가"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_High'], line=dict(color='red', width=1), name="밴드 상한"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Low'], line=dict(color='blue', width=1), name="밴드 하한"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple', width=1.5), name="RSI"), row=2, col=1)
    
    fig.add_shape(type="line", x0=df.index[0], y0=70, x1=df.index[-1], y1=70, line=dict(color="red", dash="dash"), row=2, col=1)
    fig.add_shape(type="line", x0=df.index[0], y0=30, x1=df.index[-1], y1=30, line=dict(color="green", dash="dash"), row=2, col=1)
    
    fig.update_layout(height=500, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("📋 최근 5개 봉 데이터")
    st.dataframe(df.tail(5).style.format("{:.1f}"))
