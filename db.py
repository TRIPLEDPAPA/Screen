import sqlite3
import json
import os

DB_PATH = "moneyflow.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. candidates (분석 후보 종목) 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            code TEXT PRIMARY KEY,
            name TEXT,
            category TEXT,
            role TEXT,
            score INTEGER DEFAULT 0,
            price REAL DEFAULT 0,
            change_rate REAL DEFAULT 0.0,
            day1 REAL DEFAULT 0.0,
            day2 REAL DEFAULT 0.0,
            day3 REAL DEFAULT 0.0,
            day4 REAL DEFAULT 0.0,
            day5 REAL DEFAULT 0.0,
            volume TEXT DEFAULT '0억',
            net_buy TEXT DEFAULT '0주',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. disclosures (공시) 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS disclosures (
            id TEXT PRIMARY KEY,
            title TEXT,
            stock_name TEXT,
            stock_code TEXT,
            category TEXT,
            created_at TEXT
        )
    ''')

    # 3. calendar_events (일정) 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS calendar_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_key TEXT,
            event_type TEXT,
            date_str TEXT,
            title TEXT,
            importance TEXT,
            ai_summary TEXT
        )
    ''')

    # 4. chart_analysis (차트분석 및 AI 결과 공유) 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chart_analysis (
            code TEXT PRIMARY KEY,
            name TEXT,
            timeframe TEXT DEFAULT 'D',
            rule_score INT DEFAULT 0,
            trend_status TEXT,
            rsi REAL DEFAULT 50.0,
            macd_signal TEXT,
            moving_avg_status TEXT,
            support_price REAL DEFAULT 0,
            resistance_price REAL DEFAULT 0,
            rule_summary TEXT,
            ai_summary TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 5. meta (시스템 상태)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    conn.commit()
    conn.close()

def get_all_candidates():
    """main.py lifespan 및 전체 조회 시 안전하게 리스트 반환"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM candidates ORDER BY score DESC, price DESC")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()

def update_candidate_price(code: str, price: float, change_rate: float):
    """실시간 시세 수집 후 DB 및 차트 분석 테이블 동시 연동"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE candidates 
            SET price = ?, change_rate = ?, updated_at = CURRENT_TIMESTAMP
            WHERE code = ?
        """, (price, change_rate, code))
        
        # 차트 분석 DB의 지지/저항선도 가격 변경 시 동기화
        cursor.execute("""
            UPDATE chart_analysis 
            SET support_price = ?, resistance_price = ?, updated_at = CURRENT_TIMESTAMP
            WHERE code = ?
        """, (price * 0.95, price * 1.08, code))
        
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
