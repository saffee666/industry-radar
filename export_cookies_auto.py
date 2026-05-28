#!/usr/bin/env python3
"""一键提取浏览器Cookie到config/cookies.json

使用前：关闭所有Chrome窗口
然后：python export_cookies_auto.py
提取完会自动关闭Chrome
"""
import json, subprocess, time, os, sys
from pathlib import Path

TARGETS = {
    "boss_zhipin": "https://www.zhipin.com/",
    "zbj_demand": "https://www.zbj.com/",
    "producthunt": "https://www.producthunt.com/",
}

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
PORT = 9222
HERE = Path(__file__).parent


def check_chrome_running():
    """检查Chrome是否在运行"""
    import subprocess
    result = subprocess.run(
        ['tasklist', '/FI', 'IMAGENAME eq chrome.exe', '/NH'],
        capture_output=True, text=True
    )
    return 'chrome.exe' in result.stdout


def launch_chrome():
    """启动Chrome调试模式"""
    cmd = [
        CHROME,
        f'--remote-debugging-port={PORT}',
        f'--user-data-dir={USER_DATA}',
        '--no-first-run',
        '--no-default-browser-check',
        'about:blank',  # 打开空白页
    ]
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def extract_via_cdp():
    """通过CDP协议提取cookie"""
    import requests as req

    # 等CDP就绪
    for i in range(15):
        time.sleep(2)
        try:
            resp = req.get(f'http://127.0.0.1:{PORT}/json', timeout=3)
            pages = resp.json()
            for p in pages:
                if p.get('type') == 'page':
                    ws_url = p['webSocketDebuggerUrl']
                    break
            else:
                continue
            break
        except Exception:
            continue
    else:
        print("错误: CDP连接超时")
        return None

    import websocket

    results = {}
    for site_id, url in TARGETS.items():
        try:
            ws = websocket.create_connection(ws_url, timeout=15)

            def send(method, params=None):
                ws.send(json.dumps({"id": 1, "method": method, "params": params or {}}))
                return json.loads(ws.recv())

            send("Page.enable")
            send("Network.enable")
            send("Page.navigate", {"url": url})
            time.sleep(5)  # 等页面加载

            result = send("Network.getCookies")
            ws.close()

            cookies = {}
            for c in result.get("result", {}).get("cookies", []):
                cookies[c["name"]] = c["value"]

            print(f"  [{site_id}] {len(cookies)} 个cookie")
            results[site_id] = cookies
        except Exception as e:
            print(f"  [{site_id}] 失败: {e}")
            results[site_id] = {}

    return results


def main():
    print("=== 一键导出浏览器Cookie ===\n")

    if not os.path.exists(CHROME):
        print(f"未找到Chrome: {CHROME}")
        print("请确认Chrome已安装")
        sys.exit(1)

    # 检查Chrome是否在运行
    if check_chrome_running():
        print("检测到Chrome正在运行。")
        print("请关闭所有Chrome窗口后按Enter继续...")
        input()
        time.sleep(2)
        if check_chrome_running():
            print("Chrome仍在运行！请关闭后重试。")
            sys.exit(1)

    print("启动Chrome（调试模式）...")
    proc = launch_chrome()
    time.sleep(3)

    try:
        print("提取Cookie中...\n")
        cookies = extract_via_cdp()

        if cookies is None:
            print("提取失败")
            return

        # 保存
        cookie_path = HERE / "config" / "cookies.json"
        cookie_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cookie_path, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)

        total = sum(len(v) for v in cookies.values())
        print(f"\n完成！{total} 个cookie保存到 {cookie_path}")

    finally:
        print("关闭Chrome...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("完成。现在可以重新打开Chrome了。")


if __name__ == "__main__":
    main()
