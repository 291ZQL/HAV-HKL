#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════╗
║   OK影视 - 歪比巴卜影视 (wbbb1.com)             ║
║   影视聚合观看脚本                               ║
╚══════════════════════════════════════════════════╝

架构说明：
- 苹果CMS架构，无WAF防护，可直接HTTP访问
- 详情页: /detail/{id}.html
- 播放页: /vplay/{id}-{source_id}-{episode}.html
- 分类页: /type/{type_id}.html
- 搜索: /search/{keyword}-------------.html
- 视频源: 从播放页提取 m3u8 地址
"""

import re
import sys
import requests
from urllib.parse import quote

# ==================== 配置 ====================
BASE_URL = "https://wbbb1.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": BASE_URL + "/"
}

TYPE_MAP = {"1": "电影", "2": "剧集", "3": "动漫", "4": "综艺"}

session = requests.Session()
session.headers.update(HEADERS)


def fetch(url):
    try:
        r = session.get(url, timeout=15)
        return r.text
    except Exception as e:
        return None


# ==================== 首页 ====================
def get_homepage():
    """获取首页影片"""
    html = fetch(BASE_URL + "/")
    if not html:
        return []
    
    # 用alt属性 + 详情链接
    pattern = r'alt="([^"]{2,30})"[^>]*src="[^"]*"[^>]*>.*?/detail/(\d+)\.html'
    items = re.findall(pattern, html, re.S)
    results = []
    seen = set()
    for name, vid in items:
        if name not in seen and "歪比巴卜" not in name and "更多" not in name:
            seen.add(name)
            results.append({"id": vid, "name": name})
    return results[:40]


# ==================== 分类 ====================
def get_category_list(type_id=1, page=1):
    url = f"{BASE_URL}/type/{type_id}.html"
    if page > 1:
        url = f"{BASE_URL}/type/{type_id}-{page}.html"
    html = fetch(url)
    if not html:
        return []
    
    # alt+detail组合
    pattern = r'alt="([^"]{2,30})"[^>]*src="[^"]*"[^>]*>.*?/detail/(\d+)\.html'
    items = re.findall(pattern, html, re.S)
    results = []
    seen = set()
    for name, vid in items:
        if name not in seen and "歪比巴卜" not in name:
            seen.add(name)
            results.append({"id": vid, "name": name})
    return results


# ==================== 搜索 ====================
def search_video(keyword):
    encoded = quote(keyword)
    url = f"{BASE_URL}/search/{encoded}-------------.html"
    html = fetch(url)
    if not html:
        return []
    
    # alt+detail组合
    pattern = r'alt="([^"]{2,30})"[^>]*src="[^"]*"[^>]*>.*?/detail/(\d+)\.html'
    items = re.findall(pattern, html, re.S)
    results = []
    seen = set()
    for name, vid in items:
        if name not in seen and "歪比巴卜" not in name and len(name) >= 2:
            seen.add(name)
            results.append({"id": vid, "name": name})
    return results


# ==================== 详情 ====================
def get_detail(vod_id):
    url = f"{BASE_URL}/detail/{vod_id}.html"
    html = fetch(url)
    if not html:
        return None
    
    detail = {}
    
    # 标题
    m = re.search(r'<h1[^>]*>([^<]+)', html)
    if m:
        detail["title"] = m.group(1).strip()
    
    # 信息
    for key, pat in {"导演": r'导演[：:]\s*([^<]+)', "主演": r'主演[：:]\s*([^<]+)',
                      "地区": r'地区[：:]\s*([^<]+)', "年份": r'年份[：:]\s*([^<]+)',
                      "备注": r'备注[：:]\s*([^<]+)', "类型": r'类型[：:]\s*([^<]+)'}.items():
        m = re.search(pat, html)
        if m:
            detail[key] = m.group(1).strip()
    
    # 简介
    m = re.search(r'class="[^"]*desc[^"]*"[^>]*>\s*([^<]+)', html)
    if m:
        detail["简介"] = m.group(1).strip()
    
    # 播放源
    detail["sources"] = []
    
    # 直接提取所有vplay链接，按source_id分组
    all_vplay = re.findall(r'/vplay/(\d+)-(\d+)-(\d+)\.html', html)
    if all_vplay:
        groups = {}
        for vid, sid, ep in all_vplay:
            sid_int = int(sid)
            if sid_int not in groups:
                groups[sid_int] = set()
            groups[sid_int].add(int(ep))
        
        for sid in sorted(groups.keys()):
            eps = sorted(groups[sid])
            detail["sources"].append({
                "source_id": sid,
                "name": f"线路{sid}",
                "episodes": [{"episode": e, "url": f"/vplay/{vod_id}-{sid}-{e}.html"} for e in eps]
            })
    
    # 尝试获取线路名称（从页面tab）
    tab_pattern = r'<span[^>]*>([^<]{2,15})</span>.*?module-play-list'
    tabs = re.findall(tab_pattern, html, re.S)
    for i, tab in enumerate(tabs):
        tab = tab.strip()
        if i < len(detail["sources"]):
            detail["sources"][i]["name"] = tab
    
    return detail


# ==================== 播放 ====================
def get_play_url(vod_id, source_id, episode=1):
    url = f"{BASE_URL}/vplay/{vod_id}-{source_id}-{episode}.html"
    html = fetch(url)
    if not html:
        return []
    
    # 提取m3u8地址
    m3u8s = re.findall(r'[\'"](https?[^\'"]+\.m3u8[^\'"]*)[\'"]', html)
    cleaned = []
    for u in m3u8s:
        u = u.replace("\\/", "/").replace("\\", "")
        if u not in cleaned and u.startswith("http"):
            cleaned.append(u)
    return cleaned


# ==================== 终端UI ====================
def print_header(title):
    width = 60
    print(f"\n{'═' * (width+2)}")
    print(f" {title}")
    print(f"{'═' * (width+2)}")


def print_menu(items):
    for i, item in enumerate(items, 1):
        name = item.get("name", item.get("title", "?"))
        print(f"  [{i:>3}] {name[:50]}")
    print()


def main_menu():
    while True:
        print_header("OK影视 - 歪比巴卜影视 (wbbb1.com)")
        print("  [1] 首页推荐")
        print("  [2] 电影分类")
        print("  [3] 剧集分类")
        print("  [4] 动漫分类")
        print("  [5] 综艺分类")
        print("  [S] 搜索影片")
        print("  [Q] 退出")
        choice = input("\n请选择: ").strip().upper()
        
        if choice == "Q": print("再见！"); break
        elif choice == "S": search_menu(); break
        elif choice in "12345": category_menu(int(choice)); break


def search_menu():
    keyword = input("\n请输入影片名称: ").strip()
    if not keyword: return main_menu()
    
    print("\n正在搜索...")
    results = search_video(keyword)
    if not results:
        print("未找到相关影片")
        input("\n按回车返回...")
        return main_menu()
    
    print_header(f"搜索结果: {keyword}")
    print_menu(results)
    choice = input("选择编号(0返回): ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(results):
        item = results[int(choice)-1]
        video_detail_menu(item["id"], item["name"])
    else:
        main_menu()


def category_menu(type_id):
    name = TYPE_MAP.get(str(type_id), f"分类{type_id}")
    print(f"\n正在加载{name}列表...")
    items = get_category_list(type_id)
    if not items:
        print("列表为空")
        input("\n按回车返回...")
        return main_menu()
    
    print_header(name)
    print_menu(items)
    choice = input("选择编号(0返回): ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(items):
        item = items[int(choice)-1]
        video_detail_menu(item["id"], item["name"])
    else:
        main_menu()


def video_detail_menu(vod_id, name):
    print(f"\n正在获取《{name}》详情...")
    detail = get_detail(vod_id)
    if not detail:
        print("获取失败")
        input("\n按回车返回...")
        return main_menu()
    
    print_header(f"『{detail.get('title', name)}』")
    
    for k in ["类型", "导演", "主演", "地区", "年份", "备注"]:
        if k in detail:
            v = detail[k][:80]
            print(f"  {k}: {v}")
    
    if "简介" in detail:
        desc = detail["简介"]
        print(f"\n  简介: {desc[:150]}{'…' if len(desc)>150 else ''}")
    
    sources = detail.get("sources", [])
    if sources:
        print(f"\n  播放源 ({len(sources)} 个):")
        for i, src in enumerate(sources, 1):
            eps = src["episodes"]
            label = src.get("name", f"线路{src['source_id']}")
            ep_str = f"共{len(eps)}集" if len(eps) > 1 else "单集"
            print(f"    [{i}] {label} ({ep_str})")
        
        src_choice = input("\n选择线路(0返回): ").strip()
        if src_choice.isdigit() and 1 <= int(src_choice) <= len(sources):
            src = sources[int(src_choice)-1]
            episodes = src["episodes"]
            
            if len(episodes) > 1:
                ep_nums = [e["episode"] for e in episodes]
                ranges = []
                s = ep_nums[0]; e = ep_nums[0]
                for n in ep_nums[1:]:
                    if n == e+1: e = n
                    else: ranges.append(f"{s}" if s==e else f"{s}-{e}"); s = e = n
                ranges.append(f"{s}" if s==e else f"{s}-{e}")
                print(f"  集数: {', '.join(ranges)} (共{len(episodes)}集)")
                
                ep_choice = input("选择集数(0返回): ").strip()
                if ep_choice.isdigit() and int(ep_choice) >= 1:
                    ep_num = int(ep_choice)
                    found = None
                    for e in episodes:
                        if e["episode"] == ep_num:
                            found = e; break
                    if found:
                        play_video(vod_id, src["source_id"], ep_num, detail.get("title", name))
                    else:
                        print(f"没有第{ep_num}集")
                        input("按回车返回...")
                        return main_menu()
                else:
                    return main_menu()
            else:
                play_video(vod_id, src["source_id"], 1, detail.get("title", name))
        else:
            main_menu()
    else:
        print("\n  ⚠ 未找到播放源")
        input("按回车返回...")
        return main_menu()


def play_video(vod_id, source_id, episode, title):
    print(f"\n  正在解析播放地址...")
    videos = get_play_url(vod_id, source_id, episode)
    
    if videos:
        print_header(f"▶ 播放: {title} (线路{source_id} 第{episode}集)")
        for i, v in enumerate(videos, 1):
            print(f"  [{i}] {v}")
        print()
        print("  💡 可用播放器(如VLC/手机自带播放器)打开以上地址")
        print("  💡 或复制链接在浏览器中打开")
    else:
        print("\n  ❌ 无法获取视频地址")
        print("  提示: 换个线路试试")
    
    input("\n按回车返回...")


def quick_search(keyword):
    results = search_video(keyword)
    if not results:
        print(f"未找到 '{keyword}' 相关影片")
        return
    
    print(f"\n🎯 快速搜索: {keyword} (找到{len(results)}个)")
    print_menu(results)
    
    item = results[0]
    detail = get_detail(item["id"])
    if not detail:
        print("获取详情失败")
        return
    
    print(f"\n『{detail.get('title', item['name'])}』")
    sources = detail.get("sources", [])
    if sources:
        src = sources[0]
        eps = src["episodes"]
        if eps:
            ep = eps[0]
            label = src.get("name", f"线路{src["source_id"]}")
            print(f"  自动选择: {label} 第{ep['episode']}集")
            play_video(item["id"], src["source_id"], ep["episode"], detail.get("title", item["name"]))
        else:
            print("  ⚠ 无剧集")
    else:
        print("  ⚠ 无可用播放源")


# ==================== 主入口 ====================
if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════╗
║         OK影视 - 歪比巴卜影视            ║
║         https://wbbb1.com                 ║
╚═══════════════════════════════════════════╝
""")
    
    if len(sys.argv) > 1:
        keyword = " ".join(sys.argv[1:])
        quick_search(keyword)
    else:
        main_menu()
