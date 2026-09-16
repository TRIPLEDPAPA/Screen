"""SQLite 기반 주식 데이터 및 분석 지표 영구 보존 모듈 (db.py)"""

import json
import sqlite3
from typing import Any

DB_PATH = "market_data.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    # WAL 모드 활성화 (스케줄러가 쓰는 중에도 웹 조회가 멈추지 않음)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """테이블 초기화"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # 1. 일별 분석 후보 종목 테이블 (시세, 수급, 기술지표)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_candidates (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            industry TEXT,
            role TEXT,
            score INTEGER,
            max_score INTEGER,
            current_price REAL,
            change_pct REAL,
            turnover REAL,
            turnover_100m REAL,
            foreign_inst_net INTEGER,
            return_1y REAL,
            return_6m REAL,
            return_3m REAL,
            return_1m REAL,
            return_5d REAL,
            updated_at TEXT
        );
        """)

        # 2. 월별 투자지표 및 실적 캐시 테이블 (월 1회 갱신)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_fundamentals (
            code TEXT PRIMARY KEY,
            per REAL,
            pbr REAL,
            roe REAL,
            dividend_yield REAL,
            revenue INTEGER,
            operating_profit INTEGER,
            op_margin REAL,
            debt_ratio REAL,
            updated_ym TEXT
        );
        """)

        # 3. 공매도 분석 테이블
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_short_selling (
            code TEXT PRIMARY KEY,
            short_ratio REAL,
            balance_ratio REAL,
            is_short_squeeze INTEGER,
            updated_at TEXT
        );
        """)

        # 4. DART 주요 공시 테이블
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_disclosures (
            id TEXT PRIMARY KEY,
            code TEXT,
            report_nm TEXT,
            rcept_dt TEXT,
            category TEXT
        );
        """)

        # 5. 시장 메타데이터 (최종 스캔 시점 등)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """)
        conn.commit()


def upsert_candidates(candidates: list[dict[str, Any]], time_str: str):
    """분석 후보 목록 일괄 저장 (UPSERT)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        for item in candidates:
            m = item.get("metrics", {})
            r = m.get("returns", {})
            cursor.execute("""
            INSERT INTO daily_candidates (
                code, name, industry, role, score, max_score,
                current_price, change_pct, turnover, turnover_100m,
                foreign_inst_net, return_1y, return_6m, return_3m, return_1m, return_5d, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                name=excluded.name,
                industry=excluded.industry,
                role=excluded.role,
                score=excluded.score,
                max_score=excluded.max_score,
                current_price=excluded.current_price,
                change_pct=excluded.change_pct,
                turnover=excluded.turnover,
                turnover_100m=excluded.turnover_100m,
                foreign_inst_net=excluded.foreign_inst_net,
                return_1y=excluded.return_1y,
                return_6m=excluded.return_6m,
                return_3m=excluded.return_3m,
                return_1m=excluded.return_1m,
                return_5d=excluded.return_5d,
                updated_at=excluded.updated_at;
            """, (
                item["code"], item["name"], item.get("industry", "기타"),
                item.get("role", "후발 수혜"), item.get("score", 0), item.get("max_score", 100),
                m.get("current_price", 0), m.get("change_pct", 0), m.get("turnover", 0),
                m.get("turnover_100m", 0), item.get("foreign_inst_net", 0),
                r.get("1년"), r.get("6개월"), r.get("3개월"), r.get("1개월"), r.get("5일"),
                time_str
            ))

        cursor.execute("INSERT OR REPLACE INTO market_meta (key, value) VALUES ('base_time', ?)", (time_str,))
        conn.commit()


def get_all_candidates() -> list[dict[str, Any]]:
    """대시보드 표시용 후보 목록 조회"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM daily_candidates ORDER BY score DESC, turnover DESC;")
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            r = dict(row)
            results.append({
                "code": r["code"],
                "name": r["name"],
                "industry": r["industry"],
                "role": r["role"],
                "score": r["score"],
                "max_score": r["max_score"],
                "foreign_inst_net": r["foreign_inst_net"],
                "metrics": {
                    "current_price": r["current_price"],
                    "change_pct": r["change_pct"],
                    "turnover": r["turnover"],
                    "turnover_100m": r["turnover_100m"],
                    "returns": {
                        "1년": r["return_1y"],
                        "6개월": r["return_6m"],
                        "3개월": r["return_3m"],
                        "1개월": r["return_1m"],
                        "5일": r["return_5d"],
                    }
                }
            })
        return results


def get_meta(key: str, default: str = "") -> str:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM market_meta WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default
