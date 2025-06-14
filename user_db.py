import json
from pathlib import Path
import os

# JSONファイルへのパス
DATA_PATH = Path("data/users.json")


def load_users() -> list[dict]:
    """
    data/users.json を読み込み、ユーザーリストを返す。
    存在しない場合は空リスト。
    """
    if not DATA_PATH.exists():
        return []
    try:
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def save_users(users: list[dict]) -> None:
    """
    ユーザーリストを data/users.json に書き込む。
    """
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(
        json.dumps(users, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def add_user(name: str, image_path: str, features: list) -> None:
    """
    1件のユーザー情報を追加して保存する。
    """
    users = load_users()
    users.append({
        "name": name,
        "image_path": image_path,
        "features": features,
    })
    save_users(users)


def clear_users() -> None:
    """
    ユーザー一覧を空にリセットし、data/users.jsonをクリアする。
    """
    save_users([])


def delete_user(target_name: str) -> None:
    """
    指定した名前のユーザーを削除し、対応する画像ファイルも削除する。
    """
    users = load_users()
    new_users = []
    for u in users:
        if u["name"] == target_name:
            try:
                os.remove(u["image_path"])
            except OSError:
                pass
        else:
            new_users.append(u)
    save_users(new_users)
