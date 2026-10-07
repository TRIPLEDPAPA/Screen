"""페이지별 명시 필드 및 제목 주변 구조만 파싱. 숫자를 임의 추측하지 않는다."""
import re
from bs4 import BeautifulSoup

def bond(html):
    soup=BeautifulSoup(html,'html.parser')
    text=soup.get_text(' ',strip=True)
    m=re.search(r'거래일\s*(\d{4}\.\d{2}\.\d{2})\s*([\d,.]+)\s*([\d,.]+)\s*([+−-]?[\d,.]+)%\s*전일가\s*([\d,.]+)',text)
    if not m:raise ValueError('국채 명시 시세 구조 미확보')
    date,current,delta,pct,previous=m.groups();current=float(current.replace(',',''));previous=float(previous.replace(',',''));pct=float(pct.replace('−','-').replace(',',''))
    diff=current-previous
    if abs(abs(diff)-float(delta.replace(',','')))>0.011 or (diff*pct<0):raise ValueError('국채 변동폭/부호 불일치')
    return {'val':f'{current:.2f}%','diff':round(diff,4),'chg':f'{pct:+.2f}%','unit':'yield','basis':'거래일 '+date+' · 전일 대비 금리%p / 등락률%','status':'정상'}

def kospi_fear(html):
    text=BeautifulSoup(html,'html.parser').get_text(' ',strip=True)
    m=re.search(r'기준일\s*(\d{4}\.\d{2}\.\d{2})\s*(\d{1,3})\s*(극도의 공포|극도의 탐욕|극단적 공포|극단적 탐욕|공포|탐욕|중립)\s*어제\s*(\d{1,3})',text)
    if not m:raise ValueError('심리지수 명시 구조 미확보')
    date,value,classification,previous=m.groups();value=int(value);previous=int(previous)
    if not 0<=value<=100 or not 0<=previous<=100:raise ValueError('심리지수 범위 오류')
    return {'val':str(value),'status':classification,'basis':'기준일 '+date+' · 일간 심리지수','diff':value-previous,'chg':f'{(value/previous-1)*100:+.2f}%' if previous else ''}

def google_fx(html):
    soup=BeautifulSoup(html,'html.parser');field=soup.select_one('[data-last-price]')
    if not field:raise ValueError('Google 환율 명시 가격 미확보')
    value=float(field['data-last-price'])
    # 비교값이 없으면 등락률을 만들지 않는다.
    return {'val':f'{value:,.2f}원','diff':None,'chg':'','status':'전일 대비 데이터 미확보','basis':'Google Finance 환율 · 제공 시세 지연 가능'}
