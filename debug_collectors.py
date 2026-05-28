#!/usr/bin/env python3
"""调试挂掉的采集器"""
import requests, json, re, sys
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def test(url, name, method="GET", data=None):
    try:
        if method == "POST":
            resp = requests.post(url, headers=HEADERS, json=data, timeout=15)
        else:
            resp = requests.get(url, headers=HEADERS, timeout=15)
        return resp.status_code, len(resp.text), resp.text[:300]
    except Exception as e:
        return 0, 0, str(e)[:200]

# === 36氪 ===
print("=== 36氪 ===")
urls_36kr = [
    "https://gateway.36kr.com/api/mis/nav/home/nav/tech",
    "https://36kr.com/api/info-flow/newsflash_news?b_id=0&per_page=20",
    "https://36kr.com/",
]
for url in urls_36kr:
    code, length, preview = test(url, "36kr")
    print(f"  [{code}] len={length} {url}")
    if code == 200 and length > 500:
        try:
            data = json.loads(preview) if preview.startswith("{") else None
            if data:
                print(f"    JSON keys: {list(data.keys())[:10]}")
        except:
            pass

# === 虎嗅 ===
print("\n=== 虎嗅 ===")
urls_hx = [
    "https://www.huxiu.com/v2_action/article_list",
    "https://www.huxiu.com/",
]
for url in urls_hx:
    code, length, preview = test(url, "虎嗅")
    print(f"  [{code}] len={length} {url}")
    if "article" in preview.lower() and length > 500:
        # Try to extract some content structure
        pass

# === 百度热搜 ===
print("\n=== 百度热搜 ===")
urls_bd = [
    "https://top.baidu.com/board?tab=realtime",
    "https://top.baidu.com/api/board?tab=realtime",
]
for url in urls_bd:
    code, length, preview = test(url, "百度")
    print(f"  [{code}] len={length} {url}")
    if "word" in preview.lower() or "hot" in preview.lower():
        print(f"    Looks promising")
        # Try to find data
        if "__NEXT_DATA__" in preview:
            print("    Found __NEXT_DATA__")
        if "hotScore" in preview:
            print("    Found hotScore")

# === GitHub ===
print("\n=== GitHub ===")
code, length, preview = test("https://api.github.com/search/repositories?q=stars:>1000&sort=stars&per_page=5", "GitHub API")
print(f"  [{code}] len={length}")
if code == 200:
    data = json.loads(preview)
    items = data.get("items", [])
    print(f"  Items: {len(items)}")
    for item in items[:3]:
        print(f"    - {item.get('full_name')}")

# === Google Trends ===
print("\n=== Google Trends ===")
code, length, preview = test("https://trends.google.com/trending/rss?geo=US&hours=24", "GTrends")
print(f"  [{code}] len={length}")

# === Boss直聘 ===
print("\n=== Boss直聘 ===")
code, length, preview = test("https://www.zhipin.com/wapi/zpgeek/search/joblist.json?query=AI&city=100010000&page=1&pageSize=5", "Boss")
print(f"  [{code}] len={length}")
if code == 200:
    try:
        data = json.loads(preview)
        print(f"  Keys: {list(data.keys())[:10]}")
    except:
        print(f"  Not JSON: {preview[:100]}")
