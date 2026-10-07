"""월별 경제/실적 일정. Finnhub 연결은 키 및 구독 권한이 필요."""
import os, calendar, requests

def month_events(month,category):
    y,m=map(int,month.split('-'));end=f'{month}-{calendar.monthrange(y,m)[1]:02d}'
    key=os.getenv('FINNHUB_API_KEY')
    if not key:return {'data':[],'status':'FINNHUB_API_KEY 미등록 · 경제/실적 자동수집 대기'}
    economic=category in ['economic','eco']
    path='calendar/economic' if economic else 'calendar/earnings'
    r=requests.get('https://finnhub.io/api/v1/'+path,params={'from':month+'-01','to':end,'token':key},timeout=12)
    if r.status_code!=200:return {'data':[],'status':f'일정 조회 실패 HTTP {r.status_code} · API 권한 확인'}
    j=r.json();rows=j.get('economicCalendar' if economic else 'earningsCalendar',[])
    data=[]
    for i,x in enumerate(rows):
        date=str(x.get('time') or x.get('date') or '')[:10]
        if not date.startswith(month):continue
        data.append({'id':f'{category}-{date}-{i}','date':date,'title':x.get('event') or x.get('symbol'),'actual':x.get('actual') if economic else x.get('epsActual'),'forecast':x.get('estimate') if economic else x.get('epsEstimate'),'country':x.get('country'),'source':'Finnhub','category':category,'ai_summary':'출처가 제공한 발표 일정. AI 요약은 별도 분석 필요'})
    return {'data':data,'status':'Finnhub 조회 완료 · 해외 일정 범위, 국내 실적 일정 아님'}
