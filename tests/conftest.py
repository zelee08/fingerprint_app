# tests/conftest.py

import sys, os

# テスト実行時にプロジェクトルート（このファイルの一つ上）をモジュール検索パスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
