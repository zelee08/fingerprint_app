import json
from pathlib import Path
import os

# JSONファイルへのパス
DATA_PATH = Path("data/users.json")

def load_users() -> list:
    """users.json を読み込んでPythonのリストで返す。存在しなければ空リスト。"""
    if not DATA_PATH.exists():
        return []
    try:
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

def save_users(users: list):
    """Pythonのリストを JSON に書き出す。"""
    DATA_PATH.write_text(
        json.dumps(users, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

def add_user(name: str, image_path: str, features: list):
    """1件分のユーザー登録データを追加して保存する。"""
    users = load_users()
    users.append({
        "name": name,
        "image_path": image_path,
        "features": features
    })
    save_users(users)

# user_db.py の最後に追記
def clear_users():
    """users.json を空のリストにリセットする。"""
    save_users([])

def delete_user(target_name: str):
    """指定した名前のユーザー情報と画像ファイルを削除する。"""
    users = load_users()
    new_users = []
    # 削除対象以外を残す
    for u in users:
        if u["name"] == target_name:
            # 画像ファイルも削除
            try:
                os.remove(u["image_path"])
            except:
                pass
        else:
            new_users.append(u)
    save_users(new_users)
