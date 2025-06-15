import streamlit as st
import os
from datetime import datetime
import image_utils
import user_db
import identifier
import logging
import zipfile
import tempfile
from io import BytesIO

# --- ディレクトリ準備 ---
for folder in ["logs", "images", "data"]:
    os.makedirs(folder, exist_ok=True)
if not os.path.exists("data/users.json"):
    with open("data/users.json", "w") as f:
        f.write("[]")

# --- ログ設定 ---
logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# --- Streamlit ページ設定 ---
st.set_page_config(
    page_title="指紋識別アプリ",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- カスタムCSS ---
st.markdown(
    """
    <style>
    footer { visibility: hidden; }
    html, body, [class*="css"] { font-family: "Yu Gothic UI", sans-serif; }
    div.stButton > button {
        background-color: #4C6EF5; color: white;
        padding: .5rem 1rem; border-radius: .5rem; border: none;
    }
    div.stButton > button:hover { background-color: #364FC7; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- サイドバー ---
with st.sidebar:
    st.title("メニュー")
    page = st.radio(
        "機能を選択",
        options=["指紋登録", "登録ユーザー一覧", "指紋識別", "バックアップ"]
    )
    if page != "バックアップ":
        threshold = st.slider("マッチング閾値", 100, 300, 150)
        st.markdown("---")
        if st.button("🔄 全データリセット"):
            user_db.clear_users()
            for f in os.listdir("images"):
                os.remove(os.path.join("images", f))
            st.success("✅ 全データをリセットしました")

# --- 登録ページ ---
if page == "指紋登録":
    st.markdown("## 📝 指紋登録")
    with st.form("register_form", clear_on_submit=True):
        name = st.text_input("名前を入力", placeholder="例：田中太郎")
        show_camera = st.checkbox("カメラを起動して撮影", value=False)
        camera_image = st.camera_input("指紋を撮影") if show_camera else None
        uploaded_file = st.file_uploader("📁 画像をアップロード", type=["png", "jpg", "jpeg"], key="register_upload")
        img_data = camera_image or uploaded_file
        submitted = st.form_submit_button("登録する", use_container_width=True)

    if submitted:
        if not name or not img_data:
            st.error("名前と画像を両方入力してください。")
            logging.warning(f"登録失敗: name={name}, img_data={bool(img_data)}")
        else:
            try:
                img_bytes = img_data.getvalue()
                ts = datetime.now().strftime("%Y%m%d%H%M%S")
                filename = f"{name}_{ts}.png"
                save_path = os.path.join("images", filename)
                with open(save_path, "wb") as f:
                    f.write(img_bytes)
                features = image_utils.extract_features(save_path)
                if not features:
                    st.error("特徴量が抽出できませんでした。別の画像を試してください。")
                    st.stop()
                if len(features) < 50:
                    st.error(f"有効な指紋画像ではありません（検出特徴点：{len(features)}）")
                    st.stop()
                user_db.add_user(name, save_path, features)
                st.success(f"{name} さんの指紋を登録しました。")
                st.image(save_path, use_column_width=True)
                
                # 自動バックアップ作成
                def create_backup_zip_bytes():
                    buffer = BytesIO()
                    with zipfile.ZipFile(buffer, "w") as zipf:
                        if os.path.exists("data/users.json"):
                            zipf.write("data/users.json", arcname="users.json")
                        for f in os.listdir("images"):
                            path = os.path.join("images", f)
                            if os.path.isfile(path):
                                zipf.write(path, arcname=os.path.join("images", f))
                    buffer.seek(0)
                    return buffer

                backup = create_backup_zip_bytes()
                st.download_button("📦 登録後バックアップを保存", data=backup, file_name="fingerprint_backup.zip", mime="application/zip")

            except Exception as e:
                st.error(f"登録中にエラーが発生しました：{e}")

# --- ユーザー一覧 ---
elif page == "登録ユーザー一覧":
    st.markdown("## 📋 登録ユーザー一覧")
    users = user_db.load_users()
    if not users:
        st.info("まだ登録された指紋データがありません。")
    else:
        for i in range(0, len(users), 2):
            cols = st.columns(2, gap="medium")
            for idx, u in enumerate(users[i:i+2]):
                with cols[idx]:
                    st.markdown(f"#### {u['name']}")
                    st.image(u["image_path"], use_column_width=True)
                    st.caption(f"特徴量数：{len(u['features'])}")
                    if st.button(f"🗑️ {u['name']} を削除"):
                        user_db.delete_user(u['name'])
                        st.success(f"{u['name']} さんを削除しました")
                        st.rerun()

# --- 指紋識別 ---
elif page == "指紋識別":
    st.markdown("## 🔎 指紋識別")
    with st.form("identify_form", clear_on_submit=True):
        show_camera = st.checkbox("カメラを起動して撮影", value=False)
        camera_image = st.camera_input("指紋を撮影") if show_camera else None
        uploaded_file = st.file_uploader("📁 指紋画像をアップロード", type=["png", "jpg", "jpeg"], key="identify_upload")
        img_data = camera_image or uploaded_file
        submitted = st.form_submit_button("識別する", use_container_width=True)
    if submitted and img_data:
        try:
            img_bytes = img_data.getvalue()
            ts = datetime.now().strftime("%Y%m%d%H%M%S")
            tmp_path = os.path.join("images", f"input_{ts}.png")
            with open(tmp_path, "wb") as f:
                f.write(img_bytes)
            inp_feats = image_utils.extract_features(tmp_path)
            users = user_db.load_users()
            name, score = identifier.match_fingerprint(inp_feats, users, threshold)
            if name:
                st.success(f"持ち主：{name} さん (マッチ数：{score})")
            else:
                st.warning(f"未登録の指紋です (最高マッチ数：{score})")
        except Exception as e:
            st.error(f"識別中にエラーが発生しました: {e}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

# --- バックアップ ---
elif page == "バックアップ":
    st.markdown("## 📦 データのバックアップと復元")

    def create_backup_zip():
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name = f"backup_{now}.zip"
        zip_path = os.path.join(tempfile.gettempdir(), zip_name)
        with zipfile.ZipFile(zip_path, "w") as zipf:
            if os.path.exists("data/users.json"):
                zipf.write("data/users.json", arcname="users.json")
            if os.path.exists("images"):
                for filename in os.listdir("images"):
                    f = os.path.join("images", filename)
                    if os.path.isfile(f):
                        zipf.write(f, arcname=os.path.join("images", filename))
        return zip_path

    if st.button("⬇️ バックアップを作成してダウンロード"):
        zip_path = create_backup_zip()
        with open(zip_path, "rb") as f:
            st.download_button("📥 ダウンロードはこちら", data=f, file_name=os.path.basename(zip_path), mime="application/zip")

    st.markdown("---")

    uploaded = st.file_uploader("📂 バックアップ(zip)をアップロードして復元", type=["zip"], key="backup_upload")
    if uploaded:
        with open("restore.zip", "wb") as f:
            f.write(uploaded.read())
        with zipfile.ZipFile("restore.zip", "r") as zipf:
            zipf.extractall()
        st.success("✅ 復元が完了しました！")
        if os.path.exists("data/users.json"):
            st.info("users.json が復元されました。")
        if os.path.exists("images"):
            st.info(f"{len(os.listdir('images'))} 枚の指紋画像が復元されました。")
        st.experimental_rerun()
