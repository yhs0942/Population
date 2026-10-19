import math
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import requests
import json


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

# ============================================================
# 2. 데이터 주소와 설정
# ============================================================
POPULATION_URL = (
    "https://raw.githubusercontent.com/"
    "yhs0942/Population/main/population_ts_yearly_gender.zip"
)
GEOJSON_URL = (
    "https://raw.githubusercontent.com/"
    "yhs0942/Population/main/sigungu_kr.geojson.txt"
)


# ============================================================
# 3. 인구 데이터 읽기 및 시군구별 고령화율 계산
# ============================================================
@st.cache_data(show_spinner="2026년 인구 데이터를 불러오는 중입니다...")
def load_population():
    # pandas가 ZIP 압축 CSV를 직접 읽습니다.
    data = pd.read_csv(POPULATION_URL, compression="zip")
    data.columns = data.columns.astype(str).str.strip()

    required = ["연도", "시도", "시군구", "동", "코드"]
    missing = [col for col in required if col not in data.columns]
    if missing:
        raise ValueError(
            f"인구 데이터에 필요한 열이 없습니다: {missing}\n"
            f"실제 열 이름 일부: {data.columns.tolist()[:30]}"
        )

    # 코드는 앞자리 0이 사라지지 않도록 문자열로 처리합니다.
    data["코드"] = (
        data["코드"]
        .astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(10)
    )

    # 연도는 숫자로 통일한 뒤 2026년 자료만 선택합니다.
    data["연도"] = pd.to_numeric(data["연도"], errors="coerce")
    data = data[data["연도"] == 2026].copy()
    if data.empty:
        raise ValueError("인구 데이터에서 2026년 자료를 찾지 못했습니다.")

    # '계_'로 시작하는 나이별 인구 열만 사용합니다.
    # 남_ / 여_ 열을 더하면 전체 인구가 중복 계산되므로 사용하지 않습니다.
    total_columns = [
        col for col in data.columns
        if col.startswith("계_")
    ]
    if not total_columns:
        raise ValueError("전체 인구 열('계_...')을 찾지 못했습니다.")

    # 65세 이상 인구 열: 계_65세부터 계_100세 이상까지
    senior_columns = [
        col for col in total_columns
        if (
            col == "계_100세 이상"
            or (
                col.startswith("계_")
                and col.endswith("세")
                and col[2:-1].isdigit()
                and int(col[2:-1]) >= 65
            )
        )
    ]
    if not senior_columns:
        raise ValueError("65세 이상 인구 열을 찾지 못했습니다.")

    # 인구 열을 숫자로 변환합니다.
    for col in total_columns:
        data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)

    # 동 코드 앞 5자리를 시군구 코드로 사용합니다.
    data["시군구코드"] = data["코드"].str[:5]

    # 전체 인구는 모든 계_ 열의 합, 고령 인구는 65세 이상 계_ 열의 합입니다.
    data["전체인구"] = data[total_columns].sum(axis=1)
    data["고령인구"] = data[senior_columns].sum(axis=1)

    # 동 단위 자료를 시군구 코드별로 합산합니다.
    grouped = (
        data.groupby("시군구코드", as_index=False)
        .agg(
            전체인구=("전체인구", "sum"),
            고령인구=("고령인구", "sum"),
        )
    )

    # 0으로 나누는 오류를 방지합니다.
    grouped["고령화율"] = (
        grouped["고령인구"]
        .div(grouped["전체인구"].where(grouped["전체인구"] != 0))
        .mul(100)
    )

    return grouped, total_columns, senior_columns


