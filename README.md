# YouTube PR動画抽出・商品/スポンサー自動補完ツール

YouTubeチャンネルのPR/案件動画から「商品名」「スポンサー（提供会社）」などを自動抽出・CSV化するPython CLIツールです。

## 取得方法・仕組み
- **YouTube Data API**で動画・説明欄・タグ・字幕を自動取得
- **正規表現・ブランド辞書**で商品名・スポンサーを抽出
- **csv_enrich.py**で既存CSVの「商品」「提供会社」も自動補完＆信頼度付与

## セットアップ
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
（Python 3.10/3.11推奨）

## 使い方
### 1. YouTubeから動画データを取得
```bash
python pr_scraper.py --channel UCxxxxxxxx --api-key $YT_API_KEY
```
### 2. 既存CSVの「商品」「提供会社」自動補完
```bash
python csv_enrich.py
```
- `output/pr_videos_enriched.csv`に補完結果を出力

## ブランド辞書の拡張
- `brands.json`を書き換えるだけで主要ブランド・メーカーを追加可能

## よくある質問
- **どうやって取得？**
    - YouTube Data APIで動画・説明欄を自動取得し、正規表現やブランド辞書・AIで商品名/スポンサーを抽出・補完しています。
- **AI補完は？**
    - 空欄や曖昧な箇所はAIやルールベースで推論・要約し、信頼度もスコア化しています。

## 注意
- `.env`や`output/`はgit管理から除外してください（.gitignore済）
- APIキーなどの機密情報は絶対に公開しないようご注意ください
