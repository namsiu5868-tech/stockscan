# StockScan Pro — Python FastAPI 서버 v2
# 파일 위치: C:\Users\lllol\stockscan\server\main.py
# 키움 REST API 정확한 엔드포인트 적용

import requests
import re
import os
import json
import threading
import time
import urllib.request
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ──────────────────────────────────────
# 설정
# ──────────────────────────────────────
APP_KEY    = "YeM3eYR7rbR_Qme-d8K1FLBq-V3LsO3ctAiv2bplFEs"
APP_SECRET = "6OxwAIe7c0cn6ghfhVe0kaVdPLSH9WY3qwB7qtubbJc"
BASE_URL   = "https://api.kiwoom.com"

app = FastAPI(title="StockScan Server v2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────
# 토큰 관리
# ──────────────────────────────────────
token_cache = {"token": None, "expires": None}

def get_token():
    now = datetime.now()
    if token_cache["token"] and token_cache["expires"] and now < token_cache["expires"]:
        return token_cache["token"]
    url = f"{BASE_URL}/oauth2/token"
    headers = {"Content-Type": "application/json;charset=UTF-8"}
    body = {"grant_type": "client_credentials", "appkey": APP_KEY, "secretkey": APP_SECRET}
    res = requests.post(url, headers=headers, json=body)
    data = res.json()
    token = data.get("token")
    token_cache["token"] = token
    token_cache["expires"] = now + timedelta(hours=23)
    print(f"[토큰발급] {datetime.now().strftime('%H:%M:%S')} 완료")
    return token

def api_call(api_id, body, endpoint=None):
    """키움 REST API 호출 (api-id 헤더 방식)"""
    token = get_token()
    # 엔드포인트 매핑
    ep_map = {
        "ka10001": "/api/dostk/stkinfo",  # 주식기본정보
        "ka10005": "/api/dostk/stkinfo",  # 주식일주월시분
        "ka10079": "/api/dostk/chart",    # 틱차트
        "ka10080": "/api/dostk/chart",    # 분봉
        "ka10081": "/api/dostk/chart",    # 일봉
        "ka10082": "/api/dostk/chart",    # 주봉
        "ka10083": "/api/dostk/chart",    # 월봉
        "ka10030": "/api/dostk/rnkng",    # 거래량상위
        "ka10032": "/api/dostk/rnkng",    # 거래대금상위
        "ka10027": "/api/dostk/rnkng",    # 등락률상위
        "ka20001": "/api/dostk/sect",     # 업종현재가
        "ka20003": "/api/dostk/sect",     # 전업종지수
        "ka10099": "/api/dostk/stkinfo",  # 종목리스트
        "ka10100": "/api/dostk/stkinfo",  # 종목정보조회
    }
    url = BASE_URL + (endpoint or ep_map.get(api_id, "/api/dostk/stkinfo"))
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "secretkey": APP_SECRET,
        "api-id": api_id,
    }
    res = requests.post(url, headers=headers, json=body)
    print(f"[{api_id}] {res.status_code}")
    try:
        return res.json()
    except:
        return {"error": res.text, "status_code": res.status_code}

# ──────────────────────────────────────
# 기본
# ──────────────────────────────────────

