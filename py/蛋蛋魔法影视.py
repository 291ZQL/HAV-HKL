# coding=utf-8

import re
import json
import sys
import time
import random
import requests
from urllib.parse import quote, urljoin

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    import requests as _requests
    from lxml import etree

    class BaseSpider:
        def fetch(self, url, headers=None, timeout=20, verify=False):
            s = _requests.Session()
            return s.get(url, headers=headers, timeout=timeout, verify=verify)

        def html(self, content):
            return etree.HTML(content)


class Spider(BaseSpider):
    name = '魔法影视'
    host = 'https://www.ddmf.net'

    CATEGORY_MAP = {
        '1': '电影',
        '2': '电视剧',
        '4': '动漫',
        '3': '综艺',
        '5': '福利视频',
        '37': '海外抖音',
    }

    _debug = True
    _categories = []

    def _log(self, msg):
        if self._debug:
            print(f'[魔法影视] {msg}')

    def getName(self):
        return self.name

    def isVideoFormat(self, url):
        if not url:
            return False
        url = url.lower()
        return any(url.endswith(fmt) for fmt in ['.m3u8', '.mp4', '.flv', '.ts', '.mkv', '.avi'])

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def _get_headers(self, referer=None, ajax=False):
        h = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': referer or self.host + '/',
        }
        if ajax:
            h['Accept'] = '*/*'
            h['X-Requested-With'] = 'XMLHttpRequest'
        return h

    def _fetch(self, url, referer=None, retries=3, timeout=20):
        if not hasattr(self, '_session'):
            self._session = requests.Session()
        headers = self._get_headers(referer)
        for attempt in range(retries):
            try:
                if attempt > 0:
                    time.sleep(random.uniform(1.0, 2.5))
                r = self._session.get(url, headers=headers, timeout=timeout, verify=False)
                if r.status_code == 200:
                    if not r.encoding or r.encoding.lower() in ('iso-8859-1', 'latin-1'):
                        r.encoding = r.apparent_encoding or 'utf-8'
                    return r.text or '', r.url
                self._log(f'请求失败 [{r.status_code}] {url}')
                return '', ''
            except Exception as e:
                self._log(f'请求异常 [{url}]: {e}，重试 {attempt+1}/{retries}')
                continue
        return '', ''

    def _fix_url(self, url):
        if not url:
            return ''
        if url.startswith('//'):
            return 'https:' + url
        if url.startswith('/'):
            return self.host + url
        if not url.startswith('http'):
            return urljoin(self.host + '/', url)
        return url

    def _clean_text(self, text):
        if not text:
            return ''
        text = re.sub(r'<[^>]+>', '', str(text))
        text = text.replace('\r', '').replace('\n', ' ').strip()
        text = re.sub(r'\s+', ' ', text)
        return text

    def init(self, extend=''):
        self._log('正在初始化...')
        self._categories = [
            {'type_id': k, 'type_name': v}
            for k, v in self.CATEGORY_MAP.items()
        ]
        self._log(f'分类加载完成: {len(self._categories)} 个')

    def homeContent(self, filter=False):
        try:
            if not self._categories:
                self.init()
            html, _ = self._fetch(self.host + '/')
            items = self._parse_video_list(html) if html else []
            return {
                'class': self._categories,
                'list': items[:24],
                'parse': 0,
                'jx': 0,
            }
        except Exception as e:
            self._log(f'homeContent 异常: {e}')
            return {'class': self._categories, 'list': [], 'parse': 0, 'jx': 0}

    def homeVideoContent(self):
        html, _ = self._fetch(self.host + '/')
        items = self._parse_video_list(html) if html else []
        return {'list': items[:24], 'parse': 0, 'jx': 0}

    def _parse_video_list(self, html):
        items = []
        if not html or len(html) < 500:
            return items

        seen = set()
        # 首页/分类：a.module-poster-item.module-item
        poster_pattern = r'<a\b[^>]*?\bclass="module-poster-item module-item[^"]*"[^>]*>(.*?)</a>'
        poster_matches = list(re.finditer(poster_pattern, html, re.S))
        # 搜索页：div.module-card-item.module-item（按容器拆分，避免嵌套 div 干扰）
        card_inners = self._split_card_items(html)
        self._log(f'匹配到视频卡片: poster={len(poster_matches)}, card={len(card_inners)}')

        for match in poster_matches:
            tag = match.group(0)
            inner = match.group(1)

            href_match = re.search(r'href="(/voddetail/(\d+)\.html)"', tag)
            if not href_match:
                continue
            vod_id = href_match.group(2)
            if vod_id in seen:
                continue
            seen.add(vod_id)

            title_match = re.search(r'title="([^"]*)"', tag)
            title = title_match.group(1) if title_match else ''

            pic, note = self._extract_pic_note(inner)

            items.append({
                'vod_id': vod_id,
                'vod_name': self._clean_text(title)[:120],
                'vod_pic': self._fix_url(pic),
                'vod_remarks': note,
            })

        for inner in card_inners:
            href_match = re.search(r'href="(/voddetail/(\d+)\.html)"', inner)
            if not href_match:
                continue
            vod_id = href_match.group(2)
            if vod_id in seen:
                continue
            seen.add(vod_id)

            title = ''
            tm = re.search(r'<div[^>]*class="module-card-item-title"[^>]*>.*?<strong[^>]*>(.*?)</strong>', inner, re.S)
            if tm:
                title = self._clean_text(tm.group(1))

            pic, note = self._extract_pic_note(inner)

            items.append({
                'vod_id': vod_id,
                'vod_name': self._clean_text(title)[:120],
                'vod_pic': self._fix_url(pic),
                'vod_remarks': note,
            })

        return items

    def _split_card_items(self, html):
        """从搜索页容器中拆出每个 module-card-item 的内部 HTML。"""
        container_match = re.search(r'<div[^>]*class="module-items module-card-items"[^>]*>(.*)', html, re.S)
        if not container_match:
            return []
        container = container_match.group(1)
        parts = re.split(r'<div[^>]*class="module-card-item module-item[^"]*"[^>]*>', container)
        # parts[0] 为容器开头杂物，后续偶数索引为各卡片内容
        return [parts[i] for i in range(2, len(parts), 2)]

    def _extract_pic_note(self, inner):
        pic = ''
        pm = re.search(r'<img[^>]*data-original="([^"]*)"', inner)
        if pm:
            pic = pm.group(1)
        if not pic:
            pm = re.search(r'<img[^>]*src="([^"]*)"', inner)
            if pm:
                pic = pm.group(1)
        note = ''
        nm = re.search(r'<div[^>]*class="module-item-note"[^>]*>(.*?)</div>', inner, re.S)
        if nm:
            note = self._clean_text(nm.group(1))
        return pic, note

    def categoryContent(self, tid, pg, filter=False, extend=''):
        try:
            page = int(pg) if pg else 1
            slug = str(tid)
            url = f'{self.host}/vodshow/{slug}--------{page}---.html'

            html, _ = self._fetch(url)
            items = self._parse_video_list(html) if html else []
            total_pages = self._parse_total_pages(html, page, rf'href="/vodshow/{re.escape(slug)}--------(\d+)---\.html"')

            return {
                'list': items,
                'page': page,
                'pagecount': max(total_pages, page),
                'limit': len(items),
                'total': max(total_pages, page) * len(items) if items else 0,
                'parse': 0,
                'jx': 0,
            }
        except Exception as e:
            self._log(f'categoryContent 异常: {e}')
            return {'list': [], 'page': int(pg) if pg else 1, 'pagecount': 1, 'limit': 0, 'total': 0, 'parse': 0, 'jx': 0}

    def _parse_total_pages(self, html, current_page, pattern=r'href="/vodshow/\d+--------(\d+)---\.html"'):
        total = current_page
        if not html:
            return total
        try:
            nums = re.findall(pattern, html)
            for p in nums:
                total = max(total, int(p))
        except:
            pass
        if total == current_page and len(html) > 3000:
            total = current_page + 1
        return total

    def detailContent(self, ids):
        try:
            vod_id = str(ids[0] if isinstance(ids, list) else ids)
            detail_url = f'{self.host}/voddetail/{vod_id}.html'
            html, _ = self._fetch(detail_url)

            if not html:
                return {
                    'list': [{'vod_id': vod_id, 'vod_name': '获取失败', 'vod_play_from': '默认', 'vod_play_url': ''}],
                    'parse': 0, 'jx': 0,
                }

            return self._parse_detail(vod_id, html)
        except Exception as e:
            self._log(f'detailContent 异常: {e}')
            return {
                'list': [{'vod_id': str(ids), 'vod_name': '错误', 'vod_play_from': '默认', 'vod_play_url': ''}],
                'parse': 0, 'jx': 0,
            }

    def _parse_detail(self, vod_id, html):
        # 标题
        vod_name = ''
        m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
        if m:
            vod_name = self._clean_text(m.group(1))
        if not vod_name:
            m = re.search(r'<title>(.*?)(?:-|—|\|)', html)
            if m:
                vod_name = m.group(1).strip()

        # 封面
        vod_pic = ''
        m = re.search(
            r'<a[^>]*href="/voddetail/' + re.escape(vod_id) + r'\.html"[^>]*>.*?<img[^>]*data-original="([^"]+)"',
            html, re.S
        )
        if m:
            vod_pic = self._fix_url(m.group(1))
        if not vod_pic:
            m = re.search(r'<img[^>]*data-original="([^"]+)"', html)
            if m:
                vod_pic = self._fix_url(m.group(1))

        # 分类
        type_name = ''
        m = re.search(r'<a[^>]*href="/vodtype/\d+\.html"[^>]*>([^<]+)</a>', html)
        if not m:
            m = re.search(r'<a[^>]*href="/vodshow/\d+-----------\.html"[^>]*>([^<]+)</a>', html)
        if m:
            type_name = self._clean_text(m.group(1))

        # 提取剧集列表：从 .module-play-list 中找第一个播放链接
        play_url = ''
        play_match = re.search(r'<div[^>]*class="module-play-list"[^>]*>(.*?)</div>\s*</div>', html, re.S)
        if play_match:
            first_play = re.search(r'href="(/vodplay/\d+-\d+-\d+\.html)"', play_match.group(1))
            if first_play:
                play_url = self._fix_url(first_play.group(1))

        detail = {
            'vod_id': vod_id,
            'vod_name': vod_name or '未知',
            'vod_pic': vod_pic,
            'vod_actor': '',
            'vod_director': '',
            'vod_content': type_name,
            'type_name': type_name,
            'vod_play_from': '默认',
            'vod_play_url': f'正片${play_url or vod_id}',
        }
        return {'list': [detail], 'parse': 0, 'jx': 0}

    def playerContent(self, flag, id, vipFlags=None):
        try:
            play_url = str(id or '')
            if not play_url.startswith('http'):
                play_url = self._fix_url(play_url)

            html, _ = self._fetch(play_url, referer=play_url)
            if not html:
                return {'parse': 0, 'playUrl': '', 'url': '', 'header': '', 'jx': 0}

            m = re.search(r'var player_aaaa\s*=\s*(\{.*?\});', html, re.S)
            if m:
                try:
                    player = json.loads(m.group(1))
                    real_url = player.get('url', '')
                    parse_flag = 0 if self.isVideoFormat(real_url) else 1
                    return {
                        'parse': parse_flag,
                        'playUrl': '',
                        'url': real_url,
                        'header': json.dumps(self._get_headers(play_url)),
                        'jx': 0,
                    }
                except Exception as e:
                    self._log(f'解析 player_aaaa 失败: {e}')

            return {
                'parse': 1, 'playUrl': '', 'url': play_url,
                'header': json.dumps(self._get_headers(play_url)), 'jx': 0,
            }
        except Exception as e:
            self._log(f'playerContent 异常: {e}')
            return {'parse': 0, 'playUrl': '', 'url': '', 'header': '', 'jx': 0}

    def searchContent(self, key, quick, pg='1'):
        try:
            page = int(pg) if pg else 1
            kw = quote(key)
            url = f'{self.host}/vodsearch/-------------.html?wd={kw}'
            if page > 1:
                url = f'{self.host}/vodsearch/{kw}--------{page}---.html'

            html, _ = self._fetch(url)
            items = self._parse_video_list(html) if html else []

            total_pages = self._parse_total_pages(
                html, page,
                rf'href="/vodsearch/{re.escape(kw)}--------(\d+)---\.html"'
            )
            page_nums = re.findall(rf'href="/vodsearch/{re.escape(kw)}--------(\d+)---\.html"', html)
            if not page_nums:
                page_nums = re.findall(r'href="/vodsearch/[^"]+--------(\d+)---\.html"', html)
            for p in page_nums:
                total_pages = max(total_pages, int(p))

            return {
                'list': items,
                'page': page,
                'pagecount': max(total_pages, page),
                'limit': len(items),
                'total': max(total_pages, page) * len(items) if items else 0,
                'parse': 0,
                'jx': 0,
            }
        except Exception as e:
            self._log(f'searchContent 异常: {e}')
            return {'list': [], 'page': int(pg) if pg else 1, 'pagecount': 1, 'limit': 0, 'total': 0, 'parse': 0, 'jx': 0}

    def searchContentPage(self, key, quick, page):
        return self.searchContent(key, quick, page)

    def localProxy(self, param):
        if not param or not param.startswith('http'):
            return None
        try:
            r = self.fetch(param, headers={
                'User-Agent': 'Mozilla/5.0',
                'Referer': self.host + '/',
            }, timeout=(10, 15), verify=False)
            content_type = r.headers.get('Content-Type', 'application/octet-stream')
            return [200, content_type, r.content]
        except:
            return None


