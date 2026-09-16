<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>고정밀 숏스퀴즈 & 종가 베팅 퀀트 대시보드</title>
    <!-- Tailwind CSS CDN for Professional UI Styling -->
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-slate-950 text-slate-100 font-sans antialiased min-h-screen">

    <!-- Header Navigation -->
    <header class="border-b border-slate-800 bg-slate-900/50 backdrop-blur sticky top-0 z-50 px-6 py-4 flex justify-between items-center">
        <div class="flex items-center space-x-3">
            <i class="fa-solid fa-chart-line text-blue-500 text-2xl"></i>
            <h1 class="text-xl font-bold tracking-tight">고정밀 숏스퀴즈 & 종가 베팅 퀀트 시스템</h1>
        </div>
        <div class="flex items-center space-x-4 text-sm text-slate-400">
            <span><i class="fa-regular fa-clock mr-1"></i> 실시간 EOD 스캔 완료</span>
            <span class="bg-blue-900/50 text-blue-400 border border-blue-700/50 px-3 py-1 rounded-full font-medium">Live Mode</span>
        </div>
    </header>

    <!-- Main Container -->
    <main class="p-6 max-w-7xl mx-auto space-y-8">

        <!-- Section 1: Main Screening Table (Short-term Returns: 5d ~ 1d) -->
        <section class="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-lg font-semibold flex items-center">
                    <i class="fa-solid fa-table-cells text-blue-400 mr-2"></i> 스크리닝 결과 메인 테이블 (초단기 수익률 5일 ~ 1일)
                </h2>
                <span class="text-xs text-slate-400">기준: 거래대금 100억 이상 / 숏스퀴즈 엄격 게이트 적용</span>
            </div>
            
            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse text-sm">
                    <thead>
                        <tr class="border-b border-slate-800 text-slate-400 bg-slate-950/50">
                            <th class="p-3">종목코드</th>
                            <th class="p-3">종목명</th>
                            <th class="p-3">섹터</th>
                            <th class="p-3 text-right">5일</th>
                            <th class="p-3 text-right">4일</th>
                            <th class="p-3 text-right">3일</th>
                            <th class="p-3 text-right">2일</th>
                            <th class="p-3 text-right">1일 (당일)</th>
                            <th class="p-3 text-right">거래대금(억)</th>
                            <th class="p-3 text-center">우선순위 점수</th>
                            <th class="p-3 text-center">진입 판정</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800/60" id="main-table-body">
                        <!-- Dynamic Data Injection Row Example -->
                        <tr class="hover:bg-slate-800/40 transition cursor-pointer">
                            <td class="p-3 font-mono text-slate-400">028300</td>
                            <td class="p-3 font-bold text-blue-400">HLB</td>
                            <td class="p-3 text-slate-300">제약/바이오</td>
                            <td class="p-3 text-right text-emerald-400">+6.4%</td>
                            <td class="p-3 text-right text-emerald-400">+3.1%</td>
                            <td class="p-3 text-right text-emerald-400">+4.5%</td>
                            <td class="p-3 text-right text-emerald-400">+2.0%</td>
                            <td class="p-3 text-right text-emerald-400 font-bold">+4.5%</td>
                            <td class="p-3 text-right">600억</td>
                            <td class="p-3 text-center font-bold text-amber-400">91.5점</td>
                            <td class="p-3 text-center"><span class="bg-red-950/80 text-red-400 border border-red-800/50 px-2 py-1 rounded text-xs font-bold">🔴 최우선 검토</span></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </section>

        <!-- Section 2: Detailed Modal / Analysis Section -->
        <section class="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
            <div class="border-b border-slate-800 pb-4 flex justify-between items-center">
                <div>
                    <h2 class="text-xl font-bold flex items-center">
                        <i class="fa-solid fa-magnifying-glass-chart text-emerald-400 mr-2"></i> [028300] HLB 상세 진단 리포트
                    </h2>
                    <p class="text-xs text-slate-400 mt-1">상승가능성 88점 | 종가베팅 38/45점 | 숏스퀴즈 보너스 +5점</p>
                </div>
                <div class="text-right">
                    <span class="bg-emerald-950/80 text-emerald-400 border border-emerald-800/50 px-3 py-1 rounded-full text-xs font-bold">Squeeze Candidate 충족</span>
                </div>
            </div>

            <!-- AI & Real Data Analysis -->
            <div class="bg-slate-950 border border-slate-800 p-4 rounded-lg">
                <h3 class="text-sm font-semibold text-blue-400 mb-1"><i class="fa-solid fa-robot mr-1"></i> AI & 실데이터 종합 분석 소견</h3>
                <p class="text-sm text-slate-300">공매도 잔고비중(4.2%) 및 DtC(3.1일)가 엄격 기준을 모두 충족하여 숏커버링 유입 압력이 매우 높으며, 대량 거래대금 동반에 따른 상방 탄력성 유지 중.</p>
            </div>

            <!-- Price Momentum Time-series (1yr ~ 5d) -->
            <div>
                <h3 class="text-sm font-semibold text-slate-400 mb-3"><i class="fa-solid fa-chart-area mr-1"></i> 주가 흐름 시계열 (1년·6개월·3개월·1개월·5일)</h3>
                <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
                    <div class="bg-slate-950 p-3 rounded border border-slate-800 text-center"><span class="text-xs text-slate-400 block">1년 수익률</span><span class="text-lg font-bold text-emerald-400">+125.0%</span></div>
                    <div class="bg-slate-950 p-3 rounded border border-slate-800 text-center"><span class="text-xs text-slate-400 block">6개월 수익률</span><span class="text-lg font-bold text-emerald-400">+78.4%</span></div>
                    <div class="bg-slate-950 p-3 rounded border border-slate-800 text-center"><span class="text-xs text-slate-400 block">3개월 수익률</span><span class="text-lg font-bold text-emerald-400">+52.1%</span></div>
                    <div class="bg-slate-950 p-3 rounded border border-slate-800 text-center"><span class="text-xs text-slate-400 block">1개월 수익률</span><span class="text-lg font-bold text-emerald-400">+34.2%</span></div>
                    <div class="bg-slate-950 p-3 rounded border border-slate-800 text-center"><span class="text-xs text-slate-400 block">5일 수익률</span><span class="text-lg font-bold text-emerald-400">+6.4%</span></div>
                </div>
            </div>

            <!-- Two Column Grid for Indicators, Short Squeeze & DART -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <!-- Left: Investment Metrics & Scoreboard -->
                <div class="bg-slate-950 border border-slate-800 p-4 rounded-lg space-y-3">
                    <h3 class="text-sm font-semibold text-slate-300"><i class="fa-solid fa-list-check mr-1"></i> 투자지표 및 20개 핵심 점수표</h3>
                    <div class="flex justify-between text-xs py-1 border-b border-slate-800 text-slate-400"><span>PER / PBR</span><span class="text-slate-200">적자(N/A) / 3.5배</span></div>
                    <div class="flex justify-between text-xs py-1 border-b border-slate-800 text-slate-400"><span>외인 / 기관 5일 순매수</span><span class="text-slate-200">+90억 / +60억</span></div>
                    <div class="flex justify-between text-xs py-1 border-b border-slate-800 text-slate-400"><span>과열 감점 상태</span><span class="text-amber-400">과열 1개 (-0점)</span></div>
                </div>

                <!-- Right: Short Squeeze & DART Timeline -->
                <div class="bg-slate-950 border border-slate-800 p-4 rounded-lg space-y-3">
                    <h3 class="text-sm font-semibold text-slate-300"><i class="fa-solid fa-shield-halved mr-1"></i> 공매도 현황 및 DART 공시 상태</h3>
                    <div class="flex justify-between text-xs py-1 border-b border-slate-800 text-slate-400"><span>공매도 잔고비중</span><span class="text-emerald-400 font-bold">4.2% (기준 ≥ 3%)</span></div>
                    <div class="flex justify-between text-xs py-1 border-b border-slate-800 text-slate-400"><span>DtC (Days to Cover)</span><span class="text-emerald-400 font-bold">3.1일 (기준 ≥ 2일)</span></div>
                    <div class="flex justify-between text-xs py-1 border-b border-slate-800 text-slate-400"><span>DART 최근 수주 공시</span><span class="text-slate-200">2건 연동 완료 (정상)</span></div>
                </div>
            </div>

            <!-- Risk Diagnostics (Short, Medium, Long) -->
            <div>
                <h3 class="text-sm font-semibold text-slate-400 mb-3"><i class="fa-solid fa-triangle-exclamation mr-1"></i> 시계열 리스크 진단 (단기·중기·장기)</h3>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div class="bg-slate-950 border border-slate-800 p-3 rounded text-center">
                        <span class="text-xs text-slate-400 block">단기 리스크 (5일 이격도)</span>
                        <span class="text-sm font-bold text-emerald-400">안정 (Sweet Spot)</span>
                    </div>
                    <div class="bg-slate-950 border border-slate-800 p-3 rounded text-center">
                        <span class="text-xs text-slate-400 block">중기 리스크 (정배열 추세)</span>
                        <span class="text-sm font-bold text-emerald-400">정배열 유지</span>
                    </div>
                    <div class="bg-slate-950 border border-slate-800 p-3 rounded text-center">
                        <span class="text-xs text-slate-400 block">장기 리스크 (1개월 모멘텀)</span>
                        <span class="text-sm font-bold text-emerald-400">추세 상승</span>
                    </div>
                </div>
            </div>
        </section>

    </main>

    <footer class="text-center py-6 text-xs text-slate-500 border-t border-slate-800 mt-12">
        &copy; 2026 Quantitative Short Squeeze & Closing Bet System. All rights reserved.
    </footer>

</body>
</html>
