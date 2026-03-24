#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信聊天分析脚本 v2 — 过滤+增量+图片OCR+自动上传
==================================================
基于 Mason 原始 analyze_chat.py + export_chat.py 的解码器

用法:
    # 首次运行：发现模式 — 扫描所有会话，找出业务相关的
    python analyze_chat.py --db ./decrypted --discover

    # 日常运行：增量分析+上传
    python analyze_chat.py --db ./decrypted --incremental --upload

    # 只看图片（进货单 OCR）
    python analyze_chat.py --db ./decrypted --images-only --upload

依赖: pip install requests openpyxl
"""
import argparse
import base64
import json
import os
import re
import sqlite3
import sys
import zlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
BEIJING_TZ = timezone(timedelta(hours=8))

MSG_TYPE = {
    1: "文本", 3: "图片", 34: "语音", 42: "名片",
    43: "视频", 47: "表情", 48: "位置", 49: "链接/文件",
    50: "通话", 10000: "系统消息", 10002: "撤回",
}


# ============================================================
# Config
# ============================================================
def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

CONFIG = load_config()


# ============================================================
# Protobuf 解码 (来自 Mason 的 export_chat.py, 已验证 99.8%)
# ============================================================
def read_varint(data, offset):
    result = 0
    shift = 0
    while offset < len(data):
        b = data[offset]
        offset += 1
        result |= (b & 0x7F) << shift
        if (b & 0x80) == 0:
            return result, offset
        shift += 7
        if shift > 63:
            break
    return result, offset


def is_readable(text):
    if not text or len(text) == 0:
        return False
    ok = sum(1 for c in text if c.isprintable() or c in "\n\r\t")
    return ok / len(text) > 0.5


def extract_protobuf_string(data):
    offset = 0
    results = []
    while offset < len(data):
        try:
            tag, offset = read_varint(data, offset)
            if offset >= len(data):
                break
            field = tag >> 3
            wire = tag & 0x07
            if wire == 0:
                _, offset = read_varint(data, offset)
            elif wire == 1:
                offset += 8
            elif wire == 2:
                length, offset = read_varint(data, offset)
                if length < 0 or offset + length > len(data):
                    break
                value = data[offset: offset + length]
                offset += length
                if field == 1:
                    try:
                        t = value.decode("utf-8")
                        if t and is_readable(t):
                            results.append(t)
                    except:
                        pass
            elif wire == 5:
                offset += 4
            else:
                break
        except:
            break
    return results[0] if results else ""


def decode_blob(blob):
    if not blob or len(blob) == 0:
        return ""
    data = blob if isinstance(blob, bytes) else blob.encode() if isinstance(blob, str) else blob
    if len(data) >= 2 and data[0] == 0x78:
        try:
            data = zlib.decompress(data)
        except:
            pass
    text = extract_protobuf_string(data)
    if text:
        return text
    try:
        t = data.decode("utf-8", errors="ignore").strip("\x00").strip()
        if t and is_readable(t):
            return t
    except:
        pass
    return ""


def clean_content(text):
    if not text:
        return ""
    if text.startswith("(/"):
        for i, c in enumerate(text):
            if '\u4e00' <= c <= '\u9fff' or c.isalpha():
                text = text[i:]
                break
        else:
            return ""
    clean = []
    for c in text:
        if c.isprintable() or c in "\n\r\t":
            clean.append(c)
        else:
            if len(clean) > 10:
                break
    text = "".join(clean).strip()
    match = re.match(r'^(wxid_\w+|[a-zA-Z0-9_]+):\s*\n?(.+)', text, re.DOTALL)
    if match:
        return f"[{match.group(1)}] {match.group(2).strip()}"
    return text


# ============================================================
# 联系人加载
# ============================================================
def load_contacts(dec_dir):
    contacts = {}
    for db_file in Path(dec_dir).rglob("contact*.db"):
        try:
            conn = sqlite3.connect(str(db_file))
            cur = conn.cursor()
            tables = [r[0] for r in cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            for tbl in tables:
                cols = [r[1] for r in cur.execute(f"PRAGMA table_info([{tbl}])").fetchall()]
                name_col = next((c for c in cols if c.lower() in ("username", "usr_name", "username")), None)
                nick_col = next((c for c in cols if c.lower() in ("nickname", "nick_name", "nickname")), None)
                if not name_col or not nick_col:
                    continue
                for uid, nick in cur.execute(f"SELECT [{name_col}], [{nick_col}] FROM [{tbl}]").fetchall():
                    if uid and nick:
                        contacts[uid] = nick
            conn.close()
        except:
            continue
    return contacts


# ============================================================
# Checkpoint (增量)
# ============================================================
CHECKPOINT_FILE = SCRIPT_DIR / "last_analyzed.json"

def load_checkpoint():
    if CHECKPOINT_FILE.exists():
        return json.loads(CHECKPOINT_FILE.read_text()).get("last_create_time", 0)
    return 0

def save_checkpoint(ts):
    CHECKPOINT_FILE.write_text(json.dumps({
        "last_create_time": ts,
        "updated_at": datetime.now().isoformat()
    }, ensure_ascii=False))


# ============================================================
# 过滤器
# ============================================================
def build_whitelist():
    wxids = set()
    for c in CONFIG.get("watched_contacts", []):
        if c.get("wxid"):
            wxids.add(c["wxid"])
    for g in CONFIG.get("watched_groups", []):
        if g.get("wxid"):
            wxids.add(g["wxid"])
    return wxids

def should_analyze_text(text):
    if not text:
        return False
    keywords = CONFIG.get("product_keywords", []) + CONFIG.get("business_keywords", [])
    if not keywords:
        return True  # No filter configured = analyze all
    return any(kw in text for kw in keywords)


# ============================================================
# 消息提取
# ============================================================
def extract_messages(dec_dir, since_ts=0, whitelist=None, images_only=False):
    """Extract messages from all message DBs with filtering."""
    dec_dir = Path(dec_dir)
    msg_dir = dec_dir / "message"
    if msg_dir.exists():
        msg_files = sorted(msg_dir.glob("message_[0-9]*.db"))
    else:
        msg_files = list(dec_dir.rglob("message_[0-9]*.db"))

    if not msg_files:
        print("[错误] 找不到 message 数据库")
        return [], []

    contacts = load_contacts(dec_dir)
    text_messages = []
    image_items = []
    total = 0
    filtered = 0

    for db_file in msg_files:
        try:
            conn = sqlite3.connect(str(db_file))
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Name2Id mapping
            n2id = {}
            try:
                for row in cur.execute("SELECT * FROM Name2Id").fetchall():
                    d = dict(row)
                    usr = d.get("UsrName", d.get("userName", d.get("usr_name", "")))
                    if usr:
                        n2id[usr] = d
            except:
                pass

            tables = [r[0] for r in cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'"
            ).fetchall()]

            for tbl in tables:
                tbl_hash = tbl.replace("Msg_", "")

                # Resolve contact
                chat_id = tbl_hash
                for usr, info in n2id.items():
                    vals = [str(v) for v in info.values() if v]
                    if any(tbl_hash[:12] in v for v in vals):
                        chat_id = usr
                        break

                # Whitelist filter
                if whitelist and chat_id not in whitelist:
                    continue

                chat_name = contacts.get(chat_id, chat_id)
                if "@chatroom" in str(chat_id):
                    chat_name = f"[群]{chat_name}"

                try:
                    where = f"create_time > {since_ts}" if since_ts > 0 else "1=1"
                    if images_only:
                        type_filter = "AND local_type = 3"
                    else:
                        type_filter = "AND local_type IN (1, 3)"

                    rows = cur.execute(
                        f"SELECT * FROM [{tbl}] WHERE {where} {type_filter} ORDER BY create_time ASC"
                    ).fetchall()
                except:
                    try:
                        rows = cur.execute(f"SELECT * FROM [{tbl}] ORDER BY create_time ASC").fetchall()
                    except:
                        continue

                for row in rows:
                    d = dict(row)
                    total += 1
                    ts = d.get("create_time", d.get("CreateTime", 0))
                    is_sender = d.get("is_sender", d.get("IsSender", 0))
                    msg_type = d.get("local_type", d.get("Type", 0))

                    if msg_type == 1:  # Text
                        content = ""
                        mc = d.get("message_content")
                        if mc:
                            if isinstance(mc, str) and mc.strip():
                                content = mc.strip()
                            elif isinstance(mc, bytes):
                                content = decode_blob(mc)
                        if not content:
                            cc = d.get("compress_content")
                            if cc and isinstance(cc, bytes):
                                content = decode_blob(cc)
                        if not content:
                            for col in ["packed_info_data", "StrContent", "strContent"]:
                                if col in d and d[col]:
                                    val = d[col]
                                    content = decode_blob(val) if isinstance(val, bytes) else str(val).strip()
                                    if content:
                                        break

                        content = clean_content(content)
                        if content and len(content) > 2:
                            if should_analyze_text(content):
                                try:
                                    dt = datetime.fromtimestamp(ts, tz=BEIJING_TZ)
                                    time_str = dt.strftime("%Y-%m-%d %H:%M")
                                except:
                                    time_str = str(ts)
                                text_messages.append({
                                    "time": time_str, "ts": ts,
                                    "wxid": chat_id, "contact": chat_name,
                                    "sender": "我" if is_sender else chat_name,
                                    "content": content,
                                })
                            else:
                                filtered += 1

                    elif msg_type == 3:  # Image
                        img_data = d.get("message_content") or d.get("compress_content")
                        if img_data and isinstance(img_data, bytes) and len(img_data) > 500:
                            try:
                                dt = datetime.fromtimestamp(ts, tz=BEIJING_TZ)
                                time_str = dt.strftime("%Y-%m-%d %H:%M")
                            except:
                                time_str = str(ts)
                            image_items.append({
                                "time": time_str, "ts": ts,
                                "wxid": chat_id, "contact": chat_name,
                                "image_data": img_data, "is_sender": is_sender,
                            })

            conn.close()
        except Exception as e:
            print(f"  [!!] {db_file.name}: {e}")

    print(f"  扫描: {total} 条 → 文本: {len(text_messages)} 条, 图片: {len(image_items)} 张, 过滤掉: {filtered} 条")
    return text_messages, image_items


# ============================================================
# 发现模式 — 扫描所有会话找业务相关的
# ============================================================
def discover_contacts(dec_dir):
    """Scan all conversations, rank by business relevance."""
    print("\n[发现模式] 扫描所有会话，寻找业务相关联系人...")
    contacts = load_contacts(Path(dec_dir))
    keywords = CONFIG.get("product_keywords", []) + CONFIG.get("business_keywords", [])

    # Extract ALL text messages (no whitelist, no keyword filter)
    dec_path = Path(dec_dir)
    msg_dir = dec_path / "message"
    msg_files = sorted(msg_dir.glob("message_[0-9]*.db")) if msg_dir.exists() else list(dec_path.rglob("message_[0-9]*.db"))

    chat_stats = defaultdict(lambda: {"total": 0, "business": 0, "samples": [], "name": ""})

    for db_file in msg_files:
        try:
            conn = sqlite3.connect(str(db_file))
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            n2id = {}
            try:
                for row in cur.execute("SELECT * FROM Name2Id").fetchall():
                    d = dict(row)
                    usr = d.get("UsrName", d.get("userName", ""))
                    if usr:
                        n2id[usr] = d
            except:
                pass

            tables = [r[0] for r in cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'"
            ).fetchall()]

            for tbl in tables:
                tbl_hash = tbl.replace("Msg_", "")
                chat_id = tbl_hash
                for usr, info in n2id.items():
                    vals = [str(v) for v in info.values() if v]
                    if any(tbl_hash[:12] in v for v in vals):
                        chat_id = usr
                        break

                chat_name = contacts.get(chat_id, chat_id)
                chat_stats[chat_id]["name"] = chat_name

                try:
                    # Only look at recent 30 days text messages
                    cutoff = int((datetime.now(tz=BEIJING_TZ) - timedelta(days=30)).timestamp())
                    rows = cur.execute(
                        f"SELECT * FROM [{tbl}] WHERE create_time > {cutoff} AND local_type = 1"
                    ).fetchall()
                except:
                    continue

                for row in rows:
                    d = dict(row)
                    content = ""
                    mc = d.get("message_content")
                    if mc:
                        if isinstance(mc, str):
                            content = mc.strip()
                        elif isinstance(mc, bytes):
                            content = decode_blob(mc)
                    if not content:
                        cc = d.get("compress_content")
                        if cc and isinstance(cc, bytes):
                            content = decode_blob(cc)

                    content = clean_content(content)
                    if content and len(content) > 2:
                        chat_stats[chat_id]["total"] += 1
                        if any(kw in content for kw in keywords):
                            chat_stats[chat_id]["business"] += 1
                            if len(chat_stats[chat_id]["samples"]) < 3:
                                chat_stats[chat_id]["samples"].append(content[:80])

            conn.close()
        except:
            continue

    # Rank by business message count
    ranked = sorted(chat_stats.items(), key=lambda x: -x[1]["business"])
    business_contacts = [(cid, s) for cid, s in ranked if s["business"] > 0]

    print(f"\n  共 {len(chat_stats)} 个会话, {len(business_contacts)} 个含业务关键词")
    print(f"\n{'='*70}")
    print(f"  {'wxid':<30} {'昵称':<15} {'总消息':>6} {'业务':>6} {'采样'}")
    print(f"  {'-'*30} {'-'*15} {'-'*6} {'-'*6} {'-'*20}")

    suggestions = []
    for cid, s in business_contacts[:30]:
        name = s["name"][:14]
        sample = s["samples"][0][:30] if s["samples"] else ""
        print(f"  {cid:<30} {name:<15} {s['total']:>6} {s['business']:>6} {sample}")
        if s["business"] >= 3:  # At least 3 business messages
            role = "customer"
            if any(kw in str(s["samples"]) for kw in ["报价", "进货", "发货", "供", "批"]):
                role = "supplier"
            suggestions.append({"wxid": cid, "role": role, "name": s["name"]})

    # Save suggestions
    suggest_file = SCRIPT_DIR / "discovered_contacts.json"
    with open(suggest_file, "w", encoding="utf-8") as f:
        json.dump(suggestions, f, ensure_ascii=False, indent=2)
    print(f"\n  建议关注 {len(suggestions)} 个联系人 → {suggest_file}")
    print(f"  确认后复制到 config.json 的 watched_contacts 中")


# ============================================================
# DeepSeek 分析
# ============================================================
def get_api_key():
    key = os.environ.get("DEEPSEEK_API_KEY", CONFIG.get("deepseek", {}).get("api_key", ""))
    if not key:
        print("[错误] 请设置 DEEPSEEK_API_KEY 环境变量")
        sys.exit(1)
    return key


def analyze_batch(messages, api_key):
    """Send message batch to DeepSeek for structured extraction."""
    import requests as req

    lines = []
    for m in messages:
        lines.append(f"[{m['time']}] {m['sender']}: {m['content']}")

    prompt = """分析以下微信聊天记录，提取三类信息。严格按 JSON 格式输出。

