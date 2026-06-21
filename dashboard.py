"""
진주시 무단투기 민원 × CCTV 사각지대 분석 대시보드
실행: streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import requests
import re
from math import radians, cos, sin, asin, sqrt

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
    .question-box {
        background: linear-gradient(135deg, #1e2130, #2a1f3d);
        border-left: 4px solid #ff4b4b;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 16px;
    }
    .question-box h3 { color: #ff4b4b; margin: 0 0 6px 0; font-size: 1rem; }
    .question-box p  { color: #e0e0e0; margin: 0; font-size: 1.05rem; font-weight: 500; }
    h1, h2, h3 { color: #ffffff; }
</style>
""", unsafe_allow_html=True)

# ── 데이터 로드 ───────────────────────────────────────
BASE = Path(__file__).parent

@st.cache_data
def load_data():
    spots   = pd.read_csv(BASE / "vulnerable_spots.csv",  encoding="utf-8-sig")
    stats   = pd.read_csv(BASE / "dong_stats.csv",        encoding="utf-8-sig")
    cctv    = pd.read_csv(BASE / "cctv_geocoded.csv",     encoding="utf-8-sig")
    wonroom = pd.read_csv(BASE / "wonroom_area.csv",      encoding="utf-8-sig")
    return spots, stats, cctv, wonroom

spots, stats, cctv, wonroom = load_data()

def extract_dong(address):
    if not isinstance(address, str):
        return "알수없음"
    match = re.search(r'([가-힣]+[읍면동리])', address)
    return match.group(1) if match else "알수없음"

def haversine(lat1, lng1, lat2, lng2):
    R = 6371000
    p1, p2 = radians(lat1), radians(lat2)
    dp = radians(lat2-lat1); dl = radians(lng2-lng1)
    a = sin(dp/2)**2 + cos(p1)*cos(p2)*sin(dl/2)**2
    return R * 2 * asin(sqrt(a))

dong_list = sorted([d for d in spots["읍면동"].unique() if d != "알수없음"])

# ── 사이드바 ──────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ 보기 설정")
    st.markdown("---")
    selected_dong = st.multiselect("읍면동 필터", options=["전체"] + dong_list, default=["전체"])
    radius = st.slider("취약 지점 판단 반경 (m)", 50, 200, 100, step=10)
    st.markdown("---")
    show_cctv       = st.checkbox("CCTV 위치 표시",  value=True)
    show_complaints = st.checkbox("민원 위치 표시",  value=True)
    show_vulnerable = st.checkbox("취약 지점 강조",  value=True)
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

filtered["취약지점여부"] = (filtered["최근접CCTV거리(m)"] > radius).astype(int)
vulnerable = filtered[filtered["취약지점여부"] == 1]

# ── 타이틀 & 핵심 질문 ───────────────────────────────
st.markdown("# 🗑️ 진주시 무단투기 × CCTV 사각지대 분석")
st.markdown("""
<div class="question-box">
  <h3>📌 핵심 의사결정 질문</h3>
  <p>20대 1인가구 밀집 원룸촌에서 무단투기 민원이 집중되는 지점은 CCTV 사각지대와 일치하는가?<br>
  → 데이터로 취약 지점을 특정하여 <b>CCTV 추가 설치 우선순위</b>를 제안한다.</p>
</div>
""", unsafe_allow_html=True)
st.markdown("---")

# ── KPI 카드 ──────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
pct = round(len(vulnerable) / len(filtered) * 100, 1) if len(filtered) > 0 else 0
wonroom_vuln = 0
if "원룸촌여부" in stats.columns:
    wr = stats[stats["원룸촌여부"] == 1]
    wonroom_vuln = int(wr["취약건수"].sum()) if not wr.empty else 0

