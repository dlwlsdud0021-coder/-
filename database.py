"""
database.py — 유저/보유종목/관심종목 Supabase(PostgreSQL) 관리
- 로그인, 회원가입
- 종목 추가/삭제/조회 (유저별 분리)
"""

import hashlib
import json
import os

from supabase import create_client, Client

_SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
_SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

_client: Client | None = None


def _db() -> Client:
    global _client
    if _client is None:
        _client = create_client(_SUPABASE_URL, _SUPABASE_KEY)
    return _client


# ─────────────────────────────────────────────────────────
# 테이블 초기화 (Supabase SQL Editor에서 한 번 실행)
# ─────────────────────────────────────────────────────────
INIT_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id            BIGSERIAL PRIMARY KEY,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS holdings (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users(id),
    code       TEXT NOT NULL,
    name       TEXT NOT NULL,
    avg_price  REAL NOT NULL,
    qty        INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, code)
);

CREATE TABLE IF NOT EXISTS watchlist (
    id           BIGSERIAL PRIMARY KEY,
    user_id      BIGINT NOT NULL REFERENCES users(id),
    code         TEXT NOT NULL,
    name         TEXT NOT NULL,
    target_price REAL,
    stop_loss    REAL,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, code)
);

CREATE TABLE IF NOT EXISTS market_predictions (
    id                  BIGSERIAL PRIMARY KEY,
    date                TEXT NOT NULL,
    index_name          TEXT NOT NULL DEFAULT 'KOSPI',
    predicted_direction TEXT NOT NULL,
    predicted_change    REAL,
    confidence          INTEGER,
    prediction_basis    TEXT,
    gemini_text         TEXT,
    actual_direction    TEXT,
    actual_change       REAL,
    is_correct          INTEGER,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(date, index_name)
);
"""


# ─────────────────────────────────────────────────────────
# 비밀번호
# ─────────────────────────────────────────────────────────
def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


# ─────────────────────────────────────────────────────────
# 유저
# ─────────────────────────────────────────────────────────
def create_user(username: str, password: str) -> tuple:
    """(성공여부, 메시지)"""
    if len(username) < 2:
        return False, "아이디는 2자 이상이어야 합니다."
    if len(password) < 4:
        return False, "비밀번호는 4자 이상이어야 합니다."
    try:
        _db().table("users").insert({
            "username": username,
            "password_hash": _hash(password)
        }).execute()
        return True, "회원가입 완료!"
    except Exception as e:
        msg = str(e)
        if "duplicate" in msg.lower() or "unique" in msg.lower():
            return False, "이미 사용 중인 아이디입니다."
        return False, msg


def verify_user(username: str, password: str) -> tuple:
    """(성공여부, user_id)"""
    try:
        res = _db().table("users") \
            .select("id") \
            .eq("username", username) \
            .eq("password_hash", _hash(password)) \
            .execute()
        if res.data:
            return True, res.data[0]["id"]
        return False, -1
    except Exception:
        return False, -1


def get_username(user_id: int) -> str:
    try:
        res = _db().table("users").select("username").eq("id", user_id).execute()
        return res.data[0]["username"] if res.data else ""
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────
# 보유종목
# ─────────────────────────────────────────────────────────
def add_holding(user_id: int, code: str, name: str,
                avg_price: float, qty: int) -> tuple:
    try:
        _db().table("holdings").upsert({
            "user_id": user_id,
            "code": code,
            "name": name,
            "avg_price": avg_price,
            "qty": qty,
        }, on_conflict="user_id,code").execute()
        return True, f"{name} 추가 완료"
    except Exception as e:
        return False, str(e)


def get_holdings(user_id: int) -> list:
    try:
        res = _db().table("holdings") \
            .select("code, name, avg_price, qty") \
            .eq("user_id", user_id) \
            .order("created_at") \
            .execute()
        return res.data or []
    except Exception:
        return []


def delete_holding(user_id: int, code: str):
    try:
        _db().table("holdings").delete() \
            .eq("user_id", user_id).eq("code", code).execute()
    except Exception:
        pass


def update_holding(user_id: int, code: str, avg_price: float, qty: int):
    try:
        _db().table("holdings") \
            .update({"avg_price": avg_price, "qty": qty}) \
            .eq("user_id", user_id).eq("code", code).execute()
    except Exception:
        pass


# ─────────────────────────────────────────────────────────
# 관심종목
# ─────────────────────────────────────────────────────────
def add_watchlist(user_id: int, code: str, name: str,
                  target_price: float = None, stop_loss: float = None) -> tuple:
    try:
        _db().table("watchlist").upsert({
            "user_id": user_id,
            "code": code,
            "name": name,
            "target_price": target_price,
            "stop_loss": stop_loss,
        }, on_conflict="user_id,code").execute()
        return True, f"{name} 관심종목 추가 완료"
    except Exception as e:
        return False, str(e)


def get_watchlist(user_id: int) -> list:
    try:
        res = _db().table("watchlist") \
            .select("code, name, target_price, stop_loss") \
            .eq("user_id", user_id) \
            .order("created_at") \
            .execute()
        return res.data or []
    except Exception:
        return []


def delete_watchlist(user_id: int, code: str):
    try:
        _db().table("watchlist").delete() \
            .eq("user_id", user_id).eq("code", code).execute()
    except Exception:
        pass


def update_watchlist(user_id: int, code: str,
                     target_price=None, stop_loss=None):
    try:
        _db().table("watchlist") \
            .update({"target_price": target_price, "stop_loss": stop_loss}) \
            .eq("user_id", user_id).eq("code", code).execute()
    except Exception:
        pass


# ─────────────────────────────────────────────────────────
# 예측 저장 / 조회 / 결과 업데이트
# ─────────────────────────────────────────────────────────
def save_prediction(date: str, index_name: str, predicted_direction: str,
                    predicted_change: float, confidence: int,
                    prediction_basis: dict, gemini_text: str) -> bool:
    try:
        _db().table("market_predictions").upsert({
            "date": date,
            "index_name": index_name,
            "predicted_direction": predicted_direction,
            "predicted_change": predicted_change,
            "confidence": confidence,
            "prediction_basis": json.dumps(prediction_basis, ensure_ascii=False),
            "gemini_text": gemini_text,
        }, on_conflict="date,index_name", ignore_duplicates=True).execute()
        return True
    except Exception:
        return False


def update_prediction_result(date: str, index_name: str,
                              actual_direction: str, actual_change: float) -> bool:
    try:
        res = _db().table("market_predictions") \
            .select("predicted_direction") \
            .eq("date", date).eq("index_name", index_name).execute()
        is_correct = None
        if res.data:
            is_correct = 1 if res.data[0]["predicted_direction"] == actual_direction else 0
        _db().table("market_predictions") \
            .update({
                "actual_direction": actual_direction,
                "actual_change": actual_change,
                "is_correct": is_correct,
            }) \
            .eq("date", date).eq("index_name", index_name).execute()
        return True
    except Exception:
        return False


def get_recent_predictions(limit: int = 10) -> list:
    try:
        res = _db().table("market_predictions") \
            .select("date, index_name, predicted_direction, predicted_change, "
                    "confidence, actual_direction, actual_change, is_correct, gemini_text") \
            .order("date", desc=True) \
            .limit(limit) \
            .execute()
        return res.data or []
    except Exception:
        return []


def get_prediction_accuracy() -> dict:
    try:
        res = _db().table("market_predictions").select("is_correct").execute()
        rows = res.data or []
        total = len(rows)
        evaluated = sum(1 for r in rows if r["is_correct"] is not None)
        correct = sum(1 for r in rows if r["is_correct"] == 1)
        accuracy = round(correct / evaluated * 100, 1) if evaluated else None
        return {"total": total, "correct": correct,
                "evaluated": evaluated, "accuracy": accuracy}
    except Exception:
        return {"total": 0, "correct": 0, "evaluated": 0, "accuracy": None}


# ─────────────────────────────────────────────────────────
# 앱 시작 시 연결 확인
# ─────────────────────────────────────────────────────────
def init_db():
    """Supabase 연결 확인 (테이블은 Supabase SQL Editor에서 미리 생성)"""
    try:
        _db().table("users").select("id").limit(1).execute()
    except Exception as e:
        print(f"[DB] Supabase 연결 실패: {e}")


init_db()