# ============================================================
# 4. 시군구 경계 GeoJSON 읽기
# ============================================================
@st.cache_data(show_spinner="시군구 경계 지도를 불러오는 중입니다...")
def load_geojson():
    # requests로 GeoJSON을 내려받고 JSON으로 변환합니다.
    response = requests.get(
        GEOJSON_URL,
        timeout=60,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()
    geojson = response.json()

    if "features" not in geojson:
        raise ValueError("GeoJSON에 features 항목이 없습니다.")

    # 각 경계의 코드 속성을 문자열로 정규화합니다.
    # 원본 FeatureCollection의 구조와 좌표는 그대로 유지합니다.
    for feature in geojson["features"]:
        properties = feature.get("properties", {})
        if "코드" not in properties:
            raise ValueError(
                "GeoJSON 속성에 '코드'가 없습니다. "
                f"확인 가능한 속성: {list(properties.keys())}"
            )

        code = str(properties["코드"]).strip()
        if code.endswith(".0"):
            code = code[:-2]
        properties["코드"] = code.zfill(5)

    return geojson


try:
    population_by_sigungu, total_columns, senior_columns = load_population()
except Exception as error:
    st.error("인구 데이터 처리 중 오류가 발생했습니다.")
    st.code(f"{type(error).__name__}: {error}")
    st.stop()

try:
    geojson = load_geojson()
except Exception as error:
    st.error("시군구 경계 GeoJSON을 불러오지 못했습니다.")
    st.code(f"{type(error).__name__}: {error}")
    st.stop()


# ============================================================
# 5. GeoJSON 경계와 인구 데이터를 코드로 결합
# ============================================================
# 지도 데이터의 위치 식별자는 이름이 아닌 5자리 시군구 코드입니다.
# 지도용 DataFrame의 '코드'와 GeoJSON의 properties['코드']가 일치합니다.
population_by_sigungu["코드"] = (
    population_by_sigungu["시군구코드"]
    .astype(str)
    .str.zfill(5)
)

# 지도에 표시할 이름은 GeoJSON의 '시군구' 속성을 사용합니다.
geo_properties = []
for feature in geojson["features"]:
    props = feature.get("properties", {})
    geo_properties.append({
        "코드": str(props["코드"]).zfill(5),
        "시군구": str(props.get("시군구", "")),
        "시도": str(props.get("시도", "")),
    })

geo_names = pd.DataFrame(geo_properties).drop_duplicates(subset=["코드"])

map_df = geo_names.merge(
    population_by_sigungu[["코드", "전체인구", "고령인구", "고령화율"]],
    on="코드",
    how="left",
    validate="one_to_one",
)

# 코드 일치 여부를 확인할 수 있도록 요약 정보를 표시합니다.
matched_count = int(map_df["고령화율"].notna().sum())
unmatched_count = int(map_df["고령화율"].isna().sum())

metric1, metric2, metric3 = st.columns(3)
metric1.metric("지도 경계 수", f"{len(map_df):,}개")
metric2.metric("인구 자료와 일치", f"{matched_count:,}개")
metric3.metric("인구 자료 미일치", f"{unmatched_count:,}개")

if matched_count == 0:
    st.error(
        "GeoJSON 코드와 인구 데이터의 앞 5자리 코드가 하나도 일치하지 않습니다. "
        "두 파일의 코드 형식을 확인해 주세요."
    )
    st.stop()

if unmatched_count > 0:
    st.warning(
        f"{unmatched_count}개 경계에는 인구 자료가 없어 지도에서 회색으로 표시됩니다."
    )


# ============================================================
# 6. 고령화율 단계구분도
# ============================================================
st.subheader("65세 이상 인구 비율")

# 결측 지역은 별도 색으로 표시하고, 고령화율이 높을수록 진해지는 순차 색상표를 씁니다.
map_df["지도표시값"] = map_df["고령화율"]

fig = px.choropleth(
    map_df,
    geojson=geojson,
    locations="코드",
    featureidkey="properties.코드",
    color="지도표시값",
    color_continuous_scale=[
        [0.0, "#FFF1D6"],
        [0.25, "#F8C98B"],
        [0.5, "#E99A59"],
        [0.75, "#C65D43"],
        [1.0, "#7F292F"],
    ],
    range_color=(
        0,
        max(1, float(map_df["고령화율"].max(skipna=True))),
    ),
    labels={"지도표시값": "고령화율 (%)"},
    custom_data=["시군구", "고령화율", "코드"],
)

fig.update_traces(
    marker_line_color="#FFFFFF",
    marker_line_width=0.45,
    hovertemplate=(
        "<b>%{customdata[0]}</b><br>"
        "고령화율: %{customdata[1]:.2f}%"
        "<extra></extra>"
    ),
    # 결측값은 회색으로 표시합니다.
    marker={
        "line": {"color": "white", "width": 0.45}
    },
)

# 배경 타일 없이 GeoJSON 경계만 보여 줍니다.
fig.update_geos(
    visible=False,
    showcountries=False,
    showcoastlines=False,
    showland=False,
    showframe=False,
    fitbounds="locations",
    bgcolor="#FFF9F1",
)

fig.update_layout(
    paper_bgcolor="#FFF9F1",
    plot_bgcolor="#FFF9F1",
    margin={"l": 0, "r": 0, "t": 20, "b": 0},
    coloraxis_colorbar={
        "title": "고령화율 (%)",
        "ticksuffix": "%",
        "thickness": 18,
        "len": 0.75,
    },
)

st.plotly_chart(fig, use_container_width=True)

st.caption(
    "색이 진할수록 65세 이상 인구 비율이 높습니다. "
    "지도에 마우스를 올리면 시군구 이름과 고령화율을 확인할 수 있습니다."
)


# ============================================================
# 7. 데이터 표 및 코드 매칭 확인
# ============================================================
with st.expander("📋 시군구별 고령화율 표"):
    display_df = map_df[
        ["코드", "시도", "시군구", "전체인구", "고령인구", "고령화율"]
    ].copy()
    display_df["고령화율"] = display_df["고령화율"].round(2)
    display_df = display_df.sort_values(
        "고령화율", ascending=False, na_position="last"
    )
    st.dataframe(display_df, use_container_width=True, hide_index=True)

st.caption("자료: 제공된 2026년 인구 데이터 및 시군구 경계 GeoJSON")
