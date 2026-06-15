import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 페이지 설정 및 제목
st.set_page_config(layout="wide", page_title="프로 트레이딩 대시보드")
st.title("📈 실시간 대응 주식 투자 대시보드")

# 2. 사이드바 - 종목 선택 및 파라미터 조절
st.sidebar.header("🕹️ 세팅 컨트롤러")
# 국내 주식의 경우 종목코드.KS (코스피) 또는 종목코드.KQ (코스닥) 입력 (예: 삼성전자 005930.KS)
ticker = st.sidebar.text_input("종목 코드 입력", value="005930.KS") 
period = st.sidebar.selectbox("데이터 기간", ["1d", "5d", "1mo", "3mo", "1y"], index=2)
interval = st.sidebar.selectbox("데이터 봉 주기", ["1m", "2m", "5m", "15m", "1d"], index=4)

# 지표 변수 세팅
rsi_window = st.sidebar.slider("RSI 기간", 5, 30, 14)
bb_window = st.sidebar.slider("볼린저 밴드 기간", 5, 50, 20)

# 3. 데이터 로드 및 지표 계산
@st.cache_data(ttl=60) # 1분마다 캐시 갱신 (실시간성 확보)
def load_data(ticker, period, interval):
    data = yf.download(tickers=ticker, period=period, interval=interval)
    if data.empty:
        return data
    
    # [핵심 수정 부분] yfinance 데이터가 2차원으로 들어오는 문제를 1차원(Series)으로 확실하게 압축해 줍니다.
    close_series = pd.Series(data['Close'].values.flatten(), index=data.index)
    high_series = pd.Series(data['High'].values.flatten(), index=data.index)
    low_series = pd.Series(data['Low'].values.flatten(), index=data.index)
    open_series = pd.Series(data['Open'].values.flatten(), index=data.index)
    
    # 1차원 데이터로 변환 후 데이터프레임 재생성
    clean_df = pd.DataFrame({
        'Open': open_series, 'High': high_series, 'Low': low_series, 'Close': close_series
    }, index=data.index)
    
    # 기술적 지표 계산 (ta 라이브러리 활용)
    clean_df['RSI'] = ta.momentum.rsi(clean_df['Close'], window=rsi_window)
    
    bb = ta.volatility.BollingerBands(clean_df['Close'], window=bb_window, window_dev=2)
    clean_df['BB_High'] = bb.bollinger_hband()
    clean_df['BB_Low'] = bb.bollinger_lband()
    
    adx = ta.trend.ADXIndicator(clean_df['High'], clean_df['Low'], clean_df['Close'], window=14)
    clean_df['ADX'] = adx.adx()
    
    return clean_df

df = load_data(ticker, period, interval)

if df.empty:
    st.error("종목 코드가 올바르지 않거나 데이터를 가져올 수 없습니다.")
else:
    # 4. 상단 주요 지표 요약 (Metrics)
    current_price = df['Close'].iloc[-1]
    prev_price = df['Close'].iloc[-2]
    price_diff = current_price - prev_price
    current_rsi = df['RSI'].iloc[-1]
    current_adx = df['ADX'].iloc[-1]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("현재가", f"{current_price:,.0f} 원", f"{price_diff:,.0f} 원")
    
    # RSI 상태 진단
    if current_rsi >= 70:
        rsi_status = "⚠️ 과매수 (매도 검토)"
    elif current_rsi <= 30:
        rsi_status = "✅ 과매도 (매수 검토)"
    else:
        rsi_status = "⚖️ 중립"
    col2.metric("RSI (상대강도)", f"{current_rsi:.1f}", rsi_status, delta_color="off")
    
    # 볼린저 밴드 위치 진단
    bb_low = df['BB_Low'].iloc[-1]
    bb_high = df['BB_High'].iloc[-1]
    if current_price <= bb_low:
        bb_status = "🚨 하한선 이탈 (과매도)"
    elif current_price >= bb_high:
        bb_status = "🔥 상한선 돌파 (강한 모멘텀)"
    else:
        bb_status = "➡️ 밴드 내부"
    col3.metric("볼린저 밴드 상태", bb_status)
    
    # ADX 추세 강도 진단
    if current_adx >= 25:
        adx_status = "💪 강한 추세 형성 중"
    else:
        adx_status = "💤 박스권 / 횡보"
    col4.metric("ADX (추세 강도)", f"{current_adx:.1f}", adx_status, delta_color="off")

    # 5. 프로페셔널 차트 시각화 (Plotly)
    st.subheader("📊 기술적 분석 인터랙티브 차트")
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.1, row_heights=[0.7, 0.3])
    
    # Row 1: 캔들스틱 + 볼린저 밴드
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'],
                                 low=df['Low'], close=df['Close'], name="주가"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_High'], line=dict(color='red', width=1), name="BB 상한선"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Low'], line=dict(color='blue', width=1), name="BB 하한선"), row=1, col=1)
    
    # Row 2: RSI 차트
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple', width=1.5), name="RSI"), row=2, col=1)
    fig.add_shape(type="line", x0=df.index[0], y0=70, x1=df.index[-1], y1=70, line=dict(color="red", dash="dash"), row=2, col=1)
    fig.add_shape(type="line", x0=df.index[0], y0=30, x1=df.index[-1], y1=30, line=dict(color="green", dash="dash"), row=2, col=1)
    
    fig.update_layout(height=600, xaxis_rangeslider_visible=False, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)
    
    # 6. 실시간 데이터 테이블 데이터 뷰
    st.subheader("📋 실시간 데이터 피드 (최근 5개 봉)")
    st.dataframe(df.tail(5).style.format("{:.1f}"))
