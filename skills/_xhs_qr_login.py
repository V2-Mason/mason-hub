"""
XHS QR Code Login — Playwright 扫码登录并保存 cookie
用法: python3 _xhs_qr_login.py [timeout_seconds]

流程:
1. 通过代理打开 XHS → 截图 QR → 写 QR_READY
2. 等用户扫码
3. 如果弹验证码框 → 写 NEED_CODE → 等 /tmp/xhs_verify_code 文件
4. 读验证码并输入 → 等登录完成
5. 提取 cookies → 保存到 base_config.py → 写 SUCCESS
"""
import asyncio
import os
import re
import sys
import time

TIMEOUT = int(sys.argv[1]) if len(sys.argv) > 1 else 300
MC_DIR = "/opt/mediacrawler"
QR_FILE = "/tmp/xhs_qr.png"
STATUS_FILE = "/tmp/xhs_login_status"
CODE_FILE = "/tmp/xhs_verify_code"

# 代理配置 — 从 .env 读取
TUNNEL_HOST = "z354.kdltpspro.com"
TUNNEL_PORT = "15818"
TUNNEL_USER = "t17230157281666"
TUNNEL_PWD = "49s3a6a8"

# 尝试从 .env 覆盖
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


def write_status(s):
    with open(STATUS_FILE, "w") as f:
        f.write(s)
    print(f"[STATUS] {s}")


async def wait_for_login(context, page, timeout_secs):
    """等待登录成功（cookie 出现）"""
    start = time.time()
    while time.time() - start < timeout_secs:
        await asyncio.sleep(2)
        cookies = await context.cookies()
        # 真正的登录态标志
        login_names = {
            "galaxy_creator_session_id",
            "access-token-creator.xiaohongshu.com",
            "x-user-id-creator.xiaohongshu.com",
        }
        found = [c["name"] for c in cookies if c["name"] in login_names]
        if found:
            print(f"Login confirmed: {found}")
            return True

        # web_session 长度 > 60 也算登录态
        ws = next((c for c in cookies if c["name"] == "web_session"), None)
        if ws and len(ws["value"]) > 60:
            print(f"Login confirmed: web_session len={len(ws['value'])}")
            return True
    return False


async def main():
    from playwright.async_api import async_playwright

    write_status("STARTING")

    # 清理旧验证码文件
    if os.path.exists(CODE_FILE):
        os.remove(CODE_FILE)

    proxy_url = f"http://{TUNNEL_USER}:{TUNNEL_PWD}@{TUNNEL_HOST}:{TUNNEL_PORT}"
    print(f"Using proxy: {TUNNEL_HOST}:{TUNNEL_PORT}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            proxy={"server": f"http://{TUNNEL_HOST}:{TUNNEL_PORT}",
                   "username": TUNNEL_USER,
                   "password": TUNNEL_PWD},
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        await context.clear_cookies()
        page = await context.new_page()

        try:
            print("Navigating to XHS via proxy...")
            await page.goto("https://www.xiaohongshu.com/", timeout=30000)
            await asyncio.sleep(3)

            # 点击登录（如果需要）
            login_btn = page.locator("text=登录")
            if await login_btn.count() > 0:
                await login_btn.first.click()
                await asyncio.sleep(2)

            # 截图 QR
            await page.screenshot(path=QR_FILE, full_page=False)
            print(f"QR screenshot saved: {QR_FILE}")
            write_status("QR_READY")

            # --- 阶段 A: 等待扫码（QR 消失 = 已扫码） ---
            print(f"Waiting for QR scan (timeout: {TIMEOUT}s)...")
            start = time.time()
            logged_in = False
            qr_scanned = False

            while time.time() - start < TIMEOUT:
                await asyncio.sleep(3)
                elapsed = int(time.time() - start)

                # 每 25 秒刷新截图
                if elapsed > 0 and elapsed % 25 == 0:
                    await page.screenshot(path=QR_FILE, full_page=False)
                    write_status(f"QR_REFRESHED_{elapsed}")

                # 检查是否已登录
                cookies = await context.cookies()
                login_names = {
                    "galaxy_creator_session_id",
                    "access-token-creator.xiaohongshu.com",
                    "x-user-id-creator.xiaohongshu.com",
                }
                found = [c["name"] for c in cookies if c["name"] in login_names]
                if found:
                    logged_in = True
                    print(f"Login detected: {found}")
                    break
                ws = next((c for c in cookies if c["name"] == "web_session"), None)
                if ws and len(ws["value"]) > 60:
                    logged_in = True
                    print(f"Login detected: web_session len={len(ws['value'])}")
                    break

                # 检查 QR 码是否消失（= 已扫码，可能进入验证码阶段）
                qr_img = page.locator("canvas, img[src*='qrcode'], .qrcode-img, [class*='qrcode']")
                if await qr_img.count() == 0 and not qr_scanned:
                    print("QR code disappeared — user likely scanned")
                    qr_scanned = True
                    await asyncio.sleep(2)
                    await page.screenshot(path=QR_FILE, full_page=False)

                # 扫码后才检测验证码输入框
                if qr_scanned and not logged_in:
                    # 只匹配验证码专用输入框，排除手机号输入框
                    code_input = page.locator(
                        "input[placeholder*='验证码'], "
                        "input[placeholder*='验证']"
                    )
                    if await code_input.count() > 0:
                        print("Verification code input detected!")
                        await page.screenshot(path=QR_FILE, full_page=False)
                        write_status("NEED_CODE")

                        # 等待验证码文件
                        code_wait_start = time.time()
                        code = None
                        while time.time() - code_wait_start < 120:
                            if os.path.exists(CODE_FILE):
                                with open(CODE_FILE) as f:
                                    code = f.read().strip()
                                if code:
                                    break
                            await asyncio.sleep(1)

                        if not code:
                            print("Timeout waiting for verification code")
                            write_status("TIMEOUT_NO_CODE")
                            break

                        print(f"Got verification code: {code}")
                        await code_input.first.fill(code)
                        await asyncio.sleep(0.5)

                        # 点击提交
                        submit_btn = page.locator(
                            "button:has-text('确认'), "
                            "button:has-text('提交'), "
                            "button:has-text('确定'), "
                            "button:has-text('登录'), "
                            "button[type='submit']"
                        )
                        if await submit_btn.count() > 0:
                            await submit_btn.first.click()
                            print("Submit clicked")
                        else:
                            await code_input.first.press("Enter")
                            print("Enter pressed")

                        await asyncio.sleep(3)
                        await page.screenshot(path=QR_FILE, full_page=False)
                        os.remove(CODE_FILE)

                        # 等登录完成
                        print("Waiting for login after code...")
                        logged_in = await wait_for_login(context, page, 30)
                        break

            if not logged_in:
                status = "TIMEOUT" if "TIMEOUT" not in (open(STATUS_FILE).read()) else open(STATUS_FILE).read()
                if "TIMEOUT" not in status:
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

            # 写入 base_config.py
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

        except Exception as e:
            print(f"Error: {e}")
            write_status(f"ERROR:{e}")
            await page.screenshot(path=QR_FILE, full_page=False)
        finally:
            await browser.close()


asyncio.run(main())
