#!/usr/bin/env python3
"""服务端部署验证 + 每日采集执行脚本"""
import json, sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print(f"[{datetime.now()}] 行业雷达采集开始")

signals = []

# 微博热搜
try:
    from collectors.search_trends import _weibo_hot
    s = _weibo_hot()
    signals.extend([x.to_dict() if hasattr(x, "to_dict") else x for x in s])
    print(f"  微博热搜: {len(s)} 条")
except Exception as e:
    print(f"  微博热搜: 失败 - {e}")

# B站热门
try:
    from collectors.chinese_platforms import _bilibili_hot
    s = _bilibili_hot()
    signals.extend([x.to_dict() if hasattr(x, "to_dict") else x for x in s])
    print(f"  B站热门: {len(s)} 条")
except Exception as e:
    print(f"  B站热门: 失败 - {e}")

# HN
try:
    from collectors.tech_communities import _hackernews
    s = _hackernews()
    signals.extend([x.to_dict() if hasattr(x, "to_dict") else x for x in s])
    print(f"  Hacker News: {len(s)} 条")
except Exception as e:
    print(f"  Hacker News: 失败 - {e}")

# 36氪
try:
    from collectors.policy_media import _36kr
    s = _36kr()
    signals.extend([x.to_dict() if hasattr(x, "to_dict") else x for x in s])
    print(f"  36氪: {len(s)} 条")
except Exception as e:
    print(f"  36氪: 失败 - {e}")

# 爱范儿
try:
    from collectors.policy_media import _ifanr
    s = _ifanr()
    signals.extend([x.to_dict() if hasattr(x, "to_dict") else x for x in s])
    print(f"  爱范儿: {len(s)} 条")
except Exception as e:
    print(f"  爱范儿: 失败 - {e}")

# 百度热搜
try:
    from collectors.search_trends import _baidu_hot
    s = _baidu_hot()
    signals.extend([x.to_dict() if hasattr(x, "to_dict") else x for x in s])
    print(f"  百度热搜: {len(s)} 条")
except Exception as e:
    print(f"  百度热搜: 失败 - {e}")

# 抖音热搜
try:
    from collectors.chinese_platforms import _douyin_hot
    s = _douyin_hot()
    signals.extend([x.to_dict() if hasattr(x, "to_dict") else x for x in s])
    print(f"  抖音热搜: {len(s)} 条")
except Exception as e:
    print(f"  抖音热搜: 失败 - {e}")

# GitHub Trending
try:
    from collectors.tech_communities import _gh_trending
    s = _gh_trending()
    signals.extend([x.to_dict() if hasattr(x, "to_dict") else x for x in s])
    print(f"  GitHub: {len(s)} 条")
except Exception as e:
    print(f"  GitHub: 失败 - {e}")

# V2EX 创意
try:
    from collectors.tech_communities import _v2ex
    s = _v2ex("creative")
    signals.extend([x.to_dict() if hasattr(x, "to_dict") else x for x in s])
    print(f"  V2EX创意: {len(s)} 条")
except Exception as e:
    print(f"  V2EX创意: 失败 - {e}")

# V2EX 分享
try:
    from collectors.tech_communities import _v2ex
    s = _v2ex("share")
    signals.extend([x.to_dict() if hasattr(x, "to_dict") else x for x in s])
    print(f"  V2EX分享: {len(s)} 条")
except Exception as e:
    print(f"  V2EX分享: 失败 - {e}")

# 少数派
try:
    from collectors.chinese_platforms import _sspai
    s = _sspai()
    signals.extend([x.to_dict() if hasattr(x, "to_dict") else x for x in s])
    print(f"  少数派: {len(s)} 条")
except Exception as e:
    print(f"  少数派: 失败 - {e}")

# 晚点
try:
    from collectors.policy_media import _latepost
    s = _latepost()
    signals.extend([x.to_dict() if hasattr(x, "to_dict") else x for x in s])
    print(f"  晚点: {len(s)} 条")
except Exception as e:
    print(f"  晚点: 失败 - {e}")

