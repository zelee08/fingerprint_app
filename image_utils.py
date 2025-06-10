import cv2


def extract_features(image_path: str) -> list:
    """
    指紋画像を読み込み、ORBで特徴量を抽出してリストとして返す。
    存在しないファイルや読み込み失敗時には空リストを返します。
    """
    # グレースケールで読み込み
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    # 画像が読み込めなかった場合は空リストを返す
    if img is None:
        return []
    # 必要ならリサイズ（大きすぎる画像は固定サイズに)
    img = cv2.resize(img, (300, 300))
    # ORBで特徴量抽出
    orb = cv2.ORB_create()
    keypoints, descriptors = orb.detectAndCompute(img, None)
    # 抽出できなかった場合は空リスト
    if descriptors is None:
        return []
    # JSON保存用に Pythonのリストに変換
    return descriptors.tolist()
