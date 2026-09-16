import pandas as pd
import numpy as np
import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="고정밀 숏스퀴즈 및 종가 베팅 퀀트 대시보드",
    layout="wide"
)

st.title("🎯 고정밀 숏스퀴즈 & 종가 베팅 퀀트 대시보드")
st.markdown("상승 가능성(100점)과 종가 베팅 점수(45점)를 분리하고, 이격도 과열 감점 및 동시호가/수급 신뢰도 필터를 적용한 시스템입니다.")
st.markdown("---")

# ---------------------------------------------------------
# 1. 샘플 데이터 생성 함수 (실전 연동 시 KRX API 대체)
# ---------------------------------------------------------
@st.cache_data
def load_sample_data():
    np.random.seed(42)
    data = {
        "종목코드": ["005930", "000660", "042700", "035720", "028300", "247540", "086520", "003680", "112040", "010140"],
        "종목명": ["삼성전자", "SK하이닉스", "한미반도체", "카카오", "HLB", "에코프로비엠", "에코프로", "한성기업", "위메이드", "삼성중공업"],
        "섹터": ["반도체", "반도체", "반도체", "IT/소프트웨어", "제약/바이오", "2차전지", "2차전지", "음식료", "게임", "조선/중공업"],
        "당일거래대금(억)": [1200, 850, 450, 320, 600, 1100, 950, 150, 220, 410],
        "거래량비율": [2.5, 1.8, 3.1, 1.2, 2.7, 3.5, 2.2, 1.1, 1.6, 2.0],
        "당일등락률(%)": [5.2, 3.1, 6.8, 1.5, 4.5, 7.5, 4.2, 0.8, 2.5, 3.8],
        "종가위치(%)": [85, 75, 92, 60, 88, 95, 80, 50, 65, 78],
        "윗꼬리비율(%)": [12, 18, 5, 35, 10, 3, 15, 40, 25, 14],
        "5일이격도": [103, 101, 106, 97, 104, 109, 102, 98, 100, 101],
        "10일이격도": [105, 103, 108, 99, 106, 113, 104, 99, 102, 103],
        "20일이격도": [107, 104, 111, 98, 109, 116, 107, 98, 103, 105],
        "60일이격도": [115, 110, 125, 95, 118, 132, 115, 96, 105, 108],
        "정배열여부": [True, True, True, False, True, True, True, False, True, True],
        "외인5일순매수(억)": [150, 80, 40, -20, 90, 200, 110, -5, 10, 30],
        "기관5일순매수(억)": [80, 50, -10, -30, 60, 120, 70, 2, -5, 45],
        "공매도잔고비중(%)": [1.2, 2.5, 3.8, 0.5, 4.2, 5.1, 4.8, 0.2, 1.0, 0.8],
        "DtC(일)": [1.0, 1.8, 2.5, 0.5, 3.1, 4.2, 3.8, 0.2, 0.9, 0.7],
        "동시호가체결플러스": [True, True, True, False, True, True, True, False, True, True],
        "수급확정여부": ["장 마감 확정", "장 마감 확정", "장중 추정", "장중 추정", "장 마감 확정", "장 마감 확정", "장중 추정", "장 마감 확정", "장중 추정", "장 마감 확정"]
    }
    return pd.DataFrame(data)

df = load_sample_data()