# TechCrunch
try:
    from collectors.policy_media import _techcrunch
    s = _techcrunch()
    signals.extend([x.to_dict() if hasattr(x, "to_dict") else x for x in s])
    print(f"  TechCrunch: {len(s)} 条")
except Exception as e:
    print(f"  TechCrunch: 失败 - {e}")

# === 以下需要浏览器登录Cookie ===

# Boss直聘（需cookie）
try:
    from collectors.job_markets import _boss
    s = _boss()
    signals.extend([x.to_dict() if hasattr(x, "to_dict") else x for x in s])
    print(f"  Boss直聘: {len(s)} 条")
except Exception as e:
    print(f"  Boss直聘: 失败 - {e}")

# 猪八戒（需cookie）
try:
    from collectors.freelance_markets import _zbj
    s = _zbj()
    signals.extend([x.to_dict() if hasattr(x, "to_dict") else x for x in s])
    print(f"  猪八戒: {len(s)} 条")
except Exception as e:
    print(f"  猪八戒: 失败 - {e}")

# 掘金
try:
    from collectors.tech_communities import _juejin
    s = _juejin()
    signals.extend([x.to_dict() if hasattr(x, "to_dict") else x for x in s])
    print(f"  掘金: {len(s)} 条")
except Exception as e:
    print(f"  掘金: 失败 - {e}")

# 华尔街见闻
try:
    from collectors.policy_media import _wallstreetcn
    s = _wallstreetcn()
    signals.extend([x.to_dict() if hasattr(x, "to_dict") else x for x in s])
    print(f"  华尔街见闻: {len(s)} 条")
except Exception as e:
    print(f"  华尔街见闻: 失败 - {e}")

# 雪球
try:
    from collectors.search_trends import _xueqiu_hot
    s = _xueqiu_hot()
    signals.extend([x.to_dict() if hasattr(x, "to_dict") else x for x in s])
    print(f"  雪球: {len(s)} 条")
except Exception as e:
    print(f"  雪球: 失败 - {e}")

# 虎嗅
try:
    from collectors.policy_media import _huxiu
    s = _huxiu()
    signals.extend([x.to_dict() if hasattr(x, "to_dict") else x for x in s])
    print(f"  虎嗅: {len(s)} 条")
except Exception as e:
    print(f"  虎嗅: 失败 - {e}")

# Product Hunt（需cookie）
try:
    from collectors.tech_communities import _producthunt
    s = _producthunt()
    signals.extend([x.to_dict() if hasattr(x, "to_dict") else x for x in s])
    print(f"  Product Hunt: {len(s)} 条")
except Exception as e:
    print(f"  Product Hunt: 失败 - {e}")

print(f"\n总采集: {len(signals)} 条")

if not signals:
    print("未采集到信号，退出")
    sys.exit(0)

# 去重
from processors.dedup import deduplicate
unique = deduplicate(signals)
print(f"去重后: {len(unique)} 条")

# 分类
from processors.classifier import classify_signals
classified = classify_signals(unique)

# 打分
from processors.scorer import score_signals
scored = score_signals(classified)

# 统计
from collections import Counter
inds = Counter(s.get("industry_name", "?") for s in scored)
types = Counter(s.get("signal_type_name", "?") for s in scored)
print(f"行业: {dict(inds)}")
print(f"类型: {dict(types)}")

# 保存
date_str = datetime.now().strftime("%Y-%m-%d")
Path("D:/claude产出/industry-radar/raw").mkdir(parents=True, exist_ok=True)
with open(f"D:/claude产出/industry-radar/raw/signals_{date_str}.json", "w", encoding="utf-8") as f:
    json.dump(signals, f, ensure_ascii=False, indent=2)
with open(f"D:/claude产出/industry-radar/raw/processed_{date_str}.json", "w", encoding="utf-8") as f:
    json.dump(scored, f, ensure_ascii=False, indent=2)

# 晨报
from reports.morning_brief import generate_brief
brief_path = generate_brief(scored, date_str)
print(f"晨报: {brief_path}")

print(f"[{datetime.now()}] 采集完成")
