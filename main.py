# StockScan Pro — Python FastAPI 서버 v2
# 파일 위치: C:\Users\lllol\stockscan\server\main.py
# 키움 REST API 정확한 엔드포인트 적용

import requests
import re
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
import os

@app.get("/app")
def serve_app():
    """StockScan HTML 서빙"""
    html_path = os.path.join(os.path.dirname(__file__), "stockscan_v14.html")
    return FileResponse(html_path)
