import cv2
import numpy as np

def match_fingerprint(input_features: list, users: list, threshold: int = 15):
    """
    入力特徴量と登録ユーザーの特徴量を比較し、
    最もマッチ数が多いユーザー名とそのスコアを返す。
    threshold未満なら (None, 0) を返す。
    """
    if not input_features or not users:
        return None, 0

    # 入力特徴量をNumPy配列に
    inp_desc = np.array(input_features, dtype=np.uint8)

    # BFMatcher準備
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

    best_name = None
    best_score = 0

    for user in users:
        # 登録特徴量をNumPy配列に
        reg_desc = np.array(user["features"], dtype=np.uint8)
        if reg_desc.size == 0:
            continue

        # マッチング
        matches = bf.match(inp_desc, reg_desc)
        score = len(matches)

        # 最良を更新
        if score > best_score:
            best_score = score
            best_name = user["name"]

    # スコアが閾値以上なら合致とみなす
    if best_score >= threshold:
        return best_name, best_score
    else:
        return None, best_score
