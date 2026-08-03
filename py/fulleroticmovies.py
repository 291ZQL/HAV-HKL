# -*- coding: utf-8 -*-
#!/usr/bin/env python3

import sys
import re
import json
import time
import random
import requests
from urllib import parse

sys.path.append("..")
from base.spider import Spider


class Spider(Spider):
    def __init__(self):
        self.siteUrl = "https://www.fulleroticmovies.net/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.siteUrl,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

    def fetch(self, url, headers=None, timeout=10):
        h = {
            "User-Agent": self.ua_pool[int(time.time()) % len(self.ua_pool)],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": self.siteUrl,
        }
        if headers:
            h.update(headers)
        try:
            resp = self.session.get(url, headers=h, timeout=timeout)
            resp.encoding = "utf-8"
            return resp.text
        except Exception as e:
            print(f"[源天书] 定龙脉失败: {e}")
            return ""

    def _full_url(self, path):
        if not path:
            return ""
        if path.startswith("http"):
            return path
        return parse.urljoin(self.siteUrl, path)


class Spider(YuanTianShu):

    def homeContent(self, filter):

        classes = [
            {"type_id": "newest", "type_name": "🎬 Newest Movies"},
            {"type_id": "trending", "type_name": "🔥 Trending"},
            {"type_id": "most-viewed", "type_name": "👁 Most Viewed"},
            {"type_id": "top-rated", "type_name": "⭐ Top Rated"},
            {"type_id": "category/classic", "type_name": "📼 Classic"},
            {"type_id": "category/90s", "type_name": "📼 '90s"},
            {"type_id": "category/plot-oriented", "type_name": "📖 Plot Oriented"},
            {"type_id": "category/80s", "type_name": "📼 '80s"},
            {"type_id": "category/70s", "type_name": "📼 '70s"},
            {"type_id": "category/feature", "type_name": "🎞 Feature"},
            {"type_id": "category/compilation", "type_name": "📀 Compilation"},
            {"type_id": "category/ethnic", "type_name": "🌍 Ethnic"},
            {"type_id": "category/big-tits", "type_name": "🔥 Big Tits"},
            {"type_id": "category/anal", "type_name": "🔥 Anal"},
            {"type_id": "category/group-sex", "type_name": "🔥 Group Sex"},
        ]

        html = self.fetch(self.siteUrl)
        videos = self._parse_video_list(html)

        return {
            "class": classes,
            "list": videos,
        }

    def categoryContent(self, tid, pg, filter, extend):
        if tid in ("newest", "trending", "most-viewed", "top-rated"):
            base_path = f"/{tid}/"
        elif tid.startswith(("category/", "studio/", "pornstar/")):
            base_path = f"/{tid}/"
        else:
            base_path = f"/videos/"

        if int(pg) <= 1:
            url = self._full_url(base_path)
        else:
            url = self._full_url(f"{base_path}{pg}/")

        html = self.fetch(url)
        videos = self._parse_video_list(html)

        pagecount = self._parse_pagecount(html)

        return {
            "list": videos,
            "page": int(pg),
            "pagecount": pagecount,
            "limit": 20,
            "total": pagecount * 20,
        }

    def detailContent(self, ids):
        vid = ids[0]
        url = self._full_url(vid) if not vid.startswith("http") else vid
        html = self.fetch(url)

        if not html:
            return {"list": []}

        title_match = re.search(r'<title>([^<]+)</title>', html)
        title = title_match.group(1).strip() if title_match else "Unknown"
        title = re.sub(r' - Full Erotic Movies$', '', title, flags=re.I)

        thumb_match = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html)
        thumb = thumb_match.group(1) if thumb_match else ""

        desc_match = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', html)
        desc = desc_match.group(1) if desc_match else ""

        iframe_match = re.search(r'<iframe[^>]+src="([^"]+)"', html)
        if iframe_match:
            play_url = iframe_match.group(1)
            play_url = self._full_url(play_url)
            return {
                "list": [{
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": thumb,
                    "vod_remarks": "iframe",
                    "vod_content": desc,
                    "vod_play_from": "FullErotic",
                    "vod_play_url": f"第1集${play_url}",
                }]
            }

        video_match = re.search(r'<video[^>]+src="([^"]+m3u8)"', html)
        if not video_match:
            video_match = re.search(r'<source[^>]+src="([^"]+mp4)"', html)
        if video_match:
            play_url = self._full_url(video_match.group(1))
            return {
                "list": [{
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": thumb,
                    "vod_remarks": "直链",
                    "vod_content": desc,
                    "vod_play_from": "FullErotic",
                    "vod_play_url": f"第1集${play_url}",
                }]
            }

        return {
            "list": [{
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": thumb,
                "vod_remarks": "嗅探",
                "vod_content": desc,
                "vod_play_from": "FullErotic",
                "vod_play_url": f"第1集${url}",
            }]
        }

    def playerContent(self, flag, id, vipFlags):

        if any(x in id for x in ["iframe", "embed", "player"]):
            return {"parse": 1, "url": id, "header": ""}

        if any(id.endswith(ext) for ext in [".m3u8", ".mp4", ".flv", ".mkv"]):
            return {
                "parse": 0,
                "url": id,
                "header": f"Referer={self.siteUrl}&User-Agent={self.ua_pool[0]}",
            }

        return {"parse": 1, "url": id, "header": ""}

    def searchContent(self, key, quick, pg="1"):

        search_key = parse.quote(key.replace(" ", "-").lower())
        if int(pg) <= 1:
            url = self._full_url(f"/search/{search_key}/")
        else:
            url = self._full_url(f"/search/{search_key}/{pg}/")

        html = self.fetch(url)
        videos = self._parse_video_list(html)

        return {
            "list": videos,
            "page": int(pg),
        }

    def localProxy(self, param):
        return [404, "text/plain", "Not Found"]

    def _parse_video_list(self, html):
        videos = []
        if not html:
            return videos

        pattern = re.compile(
            r'<a class="item-video[^"]*" href="([^"]+)" title="([^"]+)"[^>]*>.*?'
            r'<img class="thumb[^"]*" src="([^"]+)"(?:[^>]*data-original="([^"]+)")?[^>]*>.*?'
            r'<div class="item-title">([^<]+)</div>.*?'
            r'<div class="item-meta">(.*?)</div>',
            re.S
        )

        for match in pattern.finditer(html):
            href, title, src, data_original, title_div, meta = match.groups()

            pic = data_original if data_original else src
            if "loader" in pic or "placeholder" in pic:
                pic = src if src and "loader" not in src else ""
            pic = self._full_url(pic)

            views_match = re.search(r'<svg[^>]*#views[^>]*>.*?</svg>\s*([^<]+)', meta)
            remarks = views_match.group(1).strip() if views_match else ""

            rating_match = re.search(r'<svg[^>]*#thumb-up[^>]*>.*?</svg>\s*([^<]+)', meta)
            if rating_match:
                remarks = f"{rating_match.group(1).strip()} | {remarks}" if remarks else rating_match.group(1).strip()

            videos.append({
                "vod_id": href,
                "vod_name": title.strip(),
                "vod_pic": pic,
                "vod_remarks": remarks,
            })

        return videos

    def _parse_pagecount(self, html):
        if not html:
            return 999

        last_match = re.search(r'<li class="last"><a href="[^"]*/(\d+)/"', html)
        if last_match:
            return int(last_match.group(1))

        pages = re.findall(r'href="[^"]*/(\d+)/"[^>]*>\d+</a>', html)
        if pages:
            return max(int(p) for p in pages)

        return 999