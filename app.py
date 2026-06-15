import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 페이지 설정
st.set_page_config(layout="wide", page_title="내 자산 실시간 레이더")
st.title("📊 내 보유 자산 실시간 진단 및 전략 대시보드")

# [실제 보유 포트폴리오 데이터 세팅 - SK하이닉스 평단가 200만 원 반영]
MY_PORTFOLIO = [
    {"name": "SOL AI반도체TOP2", "code": "479810.KS", "buy_price": 20964, "qty": 48, "currency": "원"},
    {"name": "SK하이닉스", "code": "000660.KS", "buy_price": 2000000, "qty": 2, "currency": "원"},
    {"name": "미국 나스닥 ETF(QQQ)", "code": "QQQ", "buy_price": 38, "qty": 61, "currency": "$"},
    {"name": "미국 에너지 ETF(ICLN)", "code": "ICLN", "buy_price": 5.5, "qty": 7, "currency": "$"}
]

# [시장 스캐너 감시 리스트]
WATCH_LIST = [
    {"name": "제노코", "code": "361390.KQ", "sector": "우주항공/방산"},
    {"name": "한국항공우주", "code": "047810.KS", "sector": "우주항공/방산"},
    {"name": "한화에어로스페이스", "code": "012450.KS", "sector": "우주항공/방산"},
    {"name": "한화시스템", "code": "272210.KS", "sector": "우주항공/방산"},
    {"name": "LIG넥스원", "code": "079550.KS", "sector": "우주항공/방산"},
    {"name": "우리로", "code": "046970.KQ", "sector": "양자컴퓨팅"},
    {"name": "엑스게이트", "code": "433320.KQ", "sector": "양자컴퓨팅"},
    {"name": "케이씨에스", "code": "079220.KQ", "sector": "양자컴퓨팅"},
    {"name": "HD현대중공업", "code": "329180.KS", "sector": "조선"},
    {"name": "삼성중공업", "code": "010140.KS", "sector": "조선"},
    {"name": "한화오션", "code": "042660.KS", "sector": "조선"},
    {"name": "LS ELECTRIC", "code": "010120.KS", "sector": "전력인프라"},
    {"name": "HD현대일렉트릭", "code": "267260.KS", "sector": "전력인프라"},
    {"name": "삼성전자", "code": "005930.KS", "sector": "반도체"},
    {"name": "SK하이닉스", "code": "000660.KS", "sector": "반도체"}
]

# 2. 사이드바 제어 컨트롤러
st.sidebar.header("🕹️ 세팅 컨트롤러")
current_ticker = st.sidebar.text_input("차트 조회 종목 코드", value="000660.KS") # 기본값을 하이닉스로 변경
period = st.sidebar.selectbox("데이터 기간", ["3mo", "1y", "1mo", "5d"], index=0)
interval = st.sidebar.selectbox("데이터 봉 주기", ["1d", "15m", "5m", "1m"], index=0)

rsi_window = st.sidebar.slider("RSI 기간", 5, 30, 14)
bb_window = st.sidebar.slider("볼린저 밴드 기간", 5, 50, 20)

# 3. 데이터 로드 및 기술적 지표 계산 함수
@st.cache_data(ttl=45)
def get_stock_data(symbol, p, i):
    try:
        raw_data = yf.download(tickers=symbol, period=p, interval=i, progress=False)
        if raw_data.empty: return pd.DataFrame()
        
        df = pd.DataFrame(index=raw_data.index)
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in raw_data.columns:
                col_data = raw_data[col]
                df[col] = col_data.iloc[:, 0] if isinstance(col_data, pd.DataFrame) else col_data
        
        if len(df) < max(bb_window, rsi_window) + 5: return pd.DataFrame()
        
        # 볼린저 밴드 계산
        ma = df['Close'].rolling(window=bb_window).mean()
        std = df['Close'].rolling(window=bb_window).std()
        df['BB_High'] = ma + (std * 2)
        df['BB_Low'] = ma - (std * 2)
        df['MA20'] = ma
        df['MA20_Vol'] = df['Volume'].rolling(window=20).mean()
        
        # RSI 계산
        delta = df['Close'].diff()
        gain = (delta.clip(lower=0)).rolling(window=rsi_window).mean()
        loss = (-delta.clip(upper=0)).rolling(window=rsi_window).mean()
        rs = gain / (loss + 1e-10)
        df['RSI'] = 100 - (100 / (1 + rs))
        return df
    except:
        return pd.DataFrame()

# 4. 탭 구성
tab1, tab2, tab3 = st.tabs(["💼 실시간 계좌 및 포트폴리오 진단", "📊 종목 상세 차트", "🎯 오늘의 전략별 추천"])