@app.get("/")
def root():
    return {"status": "StockScan 서버 정상 작동 중", "version": "v2",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

@app.get("/token-test")
def token_test():
    try:
        token = get_token()
        return {"success": True, "token_앞10자리": token[:10] + "..."}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ──────────────────────────────────────
# 종목 정보
# ──────────────────────────────────────

@app.get("/stock/info/{code}")
def get_stock_info(code: str):
    """주식 기본정보 (ka10001)"""
    return api_call("ka10001", {"stk_cd": code})

@app.get("/stock/price/{code}")
def get_stock_price(code: str):
    """주식 일주월시분 — 현재가 (ka10005)"""
    return api_call("ka10005", {"stk_cd": code, "qry_tp": "0", "cnt": "1"})

# ──────────────────────────────────────
# 차트
# ──────────────────────────────────────

@app.get("/chart/daily/{code}")
def get_daily_chart(code: str):
    """일봉차트 (ka10081)"""
    today = datetime.now().strftime("%Y%m%d")
    return api_call("ka10081", {"stk_cd": code, "base_dt": today, "upd_stkpc_tp": "0"})

@app.get("/chart/weekly/{code}")
def get_weekly_chart(code: str):
    """주봉차트 (ka10082)"""
    today = datetime.now().strftime("%Y%m%d")
    return api_call("ka10082", {"stk_cd": code, "base_dt": today, "upd_stkpc_tp": "0"})

@app.get("/chart/monthly/{code}")
def get_monthly_chart(code: str):
    """월봉차트 (ka10083)"""
    today = datetime.now().strftime("%Y%m%d")
    return api_call("ka10083", {"stk_cd": code, "base_dt": today, "upd_stkpc_tp": "0"})

@app.get("/chart/minute/{code}")
def get_minute_chart(code: str, min_tp: str = "1"):
    """분봉차트 (ka10080) min_tp: 1,3,5,10,15,30,60"""
    return api_call("ka10080", {"stk_cd": code, "min_tp": min_tp, "upd_stkpc_tp": "0"})

# ──────────────────────────────────────
# 순위 (스크리닝 핵심)
# ──────────────────────────────────────

@app.get("/ranking/volume")
def get_top_volume(market: str = "0"):
    """거래량 상위 (ka10030) market: 0전체 1코스피 2코스닥"""
    return api_call("ka10030", {
        "mrkt_tp": market, "trde_qty_tp": "0",
        "stk_cnd": "0", "stk_prc_cnd": "0", "trde_qty_cnd": "0"
    })

@app.get("/ranking/trading-value")
def get_top_trading_value(market: str = "0"):
    """거래대금 상위 (ka10032)"""
    return api_call("ka10032", {"mrkt_tp": market, "trde_qty_tp": "0", "stk_cnd": "0"})

@app.get("/ranking/change-rate")
def get_top_change_rate(market: str = "0"):
    """등락률 상위 (ka10027)"""
    return api_call("ka10027", {"mrkt_tp": market, "stk_cnd": "0",
                                 "trde_qty_cnd": "0", "updn_tp": "1"})

# ──────────────────────────────────────
# 업종
# ──────────────────────────────────────

@app.get("/sector/all")
def get_all_sectors():
    """전업종지수 (ka20003)"""
    return api_call("ka20003", {"mrkt_tp": "0"})

@app.get("/sector/{code}")
def get_sector(code: str):
    """업종현재가 (ka20001)"""
    return api_call("ka20001", {"inds_cd": code})

@app.get("/market/status")
def get_market_status():
    """시장상승 여부 판단 — 코스피/코스닥 20일선 비교"""
    try:
        today = datetime.now().strftime("%Y%m%d")
        result = {}

        for mkt_name, inds_cd in [("kospi", "001"), ("kosdaq", "101")]:
            # 일봉차트 조회 (ka10081 대신 업종차트 ka20002 사용)
            token = get_token()
            headers = {
                "Content-Type": "application/json;charset=UTF-8",
                "authorization": f"Bearer {token}",
                "appkey": APP_KEY, "secretkey": APP_SECRET,
                "api-id": "ka20002",
            }
            res = requests.post(
                BASE_URL + "/api/dostk/sect",
                headers=headers,
                json={"inds_cd": inds_cd, "base_dt": today, "upd_stkpc_tp": "0"},
                timeout=5
            )
            data = res.json()

            candles = data.get("output2") or data.get("output") or []
            closes = []
            for c in candles:
                p = c.get("cur_prc") or c.get("clpr") or 0
                try:
                    closes.append(abs(float(str(p).replace(",", ""))))
                except:
                    pass
            closes = [p for p in closes if p > 0]

            cur = closes[0] if closes else 0
            ma20 = sum(closes[:20]) / 20 if len(closes) >= 20 else 0
            ma20_prev = sum(closes[1:21]) / 20 if len(closes) >= 21 else 0

            rising = ma20 > ma20_prev  # 20일선 우상향
            above = cur > ma20         # 현재가 > 20일선

            result[mkt_name] = {
                "current": cur,
                "ma20": round(ma20, 2),
                "above_ma20": above,
                "ma20_rising": rising,
                "bullish": above and rising
            }

        both_bullish = result.get("kospi", {}).get("bullish", False) and \
                       result.get("kosdaq", {}).get("bullish", False)

        return {
            "success": True,
            "market_up": both_bullish,
            "kospi": result.get("kospi", {}),
            "kosdaq": result.get("kosdaq", {}),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "market_up": False}

# ──────────────────────────────────────
# 뉴스 (네이버 크롤링)
# ──────────────────────────────────────

@app.get("/news/{code}")
def get_news(code: str):
    """종목 뉴스 (네이버 금융 크롤링)"""
    try:
        url = f"https://finance.naver.com/item/news_news.naver?code={code}&page=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as res:
            html = res.read().decode("euc-kr", errors="ignore")
        pattern = r'<a[^>]+href="[^"]*news[^"]*"[^>]*>([^<]{10,80})</a>'
        titles = re.findall(pattern, html)
        titles = [t.strip() for t in titles if len(t.strip()) > 10][:10]
        return {"code": code, "count": len(titles), "news": titles}
    except Exception as e:
        return {"code": code, "news": [], "error": str(e)}

# ──────────────────────────────────────
# 정적 파일 서빙 (HTML)
# ──────────────────────────────────────
from fastapi.responses import FileResponse

@app.get("/app")
def serve_app():
    """StockScan HTML 서빙"""
    html_path = os.path.join(os.path.dirname(__file__), "stockscan_v15.html")
    return FileResponse(html_path)

# ──────────────────────────────────────
# 전종목 리스트 수집
# ──────────────────────────────────────

def is_normal_stock(code: str, name: str) -> bool:
    """일반 보통주 여부 판별"""
    if not code:
        return False
    c = code.lstrip("A").strip()
    if len(c) != 6:
        return False
    # 우선주: 끝자리 5
    if c[-1] == "5":
        return False
    # ETF/ETN: 앞자리 1로 시작
    if c[0] == "1":
        return False
    # 스팩: 앞자리 4로 시작
    if c[0] == "4":
        return False
    # 이름 기반 — 보통주에 절대 안 들어가는 키워드만
    name_upper = name.upper()
    for kw in ["ETF", "ETN", "스팩", "SPAC", "인버스", "레버리지"]:
        if kw in name_upper:
            return False
    return True

# 전종목 리스트 캐시
STOCKLIST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "stocklist.json")
stock_list_cache = {"data": [], "updated": None}

