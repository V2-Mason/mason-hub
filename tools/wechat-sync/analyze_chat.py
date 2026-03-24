#!/usr/bin/env python3
"""微信聊天分析脚本 — 过滤+增量+图片OCR+结构化输出

使用方法:
    # 首次全量分析（指定解密后的 SQLite 数据库）
    python analyze_chat.py --db /path/to/decrypted_msg.db --contact-db /path/to/contact.db

    # 增量分析（只分析上次之后的新消息）
    python analyze_chat.py --db /path/to/decrypted_msg.db --incremental

    # 分析并上传到素仁轩
    python analyze_chat.py --db /path/to/decrypted_msg.db --upload

    # 只分析图片（进货单 OCR）
    python analyze_chat.py --db /path/to/decrypted_msg.db --images-only

依赖:
    pip install openai  # DeepSeek 兼容 OpenAI SDK
"""
import argparse
import base64
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ── Config ──
SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "config.json"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

CONFIG = load_config()

# ── DeepSeek Client ──
def get_client():
    """Initialize DeepSeek client (OpenAI-compatible)."""
    try:
        from openai import OpenAI
    except ImportError:
        print("ERROR: pip install openai")
        sys.exit(1)

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("ERROR: Set DEEPSEEK_API_KEY environment variable")
        sys.exit(1)

    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


# ── Checkpoint (增量分析) ──
CHECKPOINT_FILE = SCRIPT_DIR / CONFIG["incremental"]["checkpoint_file"]

def load_checkpoint():
    if CHECKPOINT_FILE.exists():
        data = json.loads(CHECKPOINT_FILE.read_text())
        return data.get("last_create_time", 0)
    return 0

def save_checkpoint(ts):
    CHECKPOINT_FILE.write_text(json.dumps({"last_create_time": ts,
                                            "updated_at": datetime.now().isoformat()}))


# ── 过滤器 ──
def build_wxid_whitelist():
    """Build set of watched wxid from config."""
    wxids = set()
    for c in CONFIG.get("watched_contacts", []):
        if c.get("wxid"):
            wxids.add(c["wxid"])
    for g in CONFIG.get("watched_groups", []):
        if g.get("wxid"):
            wxids.add(g["wxid"])
    return wxids

def should_analyze_text(text: str) -> bool:
    """Check if message text contains relevant keywords."""
    if not text:
        return False
    keywords = CONFIG.get("product_keywords", []) + CONFIG.get("business_keywords", [])
    return any(kw in text for kw in keywords)