# ==================== TAB 1: 실시간 포트폴리오 진단 ====================
with tab1:
    st.subheader("📋 내 보유 종목 실시간 수익률 및 매매 시그널")
    
    with st.spinner("⏳ 계좌 데이터를 불러와 분석 중입니다..."):
        portfolio_results = []
        for item in MY_PORTFOLIO:
            name, code, buy_p, qty, curr = item["name"], item["code"], item["buy_price"], item["qty"], item["currency"]
            
            d_set = get_stock_data(code, "3mo", "1d")
            if d_set.empty: continue
            
            close_p = float(d_set['Close'].iloc[-1])
            
            # 수익률 계산 및 포맷팅
            profit_pct = ((close_p - buy_p) / buy_p) * 100
            rsi_p = float(d_set['RSI'].iloc[-1])
            bb_h, bb_l = float(d_set['BB_High'].iloc[-1]), float(d_set['BB_Low'].iloc[-1])
            
            # 스마트 매매 진단 시그널
            if rsi_p <= 35 or close_p <= bb_l * 1.01:
                status = "✅ 낙폭과대 (추가매수 타이밍)"
            elif rsi_p >= 68 or close_p >= bb_h * 0.99:
                status = "🚨 고점과열 (분할매도 권장)"
            else:
                status = "⚖️ 정상 범위 (보유 및 관망)"
                
            portfolio_results.append({
                "종목명": name,
                "보유수량": f"{qty}주",
                "평균단가": f"{buy_p:,.2f}{curr}" if curr == "$" else f"{buy_p:,.0f}원",
                "현재가": f"{close_p:,.2f}{curr}" if curr == "$" else f"{close_p:,.0f}원",
                "실시간 수익률": f"{profit_pct:+.2f}%",
                "RSI 점수": f"{rsi_p:.1f}",
                "시스템 매매 진단": status
            })
            
        if portfolio_results:
            st.dataframe(pd.DataFrame(portfolio_results), use_container_width=True)
        else:
            st.info("보유 종목 데이터를 읽어오지 못했습니다.")

# ==================== TAB 2: 종목 상세 차트 ====================
with tab2:
    df = get_stock_data(current_ticker, period, interval)
    if df.empty:
        st.error("⚠️ 데이터를 불러오지 못했습니다. 왼쪽에서 올바른 종목코드를 입력하거나 기간을 늘려주세요.")
    else:
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
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="주가"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_High'], line=dict(color='red', width=1), name="밴드 상한"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_Low'], line=dict(color='blue', width=1), name="밴드 하한"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple', width=1.5), name="RSI"), row=2, col=1)
        fig.add_shape(type="line", x0=df.index[0], y0=70, x1=df.index[-1], y1=70, line=dict(color="red", dash="dash"), row=2, col=1)
        fig.add_shape(type="line", x0=df.index[0], y0=30, x1=df.index[-1], y1=30, line=dict(color="green", dash="dash"), row=2, col=1)
        fig.update_layout(height=450, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

# ==================== TAB 3: 오늘의 전략별 추천 ====================
with tab3:
    st.subheader("🕵️‍♂️ 전 섹터 실시간 전략 스캐너")
    with st.spinner("⏳ 우주항공/방산/양자/조선 스캐닝 중..."):
        rebound_list, value_list, momentum_list = [], [], []
        for item in WATCH_LIST:
            name, code, sec = item["name"], item["code"], item["sector"]
            d_set = get_stock_data(code, "3mo", "1d")
            if d_set.empty: continue
            
            close_p = float(d_set['Close'].iloc[-1])
            rsi_p = float(d_set['RSI'].iloc[-1])
            bb_l = float(d_set['BB_Low'].iloc[-1])
            ma20_p = float(d_set['MA20'].iloc[-1])
            vol_p = float(d_set['Volume'].iloc[-1])
            vol_ma = float(d_set['MA20_Vol'].iloc[-1])
            
            if rsi_p <= 38 or close_p <= bb_l * 1.01:
                rebound_list.append({"섹터": sec, "종목명": name, "코드": code, "현재가": f"{close_p:,.0f}원", "RSI": f"{rsi_p:.1f}"})
            if close_p < ma20_p and rsi_p < 45:
                value_list.append({"섹터": sec, "종목명": name, "코드": code, "현재가": f"{close_p:,.0f}원", "20일선 이격": f"{((close_p-ma20_p)/ma20_p)*100:+.1f}%"})
            if vol_p > vol_ma * 1.2 and close_p > ma20_p:
                momentum_list.append({"섹터": sec, "종목명": name, "코드": code, "현재가": f"{close_p:,.0f}원", "거래량": f"{float(vol_p/vol_ma)*100:.0f}% 폭증"})
        
        st.markdown("### 🟢 1. 단기 낙폭과대 반등 추천")
        st.dataframe(pd.DataFrame(rebound_list) if rebound_list else pd.DataFrame(columns=["알림"]), use_container_width=True)
        st.markdown("### 💎 2. 가성비 구간 우량주 추천")
        st.dataframe(pd.DataFrame(value_list) if value_list else pd.DataFrame(columns=["알림"]), use_container_width=True)
        st.markdown("### 🔥 3. 거래량 폭발 섹터 주도주 추천")
        st.dataframe(pd.DataFrame(momentum_list) if momentum_list else pd.DataFrame(columns=["알림"]), use_container_width=True)
