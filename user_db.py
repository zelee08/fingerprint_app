# user_db.py
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# .env の読み込み
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def add_user(name: str, image_key: str, features: list) -> None:
    """
    Supabase の users テーブルに新規レコードを挿入する
    """
    try:
        supabase.table("users").insert({
            "name": name,
            "image_key": image_key,
            "features": features
        }).execute()
    except Exception as e:
        raise RuntimeError(f"Supabase insert error: {e}")


def load_users() -> list[dict]:
    """
    Supabase の users テーブルから全レコードを取得する
    """
    try:
        response = supabase.table("users").select("*").order("id", desc=False).execute()
        return response.data or []
    except Exception as e:
        raise RuntimeError(f"Supabase select error: {e}")
