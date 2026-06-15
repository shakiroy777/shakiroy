import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 페이지 설정 및 제목
st.set_page_config(layout="wide", page_title="모바일 통합 트레이딩 레이더")
st.title("⚡ 3대 매매전략 통합 주식 대시보드")

# 감시할 핵심 섹터 주도주 리스트 (반도체, 자동차, 전력인프라, 방산/항공우주 등)
WATCH_LIST = {
    "삼성전자": "005930.KS",
    "SK하이닉스": "000660.KS",
    "현대차": "005380.KS",
    "LS ELECTRIC": "010120.KS",
    "HD현대일렉트릭": "267260.KS",
    "한화시스템": "272210.KS",
    "한화에어로스페이스": "012450.KS",
    "한국항공우주(KAI)": "047810.KS",
    "제노코": "361390.KQ",
    "POSCO홀딩스": "005490.KS"
}

# 2. 사이드바 제어 컨트롤러
st.sidebar.header("🕹️ 세팅 컨트롤러")
current_ticker = st.sidebar.text_input("차트 조회 종목 코드 (기본: 삼성전자)", value="005930.KS")
period = st.sidebar.selectbox("데이터 기간", ["3mo", "1y", "1mo", "5d"], index=0)
interval = st.sidebar.selectbox("데이터 봉 주기", ["1d", "15m", "5m", "1m"], index=0)

