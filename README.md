# YouTube PR動画抽出ツール

指定チャンネルのPR/案件動画のみを抽出し、メタ情報＋全文テキスト（説明欄＋字幕）をCSV/JSONで出力するPython CLIツールです。

## 特徴
- PR/案件動画のみを正規表現で自動判定
- 動画タイトル・説明欄・タグ・字幕を取得
- pandasでCSV出力
- ロギング・エラー処理・APIクオータ考慮
- テスト用モックデータ・pytest対応

## 必要要件
- Python 3.11 以上
- Google YouTube Data API v3 キー

## セットアップ
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 使い方
```bash
python pr_scraper.py \
  --channel UCxxxxxxxx \
  --api-key $YT_API_KEY \
  --max-videos 1000
```

- `--output`  出力CSVパス（既定: ./output）
- `--debug`   ログレベル=DEBUG

## ディレクトリ構成
```
repo/
 ├ pr_scraper.py
 ├ requirements.txt
 ├ tests/
 │   └ fixtures/
 │       └ sample_playlist.json
 ├ README.md
 └ output/     ← .gitignore
```

## テスト
```bash
pytest -q
```
