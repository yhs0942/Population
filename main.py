import math
import pandas as pd
import streamlit as st
import plotly.graph_objects as go


# ==================================================
# 1. 페이지 설정 및 디자인
# ==================================================
st.set_page_config(
    page_title="동네별 인구 피라미드",
    page_icon="🏘️",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp { background-color: #FFF9F1; }
    h1, h2, h3 { color: #654535; }
    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #EEDCCB;
        border-radius: 12px;
        padding: 15px;
    }
    .warning-note {
        color: #A33D2D;
        background: #FFF0E9;
        border: 1px solid #E8A18E;
        border-radius: 10px;
        padding: 10px 14px;
        font-weight: 600;
        margin-top: 8px;
    }
    .summary-note {
        background: #FFF1DD;
        border-left: 5px solid #E6A05B;
        border-radius: 8px;
        padding: 14px 16px;
        color: #654535;
        font-size: 16px;
        line-height: 1.7;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==================================================
# 2. 데이터 불러오기
# ==================================================
DATA_URL = (
    "https://raw.githubusercontent.com/"
    "yhs0942/Population/main/"
    "population_ts_yearly_gender.zip"
)


@st.cache_data(show_spinner="인구 데이터를 불러오는 중입니다...")
def load_data():
    # pandas가 URL의 ZIP 파일을 읽고 압축을 자동으로 풉니다.
    data = pd.read_csv(DATA_URL, compression="zip")
    data.columns = data.columns.astype(str).str.strip()

    base_columns = ["연도", "시도", "시군구", "동"]
    missing = [column for column in base_columns if column not in data.columns]
    if missing:
        raise ValueError(
            f"필수 열이 없습니다: {missing}\n"
            f"CSV의 실제 열 이름 일부: {data.columns.tolist()[:30]}"
        )

    data["연도"] = pd.to_numeric(data["연도"], errors="coerce")
    data = data.dropna(subset=["연도"]).copy()
    if data.empty:
        raise ValueError("CSV에 유효한 연도 데이터가 없습니다.")

    # CSV에 실제로 들어 있는 가장 최신 연도만 사용합니다.
    latest_year = int(data["연도"].max())
    data = data[data["연도"] == latest_year].copy()

    for column in ["시도", "시군구", "동"]:
        data[column] = data[column].fillna("").astype(str).str.strip()

    return data, latest_year


try:
    df, latest_year = load_data()
except Exception as error:
    st.error("인구 데이터를 불러오지 못했습니다.")
    st.write("데이터 주소, 인터넷 연결, CSV의 열 이름을 확인해 주세요.")
    st.code(f"{type(error).__name__}: {error}")
    st.stop()


# ==================================================
# 3. 나이별 인구 열 확인
# ==================================================
ages = [f"{age}세" for age in range(100)] + ["100세 이상"]
male_columns = [f"남_{age}" for age in ages]
female_columns = [f"여_{age}" for age in ages]
population_columns = male_columns + female_columns

missing_population = [
    column for column in population_columns if column not in df.columns
]
if missing_population:
    st.error("나이별 인구 열 일부를 찾을 수 없습니다.")
    st.write("누락된 열:", missing_population)
    st.write("CSV의 실제 열 이름:", df.columns.tolist())
    st.stop()

for column in population_columns:
    df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)


# ==================================================
# 4. 제목
# ==================================================
st.title("🏘️ 동네별 인구 피라미드")
st.write(
    "시도 → 시군구 → 동을 차례로 선택하면 "
    "연령별 인구 분포와 인구 지표를 확인할 수 있습니다."
)
st.caption(f"분석 기준 연도: {latest_year}년")


# ==================================================
# 5. 지역 선택 드롭다운 3개
# ==================================================
def reset_sigungu():
    # 시도가 바뀌면 시군구와 동 선택을 다시 설정합니다.
    st.session_state["sigungu"] = None
    st.session_state["dong"] = None


def reset_dong():
    # 시군구가 바뀌면 동 선택을 다시 설정합니다.
    st.session_state["dong"] = None


sido_options = sorted(
    df.loc[df["시도"] != "", "시도"].unique().tolist()
)
if not sido_options:
    st.error("선택할 수 있는 시도 데이터가 없습니다.")
    st.stop()

if st.session_state.get("sido") not in sido_options:
    st.session_state["sido"] = sido_options[0]

col1, col2, col3 = st.columns(3)
with col1:
    selected_sido = st.selectbox(
        "① 시도",
        sido_options,
        key="sido",
        on_change=reset_sigungu,
    )

sido_df = df[df["시도"] == selected_sido]
sigungu_options = sorted(
    sido_df.loc[sido_df["시군구"] != "", "시군구"].unique().tolist()
)
if not sigungu_options:
    st.warning("선택한 시도에 시군구 데이터가 없습니다.")
    st.stop()

if st.session_state.get("sigungu") not in sigungu_options:
    st.session_state["sigungu"] = sigungu_options[0]

with col2:
    selected_sigungu = st.selectbox(
        "② 시군구",
        sigungu_options,
        key="sigungu",
        on_change=reset_dong,
    )

sigungu_df = sido_df[sido_df["시군구"] == selected_sigungu]
dong_options = sorted(
    sigungu_df.loc[sigungu_df["동"] != "", "동"].unique().tolist()
)
if not dong_options:
    st.warning("선택한 시군구에 동·읍·면 데이터가 없습니다.")
    st.stop()

if st.session_state.get("dong") not in dong_options:
    st.session_state["dong"] = dong_options[0]

with col3:
    selected_dong = st.selectbox(
        "③ 동·읍·면",
        dong_options,
        key="dong",
    )


# ==================================================
# 6. 선택한 동네의 인구 집계
# ==================================================
selected_rows = df[
    (df["시도"] == selected_sido)
    & (df["시군구"] == selected_sigungu)
    & (df["동"] == selected_dong)
]
if selected_rows.empty:
    st.warning("선택한 지역의 데이터가 없습니다.")
    st.stop()

# 동일 지역에 행이 여러 개 있으면 나이별 인구를 합산합니다.
area_population = selected_rows[population_columns].sum()
male_population = [float(area_population[column]) for column in male_columns]
female_population = [float(area_population[column]) for column in female_columns]

total_male = sum(male_population)
total_female = sum(female_population)
total_population = total_male + total_female

# 65세 이상 인구: 65세부터 100세 이상까지 합산합니다.
senior_population = sum(male_population[65:]) + sum(female_population[65:])
aging_rate = (
    senior_population / total_population * 100
    if total_population > 0 else 0.0
)

# 0~14세 인구를 '아이' 인구로 정의해 65세 이상 인구와 비교합니다.
child_population = (
    sum(male_population[:15]) + sum(female_population[:15])
)

# 평균연령은 연령별 인구로 가중평균합니다.
# '100세 이상'은 계산을 위해 대표 나이 100세로 간주하므로 근삿값입니다.
weighted_age_sum = sum(
    age * (male_population[age] + female_population[age])
    for age in range(100)
)
weighted_age_sum += 100 * (
    male_population[100] + female_population[100]
)
average_age = (
    weighted_age_sum / total_population
    if total_population > 0 else 0.0
)


# ==================================================
# 7. 지표 카드 3개: 그래프 위에 표시
# ==================================================
st.divider()
st.subheader("📊 우리 동네 핵심 지표")

card1, card2, card3 = st.columns(3)

with card1:
    st.metric("총인구", f"{total_population:,.0f}명")

with card2:
    st.metric("평균연령", f"{average_age:.1f}세")
    st.caption("※ 100세 이상은 100세로 계산한 근삿값입니다.")

with card3:
    st.metric("고령화율 (65세 이상)", f"{aging_rate:.1f}%")
    # 고령화율이 20%를 초과할 때 카드 바로 아래에 주의 표시를 붙입니다.
    if aging_rate > 20:
        st.markdown(
            '<div class="warning-note">⚠️ 주의: 고령화율이 20%를 넘습니다.</div>',
            unsafe_allow_html=True,
        )


# ==================================================
# 8. 인구 피라미드 그래프
# ==================================================
st.divider()
st.subheader("👥 연령별 인구 피라미드")

# 남성 인구는 음수로 만들어 왼쪽에 표시합니다.
male_values = [-value for value in male_population]
# 여성 인구는 양수 그대로 오른쪽에 표시합니다.
female_values = female_population

largest = max(
    max(male_population, default=0),
    max(female_population, default=0),
    1,
)
tick_step = max(1, math.ceil(largest / 5))
axis_limit = tick_step * 5
tick_values = list(range(-axis_limit, axis_limit + 1, tick_step))
tick_text = [f"{abs(value):,.0f}" for value in tick_values]

fig = go.Figure()

fig.add_trace(
    go.Bar(
        name="남성",
        x=male_values,
        y=ages,
        orientation="h",
        marker_color="#E6A05B",
        customdata=male_population,
        hovertemplate=(
            "나이: %{y}<br>"
            "남성 인구: %{customdata:,.0f}명"
            "<extra></extra>"
        ),
    )
)

fig.add_trace(
    go.Bar(
        name="여성",
        x=female_values,
        y=ages,
        orientation="h",
        marker_color="#D98291",
        hovertemplate=(
            "나이: %{y}<br>"
            "여성 인구: %{x:,.0f}명"
            "<extra></extra>"
        ),
    )
)

fig.update_layout(
    title={
        "text": (
            f"{selected_sido} {selected_sigungu} {selected_dong} "
            f"인구 피라미드 ({latest_year}년)"
        ),
        "x": 0.5,
        "xanchor": "center",
    },
    barmode="overlay",
    bargap=0.12,
    height=1050,
    paper_bgcolor="#FFF9F1",
    plot_bgcolor="#FFFDFA",
    font={"family": "Arial, sans-serif", "size": 12, "color": "#654535"},
    legend={
        "title": "성별",
        "orientation": "h",
        "yanchor": "bottom",
        "y": 1.01,
        "xanchor": "center",
        "x": 0.5,
    },
    margin={"l": 90, "r": 35, "t": 100, "b": 65},
)

fig.update_xaxes(
    title_text="인구수 (명)",
    range=[-axis_limit, axis_limit],
    tickmode="array",
    tickvals=tick_values,
    ticktext=tick_text,
    zeroline=True,
    zerolinecolor="#9B877A",
    showgrid=True,
    gridcolor="#EFE5DB",
)

# 나이 라벨 순서를 직접 고정합니다.
# 첫 번째 0세는 아래, 마지막 100세 이상은 위에 나타납니다.
fig.update_yaxes(
    title_text="나이",
    type="category",
    categoryorder="array",
    categoryarray=ages,
    showgrid=True,
    gridcolor="#F2E8DE",
    tickfont={"size": 10},
)

st.plotly_chart(fig, use_container_width=True)
st.caption("축 확인: 맨 아래 0세 · 맨 위 100세 이상 · 남성 왼쪽 · 여성 오른쪽")


# ==================================================
# 9. 자동 한 줄 해석
# ==================================================
st.divider()
st.subheader("💡 우리 동네 인구 한 줄 해석")

if child_population > senior_population:
    interpretation = (
        f"이 동네는 0~14세 인구({child_population:,.0f}명)가 "
        f"65세 이상 인구({senior_population:,.0f}명)보다 많아, "
        "어르신보다 아이 인구가 많은 편입니다."
    )
elif senior_population > child_population:
    interpretation = (
        f"이 동네는 65세 이상 인구({senior_population:,.0f}명)가 "
        f"0~14세 인구({child_population:,.0f}명)보다 많아, "
        "아이보다 어르신 인구가 많은 편입니다."
    )
else:
    interpretation = (
        f"이 동네는 0~14세 인구와 65세 이상 인구가 "
        f"각각 {child_population:,.0f}명으로 같습니다."
    )

st.markdown(
    f'<div class="summary-note">{interpretation}</div>',
    unsafe_allow_html=True,
)


# ==================================================
# 10. 상세 데이터 표
# ==================================================
with st.expander("🔎 나이별 인구 데이터 확인"):
    detail_df = pd.DataFrame({
        "나이": ages,
        "남성 인구": male_population,
        "여성 인구": female_population,
        "전체 인구": [
            male + female
            for male, female in zip(male_population, female_population)
        ],
    })
    st.dataframe(detail_df, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption(
    f"자료: 제공된 GitHub 인구 데이터 · 기준 연도: {latest_year}"
)
