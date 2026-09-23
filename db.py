import sqlite3
import os

DB_PATH = "moneyflow.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    # WAL 모드 적용 (동시성 향상)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # [기존 테이블 유지] candidates, disclosures, calendar_events, meta 등
    # ... (기존 init_db 로직 생략) ...

    # 🆕 차트 분석 및 룰베이스/LLM 결과 저장 공유 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chart_analysis (
            code TEXT PRIMARY KEY,
            name TEXT,
            timeframe TEXT DEFAULT 'D',
            rule_score INT,              -- 룰베이스 정량 점수 (0~100)
            trend_status TEXT,          -- 기술적 패턴 상태
            rsi REAL,                   -- RSI 지표
            macd_signal TEXT,           -- MACD 신호
            moving_avg_status TEXT,     -- 이평선 정배열 상태
            support_price REAL,         -- 지지선
            resistance_price REAL,      -- 저항선
            rule_summary TEXT,          -- 룰베이스 요약 메시지
            ai_summary TEXT,            -- LLM (Gemini/OpenAI) 종합 차트 진단
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
