"""
XHS Phone Login — Playwright 手机验证码登录并保存 cookie
用法: python3 _xhs_phone_login.py <country_code> <phone_number> [timeout]

流程:
1. 通过代理打开 XHS → 切换到手机登录
2. 选择国家码 + 输入手机号 → 发送验证码
3. 写 NEED_CODE → 等 /tmp/xhs_verify_code 文件
4. 填入验证码 → 点击登录
5. 提取 cookies → 保存到 base_config.py → 写 SUCCESS
"""
import asyncio
import os
import re
import sys
import time

COUNTRY_CODE = sys.argv[1] if len(sys.argv) > 1 else "+1"
PHONE = sys.argv[2] if len(sys.argv) > 2 else ""
TIMEOUT = int(sys.argv[3]) if len(sys.argv) > 3 else 300

if not PHONE:
    print("Usage: python3 _xhs_phone_login.py <country_code> <phone> [timeout]")
    sys.exit(1)

MC_DIR = "/opt/mediacrawler"
SCREENSHOT = "/tmp/xhs_qr.png"  # 复用同一个截图路径
STATUS_FILE = "/tmp/xhs_login_status"
CODE_FILE = "/tmp/xhs_verify_code"

# 代理配置
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


def write_status(s):
    with open(STATUS_FILE, "w") as f:
        f.write(s)
    print(f"[STATUS] {s}")


