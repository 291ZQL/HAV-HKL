
#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════╗
║         🎬 OK影视 - hhkan2 资源版              ║
║     影视聚合 · 搜索 · 解析 · 播放               ║
╚══════════════════════════════════════════════════╝

功能：
  ✅ 首页多分类推荐（电影/剧集/动漫/综艺/短剧）
  ✅ 关键词搜索
  ✅ 影片详情（评分、简介、演员）
  ✅ 多播放源解析
  ✅ 分集选择（连续剧）
  ✅ 直接播放链接提取（m3u8/mp4）
  
依赖：pip install requests beautifulsoup4
"""

import requests
import re
import json
import sys
import os
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse, quote, unquote

# ============================================================
#  配置
# ============================================================
BASE_URL = "https://www.hhkan2.com/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.hhkan2.com/",
}

# 分类配置（苹果CMS标准）
CATEGORIES = {
    "1":  {"name": "🎬 电影",     "icon": "🎬"},
    "2":  {"name": "📺 连续剧",   "icon": "📺"},
    "3":  {"name": "🎨 动漫",     "icon": "🎨"},
    "4":  {"name": "🎪 综艺纪录", "icon": "🎪"},
    "37": {"name": "📱 短剧",     "icon": "📱"},
}

CACHE_DIR = "/storage/emulated/0/Download/.okvideo_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# ============================================================
#  工具函数
# ============================================================

def log(msg, level="INFO"):
    """带时间戳的日志"""
    ts = datetime.now().strftime("%H:%M:%S")
    colors = {"INFO": "", "OK": "✅", "WARN": "⚠️", "ERR": "❌", "PLAY": "▶️"}
    icon = colors.get(level, "")
    print(f"  {icon} {msg}")

def fetch(url, timeout=15):
    """请求HTML"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 850:
            log(f"站点WAF拦截，尝试备用方式...", "WARN")
            return None
        log(f"HTTP {e.response.status_code}", "ERR")
        return None
    except Exception as e:
        log(f"{e}", "ERR")
        return None

def cache_get(key):
    """读取缓存"""
    path = os.path.join(CACHE_DIR, f"{key}.json")
    if os.path.exists(path):
        age = time.time() - os.path.getmtime(path)
        if age < 300:  # 5分钟缓存
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    return None

