import re
from itertools import combinations
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="송탄고 급식 연관규칙 분석", layout="wide")


@st.cache_data
def load_and_process_data(url):
    df = pd.read_csv(url, encoding="utf-8")

    # 메뉴 전처리: 괄호 및 괄호 안 내용 제거 후 분리
    transactions = []
    all_items = set()

    for raw_menu in df["메뉴"].dropna():
        cleaned = re.sub(r"\(.*?\)", "", str(raw_menu))
        items = list(
            set(
                item.strip()
                for item in cleaned.split("|")
                if item.strip()
            )
        )
        if items:
            transactions.append(items)
            all_items.update(items)

    total_days = len(transactions)

    # 1항목 빈도 계산
    item_counts = {}
    for t in transactions:
        for item in t:
            item_counts[item] = item_counts.get(item, 0) + 1

    # 2항목(쌍) 빈도 계산
    pair_counts = {}
    for t in transactions:
        for item1, item2 in combinations(sorted(t), 2):
            pair_counts[(item1, item2)] = pair_counts.get((item1, item2), 0) + 1

    # 연관규칙 생성 (A -> B, B -> A 모두 생성)
    rules = []
    for (item1, item2), joint_count in pair_counts.items():
        # 조건: item1 -> 결과: item2
        supp = joint_count / total_days
        conf1 = joint_count / item_counts[item1]
        lift1 = conf1 / (item_counts[item2] / total_days)

        rules.append(
            {
                "조건": item1,
                "결과": item2,
                "동시": joint_count,
                "지지도": round(supp, 4),
                "신뢰도": round(conf1, 4),
                "향상도": round(lift1, 4),
            }
        )

        # 조건: item2 -> 결과: item1
        conf2 = joint_count / item_counts[item2]
        lift2 = conf2 / (item_counts[item1] / total_days)

        rules.append(
            {
                "조건": item2,
                "결과": item1,
                "동시": joint_count,
                "지지도": round(supp, 4),
                "신뢰도": round(conf2, 4),
                "향상도": round(lift2, 4),
            }
        )

    rules_df = pd.DataFrame(rules)
    return total_days, len(all_items), len(pair_counts), rules_df, sorted(list(all_items))


# 데이터 로드
DATA_URL = "https://raw.githubusercontent.com/it-teacher-go/data-share-/main/songtan_meals_184.csv"
total_days, total_menu_types, unique_pairs_count, rules_df, all_menu_list = load_and_process_data(DATA_URL)

st.title("송탄고 급식 메뉴 연관규칙 분석")

# 정보 요약 표시
st.write(
    f"**급식 일수:** {total_days}일 | "
    f"**메뉴 종류 수:** {total_menu_types}개 | "
    f"**함께 나온 적이 있는 메뉴 쌍의 수:** {unique_pairs_count}개"
)

st.divider()

# 사이드바 / 필터 옵션
st.sidebar.header("필터 및 정렬 설정")

# 메뉴 선택
selected_menu = st.sidebar.selectbox(
    "메뉴 선택 (전체 보기: 선택 안 함)",
    ["전체"] + all_menu_list
)

# 정렬 기준 선택
sort_by = st.sidebar.radio(
    "정렬 기준",
    ["향상도", "신뢰도", "동시"],
    index=0
)

# 데이터 필터링
filtered_df = rules_df.copy()
if selected_menu != "전체":
    filtered_df = filtered_df[
        (filtered_df["조건"] == selected_menu) | (filtered_df["결과"] == selected_menu)
    ]

# 정렬 적용
filtered_df = filtered_df.sort_values(by=sort_by, ascending=False).reset_index(drop=True)

# 시각화 (향상도 상위 10개)
st.subheader("향상도 상위 10개 규칙")

if not filtered_df.empty:
    top10_df = filtered_df.sort_values(by="향상도", ascending=False).head(10).copy()
    top10_df["규칙"] = top10_df["조건"] + " ➔ " + top10_df["결과"]
    top10_df = top10_df.sort_values(by="향상도", ascending=True)

    fig = px.bar(
        top10_df,
        x="향상도",
        y="규칙",
        orientation="h",
        text="향상도",
        title="향상도 Top 10 규칙",
        labels={"향상도": "향상도", "규칙": "연관 규칙"},
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(height=400, yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("선택한 메뉴에 대한 연관규칙 데이터가 없습니다.")

# 연관규칙 표 출력
st.subheader("연관규칙 데이터 표")
st.dataframe(filtered_df, use_container_width=True)
