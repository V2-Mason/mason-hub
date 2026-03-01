"""
XHS QR Code Login — Playwright 扫码登录并保存 cookie (stealth 模式)
用法: python3 _xhs_qr_login.py [timeout_seconds]

环境变量:
  SLACK_BOT_TOKEN — Slack Bot token（可选，有则直接发 Slack）
  SLACK_CHANNEL   — Slack 频道 ID（默认 #rednote）

流程:
1. Playwright 启动 Chromium（反检测参数 + stealth.js + 代理）
2. 打开 XHS → 截图 QR → 发 Slack
3. 等用户扫码（cookie 轮询检测）
4. 如果弹 Security QR → 立刻截图发 Slack
5. 如果弹验证码框 → 写 NEED_CODE → 等 /tmp/xhs_verify_code 文件
6. 提取 cookies → 保存到 base_config.py → 写 SUCCESS
"""
import asyncio
import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse

TIMEOUT = int(sys.argv[1]) if len(sys.argv) > 1 else 300
MC_DIR = "/opt/mediacrawler"
QR_FILE = "/tmp/xhs_qr.png"
STATUS_FILE = "/tmp/xhs_login_status"
CODE_FILE = "/tmp/xhs_verify_code"

# Slack 配置
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "C0AHB976R9V")  # #rednote

# 代理配置 — 从 .env 读取
TUNNEL_HOST = "z354.kdltpspro.com"
TUNNEL_PORT = "15818"
TUNNEL_USER = "t17230157281666"
TUNNEL_PWD = "49s3a6a8"

env_file = f"{MC_DIR}/.env"
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip("\"'")
                if k == "KDL_TUNNEL_HOST":
                    TUNNEL_HOST = v
                elif k == "KDL_TUNNEL_PORT":
                    TUNNEL_PORT = v
                elif k == "KDL_TUNNEL_USER":
                    TUNNEL_USER = v
                elif k == "KDL_TUNNEL_PWD":
                    TUNNEL_PWD = v

STEALTH_JS = f"{MC_DIR}/libs/stealth.min.js"


def write_status(s):
    with open(STATUS_FILE, "w") as f:
        f.write(s)
    print(f"[STATUS] {s}")