def cache_set(key, data):
    """写入缓存"""
    path = os.path.join(CACHE_DIR, f"{key}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

def clean_title(text):
    """清理HTML标签提取纯文本标题"""
    return re.sub(r'<[^>]+>', '', text).strip()

def extract_vod_ids(html):
    """提取页面中所有 voddetail 链接和标题"""
    items = []
    seen = set()
    pattern = re.compile(
        r'<a[^>]*href=["\'](/voddetail/(\d+)\.html)["\'][^>]*>(.*?)</a>',
        re.DOTALL
    )
    for m in pattern.finditer(html):
        link = m.group(1)
        vid = m.group(2)
        title = clean_title(m.group(3))
        if title and len(title) < 40 and title not in seen:
            seen.add(title)
            items.append({
                "id": vid,
                "title": title,
                "link": urljoin(BASE_URL, link),
            })
    return items

def extract_scores(html, items):
    """从文本中提取豆瓣评分和状态信息，匹配到items"""
    text = re.sub(r'<[^>]+>', '\n', html)
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    info_map = {}
    for i, line in enumerate(lines):
        # 豆瓣评分行
        sm = re.match(r'豆瓣[:：]([\d.]+)分', line)
        if sm:
            score = sm.group(1)
            name_line = ""
            j = i + 1
            while j < len(lines) and j < i + 4:
                l = lines[j]
                if re.match(r'^(正片|BT|HD|更新|已完结|全\d)', l):
                    j += 1
                    continue
                if len(l) < 30 and not re.match(r'^(豆瓣|https?://|更多|首页|电影|连续剧)', l):
                    name_line = l
                    break
                j += 1
            if name_line:
                info_map[name_line] = f"⭐{score}"

        # 状态行（更新/已完结/全N集）
        stm = re.match(r'(更新[至第]*[\d]+[集话]|已完结|全[\d]+集|更新预告片)', line)
        if stm:
            status = stm.group(1)
            k = i + 1
            while k < len(lines) and k < i + 3:
                l = lines[k]
                if len(l) < 30 and not re.match(r'^(豆瓣|正片|BT|HD|更新|已完结|全\d)', l):
                    if l not in info_map:
                        info_map[l] = f"[{status}]"
                    break
                k += 1

    for item in items:
        t = item["title"]
        for name, info in info_map.items():
            if name in t or t in name:
                if info.startswith("⭐"):
                    item["score"] = info
                else:
                    item["status"] = info
        if "score" not in item:
            item["score"] = ""
        if "status" not in item:
            item["status"] = ""

    return items


# ============================================================
#  核心API
# ============================================================

def get_homepage():
    """获取首页推荐内容"""
    log("正在获取首页...")
    html = fetch(BASE_URL)
    if not html:
        return []

    items = extract_vod_ids(html)
    items = extract_scores(html, items)

    # 去重
    seen = set()
    unique = []
    for item in items:
        if item["title"] not in seen:
            seen.add(item["title"])
            unique.append(item)

    log(f"首页共 {len(unique)} 部影片", "OK")
    return unique


def get_category(cat_id, page=1):
    """获取分类列表"""
    cat_info = CATEGORIES.get(cat_id, {"name": f"分类{cat_id}", "icon": "📁"})
    url = urljoin(BASE_URL, f"/vodtype/{cat_id}-{page}.html")

    log(f"正在获取{cat_info['name']} 第{page}页...")
    html = fetch(url)
    if not html:
        return []

    items = extract_vod_ids(html)
    items = extract_scores(html, items)

    log(f"共 {len(items)} 部", "OK")
    return items


def search(keyword, page=1):
    """搜索影片"""
    encoded = quote(keyword)
    url = f"{BASE_URL}vodsearch/{encoded}----------{page}---.html"

    log(f"搜索: \"{keyword}\" ...")
    html = fetch(url)
    if not html:
        # 尝试POST方式
        url2 = urljoin(BASE_URL, "vodsearch.html")
        try:
            resp = requests.post(url2, data={"wd": keyword, "submit": "search"},
                                headers=HEADERS, timeout=15)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            html = resp.text
        except:
            return []

    items = extract_vod_ids(html)
    items = extract_scores(html, items)

    if not items:
        log("未找到结果", "WARN")
    else:
        log(f"找到 {len(items)} 个结果", "OK")
    return items


def get_detail(vod_url):
    """
    获取影片详情，包括：
    - 标题、图片、简介、演员
    - 所有播放源及分集列表
    """
    vid = re.search(r'/voddetail/(\d+)\.html', vod_url)
    vid_str = vid.group(1) if vid else ""

    log(f"正在获取详情...")
    html = fetch(vod_url)
    if not html:
        return None

    detail = {
        "id": vid_str,
        "title": "",
        "pic": "",
        "desc": "",
        "actor": "",
        "director": "",
        "year": "",
        "area": "",
        "score": "",
        "sources": [],  # [ {name, episodes: [ {name, url}, ... ]}, ... ]
    }

    # 标题
    tm = re.search(r'<title>([^<]+)</title>', html)
    detail["title"] = clean_title(tm.group(1)) if tm else "未知"

    # 封面图
    pm = re.search(r'<img[^>]*class=["\'][^"\']*lazy[^"\']*["\'][^>]*data-original=["\']([^"\']+)["\']', html)
    if not pm:
        pm = re.search(r'<img[^>]*class=["\'][^"\']*pic[^"\']*["\'][^>]*src=["\']([^"\']+)["\']', html)
    detail["pic"] = pm.group(1) if pm else ""

    # 简介
    dm = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html)
    if dm:
        detail["desc"] = dm.group(1).strip()

    # 演员/导演等信息 - 苹果CMS常见结构
    info_patterns = {
        "导演": "director",
        "主演": "actor",
        "演员": "actor",
        "地区": "area",
        "年份": "year",
        "年代": "year",
        "语言": "lang",
        "豆瓣": "score",
    }
    for label, key in info_patterns.items():
        pm = re.search(rf'{label}[:：]\s*([^<\n]+)', html)
        if pm:
            detail[key] = pm.group(1).strip()

    # ---- 播放源和剧集解析 ----
    # 方法1: 查找隐藏的 playlist 输入框（苹果CMS常用）
    source_pattern = re.compile(
        r'<div[^>]*class=["\'][^"\']*play_source[^"\']*["\'][^>]*data-id=["\'](\d+)["\']'
    )
    source_name_pattern = re.compile(
        r'<div[^>]*class=["\'][^"\']*play_source[^"\']*["\'][^>]*.*?>.*?<strong[^>]*>(.*?)</strong>',
        re.DOTALL
    )

    # 方法2: 查找所有播放列表
    # 常见的苹果CMS结构: <ul class="playlist"> 或 id="playlist"
    playlist_sections = re.findall(
        r'<div[^>]*class=["\'][^"\']*play_source[^"\']*["\'][^>]*>.*?<ul[^>]*class=["\']playlist["\'][^>]*>(.*?)</ul>',
        html, re.DOTALL
    )

    source_names = source_name_pattern.findall(html)
    source_names = [clean_title(n) for n in source_names]

    if playlist_sections:
        for si, section in enumerate(playlist_sections):
            source_name = source_names[si] if si < len(source_names) else f"源{si+1}"
            # 提取剧集链接
            episodes = re.findall(
                r'<a[^>]*href=["\'](/vodplay/\d+-\d+-\d+\.html)["\'][^>]*>(.*?)</a>',
                section, re.DOTALL
            )
            ep_list = []
            for ep_link, ep_name in episodes:
                ep_name_clean = clean_title(ep_name)
                ep_list.append({
                    "name": ep_name_clean,
                    "url": urljoin(BASE_URL, ep_link),
                })

            if ep_list:
                detail["sources"].append({
                    "name": source_name,
                    "episodes": ep_list,
                })
    else:
        # 方法3: 从JS变量中提取
        js_match = re.search(r'var\s+player_llist\s*=\s*(\[[^\]]+\])', html)
        if js_match:
            try:
                import ast
                data = ast.literal_eval(js_match.group(1))
                if isinstance(data, list):
                    eps = []
                    for item in data:
                        if isinstance(item, (list, tuple)) and len(item) >= 2:
                            eps.append({"name": str(item[0]), "url": str(item[1])})
                    if eps:
                        detail["sources"].append({
                            "name": "默认源",
                            "episodes": eps,
                        })
            except:
                pass

        # 方法4: 查找iframe
        if not detail["sources"]:
            iframe = re.search(r'<iframe[^>]*src=["\']([^"\']+)["\']', html)
            if iframe:
                detail["sources"].append({
                    "name": "iframe播放",
                    "episodes": [{"name": "播放", "url": iframe.group(1)}],
                })

    total_eps = sum(len(s["episodes"]) for s in detail["sources"])
    log(f"{detail['title']} - {len(detail['sources'])}个源, {total_eps}集", "OK")

    return detail


