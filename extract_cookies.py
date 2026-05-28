#!/usr/bin/env python3
"""从浏览器提取登录Cookie，用于Boss直聘/猪八戒/Product Hunt采集"""
import json
import sys
from pathlib import Path

TARGETS = {
    "zhipin.com": "boss_zhipin",
    "zbj.com": "zbj_demand",
    "producthunt.com": "producthunt",
}

def extract_from_chrome():
    """从Chrome/Edge提取"""
    try:
        import browser_cookie3
    except ImportError:
        print("请先安装: pip install browser-cookie3")
        return None

    results = {}

    # 尝试 Chrome → Edge → Brave
    browsers = []
    try:
        browsers.append(("Chrome", browser_cookie3.chrome))
    except Exception:
        pass
    try:
        browsers.append(("Edge", browser_cookie3.edge))
    except Exception:
        pass
    try:
        browsers.append(("Brave", browser_cookie3.brave))
    except Exception:
        pass

    if not browsers:
        print("未找到支持的浏览器（Chrome/Edge/Brave）")
        return None

    for browser_name, loader in browsers:
        try:
            cookies = loader()
            for cookie in cookies:
                domain = cookie.domain.lstrip(".")
                for target_domain, site_id in TARGETS.items():
                    if target_domain in domain:
                        if site_id not in results:
                            results[site_id] = {}
                        results[site_id][cookie.name] = cookie.value
            if results:
                print(f"[{browser_name}] 提取到 {len(results)} 个站点的cookie")
                break
        except Exception as e:
            print(f"[{browser_name}] 读取失败: {e}")
            continue

    return results if results else None


def extract_manual():
    """手动模式：让用户在浏览器Console运行JS获得cookie"""
    print("""
=== 手动提取Cookie ===
在浏览器中打开对应网站，按F12打开开发者工具，在Console中粘贴以下代码：

---
javascript:(function(){
  var c = document.cookie.split(';').map(function(x){
    var p = x.trim().split('=');
    return [p[0], p.slice(1).join('=')];
  });
  var r = {};
  c.forEach(function(x){ if(x[0]) r[x[0]] = x[1]; });
  console.log(JSON.stringify(r, null, 2));
  copy(JSON.stringify(r));
})();
---

运行后cookie已复制到剪贴板，粘贴到下方文件中保存。
""")
    return None


def save_cookies(cookies, path="config/cookies.json"):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    print(f"Cookie已保存到 {path}")
    return path


def load_cookies(site_id, path="config/cookies.json"):
    """加载指定站点的cookie，返回dict"""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get(site_id, {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


if __name__ == "__main__":
    print("=== 浏览器Cookie提取工具 ===\n")

    # 先试自动提取
    cookies = extract_from_chrome()

    if cookies:
        for site_id, data in cookies.items():
            print(f"\n[{site_id}] {len(data)} 个cookie可用")

        path = str(Path(__file__).parent / "config" / "cookies.json")
        save_cookies(cookies, path)
        print(f"\n成功！{len(cookies)} 个站点cookie已保存")
    else:
        print("\n自动提取失败，需手动操作。")
        extract_manual()
