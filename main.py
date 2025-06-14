import streamlit as st
import os
from datetime import datetime

import image_utils
import user_db
import identifier
import logging

if not os.path.exists("logs"):
    os.makedirs("logs")

# ログの基本設定
logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# ページ設定（ワイドレイアウト＋タイトル）
st.set_page_config(
    page_title="濱上研の女",
    layout="wide",
    initial_sidebar_state="expanded",
)

#  カスタムCSS挿入 
st.markdown(
    """
    <style>
    /* 右上メニュー・フッターを非表示 */
    footer { visibility: hidden; }

    /* 背景色 */
    .css-18ni7ap { background-color: #f7f7f7; }

    /* 全体フォント */
    html, body, [class*="css"]  {
        font-family: "Yu Gothic UI", sans-serif;
    }

    /* ボタンのスタイル */
    div.stButton > button {
        background-color: #4C6EF5;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: .5rem;
        border: none;
    }
    div.stButton > button:hover {
        background-color: #364FC7;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# サイドバー 
with st.sidebar:
    st.title("🔧 メニュー")
    page = st.radio(
        "機能を選択",
        options=["指紋登録", "登録ユーザー一覧", "指紋識別"]
    )

    # 閾値スライダー
    threshold = st.slider(
        "マッチング閾値", min_value=0, max_value=100, value=15, step=1
    )

    st.markdown("---")
    if st.button("🔄 全データリセット"):
        user_db.clear_users()
        for f in os.listdir("images"):
            os.remove(os.path.join("images", f))
        st.success("✅ 全データをリセットしました")

#  指紋登録ページ 
if page == "指紋登録":
    st.markdown("## 📝 指紋登録")

    # フォームで一列にまとめる
    with st.form("register_form", clear_on_submit=True):
        # 名前入力
        name = st.text_input("名前を入力", placeholder="例：田中太郎")
        # カメラ or ファイルアップロード
        camera_image = st.camera_input("📷 カメラで指紋を撮影")
        uploaded_file = st.file_uploader("📁 画像をアップロード", type=["png","jpg","jpeg"])
        img_data = camera_image or uploaded_file
        # 幅いっぱいの登録ボタン
        submitted = st.form_submit_button("登録する", use_container_width=True)

    # フォーム送信後の処理
    if submitted:
        if not name or not img_data:
            st.error("名前と画像を両方入力してください。")
            logging.warning(f"登録失敗: 入力不足 name={name} img_data={bool(img_data)}")
        else:
            try:
                # 画像保存
                img_bytes = img_data.getvalue()
                ts = datetime.now().strftime("%Y%m%d%H%M%S")
                filename = f"{name}_{ts}.png"
                save_path = os.path.join("images", filename)
                with open(save_path, "wb") as f:
                    f.write(img_bytes)
            except Exception as e:
                st.error(f"画像の保存に失敗しました：{e}")
                logging.error(f"画像保存失敗: name={name} error={e}")
            else:
                try:
                    # 特徴量抽出
                    features = image_utils.extract_features(save_path)
                    if not features:
                        st.error("特徴量が抽出できませんでした。別の画像を試してください。")
                        logging.warning(f"特徴量抽出失敗: {save_path}")
                        raise RuntimeError("特徴量抽出失敗")
                except Exception as e:
                    st.error(f"特徴量抽出中にエラーが発生しました：{e}")
                    logging.error(f"特徴量抽出エラー: path={save_path} error={e}")
                    os.remove(save_path)
                else:
                    try:
                        # JSON登録
                        user_db.add_user(name, save_path, features)
                    except Exception as e:
                        st.error(f"データベースへの保存に失敗しました：{e}")
                        logging.error(f"JSON登録失敗: name={name} path={save_path} error={e}")
                    else:
                        st.success(f"{name} さんの指紋を登録しました。")
                        logging.info(f"登録成功: name={name} path={save_path} features={len(features)}")


#  登録ユーザー一覧ページ 
elif page == "登録ユーザー一覧":
    st.markdown("## 📋 登録ユーザー一覧")
    users = user_db.load_users()
    if not users:
        st.info("まだ登録された指紋データがありません。")
    else:
        for i in range(0, len(users), 2):
            cols = st.columns(2, gap="medium")
            for idx, user in enumerate(users[i : i+2]):
                with cols[idx]:
                    st.markdown(f"#### {user['name']}")
                    st.image(user["image_path"], use_column_width=True)
                    st.caption(f"特徴量数：{len(user['features'])}")
                    if st.button(f"🗑️ {user['name']} を削除"):
                        user_db.delete_user(user["name"])
                        st.success(f"{user['name']} さんを削除しました")
                        st.experimental_rerun()


#  指紋識別ページ 
elif page == "指紋識別":
    st.markdown("## 🔎 指紋識別")

    # フォームで一列にまとめる
    with st.form("identify_form", clear_on_submit=True):
        # カメラ or ファイルアップロード
        camera_image = st.camera_input("📷 カメラで撮影")
        uploaded_file = st.file_uploader("📁 画像をアップロード", type=["png","jpg","jpeg"])
        img_data = camera_image or uploaded_file
        # 幅いっぱいの識別ボタン
        submitted = st.form_submit_button("識別する", use_container_width=True)

    # フォーム送信後の処理
    if submitted:
        if not img_data:
            st.error("画像をアップロードまたは撮影してください。")
            logging.warning("識別失敗: 入力画像なし")
        else:
            try:
                # 一時保存
                img_bytes = img_data.getvalue()
                ts = datetime.now().strftime("%Y%m%d%H%M%S")
                tmp_name = f"input_{ts}.png"
                tmp_path = os.path.join("images", tmp_name)
                with open(tmp_path, "wb") as f:
                    f.write(img_bytes)
            except Exception as e:
                st.error(f"画像の一時保存に失敗しました：{e}")
                logging.error(f"一時保存失敗: error={e}")
            else:
                try:
                    # 特徴量抽出
                    inp_feats = image_utils.extract_features(tmp_path)
                    if not inp_feats:
                        st.error("特徴量が抽出できませんでした。別の画像を試してください。")
                        logging.warning(f"識別特徴量抽出失敗: {tmp_path}")
                        raise RuntimeError("特徴量抽出失敗")
                except Exception as e:
                    st.error(f"特徴量抽出中にエラーが発生しました：{e}")
                    logging.error(f"識別特徴量抽出エラー: error={e}")
                else:
                    try:
                        # マッチング
                        users = user_db.load_users()
                        name, score = identifier.match_fingerprint(inp_feats, users, threshold)
                    except Exception as e:
                        st.error(f"識別処理に失敗しました：{e}")
                        logging.error(f"識別エラー: input={tmp_name} error={e}")
                    else:
                        if name:
                            st.success(f"持ち主：{name} さん  (マッチ数：{score})")
                            logging.info(f"識別成功: input={tmp_name} owner={name} score={score}")
                        else:
                            st.warning(f"未登録の指紋です  (最高マッチ数：{score})")
                            logging.warning(f"識別未登録: input={tmp_name} max_score={score}")
            # finally 相当：一時ファイルを削除
            try:
                if 'tmp_path' in locals() and os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except:
                pass