聊天记录：
""" + "\n".join(lines) + """

请提取：
1. orders: 订单/交易记录 [{"time":"", "product":"产品名", "quantity":数量, "amount":金额, "buyer":"买家名"}]
2. feedback: 客户反馈 [{"time":"", "summary":"一句话摘要", "sentiment":"正面/负面/中性", "product":"涉及产品"}]
3. demand_signals: 需求信号 [{"description":"描述", "count":出现次数, "urgency":"高/中/低"}]
4. daily_summary: 一句话总结今日经营状况

只输出 JSON，不要其他文字。如果某类无数据就返回空数组。"""

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    model = CONFIG.get("deepseek", {}).get("model", "deepseek-chat")

    try:
        resp = req.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "你是电商数据提取助手。只输出 JSON。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 4000,
            },
            timeout=60,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        return json.loads(content)
    except Exception as e:
        print(f"  [错误] DeepSeek: {e}")
        return {"orders": [], "feedback": [], "demand_signals": [], "daily_summary": f"分析失败: {e}"}


def analyze_image_ocr(image_data, context, api_key):
    """Send image to DeepSeek Vision for OCR."""
    import requests as req

    b64 = base64.b64encode(image_data).decode("utf-8")
    prompt = f"""这是微信聊天中的图片，可能是进货单/报价单/产品清单/收据。
{f"上下文: {context}" if context else ""}

