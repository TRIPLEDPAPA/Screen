import os
import json
import pandas as pd
import numpy as np
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from db import get_db_connection, init_db

# (필요 시 OpenAI / Google Gemini SDK import)
# import google.generativeai as genai
# import openai

app = FastAPI()

# 최초 실행 시 DB 초기화
init_db()

# ================= ================= =================
# 🧠 1. 백엔드 룰베이스 알고리즘 (정량 분석)
# ================= ================= =================
def run_rule_based_chart_analysis(df: pd.DataFrame):
    """
    Pandas 기반 기술적 지표 산출 및 룰베이스 채점 Engine
    """
    close = df['close']
    
    # 1) 이동평균선 산출
    ma5 = close.rolling(window=5).mean().iloc[-1]
    ma20 = close.rolling(window=20).mean().iloc[-1]
    ma60 = close.rolling(window=60).mean().iloc[-1]
    current_price = close.iloc[-1]

    # 정배열 여부 판단
    if current_price > ma5 > ma20 > ma60:
        ma_status = "완전 정배열 (강한 상승세)"
        ma_score = 35
    elif current_price > ma20 > ma60:
        ma_status = "상승 추세 유지"
        ma_score = 25
    elif ma5 > ma20:
        ma_status = "단기 골든크로스 구간"
        ma_score = 20
    else:
        ma_status = "역배열 / 하락 추세"
        ma_score = 10

    # 2) RSI 산출 (14일)
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    rsi = (100 - (100 / (1 + rs))).iloc[-1]

    if 50 <= rsi <= 65:
        rsi_score = 30
        rsi_msg = "안정적인 상승 수급 구간"
    elif 30 <= rsi < 50:
        rsi_score = 20
        rsi_msg = "관망 및 반등 모색 구간"
    elif rsi > 70:
        rsi_score = 15
        rsi_msg = "과매수 구간 (단기 조정 주의)"
    else:  # rsi < 30
        rsi_score = 10
        rsi_msg = "과매도 구간 (기술적 반등 가능성)"

    # 3) 지지/저항선 (최근 20일 기준)
    support = float(close.tail(20).min())
    resistance = float(close.tail(20).max())
    
    # 지지선 접근 시 가산점
    near_support = abs(current_price - support) / current_price < 0.03
    support_score = 25 if near_support else 15

    # 종합 룰베이스 점수 (100점 만점)
    total_rule_score = ma_score + rsi_score + support_score + 10
    
    rule_summary = f"[이동평균선] {ma_status} | [RSI] {rsi:.1f} ({rsi_msg})"
    
    return {
        "rule_score": min(total_rule_score, 100),
        "trend_status": ma_status,
        "rsi": round(rsi, 1),
        "moving_avg_status": ma_status,
        "support_price": support,
        "resistance_price": resistance,
        "rule_summary": rule_summary
    }

# ================= ================= =================
# 🤖 2. LLM API 연동 (정성 해석)
# ================= ================= =================
def generate_llm_chart_report(stock_name: str, rule_res: dict) -> str:
    """
    룰베이스 분석 결과를 바탕으로 LLM(Gemini/OpenAI)이 투자자용 요약 생성
    """
    prompt = f"""
    당신은 퀀트 및 기술적 분석 전문 AI입니다. 다음 데이터를 바탕으로 {stock_name} 종목의 차트를 2~3문장으로 명확하게 종합 진단해 주세요.
    
    - 룰베이스 점수: {rule_res['rule_score']}점
    - 이평선 상태: {rule_res['moving_avg_status']}
    - RSI 지표: {rule_res['rsi']}
    - 주요 지지선: {rule_res['support_price']}원 / 저항선: {rule_res['resistance_price']}원
    - 핵심 요약: {rule_res['rule_summary']}
    """
    
    # 예시: OpenAI/Gemini 호출 로직 (API 키 미설정 시 대체 프롬프트 출력)
    try:
        # response = openai.ChatCompletion.create(...) 또는 genai.generate_text(...)
        # return response.text
        return f"{stock_name} 차트는 {rule_res['moving_avg_status']} 양상을 보이고 있습니다. RSI({rule_res['rsi']}) 지표상 {rule_res['rule_summary'].split('|')[1].strip()}에 위치하며, 주요 지지선({rule_res['support_price']:,.0f}원) 부근에서 단기 방향성을 타진할 것으로 판단됩니다."
    except Exception as e:
        return f"현재 {rule_res['moving_avg_status']} 상태이며, 지지선 단기 반등 모멘텀을 주시할 필요가 있습니다."

# ================= ================= =================
# 📡 3. API 엔드포인트
# ================= ================= =================
@app.get("/api/chart-analysis")
def get_chart_analysis(code: str = Query(None)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1) 특정 종목 요청 시
    if code:
        cursor.execute("SELECT * FROM chart_analysis WHERE code = ?", (code,))
        row = cursor.fetchone()
        
        # 데이터가 없을 경우 실시간 계산 후 DB 저장 (On-Demand)
        if not row:
            # 임시 시뮬레이션 가격 데이터 생성 (실제 서비스 시 yfinance 또는 HTS API 연동)
            dates = pd.date_range(end=pd.Timestamp.now(), periods=60)
            prices = np.cumsum(np.random.randn(60)) + 10000
            df = pd.DataFrame({'close': prices}, index=dates)
            
            # 종목명 가져오기
            cursor.execute("SELECT name FROM candidates WHERE code = ?", (code,))
            cand_row = cursor.fetchone()
            stock_name = cand_row['name'] if cand_row else f"종목({code})"
            
            # 룰베이스 & LLM 분석 실행
            rule_res = run_rule_based_chart_analysis(df)
            llm_report = generate_llm_chart_report(stock_name, rule_res)
            
            # DB 저장 (DB 공유)
            cursor.execute('''
                INSERT OR REPLACE INTO chart_analysis 
                (code, name, timeframe, rule_score, trend_status, rsi, macd_signal, moving_avg_status, support_price, resistance_price, rule_summary, ai_summary, updated_at)
                VALUES (?, ?, 'D', ?, ?, ?, '매수우위', ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                code, stock_name, rule_res['rule_score'], rule_res['trend_status'], 
                rule_res['rsi'], rule_res['moving_avg_status'], rule_res['support_price'], 
                rule_res['resistance_price'], rule_res['rule_summary'], llm_report
            ))
            conn.commit()
            
            cursor.execute("SELECT * FROM chart_analysis WHERE code = ?", (code,))
            row = cursor.fetchone()
            
        conn.close()
        return dict(row)
    
    # 2) 코드 입력 없이 요청 시 상위 차트 점수 목록 반환
    else:
        cursor.execute("SELECT * FROM chart_analysis ORDER BY rule_score DESC LIMIT 30")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

@app.get("/")
def read_root():
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())
