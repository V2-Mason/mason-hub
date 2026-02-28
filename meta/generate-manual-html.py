#!/usr/bin/env python3
"""将 ops-manual.md 转为带样式的 HTML 文件"""

import re
import os

INPUT = os.path.expanduser("~/mason-hub/meta/ops-manual.md")
OUTPUT = os.path.expanduser("~/mason-hub/meta/ops-manual.html")

with open(INPUT, "r", encoding="utf-8") as f:
    md = f.read()

# --- Markdown → HTML (手写轻量转换，不依赖外部库) ---

def md_to_html(text):
    lines = text.split("\n")
    html_lines = []
    in_table = False
    in_code = False
    in_list = False
    in_sublist = False
    table_header_done = False

    for line in lines:
        # Code blocks
        if line.strip().startswith("```"):
            if in_code:
                html_lines.append("</code></pre>")
                in_code = False
            else:
                html_lines.append('<pre class="code-block"><code>')
                in_code = True
            continue
        if in_code:
            html_lines.append(line.replace("<", "&lt;").replace(">", "&gt;"))
            continue

        # Close list if needed
        if in_sublist and not line.startswith("   -") and not line.startswith("   *"):
            html_lines.append("</ul>")
            in_sublist = False
        if in_list and not line.startswith("   -") and not re.match(r'^\d+\.', line.strip()) and not line.startswith("- ") and line.strip() != "":
            if not line.startswith("   "):
                html_lines.append("</ul>" if in_list == "ul" else "</ol>")
                in_list = False

        # Table
        if "|" in line and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(re.match(r'^[-:]+$', c) for c in cells):
                table_header_done = True
                continue
            if not in_table:
                html_lines.append('<div class="table-wrapper"><table>')
                in_table = True
                tag = "th"
                table_header_done = False
            else:
                tag = "th" if not table_header_done else "td"
            row = "".join(f"<{tag}>{inline(c)}</{tag}>" for c in cells)
            html_lines.append(f"<tr>{row}</tr>")
            continue
        elif in_table:
            html_lines.append("</table></div>")
            in_table = False
            table_header_done = False

        # Headings
        m = re.match(r'^(#{1,4})\s+(.*)', line)
        if m:
            level = len(m.group(1))
            html_lines.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
            continue

        # HR
        if line.strip() == "---":
            html_lines.append("<hr>")
            continue

        # Ordered list
        m = re.match(r'^(\d+)\.\s+(.*)', line)
        if m:
            if not in_list:
                html_lines.append("<ol>")
                in_list = "ol"
            html_lines.append(f"<li>{inline(m.group(2))}</li>")
            continue

        # Sub-list
        if line.startswith("   - ") or line.startswith("   * "):
            if not in_sublist:
                html_lines.append("<ul class='sublist'>")
                in_sublist = True
            html_lines.append(f"<li>{inline(line.strip()[2:])}</li>")
            continue

        # Unordered list
        if line.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = "ul"
            html_lines.append(f"<li>{inline(line[2:])}</li>")
            continue

        # Empty line
        if line.strip() == "":
            if in_list:
                pass  # keep list open
            html_lines.append("")
            continue

        # Paragraph
        html_lines.append(f"<p>{inline(line)}</p>")

    # Close open elements
    if in_table:
        html_lines.append("</table></div>")
    if in_sublist:
        html_lines.append("</ul>")
    if in_list:
        html_lines.append("</ul>" if in_list == "ul" else "</ol>")
    if in_code:
        html_lines.append("</code></pre>")

    return "\n".join(html_lines)


def inline(text):
    """Handle inline formatting"""
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Inline code
    text = re.sub(r'`([^`]+)`', r'<code class="inline">\1</code>', text)
    # Links (if any)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    return text


body = md_to_html(md)

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mason Hub — 日常运营手册</title>
<style>
  @page {{ margin: 2cm; }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
    max-width: 800px;
    margin: 0 auto;
    padding: 40px 24px;
    color: #1a1a1a;
    line-height: 1.7;
    background: #fff;
  }}
  h1 {{
    font-size: 28px;
    border-bottom: 3px solid #2563eb;
    padding-bottom: 12px;
    margin-bottom: 8px;
  }}
  h2 {{
    font-size: 22px;
    color: #2563eb;
    margin-top: 36px;
    border-left: 4px solid #2563eb;
    padding-left: 12px;
  }}
  h3 {{
    font-size: 17px;
    color: #374151;
    margin-top: 24px;
  }}
  hr {{
    border: none;
    border-top: 1px solid #e5e7eb;
    margin: 28px 0;
  }}
  .table-wrapper {{
    overflow-x: auto;
    margin: 16px 0;
  }}
  table {{
    border-collapse: collapse;
    width: 100%;
    font-size: 14px;
  }}
  th {{
    background: #f1f5f9;
    font-weight: 600;
    text-align: left;
    padding: 10px 14px;
    border: 1px solid #e2e8f0;
  }}
  td {{
    padding: 8px 14px;
    border: 1px solid #e2e8f0;
  }}
  tr:nth-child(even) td {{
    background: #f8fafc;
  }}
  .code-block {{
    background: #1e293b;
    color: #e2e8f0;
    padding: 16px 20px;
    border-radius: 8px;
    overflow-x: auto;
    font-size: 13px;
    line-height: 1.5;
  }}
  code.inline {{
    background: #f1f5f9;
    color: #dc2626;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.9em;
  }}
  ol, ul {{
    padding-left: 24px;
  }}
  li {{
    margin-bottom: 4px;
  }}
  ul.sublist {{
    margin-top: 4px;
    padding-left: 20px;
  }}
  strong {{
    color: #111827;
  }}
  p {{
    margin: 8px 0;
  }}
  @media print {{
    body {{ padding: 0; }}
    .code-block {{ background: #f3f4f6 !important; color: #1e293b !important; border: 1px solid #d1d5db; }}
    h2 {{ page-break-before: auto; }}
  }}
</style>
</head>
<body>
{body}
<footer style="margin-top:48px; padding-top:16px; border-top:1px solid #e5e7eb; color:#9ca3af; font-size:13px;">
Mason Hub v1.0 · 生成于 2026-02-27 · 保密文件
</footer>
</body>
</html>"""

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ 已生成: {OUTPUT}")
print(f"   大小: {os.path.getsize(OUTPUT)} bytes")
