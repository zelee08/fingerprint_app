import numpy as np
from identifier import match_fingerprint

def test_no_users():
    name, score = match_fingerprint([[0,1,2]], [], threshold=1)
    assert name is None and score == 0

def test_perfect_match():
    # 同じ特徴量を登録したら閾値以下でもマッチ
    users = [{"name":"X", "features":[[10,20,30]]}]
    name, score = match_fingerprint([[10,20,30]], users, threshold=1)
    assert name == "X"
    assert score >= 1

def test_below_threshold():
    users = [{"name":"Y", "features":[[0,0,0]]}]
    name, score = match_fingerprint([[1,1,1]], users, threshold=5)
    assert name is None
    assert score < 5