def resolve_play_url(play_url, max_depth=3):
    """
    深度解析播放页，提取最终视频直链
    支持 m3u8 / mp4 / flv
    """
    if max_depth <= 0:
        return None

    log(f"解析播放地址...")
    html = fetch(play_url, timeout=10)
    if not html:
        return None

    # 查找视频直链
    patterns = [
        # 常见videojs/dplayer等
        r'url\s*[:=]\s*["\']([^"\']+\.(?:m3u8|mp4|flv)[^"\']*)["\']',
        r'src\s*[:=]\s*["\']([^"\']+\.(?:m3u8|mp4|flv)[^"\']*)["\']',
        r'video[^>]*src=["\']([^"\']+)["\']',
        r'<source[^>]*src=["\']([^"\']+)["\']',
        # JSON格式
        r'"url"\s*:\s*"([^"]+)"',
        r'"playurl"\s*:\s*"([^"]+)"',
        r'"link"\s*:\s*"([^"]+)"',
        r'"src"\s*:\s*"([^"]+)"',
        # JS变量
        r'var\s+url\s*=\s*["\']([^"\']+)["\']',
        r'var\s+play_url\s*=\s*["\']([^"\']+)["\']',
        # unicode编码
        r'\\u002F[^"\']*\\u002E(?:m3u8|mp4)[^"\']*',
    ]

    for pattern in patterns:
        m = re.search(pattern, html)
        if m:
            url = m.group(1)
            # unicode解码
            if '\\u' in url:
                url = url.encode('utf-8').decode('unicode_escape')
            if url.startswith('//'):
                url = 'https:' + url
            log(f"发现视频链接", "PLAY")
            return url

    # 递归解析iframe
    iframe = re.search(r'<iframe[^>]*src=["\']([^"\']+)["\']', html)
    if iframe:
        iframe_url = iframe.group(1)
        # 避免循环
        if iframe_url != play_url:
            log(f"进入内嵌播放器...")
            return resolve_play_url(iframe_url, max_depth - 1)

    # 查找302跳转
    try:
        resp = requests.get(play_url, headers=HEADERS, allow_redirects=True, timeout=10)
        final_url = resp.url
        if final_url != play_url and any(ext in final_url for ext in ['.m3u8', '.mp4', '.flv']):
            log(f"302跳转至视频链接", "PLAY")
            return final_url
    except:
        pass

    log("未能解析出视频直链", "WARN")
    return None


