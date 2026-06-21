"""
진주시 무단투기 민원 × CCTV 사각지대 분석 대시보드
"""

import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import json
import re
from math import radians, cos, sin, asin, sqrt

st.set_page_config(
    page_title="진주시 무단투기 CCTV 사각지대 분석",
    page_icon="🗑️", layout="wide", initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    section[data-testid="stSidebar"] { background-color: #1a1d27; }
    .metric-card {
        background-color: #1e2130; border-radius: 10px;
        padding: 20px; text-align: center; border: 1px solid #2e3250;
    }
    .metric-value { font-size: 2rem; font-weight: bold; }
    .metric-label { font-size: 0.9rem; color: #a0a0b0; margin-top: 4px; }
    .red { color: #ff4b4b; } .orange { color: #ffa64d; }
    .blue { color: #4b9eff; } .green { color: #4bcc7a; }
    .question-box {
        background: linear-gradient(135deg, #1e2130, #2a1f3d);
        border-left: 4px solid #ff4b4b; border-radius: 8px;
        padding: 16px 20px; margin-bottom: 16px;
    }
    .question-box h3 { color: #ff4b4b; margin: 0 0 6px 0; font-size: 1rem; }
    .question-box p  { color: #e0e0e0; margin: 0; font-size: 1.05rem; font-weight: 500; }
    h1, h2, h3 { color: #ffffff; }
</style>
""", unsafe_allow_html=True)

BASE = Path(__file__).parent

@st.cache_data
def load_data():
    spots   = pd.read_csv(BASE / "vulnerable_spots.csv",  encoding="utf-8-sig")
    stats   = pd.read_csv(BASE / "dong_stats.csv",        encoding="utf-8-sig")
    cctv    = pd.read_csv(BASE / "cctv_geocoded.csv",     encoding="utf-8-sig")
    wonroom = pd.read_csv(BASE / "wonroom_area.csv",      encoding="utf-8-sig")
    return spots, stats, cctv, wonroom

@st.cache_data
def load_geojson():
    gj_path = BASE / "jinju_dongs.geojson"
    if gj_path.exists():
        with open(gj_path, encoding="utf-8") as f:
            return json.load(f)
    return None

spots, stats, cctv, wonroom = load_data()
geojson = load_geojson()

def extract_dong(address):
    if not isinstance(address, str): return "알수없음"
    match = re.search(r'([가-힣]+[읍면동리])', address)
    return match.group(1) if match else "알수없음"

def haversine(lat1, lng1, lat2, lng2):
    R = 6371000
    p1, p2 = radians(lat1), radians(lat2)
    dp = radians(lat2-lat1); dl = radians(lng2-lng1)
    a = sin(dp/2)**2 + cos(p1)*cos(p2)*sin(dl/2)**2
    return R * 2 * asin(sqrt(a))

dong_list = sorted([d for d in spots["읍면동"].unique() if d != "알수없음"])

# ── 사이드바 ──
with st.sidebar:
    st.markdown("## ⚙️ 보기 설정")
    st.markdown("---")
    selected_dong = st.multiselect("읍면동 필터", options=["전체"] + dong_list, default=["전체"])
    radius = st.slider("취약 지점 판단 반경 (m)", 50, 200, 100, step=10)
    st.markdown("---")
    show_polygon    = st.checkbox("원룸촌 구역 폴리곤", value=True)
    show_cctv       = st.checkbox("CCTV 위치 표시",    value=True)
    show_complaints = st.checkbox("민원 위치 표시",    value=True)
    show_vulnerable = st.checkbox("취약 지점 강조",    value=True)
    st.markdown("---")
    st.markdown("**데이터 출처**")
    st.caption("· 경상남도 진주시 CCTV 위치정보")
    st.caption("· 경상남도 진주시 쓰레기 무단투기 신고정보")
    st.caption("· 행정동별 연령별 주민등록 인구현황")

# ── 필터링 ──
if "전체" in selected_dong or not selected_dong:
    filtered = spots.copy()
else:
    filtered = spots[spots["읍면동"].isin(selected_dong)].copy()

filtered["취약지점여부"] = (filtered["최근접CCTV거리(m)"] > radius).astype(int)
vulnerable = filtered[filtered["취약지점여부"] == 1]

# ── 타이틀 ──
st.markdown("# 🗑️ 진주시 무단투기 × CCTV 사각지대 분석")
st.markdown("""
<div class="question-box">
  <h3>📌 핵심 의사결정 질문</h3>
  <p>20대 1인가구 밀집 원룸촌에서 무단투기 민원이 집중되는 지점은 CCTV 사각지대와 일치하는가?<br>
  → 데이터로 취약 지점을 특정하여 <b>CCTV 추가 설치 우선순위</b>를 제안한다.</p>
</div>
""", unsafe_allow_html=True)
st.markdown("---")

# ── KPI ──
c1, c2, c3, c4 = st.columns(4)
pct = round(len(vulnerable)/len(filtered)*100, 1) if len(filtered) > 0 else 0
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

tab1, tab2, tab3, tab4 = st.tabs(["🗺️ 인터랙티브 지도", "📊 통계 분석", "💡 CCTV 설치 시뮬레이션", "📋 취약 지점 목록"])

# ════ TAB 1: 지도 ════
with tab1:
    st.markdown("### 민원 발생 × CCTV 분포 지도")
    st.caption("🔴 취약 지점  🟡 일반 민원  🔵 CCTV(클러스터)  🟣 원룸촌 구역")

    m = folium.Map(location=[35.18, 128.10], zoom_start=13, tiles="CartoDB dark_matter")

    # ① 원룸촌 폴리곤 (로컬 GeoJSON)
    if show_polygon and geojson:
        for feature in geojson["features"]:
            is_wr = feature["properties"].get("wonroom", 0) == 1
            name  = feature["properties"].get("name", "")
            folium.GeoJson(
                feature,
                style_function=lambda x, wr=is_wr: {
                    "fillColor":   "#9b59b6" if wr else "#2c3e50",
                    "color":       "#c39bd3" if wr else "#4a4a6a",
                    "weight":      3 if wr else 1,
                    "fillOpacity": 0.55 if wr else 0.10,
                },
                tooltip=folium.Tooltip(f"{'🏠 원룸촌 | ' if is_wr else ''}{name}"),
            ).add_to(m)

    # ② CCTV 클러스터
    if show_cctv:
        cctv_cluster = MarkerCluster(
            options={"maxClusterRadius": 40, "disableClusteringAtZoom": 16}
        ).add_to(m)
        for _, row in cctv.dropna(subset=["위도","경도"]).iterrows():
            folium.CircleMarker(
                location=[row["위도"], row["경도"]],
                radius=4, color="#4b9eff", fill=True, fill_opacity=0.7,
                popup=f"CCTV: {row.get('설치장소','')}<br>목적: {row.get('목적','')}",
            ).add_to(cctv_cluster)

    # ③ 일반 민원
    if show_complaints:
        for _, row in filtered[filtered["취약지점여부"]==0].dropna(subset=["lat","lng"]).iterrows():
            folium.CircleMarker(
                location=[row["lat"], row["lng"]],
                radius=6, color="#ffa64d", fill=True, fill_opacity=0.8,
                popup=f"<b>민원</b><br>{row.get('위반장소','')}<br>{row.get('위반일자','')}",
            ).add_to(m)

    # ④ 취약 지점
    if show_vulnerable:
        for _, row in vulnerable.dropna(subset=["lat","lng"]).iterrows():
            folium.CircleMarker(
                location=[row["lat"], row["lng"]],
                radius=10, color="#ff4b4b", fill=True, fill_opacity=0.9,
                popup=(f"<b>⚠️ 사각지대</b><br>{row.get('위반장소','')}<br>"
                       f"{row.get('위반일자','')}<br>최근접 CCTV: {row.get('최근접CCTV거리(m)','')}m"),
            ).add_to(m)

    folium.LayerControl().add_to(m)
    st_folium(m, width="100%", height=560, returned_objects=[])

# ════ TAB 2: 통계 ════
with tab2:
    st.markdown("### 원인 분석: 왜 이 지역에 무단투기가 많은가?")
    st.markdown("""
    - 🏠 **1인가구·대학생 밀집** → 분리수거 인식 낮음, 야간 배달 쓰레기 증가
    - 📷 **CCTV 사각지대** → 감시 공백으로 인한 투기 유발
    - 🌙 **야간 시간대 집중** → 단속 인력 부재
    - 🏘️ **원룸촌 골목 구조** → 좁고 어두운 이면도로, 관리 사각
    """)
    st.markdown("---")

    dong_f = stats[stats["읍면동"] != "알수없음"].copy()
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### 읍면동별 민원 건수")
        fig1 = px.bar(dong_f.sort_values("민원건수", ascending=True).tail(15),
                      x="민원건수", y="읍면동", orientation="h",
                      color="취약건수", color_continuous_scale=["#1e2130","#ff4b4b"],
                      template="plotly_dark")
        fig1.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                           height=400, margin=dict(l=10,r=10,t=10,b=10))
        st.plotly_chart(fig1, use_container_width=True)

    with col_b:
        st.markdown("#### 읍면동별 사각지대 비율")
        dong_top = dong_f[dong_f["민원건수"]>=3].sort_values("취약비율(%)", ascending=True).tail(15)
        fig2 = px.bar(dong_top, x="취약비율(%)", y="읍면동", orientation="h",
                      color="취약비율(%)", color_continuous_scale=["#4b9eff","#ff4b4b"],
                      template="plotly_dark")
        fig2.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                           height=400, margin=dict(l=10,r=10,t=10,b=10))
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("#### 20대 인구 비율 vs 취약 건수 (원룸촌 일치 여부)")
    sc = dong_f.dropna(subset=["20대_비율(%)"]).copy()
    sc["원룸촌"] = sc["원룸촌여부"].map({1.0:"원룸촌 ✅", 0.0:"비원룸촌"}).fillna("데이터없음")
    fig3 = px.scatter(sc, x="20대_비율(%)", y="취약건수", size="민원건수", color="원룸촌",
                      color_discrete_map={"원룸촌 ✅":"#ff4b4b","비원룸촌":"#4b9eff","데이터없음":"#888"},
                      hover_name="읍면동", template="plotly_dark",
                      labels={"20대_비율(%)":"20대 인구 비율 (%)","취약건수":"사각지대 민원 건수"})
    fig3.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                       height=380, margin=dict(l=10,r=10,t=10,b=10))
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("💡 오른쪽 위로 갈수록 20대가 많고 사각지대도 많은 지역 → CCTV 추가 설치 최우선 대상")

# ════ TAB 3: 시뮬레이션 ════
with tab3:
    st.markdown("### 💡 CCTV 추가 설치 시뮬레이션")
    st.markdown("취약 지점에 CCTV를 설치했을 때 **커버 가능한 민원 건수**를 추정합니다.")

    sim_radius = st.slider("신규 CCTV 커버 반경 (m)", 50, 200, 100, step=10, key="sim")
    max_cctv   = st.slider("추가 설치 CCTV 수", 1, 20, 5)

    vuln_valid = vulnerable.dropna(subset=["lat","lng"]).copy()
    selected_locs = []
    remaining = vuln_valid.copy()

    for _ in range(max_cctv):
        if remaining.empty: break
        center = remaining.iloc[0]
        dists  = remaining.apply(lambda r: haversine(center["lat"],center["lng"],r["lat"],r["lng"]), axis=1)
        covered = remaining[dists <= sim_radius]
        selected_locs.append({"lat":center["lat"],"lng":center["lng"],
                               "커버건수":len(covered),"주소":center.get("위반장소","")})
        remaining = remaining[dists > sim_radius]

    sim_df = pd.DataFrame(selected_locs)
    total_covered = len(vuln_valid) - len(remaining)
    cover_pct = round(total_covered/len(vuln_valid)*100,1) if len(vuln_valid)>0 else 0

    k1,k2,k3 = st.columns(3)
    with k1: st.markdown(f'<div class="metric-card"><div class="metric-value orange">{max_cctv}대</div><div class="metric-label">추가 설치 CCTV</div></div>', unsafe_allow_html=True)
    with k2: st.markdown(f'<div class="metric-card"><div class="metric-value green">{total_covered}건</div><div class="metric-label">커버 가능 취약 민원</div></div>', unsafe_allow_html=True)
    with k3: st.markdown(f'<div class="metric-card"><div class="metric-value green">{cover_pct}%</div><div class="metric-label">사각지대 해소율</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### 신규 CCTV 설치 권장 위치")

    m3 = folium.Map(location=[35.18, 128.10], zoom_start=13, tiles="CartoDB dark_matter")
    for _, row in vuln_valid.iterrows():
        folium.CircleMarker(location=[row["lat"],row["lng"]], radius=6,
                            color="#ff4b4b", fill=True, fill_opacity=0.7,
                            popup=f"취약: {row.get('위반장소','')}").add_to(m3)
    if not sim_df.empty:
        for i, row in sim_df.iterrows():
            folium.Marker(location=[row["lat"],row["lng"]],
                          popup=f"📷 신규 CCTV {i+1}번<br>커버: {row['커버건수']}건",
                          icon=folium.Icon(color="green", icon="camera", prefix="fa")).add_to(m3)
            folium.Circle(location=[row["lat"],row["lng"]], radius=sim_radius,
                          color="#4bcc7a", fill=True, fill_opacity=0.15).add_to(m3)
    st_folium(m3, width="100%", height=460, returned_objects=[])

    st.markdown("#### 📋 CCTV 설치 우선순위 목록")
    if not sim_df.empty:
        sd = sim_df.copy(); sd.index = range(1, len(sd)+1); sd.index.name="우선순위"
        st.dataframe(sd[["주소","커버건수","lat","lng"]].rename(
            columns={"커버건수":"커버 가능 민원 수","lat":"위도","lng":"경도"}), use_container_width=True)

# ════ TAB 4: 목록 ════
with tab4:
    st.markdown(f"### ⚠️ 취약 지점 목록 — 반경 {radius}m 내 CCTV 없는 민원 지점")
    vd = vulnerable[["위반장소","읍면동","위반일자","최근접CCTV거리(m)"]].copy()
    vd = vd.sort_values("최근접CCTV거리(m)", ascending=False).reset_index(drop=True)
    vd.index += 1; vd.columns = ["주소","읍면동","위반일자","최근접CCTV거리(m)"]
    st.dataframe(vd, use_container_width=True, height=500)
    st.markdown(f"**총 {len(vd)}건**")
    csv = vd.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(label="CSV 다운로드", data=csv,
                       file_name="vulnerable_spots_export.csv", mime="text/csv")
