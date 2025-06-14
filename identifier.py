import cv2
import numpy as np

def match_fingerprint(input_features: list,
                      users: list,
                      threshold: int = 150,
                      ratio: float = 0.75) -> tuple[str | None, int]:
    """
    入力特徴量と登録ユーザーの特徴量を比較し、
    Lowe の比率テストで良いマッチのみをカウントします。
    最もマッチ数が多いユーザー名とそのスコアを返し、
    threshold 未満なら (None, score) を返します。
    """
    if not input_features or not users:
        return None, 0

    # 入力特徴量を NumPy 配列に
    inp_desc = np.array(input_features, dtype=np.uint8)

    # Hamming 距離用 BFMatcher (crossCheck は False)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

    best_name = None
    best_score = 0

    for user in users:
        reg_feats = user.get("features", [])
        if not reg_feats:
            continue

        reg_desc = np.array(reg_feats, dtype=np.uint8)

        # k-NN で 2 つ返してもらう
        raw_matches = bf.knnMatch(inp_desc, reg_desc, k=2)

        # Lowe の比率テスト
        good = []
        for m, n in raw_matches:
            if m.distance < ratio * n.distance:
                good.append(m)

        score = len(good)
        if score > best_score:
            best_score = score
            best_name = user["name"]

    # 閾値以上なら合致とみなす
    if best_score >= threshold:
        return best_name, best_score
    else:
        return None, best_score