if __name__ == '__main__':
    spider = Spider()
    spider.init()
    print('=== 首页 ===')
    home = spider.homeContent(False)
    print(f"分类: {len(home.get('class', []))} 个")
    print(f"首页视频: {len(home.get('list', []))} 个")
    for v in home.get('list', [])[:5]:
        print(f"  {v['vod_name']} (ID: {v['vod_id']}, 备注: {v['vod_remarks']}, 封面: {v['vod_pic'][:50]}...)")

    print('\n=== 分类: 福利视频 第1页 ===')
    cat = spider.categoryContent('5', '1', False)
    print(f"  结果: {len(cat.get('list', []))} 个, 总页数: {cat.get('pagecount')}")
    for v in cat.get('list', [])[:5]:
        print(f"    {v['vod_name']} (ID: {v['vod_id']}, 备注: {v['vod_remarks']})")

    print('\n=== 分类: 海外抖音 第1页 ===')
    cat2 = spider.categoryContent('37', '1', False)
    print(f"  结果: {len(cat2.get('list', []))} 个, 总页数: {cat2.get('pagecount')}")
    for v in cat2.get('list', [])[:5]:
        print(f"    {v['vod_name']} (ID: {v['vod_id']}, 备注: {v['vod_remarks']})")

    if cat.get('list'):
        first = cat['list'][0]
        print(f"\n=== 详情: {first['vod_name']} (ID: {first['vod_id']}) ===")
        detail = spider.detailContent([first['vod_id']])
        if detail.get('list'):
            d = detail['list'][0]
            print(f"  名称: {d.get('vod_name')}")
            print(f"  封面: {d.get('vod_pic', '')[:80]}...")
            print(f"  分类: {d.get('type_name')}")
            print(f"  播放页: {d.get('vod_play_url', '')[:120]}...")

            play_url = d['vod_play_url'].split('$')[-1]
            print(f"\n=== 播放: {first['vod_name']} ===")
            play = spider.playerContent('默认', play_url)
            print(f"  真实URL: {play.get('url', '')[:120]}...")

    print(f"\n=== 搜索: 测试 ===")
    search = spider.searchContent('测试', False, '1')
    print(f"  搜索结果: {len(search.get('list', []))} 个, 总页数: {search.get('pagecount')}")
    for v in search.get('list', [])[:5]:
        print(f"    {v['vod_name']} (ID: {v['vod_id']})")
