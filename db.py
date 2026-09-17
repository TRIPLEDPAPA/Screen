#!/usr/bin/env python3
"""Money Flow 데이터베이스 최적화 및 고속 I/O 관리 모듈"""

from __future__ import annotations
import sqlite3
import json
from pathlib import Path

DB_FILE = Path(__file__).resolve().parent / "money_flow.db"

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    # WAL 모드 활성화로 동시성 및 쓰기 성능 극대화
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # 1. 퀀트 후보 종목 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            code TEXT PRIMARY KEY,
            name TEXT,
            industry TEXT,
            role TEXT,
            score INTEGER,
            max_score INTEGER,
            foreign_inst_net INTEGER,
            data_json TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_candidates_industry ON candidates(industry);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_candidates_score ON candidates(score DESC);")

    # 2. DART 공시 피드 테이블 (월/일 및 키워드 인덱싱)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS disclosures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_md TEXT,
            time TEXT,
            category TEXT,
            title TEXT,
            tag TEXT,
            tag_color TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_disclosures_date ON disclosures(date_md DESC);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_disclosures_category ON disclosures(category);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_disclosures_title ON disclosures(title);")

    # 3. 캘린더 일정 테이블 (2026년 연간 관리)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calendar_events (
            id TEXT PRIMARY KEY,
            category TEXT,
            date_md TEXT,
            time TEXT,
            title TEXT,
            country TEXT,
            tag TEXT,
            tag_color TEXT,
            actual TEXT,
            forecast TEXT,
            source TEXT,
            ai_summary TEXT,
            status TEXT DEFAULT 'SCHEDULED',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_calendar_date ON calendar_events(date_md);")

    # 4. 자사주 매입·소각 추적 테이블 (시총 1조 이상)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS buybacks (
            code TEXT PRIMARY KEY,
            name TEXT,
            market_cap INTEGER,
            announcement_date TEXT,
            plan_period TEXT,
            plan_qty INTEGER,
            plan_amount INTEGER,
            buy_type TEXT,
            actual_price REAL,
            actual_days INTEGER,
            cancellation_status TEXT,
            sh_reduction INTEGER,
            shareholder_return_pct REAL,
            data_json TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_buybacks_date ON buybacks(announcement_date DESC);")

    # 5. 메타 정보 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    conn.commit()
    conn.close()

def upsert_candidates(records: list[dict], time_str: str):
    conn = get_connection()
    cursor = conn.cursor()
    for r in records:
        cursor.execute("""
            INSERT INTO candidates (code, name, industry, role, score, max_score, foreign_inst_net, data_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                name=excluded.name, industry=excluded.industry, role=excluded.role,
                score=excluded.score, max_score=excluded.max_score,
                foreign_inst_net=excluded.foreign_inst_net, data_json=excluded.data_json,
                updated_at=CURRENT_TIMESTAMP
        """, (
            r["code"], r["name"], r["industry"], r["role"], r["score"], r["max_score"],
            r["foreign_inst_net"], json.dumps(r, ensure_ascii=False)
        ))
    cursor.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('base_time', ?)", (time_str,))
    conn.commit()
    conn.close()

def get_all_candidates() -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT data_json FROM candidates ORDER BY score DESC")
    rows = cursor.fetchall()
    conn.close()
    return [json.loads(row["data_json"]) for row in rows]

def get_meta(key: str, default: str = "") -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM meta WHERE key=?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default