async def main():
    from playwright.async_api import async_playwright

    write_status("STARTING")
    if os.path.exists(CODE_FILE):
        os.remove(CODE_FILE)

    print(f"Phone: {COUNTRY_CODE} {PHONE}")
    print(f"Proxy: {TUNNEL_HOST}:{TUNNEL_PORT}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            proxy={
                "server": f"http://{TUNNEL_HOST}:{TUNNEL_PORT}",
                "username": TUNNEL_USER,
                "password": TUNNEL_PWD,
            },
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
            await page.screenshot(path=SCREENSHOT)

            # 点击登录按钮（如果需要）
            login_btn = page.locator("text=登录")
            if await login_btn.count() > 0:
                await login_btn.first.click()
                await asyncio.sleep(2)
                await page.screenshot(path=SCREENSHOT)
                print("Login dialog opened")

            # 切换到手机号登录（点击"手机号登录"标签）
            phone_tab = page.locator(
                "text=手机号登录, "
                "text=其他方式登录, "
                "[class*='phone'], "
                "text=手机号"
            )
            if await phone_tab.count() > 0:
                await phone_tab.first.click()
                await asyncio.sleep(1)
                print("Switched to phone login tab")

            await page.screenshot(path=SCREENSHOT)

            # 选择国家码（如果不是默认的 +86 且需要切换）
            if COUNTRY_CODE != "+86":
                # 找到国家码选择器并点击
                country_selector = page.locator(
                    "[class*='country'], "
                    "[class*='area-code'], "
                    "[class*='area_code'], "
                    "span:has-text('86')"
                )
                if await country_selector.count() > 0:
                    await country_selector.first.click()
                    await asyncio.sleep(1)
                    print("Country code selector opened")
                    await page.screenshot(path=SCREENSHOT)

                    # 查找目标国家码
                    target_code = COUNTRY_CODE.lstrip("+")
                    # 先试搜索框
                    search_input = page.locator(
                        "input[placeholder*='搜索'], "
                        "input[placeholder*='search'], "
                        "input[placeholder*='国家']"
                    )
                    if await search_input.count() > 0:
                        # 用国家码数字搜索
                        await search_input.first.fill(target_code)
                        await asyncio.sleep(1)
                        await page.screenshot(path=SCREENSHOT)

                    # 点击包含目标国家码的选项
                    # 用 XPath 文本匹配，避免 CSS 选择器中 + 号的问题
                    option = page.locator(
                        f"xpath=//span[contains(text(),'+{target_code}')] | "
                        f"//div[contains(text(),'+{target_code}')] | "
                        f"//li[contains(text(),'+{target_code}')]"
                    )
                    if await option.count() > 0:
                        await option.first.click()
                        print(f"Selected country code +{target_code}")
                    else:
                        print(f"WARNING: Could not find +{target_code} option")

                    await asyncio.sleep(1)

            await page.screenshot(path=SCREENSHOT)

            # 输入手机号
            phone_input = page.locator(
                "input[placeholder*='手机号'], "
                "input[placeholder*='phone'], "
                "input[type='tel'], "
                "input[name='phone']"
            )
            if await phone_input.count() > 0:
                await phone_input.first.fill(PHONE)
                print(f"Phone number entered: {PHONE}")
                await asyncio.sleep(0.5)
            else:
                print("ERROR: Cannot find phone input")
                await page.screenshot(path=SCREENSHOT)
                write_status("ERROR_NO_PHONE_INPUT")
                await browser.close()
                return

            await page.screenshot(path=SCREENSHOT)

            # 同意协议（如果有勾选框）
            agree_check = page.locator(
                "input[type='checkbox'], "
                "[class*='agree'], "
                "[class*='checkbox'], "
                "[class*='protocol']"
            )
            if await agree_check.count() > 0:
                try:
                    await agree_check.first.click()
                    print("Agreement checkbox clicked")
                    await asyncio.sleep(0.5)
                except Exception:
                    pass

            # 点击发送验证码
            send_code_btn = page.locator(
                "text=发送验证码, "
                "text=获取验证码, "
                "text=发送, "
                "text=获取, "
                "button:has-text('验证码'), "
                "button:has-text('发送')"
            )
            if await send_code_btn.count() > 0:
                await send_code_btn.first.click()
                print("Send verification code button clicked")
                await asyncio.sleep(2)
            else:
                # 也许需要先点登录按钮触发验证码发送
                login_submit = page.locator(
                    "button:has-text('登录'), "
                    "button[type='submit']"
                )
                if await login_submit.count() > 0:
                    await login_submit.first.click()
                    print("Login button clicked (may trigger code sending)")
                    await asyncio.sleep(2)

            await page.screenshot(path=SCREENSHOT)
            write_status("CODE_SENT")
            print("Verification code should be sent. Waiting for code input...")

            # 等待验证码文件
            write_status("NEED_CODE")
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
                await browser.close()
                return

            print(f"Got verification code: {code}")

            # 找到验证码输入框并填入
            code_input = page.locator(
                "input[placeholder*='验证码'], "
                "input[placeholder*='验证'], "
                "input[placeholder*='code']"
            )
            if await code_input.count() > 0:
                await code_input.first.fill(code)
                print("Verification code entered")
            else:
                # 可能验证码和手机号在同一个流程里
                # 尝试所有空的 input
                all_inputs = page.locator("input:not([type='checkbox'])")
                count = await all_inputs.count()
                for i in range(count):
                    val = await all_inputs.nth(i).input_value()
                    if not val or len(val) < 3:
                        await all_inputs.nth(i).fill(code)
                        print(f"Code entered in input #{i}")
                        break

            await asyncio.sleep(0.5)
            await page.screenshot(path=SCREENSHOT)

            # 点击登录
            login_btn = page.locator(
                "button:has-text('登录'), "
                "button[type='submit'], "
                "button:has-text('确认')"
            )
            if await login_btn.count() > 0:
                await login_btn.first.click()
                print("Login button clicked")
            else:
                await code_input.first.press("Enter")
                print("Enter pressed")

            await asyncio.sleep(5)
            await page.screenshot(path=SCREENSHOT)

            # 检查是否还有安全验证 QR
            security_qr = page.locator("text=Security Verification, text=安全验证")
            if await security_qr.count() > 0:
                print("Security verification QR detected, waiting...")
                write_status("SECURITY_QR")
                # 等最多 120 秒
                sec_start = time.time()
                while time.time() - sec_start < 120:
                    await asyncio.sleep(3)
                    await page.screenshot(path=SCREENSHOT)
                    if await security_qr.count() == 0:
                        print("Security verification passed")
                        break

            # 等待登录完成
            print("Checking login status...")
            await asyncio.sleep(3)
            cookies = await context.cookies()

            login_names = {
                "galaxy_creator_session_id",
                "access-token-creator.xiaohongshu.com",
                "x-user-id-creator.xiaohongshu.com",
            }
            found = [c["name"] for c in cookies if c["name"] in login_names]
            ws = next((c for c in cookies if c["name"] == "web_session"), None)
            ws_ok = ws and len(ws["value"]) > 60

            if not found and not ws_ok:
                # 再等一会
                for _ in range(10):
                    await asyncio.sleep(3)
                    cookies = await context.cookies()
                    found = [c["name"] for c in cookies if c["name"] in login_names]
                    ws = next((c for c in cookies if c["name"] == "web_session"), None)
                    ws_ok = ws and len(ws["value"]) > 60
                    if found or ws_ok:
                        break

            if not found and not ws_ok:
                print("Login not detected after code submission")
                await page.screenshot(path=SCREENSHOT)
                write_status("LOGIN_FAILED")
                await browser.close()
                return

            print(f"Login confirmed! cookies: {found}, ws_ok: {ws_ok}")

            # 提取并保存 cookies
            await asyncio.sleep(2)
            cookies = await context.cookies()
            cookie_str = "; ".join(
                f'{c["name"]}={c["value"]}'
                for c in cookies
                if "xiaohongshu" in c.get("domain", "")
            )

            if not cookie_str:
                print("ERROR: No XHS cookies")
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

            # 清理
            if os.path.exists(CODE_FILE):
                os.remove(CODE_FILE)

        except Exception as e:
            print(f"Error: {e}")
            await page.screenshot(path=SCREENSHOT)
            write_status(f"ERROR:{e}")
        finally:
            await browser.close()


asyncio.run(main())
