"""招聘市场采集器: Boss直聘, 猎聘"""

import re
import time
import random
import requests
from pathlib import Path
from .base import make_signal

CONFIG_PATH = Path(__file__).parent.parent / "config" / "sources.yaml"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

MOBILE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"


def _load_sources():
    import yaml
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return [s for s in config["sources"]["job_markets"] if s.get("enabled")]


def _boss():
    """Boss直聘 — 公开SEO端点（无需登录）

    返回热门岗位、热门城市、热门公司等招聘趋势信号。
    API: wapi/zpgeek/search/job/seo/data.json
    """
    signals = []
    cities = {"101030100": "上海", "101280600": "深圳", "101210100": "杭州", "101280100": "广州", "101200100": "武汉", "101230100": "福州"}

    for city_code, city_name in cities.items():
        time.sleep(random.uniform(2, 5))
        try:
            # 先试移动UA（云服务器IP更容易过）
            resp = requests.get(
                "https://www.zhipin.com/wapi/zpgeek/search/job/seo/data.json",
                params={"city": city_code, "jobCity": city_code},
                headers={"User-Agent": MOBILE_UA, "Referer": "https://www.zhipin.com/"},
                timeout=15
            )
            if resp.status_code == 200 and resp.json().get("code") == 35:
                # 移动UA也被封，再试桌面UA
                time.sleep(2)
                resp = requests.get(
                    "https://www.zhipin.com/wapi/zpgeek/search/job/seo/data.json",
                    params={"city": city_code, "jobCity": city_code},
                    headers={**HEADERS, "Referer": "https://www.zhipin.com/"},
                    timeout=15
                )
            if resp.status_code != 200:
                print(f"    Boss[{city_name}] HTTP {resp.status_code}")
                continue
            data = resp.json()
            if data.get("code") != 0:
                print(f"    Boss[{city_name}] API code={data.get('code')} msg={data.get('message','')}")
                continue

            seo = data.get("zpData", {}).get("seoData")
            if not seo:
                print(f"    Boss[{city_name}] seoData为空, keys={list(data.keys())[:5]}")
                continue
            hot_jobs = seo.get("hotJobs", [])
            hot_brands = seo.get("hotBrands", [])

            # 热门岗位趋势
            for job in hot_jobs[:10]:
                name = job.get("name", "")
                if name:
                    signals.append(make_signal(
                        title=f"{city_name}热门岗位: {name}",
                        url=f"https://www.zhipin.com/web/geek/job?city={city_code}&query={name}",
                        source="boss_zhipin",
                        source_name="Boss直聘",
                        category="job_markets",
                        language="zh",
                        snippet=f"{city_name}地区「{name}」为当前热门招聘方向",
                        raw_text=f"{city_name} hot job: {name}",
                        metadata={"city": city_name, "job_type": name}
                    ))

            # 热门公司
            for brand in hot_brands[:5]:
                name = brand.get("name", "")
                if name:
                    signals.append(make_signal(
                        title=f"{city_name}热门雇主: {name}",
                        url=f"https://www.zhipin.com/web/geek/job?city={city_code}&query={name}",
                        source="boss_zhipin",
                        source_name="Boss直聘",
                        category="job_markets",
                        language="zh",
                        snippet=f"{city_name}地区「{name}」正在积极招聘",
                        raw_text=f"{city_name} hot brand: {name}",
                        metadata={"city": city_name, "brand": name}
                    ))

        except Exception as e:
            print(f"   Boss({city_name})异常: {e}")
            continue

    return signals


def _liepin():
    """猎聘 - 高端人才需求趋势"""
    signals = []
    keywords = ["AI大模型", "出海", "跨境电商", "新能源", "芯片", "机器人"]

    for kw in keywords[:6]:
        try:
            resp = requests.get(
                "https://www.liepin.com/zhaopin/",
                params={"key": kw, "dqs": "010"},
                headers={**HEADERS, "Referer": "https://www.liepin.com/"},
                timeout=15
            )
            if resp.status_code == 200:
                html = resp.text
                # 提取岗位数量
                count_match = re.search(r'data-total="(\d+)"', html)
                total = int(count_match.group(1)) if count_match else 0

                # 提取薪资范围
                salary_matches = re.findall(r'<span class="text-warning">([^<]+)</span>', html)
                top_salaries = salary_matches[:3] if salary_matches else []

                if total > 0:
                    signals.append(make_signal(
                        title=f"「{kw}」猎聘岗位: {total}个",
                        url=f"https://www.liepin.com/zhaopin/?key={kw}",
                        source="liepin",
                        source_name="猎聘",
                        category="job_markets",
                        language="zh",
                        snippet=f"{kw}相关高端岗位 {total} 个",
                        metadata={"keyword": kw, "job_count": total, "top_salaries": top_salaries}
                    ))
        except Exception as e:
            print(f"   猎聘({kw})异常: {e}")
            continue

    return signals


def collect_job_markets():
    """采集所有招聘市场信号源"""
    import yaml
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    sources = [s for s in config["sources"]["job_markets"] if s.get("enabled")]

    all_signals = []

    collectors = {
        "boss_zhipin": _boss,
        "liepin": _liepin,
    }

    for src in sources:
        sid = src["id"]
        if sid in collectors:
            try:
                signals = collectors[sid]()
                all_signals.extend(signals)
                print(f"   [{src['name']}] {len(signals)} 条")
            except Exception as e:
                print(f"   [{src['name']}] 失败: {e}")

    return all_signals


if __name__ == "__main__":
    signals = collect_job_markets()
    for s in signals:
        print(f"  [{s.source_name}] {s.title[:60]}")
