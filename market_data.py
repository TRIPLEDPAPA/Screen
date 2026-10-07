"""사용자 지정 출처만 조회. 파싱이 검증되지 않으면 미확보 표시."""
import datetime as dt
import threading
from concurrent.futures import ThreadPoolExecutor
import requests
from bs4 import BeautifulSoup

SOURCES={
 'usdkrw':('macro','https://www.google.com/finance/beta/quote/USD-KRW'),
 'kospi200_fut':('macro','https://kr.investing.com/indices/korea-200-futures'),
 'kospi':('macro','https://kr.investing.com/indices/kospi'),
 'kosdaq':('macro','https://kr.investing.com/indices/kosdaq'),
 'spx':('macro','https://kr.investing.com/indices/us-spx-500'),
 'dji':('macro','https://kr.investing.com/indices/us-30'),
 'nasdaq':('macro','https://kr.investing.com/indices/nasdaq-composite'),
 'wti':('macro','https://kr.investing.com/commodities/crude-oil'),
 'brent':('macro','https://kr.investing.com/commodities/brent-oil'),
 'copper':('macro','https://kr.investing.com/commodities/copper'),
 'corn':('macro','https://kr.investing.com/commodities/us-corn'),
 'btc':('macro','https://www.upbit.com/exchange?code=CRIX.UPBIT.KRW-BTC'),
 'eth':('macro','https://www.upbit.com/exchange?code=CRIX.UPBIT.KRW-ETH'),
 'xrp':('macro','https://www.upbit.com/exchange?code=CRIX.UPBIT.KRW-XRP'),
 'samsung':('night','https://www.gate.com/futures/USDT/SAMSUNG_USDT'),
 'hynix':('night','https://www.gate.com/futures/USDT/SKHYNIX_USDT'),
 'hyundai':('night','https://www.gate.com/futures/USDT/HYUNDAI_USDT'),
 'samsungem':('night','https://www.gate.com/futures/USDT/SAMSUNGEM_USDT'),
 'crypto_fg':('night','https://alternative.me/crypto/fear-and-greed-index/'),
 'kospi_fg':('night','https://fastjusik.com/feargreed'),
 **{f'yield_{n}y':('bonds',f'https://datacenter.hankyung.com/rates-bonds/us{n}yy') for n in [2,5,10,30]}}
_lock=threading.Lock()
_cache={}

def number(value):
    return float(str(value).replace(',','').replace('%','').replace('−','-').strip())

def fetch(key):
    group,url=SOURCES[key]
    stamp=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec='seconds')
    out={'val':'미확보','chg':'','up':False,'source':url,'fetched_at':stamp,'status':'미확보'}
    try:
        if key in ['btc','eth','xrp']:
            r=requests.get('https://api.upbit.com/v1/ticker',params={'markets':'KRW-'+key.upper()},timeout=8)
            r.raise_for_status(); data=r.json()[0]
            price=data['trade_price']; pct=data['signed_change_rate']*100
            out.update(val=f'{price:,.0f}원',chg=f'{pct:+.2f}%',up=pct>0,status='정상',basis='Upbit 전일 기준',source_time=data.get('timestamp'))
        elif key in ['samsung','hynix','hyundai','samsungem']:
            contract=url.rsplit('/',1)[-1]
            r=requests.get('https://api.gateio.ws/api/v4/futures/usdt/tickers',params={'contract':contract},timeout=8)
            r.raise_for_status(); data=r.json()
            row=next((x for x in data if x.get('contract')==contract),None)
            if not row: raise ValueError('해당 계약 없음')
            pct=number(row['change_percentage'])
            out.update(val=f"{number(row['last']):,.4f} USDT",chg=f'{pct:+.2f}%',up=pct>0,status='정상',basis='Gate 선물 · 24시간 등락')
        elif key=='crypto_fg':
            r=requests.get('https://api.alternative.me/fng/',timeout=8);r.raise_for_status(); row=r.json()['data'][0]
            out.update(val=row['value'],status=row['value_classification'],basis='일간 지수',source_time=row['timestamp'])
        else:
            r=requests.get(url,headers={'User-Agent':'Mozilla/5.0'},timeout=8);r.raise_for_status()
            soup=BeautifulSoup(r.text,'html.parser')
            # 명시적인 데이터 필드만 사용. 페이지 내 임의 숫자 추출 금지.
            price=soup.select_one('[data-test="instrument-price-last"]')
            change=soup.select_one('[data-test="instrument-price-change-percent"]')
            if price and change:
                pct=number(change.get_text().replace('(','').replace(')',''))
                out.update(val=price.get_text(strip=True),chg=f'{pct:+.2f}%',up=pct>0,status='지연 여부 미확인',basis='출처 표기 기준')
            else:
                out['status']='출처 파싱 미확인 · 미확보'
    except (requests.RequestException,ValueError,TypeError,KeyError,IndexError):
        out['status']='조회 실패 · 미확보'
    return key,group,out

def refresh():
    updates={'macro':{},'night':{},'bonds':{}}
    with ThreadPoolExecutor(max_workers=6) as pool:
        for key,group,row in pool.map(fetch,SOURCES): updates[group][key]=row
    with _lock:
        for group,rows in updates.items():
            for key,row in rows.items():
                previous=_cache.get(group,{}).get(key)
                if row['val']=='미확보' and previous and previous['val']!='미확보':
                    row={**previous,'status':'갱신 실패 · 이전 값','attempted_at':row['fetched_at']}
                _cache.setdefault(group,{})[key]=row

def snapshot():
    with _lock:
        return {group:{key:dict(_cache.get(group,{}).get(key,{'val':'미확보','chg':'','up':False,'source':url,'status':'초기 조회 대기'}))
                 for key,(g,url) in SOURCES.items() if g==group} for group in ['macro','night','bonds']}
