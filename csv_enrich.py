import pandas as pd
import re
import json
from pathlib import Path

INPUT_CSV = "パパラピーズPR案件.csv"
OUTPUT_CSV = "output/pr_videos_enriched.csv"

BRAND_DICT_PATH = Path("brands.json")
if BRAND_DICT_PATH.exists():
    BRAND_DICT = set(json.loads(BRAND_DICT_PATH.read_text(encoding="utf-8")))
else:
    BRAND_DICT = set()

def extract_products(description: str) -> str:
    if not isinstance(description, str):
        return ""
    products = []
    for line in description.splitlines():
        line = line.strip()
        if not line:
            continue
        # スキップ条件
        if line.startswith("#"):
            continue
        if any(kw in line for kw in ["提供", "クーポン", "利用期限", "割引率", "検索して商品チェック", "http"]):
            continue
        # 末尾が数字だけのID行も除外
        if re.fullmatch(r"[0-9]{6,}", line):
            continue
        # 明らかなURLは除外
        if line.startswith("https://") or line.startswith("http://"):
            continue
        # 候補として追加
        products.append(line)
    # 重複除外
    products = list(dict.fromkeys(products))
    return "; ".join(products)

def extract_sponsor_from_desc(description: str) -> str:
    if not isinstance(description, str):
        return ""
    m = re.search(r"提供[:：]?([\w\u3000-\u9FFF\uFF01-\uFF5E\s]+)", description)
    return m.group(1).strip() if m else ""

def main():
    df = pd.read_csv(INPUT_CSV)
    for idx, row in df.iterrows():
        # 商品名補完
        product = str(row.get("商品", ""))
        if not product or pd.isna(product):
            product_candidate = extract_products(row.get("description", ""))
            df.at[idx, "商品"] = product_candidate
        # 提供会社補完
        sponsor = str(row.get("提供会社", ""))
        if (not sponsor or pd.isna(sponsor)) and isinstance(row.get("description"), str):
            sponsor_candidate = extract_sponsor_from_desc(row["description"])
            df.at[idx, "提供会社"] = sponsor_candidate
        # confidence_score 追加（簡易）：商品名がタイトルか説明に含まれる回数
        prod_val = df.at[idx, "商品"]
        prod = "" if pd.isna(prod_val) else str(prod_val)
        confidence = 0
        if prod:
            for field in [row.get("title", ""), row.get("description", "")]:
                field_str = "" if pd.isna(field) else str(field)
                if prod and prod in field_str:
                    confidence += 1
        df.at[idx, "confidence_score"] = confidence
    output_path = Path(OUTPUT_CSV)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"Enriched CSV written to {output_path}")

if __name__ == "__main__":
    main()