# ---------------------------------------------------------
# 2. 스코어링 및 페널티 연산 함수
# ---------------------------------------------------------
def calculate_scores(row):
    # 과열 감점 계산 (5일>=108, 10일>=112, 20일>=115, 60일>=130)
    overheat_count = 0
    if row["5일이격도"] >= 108: overheat_count += 1
    if row["10일이격도"] >= 112: overheat_count += 1
    if row["20일이격도"] >= 115: overheat_count += 1
    if row["60일이격도"] >= 130: overheat_count += 1

    penalty = 0
    if overheat_count == 2: penalty = 3
    elif overheat_count == 3: penalty = 6
    elif overheat_count >= 4: penalty = 10

    # 상승 가능성 점수 (100점 만점)
    sec_score = 16 
    fund_score = 15 
    sup_score = 15 if (row["외인5일순매수(억)"] > 0 and row["기관5일순매수(억)"] > 0) else 8 
    trend_score = 22 if row["정배열여부"] else 10 
    risk_score = 15 - penalty 
    
    growth_score = max(0, sec_score + fund_score + sup_score + trend_score + risk_score)

    # 종가 베팅 점수 (45점 만점)
    t_amt = row["당일거래대금(억)"]
    s_amt = 6 if t_amt >= 1000 else (5 if t_amt >= 500 else (4 if t_amt >= 300 else (3 if t_amt >= 100 else 0)))
    
    v_rat = row["거래량비율"]
    s_vol = 5 if v_rat >= 3 else (4 if v_rat >= 2 else (3 if v_rat >= 1.5 else (1 if v_rat >= 1.2 else 0)))

    c_pos = row["종가위치(%)"]
    s_pos = 5 if c_pos >= 90 else (4 if c_pos >= 80 else (3 if c_pos >= 70 else (1 if c_pos >= 60 else 0)))

    chg = row["당일등락률(%)"]
    s_chg = 4 if (3 <= chg <= 8) else (3 if (1 <= chg < 3) else (2 if (8 < chg <= 12) else (1 if 0 <= chg < 1 else 0)))

    s_body = 3 if c_pos >= 70 else 2
    w_tail = row["윗꼬리비율(%)"]
    s_tail = 3 if w_tail <= 10 else (2 if w_tail <= 20 else (1 if w_tail <= 30 else 0))

    s_align = 5 if row["정배열여부"] else 0
    s_fgn = 5 if row["외인5일순매수(억)"] > 100 else (3 if row["외인5일순매수(억)"] > 0 else 0)
    s_org = 4 if row["기관5일순매수(억)"] > 50 else (2 if row["기관5일순매수(억)"] > 0 else 0)
    s_break = 5 if row["종가위치(%)"] >= 80 else 3

    closing_score = s_amt + s_vol + s_pos + s_chg + s_body + s_tail + s_align + s_fgn + s_org + s_break

    # 숏스퀴즈 보너스 (최대 +5점)
    sq_bonus = 0
    if row["공매도잔고비중(%)"] >= 3.0 and row["DtC(일)"] >= 2.0:
        sq_bonus = 3
        if row["거래량비율"] >= 2.0:
            sq_bonus = 5

    # 최종 우선순위 산식
    closing_normalized = (closing_score / 45.0) * 100
    final_priority = (growth_score * 0.7) + (closing_normalized * 0.3) + sq_bonus

    return pd.Series({
        "상승가능성점수": growth_score,
        "종가베팅점수": closing_score,
        "과열개수": overheat_count,
        "숏스퀴즈보너스": sq_bonus,
        "최종우선순위점수": round(final_priority, 2)
    })

# 점수 병합
score_df = df.apply(calculate_scores, axis=1)
result_df = pd.concat([df, score_df], axis=1)

# 진입 여부 판정 (3단계 기준)
def determine_status(row):
    if row["상승가능성점수"] >= 75 and row["종가베팅점수"] >= 34 and row["당일거래대금(억)"] >= 100 and row["동시호가체결플러스"]:
        if row["최종우선순위점수"] >= 85: return "🔴 최우선 검토"
        elif row["최종우선순위점수"] >= 78: return "🟠 적극 관찰"
        else: return "🟡 눌림목 대기"
    else:
        return "⚪ 진입 보류"

result_df["진입판정"] = result_df.apply(determine_status, axis=1)
result_df = result_df.sort_values(by="최종우선순위점수", ascending=False).reset_index(drop=True)

# ---------------------------------------------------------
# 3. 대시보드 UI 레이아웃 구성 (상하 단일 컬럼 구조)
# ---------------------------------------------------------

