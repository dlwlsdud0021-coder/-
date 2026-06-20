"""
main.py — 포켓주식 FastAPI 백엔드
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

import database as db
from market_data import (get_index_data, get_us_indices, search_stock_by_name,
    get_all_tickers, get_top_stocks, get_ohlcv, get_investor_trading, get_current_price)
from news import fetch_market_news, fetch_stock_news
from home_analysis import analyze_us_impact, generate_forecast, calc_ma_status, market_phase, is_market_open
from analysis import analyze_stock, watchlist_timing

# ─────────────────────────────────────────────────────────
# JWT 설정
# ─────────────────────────────────────────────────────────
_JWT_SECRET = os.environ.get("JWT_SECRET", "pocket-stock-secret-2026")
_JWT_ALGO = "HS256"
_JWT_EXPIRE_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def _make_token(user_id: int, username: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=_JWT_EXPIRE_DAYS)
    return jwt.encode({"sub": str(user_id), "name": username, "exp": exp}, _JWT_SECRET, algorithm=_JWT_ALGO)

def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGO])
    except JWTError:
        return {}

def get_current_user(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    payload = _decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="인증이 만료되었습니다")
    return {"user_id": int(payload["sub"]), "username": payload["name"]}

# ─────────────────────────────────────────────────────────
# FastAPI 앱
# ─────────────────────────────────────────────────────────
app = FastAPI(title="포켓주식 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────
# Pydantic 모델
# ─────────────────────────────────────────────────────────
class LoginBody(BaseModel):
    username: str
    password: str

class RegisterBody(BaseModel):
    username: str
    password: str

class HoldingBody(BaseModel):
    code: str
    name: str
    avg_price: float
    qty: int

class WatchlistBody(BaseModel):
    code: str
    name: str
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None

class StockSearchBody(BaseModel):
    query: str

# ─────────────────────────────────────────────────────────
# 인증 API
# ─────────────────────────────────────────────────────────
@app.post("/api/auth/login")
def login(body: LoginBody):
    ok, user_id = db.verify_user(body.username, body.password)
    if not ok:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 틀렸습니다")
    token = _make_token(user_id, body.username)
    return {"token": token, "username": body.username, "user_id": user_id}

@app.post("/api/auth/register")
def register(body: RegisterBody):
    ok, msg = db.create_user(body.username, body.password)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    ok2, user_id = db.verify_user(body.username, body.password)
    token = _make_token(user_id, body.username)
    return {"token": token, "username": body.username, "user_id": user_id, "message": msg}

@app.get("/api/auth/me")
def me(user=Depends(get_current_user)):
    return user

# ─────────────────────────────────────────────────────────
# 홈 API
# ─────────────────────────────────────────────────────────
@app.get("/api/home")
def home_data():
    try:
        idx = get_index_data()
        us_raw = get_us_indices()
        kp = idx.get("KOSPI", {})
        kd = idx.get("KOSDAQ", {})
        sp = us_raw.get("S&P500", {})
        nd = us_raw.get("나스닥", {})
        indices = {
            "kospi": kp.get("current", 0),
            "kospi_change_pct": kp.get("change_pct", 0),
            "kosdaq": kd.get("current", 0),
            "kosdaq_change_pct": kd.get("change_pct", 0),
            "sp500": sp.get("current", 0),
            "sp500_change_pct": sp.get("change_pct", 0),
            "nasdaq": nd.get("current", 0),
            "nasdaq_change_pct": nd.get("change_pct", 0),
        }
        us = {"sp500_pct": sp.get("change_pct", 0), "nasdaq_pct": nd.get("change_pct", 0)}
        kr = {"kospi": kp.get("current", 0), "kospi_pct": kp.get("change_pct", 0),
              "kosdaq": kd.get("current", 0), "kosdaq_pct": kd.get("change_pct", 0)}
        analysis = analyze_us_impact(us, kr, {})
        forecast = generate_forecast(us, kr, {})
        return {
            "indices": indices,
            "analysis": analysis,
            "forecast": forecast,
            "market_phase": market_phase(),
            "is_open": is_market_open(),
        }
    except Exception as e:
        return {"error": str(e), "indices": {}, "analysis": [], "forecast": {}, "market_phase": "close", "is_open": False}

# ─────────────────────────────────────────────────────────
# 시장 지수 API
# ─────────────────────────────────────────────────────────
@app.get("/api/market")
def market_data():
    try:
        idx = get_index_data()
        us = get_us_indices()
        return {"kr": idx, "us": us}
    except Exception as e:
        return {"error": str(e)}

# ─────────────────────────────────────────────────────────
# 뉴스 API
# ─────────────────────────────────────────────────────────
@app.get("/api/news")
def market_news():
    try:
        return {"news": fetch_market_news()}
    except Exception as e:
        return {"news": [], "error": str(e)}

@app.get("/api/news/{code}")
def stock_news(code: str):
    try:
        tickers = get_all_tickers()
        name = tickers.get(code, code)
        return {"news": fetch_stock_news(code, name), "name": name}
    except Exception as e:
        return {"news": [], "error": str(e)}

# ─────────────────────────────────────────────────────────
# 보유종목 API
# ─────────────────────────────────────────────────────────
@app.get("/api/holdings")
def get_holdings_list(user=Depends(get_current_user)):
    holdings = db.get_holdings(user["user_id"])
    if not holdings:
        return {"holdings": [], "total_value": 0, "total_pnl": 0}
    try:
        indices = get_market_indices()
    except Exception:
        indices = {}
    result = []
    total_value = 0
    total_cost = 0
    for h in holdings:
        code = h["code"]
        price_key = f"price_{code}"
        cur_price = indices.get(price_key, h["avg_price"])
        value = cur_price * h["qty"]
        cost = h["avg_price"] * h["qty"]
        pnl = value - cost
        pnl_pct = (pnl / cost * 100) if cost > 0 else 0
        total_value += value
        total_cost += cost
        result.append({
            **h,
            "cur_price": cur_price,
            "value": value,
            "pnl": pnl,
            "pnl_pct": round(pnl_pct, 2),
        })
    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
    return {
        "holdings": result,
        "total_value": total_value,
        "total_pnl": total_pnl,
        "total_pnl_pct": round(total_pnl_pct, 2),
    }

@app.post("/api/holdings")
def add_holding(body: HoldingBody, user=Depends(get_current_user)):
    ok, msg = db.add_holding(user["user_id"], body.code, body.name, body.avg_price, body.qty)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@app.delete("/api/holdings/{code}")
def delete_holding(code: str, user=Depends(get_current_user)):
    db.delete_holding(user["user_id"], code)
    return {"message": "삭제 완료"}

@app.get("/api/holdings/{code}/detail")
def holding_detail(code: str, user=Depends(get_current_user)):
    holdings = db.get_holdings(user["user_id"])
    h = next((x for x in holdings if x["code"] == code), None)
    if not h:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다")
    try:
        ohlcv = get_ohlcv(code, days=60)
        inv = get_investor_trading(code, days=5)
        analysis = analyze_stock(ohlcv, inv, h["avg_price"], h["qty"])
        pd2 = get_current_price(code)
        analysis["cur_price"] = pd2.get("current_price", h["avg_price"])
        news = fetch_stock_news(code, h["name"])
        analysis["news"] = news[:3]
    except Exception as e:
        analysis = {"error": str(e)}
    return {"holding": h, "analysis": analysis}

# ─────────────────────────────────────────────────────────
# 관심종목 API
# ─────────────────────────────────────────────────────────
@app.get("/api/watchlist")
def get_watchlist(user=Depends(get_current_user)):
    items = db.get_watchlist(user["user_id"])
    return {"watchlist": items}

@app.post("/api/watchlist")
def add_watchlist(body: WatchlistBody, user=Depends(get_current_user)):
    ok, msg = db.add_watchlist(user["user_id"], body.code, body.name, body.target_price, body.stop_loss)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@app.delete("/api/watchlist/{code}")
def delete_watchlist(code: str, user=Depends(get_current_user)):
    db.delete_watchlist(user["user_id"], code)
    return {"message": "삭제 완료"}

@app.get("/api/watchlist/{code}/detail")
def watchlist_detail(code: str, user=Depends(get_current_user)):
    items = db.get_watchlist(user["user_id"])
    item = next((x for x in items if x["code"] == code), None)
    if not item:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다")
    try:
        ohlcv = get_ohlcv(code, days=60)
        inv = get_investor_trading(code, days=5)
        analysis = analyze_stock(ohlcv, inv)
        pd2 = get_current_price(code)
        analysis["cur_price"] = pd2.get("current_price", 0)
        timing = watchlist_timing(analysis, item.get("target_price"), item.get("stop_loss"))
        analysis["timing"] = timing
    except Exception as e:
        analysis = {"error": str(e)}
    return {"item": item, "analysis": analysis}

# ─────────────────────────────────────────────────────────
# 종목 검색 API
# ─────────────────────────────────────────────────────────
@app.get("/api/stock/search")
def search_stock(q: str = ""):
    if not q:
        return {"results": []}
    results = search_stock_by_name(q, max_results=10)
    return {"results": [{"name": r[0], "code": r[1]} for r in results]}

@app.get("/api/stock/{code}")
def stock_detail(code: str):
    try:
        tickers = get_all_tickers()
        name = tickers.get(code, code)
        ohlcv = get_ohlcv(code, days=60)
        inv = get_investor_trading(code, days=5)
        analysis = analyze_stock(ohlcv, inv)
        pd2 = get_current_price(code)
        analysis["cur_price"] = pd2.get("current_price", 0)
        news = fetch_stock_news(code, name)
        return {"code": code, "name": name, "analysis": analysis, "news": news}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─────────────────────────────────────────────────────────
# 매집 스캐너 API
# ─────────────────────────────────────────────────────────
_scanner_cache = {"data": None, "ts": 0}

@app.get("/api/scanner")
def scanner():
    import time
    now = time.time()
    if _scanner_cache["data"] and now - _scanner_cache["ts"] < 3600:
        return _scanner_cache["data"]
    try:
        stocks = get_top_stocks(100)
        results = []
        for s in stocks[:100]:
            try:
                ohlcv = get_ohlcv(s["code"], days=60)
                inv = get_investor_trading(s["code"], days=5)
                a = analyze_stock(ohlcv, inv)
                if a["score"] >= 3:
                    pd2 = get_current_price(s["code"])
                    results.append({
                        "code": s["code"], "name": s["name"],
                        "price": pd2.get("current_price", 0),
                        "change_pct": pd2.get("change_pct", 0),
                        **a
                    })
            except Exception:
                continue
        results.sort(key=lambda x: (x["score"], x.get("volume_ratio", 0)), reverse=True)
        data = {"results": results[:20]}
        _scanner_cache["data"] = data
        _scanner_cache["ts"] = now
        return data
    except Exception as e:
        return {"results": [], "error": str(e)}

# ─────────────────────────────────────────────────────────
# 정적 파일 서빙 (프론트엔드)
# ─────────────────────────────────────────────────────────
app.mount("/icons", StaticFiles(directory="frontend/icons"), name="icons")
app.mount("/js", StaticFiles(directory="frontend/js"), name="js")

@app.get("/manifest.json")
def manifest():
    return FileResponse("frontend/manifest.json")

@app.get("/service-worker.js")
def service_worker():
    return FileResponse("frontend/service-worker.js", media_type="application/javascript")

@app.get("/")
@app.head("/")
def root():
    return FileResponse("frontend/index.html")

@app.get("/{full_path:path}")
def serve_frontend(full_path: str):
    return FileResponse("frontend/index.html")