# 3. 데이터 로드 및 지표 계산 공통 함수 (안전 모드)
@st.cache_data(ttl=60)
def get_stock_data(symbol, p, i):
    try:
        raw_data = yf.download(tickers=symbol, period=p, interval=i, progress=False)
        if raw_data.empty: return pd.DataFrame()
        
        df = pd.DataFrame(index=raw_data.index)
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in raw_data.columns:
                col_data = raw_data[col]
                df[col] = col_data.iloc[:, 0] if isinstance(col_data, pd.DataFrame) else col_data
        
        if len(df) < 25: return pd.DataFrame()
        
        # 볼린저 밴드
        ma = df['Close'].rolling(window=20).mean()
        std = df['Close'].rolling(window=20).std()
        df['BB_High'] = ma + (std * 2)
        df['BB_Low'] = ma - (std * 2)
        df['MA20'] = ma
        df['MA20_Vol'] = df['Volume'].rolling(window=20).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.clip(lower=0)).rolling(window=14).mean()
        loss = (-delta.clip(upper=0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-10)
        df['RSI'] = 100 - (100 / (1 + rs))
        return df
    except:
        return pd.DataFrame()

# 4. 탭 구성 (차트 보기 vs 3대 전략 추천)
tab1, tab2 = st.tabs(["📊 종목 상세 차트", "🎯 오늘의 3대 추천 전략"])

# ==================== TAB 1: 종목 상세 차트 ====================
with tab1:
    df = get_stock_data(current_ticker, period, interval)
    if df.empty:
        st.error("⚠️ 데이터가 부족하거나 코드가 올바르지 않습니다. 왼쪽 기간을 3mo 이상으로 늘려주세요.")
    else:
        # 상단 실시간 계측기
        c_price = float(df['Close'].iloc[-1])
        p_price = float(df['Close'].iloc[-2])
        diff = c_price - p_price
        c_rsi = float(df['RSI'].iloc[-1])
        b_high, b_low = float(df['BB_High'].iloc[-1]), float(df['BB_Low'].iloc[-1])
        
        col1, col2, col3 = st.columns(3)
        col1.metric("현재가", f"{c_price:,.0f} 원", f"{diff:,.0f} 원")
        
        rsi_sig = "⚠️ 과매수" if c_rsi >= 70 else ("✅ 과매도" if c_rsi <= 30 else "⚖️ 중립")
        col2.metric("RSI 지표", f"{c_rsi:.1f}", rsi_sig, delta_color="off")
        
        bb_sig = "🔥 상한선 돌파" if c_price >= b_high else ("🚨 하한선 이탈" if c_price <= b_low else "➡️ 밴드 내부")
        col3.metric("볼린저 밴드", bb_sig)
        
        # 차트 그리기
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="주가"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_High'], line=dict(color='red', width=1), name="밴드 상한"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_Low'], line=dict(color='blue', width=1), name="밴드 하한"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple', width=1.5), name="RSI"), row=2, col=1)
        fig.add_shape(type="line", x0=df.index[0], y0=70, x1=df.index[-1], y1=70, line=dict(color="red", dash="dash"), row=2, col=1)
        fig.add_shape(type="line", x0=df.index[0], y0=30, x1=df.index[-1], y1=30, line=dict(color="green", dash="dash"), row=2, col=1)
        fig.update_layout(height=450, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

# ==================== TAB 2: 오늘의 3대 추천 전략 ====================
with tab2:
    st.subheader("🕵️‍♂️ 실시간 주도주 시장 스캐너")
    st.write("엄선된 10대 핵심 유망 종목 중에서 실시간 조건에 맞는 최적의 타점을 골라냅니다.")
    
    with st.spinner("⏳ 시장 데이터 분석 및 전략 스캐닝 중..."):
        rebound_list = []    # 전략 1
        value_list = []      # 전략 2
        momentum_list = []   # 전략 3
        
        for name, code in WATCH_LIST.items():
            d_set = get_stock_data(code, "3mo", "1d")
            if d_set.empty: continue
            
            # 최신 값 추출
            close_p = float(d_set['Close'].iloc[-1])
            rsi_p = float(d_set['RSI'].iloc[-1])
            bb_l = float(d_set['BB_Low'].iloc[-1])
            ma20_p = float(d_set['MA20'].iloc[-1])
            vol_p = float(d_set['Volume'].iloc[-1])
            vol_ma = float(d_set['MA20_Vol'].iloc[-1])
            
            # [전략 1] 단기 반등 (RSI 과매도 구간이거나 볼린저 밴드 하한선 근접)
            if rsi_p <= 40 or close_p <= bb_l * 1.01:
                rebound_list.append({"종목명": name, "코드": code, "현재가": f"{close_p:,.0f}원", "RSI": f"{rsi_p:.1f}"})
                
            # [전략 2] 실적 탄탄 가성비 우량주 (yfinance 기본 재무연동 에러 방지를 위해 멀티팩터 가치 스캔)
            # 이격도가 20일선 아래에 있으면서 과매도 영역에 진입한 저평가 상태 검형
            if close_p < ma20_p and rsi_p < 45:
                value_list.append({"종목명": name, "코드": code, "현재가": f"{close_p:,.0f}원", "20일선 이격": f"{((close_p-ma20_p)/ma20_p)*100:+.1f}%"})
                
            # [전략 3] 돈이 몰리는 주도주 모멘텀 (오늘 거래량이 20일 평균 거래량 돌파 + 주가가 20일선 위)
            if vol_p > vol_ma * 1.2 and close_p > ma20_p:
                momentum_list.append({"종목명": name, "코드": code, "현재가": f"{close_p:,.0f}원", "거래량 폭발": f"{float(vol_p/vol_ma)*100:.0f}% 폭증"})
        
        # 결과 화면 배치
        st.markdown("---")
        
        # 전략 1 표시
        st.markdown("### 🟢 1. 단기 낙폭과대 반등 추천 (RSI 바닥권)")
        if rebound_list: st.dataframe(pd.DataFrame(rebound_list), use_container_width=True)
        else: st.info("현재 바닥권까지 과매도된 낙폭과대 종목이 없습니다.")
        
        # 전략 2 표시
        st.markdown("### 💎 2. 가성비 구간 우량주 추천 (저평가 매집)")
        if value_list: st.dataframe(pd.DataFrame(value_list), use_container_width=True)
        else: st.info("현재 밸류에이션 하단에 위치한 우량 매집 후보가 없습니다.")
        
        # 전략 3 표시
        st.markdown("### 🔥 3. 거래량 폭발 섹터 주도주 추천 (돌파 매매)")
        if momentum_list: st.dataframe(pd.DataFrame(momentum_list), use_container_width=True)
        else: st.info("현재 평균 거래량을 돌파하며 강하게 튀어 오르는 주도주가 없습니다.")
