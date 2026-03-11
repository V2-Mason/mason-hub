"""产品匹配推荐：reference_analysis.json + DB产品数据 + catalog补充 → Top 3 推荐 + product_override.json

拆解竞品视频后，自动匹配产品库中最适合套用的产品。
数据源：阿里云 kbeauty.db（source of truth）+ catalog.json（内容补充字段）。
EMP_0008（内容运营总监）审核推荐 → Mason 确认 → 管线继续。

用法（独立运行）：
  python product_match.py <reference_analysis.json> [--brand surenxuan] [--top 3] [--skip-gemini]

用法（管线内调用）：
  from product_match import recommend
  recommendations, override = recommend(analysis_path, brand='surenxuan')
"""
import argparse
import json
import os
import subprocess
import sys

BRANDS_DIR = os.path.expanduser('~/mason-hub/shared/brands')
CRED_DIR = os.path.expanduser('~/mason-hub/.credentials')

# SSH 隧道配置（GCP → 阿里云）
SSH_HOST = 'localhost'
SSH_PORT = 2222
SSH_USER = 'root'
DB_PATH = '/opt/surenxuan/data/kbeauty.db'


# ═══════════════════════════════════════════════════════════════════
# 数据加载（DB 为 source of truth，catalog.json 补充内容字段）
# ═══════════════════════════════════════════════════════════════════

def _price_to_signal(price):
    """将实际零售价转为价格区间描述。"""
    if not price or price <= 0:
        return ''
    if price < 80:
        return '不到一百'
    if price < 120:
        return '百元价位'
    if price < 180:
        return '百元出头'
    if price < 250:
        return '不到两百五'
    return '两百以上'