# 서버 시작 시 기존 파일 자동 로드
def _load_stocklist_from_file():
    if os.path.exists(STOCKLIST_FILE):
        try:
            with open(STOCKLIST_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            stock_list_cache["data"] = saved.get("data", [])
            stock_list_cache["updated"] = saved.get("updated")
            print(f"[자동로드] 전종목 리스트 {len(stock_list_cache['data'])}개 로드 완료")
        except Exception as e:
            print(f"[자동로드] 실패: {e}")

_load_stocklist_from_file()

# ──────────────────────────────────────
# KRX 휴장일 (매년 초 해당 연도 추가)
# ──────────────────────────────────────
KRX_HOLIDAYS = {
    # 2025년
    "20250101","20250129","20250130","20250131",
    "20250301","20250505","20250506","20250606",
    "20250815","20251003","20251006","20251007","20251008",
    "20251009","20251225","20251231",
    # 2026년
    "20260101","20260128","20260129","20260130",
    "20260301","20260505","20260525","20260606",
    "20260815","20260924","20260925","20260928",
    "20261009","20261225",
}

def is_trading_day(date=None):
    if date is None:
        date = datetime.now()
    if date.weekday() >= 5:
        return False
    if date.strftime("%Y%m%d") in KRX_HOLIDAYS:
        return False
    return True

def _auto_collect_on_startup():
    if not is_trading_day():
        print(f"[자동수집] 오늘은 휴장일. 건너뜀.")
        return
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            updated = saved.get("updated", "")
            if updated.startswith(datetime.now().strftime("%Y-%m-%d")):
                print(f"[자동수집] 오늘 이미 수집 완료 ({updated}). 건너뜀.")
                # 이평선 미수집 시 이평선만 자동 시작
                ma_updated = saved.get("ma_updated", "")
                if not ma_updated.startswith(datetime.now().strftime("%Y-%m-%d")):
                    print(f"[자동수집] 이평선 미수집 — 이평선 수집 시작")
                    t = threading.Thread(target=collect_ma_thread, daemon=True)
                    t.start()
                return
        except:
            pass
    if not stock_list_cache["data"]:
        print(f"[자동수집] 전종목 리스트 없음. 건너뜀.")
        return
    print(f"[자동수집] 서버 시작 — 전종목 기본데이터 수집 시작")
    t = threading.Thread(target=collect_basic_data_thread, daemon=True)
    t.start()

threading.Thread(target=lambda: (time.sleep(3), _auto_collect_on_startup()), daemon=True).start()

def fetch_stock_list_by_market(market_code):
    """시장별 전종목 리스트 수집
    market_code: 0=코스피, 10=코스닥
    """
    all_stocks = []
    next_key = ""
    market_name = "코스피" if market_code == 0 else "코스닥"

    while True:
        token = get_token()
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"Bearer {token}",
            "appkey": APP_KEY,
            "secretkey": APP_SECRET,
            "api-id": "ka10099",
        }
        if next_key:
            headers["cont-yn"] = "Y"
            headers["next-key"] = next_key

        body = {"mrkt_tp": str(market_code)}

        url = BASE_URL + "/api/dostk/stkinfo"
        res = requests.post(url, headers=headers, json=body)
        
        print(f"[{market_name}] 상태코드: {res.status_code}")
        
        try:
            data = res.json()
        except:
            print(f"[{market_name}] JSON 파싱 실패: {res.text[:200]}")
            break

        print(f"[{market_name}] 응답키: {list(data.keys())}")

        # 응답 파싱 - 'list' 키로 데이터 추출
        items = data.get("list", [])
        
        if not items:
            print(f"[{market_name}] 데이터 없음")
            break

        for item in items:
            code = (item.get("code") or item.get("stk_cd") or "").strip()
            name = (item.get("name") or item.get("stk_nm") or "").strip()
            if code and name and is_normal_stock(code, name):
                all_stocks.append({
                    "code": code,
                    "name": name,
                    "market": market_name
                })

        # 연속 조회
        cont_yn = res.headers.get("cont-yn", "N")
        if cont_yn == "Y":
            next_key = res.headers.get("next-key", "")
            print(f"[{market_name}] 연속조회: {next_key}")
        else:
            break

    return all_stocks