with c1:
    st.markdown(f'<div class="metric-card"><div class="metric-value red">{len(filtered)}</div><div class="metric-label">총 민원 건수</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-card"><div class="metric-value orange">{len(vulnerable)}</div><div class="metric-label">CCTV 사각지대 민원</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="metric-card"><div class="metric-value orange">{pct}%</div><div class="metric-label">사각지대 비율</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="metric-card"><div class="metric-value blue">{wonroom_vuln}</div><div class="metric-label">원룸촌 내 취약 민원</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── 탭 구성 ──────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["🗺️ 인터랙티브 지도", "📊 통계 분석", "💡 CCTV 설치 시뮬레이션", "📋 취약 지점 목록"])

# ════════════════════════════════════════════════════
# TAB 1: 지도 (plotly mapbox - 빠름)
# ════════════════════════════════════════════════════
with tab1:
    st.markdown("### 민원 발생 × CCTV 분포 지도")
    st.caption("🔴 취약 지점(사각지대)  🟡 일반 민원  🔵 CCTV 위치")

    fig_map = go.Figure()

    # CCTV 레이어
    if show_cctv:
        cctv_v = cctv.dropna(subset=["위도","경도"])
        fig_map.add_trace(go.Scattermapbox(
            lat=cctv_v["위도"], lon=cctv_v["경도"],
            mode="markers",
            marker=dict(size=6, color="#4b9eff", opacity=0.7),
            name="CCTV",
            text=cctv_v.get("설치장소", ""),
            hovertemplate="📷 CCTV<br>%{text}<extra></extra>",
        ))

    # 일반 민원 레이어
    if show_complaints:
        normal = filtered[(filtered["취약지점여부"] == 0)].dropna(subset=["lat","lng"])
        fig_map.add_trace(go.Scattermapbox(
            lat=normal["lat"], lon=normal["lng"],
            mode="markers",
            marker=dict(size=8, color="#ffa64d", opacity=0.8),
            name="일반 민원",
            text=normal.get("위반장소", ""),
            hovertemplate="🟡 민원<br>%{text}<br>날짜: %{customdata}<extra></extra>",
            customdata=normal.get("위반일자", ""),
        ))

    # 취약 지점 레이어
    if show_vulnerable:
        vuln_v = vulnerable.dropna(subset=["lat","lng"])
        fig_map.add_trace(go.Scattermapbox(
            lat=vuln_v["lat"], lon=vuln_v["lng"],
            mode="markers",
            marker=dict(size=12, color="#ff4b4b", opacity=0.9),
            name="⚠️ 사각지대",
            text=vuln_v.get("위반장소", ""),
            hovertemplate="⚠️ 사각지대<br>%{text}<br>최근접 CCTV: %{customdata}m<extra></extra>",
            customdata=vuln_v.get("최근접CCTV거리(m)", ""),
        ))

    fig_map.update_layout(
        mapbox=dict(
            style="carto-darkmatter",
            center=dict(lat=35.18, lon=128.11),
            zoom=12,
        ),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        margin=dict(l=0, r=0, t=0, b=0),
        height=560,
        legend=dict(
            bgcolor="#1e2130", font=dict(color="white"),
            x=0.01, y=0.99,
        ),
    )
    st.plotly_chart(fig_map, use_container_width=True)

# ════════════════════════════════════════════════════
# TAB 2: 통계 분석
# ════════════════════════════════════════════════════
with tab2:
    st.markdown("### 원인 분석: 왜 이 지역에 무단투기가 많은가?")
    st.markdown("""
    - 🏠 **1인가구·대학생 밀집** → 분리수거 인식 낮음, 야간 배달 쓰레기 증가
    - 📷 **CCTV 사각지대** → 감시 공백으로 인한 투기 유발
    - 🌙 **야간 시간대 집중** → 단속 인력 부재
    - 🏘️ **원룸촌 골목 구조** → 좁고 어두운 이면도로, 관리 사각
    """)
    st.markdown("---")

    col_a, col_b = st.columns(2)
    dong_f = stats[stats["읍면동"] != "알수없음"].copy()

    with col_a:
        st.markdown("#### 읍면동별 민원 건수")
        fig1 = px.bar(
            dong_f.sort_values("민원건수", ascending=True).tail(15),
            x="민원건수", y="읍면동", orientation="h",
            color="취약건수", color_continuous_scale=["#1e2130","#ff4b4b"],
            template="plotly_dark"
        )
        fig1.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                           height=400, margin=dict(l=10,r=10,t=10,b=10))
        st.plotly_chart(fig1, use_container_width=True)

    with col_b:
        st.markdown("#### 읍면동별 사각지대 비율")
        dong_top = dong_f[dong_f["민원건수"] >= 3].sort_values("취약비율(%)", ascending=True).tail(15)
        fig2 = px.bar(
            dong_top, x="취약비율(%)", y="읍면동", orientation="h",
            color="취약비율(%)", color_continuous_scale=["#4b9eff","#ff4b4b"],
            template="plotly_dark"
        )
        fig2.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                           height=400, margin=dict(l=10,r=10,t=10,b=10))
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("#### 20대 인구 비율 vs 취약 건수 (원룸촌 일치 여부)")
    scatter_data = dong_f.dropna(subset=["20대_비율(%)"])
    scatter_data = scatter_data.copy()
    scatter_data["원룸촌"] = scatter_data["원룸촌여부"].map({1.0:"원룸촌 ✅", 0.0:"비원룸촌"}).fillna("데이터없음")
    fig3 = px.scatter(
        scatter_data, x="20대_비율(%)", y="취약건수",
        size="민원건수", color="원룸촌",
        color_discrete_map={"원룸촌 ✅":"#ff4b4b","비원룸촌":"#4b9eff","데이터없음":"#888"},
        hover_name="읍면동",
        labels={"20대_비율(%)":"20대 인구 비율 (%)","취약건수":"사각지대 민원 건수"},
        template="plotly_dark"
    )
    fig3.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                       height=380, margin=dict(l=10,r=10,t=10,b=10))
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("💡 오른쪽 위로 갈수록 20대가 많고 사각지대도 많은 지역 → CCTV 추가 설치 최우선 대상")

