import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(
    page_title="디지털 자산 모니터링",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
.metric-card { background:#fff; border-radius:10px; border:1px solid #e8e8e8; padding:16px 20px; }
.stMetric { background:#fff; border-radius:10px; border:1px solid #e8e8e8; padding:12px; }
</style>
""", unsafe_allow_html=True)

# ================================================================
# 데이터 수집 함수
# ================================================================

@st.cache_data(ttl=3600)
def get_upbit_markets():
    try:
        r = requests.get("https://api.upbit.com/v1/market/all", timeout=10)
        data = r.json()
        rows = []
        for item in data:
            if item['market'].startswith('KRW-'):
                rows.append({
                    '심볼': item['market'],
                    '이름': item['korean_name'],
                    '거래소': '업비트',
                    '상태': 'active'
                })
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"업비트 수집 오류: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_bithumb_markets():
    try:
        r = requests.get("https://api.bithumb.com/public/ticker/ALL_KRW", timeout=10)
        data = r.json().get('data', {})
        rows = []
        for symbol, info in data.items():
            if symbol == 'date':
                continue
            rows.append({
                '심볼': f'KRW-{symbol}',
                '이름': symbol,
                '거래소': '빗썸',
                '상태': 'active'
            })
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"빗썸 수집 오류: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_coinone_markets():
    try:
        r = requests.get("https://api.coinone.co.kr/public/v2/markets/KRW", timeout=10)
        data = r.json().get('markets', [])
        rows = []
        for item in data:
            symbol = item.get('target_currency', '').upper()
            rows.append({
                '심볼': f'KRW-{symbol}',
                '이름': symbol,
                '거래소': '코인원',
                '상태': 'active'
            })
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"코인원 수집 오류: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_korbit_markets():
    try:
        r = requests.get("https://api.korbit.co.kr/v1/ticker/detailed/all", timeout=10)
        data = r.json()
        rows = []
        for pair in data:
            if not pair.endswith('_krw'):
                continue
            symbol = pair.replace('_krw', '').upper()
            rows.append({
                '심볼': f'KRW-{symbol}',
                '이름': symbol,
                '거래소': '코빗',
                '상태': 'active'
            })
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"코빗 수집 오류: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_prices():
    markets = ['KRW-BTC', 'KRW-ETH', 'KRW-XRP', 'KRW-SOL']
    try:
        r = requests.get(
            f"https://api.upbit.com/v1/ticker?markets={','.join(markets)}",
            timeout=10
        )
        data = r.json()
        rows = []
        names = {'KRW-BTC': '비트코인', 'KRW-ETH': '이더리움', 'KRW-XRP': '리플', 'KRW-SOL': '솔라나'}
        for item in data:
            rows.append({
                '심볼': item['market'],
                '이름': names.get(item['market'], item['market']),
                '현재가': item['trade_price'],
                '시가': item['opening_price'],
                '고가': item['high_price'],
                '저가': item['low_price'],
                '거래량': item['acc_trade_volume_24h'],
                '거래대금': item['acc_trade_price_24h'],
                '전일대비(%)': round(item['signed_change_rate'] * 100, 2)
            })
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"시세 수집 오류: {e}")
        return pd.DataFrame()

# ================================================================
# 메인 UI
# ================================================================

st.title("📊 디지털 자산 모니터링")
st.caption(f"최종 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 새로고침 버튼
if st.button("🔄 데이터 새로고침"):
    st.cache_data.clear()
    st.rerun()

st.divider()

# 데이터 로딩
with st.spinner("데이터 수집 중..."):
    df_upbit   = get_upbit_markets()
    df_bithumb = get_bithumb_markets()
    df_coinone = get_coinone_markets()
    df_korbit  = get_korbit_markets()
    df_prices  = get_prices()

# 전체 종목 합치기
df_all = pd.concat([df_upbit, df_bithumb, df_coinone, df_korbit], ignore_index=True)

# ================================================================
# 요약 지표
# ================================================================

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("전체 상장 종목", f"{len(df_all):,}개")
with col2:
    st.metric("업비트", f"{len(df_upbit):,}개")
with col3:
    st.metric("빗썸", f"{len(df_bithumb):,}개")
with col4:
    st.metric("코인원 + 코빗", f"{len(df_coinone) + len(df_korbit):,}개")

st.divider()

# ================================================================
# 탭 구성
# ================================================================

tab1, tab2, tab3 = st.tabs(["📈 거래소 현황", "💰 주요 종목 시세", "🔍 종목 검색"])

# ── 탭 1: 거래소 현황 ──
with tab1:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("거래소별 상장 종목 수")
        exchange_count = df_all.groupby('거래소').size().reset_index(name='종목수')
        fig1 = px.bar(
            exchange_count,
            x='거래소', y='종목수',
            color='거래소',
            color_discrete_sequence=['#6366f1', '#0ea5e9', '#10b981', '#f59e0b'],
            text='종목수'
        )
        fig1.update_traces(textposition='outside')
        fig1.update_layout(showlegend=False, height=350, margin=dict(t=20, b=20))
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.subheader("거래소별 비율")
        fig2 = px.pie(
            exchange_count,
            names='거래소', values='종목수',
            color_discrete_sequence=['#6366f1', '#0ea5e9', '#10b981', '#f59e0b'],
            hole=0.4
        )
        fig2.update_layout(height=350, margin=dict(t=20, b=20))
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("거래소별 종목 목록")
    selected_exchange = st.selectbox(
        "거래소 선택",
        ['전체', '업비트', '빗썸', '코인원', '코빗']
    )
    if selected_exchange == '전체':
        st.dataframe(df_all, use_container_width=True, height=400)
    else:
        st.dataframe(
            df_all[df_all['거래소'] == selected_exchange],
            use_container_width=True, height=400
        )

# ── 탭 2: 주요 종목 시세 ──
with tab2:
    st.subheader("주요 종목 시세 (업비트 기준)")

    if not df_prices.empty:
        # 시세 카드
        cols = st.columns(4)
        for i, row in df_prices.iterrows():
            with cols[i]:
                change = row['전일대비(%)']
                delta_color = "normal" if change >= 0 else "inverse"
                st.metric(
                    label=f"{row['이름']} ({row['심볼']})",
                    value=f"{row['현재가']:,}원",
                    delta=f"{change:+.2f}%"
                )

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("전일대비 등락률")
            colors = ['#10b981' if x >= 0 else '#ef4444' for x in df_prices['전일대비(%)']]
            fig3 = go.Figure(go.Bar(
                x=df_prices['이름'],
                y=df_prices['전일대비(%)'],
                marker_color=colors,
                text=[f"{v:+.2f}%" for v in df_prices['전일대비(%)']],
                textposition='outside'
            ))
            fig3.update_layout(
                height=320,
                margin=dict(t=20, b=20),
                yaxis_title="등락률 (%)"
            )
            st.plotly_chart(fig3, use_container_width=True)

        with col2:
            st.subheader("24시간 거래대금")
            df_prices['거래대금(억)'] = (df_prices['거래대금'] / 1e8).round(1)
            fig4 = px.bar(
                df_prices,
                x='이름', y='거래대금(억)',
                color='이름',
                color_discrete_sequence=['#6366f1', '#0ea5e9', '#10b981', '#f59e0b'],
                text='거래대금(억)'
            )
            fig4.update_traces(textposition='outside', texttemplate='%{text:.0f}억')
            fig4.update_layout(showlegend=False, height=320, margin=dict(t=20, b=20))
            st.plotly_chart(fig4, use_container_width=True)

        st.subheader("상세 시세 데이터")
        display_df = df_prices[['이름', '심볼', '현재가', '시가', '고가', '저가', '전일대비(%)']].copy()
        display_df['현재가'] = display_df['현재가'].apply(lambda x: f"{x:,}")
        display_df['시가']   = display_df['시가'].apply(lambda x: f"{x:,}")
        display_df['고가']   = display_df['고가'].apply(lambda x: f"{x:,}")
        display_df['저가']   = display_df['저가'].apply(lambda x: f"{x:,}")
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.warning("시세 데이터를 불러올 수 없어요.")

# ── 탭 3: 종목 검색 ──
with tab3:
    st.subheader("종목 검색")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("심볼 또는 이름 검색", placeholder="예: BTC, 비트코인, ETH...")
    with col2:
        exchange_filter = st.selectbox("거래소", ['전체', '업비트', '빗썸', '코인원', '코빗'])

    filtered = df_all.copy()
    if query:
        filtered = filtered[
            filtered['심볼'].str.contains(query.upper(), na=False) |
            filtered['이름'].str.contains(query, na=False)
        ]
    if exchange_filter != '전체':
        filtered = filtered[filtered['거래소'] == exchange_filter]

    st.caption(f"검색 결과: {len(filtered)}개")
    st.dataframe(filtered, use_container_width=True, height=500, hide_index=True)
