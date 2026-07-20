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
    html_path = os.path.join(os.path.dirname(__file__), "stockscan_v14.html")
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
            headers = {
                "Content-Type": "application/json;charset=UTF-8",
                "authorization": f"Bearer {token}",
                "appkey": APP_KEY,
                "secretkey": APP_SECRET,
                "api-id": "ka10001",
            }
            res = requests.post(
                BASE_URL + "/api/dostk/stkinfo",
                headers=headers,
                json={"stk_cd": code},
                timeout=5
            )
            data = res.json()

            results.append({
                "code":     code,
                "name":     name,
                "market":   market,
                "price":    abs(int(data.get("cur_prc", 0) or 0)),
                "chg_rate": float(data.get("trde_tern_rt", 0) or 0),
                "volume":   int(data.get("trde_qty", 0) or 0),
                "per":      float(data.get("per", 0) or 0),
                "pbr":      float(data.get("pbr", 0) or 0),
                "roe":      float(data.get("roe", 0) or 0),
            })
            scan_status["done"] += 1

        except Exception as e:
            scan_status["failed"] += 1
            print(f"[스캔2단계] 실패 {code} {name}: {e}")

        time.sleep(0.21)  # 초당 5건 제한

        if (i + 1) % 100 == 0:
            _save_results(results)
            print(f"[스캔2단계] {i+1}/{len(targets)} ({scan_status['done']}성공/{scan_status['failed']}실패)")

    _save_results(results)
    scan_status["running"] = False
    scan_status["finished"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[스캔2단계] 완료! {scan_status['done']}개 수집")

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
    return {
        "running":  scan_status["running"],
        "total":    scan_status["total"],
        "done":     scan_status["done"],
        "failed":   scan_status["failed"],
        "percent":  f"{pct}%",
        "started":  scan_status["started"],
        "finished": scan_status["finished"],
        "error":    scan_status["error"],
    }

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
