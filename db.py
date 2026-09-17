"""db.py - 데이터 로드 및 숏스퀴즈/이격도 감점/정량 엔진"""
import pandas as pd
import numpy as np
from sector_master import SECTOR_CHAINS, get_stock_profile

def load_market_data():
    rows = []
    np.random.seed(42)
    
    for sector, roles in SECTOR_CHAINS.items():
        for role_name, stock_list in roles.items():
            for name in stock_list:
                sec, role, code = get_stock_profile(name)
                
                cur_price = np.random.randint(15000, 350000)
                chg = round(np.random.uniform(-1.5, 9.5), 2)
                turnover = np.random.randint(150, 3000) * 100_000_000
                
                d5 = round(np.random.uniform(98, 114), 1)
                d10 = round(np.random.uniform(99, 118), 1)
                d20 = round(np.random.uniform(96, 122), 1)
                d60 = round(np.random.uniform(94, 135), 1)
                
                rows.append({
                    "종목코드": code,
                    "종목명": name,
                    "섹터": sec,
                    "역할": role,
                    "현재가": cur_price,
                    "등락률": chg,
                    "거래대금": turnover,
                    "거래량비율": round(np.random.uniform(1.1, 4.2), 2),
                    "종가위치": round(np.random.uniform(60, 98), 1),
                    "외인5일순매수": np.random.randint(-3000, 25000),
                    "기관5일순매수": np.random.randint(-2000, 18000),
                    "정배열여부": np.random.choice([True, False], p=[0.75, 0.25]),
                    "동시호가체결플러스": np.random.choice([True, False], p=[0.8, 0.2]),
                    
                    "5일이격도": d5,
                    "10일이격도": d10,
                    "20일이격도": d20,
                    "60일이격도": d60,
                    
                    "공매도잔고비중": round(np.random.uniform(0.5, 5.5), 1),
                    "DtC": round(np.random.uniform(0.8, 4.2), 1),
                    "5일공매도비중": round(np.random.uniform(1.0, 8.0), 1),
                    "종가위산20일이평선상회": np.random.choice([True, False], p=[0.8, 0.2]),
                    
                    # 메인 테이블용 초단기 시계열 (5일 ~ 1일)
                    "수익률_5일": round(np.random.uniform(-3, 15), 2),
                    "수익률_4일": round(np.random.uniform(-2, 10), 2),
                    "수익률_3일": round(np.random.uniform(-2, 8), 2),
                    "수익률_2일": round(np.random.uniform(-2, 6), 2),
                    "수익률_1일": chg,
                    
                    # 상세 모달용 중장기 시계열 (1년, 6개월, 3개월, 1개월, 20일, 10일)
                    "수익률_1년": round(np.random.uniform(-30, 200), 2),
                    "수익률_6개월": round(np.random.uniform(-20, 120), 2),
                    "수익률_3개월": round(np.random.uniform(-15, 80), 2),
                    "수익률_1개월": round(np.random.uniform(-10, 45), 2),
                    "수익률_20일": round(np.random.uniform(-8, 30), 2),
                    "수익률_10일": round(np.random.uniform(-5, 20), 2),

                    "키맞추기룸": round(np.random.uniform(0.0, 7.5), 1),
                    "PER": round(np.random.uniform(8, 50), 1),
                    "PBR": round(np.random.uniform(0.9, 5.8), 1),
                    "ROE": round(np.random.uniform(5, 30), 1),
                    "배당수익률": round(np.random.uniform(0, 3.5), 1),
                    "수주여부": np.random.choice([True, False], p=[0.7, 0.3]),
                    "내부자매수": np.random.choice([True, False], p=[0.4, 0.6]),
                })
                
    return pd.DataFrame(rows)

def calculate_quant_engine(df):
    def process_row(row):
        overheat_count = 0
        if row["5일이격도"] >= 108: overheat_count += 1
        if row["10일이격도"] >= 112: overheat_count += 1
        if row["20일이격도"] >= 115: overheat_count += 1
        if row["60일이격도"] >= 130: overheat_count += 1

        penalty = 0
        if overheat_count == 2: penalty = 3
        elif overheat_count == 3: penalty = 6
        elif overheat_count >= 4: penalty = 10

        sec_score = 16 
        fund_score = 15 
        sup_score = 15 if (row["외인5일순매수"] > 0 and row["기관5일순매수"] > 0) else 8 
        trend_score = 22 if row["정배열여부"] else 10 
        risk_score = max(0, 15 - penalty)
        growth_score = sec_score + fund_score + sup_score + trend_score + risk_score

        t_amt = row["거래대금"] / 100_000_000
        s_amt = 6 if t_amt >= 1000 else (5 if t_amt >= 500 else (4 if t_amt >= 300 else (3 if t_amt >= 100 else 0)))
        v_rat = row["거래량비율"]
        s_vol = 5 if v_rat >= 3 else (4 if v_rat >= 2 else (3 if v_rat >= 1.5 else (1 if v_rat >= 1.2 else 0)))
        c_pos = row["종가위치"]
        s_pos = 5 if c_pos >= 90 else (4 if c_pos >= 80 else (3 if c_pos >= 70 else (1 if c_pos >= 60 else 0)))
        chg = row["등락률"]
        s_chg = 4 if (3 <= chg <= 8) else (3 if (1 <= chg < 3) else (2 if (8 < chg <= 12) else (1 if 0 <= chg < 1 else 0)))

        closing_score = s_amt + s_vol + s_pos + s_chg + 5 + 3 + (5 if row["정배열여부"] else 0) + 3 + 2 + 3

        # 숏스퀴즈 엄격 8대 게이트
        cond_1 = row["공매도잔고비중"] >= 3.0
        cond_2 = row["DtC"] >= 2.0
        cond_3 = row["5일공매도비중"] >= 5.0
        cond_4 = row["거래량비율"] >= 2.0
        cond_5 = row["종가위산20일이평선상회"]
        cond_6 = row["등락률"] >= 3.0
        cond_7 = row["종가위치"] >= 70.0
        cond_8 = t_amt >= 100

        sq_passed = all([cond_1, cond_2, cond_3, cond_4, cond_5, cond_6, cond_7, cond_8])
        sq_bonus = 5 if (sq_passed and row["공매도잔고비중"] >= 4.5 and row["DtC"] >= 3.0) else (3 if sq_passed else 0)

        closing_normalized = (closing_score / 45.0) * 100
        final_priority = (growth_score * 0.7) + (closing_normalized * 0.3) + sq_bonus

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
        if row["상승가능성점수"] >= 75 and row["종가베팅점수"] >= 30 and row["동시호가체결플러스"]:
            if row["최종우선순위점수"] >= 85: return "🔴 최우선 검토"
            elif row["최종우선순위점수"] >= 78: return "🟠 적극 관찰"
            else: return "🟡 눌림목 대기"
        return "⚪ 진입 보류"

    result["진입판정"] = result.apply(judge, axis=1)
    return result.sort_values(by="최종우선순위점수", ascending=False).reset_index(drop=True)