def load_products_from_db():
    """通过 SSH 隧道查询阿里云 kbeauty.db，获取在库产品。

    Returns:
        list of product dicts from DB, or empty list if SSH fails.
    """
    query_script = (
        "import sqlite3, json\n"
        f"db = sqlite3.connect('{DB_PATH}')\n"
        "db.row_factory = sqlite3.Row\n"
        "cur = db.execute('''\n"
        "  SELECT p.id, p.name_cn, p.brand_cn, p.category_l1, p.category_l2,\n"
        "         p.actual_retail_price, p.expiry_date, p.filter_status,\n"
        "         p.key_selling_points, p.usage_instructions,\n"
        "         COALESCE(SUM(im.quantity), 0) as stock\n"
        "  FROM products p\n"
        "  LEFT JOIN inventory_movements im ON im.product_id = p.id\n"
        "  WHERE p.filter_status != 'excluded'\n"
        "  GROUP BY p.id\n"
        "  HAVING stock > 0\n"
        "''')\n"
        "rows = [dict(r) for r in cur.fetchall()]\n"
        "print(json.dumps(rows, ensure_ascii=False))\n"
    )
    try:
        result = subprocess.run(
            ['ssh', '-p', str(SSH_PORT), '-o', 'ConnectTimeout=5',
             '-o', 'StrictHostKeyChecking=no',
             f'{SSH_USER}@{SSH_HOST}', 'python3'],
            input=query_script,
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            print(f"WARNING: DB 查询失败 (exit {result.returncode}): {result.stderr[:200]}",
                  file=sys.stderr)
            return []
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
        print(f"WARNING: SSH/DB 连接失败: {e}", file=sys.stderr)
        return []


def load_content_supplements(brand='surenxuan'):
    """加载 catalog.json 的内容补充数据，以 db_name 为键。

    Returns:
        dict: {db_name: supplement_dict}
    """
    path = os.path.join(BRANDS_DIR, brand, 'catalog.json')
    if not os.path.exists(path):
        print(f"WARNING: 内容补充文件不存在: {path}", file=sys.stderr)
        return {}

    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    supplements = {}
    for entry in data.get('content_supplements', []):
        db_name = entry.get('db_name', '')
        if db_name:
            supplements[db_name] = entry
    return supplements


def merge_products(db_products, supplements):
    """合并 DB 产品数据与 catalog 内容补充。

    DB 提供：名称、品牌、品类、价格、库存、保质期
    catalog 补充：category_aliases、target_concerns、skin_types、
                  core_selling_point、demo_action、priority

    Returns:
        list of unified product dicts.
    """
    merged = []
    for dbp in db_products:
        name_cn = dbp.get('name_cn', '')
        sup = supplements.get(name_cn, {})

        product = {
            'product_id': f"db-{dbp['id']}",
            'product_name': f"{dbp.get('brand_cn', '')} {name_cn}".strip(),
            'brand': dbp.get('brand_cn', ''),
            'category': dbp.get('category_l2', '') or dbp.get('category_l1', ''),
            'category_aliases': sup.get('category_aliases', []),
            'target_concerns': sup.get('target_concerns', []),
            'skin_types': sup.get('skin_types', []),
            'core_selling_point': sup.get('core_selling_point',
                                          dbp.get('key_selling_points', '') or ''),
            'demo_action': sup.get('demo_action',
                                   dbp.get('usage_instructions', '') or ''),
            'actual_retail_price': dbp.get('actual_retail_price', 0),
            'price_signal': _price_to_signal(dbp.get('actual_retail_price', 0)),
            'in_stock': True,
            'stock': dbp.get('stock', 0),
            'expiry_date': dbp.get('expiry_date', ''),
            'priority': sup.get('priority', 5),
            'has_content_supplement': bool(sup),
        }
        merged.append(product)
    return merged


def load_catalog(brand='surenxuan'):
    """加载品牌产品数据（DB + 内容补充合并）。

    优先从阿里云 DB 获取实时数据，合并 catalog.json 内容补充。
    SSH 不通时 fallback 到纯 catalog.json（仅含有内容补充的产品，无价格/库存）。

    Returns:
        list of product dicts.
    """
    supplements = load_content_supplements(brand)

    db_products = load_products_from_db()
    if db_products:
        merged = merge_products(db_products, supplements)
        print(f"  DB 产品: {len(db_products)} 个在库, 内容补充: {len(supplements)} 个")
        return merged

    # Fallback：SSH 不通，用 catalog supplements 构建有限产品列表
    print("WARNING: DB 不可用，使用 catalog.json fallback（无实时库存/价格）", file=sys.stderr)
    fallback = []
    for db_name, sup in supplements.items():
        fallback.append({
            'product_id': f"catalog-{db_name}",
            'product_name': db_name,
            'brand': '',
            'category': sup.get('category_aliases', [''])[0] if sup.get('category_aliases') else '',
            'category_aliases': sup.get('category_aliases', []),
            'target_concerns': sup.get('target_concerns', []),
            'skin_types': sup.get('skin_types', []),
            'core_selling_point': sup.get('core_selling_point', ''),
            'demo_action': sup.get('demo_action', ''),
            'actual_retail_price': 0,
            'price_signal': '',
            'in_stock': True,
            'stock': 0,
            'expiry_date': '',
            'priority': sup.get('priority', 5),
            'has_content_supplement': True,
        })
    return fallback


# ═══════════════════════════════════════════════════════════════════
# 规则打分
# ═══════════════════════════════════════════════════════════════════

def _normalize(text):
    """统一文本格式（小写+去空格）。"""
    if not text:
        return ''
    return text.lower().strip()


def _category_match(product, analysis_entry):
    """检查产品品类是否匹配拆解结果的 product_type。"""
    analysis_type = _normalize(analysis_entry.get('product_type', ''))
    if not analysis_type:
        return False

    product_cat = _normalize(product.get('category', ''))
    aliases = [_normalize(a) for a in product.get('category_aliases', [])]
    all_categories = [product_cat] + aliases

    for cat in all_categories:
        if cat and (cat in analysis_type or analysis_type in cat):
            return True
    return False


def _concern_overlap(product, analysis_entry):
    """计算肤质/功效关注点重叠数。"""
    product_concerns = [_normalize(c) for c in product.get('target_concerns', [])]
    analysis_concern = _normalize(analysis_entry.get('target_skin_concern', ''))
    analysis_function = _normalize(analysis_entry.get('core_function', ''))
    combined = analysis_concern + ' ' + analysis_function

    count = 0
    for pc in product_concerns:
        if pc and pc in combined:
            count += 1
    return count


def _price_match(product, analysis_entry):
    """价格区间对比（支持文本和数值）。"""
    p_price = _normalize(product.get('price_signal', ''))
    a_price = _normalize(analysis_entry.get('price_signal', ''))
    if not a_price or '未提及' in a_price:
        return False

    # 文本匹配
    if p_price:
        bands = ['百元', '不到两百', '两百', '不到一百', '百元出头', '百元价位']
        for band in bands:
            if band in p_price and band in a_price:
                return True

    return False


def score_products(analysis_products, catalog, top_n=5):
    """规则打分：品类匹配 +10 / 肤质重叠 +3 / 价格接近 +2 / 优先级 +4~0。

    Args:
        analysis_products: reference_analysis.json 中的 product_catalog 数组。
        catalog: catalog.json 中的 products 数组。
        top_n: 返回候选数量。
    Returns:
        list of (product, score, match_details) tuples，按分数降序。
    """
    scores = []

    for product in catalog:
        if not product.get('in_stock', True):
            continue

        total_score = 0
        match_details = []

        for ap in analysis_products:
            if _category_match(product, ap):
                total_score += 10
                match_details.append(f"品类匹配: {ap.get('product_type', '?')}")

            overlap = _concern_overlap(product, ap)
            if overlap > 0:
                total_score += 3 * overlap
                match_details.append(f"功效关联: {overlap}项")

            if _price_match(product, ap):
                total_score += 2
                match_details.append("价格区间接近")

        # 库存优先级加分（priority 1 → +4, priority 5 → +0）
        priority = product.get('priority', 5)
        total_score += max(0, 5 - priority)

        if total_score > 0:
            scores.append((product, total_score, match_details))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_n]