# ── 数据库查询 ──
def get_watched_messages(db_path: str, contact_db_path: str = None,
                         since_ts: int = 0, images_only: bool = False):
    """Extract messages from watched contacts/groups, optionally filtered."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Get Name2Id mapping (wxid → table hash)
    try:
        name2id = {r["user_name"]: r["table_name"] if "table_name" in r.keys() else r[1]
                   for r in conn.execute("SELECT * FROM Name2Id").fetchall()}
    except Exception:
        # Fallback: scan for Msg_* tables
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'"
        ).fetchall()]
        name2id = {f"unknown_{t}": t for t in tables}

    # Contact name lookup
    contact_names = {}
    if contact_db_path and os.path.exists(contact_db_path):
        cconn = sqlite3.connect(contact_db_path)
        try:
            for r in cconn.execute("SELECT UserName, NickName FROM Contact").fetchall():
                contact_names[r[0]] = r[1]
        except Exception:
            pass
        cconn.close()

    whitelist = build_wxid_whitelist()
    messages = []
    image_items = []

    for wxid, table_name in name2id.items():
        # Filter by whitelist (if whitelist is configured)
        if whitelist and wxid not in whitelist:
            continue

        contact_name = contact_names.get(wxid, wxid)

        try:
            where = f"create_time > {since_ts}" if since_ts > 0 else "1=1"

            if images_only:
                # local_type 3 = image
                rows = conn.execute(
                    f"SELECT * FROM [{table_name}] WHERE {where} AND local_type = 3 "
                    f"ORDER BY create_time ASC"
                ).fetchall()
            else:
                # local_type 1 = text, 3 = image
                rows = conn.execute(
                    f"SELECT * FROM [{table_name}] WHERE {where} AND local_type IN (1, 3) "
                    f"ORDER BY create_time ASC"
                ).fetchall()

            for r in rows:
                r = dict(r)
                ts = r.get("create_time", 0)
                local_type = r.get("local_type", 0)
                is_sender = r.get("is_sender", 0)

                if local_type == 1:
                    # Text message — decode protobuf content
                    text = _decode_text(r.get("message_content") or r.get("compress_content"))
                    if text and should_analyze_text(text):
                        messages.append({
                            "wxid": wxid,
                            "contact": contact_name,
                            "time": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M"),
                            "text": text,
                            "is_sender": is_sender,
                            "type": "text",
                        })

                elif local_type == 3:
                    # Image message — extract image bytes
                    img_data = r.get("message_content") or r.get("compress_content")
                    if img_data and len(img_data) > 500:  # Skip tiny thumbnails
                        image_items.append({
                            "wxid": wxid,
                            "contact": contact_name,
                            "time": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M"),
                            "image_data": img_data,
                            "is_sender": is_sender,
                            "type": "image",
                        })

        except Exception as e:
            # Table might not exist or have different schema
            continue

    conn.close()
    return messages, image_items


def _decode_text(blob):
    """Decode protobuf BLOB to plain text. Simplified — adapt to your actual format."""
    if not blob:
        return None
    if isinstance(blob, str):
        return blob
    # Try direct UTF-8 decode (some messages are plain text in BLOB)
    try:
        text = blob.decode("utf-8", errors="ignore")
        # Strip protobuf framing bytes (common pattern: \n\x??\n followed by text)
        if text and len(text) > 2:
            # Find first readable Chinese/ASCII segment
            import re
            match = re.search(r'[\u4e00-\u9fff\w].{5,}', text)
            if match:
                return match.group(0)
        return text if len(text) > 3 else None
    except Exception:
        return None


# ── DeepSeek 分析 ──
def analyze_text_batch(client, messages: list) -> dict:
    """Send a batch of text messages to DeepSeek for structured extraction."""
    if not messages:
        return {"orders": [], "feedback": [], "demand_signals": [], "daily_summary": "无消息"}

    # Format messages for prompt
    lines = []
    for m in messages:
        direction = "我方" if m["is_sender"] else m["contact"]
        lines.append(f"[{m['time']}] {direction}: {m['text']}")

    prompt = f"""分析以下微信聊天记录，提取三类信息。严格按 JSON 格式输出。

聊天记录：
{'chr(10)'.join(lines)}

请提取：
1. orders: 订单/交易记录 [{{"time":"", "product":"产品名", "quantity":数量, "amount":金额, "buyer":"买家名"}}]
2. feedback: 客户反馈 [{{"time":"", "summary":"一句话摘要", "sentiment":"正面/负面/中性", "product":"涉及产品"}}]
3. demand_signals: 需求信号 [{{"description":"描述", "count":出现次数, "urgency":"高/中/低"}}]
4. daily_summary: 一句话总结今日经营状况

只输出 JSON，不要其他文字。如果某类无数据就返回空数组。"""

    try:
        resp = client.chat.completions.create(
            model=CONFIG["deepseek"]["model"],
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        print(f"  DeepSeek text analysis error: {e}")
        return {"orders": [], "feedback": [], "demand_signals": [], "daily_summary": f"分析失败: {e}"}


def analyze_image(client, image_data: bytes, context: str = "") -> dict:
    """Send an image to DeepSeek Vision for OCR + structured extraction.

    Returns: {"type": "price_list"|"order"|"receipt"|"other", "items": [...], "raw_text": "..."}
    """
    # Base64 encode the image
    b64 = base64.b64encode(image_data).decode("utf-8")

    prompt = f"""这是一张微信聊天中的图片，可能是进货单、报价单、产品清单或收据。
{f"上下文: {context}" if context else ""}

请分析这张图片：
1. 判断图片类型: price_list(报价单/进货单) / order(订单截图) / receipt(收据/转账) / product(产品图) / other(其他)
2. 如果是 price_list 或 order，提取所有产品信息:
   items: [{{"product":"产品名(中文)", "price":单价, "quantity":数量或null, "unit":"件/盒/支", "note":"备注"}}]
3. 如果是 receipt，提取: {{"amount":金额, "payer":"付款方", "receiver":"收款方", "time":"时间"}}
4. raw_text: 图片中所有可识别的文字

