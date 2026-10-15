import math
import pandas as pd
import streamlit as st
import plotly.graph_objects as go


# --------------------------------------------------
# 1. 페이지 기본 설정
# --------------------------------------------------
st.set_page_config(
    page_title="동네별 인구 피라미드",
    page_icon="🏘️",
    layout="wide",
)

# 따뜻한 색상의 CSS 디자인
st.markdown(
    """
    <style>
    .stApp {
        background-color: #FFF9F1;
    }

    h1, h2, h3 {
        color: #563D32;
    }

    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #F0DDCA;
        padding: 16px;
        border-radius: 12px;
    }

    div[data-baseweb="select"] {
        background-color: #FFFFFF;
    }

    .intro {
        color: #80695B;
        font-size: 16px;
        line-height: 1.7;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# 2. 데이터 불러오기
# --------------------------------------------------
DATA_URL = (
    "https://raw.githubusercontent.com/"
    "yhs0942/Population/main/"
    "population_ts_yearly_gender.zip"
)


@st.cache_data(show_spinner="전국 인구 데이터를 불러오는 중입니다...")
def load_data():
    """GitHub의 ZIP CSV를 읽고 가장 최신 연도만 남깁니다."""

    # pandas가 URL의 ZIP 압축을 자동으로 처리합니다.
    df = pd.read_csv(DATA_URL, compression="zip")

    # 열 이름에 불필요한 공백이 있다면 제거합니다.
    df.columns = df.columns.astype(str).str.strip()

    # 지역 및 연도 열이 있는지 확인합니다.
    required_columns = ["연도", "시도", "시군구", "동"]
    missing_columns = [
        col for col in required_columns if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "필수 열을 찾을 수 없습니다: "
            + ", ".join(missing_columns)
        )

    # 연도를 숫자로 변환합니다.
    # 숫자로 바꿀 수 없는 값은 결측값으로 처리합니다.
    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
    df = df.dropna(subset=["연도"])

    if df.empty:
        raise ValueError("데이터에 유효한 연도가 없습니다.")

    # 데이터에 실제로 존재하는 가장 최신 연도를 찾습니다.
    latest_year = int(df["연도"].max())

    # 최신 연도 데이터만 사용합니다.
    df = df[df["연도"] == latest_year].copy()

    # 지역 이름을 문자열로 통일하고 앞뒤 공백을 제거합니다.
    for col in ["시도", "시군구", "동"]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    return df, latest_year


try:
    df, latest_year = load_data()
except Exception as e:
    st.error("인구 데이터를 불러오는 중 오류가 발생했습니다.")
    st.exception(e)
    st.stop()


# --------------------------------------------------
# 3. 나이별 인구 열 만들기
# --------------------------------------------------
# 0세부터 99세까지, 마지막은 100세 이상입니다.
ages = [f"{i}세" for i in range(100)] + ["100세 이상"]

# 남자와 여자 인구 열 이름을 각각 만듭니다.
male_columns = [f"남_{age}" for age in ages]
female_columns = [f"여_{age}" for age in ages]

# 실제 데이터에 나이별 인구 열이 모두 있는지 확인합니다.
required_age_columns = male_columns + female_columns
missing_age_columns = [
    col for col in required_age_columns if col not in df.columns
]

if missing_age_columns:
    st.error(
        "일부 나이별 인구 열이 데이터에 없습니다. "
        "실제 CSV의 열 이름을 확인해 주세요."
    )
    st.write("누락된 열:", missing_age_columns)
    st.stop()

# 인구 열을 숫자로 변환합니다.
# 비어 있거나 숫자가 아닌 값은 0으로 처리합니다.
for col in required_age_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)


# --------------------------------------------------
# 4. 화면 제목
# --------------------------------------------------
st.title("🏘️ 동네별 인구 피라미드")

st.markdown(
    f"""
    <p class="intro">
    우리 동네의 연령별 인구 구성을 살펴보세요.
    아래에서 시도, 시군구, 동을 차례로 선택하면
    남성과 여성의 인구 분포를 비교할 수 있습니다.
    </p>
    """,
    unsafe_allow_html=True,
)

st.caption(f"📅 분석 기준 연도: {latest_year}년")


# --------------------------------------------------
# 5. 지역 선택 드롭다운 3개
# --------------------------------------------------
st.subheader("📍 지역 선택")

col1, col2, col3 = st.columns(3)

# 첫 번째 드롭다운: 시도
sido_options = sorted(df["시도"].unique().tolist())

with col1:
    selected_sido = st.selectbox(
        "① 시도",
        options=sido_options,
        key="selected_sido",
    )

# 선택한 시도에 속한 시군구만 추립니다.
sido_df = df[df["시도"] == selected_sido]

sigungu_options = sorted(sido_df["시군구"].unique().tolist())

with col2:
    selected_sigungu = st.selectbox(
        "② 시군구",
        options=sigungu_options,
        key="selected_sigungu",
    )

# 선택한 시도와 시군구에 속한 동만 추립니다.
sigungu_df = sido_df[
    sido_df["시군구"] == selected_sigungu
]

dong_options = sorted(sigungu_df["동"].unique().tolist())

with col3:
    selected_dong = st.selectbox(
        "③ 동·읍·면",
        options=dong_options,
        key="selected_dong",
    )


# --------------------------------------------------
# 6. 선택한 지역의 인구 데이터 찾기
# --------------------------------------------------
selected_rows = df[
    (df["시도"] == selected_sido)
    & (df["시군구"] == selected_sigungu)
    & (df["동"] == selected_dong)
]

if selected_rows.empty:
    st.warning("선택한 지역의 인구 데이터가 없습니다.")
    st.stop()

# 같은 지역이 여러 행으로 들어 있는 경우에도
# 나이별 인구를 합산해 하나의 인구 분포로 만듭니다.
area_data = selected_rows[required_age_columns].sum()

male_population = [
    int(area_data[col]) for col in male_columns
]
female_population = [
    int(area_data[col]) for col in female_columns
]

# 전체 남녀 인구를 계산합니다.
total_male = sum(male_population)
total_female = sum(female_population)
total_population = total_male + total_female


# --------------------------------------------------
# 7. 주요 인구 지표 표시
# --------------------------------------------------
st.divider()
st.subheader("📊 주요 인구 지표")

metric1, metric2, metric3 = st.columns(3)

with metric1:
    st.metric(
        label="전체 인구",
        value=f"{total_population:,}명",
    )

with metric2:
    st.metric(
        label="남성 인구",
        value=f"{total_male:,}명",
    )

with metric3:
    st.metric(
        label="여성 인구",
        value=f"{total_female:,}명",
    )


# --------------------------------------------------
# 8. 인구 피라미드 그리기
# --------------------------------------------------
st.divider()
st.subheader("👥 연령별 인구 피라미드")

# 남성은 음수로 바꿔 왼쪽에 표시합니다.
# 여성은 양수 그대로 두어 오른쪽에 표시합니다.
male_values = [-value for value in male_population]
female_values = female_population

# 양쪽 막대가 같은 범위를 사용하도록 x축 범위를 계산합니다.
largest_population = max(
    max(male_population, default=0),
    max(female_population, default=0),
    1,
)

# 눈금 간격을 적절하게 정합니다.
tick_step = max(1, math.ceil(largest_population / 5))
axis_limit = tick_step * 5

# 음수 쪽도 실제 인구수는 양수로 보이도록 눈금 라벨을 지정합니다.
tick_values = list(range(-axis_limit, axis_limit + 1, tick_step))
tick_text = [f"{abs(value):,}" for value in tick_values]

fig = go.Figure()

# 남성 막대: 왼쪽, 주황색 계열
fig.add_trace(
    go.Bar(
        x=male_values,
        y=ages,
        name="남성",
        orientation="h",
        marker_color="#E9A15A",
        hovertemplate=(
            "나이: %{y}<br>"
            "남성 인구: %{customdata:,}명"
            "<extra></extra>"
        ),
        customdata=male_population,
    )
)

# 여성 막대: 오른쪽, 분홍색 계열
fig.add_trace(
    go.Bar(
        x=female_values,
        y=ages,
        name="여성",
        orientation="h",
        marker_color="#D98291",
        hovertemplate=(
            "나이: %{y}<br>"
            "여성 인구: %{x:,}명"
            "<extra></extra>"
        ),
    )
)

fig.update_layout(
    title={
        "text": (
            f"{selected_sido} {selected_sigungu} "
            f"{selected_dong} 인구 피라미드 ({latest_year}년)"
        ),
        "x": 0.5,
        "xanchor": "center",
    },
    barmode="overlay",
    bargap=0.12,
    height=1100,
    paper_bgcolor="#FFF9F1",
    plot_bgcolor="#FFFDF9",
    font=dict(
        family="Arial, sans-serif",
        size=12,
        color="#563D32",
    ),
    legend=dict(
        title="성별",
        orientation="h",
        yanchor="bottom",
        y=1.01,
        xanchor="center",
        x=0.5,
    ),
    margin=dict(l=75, r=35, t=100, b=65),
)

# x축: 남성은 음수, 여성은 양수지만 눈금에는 양수 인구수를 표시합니다.
fig.update_xaxes(
    title_text="인구수 (명)",
    range=[-axis_limit, axis_limit],
    tickmode="array",
    tickvals=tick_values,
    ticktext=tick_text,
    zeroline=True,
    zerolinecolor="#9B877A",
    zerolinewidth=1.5,
    showgrid=True,
    gridcolor="#EFE4D8",
)

# 중요: 나이 라벨을 0세부터 100세 이상까지 직접 지정합니다.
# categoryorder와 categoryarray로 순서를 고정합니다.
# categoryarray의 첫 항목인 0세가 아래쪽,
# 마지막 항목인 100세 이상이 위쪽에 표시됩니다.
fig.update_yaxes(
    title_text="나이",
    type="category",
    categoryorder="array",
    categoryarray=ages,
    showgrid=True,
    gridcolor="#F4EAE0",
    tickfont=dict(size=10),
)

# 그래프를 화면에 표시합니다.
st.plotly_chart(fig, use_container_width=True)

# 축 순서 확인용 안내 문구
st.caption(
    "축 확인: 맨 아래는 0세, 맨 위는 100세 이상입니다. "
    "남성은 왼쪽, 여성은 오른쪽에 표시됩니다."
)


# --------------------------------------------------
# 9. 데이터 확인용 표
# --------------------------------------------------
with st.expander("🔎 선택한 지역의 나이별 인구 데이터 확인"):
    # 그래프와 같은 나이 순서로 표를 만듭니다.
    detail_df = pd.DataFrame(
        {
            "나이": ages,
            "남성 인구": male_population,
            "여성 인구": female_population,
            "전체 인구": [
                m + f
                for m, f in zip(male_population, female_population)
            ],
        }
    )

    st.dataframe(
        detail_df,
        use_container_width=True,
        hide_index=True,
    )

st.markdown(
    """
    ---
    <p style="text-align:center; color:#9B877A; font-size:12px;">
    동네별 인구 피라미드 · 자료: 제공된 GitHub 인구 데이터
    </p>
    """,
    unsafe_allow_html=True,
)
