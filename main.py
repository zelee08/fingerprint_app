import streamlit as st
import os
from datetime import datetime
import image_utils
import user_db
import identifier
import logging

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
        options=["指紋登録", "登録ユーザー一覧", "指紋識別"]
    )
    threshold = st.slider("マッチング閾値", 0, 100, 15)
    st.markdown("---")
    if st.button("🔄 全データリセット"):
        user_db.clear_users()
        for f in os.listdir("images"):
            os.remove(os.path.join("images", f))
        st.success("✅ 全データをリセットしました")

# --- 指紋登録ページ ---
if page == "指紋登録":
    st.markdown("## 📝 指紋登録")
    with st.form("register_form", clear_on_submit=True):
        name = st.text_input("名前を入力", placeholder="例：田中太郎")
        camera_image = st.camera_input("📷 カメラで指紋を撮影")
        uploaded_file = st.file_uploader("📁 画像をアップロード", type=["png","jpg","jpeg"])
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
                    logging.warning(f"特徴量抽出失敗: {save_path}")
                else:
                    user_db.add_user(name, save_path, features)
                    st.success(f"{name} さんの指紋を登録しました。")
                    st.image(save_path, use_container_width=True)
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
                        st.experimental_rerun()

# --- 指紋識別ページ ---
elif page == "指紋識別":
    st.markdown("## 🔎 指紋識別")
    with st.form("identify_form", clear_on_submit=True):
        camera_image = st.camera_input("📷 カメラで撮影")
        uploaded_file = st.file_uploader("📁 画像をアップロード", type=["png","jpg","jpeg"])
        img_data = camera_image or uploaded_file
        submitted = st.form_submit_button("識別する", use_container_width=True)
    if submitted:
        if not img_data:
            st.error("画像をアップロードまたは撮影してください。")
            logging.warning("識別失敗: 入力画像なし")
        else:
            try:
                # ① バイト列を一時ファイルに保存
                img_bytes = img_data.getvalue()
                ts = datetime.now().strftime("%Y%m%d%H%M%S")
                tmp_name = f"input_{ts}.png"
                tmp_path = os.path.join("images", tmp_name)
                with open(tmp_path, "wb") as f:
                    f.write(img_bytes)

                # ② ファイル版の特徴量抽出を呼び出し
                inp_feats = image_utils.extract_features(tmp_path)
                if not inp_feats:
                    raise RuntimeError("特徴量抽出失敗")

                # ③ マッチング
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
                # ④ 一時ファイルを必ず削除
                try:
                    if 'tmp_path' in locals() and os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except OSError:
                    pass
