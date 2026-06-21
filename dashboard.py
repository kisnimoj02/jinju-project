"""
진주시 무단투기 민원 × CCTV 사각지대 분석 대시보드
실행: streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ── 페이지 설정 ───────────────────────────────────────
st.set_page_config(
    page_title="진주시 무단투기 CCTV 사각지대 분석",
    page_icon="🗑️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── 다크모드 CSS ──────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    section[data-testid="stSidebar"] { background-color: #1a1d27; }
    .metric-card {
        background-color: #1e2130;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        border: 1px solid #2e3250;
    }
    .metric-value { font-size: 2rem; font-weight: bold; }
    .metric-label { font-size: 0.9rem; color: #a0a0b0; margin-top: 4px; }
    .red   { color: #ff4b4b; }
    .orange{ color: #ffa64d; }
    .blue  { color: #4b9eff; }
    .green { color: #4bcc7a; }
    h1, h2, h3 { color: #ffffff; }
</style>
""", unsafe_allow_html=True)

# ── 데이터 로드 ───────────────────────────────────────
BASE = Path(__file__).parent

@st.cache_data
def load_data():
    spots    = pd.read_csv(BASE / "data/processed/vulnerable_spots.csv", encoding="utf-8-sig")
    stats    = pd.read_csv(BASE / "data/processed/dong_stats.csv",       encoding="utf-8-sig")
    cctv     = pd.read_csv(BASE / "data/processed/cctv_geocoded.csv",    encoding="utf-8-sig")
    wonroom  = pd.read_csv(BASE / "data/processed/wonroom_area.csv",     encoding="utf-8-sig")
    return spots, stats, cctv, wonroom

spots, stats, cctv, wonroom = load_data()

# 읍면동 목록
dong_list = sorted([d for d in spots["읍면동"].unique() if d != "알수없음"])

# ── 사이드바 ──────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ 보기 설정")
    st.markdown("---")

    selected_dong = st.multiselect(
        "읍면동 필터",
        options=["전체"] + dong_list,
        default=["전체"]
    )

    radius = st.slider("취약 지점 판단 반경 (m)", 50, 200, 100, step=10)

    show_cctv       = st.checkbox("CCTV 위치 표시",    value=True)
    show_complaints = st.checkbox("민원 위치 표시",    value=True)
    show_vulnerable = st.checkbox("취약 지점 강조",    value=True)

    st.markdown("---")
    st.markdown("**데이터 출처**")
    st.caption("· 경상남도 진주시 CCTV 위치정보")
    st.caption("· 경상남도 진주시 쓰레기 무단투기 신고정보")
    st.caption("· 행정동별 연령별 주민등록 인구현황")

# ── 데이터 필터링 ─────────────────────────────────────
if "전체" in selected_dong or not selected_dong:
    filtered = spots.copy()
else:
    filtered = spots[spots["읍면동"].isin(selected_dong)].copy()

# 반경 기준 재계산
filtered["취약지점여부"] = (filtered["최근접CCTV거리(m)"] > radius).astype(int)
vulnerable = filtered[filtered["취약지점여부"] == 1]

# ── 타이틀 ───────────────────────────────────────────
st.markdown("# 🗑️ 진주시 무단투기 × CCTV 사각지대 분석")
st.markdown("무단투기 민원 발생 위치와 CCTV 설치 현황을 교차 분석하여 감시 인프라 취약 지점을 도출합니다.")
st.markdown("---")