@app.get("/stocklist/fetch")
def fetch_all_stocks():
    """전종목 리스트 수집 (코스피 + 코스닥)"""
    try:
        print("[전종목수집] 시작...")
        kospi = fetch_stock_list_by_market(0)
        print(f"[전종목수집] 코스피: {len(kospi)}개")
        kosdaq = fetch_stock_list_by_market(10)
        print(f"[전종목수집] 코스닥: {len(kosdaq)}개")

        all_stocks = kospi + kosdaq
        stock_list_cache["data"] = all_stocks
        stock_list_cache["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 파일로 저장 (덮어쓰기)
        os.makedirs(os.path.dirname(STOCKLIST_FILE), exist_ok=True)
        with open(STOCKLIST_FILE, "w", encoding="utf-8") as f:
            json.dump({"updated": stock_list_cache["updated"], "data": all_stocks}, f, ensure_ascii=False)

        print(f"[전종목수집] 완료: 총 {len(all_stocks)}개")
        return {
            "success": True,
            "total": len(all_stocks),
            "kospi": len(kospi),
            "kosdaq": len(kosdaq),
            "updated": stock_list_cache["updated"],
            "sample": all_stocks[:5]  # 처음 5개만 미리보기
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/stocklist")
def get_stock_list():
    """저장된 전종목 리스트 조회"""
    return {
        "total": len(stock_list_cache["data"]),
        "updated": stock_list_cache["updated"],
        "data": stock_list_cache["data"]
    }


# ──────────────────────────────────────
# 스캔 엔진 2단계 — 전종목 기본데이터 수집
# ──────────────────────────────────────

# 수집 진행상황
scan_status = {
    "running": False,
    "total": 0,
    "done": 0,
    "failed": 0,
    "started": None,
    "finished": None,
    "error": None,
    # 이평선 백그라운드 수집
    "ma_running": False,
    "ma_total": 0,
    "ma_done": 0,
    "ma_started": None,
    "ma_finished": None,
}

DATA_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
DATA_FILE = os.path.join(DATA_DIR, "stocks_basic.json")

def _save_results(results):
    """결과를 JSON 파일로 덮어쓰기 저장"""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total": len(results),
            "data": results
        }, f, ensure_ascii=False)

