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
    page_title="指紋識別アプリ",
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

# --- サイドバー ---
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

# --- 指紋登録ページ ---
if page == "指紋登録":
    st.markdown("## 📝 指紋登録")
    col1, col2 = st.columns([1, 2], gap="large")
    with col1:
        name = st.text_input("名前を入力", placeholder="例：田中太郎")
        uploaded_file = st.file_uploader("指紋画像をアップロード", type=["png","jpg","jpeg"])
        if st.button("登録する"):
            if not name or not uploaded_file:
                st.error("名前と画像を両方入力してください。")
            else:
                try:
                    # 画像保存
                    ts = datetime.now().strftime("%Y%m%d%H%M%S")
                    filename = f"{name}_{ts}.png"
                    save_path = os.path.join("images", filename)
                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                except Exception as e:
                    st.error(f"画像の保存に失敗しました：{e}")
                else:
                    try:
                        # 特徴量抽出
                        features = image_utils.extract_features(save_path)
                        if not features:
                            st.error("特徴量が抽出できませんでした。別の画像を試してください。")
                            raise RuntimeError("特徴量抽出失敗")
                    except Exception as e:
                        st.error(f"特徴量抽出中にエラーが発生しました：{e}")
                        if os.path.exists(save_path):
                            os.remove(save_path)
                    else:
                        try:
                            # JSON登録
                            user_db.add_user(name, save_path, features)
                        except Exception as e:
                            st.error(f"データベースへの保存に失敗しました：{e}")
                            logging.error(f"登録失敗: {name} / 原因={e}")
                        else:
                            st.success(f"{name} さんの指紋を登録しました。")
                            logging.info(f"登録成功: {name} / {save_path} / 特徴量数={len(features)}")

    with col2:
        st.markdown("### アップロード例")
        # 例示用画像があればパスを指定
        # st.image("assets/fingerprint_example.png", use_column_width=True)

# --- 登録ユーザー一覧ページ ---
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
                    # 削除ボタン
                    if st.button(f"🗑️ {user['name']} を削除"):
                        user_db.delete_user(user["name"])
                        st.success(f"{user['name']} さんを削除しました")
                        st.experimental_rerun()

# --- 指紋識別ページ ---
elif page == "指紋識別":
    st.markdown("## 🔎 指紋識別")
    col1, col2 = st.columns([1, 2], gap="large")
    with col1:
        uploaded_file = st.file_uploader("識別したい指紋画像をアップロード", type=["png","jpg","jpeg"])
        if st.button("識別する"):
            if not uploaded_file:
                st.error("画像をアップロードしてください。")
            else:
                try:
                    # 一時保存
                    ts = datetime.now().strftime("%Y%m%d%H%M%S")
                    tmp_name = f"input_{ts}.png"
                    tmp_path = os.path.join("images", tmp_name)
                    with open(tmp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                except Exception as e:
                    st.error(f"画像の一時保存に失敗しました：{e}")
                else:
                    try:
                        # 特徴量抽出
                        inp_feats = image_utils.extract_features(tmp_path)
                        if not inp_feats:
                            st.error("特徴量が抽出できませんでした。別の画像を試してください。")
                            raise RuntimeError("特徴量抽出失敗")
                    except Exception as e:
                        st.error(f"特徴量抽出中にエラーが発生しました：{e}")
                    else:
                        try:
                            # マッチング
                            users = user_db.load_users()
                            name, score = identifier.match_fingerprint(inp_feats, users, threshold)
                        except Exception as e:
                            st.error(f"識別処理に失敗しました：{e}")
                            logging.error(f"識別エラー: 入力={tmp_name} / Error={e}")
                        else:
                            if name:
                                st.success(f"持ち主：{name} さん  (マッチ数：{score})")
                                logging.info(f"識別成功: 入力={tmp_name} / 持ち主={name} / スコア={score}")
                            else:
                                st.warning(f"未登録の指紋です  (最高マッチ数：{score})")
                                logging.warning(f"識別未登録: 入力={tmp_name} / 最高スコア={score}")
                finally:
                    # 一時ファイル削除
                    if 'tmp_path' in locals() and os.path.exists(tmp_path):
                        os.remove(tmp_path)