# ── KPI 카드 ──────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value red">{len(filtered)}</div>
        <div class="metric-label">총 민원 건수</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value orange">{len(vulnerable)}</div>
        <div class="metric-label">취약 지점 건수</div>
    </div>""", unsafe_allow_html=True)
with c3:
    pct = round(len(vulnerable) / len(filtered) * 100, 1) if len(filtered) > 0 else 0
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value orange">{pct}%</div>
        <div class="metric-label">취약 지점 비율</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value blue">{len(cctv)}</div>
        <div class="metric-label">CCTV 설치 수</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── 탭 구성 ──────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🗺️ 인터랙티브 지도", "📊 통계 분석", "📋 취약 지점 목록"])

# ════════════════════════════════════════════════════
# TAB 1: 지도
# ════════════════════════════════════════════════════
with tab1:
    st.markdown("### 민원 발생 × CCTV 분포 지도")
    st.caption("🔴 취약 지점(CCTV 없음)  🟡 일반 민원  🔵 CCTV 위치")

    m = folium.Map(
        location=[35.18, 128.11],
        zoom_start=13,
        tiles="CartoDB dark_matter"
    )

    # CCTV 마커
    if show_cctv:
        cctv_valid = cctv.dropna(subset=["위도", "경도"])
        for _, row in cctv_valid.iterrows():
            folium.CircleMarker(
                location=[row["위도"], row["경도"]],
                radius=4,
                color="#4b9eff",
                fill=True,
                fill_opacity=0.6,
                popup=f"CCTV: {row.get('설치장소','')}<br>목적: {row.get('목적','')}",
            ).add_to(m)

    # 민원 마커
    if show_complaints:
        comp_valid = filtered.dropna(subset=["lat", "lng"])
        for _, row in comp_valid.iterrows():
            is_vuln = row["취약지점여부"] == 1
            if is_vuln and show_vulnerable:
                color, radius_m, opacity = "#ff4b4b", 8, 0.9
            else:
                color, radius_m, opacity = "#ffa64d", 5, 0.7

            folium.CircleMarker(
                location=[row["lat"], row["lng"]],
                radius=radius_m,
                color=color,
                fill=True,
                fill_opacity=opacity,
                popup=(
                    f"<b>{'⚠️ 취약 지점' if is_vuln else '민원'}</b><br>"
                    f"주소: {row.get('위반장소','')}<br>"
                    f"날짜: {row.get('위반일자','')}<br>"
                    f"최근접 CCTV: {row.get('최근접CCTV거리(m)', '')}m"
                ),
            ).add_to(m)

    st_folium(m, width="100%", height=550)

# ════════════════════════════════════════════════════
# TAB 2: 통계
# ════════════════════════════════════════════════════
with tab2:
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("### 읍면동별 민원 건수")
        dong_filtered = stats[stats["읍면동"] != "알수없음"].copy()
        fig1 = px.bar(
            dong_filtered.sort_values("민원건수", ascending=True).tail(15),
            x="민원건수", y="읍면동",
            orientation="h",
            color="취약건수",
            color_continuous_scale=["#1e2130", "#ff4b4b"],
            labels={"민원건수": "민원 건수", "취약건수": "취약 건수"},
            template="plotly_dark"
        )
        fig1.update_layout(
            plot_bgcolor="#0e1117",
            paper_bgcolor="#0e1117",
            height=420,
            margin=dict(l=10, r=10, t=10, b=10)
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col_b:
        st.markdown("### 읍면동별 취약 비율 (%)")
        dong_top = dong_filtered[dong_filtered["민원건수"] >= 3].sort_values("취약비율(%)", ascending=True).tail(15)
        fig2 = px.bar(
            dong_top,
            x="취약비율(%)", y="읍면동",
            orientation="h",
            color="취약비율(%)",
            color_continuous_scale=["#4b9eff", "#ff4b4b"],
            template="plotly_dark"
        )
        fig2.update_layout(
            plot_bgcolor="#0e1117",
            paper_bgcolor="#0e1117",
            height=420,
            margin=dict(l=10, r=10, t=10, b=10)
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### 20대 인구 비율 vs 취약 건수")
    scatter_data = dong_filtered.dropna(subset=["20대_비율(%)"])
    fig3 = px.scatter(
        scatter_data,
        x="20대_비율(%)", y="취약건수",
        size="민원건수", color="원룸촌여부",
        hover_name="읍면동",
        color_continuous_scale=["#4b9eff", "#ff4b4b"],
        labels={"20대_비율(%)": "20대 인구 비율 (%)", "취약건수": "취약 지점 건수"},
        template="plotly_dark"
    )
    fig3.update_layout(
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        height=380,
        margin=dict(l=10, r=10, t=10, b=10)
    )
    st.plotly_chart(fig3, use_container_width=True)

# ════════════════════════════════════════════════════
# TAB 3: 취약 지점 테이블
# ════════════════════════════════════════════════════
with tab3:
    st.markdown("### ⚠️ 취약 지점 목록 (CCTV 미설치 구간)")
    st.caption(f"반경 {radius}m 내 CCTV 없는 민원 발생 지점")

    vuln_display = vulnerable[["위반장소", "읍면동", "위반일자", "최근접CCTV거리(m)"]].copy()
    vuln_display = vuln_display.sort_values("최근접CCTV거리(m)", ascending=False).reset_index(drop=True)
    vuln_display.index += 1
    vuln_display.columns = ["주소", "읍면동", "위반일자", "최근접CCTV거리(m)"]

    st.dataframe(
        vuln_display,
        use_container_width=True,
        height=500
    )

    st.markdown(f"**총 {len(vuln_display)}건**")

    csv = vuln_display.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        label="📥 취약 지점 CSV 다운로드",
        data=csv,
        file_name="vulnerable_spots_export.csv",
        mime="text/csv"
    )
