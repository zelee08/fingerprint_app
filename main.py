import streamlit as st
import os
from datetime import datetime
import image_utils
import user_db
import identifier
import logging
import zipfile
import tempfile


# --- ディレクトリ準備 ---
if not os.path.exists("logs"):
    os.makedirs("logs")
if not os.path.exists("images"):
    os.makedirs("images")

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
    .css-18ni7ap { background-color: #f7f7f7; }
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
    st.title("🔧 メニュー")
    page = st.radio(
        "機能を選択",
        options=["指紋登録", "登録ユーザー一覧", "指紋識別", "バックアップ"]
    )
    if page != "バックアップ":  # バックアップページ以外では閾値とリセット表示
        threshold = st.slider("マッチング閾値", 100, 300, 150)
        st.markdown("---")
        if st.button("🔄 全データリセット"):
            user_db.clear_users()
            for f in os.listdir("images"):
                os.remove(os.path.join("images", f))
            st.success("✅ 全データをリセットしました")

if page == "指紋登録":
    st.markdown("## 📝 指紋登録")

    with st.form("register_form", clear_on_submit=True):
        name = st.text_input("名前を入力", placeholder="例：田中太郎")

        # 🔁 カメラ表示トグル
        show_camera = st.checkbox("📸 カメラを起動して撮影する", value=False)

        if show_camera:
            camera_image = st.camera_input("📷 指紋を撮影")
        else:
            camera_image = None

        # 🔁 画像アップロード（カメラと併用可）
        uploaded_file = st.file_uploader("📁 画像をアップロード", type=["png", "jpg", "jpeg"], key="register_upload")

        # 🖼️ 入力された画像（撮影 or アップロードのいずれか）
        img_data = camera_image or uploaded_file

        submitted = st.form_submit_button("登録する", use_container_width=True)

    if submitted:
        if not name or not img_data:
            st.error("名前と画像を両方入力してください。")
            logging.warning(f"登録失敗: name={name}, img_data={bool(img_data)}")
        else:
            try:
                # 1. 画像をローカル保存
                img_bytes = img_data.getvalue()
                ts = datetime.now().strftime("%Y%m%d%H%M%S")
                filename = f"{name}_{ts}.png"
                save_path = os.path.join("images", filename)
                with open(save_path, "wb") as f:
                    f.write(img_bytes)

                features = image_utils.extract_features(save_path)
                if not features:
                    st.error("特徴量が抽出できませんでした。別の画像を試してください。")
                    logging.warning(f"特徴量抽出失敗: {save_path}")
                    st.stop()  # または continue

                MIN_FEATURES = 50
                if len(features) < MIN_FEATURES:
                    st.error(f"有効な指紋画像ではありません（検出特徴点：{len(features)}）")
                    logging.warning(f"指紋判定失敗: detected={len(features)} < {MIN_FEATURES}")
                    st.stop()  # または continue
                # ────────────────────────────────

                # 3. DB に登録
                user_db.add_user(name, save_path, features)
                st.success(f"{name} さんの指紋を登録しました。")
                st.image(save_path, use_column_width=True)
                logging.info(f"登録成功: name={name}, path={save_path}")

            except Exception as e:
                st.error(f"登録中にエラーが発生しました：{e}")
                logging.error(f"登録処理エラー: {e}")

# --- 登録ユーザー一覧ページ ---
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
                    st.image(u["image_path"], use_container_width=True)
                    st.caption(f"特徴量数：{len(u['features'])}")
                    if st.button(f"🗑️ {u['name']} を削除"):
                        user_db.delete_user(u['name'])
                        st.success(f"{u['name']} さんを削除しました")
                        st.rerun()

# --- 指紋識別ページ ---
elif page == "指紋識別":
    st.markdown("## 🔎 指紋識別")

    with st.form("identify_form", clear_on_submit=True):
        # 🔁 カメラ表示トグル
        show_camera = st.checkbox("📸 カメラを起動して撮影する", value=False)

        if show_camera:
            camera_image = st.camera_input("📷 指紋を撮影")
        else:
            camera_image = None

        # 🔁 画像アップロード（カメラと併用可）
        uploaded_file = st.file_uploader("📁 指紋画像をアップロード", type=["png", "jpg", "jpeg"], key="identify_upload")

        # 🖼️ 入力された画像（撮影 or アップロードのいずれか）
        img_data = camera_image or uploaded_file

        submitted = st.form_submit_button("識別する", use_container_width=True)
    if submitted:
        if not img_data:
            st.error("画像をアップロードまたは撮影してください。")
            logging.warning("識別失敗: 入力画像なし")
        else:
            try:
                # バイト列を一時ファイルに保存
                img_bytes = img_data.getvalue()
                ts = datetime.now().strftime("%Y%m%d%H%M%S")
                tmp_name = f"input_{ts}.png"
                tmp_path = os.path.join("images", tmp_name)
                with open(tmp_path, "wb") as f:
                    f.write(img_bytes)

                # ファイル版の特徴量抽出を呼び出し
                inp_feats = image_utils.extract_features(tmp_path)
                if not inp_feats:
                    raise RuntimeError("特徴量抽出失敗")

                # マッチング
                users = user_db.load_users()
                name, score = identifier.match_fingerprint(inp_feats, users, threshold)
                if name:
                    st.success(f"持ち主：{name} さん (マッチ数：{score})")
                else:
                    st.warning(f"未登録の指紋です (最高マッチ数：{score})")

            except Exception as e:
                st.error(f"識別中にエラーが発生しました: {e}")
                logging.error(f"識別処理エラー: {e}")

            finally:
                #  一時ファイルを必ず削除
                try:
                    if 'tmp_path' in locals() and os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except OSError:
                    pass

# -----------------------
# 🔹 1. ZIPでバックアップ作成・ダウンロード
# -----------------------
def create_backup_zip(zip_name="backup.zip"):
    with zipfile.ZipFile(zip_name, "w") as zipf:
        if os.path.exists("data/users.json"):
            zipf.write("data/users.json", arcname="users.json")
        image_dir = "images"
        if os.path.exists(image_dir):
            for filename in os.listdir(image_dir):
                path = os.path.join(image_dir, filename)
                if os.path.isfile(path):
                    zipf.write(path, arcname=os.path.join("images", filename))
    return zip_name

st.subheader("📦 バックアップと復元")

if st.button("⬇️ バックアップをダウンロード"):
    zip_path = create_backup_zip()
    with open(zip_path, "rb") as f:
        st.download_button(
            label="📥 ここからダウンロード",
            data=f,
            file_name="fingerprint_backup.zip",
            mime="application/zip"
        )

# -----------------------
# 🔹 2. ZIPアップロード → 復元
# -----------------------
uploaded = st.file_uploader("📂 バックアップ(zip)をアップロードして復元", type=["zip"])

if uploaded is not None:
    with open("restore.zip", "wb") as f:
        f.write(uploaded.read())
    with zipfile.ZipFile("restore.zip", "r") as zipf:
        zipf.extractall()

    st.success("✅ 復元が完了しました！")

    # 中身が正しく入っているか確認
    if os.path.exists("data/users.json"):
        st.info("users.json が復元されました。")
    if os.path.exists("images"):
        st.info(f"{len(os.listdir('images'))} 枚の指紋画像が復元されました。")

elif page == "バックアップ":
    st.markdown("## 📦 データのバックアップと復元")

    # --- zip作成関数（日時付きファイル名） ---
    from datetime import datetime
def create_backup_zip():
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"backup_{now}.zip"
    zip_path = os.path.join(tempfile.gettempdir(), zip_name)  # ✅ ここ重要！
    with zipfile.ZipFile(zip_path, "w") as zipf:
        if os.path.exists("data/users.json"):
            zipf.write("data/users.json", arcname="users.json")
        if os.path.exists("images"):
            for filename in os.listdir("images"):
                f = os.path.join("images", filename)
                if os.path.isfile(f):
                    zipf.write(f, arcname=os.path.join("images", filename))
    return zip_path

    # --- バックアップ作成UI ---
    if st.button("⬇️ バックアップを作成してダウンロード"):
        zip_path = create_backup_zip()
        with open(zip_path, "rb") as f:
            st.download_button(
                label="📥 ダウンロードはこちら",
                data=f,
                file_name=zip_path,
                mime="application/zip"
            )

    st.markdown("---")

    # --- アップロード＆復元 ---
    uploaded = st.file_uploader("📂 バックアップ(zip)をアップロードして復元", type=["zip"], key="backup_upload")

    if uploaded is not None:
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
