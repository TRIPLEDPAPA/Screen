"""한경 공개 전종목 목록: 분류 원본 보존, 원자적 캐시, 부분 조회 실패 시 기존 캐시 유지."""
import datetime as dt
import json
import os
import re
from pathlib import Path
import requests
SOURCE='https://datacenter.hankyung.com/equities-all/korea'
FILE=Path(os.getenv('MASTER_PATH',str(Path(__file__).parent/'stock_master.json')))

def normalize(payload,market):
    if not isinstance(payload,dict) or not isinstance(payload.get('data'),list):
        raise ValueError('한경 응답 형식 변경 · data 목록 없음')
    rows=[]
    for group in payload['data']:
        industry=str(group.get('name') or '기타').strip()
        for stock in group.get('sub',[]):
            code=str(stock.get('shortcode') or '').strip()
            name=str(stock.get('name') or '').strip()
            if not re.fullmatch(r'[0-9A-Z]{6}',code) or not name: continue
            # 상품명 기반 제외는 보조 검사. 원본 페이지 범위는 국내주식 목록.
            if re.search(r'ETF|ETN|KODEX|TIGER|KOSEF|KBSTAR|ARIRANG|HANARO|SOL |ACE |RISE |PLUS ',name,re.I): continue
            rows.append({'code':code,'name':name,'market':market,'source_industry':industry,'industry_source':'한경 전종목시세','industry':industry})
    if not rows: raise ValueError(market+' 종목 없음 · 기존 목록 보존')
    return rows

def read():
    try:
        value=json.loads(FILE.read_text(encoding='utf-8'))
        return value if isinstance(value,dict) and isinstance(value.get('rows'),list) else {'rows':[],'status':'캐시 형식 오류'}
    except (OSError,ValueError): return {'rows':[],'status':'최초 수집 대기'}

def refresh(force=False):
    old=read()
    if old.get('rows') and not force: return old
    rows=[]
    for market in ['kospi','kosdaq']:
        r=requests.get(SOURCE,params={'type':market},headers={'User-Agent':'MoneyFlow/1.0','Referer':'https://datacenter.hankyung.com/equities-all'},timeout=15)
        r.raise_for_status(); rows.extend(normalize(r.json(),market.upper()))
    unique={r['code']:r for r in rows}
    if len(unique)!=len(rows): raise ValueError('중복 종목코드 · 목록 갱신 보류')
    result={'rows':list(unique.values()),'collected_at':dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(),'source':SOURCE,'status':'수집 완료','classification':'한경 원본 업종. 사용자 세분류와 다를 수 있음'}
    FILE.parent.mkdir(parents=True,exist_ok=True)
    temp=FILE.with_suffix('.tmp');temp.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8');temp.replace(FILE)
    return result

def profile(code):
    return next((r for r in read().get('rows',[]) if r['code']==code),None)
if __name__=='__main__':
    try:
        result=refresh(force=True)
        print('수집 완료:',len(result['rows']),'종목',result['collected_at'])
    except (requests.RequestException,ValueError) as e:
        print('수집 실패 · 기존 캐시 유지:',type(e).__name__)
        raise SystemExit(1)