# ============================================================
#  UI 界面
# ============================================================

def print_header(title):
    """打印区块标题"""
    print()
    print(f"  {'=' * 48}")
    print(f"  {title}")
    print(f"  {'=' * 48}")

def print_video_list(items, start=1):
    """打印影片列表"""
    if not items:
        print("  (空)")
        return
    for i, item in enumerate(items[:30], start):
        score = item.get("score", "")
        status = item.get("status", "")
        tag = f"{score} " if score else ""
        tag += f"{status} " if status else ""
        print(f"  [{i:2d}] {tag}{item['title']}")
    if len(items) > 30:
        print(f"  ... 还有 {len(items) - 30} 部")


def print_detail(detail):
    """打印影片详情"""
    if not detail:
        return

    print()
    print(f"  {'─' * 48}")
    print(f"  🎬 {detail['title']}")

    if detail.get("score"):
        print(f"  ⭐ 豆瓣: {detail['score']}")
    if detail.get("year"):
        print(f"  📅 年份: {detail['year']}")
    if detail.get("area"):
        print(f"  🌍 地区: {detail['area']}")
    if detail.get("actor"):
        print(f"  👤 主演: {detail['actor'][:60]}")
    if detail.get("desc"):
        desc = detail["desc"][:200]
        print(f"  📝 简介: {desc}{'...' if len(detail['desc']) > 200 else ''}")

    # 显示播放源
    print(f"  {'─' * 48}")
    print(f"  📡 播放源:")
    for si, source in enumerate(detail["sources"], 1):
        eps = source["episodes"]
        print(f"    [{si}] {source['name']} ({len(eps)}集)")
        # 显示前10集
        ep_preview = eps[:10]
        preview_str = "  ".join([f"{e['name']}" for e in ep_preview])
        if preview_str:
            print(f"         {preview_str}")
        if len(eps) > 10:
            print(f"         ... 还有 {len(eps) - 10} 集")

    total = sum(len(s["episodes"]) for s in detail["sources"])
    print(f"  {'─' * 48}")
    print(f"  💡 共 {len(detail['sources'])} 个播放源, {total} 集")


# ============================================================
#  主菜单
# ============================================================