def slack_upload(filepath, message):
    """直接从阿里云上传图片到 Slack（3-step API）"""
    if not SLACK_TOKEN:
        print("No SLACK_TOKEN, skipping upload")
        return False

    try:
        fsize = os.path.getsize(filepath)

        # Step 1: getUploadURLExternal
        data = urllib.parse.urlencode({
            "filename": "xhs_qr.png",
            "length": fsize,
        }).encode()
        req = urllib.request.Request(
            "https://slack.com/api/files.getUploadURLExternal",
            data=data,
            headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
        if not resp.get("ok"):
            print(f"Slack getUploadURL failed: {resp.get('error')}")
            return False

        upload_url = resp["upload_url"]
        file_id = resp["file_id"]

        # Step 2: upload file
        with open(filepath, "rb") as f:
            file_data = f.read()

        boundary = "----SlackUploadBoundary"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="xhs_qr.png"\r\n'
            f"Content-Type: image/png\r\n\r\n"
        ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

        req2 = urllib.request.Request(
            upload_url,
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        urllib.request.urlopen(req2, timeout=15)

        # Step 3: completeUploadExternal
        complete_data = json.dumps({
            "files": [{"id": file_id, "title": "XHS QR Code"}],
            "channel_id": SLACK_CHANNEL,
            "initial_comment": message,
        }).encode()
        req3 = urllib.request.Request(
            "https://slack.com/api/files.completeUploadExternal",
            data=complete_data,
            headers={
                "Authorization": f"Bearer {SLACK_TOKEN}",
                "Content-Type": "application/json",
            },
        )
        resp3 = json.loads(urllib.request.urlopen(req3, timeout=10).read())
        if resp3.get("ok"):
            print(f"Slack upload OK ({fsize} bytes)")
            return True
        else:
            print(f"Slack complete failed: {resp3.get('error')}")
            return False

    except Exception as e:
        print(f"Slack upload error: {e}")
        return False


def get_web_session(cookies):
    """从 cookie 列表中提取 web_session 值"""
    ws = next((c for c in cookies if c["name"] == "web_session"), None)
    return ws["value"] if ws else ""


def check_login(cookies, old_web_session=""):
    """检查登录态 — 采用 MediaCrawler 同样的逻辑"""
    # 方法 1: 特定登录 cookie
    login_names = {
        "galaxy_creator_session_id",
        "access-token-creator.xiaohongshu.com",
        "x-user-id-creator.xiaohongshu.com",
    }
    found = [c["name"] for c in cookies if c["name"] in login_names]
    if found:
        return True, f"cookies: {found}"
    # 方法 2: web_session 值发生变化（MediaCrawler 的核心检测）
    current_ws = get_web_session(cookies)
    if current_ws and old_web_session and current_ws != old_web_session:
        return True, f"web_session changed (old={old_web_session[:20]}... new={current_ws[:20]}...)"
    return False, ""


async def main():
    from playwright.async_api import async_playwright

    write_status("STARTING")

    if os.path.exists(CODE_FILE):
        os.remove(CODE_FILE)

    print(f"Using proxy: {TUNNEL_HOST}:{TUNNEL_PORT}")
    print(f"Slack: {'enabled' if SLACK_TOKEN else 'disabled'}")
    print(f"Timeout: {TIMEOUT}s")
    print(f"Stealth: {os.path.exists(STEALTH_JS)}")

    async with async_playwright() as p:
        # 使用反检测参数启动 Chromium
        browser = await p.chromium.launch(
            headless=True,
            proxy={
                "server": f"http://{TUNNEL_HOST}:{TUNNEL_PORT}",
                "username": TUNNEL_USER,
                "password": TUNNEL_PWD,
            },
            args=[
                # 关键反检测参数（与 MediaCrawler 一致）
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-features=TranslateUI",
                "--disable-ipc-flooding-protection",
                "--disable-hang-monitor",
            ],
            ignore_default_args=["--enable-automation"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/127.0.6533.17 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )

        # 注入 stealth.js 反检测脚本（与 MediaCrawler 一致）
        if os.path.exists(STEALTH_JS):
            await context.add_init_script(path=STEALTH_JS)
            print(f"Stealth script injected")
        else:
            print(f"WARNING: stealth.js not found at {STEALTH_JS}")

        page = await context.new_page()

        try:
            t0 = time.time()
            print("Navigating to XHS via proxy...")
            await page.goto("https://www.xiaohongshu.com/", timeout=30000)
            await asyncio.sleep(3)
            print(f"Page loaded ({time.time()-t0:.1f}s)")

            # 点击登录（如果需要）
            login_btn = page.locator("text=登录")
            if await login_btn.count() > 0:
                await login_btn.first.click()
                await asyncio.sleep(2)

            # 记录登录前的 web_session（用于后续对比）
            init_cookies = await context.cookies()
            old_web_session = get_web_session(init_cookies)
            print(f"Initial web_session: {old_web_session[:30]}..." if old_web_session else "No initial web_session")

            # 截图 QR → 直接发 Slack
            await page.screenshot(path=QR_FILE, full_page=False)
            qr_time = time.time()
            print(f"QR screenshot saved ({qr_time-t0:.1f}s)")
            write_status("QR_READY")

            from datetime import datetime, timezone, timedelta
            cst = timezone(timedelta(hours=8))
            ts_str = datetime.now(cst).strftime("%H:%M:%S CST")
            slack_upload(QR_FILE, f"🍪 *XHS Cookie 刷新* [{ts_str}] — 请用小红书 APP 扫描此二维码登录")
            print(f"QR sent to Slack ({time.time()-qr_time:.1f}s after screenshot)")

            # --- 等待扫码 ---
            RESEND_FILE = "/tmp/xhs_resend_code"
            if os.path.exists(RESEND_FILE):
                os.remove(RESEND_FILE)

            print(f"Waiting for QR scan (timeout: {TIMEOUT}s)...")
            start = time.time()
            logged_in = False
            security_qr_sent = False
            sms_detected = False
            last_screenshot = time.time()

            while time.time() - start < TIMEOUT:
                await asyncio.sleep(3)
                elapsed = int(time.time() - start)

                # 每 30 秒截一次图（用于调试，不发 Slack）
                if time.time() - last_screenshot > 30:
                    await page.screenshot(path=QR_FILE, full_page=False)
                    last_screenshot = time.time()

                # 检查是否已登录（cookie 对比）
                cookies = await context.cookies()
                ok, reason = check_login(cookies, old_web_session)
                if ok:
                    logged_in = True
                    print(f"Login detected at {elapsed}s: {reason}")
                    break

                # 每轮打印 cookie 状态方便调试
                current_ws = get_web_session(cookies)
                if elapsed % 15 == 0:
                    cookie_names = [c["name"] for c in cookies if "xiaohongshu" in c.get("domain", "")]
                    print(f"  [{elapsed}s] cookies: {cookie_names}, ws={current_ws[:20] if current_ws else 'none'}...")

                # 检查页面是否出现了新内容（Security QR / SMS 验证）
                try:
                    page_text = await page.inner_text("body")
                except Exception:
                    page_text = ""

                # Security Verification QR
                if not security_qr_sent and ("Security Verification" in page_text or "安全验证" in page_text):
                    print(f"Security Verification detected at {elapsed}s!")
                    await page.screenshot(path=QR_FILE, full_page=False)
                    write_status("SECURITY_QR")
                    ts_now = datetime.now(cst).strftime("%H:%M:%S CST")
                    slack_upload(
                        QR_FILE,
                        f"🔐 *安全验证* [{ts_now}] — 请用已登录的小红书 APP 扫描此二维码完成验证"
                    )
                    security_qr_sent = True

                # SMS 验证码弹框
                if not sms_detected and ("SMS Verification" in page_text or "短信验证" in page_text or "Verification code has been sent" in page_text):
                    print(f"SMS Verification detected at {elapsed}s!")
                    await page.screenshot(path=QR_FILE, full_page=False)
                    write_status("NEED_CODE")
                    ts_now = datetime.now(cst).strftime("%H:%M:%S CST")
                    slack_upload(QR_FILE, f"🔢 *SMS 验证* [{ts_now}] — 验证码已发送，等待输入。如需重发请告知。")
                    sms_detected = True

                # 检查 resend 指令
                if sms_detected and os.path.exists(RESEND_FILE):
                    os.remove(RESEND_FILE)
                    print("Resend requested!")
                    resend_btn = page.locator(
                        "text=Get code, "
                        "text=重新获取, "
                        "text=重新发送, "
                        "text=Resend"
                    )
                    if await resend_btn.count() > 0:
                        await resend_btn.first.click()
                        print("Resend button clicked")
                        await asyncio.sleep(2)
                        await page.screenshot(path=QR_FILE, full_page=False)
                        slack_upload(QR_FILE, "🔄 验证码已重新发送")
                    else:
                        print("Resend button not found")

                # 检查验证码文件
                if sms_detected and os.path.exists(CODE_FILE):
                    with open(CODE_FILE) as f:
                        code = f.read().strip()
                    if code:
                        print(f"Got verification code: {code}")
                        os.remove(CODE_FILE)

                        code_input = page.locator(
                            "input[placeholder*='验证码'], "
                            "input[placeholder*='verification code'], "
                            "input[placeholder*='code'], "
                            "input[placeholder*='验证']"
                        )
                        if await code_input.count() > 0:
                            await code_input.first.fill(code)
                            print("Verification code entered, waiting for auto-submit...")
                        else:
                            # 尝试所有空的 input
                            all_inputs = page.locator("input:not([type='checkbox'])")
                            count = await all_inputs.count()
                            for i in range(count):
                                val = await all_inputs.nth(i).input_value()
                                if not val or len(val) < 3:
                                    await all_inputs.nth(i).fill(code)
                                    print(f"Code entered in input #{i}")
                                    break

                        # 不主动点按钮——等 XHS 自动验证或用户手动完成
                        # 如果 5 秒后没有自动提交，再尝试用 force 点击
                        await asyncio.sleep(5)
                        await page.screenshot(path=QR_FILE, full_page=False)

                        cookies = await context.cookies()
                        ok, reason = check_login(cookies, old_web_session)
                        if ok:
                            logged_in = True
                            print(f"Login confirmed after code: {reason}")
                            break

                        # 检查是否有 CAPTCHA 滑块
                        captcha = page.locator("[class*='captcha'], [class*='slider']")
                        if await captcha.count() > 0:
                            print("CAPTCHA slider detected! Sending screenshot to Slack...")
                            ts_now = datetime.now(cst).strftime("%H:%M:%S CST")
                            slack_upload(
                                QR_FILE,
                                f"⚠️ *滑动验证码* [{ts_now}] — 检测到 CAPTCHA，脚本无法自动处理。"
                                f" 尝试用 force click 提交..."
                            )

                        # 尝试 force click 绕过遮挡
                        submit_btn = page.locator(
                            "button:has-text('登录'), "
                            "button[type='submit']"
                        )
                        if await submit_btn.count() > 0:
                            try:
                                await submit_btn.first.click(force=True, timeout=3000)
                                print("Login button force-clicked")
                            except Exception as e:
                                print(f"Force click failed: {e}")

                        # 等登录完成
                        print("Waiting for login after code...")
                        for _ in range(20):
                            await asyncio.sleep(3)
                            cookies = await context.cookies()
                            ok, reason = check_login(cookies, old_web_session)
                            if ok:
                                logged_in = True
                                print(f"Login confirmed: {reason}")
                                break
                        break

            if not logged_in:
                cur_status = open(STATUS_FILE).read()
                if "TIMEOUT" not in cur_status:
                    write_status("TIMEOUT")
                print("Login not detected")
                await page.screenshot(path=QR_FILE, full_page=False)
                await browser.close()
                return

            # --- 登录成功 — 提取 cookies ---
            await asyncio.sleep(2)
            cookies = await context.cookies()
            cookie_str = "; ".join(
                f'{c["name"]}={c["value"]}'
                for c in cookies
                if "xiaohongshu" in c.get("domain", "")
            )

            if not cookie_str:
                print("ERROR: No XHS cookies found after login")
                write_status("ERROR_NO_COOKIES")
                await browser.close()
                return

            config_path = f"{MC_DIR}/config/base_config.py"
            with open(config_path, "r") as f:
                config = f.read()

            new_config = re.sub(
                r"COOKIES\s*=\s*['\"].*?['\"]",
                f"COOKIES = '{cookie_str}'",
                config,
                count=1,
                flags=re.DOTALL,
            )

            with open(config_path, "w") as f:
                f.write(new_config)

            print(f"Cookie saved ({len(cookie_str)} chars)")
            write_status("SUCCESS")
            slack_upload(QR_FILE, f"✅ *XHS Cookie 刷新成功* — 新 cookie 已保存（{len(cookie_str)} chars）")

        except Exception as e:
            print(f"Error: {e}")
            write_status(f"ERROR:{e}")
            try:
                await page.screenshot(path=QR_FILE, full_page=False)
            except Exception:
                pass
        finally:
            await browser.close()


asyncio.run(main())
