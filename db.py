"""SQLite 기반 주식 데이터 및 분석 지표 영구 보존 모듈 (db.py)"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent / "market_data.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()

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
            ref_5d REAL,
            ref_10d REAL,
            ref_30d REAL,
            ref_3m REAL,
            ref_6m REAL,
            ref_1y REAL,
            detail_json TEXT,
            updated_at TEXT
        );
        """)

        # 기존 테이블 마이그레이션 대비 컬럼 확인 및 추가
        cursor.execute("PRAGMA table_info(daily_candidates);")
        columns = [row["name"] for row in cursor.fetchall()]
        for col in ["ref_5d", "ref_10d", "ref_30d", "ref_3m", "ref_6m", "ref_1y"]:
            if col not in columns:
                cursor.execute(f"ALTER TABLE daily_candidates ADD COLUMN {col} REAL;")
        if "detail_json" not in columns:
            cursor.execute("ALTER TABLE daily_candidates ADD COLUMN detail_json TEXT;")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """)
        conn.commit()


def upsert_candidates(candidates: list[dict[str, Any]], time_str: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        for item in candidates:
            m = item.get("metrics", {})
            ref = item.get("past_ref_prices", {})

            detail_data = {
                "fundamentals": item.get("fundamentals", {}),
                "short_selling": item.get("short_selling", {}),
                "twenty_metrics": item.get("twenty_metrics", []),
                "risks": item.get("risks", {}),
                "ai_briefing": item.get("ai_briefing", ""),
                "upside_probability": item.get("upside_probability", 50),
                "upside_status": item.get("upside_status", "중립 관망"),
                "technical": item.get("technical", {})
            }

            cursor.execute("""
            INSERT INTO daily_candidates (
                code, name, industry, role, score, max_score,
                current_price, change_pct, turnover, turnover_100m,
                foreign_inst_net, ref_5d, ref_10d, ref_30d, ref_3m, ref_6m, ref_1y, detail_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                ref_5d=excluded.ref_5d,
                ref_10d=excluded.ref_10d,
                ref_30d=excluded.ref_30d,
                ref_3m=excluded.ref_3m,
                ref_6m=excluded.ref_6m,
                ref_1y=excluded.ref_1y,
                detail_json=excluded.detail_json,
                updated_at=excluded.updated_at;
            """, (
                item["code"], item["name"], item.get("industry", "기타"),
                item.get("role", "후발 수혜"), item.get("score", 0), item.get("max_score", 100),
                m.get("current_price", 0), m.get("change_pct", 0), m.get("turnover", 0),
                m.get("turnover_100m", 0), item.get("foreign_inst_net", 0),
                ref.get("5d"), ref.get("10d"), ref.get("30d"), ref.get("3m"), ref.get("6m"), ref.get("1y"),
                json.dumps(detail_data, ensure_ascii=False),
                time_str
            ))

        cursor.execute("INSERT OR REPLACE INTO market_meta (key, value) VALUES ('base_time', ?)", (time_str,))
        conn.commit()


def get_all_candidates() -> list[dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM daily_candidates ORDER BY score DESC, turnover DESC;")
        rows = cursor.fetchall()

        results = []
        for row in rows:
            r = dict(row)
            detail_dict = {}
            if r.get("detail_json"):
                try:
                    detail_dict = json.loads(r["detail_json"])
                except Exception:
                    pass

            cur_p = r["current_price"] or 1.0
            r5d = round(((cur_p - (r["ref_5d"] or cur_p)) / (r["ref_5d"] or cur_p)) * 100, 1)
            r10d = round(((cur_p - (r["ref_10d"] or cur_p)) / (r["ref_10d"] or cur_p)) * 100, 1)
            r30d = round(((cur_p - (r["ref_30d"] or cur_p)) / (r["ref_30d"] or cur_p)) * 100, 1)
            r3m = round(((cur_p - (r["ref_3m"] or cur_p)) / (r["ref_3m"] or cur_p)) * 100, 1)
            r6m = round(((cur_p - (r["ref_6m"] or cur_p)) / (r["ref_6m"] or cur_p)) * 100, 1)
            r1y = round(((cur_p - (r["ref_1y"] or cur_p)) / (r["ref_1y"] or cur_p)) * 100, 1)

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
                        "5일": r5d,
                        "10일": r10d,
                        "30일": r30d,
                        "3개월": r3m,
                        "6개월": r6m,
                        "1년": r1y
                    }
                },
                "past_ref_prices": {
                    "5d": r["ref_5d"],
                    "10d": r["ref_10d"],
                    "30d": r["ref_30d"],
                    "3m": r["ref_3m"],
                    "6m": r["ref_6m"],
                    "1y": r["ref_1y"],
                },
                "fundamentals": detail_dict.get("fundamentals", {}),
                "short_selling": detail_dict.get("short_selling", {}),
                "twenty_metrics": detail_dict.get("twenty_metrics", []),
                "risks": detail_dict.get("risks", {}),
                "ai_briefing": detail_dict.get("ai_briefing", ""),
                "upside_probability": detail_dict.get("upside_probability", 50),
                "upside_status": detail_dict.get("upside_status", "중립 관망"),
                "technical": detail_dict.get("technical", {})
            })
        return results


def get_meta(key: str, default: str = "") -> str:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM market_meta WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default
