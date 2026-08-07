#coding=utf-8
#!/usr/bin/python
import sys
sys.path.append('..')
from base.spider import Spider
import json
import re
from urllib import request, parse

class Spider(Spider):
    def getName(self):
        return "Movzer"

    def init(self, extend=""):
        self.host = "https://www.movzer.com"
        self.header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.movzer.com/"
        }
        self.categories = [
            {"type_id": "492", "type_name": "阴部"},
            {"type_id": "594", "type_name": "奶子"},
            {"type_id": "523", "type_name": "性交"},
            {"type_id": "283", "type_name": "操"},
            {"type_id": "102", "type_name": "口交"},
            {"type_id": "36", "type_name": "屁股"},
            {"type_id": "17", "type_name": "业余"},
            {"type_id": "1", "type_name": "首页"}
        ]
        self.slug_map = {
            "492": "pussy",
            "594": "tits",
            "523": "sex",
            "283": "fucking",
            "102": "blowjob",
            "36": "ass",
            "17": "amateurs",
            "1": ""
        }
        pass

    def isVideoFormat(self, url):
        return True if re.search(r'\.(mp4|m3u8|flv|mp3|m4a)', url) else False

    def manualVideoCheck(self):
        pass

    def homeContent(self, filter):
        result = {
            "class": self.categories,
            "list": []
        }
        try:
            url = self.host + "/?hl=zh"
            html = self.fetch(url)
            videos = self.parseList(html)
            result["list"] = videos
        except Exception as e:
            print(e)
        return result

    def homeVideoContent(self):
        result = {"list": []}
        try:
            url = self.host + "/?hl=zh"
            html = self.fetch(url)
            videos = self.parseList(html)
            result["list"] = videos
        except Exception as e:
            print(e)
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": int(pg), "pagecount": 999, "limit": 120, "total": 99999}
        try:
            if tid == "1":
                if int(pg) == 1:
                    url = self.host + "/?hl=zh"
                else:
                    url = self.host + "/videos?hl=zh&s=n&p=" + str(pg)
            else:
                slug = self.slug_map.get(tid, "pussy")
                url = self.host + "/categories/" + tid + "/" + slug + "?hl=zh"
                if int(pg) > 1:
                    url += "&p=" + str(pg)

            html = self.fetch(url)
            videos = self.parseList(html)
            result["list"] = videos
            if len(videos) == 0:
                result["pagecount"] = int(pg) - 1 if int(pg) > 1 else 1
        except Exception as e:
            print(e)
        return result

    def detailContent(self, array):
        result = {"list": []}
        try:
            vid_info = array[0]
            parts = vid_info.split("|")
            if len(parts) >= 2:
                vid = parts[0]
                slug = parts[1]
                mp4 = parts[2] if len(parts) > 2 else ""
                title = parts[3] if len(parts) > 3 else ""
                pic = parts[4] if len(parts) > 4 else ""
                time = parts[5] if len(parts) > 5 else ""

                # 如果列表页没有mp4，尝试从详情页获取
                if not mp4:
                    mp4 = self.getMp4FromDetail(vid, slug)

                vod = {
                    "vod_id": vid_info,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": time,
                    "vod_content": title,
                    "vod_play_from": "Movzer",
                    "vod_play_url": "正片$" + mp4 if mp4 else ""
                }
                result["list"].append(vod)
        except Exception as e:
            print(e)
        return result

    def searchContent(self, key, quick):
        result = {"list": [], "page": 1, "pagecount": 1, "limit": 120, "total": 120}
        try:
            url = self.host + "/mzr?q=" + parse.quote(key) + "&hl=zh"
            html = self.fetch(url)
            videos = self.parseList(html)
            result["list"] = videos
        except Exception as e:
            print(e)
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {
            "parse": 0,
            "playUrl": "",
            "url": id,
            "header": json.dumps(self.header)
        }
        return result

    def fetch(self, url):
        req = request.Request(url, headers=self.header)
        with request.urlopen(req, timeout=15) as response:
            return response.read().decode('utf-8')

    def parseList(self, html):
        videos = []
        blocks = html.split('<div class="grid-item-el">')
        for block in blocks[1:]:
            if 'class="emb-grid-item-el"' in block:
                continue
            if 'class="kim"' not in block and 'href=' not in block:
                continue

            href_match = re.search(r'<a[^>]*href="([^"]*)"[^>]*title="([^"]*)"', block)
            if not href_match:
                continue
            href, title = href_match.groups()

            mp4_match = re.search(r'data-mp4="([^"]*)"', block)
            mp4 = mp4_match.group(1) if mp4_match else ""

            pic_match = re.search(r'<img[^>]*src="([^"]*)"', block)
            pic = pic_match.group(1) if pic_match else ""

            time_match = re.search(r'<span class="time">([^<]*)</span>', block)
            time = time_match.group(1) if time_match else ""

            txt_match = re.search(r'<p class="txt">([^<]*)</p>', block)
            txt = txt_match.group(1) if txt_match else title

            vid_match = re.search(r'/v(?:/bin)?/(\d+)', href)
            if not vid_match:
                continue
            vid = vid_match.group(1)

            slug_match = re.search(r'/v(?:/bin)?/\d+/([^?]+)', href)
            slug = slug_match.group(1) if slug_match else ""

            if pic.startswith('//'):
                pic = 'https:' + pic
            elif pic.startswith('/'):
                pic = self.host + pic

            if mp4 and mp4.startswith('//'):
                mp4 = 'https:' + mp4

            vod_id = vid + "|" + slug + "|" + mp4 + "|" + title + "|" + pic + "|" + time

            videos.append({
                "vod_id": vod_id,
                "vod_name": title or txt,
                "vod_pic": pic,
                "vod_remarks": time
            })

        return videos

    def getMp4FromDetail(self, vid, slug):
        urls_to_try = [
            self.host + "/v/bin/" + vid + "/" + slug + "?hl=zh",
            self.host + "/v/" + vid + "/" + slug + "?hl=zh"
        ]
        for url in urls_to_try:
            try:
                html = self.fetch(url)
                mp4_match = re.search(r'data-mp4="([^"]*)"', html)
                if mp4_match:
                    mp4 = mp4_match.group(1)
                    if mp4.startswith('//'):
                        mp4 = 'https:' + mp4
                    return mp4
            except:
                continue
        return ""

    config = {
        "player": {},
        "filter": {}
    }
    header = {}

    def localProxy(self, param):
        action = {
            'url': '',
            'header': '',
            'param': '',
            'type': 'string',
            'after': ''
        }
        return [200, "video/MP2T", action, ""]
