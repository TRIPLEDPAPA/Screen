"""50개 섹터 및 밸류체인 마스터 데이터 (sector_master.py)"""

import db

def get_ticker_map() -> dict[str, str]:
    mapping = {
        "삼성전자": "005930", "SK하이닉스": "000660", "LG에너지솔루션": "373220",
        "현대차": "005380", "NAVER": "035420", "기아": "000270", "POSCO홀딩스": "005490"
    }
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, code FROM stock_list")
        rows = cursor.fetchall()
        conn.close()
        for r in rows:
            if r["name"] and r["code"]:
                mapping[r["name"].strip()] = str(r["code"]).zfill(6)
    except Exception:
        pass
    return mapping

TICKER_MAP = get_ticker_map()
