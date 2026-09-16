import pandas as pd
import numpy as np

def load_market_data():
    """KRX, DART 및 퀀트 지표 연동용 데이터셋 (삼성전자 등 비적격 종목 숏스퀴즈 원천 차단 검증 포함)"""
    np.random.seed(42)
    data = {
        "종목코드": ["005930", "000660", "042700", "035720", "028300", "247540", "086520", "003680", "112040", "010140"],
        "종목명": ["삼성전자", "SK하이닉스", "한미반도체", "카카오", "HLB", "에코프로비엠", "에코프로", "한성기업", "위메이드", "삼성중공업"],
        "섹터": ["반도체", "반도체", "반도체", "IT/소프트웨어", "제약/바이오", "2차전지", "2차전지", "음식료", "게임", "조선/중공업"],
        
        # [메인 테이블 전용] 초단기 수익률 (5일, 4일, 3일, 2일, 1일) (%)
        "수익률_5일": [4.2, 2.1, 8.5, -1.2, 6.4, 12.5, 9.1, -2.0, 1.5, 3.2],
        "수익률_4일": [1.5, 0.8, 4.2, -0.5, 3.1, 5.2, 4.0, -0.8, 0.9, 1.4],
        "수익률_3일": [2.8, 3.5, 6.1, 0.2, 4.5, 8.1, 6.5, 0.5, 2.1, 2.8],
        "수익률_2일": [-0.5, 1.2, 3.0, -1.8, 2.0, 4.5, 3.2, -1.5, -0.4, 0.6],
        "수익률_1일": [5.2, 3.1, 6.8, 1.5, 4.5, 7.5, 4.2, 0.8, 2.5, 3.8],

        # [상세 모달 전용] 중장기 및 추세 수익률 (1년, 6개월, 3개월, 1개월[30일], 20일, 10일, 5일 흐름) (%)
        "수익률_1년": [48.5, 45.1, 150.4, -48.5, 125.0, 240.5, 185.0, -35.2, 35.4, 65.2],
        "수익률_6개월": [35.2, 30.4, 98.5, -35.2, 78.4, 165.2, 125.4, -25.4, 22.1, 42.5],
        "수익률_3개월": [25.4, 22.0, 65.2, -20.5, 52.1, 110.4, 85.2, -18.5, 15.4, 28.1],
        "수익률_1개월": [18.6, 15.1, 42.1, -12.4, 34.2, 68.5, 52.1, -12.0, 10.2, 18.5],
        "수익률_20일": [14.2, 11.5, 28.6, -7.5, 21.5, 45.2, 36.4, -8.2, 6.5, 12.4],
        "수익률_10일": [8.5, 6.2, 15.4, -3.1, 12.0, 22.4, 18.0, -4.5, 3.2, 7.1],

        "당일거래대금(억)": [1200, 850, 450, 320, 600, 1100, 950, 150, 220, 410],
        "거래량비율": [2.5, 1.8, 3.1, 1.2, 2.7, 3.5, 2.2, 1.1, 1.6, 2.0],
        "종가위치(%)": [85, 75, 92, 60, 88, 95, 80, 50, 65, 78],
        "윗꼬리비율(%)": [12, 18, 5, 35, 10, 3, 15, 40, 25, 14],
        "5일이격도": [103, 101, 106, 97, 104, 109, 102, 98, 100, 101],
        "10일이격도": [105, 103, 108, 99, 106, 113, 104, 99, 102, 103],
        "20일이격도": [107, 104, 111, 98, 109, 116, 107, 98, 103, 105],
        "60일이격도": [115, 110, 125, 95, 118, 132, 115, 96, 105, 108],
        "정배열여부": [True, True, True, False, True, True, True, False, True, True],
        "종가위산20일이평선상회": [True, True, True, False, True, True, True, False, True, True],
        "외인5일순매수(억)": [150, 80, 40, -20, 90, 200, 110, -5, 10, 30],
        "기관5일순매수(억)": [80, 50, -10, -30, 60, 120, 70, 2, -5, 45],
        
        # 숏스퀴즈 8대 검증 항목
        "공매도잔고비중(%)": [1.2, 2.5, 3.8, 0.5, 4.2, 5.1, 4.8, 0.2, 1.0, 0.8], # 삼성전자 1.2% (기준 3% 미달)
        "DtC(일)": [1.0, 1.8, 2.5, 0.5, 3.1, 4.2, 3.8, 0.2, 0.9, 0.7],          # 삼성전자 1.0일 (기준 2일 미달)
        "5일공매도비중(%)": [2.1, 3.5, 5.6, 1.0, 6.2, 7.5, 6.8, 0.5, 1.8, 2.0],
        
        "동시호가체결플러스": [True, True, True, False, True, True, True, False, True, True],
        "수급확정여부": ["장 마감 확정", "장 마감 확정", "장중 추정", "장중 추정", "장 마감 확정", "장 마감 확정", "장중 추정", "장 마감 확정", "장중 추정", "장 마감 확정"],
        "PER": [15.2, 12.4, 25.1, 45.2, 0.0, 38.5, 42.1, 10.5, 18.2, 22.0],
        "PBR": [1.4, 1.8, 4.2, 2.1, 3.5, 5.2, 4.8, 0.8, 1.5, 1.1]
    }
    return pd.DataFrame(data)