def collect_basic_data_thread():
    """전종목 기본데이터 수집 (별도 스레드)"""
    scan_status["running"] = True
    scan_status["done"] = 0
    scan_status["failed"] = 0
    scan_status["started"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scan_status["finished"] = None
    scan_status["error"] = None

    if not stock_list_cache["data"]:
        scan_status["running"] = False
        scan_status["error"] = "전종목 리스트 없음. /stocklist/fetch 먼저 실행하세요."
        return

    targets = [
        s for s in stock_list_cache["data"]
        if is_normal_stock(s["code"], s["name"])
    ]
    scan_status["total"] = len(targets)
    print(f"[스캔2단계] 대상 종목: {len(targets)}개")

    results = []

    for i, stock in enumerate(targets):
        code = stock["code"]
        name = stock["name"]
        market = stock["market"]

        try:
            token = get_token()
            # 1) 기본정보 수집
            headers1 = {
                "Content-Type": "application/json;charset=UTF-8",
                "authorization": f"Bearer {token}",
                "appkey": APP_KEY, "secretkey": APP_SECRET,
                "api-id": "ka10001",
            }
            res1 = requests.post(BASE_URL + "/api/dostk/stkinfo", headers=headers1, json={"stk_cd": code}, timeout=5)
            data = res1.json()
            time.sleep(0.21)

            # 2) 일봉 수집 (200일치)
            headers2 = {
                "Content-Type": "application/json;charset=UTF-8",
                "authorization": f"Bearer {token}",
                "appkey": APP_KEY, "secretkey": APP_SECRET,
                "api-id": "ka10081",
            }
            today = datetime.now().strftime("%Y%m%d")
            res2 = requests.post(BASE_URL + "/api/dostk/chart", headers=headers2,
                                 json={"stk_cd": code, "base_dt": today, "upd_stkpc_tp": "0"}, timeout=5)
            chart = res2.json()
            time.sleep(0.21)

            # 종가 리스트 추출 (최신순 → 역순)
            candles = chart.get("output2") or chart.get("output") or []
            closes = []
            for c in candles:
                p = c.get("cur_prc") or c.get("stck_clpr") or 0
                try:
                    closes.append(abs(int(str(p).replace(",", ""))))
                except:
                    pass
            closes = [p for p in closes if p > 0]

            # 이평선 계산
            def ma(n):
                if len(closes) >= n:
                    return round(sum(closes[:n]) / n)
                return 0

            ma5   = ma(5)
            ma20  = ma(20)
            ma60  = ma(60)
            ma120 = ma(120)
            ma200 = ma(200)

            # 정배열 여부: 5>20>60>120>200
            price_now = abs(int(data.get("cur_prc", 0) or 0))
            is_bullish = (ma5 > 0 and ma20 > 0 and ma60 > 0 and ma120 > 0 and ma200 > 0
                          and ma5 > ma20 > ma60 > ma120 > ma200)
            above_120 = price_now > ma120 if ma120 > 0 else False

            results.append({
                "code":      code,
                "name":      name,
                "market":    market,
                "price":     price_now,
                "chg_rate":  float(data.get("flu_rt", 0) or 0),
                "volume":    int(data.get("trde_qty", 0) or 0),
                "per":       float(data.get("per", 0) or 0),
                "pbr":       float(data.get("pbr", 0) or 0),
                "roe":       float(data.get("roe", 0) or 0),
                "ma5":       ma5,
                "ma20":      ma20,
                "ma60":      ma60,
                "ma120":     ma120,
                "ma200":     ma200,
                "is_bullish": is_bullish,
                "above_120": above_120,
            })
            scan_status["done"] += 1

        except Exception as e:
            scan_status["failed"] += 1
            print(f"[스캔2단계] 실패 {code} {name}: {e}")

        if (i + 1) % 100 == 0:
            _save_results(results)
            print(f"[스캔2단계] {i+1}/{len(targets)} ({scan_status['done']}성공/{scan_status['failed']}실패)")

    _save_results(results)
    scan_status["running"] = False
    scan_status["finished"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[스캔2단계] 완료! {scan_status['done']}개 수집")
    # 이평선 백그라운드 수집 자동 시작
    t = threading.Thread(target=collect_ma_thread, daemon=True)
    t.start()

@app.get("/scan/collect")
def start_scan_collect():
    """전종목 기본데이터 수집 시작"""
    if scan_status["running"]:
        return {"success": False, "message": f"이미 수집 중 ({scan_status['done']}/{scan_status['total']})"}
    if not stock_list_cache["data"]:
        return {"success": False, "message": "전종목 리스트 없음. /stocklist/fetch 먼저 실행하세요."}
    t = threading.Thread(target=collect_basic_data_thread, daemon=True)
    t.start()
    target_count = len([s for s in stock_list_cache["data"] if is_normal_stock(s["code"], s["name"])])
    return {
        "success": True,
        "message": "수집 시작. /scan/status 로 진행상황 확인하세요.",
        "target": target_count,
        "예상소요시간": f"약 {round(target_count * 0.21 / 60)}분"
    }

@app.get("/scan/status")
def get_scan_status():
    """수집 진행상황 확인"""
    pct = round(scan_status["done"] / scan_status["total"] * 100, 1) if scan_status["total"] > 0 else 0
    ma_pct = round(scan_status["ma_done"] / scan_status["ma_total"] * 100, 1) if scan_status["ma_total"] > 0 else 0
    return {
        "running":     scan_status["running"],
        "total":       scan_status["total"],
        "done":        scan_status["done"],
        "failed":      scan_status["failed"],
        "percent":     f"{pct}%",
        "started":     scan_status["started"],
        "finished":    scan_status["finished"],
        "error":       scan_status["error"],
        "ma_running":  scan_status["ma_running"],
        "ma_total":    scan_status["ma_total"],
        "ma_done":     scan_status["ma_done"],
        "ma_percent":  f"{ma_pct}%",
        "ma_started":  scan_status["ma_started"],
        "ma_finished": scan_status["ma_finished"],
    }

# ── 이평선 백그라운드 수집 ──────────────────────────
def collect_ma_thread():
    """기본데이터 수집 완료 후 이평선 백그라운드 수집"""
    if not os.path.exists(DATA_FILE):
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        saved = json.load(f)
    stocks = saved.get("data", [])

    scan_status["ma_running"] = True
    scan_status["ma_total"] = len(stocks)
    scan_status["ma_done"] = 0
    scan_status["ma_started"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scan_status["ma_finished"] = None
    print(f"[이평선수집] 시작: {len(stocks)}개")

    today = datetime.now().strftime("%Y%m%d")

    for i, stock in enumerate(stocks):
        code = stock["code"]
        # 이미 이평선 있으면 건너뜀
        if stock.get("ma5", 0) > 0:
            scan_status["ma_done"] += 1
            continue
        try:
            token = get_token()
            headers = {
                "Content-Type": "application/json;charset=UTF-8",
                "authorization": f"Bearer {token}",
                "appkey": APP_KEY, "secretkey": APP_SECRET,
                "api-id": "ka10081",
            }
            res = requests.post(
                BASE_URL + "/api/dostk/chart",
                headers=headers,
                json={"stk_cd": code, "base_dt": today, "upd_stkpc_tp": "0"},
                timeout=5
            )
            chart = res.json()
            candles = chart.get("output2") or chart.get("output") or []
            closes = []
            opens  = []
            highs  = []
            lows   = []
            volumes = []
            for c in candles:
                p  = c.get("cur_prc") or c.get("stck_clpr") or 0
                op = c.get("open_prc") or c.get("stck_oprc") or 0
                hi = c.get("high_prc") or c.get("stck_hgpr") or 0
                lo = c.get("low_prc")  or c.get("stck_lwpr") or 0
                v  = c.get("trde_qty") or 0
                try: closes.append(abs(int(str(p).replace(",",""))))
                except: closes.append(0)
                try: opens.append(abs(int(str(op).replace(",",""))))
                except: opens.append(0)
                try: highs.append(abs(int(str(hi).replace(",",""))))
                except: highs.append(0)
                try: lows.append(abs(int(str(lo).replace(",",""))))
                except: lows.append(0)
                try: volumes.append(abs(int(str(v).replace(",",""))))
                except: volumes.append(0)

            closes_f = [p for p in closes if p > 0]

            def ma(arr, n):
                a = [x for x in arr[:n] if x > 0]
                return round(sum(a)/len(a)) if len(a)>=n else 0

            stock["ma5"]   = ma(closes, 5)
            stock["ma20"]  = ma(closes, 20)
            stock["ma60"]  = ma(closes, 60)
            stock["ma120"] = ma(closes, 120)
            stock["ma200"] = ma(closes, 200)

            # 20일 평균 거래량
            vols_20 = [v for v in volumes[:20] if v > 0]
            stock["vol_ma20"] = round(sum(vols_20)/len(vols_20)) if vols_20 else 0

            # RSI(14)
            def calc_rsi(closes, n=14):
                if len(closes) < n+1: return 50
                gains, losses = [], []
                for i in range(1, n+1):
                    d = closes[i-1] - closes[i]  # 최신순이라 역방향
                    if d > 0: gains.append(d)
                    else: losses.append(abs(d))
                ag = sum(gains)/n if gains else 0
                al = sum(losses)/n if losses else 0
                return round(100 - 100/(1+ag/al)) if al > 0 else 100

            rsi = calc_rsi(closes)
            stock["rsi"] = rsi

            # MACD (10,25,7)
            def ema(arr, n):
                if len(arr) < n: return 0
                k = 2/(n+1)
                e = arr[-n]  # 최신순 역방향
                for i in range(n-1, -1, -1):
                    e = arr[i]*k + e*(1-k)
                return e

            ema10 = ema(closes, 10)
            ema25 = ema(closes, 25)
            macd_val = ema10 - ema25
            stock["macd"] = round(macd_val)
            stock["macd_golden"] = macd_val > 0  # 0선 위 = 골든크로스

            # STO(5,3,3)
            def calc_sto(highs, lows, closes, k=5):
                if len(closes) < k: return 50
                h = max([x for x in highs[:k] if x>0] or [1])
                l = min([x for x in lows[:k] if x>0] or [0])
                c = closes[0]
                return round((c-l)/(h-l)*100) if h>l else 50

            sto_k = calc_sto(highs, lows, closes)
            stock["sto"] = sto_k

            price = stock.get("price", 0)
            stock["is_bullish"] = bool(
                stock["ma5"]>0 and stock["ma20"]>0 and stock["ma60"]>0 and
                stock["ma120"]>0 and stock["ma200"]>0 and
                stock["ma5"]>stock["ma20"]>stock["ma60"]>stock["ma120"]>stock["ma200"]
            )
            stock["above_120"] = price > stock["ma120"] if stock["ma120"] > 0 else False

            # ── 캔들패턴 (최근 3봉 기준) ──────────────
            patterns = []
            if len(closes) >= 3 and len(opens) >= 3:
                c0,c1,c2 = closes[0],closes[1],closes[2]
                o0,o1,o2 = opens[0],opens[1],opens[2]
                h0,h1    = highs[0],highs[1]
                l0,l1    = lows[0],lows[1]
                body0 = abs(c0-o0)
                body1 = abs(c1-o1)
                full0 = h0-l0 if h0>l0 else 1

                # 도지: 몸통이 전체의 10% 이하
                if body0 < full0*0.1:
                    patterns.append("도지")
                # 쌍도지: 연속 2개 도지
                if body0 < full0*0.1 and body1 < (h1-l1)*0.1:
                    patterns.append("쌍도지")
                # 망치형: 아래꼬리>=몸통*2, 위꼬리 작음, 양봉
                lower_wick0 = min(c0,o0)-l0
                upper_wick0 = h0-max(c0,o0)
                if lower_wick0 >= body0*2 and upper_wick0 < body0*0.5 and c0>o0:
                    patterns.append("망치형")
                # 상승장악형: 전일음봉, 당일양봉이 전일봉 완전포함
                if c1<o1 and c0>o0 and c0>o1 and o0<c1:
                    patterns.append("상승장악형")
                # 양음양: 양봉→음봉→양봉
                if len(closes)>=3 and c2>o2 and c1<o1 and c0>o0 and o1>c2 and c1<o2:
                    patterns.append("양음양")
                # 샛별형: 큰음봉→도지→큰양봉
                if len(closes)>=3 and c2<o2 and body1<(h1-l1)*0.2 and c0>o0 and body0>body2*0.5:
                    patterns.append("샛별형")
                # 저녁별형: 큰양봉→도지→큰음봉
                if len(closes)>=3 and c2>o2 and body1<(h1-l1)*0.2 and c0<o0:
                    patterns.append("저녁별형")

            stock["patterns"] = patterns

            scan_status["ma_done"] += 1

        except Exception as e:
            scan_status["ma_done"] += 1

        time.sleep(0.21)

        if (i + 1) % 200 == 0:
            # 중간 저장
            saved["data"] = stocks
            saved["ma_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(saved, f, ensure_ascii=False)
            print(f"[이평선수집] {i+1}/{len(stocks)} ({scan_status['ma_done']}완료)")

    # 최종 저장
    saved["data"] = stocks
    saved["ma_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(saved, f, ensure_ascii=False)

    scan_status["ma_running"] = False
    scan_status["ma_finished"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[이평선수집] 완료! {scan_status['ma_done']}개")

@app.get("/scan/ma-collect")
def start_ma_collect():
    """이평선 수집 수동 시작"""
    if scan_status["ma_running"]:
        return {"success": False, "message": f"이평선 수집 중 ({scan_status['ma_done']}/{scan_status['ma_total']})"}
    t = threading.Thread(target=collect_ma_thread, daemon=True)
    t.start()
    return {"success": True, "message": "이평선 수집 시작. /scan/status 로 확인하세요."}


@app.get("/scan/result")
def get_scan_result():
    """저장된 수집 결과 조회 (샘플 5개)"""
    if not os.path.exists(DATA_FILE):
        return {"success": False, "message": "수집 데이터 없음. /scan/collect 먼저 실행하세요."}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {
        "success": True,
        "updated": data.get("updated"),
        "total":   data.get("total"),
        "sample":  data["data"][:5]
    }

@app.get("/scan/result/all")
def get_scan_result_all():
    """저장된 수집 결과 전체 조회"""
    if not os.path.exists(DATA_FILE):
        return {"success": False, "message": "수집 데이터 없음. /scan/collect 먼저 실행하세요."}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {
        "success": True,
        "updated": data.get("updated"),
        "total":   data.get("total"),
        "data":    data["data"]
    }