st.subheader("📊 1. 스크리닝 결과 메인 테이블")
st.dataframe(
    result_df[["종목코드", "종목명", "섹터", "당일거래대금(억)", "상승가능성점수", "종가베팅점수", "숏스퀴즈보너스", "최종우선순위점수", "수급확정여부", "진입판정"]],
    use_container_width=True
)

st.markdown("---")

st.subheader("🔍 2. 종목별 상세 분석 및 📑 DART 수주 타임라인 (세로 상하 배치)")

# 선택 종목 드롭다운
selected_stock = st.selectbox("상세 분석할 종목을 선택하세요:", result_df["종목명"].tolist())
target_row = result_df[result_df["종목명"] == selected_stock].iloc[0]

# 상하로 길게 내려오는 단일 컬럼 구조 (Vertical Top-Down Layout)
st.markdown(f"### 📌 [{target_row['종목코드']}] {target_row['종목명']} 상세 진단 리포트")

# 섹션 1: 공매도 및 수급 압박 분석
with st.container():
    st.markdown("#### 📂 [대분류 1] 공매도 및 수급 압박 섹션")
    col1, col2, col3 = st.columns(3)
    col1.metric("공매도 잔고비중", f"{target_row['공매도잔고비중(%)']}%", "기준 ≥ 3%")
    col2.metric("숏커버 소요일 (DtC)", f"{target_row['DtC(일)']}일", "기준 ≥ 2일")
    col3.metric("수급 데이터 상태", target_row["수급확정여부"])
    
    st.markdown(f"* **이격도 과열 감지 개수:** {target_row['과열개수']}개 (페널티 적용 완료)")
    st.markdown(f"* **숏스퀴즈 보너스 점수:** +{target_row['숏스퀴즈보너스']}점 부여")

st.markdown("---")

# 섹션 2: 📑 DART 최근 1달 수주 타임라인
with st.container():
    st.markdown("#### 📂 [대분류 2] 📑 DART 최근 1달 수주 타임라인")
    st.info("💡 최근 30일 내 단일판매·공급계약 체결 공시 및 매출액 대비 수주 집중도 요약")
    
    timeline_data = pd.DataFrame({
        "공시일자": ["2026-09-10", "2026-08-25"],
        "계약명": ["반도체 제조장비 공급 계약", "2차전지 부품 단일판매 체결"],
        "계약금액(억원)": [450, 1200],
        "매출액대비비중(%)": [28.5, 65.2],
        "동조화 분석": ["대차잔고 감소 시작 (숏커버 징후)", "거래량 3배 폭증 동반"]
    })
    st.dataframe(timeline_data, use_container_width=True)

st.markdown("---")

# 섹션 3: 45점 만점 종가 베팅 지표 상세 내역
with st.container():
    st.markdown("#### 📂 [대분류 3] 종가 베팅 점수 (45점 만점) 세부 내역")
    col_a, col_b = st.columns(2)
    with col_a:
        st.write(f"- **당일 거래대금:** {target_row['당일거래대금(억)']}억원")
        st.write(f"- **거래량 비율:** {target_row['거래량비율']}배")
        st.write(f"- **종가 위치:** {target_row['종가위치(%)']}%")
        st.write(f"- **당일 등락률:** {target_row['당일등락률(%)']}%")
        st.write(f"- **윗꼬리 비율:** {target_row['윗꼬리비율(%)']}%")
    with col_b:
        st.write(f"- **이평선 정배열 여부:** {'충족' if target_row['정배열여부'] else '미충족'}")
        st.write(f"- **외국인 5일 순매수:** {target_row['외인5일순매수(억)']}억원")
        st.write(f"- **기관 5일 순매수:** {target_row['기관5일순매수(억)']}억원")
        st.write(f"- **동시호가 체결 강도:** {'플러스 유지 (통과)' if target_row['동시호가체결플러스'] else '마이너스 전환 (반려)'}")
        st.markdown(f"### **종가 베팅 총점: {target_row['종가베팅점수']} / 45점**")

st.markdown("---")
st.success("✨ 모든 룰과 상하 레이아웃 배치가 반영된 퀀트 대시보드 코드가 정상적으로 준비되었습니다.")