def main():
    print()
    print(f"  ╔{'═' * 46}╗")
    print(f"  ║     🎬 OK影视 · hhkan2 资源版              ║")
    print(f"  ║     影视聚合 · 一键搜索 · 解析播放          ║")
    print(f"  ╚{'═' * 46}╝")
    print(f"  📍 数据源: {BASE_URL}")

    current_list = []
    current_list_label = ""

    while True:
        print()
        print(f"  {'─' * 48}")
        print(f"  📋 主菜单")
        print(f"  {'─' * 48}")
        print(f"  [1] 🏠 首页推荐")
        print(f"  [2] 📂 分类浏览")
        print(f"  [3] 🔍 搜索影片")
        print(f"  [4] 👁 查看详情 / 获取播放")
        print(f"  [5] 🎯 快速搜索 + 播放")
        print(f"  [0] 🚪 退出")
        print(f"  {'─' * 48}")

        choice = input("  请选择 [0-5]: ").strip()

        if choice == "0":
            print("\n  👋 感谢使用 OK影视！再见！\n")
            break

        elif choice == "1":
            current_list = get_homepage()
            current_list_label = "首页推荐"
            print_header(f"🏠 {current_list_label}")
            print_video_list(current_list)

        elif choice == "2":
            print(f"\n  📂 分类列表:")
            for cid, cinfo in CATEGORIES.items():
                print(f"    [{cid}] {cinfo['icon']} {cinfo['name']}")
            cat_id = input("  选择分类编号: ").strip()
            if cat_id not in CATEGORIES:
                log("无效分类", "WARN")
                continue
            try:
                page = int(input("  页码 (默认1): ").strip() or "1")
            except:
                page = 1
            current_list = get_category(cat_id, page)
            current_list_label = CATEGORIES[cat_id]["name"]
            print_header(f"📂 {current_list_label}")
            print_video_list(current_list)

        elif choice == "3":
            keyword = input("  输入关键词: ").strip()
            if not keyword:
                continue
            current_list = search(keyword)
            current_list_label = f"搜索: {keyword}"
            print_header(f"🔍 {current_list_label}")
            print_video_list(current_list)

        elif choice == "4":
            if not current_list:
                log("请先在首页/分类/搜索中获取列表", "WARN")
                continue

            print_header(f"📋 {current_list_label} (前20条)")
            print_video_list(current_list[:20], 1)

            try:
                sel = int(input("  选择影片编号: ").strip())
                if sel < 1 or sel > len(current_list):
                    log("编号超出范围", "WARN")
                    continue
            except:
                log("无效输入", "WARN")
                continue

            item = current_list[sel - 1]
            detail = get_detail(item["link"])
            print_detail(detail)

            if not detail or not detail["sources"]:
                log("该影片暂无可用播放源", "WARN")
                continue

            # 选择播放源和剧集
            try:
                si = int(input(f"\n  选择播放源 [1-{len(detail['sources'])}]: ").strip())
                if si < 1 or si > len(detail["sources"]):
                    continue
                source = detail["sources"][si - 1]
            except:
                continue

            eps = source["episodes"]
            if len(eps) > 1:
                print(f"\n  📺 剧集列表 ({source['name']}):")
                # 分页显示
                page_size = 20
                total_pages = (len(eps) + page_size - 1) // page_size
                ep_page = 1
                while True:
                    start_idx = (ep_page - 1) * page_size
                    end_idx = min(start_idx + page_size, len(eps))
                    for i in range(start_idx, end_idx):
                        print(f"    [{i + 1:3d}] {eps[i]['name']}")
                    print(f"    第{ep_page}/{total_pages}页 (共{len(eps)}集)")
                    if total_pages > 1:
                        nav = input("  n下一页 p上一页 q退出 或直接输集数: ").strip().lower()
                        if nav == 'n' and ep_page < total_pages:
                            ep_page += 1
                            continue
                        elif nav == 'p' and ep_page > 1:
                            ep_page -= 1
                            continue
                        elif nav == 'q':
                            break
                        try:
                            ei = int(nav)
                            if 1 <= ei <= len(eps):
                                play_url = eps[ei - 1]["url"]
                                log(f"选集: {eps[ei - 1]['name']}", "OK")
                                video_url = resolve_play_url(play_url)
                                if video_url:
                                    print(f"\n  {'─' * 48}")
                                    print(f"  📺 播放地址:")
                                    print(f"  {video_url}")
                                    print(f"  {'─' * 48}")
                                    print(f"  💡 提示: 复制链接到 VLC / PotPlayer / 浏览器 播放")
                                    if video_url.endswith('.m3u8'):
                                        print(f"  💡 m3u8推荐: VLC / IINA / PotPlayer / MX Player")
                                    input("\n  按回车继续...")
                                break
                        except:
                            break
                    else:
                        try:
                            ei = int(input("  选择集数编号: ").strip())
                            if 1 <= ei <= len(eps):
                                play_url = eps[ei - 1]["url"]
                                log(f"选集: {eps[ei - 1]['name']}", "OK")
                                video_url = resolve_play_url(play_url)
                                if video_url:
                                    print(f"\n  {'─' * 48}")
                                    print(f"  📺 播放地址:")
                                    print(f"  {video_url}")
                                    print(f"  {'─' * 48}")
                                    print(f"  💡 提示: 复制链接到播放器播放")
                                    if video_url.endswith('.m3u8'):
                                        print(f"  💡 m3u8推荐: VLC / PotPlayer / MX Player")
                                    input("\n  按回车继续...")
                                break
                        except:
                            break
                    break
            else:
                # 单集(电影)
                play_url = eps[0]["url"]
                video_url = resolve_play_url(play_url)
                if video_url:
                    print(f"\n  {'─' * 48}")
                    print(f"  📺 播放地址:")
                    print(f"  {video_url}")
                    print(f"  {'─' * 48}")
                    print(f"  💡 提示: 复制链接到播放器播放")
                    if video_url.endswith('.m3u8'):
                        print(f"  💡 m3u8推荐: VLC / PotPlayer / MX Player")
                    input("\n  按回车继续...")

        elif choice == "5":
            keyword = input("  搜索关键词: ").strip()
            if not keyword:
                continue
            items = search(keyword)
            if items:
                first = items[0]
                log(f"自动获取: {first['title']}", "OK")
                detail = get_detail(first["link"])
                if detail and detail["sources"]:
                    source = detail["sources"][0]
                    if source["episodes"]:
                        play_url = source["episodes"][0]["url"]
                        ep_name = source["episodes"][0]["name"]
                        log(f"播放: {ep_name}", "PLAY")
                        video_url = resolve_play_url(play_url)
                        if video_url:
                            print(f"\n  {'─' * 48}")
                            print(f"  🎬 {detail['title']} - {ep_name}")
                            print(f"  📺 播放地址:")
                            print(f"  {video_url}")
                            print(f"  {'─' * 48}")
                            print(f"  💡 提示: 复制链接到播放器播放")
                            if video_url.endswith('.m3u8'):
                                print(f"  💡 m3u8推荐: VLC / PotPlayer / MX Player")
                            input("\n  按回车继续...")

        else:
            log("无效选项", "WARN")