只输出 JSON。"""

    try:
        resp = client.chat.completions.create(
            model=CONFIG["deepseek"]["vision_model"],
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ],
            }],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=2000,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        print(f"  DeepSeek vision error: {e}")
        return {"type": "other", "items": [], "raw_text": "", "error": str(e)}


# ── 主流程 ──
def run(args):
    config = load_config()
    client = get_client()

    # Incremental checkpoint
    since_ts = load_checkpoint() if args.incremental else 0
    if since_ts:
        print(f"增量模式: 只分析 {datetime.fromtimestamp(since_ts)} 之后的消息")

    # Extract messages
    print(f"读取数据库: {args.db}")
    messages, images = get_watched_messages(
        args.db,
        contact_db_path=args.contact_db,
        since_ts=since_ts,
        images_only=args.images_only,
    )
    print(f"  文本消息: {len(messages)} 条（已过滤）")
    print(f"  图片消息: {len(images)} 张")

    if not messages and not images:
        print("无新消息需要分析")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    result = {"date": today, "orders": [], "feedback": [], "demand_signals": [], "daily_summary": ""}

    # Analyze text messages in batches
    if messages and not args.images_only:
        batch_size = config["deepseek"]["max_messages_per_batch"]
        for i in range(0, len(messages), batch_size):
            batch = messages[i:i + batch_size]
            print(f"  分析文本 {i+1}-{i+len(batch)}/{len(messages)}...")
            batch_result = analyze_text_batch(client, batch)
            result["orders"].extend(batch_result.get("orders", []))
            result["feedback"].extend(batch_result.get("feedback", []))
            result["demand_signals"].extend(batch_result.get("demand_signals", []))
            if batch_result.get("daily_summary"):
                result["daily_summary"] = batch_result["daily_summary"]

    # Analyze images (price lists, orders, receipts)
    if images:
        price_list_items = []
        for idx, img in enumerate(images):
            print(f"  分析图片 {idx+1}/{len(images)} (from {img['contact']})...")
            # Get surrounding text context
            context = f"来自 {img['contact']}，时间 {img['time']}"
            img_result = analyze_image(client, img["image_data"], context)

            if img_result.get("type") in ("price_list", "order"):
                for item in img_result.get("items", []):
                    price_list_items.append({
                        "source": img["contact"],
                        "time": img["time"],
                        **item,
                    })
                    # Also add as order if it looks like a confirmed order
                    if img_result["type"] == "order":
                        result["orders"].append({
                            "time": img["time"],
                            "product": item.get("product", ""),
                            "quantity": item.get("quantity") or 0,
                            "amount": item.get("price") or 0,
                            "buyer": img["contact"],
                        })

            elif img_result.get("type") == "receipt":
                # Receipt → add as payment signal
                result["feedback"].append({
                    "time": img["time"],
                    "summary": f"收到转账 ¥{img_result.get('amount', '?')} from {img_result.get('payer', img['contact'])}",
                    "sentiment": "正面",
                    "product": "",
                })

        # Save extracted price list items separately
        if price_list_items:
            output_path = SCRIPT_DIR / f"price_list_{today}.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(price_list_items, f, ensure_ascii=False, indent=2)
            print(f"  进货单提取: {len(price_list_items)} 个产品 → {output_path}")

    # Output
    output_path = SCRIPT_DIR / f"daily_report_{today}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n输出: {output_path}")
    print(f"  订单: {len(result['orders'])}, 反馈: {len(result['feedback'])}, 信号: {len(result['demand_signals'])}")

    # Upload to surenxuan
    if args.upload:
        upload_url = config["surenxuan_api"]["url"]
        print(f"\n上传到素仁轩: {upload_url}")
        try:
            import urllib.request
            req = urllib.request.Request(
                upload_url,
                data=json.dumps(result).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                print(f"  上传成功: {resp_data.get('message', '')}")
        except Exception as e:
            print(f"  上传失败: {e}")

    # Save checkpoint
    if messages or images:
        max_ts = 0
        # Get max timestamp from messages
        # (In real implementation, track from DB query)
        save_checkpoint(int(datetime.now().timestamp()))
        print(f"检查点已保存")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="微信聊天分析 → 素仁轩")
    parser.add_argument("--db", required=True, help="解密后的消息数据库路径")
    parser.add_argument("--contact-db", help="联系人数据库路径（用于解析昵称）")
    parser.add_argument("--incremental", action="store_true", help="增量模式（只分析新消息）")
    parser.add_argument("--upload", action="store_true", help="分析完自动上传到素仁轩")
    parser.add_argument("--images-only", action="store_true", help="只分析图片（进货单OCR）")
    args = parser.parse_args()
    run(args)
