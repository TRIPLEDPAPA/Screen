import streamlit as st
import pandas as pd
from db import load_sample_data, calculate_quant_scores

# 페이지 설정
st.set_page_config(
    page_title="고정밀 숏스퀴즈 및 종가 베팅 퀀트 대시보드",
    layout="wide"
)

st.title("🎯 고정밀 숏스퀴즈 & 종가 베팅 퀀트 대시보드")
st.markdown("메인 테이블(5일~1일 초단기)과 상세 모달(10일~1년 중장기) 시계열 분리 및 상하 단일 컬럼 레이아웃 시스템입니다.")
st.markdown("---")

# 데이터 로드 및 연산
raw_df = load_sample_data()
result_df = calculate_quant_scores(raw_df)

# ---------------------------------------------------------
# 1. 메인 테이블 (초단기 수익률 5일 ~ 1일 집중 추적)
# ---------------------------------------------------------
st.subheader("📊 1. 스크리닝 결과 메인 테이블 (초단기 수익률 5일 ~ 1일)")
main_columns = [
    "종목코드", "종목명", "섹터", 
    "수익률_5일", "수익률_4일", "수익률_3일", "수익률_2일", "수익률_1일",
    "당일거래대금(억)", "상승가능성점수", "종가베팅점수", "숏스퀴즈보너스", "최종우선순위점수", "진입판정"
]
st.dataframe(result_df[main_columns], use_container_width=True)

st.markdown("---")

# ---------------------------------------------------------
# 2. 상세 분석 모달 / 섹션 (세로 상하 단일 컬럼 배치)
# ---------------------------------------------------------
st.subheader("🔍 2. 종목별 상세 분석 및 📑 DART 수주 타임라인 (세로 상하 배치)")

selected_stock = st.selectbox("상세 분석할 종목을 선택하세요:", result_df["종목명"].tolist())
target_row = result_df[result_df["종목명"] == selected_stock].iloc[0]

st.markdown(f"### 📌 [{target_row['종목코드']}] {target_row['종목명']} 상세 진단 리포트")

# [상세 분석 전용] 중장기 및 추세 수익률 (10일 ~ 1년) 시계열 뷰
with st.container():
    st.markdown("#### 📈 [상세 분석] 중장기 및 추세 수익률 시계열 (10일 ~ 1년)")
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("10일 수익률", f"{target_row['수익률_10일']}%")
    m2.metric("20일 수익률", f"{target_row['수익률_20일']}%")
    m3.metric("30일 수익률", f"{target_row['수익률_30일']}%")
    m4.metric("3개월 수익률", f"{target_row['수익률_3개월']}%")
    m5.metric("6개월 수익률", f"{target_row['수익률_6개월']}%")
    m6.metric("1년 수익률", f"{target_row['수익률_1년']}%")

st.markdown("---")

# 대분류 1: 공매도 및 수급 압박 섹션
with st.container():
    st.markdown("#### 📂 [대분류 1] 공매도 및 수급 압박 섹션")
    c1, c2, c3 = st.columns(3)
    c1.metric("공매도 잔고비중", f"{target_row['공매도잔고비중(%)']}%", "기준 ≥ 3%")
    c2.metric("숏커버 소요일 (DtC)", f"{target_row['DtC(일)']}일", "기준 ≥ 2일")
    c3.metric("5일 공매도 비중", f"{target_row['5일공매도비중(%)']}%", "기준 ≥ 5%")
    
    st.markdown(f"* **숏스퀴즈 충족 조건 수:** {target_row['숏스퀴즈충족조건수']}/8개 (보너스 +{target_row['숏스퀴즈보너스']}점)")
    st.markdown(f"* **이격도 과열 감지 개수:** {target_row['과열개수']}개 (감점: -{target_row['과열감점']}점)")

st.markdown("---")

# 대분류 2: DART 최근 1달 수주 타임라인
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

# 대분류 3: 종가 베팅 점수 세부 내역
with st.container():
    st.markdown("#### 📂 [대분류 3] 종가 베팅 점수 (45점 만점) 세부 내역")
    col_a, col_b = st.columns(2)
    with col_a:
        st.write(f"- **당일 거래대금:** {target_row['당일거래대금(억)']}억원")
        st.write(f"- **거래량 비율:** {target_row['거래량비율']}배")
        st.write(f"- **종가 위치:** {target_row['종가위치(%)']}%")
        st.write(f"- **당일 등락률 (1일):** {target_row['수익률_1일']}%")
        st.write(f"- **윗꼬리 비율:** {target_row['윗꼬리비율(%)']}%")
    with col_b:
        st.write(f"- **이평선 정배열 여부:** {'충족' if target_row['정배열여부'] else '미충족'}")
        st.write(f"- **외국인 5일 순매수:** {target_row['외인5일순매수(억)']}억원")
        st.write(f"- **기관 5일 순매수:** {target_row['기관5일순매수(억)']}억원")
        st.write(f"- **동시호가 체결 강도:** {'플러스 유지 (통과)' if target_row['동시호가체결플러스'] else '마이너스 전환 (반려)'}")
        st.markdown(f"### **종가 베팅 총점: {target_row['종가베팅점수']} / 45점**")

st.markdown("---")
st.success("✨ `db.py`와 `main.py` 파일 분리가 완료되었습니다. `streamlit run main.py` 명령어로 실행하세요.")