def calculate_quant_engine(df):
    """엄격한 숏스퀴즈 게이트 및 스코어링 엔진 연산"""
    def process_row(row):
        # 1. 과열 감점 룰 (5일선≥108, 10일선≥112, 20일선≥115, 60일선≥130)
        overheat_count = 0
        if row["5일이격도"] >= 108: overheat_count += 1
        if row["10일이격도"] >= 112: overheat_count += 1
        if row["20일이격도"] >= 115: overheat_count += 1
        if row["60일이격도"] >= 130: overheat_count += 1

        penalty = 0
        if overheat_count == 2: penalty = 3
        elif overheat_count == 3: penalty = 6
        elif overheat_count >= 4: penalty = 10

        # 2. 상승 가능성 점수 (100점 만점)
        sec_score = 16 
        fund_score = 15 
        sup_score = 15 if (row["외인5일순매수(억)"] > 0 and row["기관5일순매수(억)"] > 0) else 8 
        trend_score = 22 if row["정배열여부"] else 10 
        risk_score = max(0, 15 - penalty)
        growth_score = sec_score + fund_score + sup_score + trend_score + risk_score

        # 3. 종가 베팅 점수 (45점 만점)
        t_amt = row["당일거래대금(억)"]
        s_amt = 6 if t_amt >= 1000 else (5 if t_amt >= 500 else (4 if t_amt >= 300 else (3 if t_amt >= 100 else 0)))
        
        v_rat = row["거래량비율"]
        s_vol = 5 if v_rat >= 3 else (4 if v_rat >= 2 else (3 if v_rat >= 1.5 else (1 if v_rat >= 1.2 else 0)))

        c_pos = row["종가위치(%)"]
        s_pos = 5 if c_pos >= 90 else (4 if c_pos >= 80 else (3 if c_pos >= 70 else (1 if c_pos >= 60 else 0)))

        chg = row["수익률_1일"]
        s_chg = 4 if (3 <= chg <= 8) else (3 if (1 <= chg < 3) else (2 if (8 < chg <= 12) else (1 if 0 <= chg < 1 else 0)))

        s_body = 3 if c_pos >= 70 else 2
        w_tail = row["윗꼬리비율(%)"]
        s_tail = 3 if w_tail <= 10 else (2 if w_tail <= 20 else (1 if w_tail <= 30 else 0))

        s_align = 5 if row["정배열여부"] else 0
        s_fgn = 5 if row["외인5일순매수(억)"] > 100 else (3 if row["외인5일순매수(억)"] > 0 else 0)
        s_org = 4 if row["기관5일순매수(억)"] > 50 else (2 if row["기관5일순매수(억)"] > 0 else 0)
        s_break = 5 if row["종가위치(%)"] >= 80 else 3

        closing_score = s_amt + s_vol + s_pos + s_chg + s_body + s_tail + s_align + s_fgn + s_org + s_break

        # 4. 엄격한 숏스퀴즈 8대 조건 게이트 (모두 만족해야 진입 및 보너스 부여)
        cond_1 = row["공매도잔고비중(%)"] >= 3.0
        cond_2 = row["DtC(일)"] >= 2.0
        cond_3 = row["5일공매도비중(%)"] >= 5.0
        cond_4 = row["거래량비율"] >= 2.0
        cond_5 = row["종가위산20일이평선상회"]
        cond_6 = row["수익률_1일"] >= 3.0
        cond_7 = row["종가위치(%)"] >= 70.0
        cond_8 = row["당일거래대금(억)"] >= 100

        sq_passed = all([cond_1, cond_2, cond_3, cond_4, cond_5, cond_6, cond_7, cond_8])
        
        sq_bonus = 0
        if sq_passed:
            # 조건 만족도에 따른 세부 보너스 (+2 ~ +5점)
            sq_bonus = 5 if (row["공매도잔고비중(%)"] >= 4.5 and row["DtC(일)"] >= 3.5) else 3

        # 5. 최종 우선순위 산식
        closing_normalized = (closing_score / 45.0) * 100
        final_priority = (growth_score * 0.7) + (closing_normalized * 0.3) + sq_bonus

        # 6. 리스크 진단 자동 판정 (단기 / 중기 / 장기)
        short_risk = "안정" if row["5일이격도"] < 108 else "과열 주의"
        medium_risk = "정배열 유지" if row["정배열여부"] else "역배열 이탈 주의"
        long_risk = "추세 상승" if row["수익률_1개월"] > 0 else "장기 하락 압력"

        return pd.Series({
            "상승가능성점수": growth_score,
            "종가베팅점수": closing_score,
            "과열개수": overheat_count,
            "과열감점": penalty,
            "숏스퀴즈적합여부": "🔴 Squeeze Candidate" if sq_passed else "⚪ 일반 종목",
            "숏스퀴즈보너스": sq_bonus,
            "최종우선순위점수": round(final_priority, 2),
            "단기리스크": short_risk,
            "중기리스크": medium_risk,
            "장기리스크": long_risk
        })

    scores = df.apply(process_row, axis=1)
    result = pd.concat([df, scores], axis=1)

    def judge(row):
        if (row["상승가능성점수"] >= 75 and 
            row["종가베팅점수"] >= 34 and 
            row["당일거래대금(억)"] >= 100 and 
            row["거래량비율"] >= 2.0 and
            row["종가위치(%)"] >= 70 and
            row["정배열여부"] and
            row["동시호가체결플러스"]):
            
            if row["최종우선순위점수"] >= 85: return "🔴 최우선 검토"
            elif row["최종우선순위점수"] >= 78: return "🟠 적극 관찰"
            else: return "🟡 눌림목 대기"
        else:
            return "⚪ 진입 보류"

    result["진입판정"] = result.apply(judge, axis=1)
    return result.sort_values(by="최종우선순위점수", ascending=False).reset_index(drop=True)
