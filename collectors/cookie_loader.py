"""加载用户浏览器导出的Cookie，注入requests session"""
import json
from pathlib import Path

COOKIE_FILE = Path(__file__).parent.parent / "config" / "cookies.json"


def load_for_site(site_id):
    """返回 {cookie_name: cookie_value}"""
    try:
        with open(COOKIE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data.get(site_id, {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def apply_cookies(session, site_id):
    """将cookie注入到requests session"""
    cookies = load_for_site(site_id)
    for name, value in cookies.items():
        session.cookies.set(name, value, domain=get_domain(site_id))
    return len(cookies)


def get_domain(site_id):
    return {
        "boss_zhipin": ".zhipin.com",
        "zbj_demand": ".zbj.com",
        "producthunt": ".producthunt.com",
    }.get(site_id, "")


if __name__ == "__main__":
    for sid in ["boss_zhipin", "zbj_demand", "producthunt"]:
        c = load_for_site(sid)
        print(f"{sid}: {len(c)} cookies")
        if c:
            print(f"  示例: {list(c.keys())[:5]}")
