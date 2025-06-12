# user_db.py
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# .env を読み込む
load_dotenv()
SUPA_URL = os.getenv("SUPABASE_URL")
SUPA_KEY = os.getenv("SUPABASE_ANON_KEY")

# Supabase クライアントを生成
supabase: Client = create_client(SUPA_URL, SUPA_KEY)

def add_user(name: str, image_key: str, features: list) -> None:
    """Supabase の users テーブルに新規レコードを挿入する"""
    data = {
        "name": name,
        "image_key": image_key,
        "features": features
    }
    res = supabase.table("users").insert(data).execute()
    if res.error:
        raise RuntimeError(f"Supabase insert error: {res.error.message}")

def load_users() -> list[dict]:
    """Supabase の users テーブルから全レコードを取得"""
    res = supabase.table("users").select("*").execute()
    if res.error:
        raise RuntimeError(f"Supabase select error: {res.error.message}")
    return res.data or []

def delete_user(name: str) -> None:
    """指定した name のユーザーを削除"""
    res = supabase.table("users").delete().eq("name", name).execute()
    if res.error:
        raise RuntimeError(f"Supabase delete error: {res.error.message}")
