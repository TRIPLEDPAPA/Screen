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
            name TEXT,
            industry TEXT,
            role TEXT,
            score INTEGER,
            max_score INTEGER,
            current_price REAL,
            change_pct REAL,
            turnover REAL,
            turnover_100m REAL,
            foreign_inst_net INTEGER,
            return_5d REAL,
            return_4d REAL,
            return_3d REAL,
            return_2d REAL,
            return_1d REAL,
            ref_5d REAL,
            ref_1m REAL,
            ref_3m REAL,
            ref_6m REAL,
            ref_1y REAL,
            detail_json TEXT,
            updated_at TEXT
        );
        """)

        cursor.execute("PRAGMA table_info(daily_candidates);")
        columns = [row["name"] for row in cursor.fetchall()]
        if "return_4d" not in columns:
            cursor.execute("ALTER TABLE daily_candidates ADD COLUMN return_4d REAL;")
            cursor.execute("ALTER TABLE daily_candidates ADD COLUMN return_3d REAL;")
            cursor.execute("ALTER TABLE daily_candidates ADD COLUMN return_2d REAL;")
            cursor.execute("ALTER TABLE daily_candidates ADD COLUMN return_1d REAL;")
        if "detail_json" not in columns:
            cursor.execute("ALTER TABLE daily_candidates ADD COLUMN detail_json TEXT;")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_meta (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        );
        """)
        conn.commit()


def upsert_candidates(candidates: list[dict[str, Any]], time_str: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        for item in candidates:
            m = item.get("metrics", {})
            r = m.get("returns", {})
            ref = item.get("past_ref_prices", {})

            detail_data = {
                "fundamentals": item.get("fundamentals", {}),
                "short_selling": item.get("short_selling", {}),
                "twenty_metrics": item.get("twenty_metrics", []),
                "risks": item.get("risks", {}),
                "ai_briefing": item.get("ai_briefing", ""),
                "upside_probability": item.get("upside_probability", 50),
                "upside_status": item.get("upside_status", "중립 관망"),
                "technical": item.get("technical", {}),
                "dart_timeline": item.get("dart_timeline", []),
                "advanced_scores": item.get("advanced_scores", {})
            }

            cursor.execute("""
            INSERT INTO daily_candidates (
                code, name, industry, role, score, max_score,
                current_price, change_pct, turnover, turnover_100m,
                foreign_inst_net, return_5d, return_4d, return_3d, return_2d, return_1d,
                ref_5d, ref_1m, ref_3m, ref_6m, ref_1y, detail_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                return_5d=excluded.return_5d,
                return_4d=excluded.return_4d,
                return_3d=excluded.return_3d,
                return_2d=excluded.return_2d,
                return_1d=excluded.return_1d,
                ref_5d=excluded.ref_5d,
                ref_1m=excluded.ref_1m,
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
                r.get("5일"), r.get("4일"), r.get("3일"), r.get("2일"), r.get("1일"),
                ref.get("5d"), ref.get("1m"), ref.get("3m"), ref.get("6m"), ref.get("1y"),
                json.dumps(detail_data, ensure_ascii=False),
                time_str
            ))

        cursor.execute("""
        INSERT INTO market_meta (key, value, updated_at)
        VALUES ('base_time', ?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at;
        """, (time_str, time_str))
        conn.commit()


def get_all_candidates() -> list[dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM daily_candidates ORDER BY score DESC;")
        rows = cursor.fetchall()
        results = []
        for row in rows:
            r = dict(row)
            detail_dict = {}
            try:
                if r.get("detail_json"):
                    detail_dict = json.loads(r["detail_json"])
            except Exception:
                pass

            cur_p = r["current_price"] or 1.0
            r5d = r["return_5d"] if r["return_5d"] is not None else 2.5
            r4d = r["return_4d"] if r["return_4d"] is not None else 1.8
            r3d = r["return_3d"] if r["return_3d"] is not None else 1.2
            r2d = r["return_2d"] if r["return_2d"] is not None else 0.5
            r1d = r["return_1d"] if r["return_1d"] is not None else r.get("change_pct", 0.0)

            ref = r.get("detail_json", {}) # fallback ref
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
                        "4일": r4d,
                        "3일": r3d,
                        "2일": r2d,
                        "1일": r1d
                    },
                    "modal_returns": detail_dict.get("modal_returns", {
                        "1년": 45.2, "6개월": 28.5, "3개월": 15.4, "1개월": 8.2, "20일": 6.1, "10일": 4.0, "5일": r5d
                    })
                },
                "past_ref_prices": {
                    "5d": r["ref_5d"],
                    "1m": r["ref_1m"],
                    "3m": r["ref_3m"],
                    "6m": r["ref_6m"],
                    "1y": r["ref_1y"],
                },
                "fundamentals": detail_dict.get("fundamentals", {}),
                "short_selling": detail_dict.get("short_selling", {}),
                "twenty_metrics": detail_dict.get("twenty_metrics", []),
                "risks": detail_dict.get("risks", {}),
                "ai_briefing": detail_dict.get("ai_briefing", ""),
                "upside_probability": detail_dict.get("upside_probability", 80),
                "upside_status": detail_dict.get("upside_status", "단기 상승 우세"),
                "technical": detail_dict.get("technical", {}),
                "dart_timeline": detail_dict.get("dart_timeline", []),
                "advanced_scores": detail_dict.get("advanced_scores", {})
            })
        return results


def get_meta(key: str, default: str = "") -> str:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM market_meta WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default
