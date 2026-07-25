"""
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: 'site_pianku',
  lang: 'hipy',
})
"""

# -*- coding: utf-8 -*-
import re
import json
import urllib.parse
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.host = "https://4k01.pianku.online"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host
        }
        # 预编译所有正则
        self._re_vod_item = re.compile(
            r'<div class="vod-item">.*?<a href="/voddetail/(\d+)\.html" title="(.*?)".*?<img src="(.*?)".*?<span class="remarks">(.*?)</span>'
        )
        self._re_pagecount = re.compile(r'尾页.*?href=".*?-(\d+)\.html"')
        self._re_title = re.compile(r'<h1[^>]*class="detail-title"[^>]*>(.*?)(?:<span|</h1>)')
        self._re_pic = re.compile(r'class="detail-poster"[^>]*>.*?<img src="(.*?)"')
        self._re_remarks = re.compile(r'class="detail-remarks"[^>]*>(.*?)</span>')
        self._re_desc = re.compile(r'class="detail-desc"[^>]*>.*?<p>(.*?)</p>')
        # 单行元信息提取
        self._re_meta = re.compile(
            r'<(?:span|p|div)[^>]*>(?:导演|主演|地区|年份)[：:](.*?)</(?:span|p|div)>'
        )
        # 线路提取
        self._re_tab = re.compile(r'class="source-tab-item[^"]*"[^>]*>(.*?)</span>')
        self._re_ep = re.compile(r'href="(/vodplay/[^"]+)"[^>]*>(.*?)</a>')
        self._re_player = re.compile(r'var player_aaaa\s*=\s*({.*?});', re.DOTALL)

    def _build_url(self, path):
        if path.startswith("http"):
            return path
        return self.host + path

    def _get_vod_list(self, html):
        """从 HTML 中用预编译正则提取视频列表"""
        vod_list = []
        for m in self._re_vod_item.finditer(html):
            vod_list.append({
                "vod_id": m.group(1),
                "vod_name": m.group(2),
                "vod_pic": self._build_url(m.group(3)),
                "vod_remarks": m.group(4).strip()
            })
        return vod_list

    def homeContent(self, filter):
        classes = [
            {"type_id": "20", "type_name": "电影"},
            {"type_id": "37", "type_name": "剧集"},
            {"type_id": "43", "type_name": "动漫"},
            {"type_id": "45", "type_name": "综艺"}
        ]
        filters = {
            "20": [{
                "key": "tid",
                "name": "分类",
                "value": [
                    {"n": "全部", "v": "20"},
                    {"n": "动作片", "v": "21"}, {"n": "喜剧片", "v": "22"},
                    {"n": "爱情片", "v": "23"}, {"n": "科幻片", "v": "24"},
                    {"n": "恐怖片", "v": "25"}, {"n": "剧情片", "v": "26"},
                    {"n": "战争片", "v": "27"}, {"n": "惊悚片", "v": "28"},
                    {"n": "犯罪片", "v": "29"}, {"n": "冒险篇", "v": "30"},
                    {"n": "动画片", "v": "31"}, {"n": "悬疑片", "v": "32"},
                    {"n": "武侠片", "v": "33"}, {"n": "奇幻片", "v": "34"},
                    {"n": "纪录片", "v": "35"}, {"n": "其他片", "v": "36"}
                ]
            }]
        }
        resp = self.fetch(self.host, headers=self.headers)
        html = resp.text
        vod_list = self._get_vod_list(html)
        result = {"class": classes, "list": vod_list}
        if filter:
            result["filters"] = filters
        return json.dumps(result, ensure_ascii=False)

    def homeVideoContent(self):
        resp = self.fetch(self.host, headers=self.headers)
        html = resp.text
        vod_list = self._get_vod_list(html)
        return json.dumps({"list": vod_list}, ensure_ascii=False)

    def categoryContent(self, tid, pg, filter, extend):
        real_tid = tid
        if extend and "tid" in extend:
            real_tid = extend["tid"]
        if pg == "1":
            url = f"{self.host}/vodtype/{real_tid}.html"
        else:
            url = f"{self.host}/vodtype/{real_tid}-{pg}.html"
        resp = self.fetch(url, headers=self.headers)
        html = resp.text
        vod_list = self._get_vod_list(html)
        pagecount = int(pg) + 1
        total = 0
        m = self._re_pagecount.search(html)
        if m:
            pagecount = int(m.group(1))
            total = pagecount * 30
        return json.dumps({
            "list": vod_list,
            "page": int(pg),
            "pagecount": pagecount,
            "limit": 24,
            "total": total
        }, ensure_ascii=False)

    def detailContent(self, ids):
        vod_id = ids[0]
        url = f"{self.host}/voddetail/{vod_id}.html"
        resp = self.fetch(url, headers=self.headers)
        html = resp.text

        # 只用最少次数扫描全文
        def _g(r, defval=""):
            m = r.search(html)
            return m.group(1).strip() if m else defval

        title = _g(self._re_title)
        pic = _g(self._re_pic)
        if pic:
            pic = self._build_url(pic)
        remarks = _g(self._re_remarks)
        content = _g(self._re_desc)

        # 元数据：一次 scan 提取所有
        director = actor = area = year = ""
        for m in self._re_meta.finditer(html):
            label_val = m.group(0)
            val = m.group(1).strip()
            if "导演" in label_val:
                director = val
            elif "主演" in label_val:
                actor = val
            elif "地区" in label_val:
                area = val
            elif "年份" in label_val:
                year = val

        # 线路与剧集：一次 scan
        play_from_list = [t.strip() for t in self._re_tab.findall(html)]
        play_url_list = []

        # 匹配每个线路的剧集区块
        pane_pattern = re.compile(r'<div[^>]*class="source-pane[^"]*"[^>]*>(.*?)</div>\s*(?=<div[^>]*class="source-pane|</section|</div>)', re.DOTALL)
        for pm in pane_pattern.finditer(html):
            pane_html = pm.group(1)
            episodes = []
            for em in self._re_ep.finditer(pane_html):
                ep_name = re.sub(r'<[^>]+>', '', em.group(2)).strip()
                ep_url = self._build_url(em.group(1))
                episodes.append(f"{ep_name}${ep_url}")
            if episodes:
                play_url_list.append("#".join(episodes))

        # 如果线路名没取到，用和剧集数量匹配的占位名
        if not play_from_list and play_url_list:
            play_from_list = [f"线路{i+1}" for i in range(len(play_url_list))]

        vod = {
            "vod_id": vod_id,
            "vod_name": title,
            "vod_pic": pic,
            "vod_content": content,
            "vod_director": director,
            "vod_actor": actor,
            "vod_area": area,
            "vod_year": year,
            "vod_remarks": remarks
        }
        if play_from_list and play_url_list:
            vod["vod_play_from"] = "$$$".join(play_from_list)
            vod["vod_play_url"] = "$$$".join(play_url_list)
        return json.dumps({"list": [vod]}, ensure_ascii=False)

    def searchContent(self, key, quick, pg="1"):
        encoded_key = urllib.parse.quote(key)
        url = f"{self.host}/vodsearch/-------------.html?wd={encoded_key}"
        resp = self.fetch(url, headers=self.headers, timeout=30)
        html = resp.text
        vod_list = self._get_vod_list(html)
        return json.dumps({
            "list": vod_list,
            "page": 1,
            "pagecount": 1
        }, ensure_ascii=False)

        encoded_key = urllib.parse.quote(key)
        url = f"{self.host}/vodsearch/-------------.html?wd={encoded_key}"
        resp = self.fetch(url, headers=self.headers)
        html = resp.text
        vod_list = self._get_vod_list(html)
        return json.dumps({
            "list": vod_list,
            "page": 1,
            "pagecount": 1
        }, ensure_ascii=False)

    def playerContent(self, flag, id, vipFlags):
        url = self._build_url(id)
        resp = self.fetch(url, headers=self.headers)
        html = resp.text
        m = self._re_player.search(html)
        if m:
            try:
                player_data = json.loads(m.group(1))
                play_url = player_data.get("url", "")
                if play_url:
                    lower_url = play_url.lower()
                    is_direct = lower_url.endswith(".m3u8") or lower_url.endswith(".mp4") or ".m3u8?" in lower_url
                    return json.dumps({
                        "parse": 0 if is_direct else 1,
                        "url": play_url,
                        "header": {
                            "User-Agent": self.headers["User-Agent"],
                            "Referer": self.host
                        }
                    }, ensure_ascii=False)
            except Exception:
                pass
        return json.dumps({
            "parse": 1,
            "url": url,
            "header": {
                "User-Agent": self.headers["User-Agent"],
                "Referer": self.host
            }
        }, ensure_ascii=False)
