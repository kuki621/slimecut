import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import plotly.graph_objects as go

# Streamlit 앱 제목
st.title("배당 확인기")

# 실시간 원/달러 환율 가져오기
def get_usd_to_krw_rate():
    try:
        response = requests.get("https://api.exchangerate-api.com/v4/latest/USD")
        data = response.json()
        return data['rates']['KRW']
    except Exception as e:
        st.error(f"환율 정보를 가져오는 데 실패했습니다: {e}")
        return None

# 종목 티커와 이름 매핑 (예시)
stock_mapping = {
    "애플": "AAPL",
    "마이크로소프트": "MSFT",
    "테슬라": "TSLA",
    "삼성전자": "005930.KS",
    "네이버": "035420.KQ"
}

# 세금 공제 비율 (미국 주식 기준, 예시로 15%)
WITHHOLDING_TAX_RATE = 0.15

# 검색창 만들기
ticker_input = st.text_input("종목 이름 또는 티커를 입력하세요 (예: 애플, AAPL):")

if ticker_input:
    try:
        # 입력값 기반으로 매칭된 티커 가져오기
        ticker = stock_mapping.get(ticker_input, ticker_input)

        # yfinance를 사용해 티커 데이터 가져오기
        stock = yf.Ticker(ticker)

        # 종목 정보 가져오기
        info = stock.info
        st.subheader(f"{ticker_input.upper()}의 종목 정보")
        st.write(f"**회사 이름:** {info.get('shortName', '정보 없음')}")
        
        st.write(f"**시가총액:** {info.get('marketCap', '정보 없음'):,} USD (약 {info.get('marketCap', '정보 없음') / 1000000000:.2f} 억 달러)")
        st.write(f"**발행 주식 수:** {info.get('sharesOutstanding', '정보 없음'):,} 주")

        # 차트 기간 선택
        timeframe_options = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"]
        timeframe = st.selectbox("차트 기간을 선택하세요:", timeframe_options, index=5)

        # 주가 데이터 가져오기
        history = stock.history(period=timeframe, interval="1d")

        if history.empty:
            st.warning("이 종목에 대한 데이터가 없습니다.")
        else:
            # 현재 주가 가져오기
            current_price = history.iloc[-1]['Close']

            # 실시간 차트 생성
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=history.index,
                open=history['Open'],
                high=history['High'],
                low=history['Low'],
                close=history['Close'],
                name="Price"
            ))
            fig.update_layout(
                title=f"{ticker_input.upper()}의 {timeframe} 차트",
                xaxis_title="날짜",
                yaxis_title="주가 (USD)",
                xaxis_rangeslider_visible=True
            )

            st.subheader(f"{ticker_input.upper()}의 현재 주가")
            st.write(f"**현재 주가**: {current_price:.2f} USD")
            st.plotly_chart(fig)

            # 배당 데이터 가져오기
            dividends = stock.dividends

            if dividends.empty:
                st.warning("이 종목에 대한 배당 정보가 없습니다.")
            else:
                # 최근 배당 데이터 표시
                last_dividend_date = dividends.index[-1].strftime('%Y-%m-%d')
                last_dividend_amount = round(dividends.iloc[-1], 2)

                # 배당률 계산
                dividend_yield = round((last_dividend_amount / current_price) * 100, 2)

                # 실시간 환율 가져오기
                usd_to_krw_rate = get_usd_to_krw_rate()

                if usd_to_krw_rate:
                    last_dividend_amount_krw = round(last_dividend_amount * usd_to_krw_rate)

                    st.subheader(f"{ticker_input.upper()}의 배당 정보")
                    st.write(f"**배당락일**: {last_dividend_date}")
                    st.write(f"**최근 배당금**: {last_dividend_amount} USD / {last_dividend_amount_krw} KRW")
                    st.write(f"**배당 수익률**: {dividend_yield}%")

                    # 디버깅: 배당 데이터의 시작 날짜 표시
                    min_date = dividends.index.min()
                    st.write(f"**배당 데이터 시작 날짜:** {min_date}")

                    # 역대 배당 데이터를 표로 표시 (최근 10년치 데이터로 제한)
                    dividends_krw = dividends * usd_to_krw_rate
                    dividends_after_tax = dividends_krw * (1 - WITHHOLDING_TAX_RATE)
                    dividends_df = pd.DataFrame({
                        "배당락일": dividends.index.strftime('%Y-%m-%d'),
                        "배당금 (USD)": dividends.values.round(2),
                        "배당금 (KRW)": dividends_krw.values.round(),
                        "세후 배당금 (KRW)": dividends_after_tax.values.round()
                    })
                    dividends_df = dividends_df.sort_values(by="배당락일", ascending=False)

                    # 10년치 데이터로 필터링
                    last_10_years = pd.Timestamp.now() - pd.DateOffset(years=10)
                    dividends_df = dividends_df[pd.to_datetime(dividends_df["배당락일"]) >= last_10_years]

                    st.subheader("역대 배당 내역")
                    st.dataframe(dividends_df)

                else:
                    st.warning("환율 정보를 가져올 수 없어 원화 환산 금액을 표시할 수 없습니다.")
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
else:
    st.info("종목 이름 또는 티커를 입력하면 배당 정보를 확인할 수 있습니다.")

st.markdown("**Made by Kuki**")