# ════════════════════════════════════════════════════
# TAB 3: CCTV 설치 시뮬레이션
# ════════════════════════════════════════════════════
with tab3:
    st.markdown("### 💡 CCTV 추가 설치 시뮬레이션")
    st.markdown("취약 지점에 CCTV를 설치했을 때 **커버 가능한 민원 건수**를 추정합니다.")

    sim_radius = st.slider("신규 CCTV 커버 반경 (m)", 50, 200, 100, step=10, key="sim")
    max_cctv   = st.slider("추가 설치 CCTV 수", 1, 20, 5)

    vuln_valid = vulnerable.dropna(subset=["lat","lng"]).copy()
    selected_locations = []
    remaining = vuln_valid.copy()

    for _ in range(max_cctv):
        if remaining.empty:
            break
        center = remaining.iloc[0]
        dists = remaining.apply(
            lambda r: haversine(center["lat"], center["lng"], r["lat"], r["lng"]), axis=1
        )
        covered = remaining[dists <= sim_radius]
        selected_locations.append({
            "lat": center["lat"], "lng": center["lng"],
            "커버건수": len(covered),
            "주소": center.get("위반장소","")
        })
        remaining = remaining[dists > sim_radius]

    sim_df = pd.DataFrame(selected_locations)
    total_covered = len(vuln_valid) - len(remaining)
    cover_pct = round(total_covered / len(vuln_valid) * 100, 1) if len(vuln_valid) > 0 else 0

    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown(f'<div class="metric-card"><div class="metric-value orange">{max_cctv}대</div><div class="metric-label">추가 설치 CCTV</div></div>', unsafe_allow_html=True)
    with k2:
        st.markdown(f'<div class="metric-card"><div class="metric-value green">{total_covered}건</div><div class="metric-label">커버 가능 취약 민원</div></div>', unsafe_allow_html=True)
    with k3:
        st.markdown(f'<div class="metric-card"><div class="metric-value green">{cover_pct}%</div><div class="metric-label">사각지대 해소율</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### 신규 CCTV 설치 권장 위치")

    fig_sim = go.Figure()

    # 기존 취약 지점
    fig_sim.add_trace(go.Scattermapbox(
        lat=vuln_valid["lat"], lon=vuln_valid["lng"],
        mode="markers",
        marker=dict(size=8, color="#ff4b4b", opacity=0.7),
        name="취약 지점",
        text=vuln_valid.get("위반장소",""),
        hovertemplate="⚠️ %{text}<extra></extra>",
    ))

    # 신규 CCTV 권장 위치
    if not sim_df.empty:
        fig_sim.add_trace(go.Scattermapbox(
            lat=sim_df["lat"], lon=sim_df["lng"],
            mode="markers+text",
            marker=dict(size=18, color="#4bcc7a", opacity=0.9, symbol="circle"),
            text=[f"📷{i+1}" for i in range(len(sim_df))],
            textposition="middle center",
            name="신규 CCTV 권장",
            customdata=sim_df["커버건수"],
            hovertemplate="📷 신규 CCTV<br>%{customdata}건 커버<extra></extra>",
        ))

    fig_sim.update_layout(
        mapbox=dict(style="carto-darkmatter", center=dict(lat=35.18, lon=128.11), zoom=12),
        paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        margin=dict(l=0,r=0,t=0,b=0), height=480,
        legend=dict(bgcolor="#1e2130", font=dict(color="white"), x=0.01, y=0.99),
    )
    st.plotly_chart(fig_sim, use_container_width=True)

    st.markdown("#### 📋 CCTV 설치 우선순위 목록")
    if not sim_df.empty:
        sim_display = sim_df.copy()
        sim_display.index = range(1, len(sim_display)+1)
        sim_display.index.name = "우선순위"
        st.dataframe(sim_display[["주소","커버건수","lat","lng"]].rename(
            columns={"커버건수":"커버 가능 민원 수","lat":"위도","lng":"경도"}
        ), use_container_width=True)

# ════════════════════════════════════════════════════
# TAB 4: 취약 지점 목록
# ════════════════════════════════════════════════════
with tab4:
    st.markdown(f"### ⚠️ 취약 지점 목록 — 반경 {radius}m 내 CCTV 없는 민원 지점")
    vuln_display = vulnerable[["위반장소","읍면동","위반일자","최근접CCTV거리(m)"]].copy()
    vuln_display = vuln_display.sort_values("최근접CCTV거리(m)", ascending=False).reset_index(drop=True)
    vuln_display.index += 1
    vuln_display.columns = ["주소","읍면동","위반일자","최근접CCTV거리(m)"]
    st.dataframe(vuln_display, use_container_width=True, height=500)
    st.markdown(f"**총 {len(vuln_display)}건**")

    csv = vuln_display.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        label="CSV 다운로드",
        data=csv,
        file_name="vulnerable_spots_export.csv",
        mime="text/csv"
    )
