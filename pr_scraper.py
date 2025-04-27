import spacy
import json
nlp = spacy.load('ja_ginza')
# ブランド辞書を外部JSONから読み込み
with open('brands.json', encoding='utf-8') as f:
    BRAND_DICT = json.load(f)

def extract_sponsor_and_product(description, title, caption):
    import re
    sponsor = ""
    product = ""
    # 1. 提供会社（従来通り）
    sponsor_match = re.search(r'提供[:：]?([\w\u3000-\u9FFF\uFF01-\uFF5E\s]+)', description)
    if sponsor_match:
        sponsor = sponsor_match.group(1).strip()
    # 2. 説明欄の箇条書きから商品候補を抽出
    lines = re.split(r'[\n◆■\-・●]', description)
    product_candidates = []
    for line in lines:
        if any(b in line for b in BRAND_DICT):
            product_candidates.append(line.strip())
    # 3. spaCyで固有名詞抽出
    doc = nlp(description + " " + title + " " + (caption or ""))
    for ent in doc.ents:
        if ent.label_ in ["ORG", "PRODUCT"] and any(b in ent.text for b in BRAND_DICT):
            product_candidates.append(ent.text)
    # 4. 最も多く出現したものを商品名とする（なければ空欄）
    if product_candidates:
        product = max(set(product_candidates), key=product_candidates.count)
    return sponsor, product

rows = []
for pr in pr_videos:
    caption = get_caption(pr["video_id"])
    sponsor, product = extract_sponsor_and_product(pr["description"], pr["title"], caption)
    video_url = f"https://www.youtube.com/watch?v={pr['video_id']}"
    # 信頼度スコアリング: タイトル・説明・字幕に商品名が何回出現するか
    confidence_score = 0
    if product:
        for field in [pr["title"], pr["description"], caption or ""]:
            if product in field:
                confidence_score += 1
    rows.append({
        "video_id": pr["video_id"],
        "published_at": pr["published_at"],
        "title": pr["title"],
        "description": pr["description"],
        "caption": caption,
        "is_pr": True,
        "pr_keyword_hit": pr["pr_keyword_hit"],
        "sponsor": sponsor,
        "product": product,
        "video_url": video_url,
        "confidence_score": confidence_score
    })
df = pd.DataFrame(rows)
out_path = output_dir / "pr_videos.csv"
df.to_csv(out_path, index=False, encoding="utf-8")