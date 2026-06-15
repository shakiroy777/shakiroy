import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 페이지 설정
st.set_page_config(layout="wide", page_title="모바일 트레이딩 레이더")
st.title("📈 실시간 대응 주식 투자 대시보드")

# 2. 사이드바 - 제어 컨트롤러
st.sidebar.header("🕹️ 세팅 컨트롤러")
ticker = st.sidebar.text_input("종목 코드 입력 (삼성전자: 005930.KS)", value="005930.KS")
# 안전한 계산을 위해 기본 조회 기간을 3개월(3mo)로 변경합니다.
period = st.sidebar.selectbox("데이터 기간", ["3mo", "1y", "1mo", "5d"], index=0)
interval = st.sidebar.selectbox("데이터 봉 주기", ["1d", "15m", "5m", "1m"], index=0)

rsi_window = st.sidebar.slider("RSI 기간", 5, 30, 14)
bb_window = st.sidebar.slider("볼린저 밴드 기간", 5, 50, 20)

# 3. 데이터 로드 및 순수 판다스 지표 계산
@st.cache_data(ttl=30)
def load_bulletproof_data(symbol, p, i):
    raw_data = yf.download(tickers=symbol, period=p, interval=i)
    if raw_data.empty:
        return pd.DataFrame()
    
    # 야후파이낸스 특유의 2차원 데이터를 1차원으로 강제 압축 정제
    df_clean = pd.DataFrame(index=raw_data.index)
    for col in ['Open', 'High', 'Low', 'Close']:
        if col in raw_data.columns:
            col_data = raw_data[col]
            df_clean[col] = col_data.iloc[:, 0] if isinstance(col_data, pd.DataFrame) else col_data
    
    # 데이터 개수가 부족하면 계산 생략
    if len(df_clean) < max(bb_window, rsi_window) + 5:
        return pd.DataFrame()
        
    # [외부 라이브러리 없이 직접 계산 - 에러 발생 확률 제거]
    # 1. 볼린저 밴드 계산
    ma = df_clean['Close'].rolling(window=bb_window).mean()
    std = df_clean['Close'].rolling(window=bb_window).std()
    df_clean['BB_High'] = ma + (std * 2)
    df_clean['BB_Low'] = ma - (std * 2)
    df_clean['MA20'] = ma
    
    # 2. RSI 계산
    delta = df_clean['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=rsi_window).mean()
    avg_loss = loss.rolling(window=rsi_window).mean()
    rs = avg_gain / (avg_loss + 1e-10) # 0으로 나누기 방지
    df_clean['RSI'] = 100 - (100 / (1 + rs))
    
    return df_clean

# 데이터 실행
df = load_bulletproof_data(ticker, period, interval)

if df.empty:
    st.error("⚠️ 데이터가 부족하거나 종목 코드가 올바르지 않습니다. 왼쪽 메뉴에서 '데이터 기간'을 3mo 나 1y로 늘려주세요!")
else:
    # 4. 상단 실시간 계측기 (Metrics)
    c_price = float(df['Close'].iloc[-1])
    p_price = float(df['Close'].iloc[-2])
    diff = c_price - p_price
    c_rsi = float(df['RSI'].iloc[-1])
    c_ma = float(df['MA20'].iloc[-1])
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("현재가", f"{c_price:,.0f} 원", f"{diff:,.0f} 원")
    
    # RSI 신호 판정
    if pd.isna(c_rsi): rsi_sig, rsi_val = "계산중", "0.0"
    elif c_rsi >= 70: rsi_sig, rsi_val = "⚠️ 과매수 (매도)", f"{c_rsi:.1f}"
    elif c_rsi <= 30: rsi_sig, rsi_val = "✅ 과매도 (매수)", f"{c_rsi:.1f}"
    else: rsi_sig, rsi_val = "⚖️ 중립", f"{c_rsi:.1f}"
    col2.metric("RSI 상태", rsi_val, rsi_sig, delta_color="off")
    
    # 볼린저 밴드 판정
    b_high = float(df['BB_High'].iloc[-1])
    b_low = float(df['BB_Low'].iloc[-1])
    if c_price >= b_high: bb_sig = "🔥 상한선 돌파"
    elif c_price <= b_low: bb_sig = "🚨 하한선 이탈"
    else: bb_sig = "➡️ 밴드 내부"
    col3.metric("볼린저 밴드", bb_sig)
    
    # 20일 이평선 기준 가격 위치 (추세 판정)
    trend_pct = ((c_price - c_ma) / c_ma) * 100
    if trend_pct > 1: trend_sig = "💪 상승 추세 우위"
    elif trend_pct < -1: trend_sig = "📉 하락 추세 우위"
    else: trend_sig = "💤 단기 횡보"
    col4.metric("20일선 이격도", f"{trend_pct:+.1f}%", trend_sig, delta_color="off")

    # 5. 인터랙티브 차트 시각화
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