分析并输出 JSON:
1. type: "price_list" / "order" / "receipt" / "product" / "other"
2. items: [{{"product":"产品名(中文)", "price":单价, "quantity":数量或null, "unit":"件/盒/支", "note":"备注"}}]
3. raw_text: 图片中可识别文字

只输出 JSON。"""

    vision_model = CONFIG.get("deepseek", {}).get("vision_model", "deepseek-chat")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        resp = req.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json={
                "model": vision_model,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    ],
                }],
                "temperature": 0.1,
                "max_tokens": 2000,
            },
            timeout=60,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        return json.loads(content)
    except Exception as e:
        print(f"  [错误] Vision: {e}")
        return {"type": "other", "items": [], "raw_text": ""}


# ============================================================
# 上传到素仁轩
# ============================================================
def upload_to_surenxuan(result):
    url = CONFIG.get("surenxuan_api", {}).get("url", "")
    api_key = CONFIG.get("surenxuan_api", {}).get("api_key", "srx-wechat-2026")
    if not url:
        print("  [跳过] 未配置 surenxuan_api.url")
        return
    try:
        import urllib.request
        data = json.dumps(result, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        }, method="POST")
        resp = urllib.request.urlopen(req, timeout=30)
        resp_data = json.loads(resp.read().decode())
        print(f"  上传成功: {resp_data.get('message', '')}")
    except Exception as e:
        print(f"  上传失败: {e}")


# ============================================================
# 主流程
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="微信聊天分析 v2")
    parser.add_argument("--db", required=True, help="解密后数据库目录")
    parser.add_argument("--discover", action="store_true", help="发现模式：扫描所有会话找业务联系人")
    parser.add_argument("--incremental", action="store_true", help="增量模式：只分析新消息")
    parser.add_argument("--upload", action="store_true", help="分析完自动上传到素仁轩")
    parser.add_argument("--images-only", action="store_true", help="只分析图片")
    parser.add_argument("--days", type=int, default=7, help="分析最近N天（非增量模式）")
    args = parser.parse_args()

    print("=" * 55)
    print("  微信聊天分析 v2 — 素仁轩")
    print("=" * 55)

    if args.discover:
        discover_contacts(args.db)
        return

    api_key = get_api_key()
    whitelist = build_whitelist()
    if whitelist:
        print(f"  白名单: {len(whitelist)} 个联系人")
    else:
        print("  [注意] 未配置白名单，将分析所有会话（建议先 --discover）")

    # Checkpoint
    since_ts = load_checkpoint() if args.incremental else 0
    if not since_ts and not args.incremental:
        since_ts = int((datetime.now(tz=BEIJING_TZ) - timedelta(days=args.days)).timestamp())
    if since_ts:
        dt = datetime.fromtimestamp(since_ts, tz=BEIJING_TZ)
        print(f"  时间范围: {dt.strftime('%Y-%m-%d %H:%M')} 之后")

    # Extract
    print(f"\n[1/3] 提取消息...")
    messages, images = extract_messages(
        args.db, since_ts=since_ts,
        whitelist=whitelist if whitelist else None,
        images_only=args.images_only,
    )

    if not messages and not images:
        print("  无新消息")
        return

    today = datetime.now(tz=BEIJING_TZ).strftime("%Y-%m-%d")
    result = {"date": today, "orders": [], "feedback": [], "demand_signals": [], "daily_summary": ""}

    # Analyze text
    if messages and not args.images_only:
        batch_size = CONFIG.get("deepseek", {}).get("max_messages_per_batch", 50)
        print(f"\n[2/3] DeepSeek 分析 ({len(messages)} 条, 每批 {batch_size})...")
        for i in range(0, len(messages), batch_size):
            batch = messages[i:i + batch_size]
            print(f"  批次 {i//batch_size + 1}: {len(batch)} 条...")
            r = analyze_batch(batch, api_key)
            result["orders"].extend(r.get("orders", []))
            result["feedback"].extend(r.get("feedback", []))
            result["demand_signals"].extend(r.get("demand_signals", []))
            if r.get("daily_summary"):
                result["daily_summary"] = r["daily_summary"]

    # Analyze images
    if images:
        print(f"\n[2b/3] 图片分析 ({len(images)} 张)...")
        price_items = []
        for idx, img in enumerate(images[:20]):  # Cap at 20 images
            print(f"  图片 {idx+1}/{min(len(images), 20)} ({img['contact']})...")
            r = analyze_image_ocr(img["image_data"], f"来自 {img['contact']}", api_key)
            if r.get("type") in ("price_list", "order"):
                for item in r.get("items", []):
                    price_items.append({"source": img["contact"], "time": img["time"], **item})
                    if r["type"] == "order":
                        result["orders"].append({
                            "time": img["time"], "product": item.get("product", ""),
                            "quantity": item.get("quantity") or 0,
                            "amount": item.get("price") or 0, "buyer": img["contact"],
                        })
        if price_items:
            pf = SCRIPT_DIR / f"price_list_{today}.json"
            with open(pf, "w", encoding="utf-8") as f:
                json.dump(price_items, f, ensure_ascii=False, indent=2)
            print(f"  进货单: {len(price_items)} 个产品 → {pf}")

    # Output
    print(f"\n[3/3] 结果")
    print(f"  订单: {len(result['orders'])}, 反馈: {len(result['feedback'])}, 信号: {len(result['demand_signals'])}")
    if result["daily_summary"]:
        print(f"  总结: {result['daily_summary']}")

    out_file = SCRIPT_DIR / f"daily_report_{today}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  保存: {out_file}")

    if args.upload:
        print(f"\n  上传素仁轩...")
        upload_to_surenxuan(result)

    # Save checkpoint
    max_ts = max([m["ts"] for m in messages], default=0) if messages else 0
    if max_ts > 0:
        save_checkpoint(max_ts)

    print(f"\n{'='*55}")
    print("  完成!")


if __name__ == "__main__":
    main()