# ═══════════════════════════════════════════════════════════════════
# Gemini 排序 + 理由
# ═══════════════════════════════════════════════════════════════════

MATCH_REASONING_PROMPT = """你是一位护肤品内容运营专家。

参照视频中的产品:
{analysis_products_json}

候选替换产品（来自素仁轩产品库）:
{candidates_json}

请从候选产品中选出最佳的 {top_n} 个产品，并为每个产品写一句话理由。

判断标准:
1. 品类匹配度（同品类优先于跨品类）
2. 目标肤质/功效的关联性
3. 演示方式的可替换性（跨品类时，新产品的使用方式是否能自然融入原视频结构）
4. 价格带是否接近

输出 JSON 数组:
[
  {{
    "product_id": "候选产品 product_id",
    "rank": 1,
    "reasoning": "一句话理由（中文，30字以内）",
    "match_type": "same_category 或 cross_category"
  }}
]

只输出 JSON，不要其他文字。"""


def gemini_rank_and_reason(analysis_products, candidates, top_n=3,
                           model='gemini-2.5-flash'):
    """Gemini Flash 排序 + 一句话理由。

    Args:
        analysis_products: 原视频的 product_catalog 条目。
        candidates: score_products 输出的 (product, score, details) 列表。
        top_n: 最终推荐数量。
        model: Gemini 模型。
    Returns:
        list of dicts: product + rank + reasoning + match_type。
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gemini_analyze import _parse_gemini_json

    api_key_path = os.path.join(CRED_DIR, 'gemini-api-key.txt')
    if not os.path.exists(api_key_path):
        print("WARNING: Gemini API key not found, using rule-based ranking", file=sys.stderr)
        return _fallback_ranking(candidates, top_n)

    from google import genai

    api_key = open(api_key_path).read().strip()
    client = genai.Client(api_key=api_key)

    # 精简输入（只取匹配需要的字段）
    analysis_slim = [
        {k: p.get(k, '') for k in
         ('product_type', 'core_function', 'target_skin_concern', 'price_signal', 'demo_method')}
        for p in analysis_products
    ]
    candidates_slim = [
        {k: c[0].get(k, '') for k in
         ('product_id', 'product_name', 'brand', 'category', 'target_concerns',
          'core_selling_point', 'demo_action', 'price_signal',
          'actual_retail_price')}
        for c in candidates
    ]

    prompt = MATCH_REASONING_PROMPT.format(
        analysis_products_json=json.dumps(analysis_slim, indent=2, ensure_ascii=False),
        candidates_json=json.dumps(candidates_slim, indent=2, ensure_ascii=False),
        top_n=top_n,
    )

    response = client.models.generate_content(model=model, contents=[prompt])
    rankings = _parse_gemini_json(response.text)

    if not isinstance(rankings, list):
        print("WARNING: Gemini returned non-list, falling back to rule-based", file=sys.stderr)
        return _fallback_ranking(candidates, top_n)

    # 将 Gemini 排序结果与完整产品信息合并
    candidate_map = {c[0]['product_id']: c[0] for c in candidates}
    results = []
    for r in rankings[:top_n]:
        pid = r.get('product_id', '')
        product = candidate_map.get(pid)
        if not product:
            continue
        results.append({
            **product,
            'rank': r.get('rank', len(results) + 1),
            'reasoning': r.get('reasoning', ''),
            'match_type': r.get('match_type', 'unknown'),
        })

    # 如果 Gemini 返回不够 top_n 个，用规则补齐
    if len(results) < top_n:
        existing_ids = {r['product_id'] for r in results}
        for c in candidates:
            if c[0]['product_id'] not in existing_ids and len(results) < top_n:
                results.append({
                    **c[0],
                    'rank': len(results) + 1,
                    'reasoning': '规则打分补充',
                    'match_type': 'rule_based',
                })

    return results


def _fallback_ranking(candidates, top_n=3):
    """纯规则打分 fallback（无 Gemini 时使用）。"""
    results = []
    for i, (product, score, details) in enumerate(candidates[:top_n]):
        results.append({
            **product,
            'rank': i + 1,
            'reasoning': '; '.join(details[:2]) if details else '规则打分',
            'match_type': 'rule_based',
        })
    return results


# ═══════════════════════════════════════════════════════════════════
# 格式转换
# ═══════════════════════════════════════════════════════════════════

def format_product_override(recommendations):
    """转为 shooting_script.py 需要的 product_override 格式。

    Args:
        recommendations: gemini_rank_and_reason 的输出。
    Returns:
        list of dicts（shooting_script.py 格式）。
    """
    override = []
    for rec in recommendations:
        override.append({
            'product_name': rec.get('product_name', ''),
            'replacement_category': rec.get('category', ''),
            'target_concern': ', '.join(rec.get('target_concerns', [])),
            'demo_action': rec.get('demo_action', ''),
            'core_selling_point': rec.get('core_selling_point', ''),
            'price_signal': rec.get('price_signal', ''),
            'actual_retail_price': rec.get('actual_retail_price', 0),
        })
    return override


# ═══════════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════════

def recommend(analysis_path, brand='surenxuan', top_n=3,
              skip_gemini=False, model='gemini-2.5-flash'):
    """主入口：分析 JSON → 推荐列表 + product_override。

    Args:
        analysis_path: reference_analysis.json 路径。
        brand: 品牌名。
        top_n: 推荐数量。
        skip_gemini: 跳过 Gemini，纯规则打分。
        model: Gemini 模型。
    Returns:
        (recommendations, product_override) tuple。
    """
    with open(analysis_path, encoding='utf-8') as f:
        analysis = json.load(f)

    analysis_products = analysis.get('product_catalog', [])
    if not analysis_products:
        print("WARNING: 参照视频中无产品数据，跳过匹配", file=sys.stderr)
        return [], []

    catalog = load_catalog(brand)
    if not catalog:
        print("WARNING: 产品目录为空", file=sys.stderr)
        return [], []

    print(f"  产品库: {len(catalog)} 个产品")
    print(f"  参照视频: {len(analysis_products)} 个产品")

    # Step 1: 规则打分
    candidates = score_products(analysis_products, catalog, top_n=min(top_n + 2, len(catalog)))
    print(f"  规则打分候选: {len(candidates)} 个")

    if not candidates:
        print("WARNING: 无匹配候选产品", file=sys.stderr)
        return [], []

    # Step 2: Gemini 排序+理由（或 fallback）
    if skip_gemini:
        recommendations = _fallback_ranking(candidates, top_n)
    else:
        recommendations = gemini_rank_and_reason(
            analysis_products, candidates, top_n=top_n, model=model
        )

    # Step 3: 格式化
    product_override = format_product_override(recommendations)

    print(f"\n  推荐结果:")
    for rec in recommendations:
        tag = '同品类' if rec.get('match_type') == 'same_category' else '跨品类'
        print(f"    {rec['rank']}. {rec['product_name']} ({rec['brand']}) [{tag}]")
        print(f"       {rec.get('reasoning', '')}")

    return recommendations, product_override


def main():
    parser = argparse.ArgumentParser(description='产品匹配推荐')
    parser.add_argument('analysis', help='reference_analysis.json 路径')
    parser.add_argument('--brand', default='surenxuan', help='品牌名')
    parser.add_argument('--top', type=int, default=3, help='推荐数量')
    parser.add_argument('--skip-gemini', action='store_true', help='跳过 Gemini，纯规则打分')
    parser.add_argument('--model', default='gemini-2.5-flash', help='Gemini 模型')
    parser.add_argument('--output-dir', help='输出目录（默认与输入同目录）')
    args = parser.parse_args()

    if not os.path.exists(args.analysis):
        print(f"ERROR: 文件不存在: {args.analysis}", file=sys.stderr)
        return 1

    recommendations, product_override = recommend(
        args.analysis, brand=args.brand, top_n=args.top,
        skip_gemini=args.skip_gemini, model=args.model,
    )

    if not recommendations:
        print("无匹配结果。")
        return 0

    output_dir = args.output_dir or os.path.dirname(args.analysis) or '.'

    rec_path = os.path.join(output_dir, 'product_recommendations.json')
    with open(rec_path, 'w', encoding='utf-8') as f:
        json.dump(recommendations, f, indent=2, ensure_ascii=False)

    override_path = os.path.join(output_dir, 'product_override.json')
    with open(override_path, 'w', encoding='utf-8') as f:
        json.dump(product_override, f, indent=2, ensure_ascii=False)

    print(f"\n推荐已保存: {rec_path}")
    print(f"产品替换文件: {override_path}")

    return 0


if __name__ == '__main__':
    exit(main())