# ============================================================
#  命令行快捷模式
# ============================================================

def quick_play(keyword):
    """命令行模式: 直接搜索并播放"""
    print(f"\n  🎯 快速搜索: {keyword}")
    items = search(keyword)
    if not items:
        print("  ❌ 未找到相关影片")
        return

    first = items[0]
    print(f"\n  ▶ 自动播放第一个结果: {first['title']}")
    detail = get_detail(first["link"])
    if not detail or not detail["sources"]:
        print("  ❌ 无可用播放源")
        return

    source = detail["sources"][0]
    ep = source["episodes"][0]
    print(f"  📺 {source['name']} - {ep['name']}")

    video = resolve_play_url(ep["url"])
    if video:
        print(f"\n  {'═' * 48}")
        print(f"  ✅ 播放链接:")
        print(f"  {video}")
        print(f"  {'═' * 48}")
        print(f"  💡 复制链接用播放器打开")
    else:
        print("  ❌ 链接解析失败")


# ============================================================
#  入口
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) > 1:
        quick_play(" ".join(sys.argv[1:]))
    else:
        try:
            main()
        except KeyboardInterrupt:
            print("\n\n  👋 再见！\n")
        except Exception as e:
            print(f"\n  ❌ 错误: {e}\n")
            import traceback
            traceback.print_exc()
