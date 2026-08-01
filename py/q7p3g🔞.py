# -*- coding: utf-8 -*-
import sys,re,json,html as hmod,base64,subprocess
from urllib.parse import quote,unquote,urljoin
sys.path.append('..')
try:
    from base.spider import Spider as _B
except ImportError:
    class _B:pass
try:import requests
except ImportError:requests=None

_H=[104,116,116,112,115,58,47,47,119,119,119,46,114,51,101,50,111,46,116,111,112]
H=bytes(_H).decode()
IMG_HOST="https://www.q7p3g.top/index/home.html"
U="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
_PROXY_PORT=9978
_proxy_started=False

SUB=[
 ("最新剧情","juqing","/cYcL2p1cWluZy9saXN0cy5odG1s.html"),
 ("  麻豆传媒","juqing","/cYcL2p1cWluZy9saXN0Lem6u%2BixhuS8oOWqki5odG1s.html"),
 ("  天美传媒","juqing","/cYcL2p1cWluZy9saXN0LeWkqee%2BjuS8oOWqki5odG1s.html"),
 ("  星空果冻","juqing","/cYcL2p1cWluZy9saXN0LeaYn%2BepuuaenOWGuy5odG1s.html"),
 ("  蜜桃精东","juqing","/cYcL2p1cWluZy9saXN0LeicnOahg%2BeyvuS4nC5odG1s.html"),
 ("  韩国伦理","juqing","/cYcL2p1cWluZy9saXN0LemfqeWbveS8pueQhi5odG1s.html"),
 ("  COSPLAY","juqing","/cYcL2p1cWluZy9saXN0LUNPU1BMQVkuaHRtbA%3D%3D.html"),
 ("  经典三级","juqing","/cYcL2p1cWluZy9saXN0Lee7j%2BWFuOS4iee6py5odG1s.html"),
 ("  中文字幕","juqing","/cYcL2p1cWluZy9saXN0LeS4reaWh%2BWtl%2BW5lS5odG1s.html"),
 ("最新电影","shipin","/cYcL3NoaXBpbi9saXN0cy5odG1s.html"),
 ("  日本av","shipin","/cYcL3NoaXBpbi9saXN0LeaXpeacrGF2Lmh0bWw%3D.html"),
 ("  韩国热舞","shipin","/cYcL3NoaXBpbi9saXN0LemfqeWbveeDreiIni5odG1s.html"),
 ("  欧美精品","shipin","/cYcL3NoaXBpbi9saXN0Leasp%2Be%2BjueyvuWTgS5odG1s.html"),
 ("  动漫电影","shipin","/cYcL3NoaXBpbi9saXN0LeWKqOa8q%2BeUteW9sS5odG1s.html"),
 ("  国产自拍","shipin","/cYcL3NoaXBpbi9saXN0LeWbveS6p%2BiHquaLjS5odG1s.html"),
 ("  岛国无码","shipin","/cYcL3NoaXBpbi9saXN0LeWym%2BWbveaXoOeggS5odG1s.html"),
 ("  JVID","shipin","/cYcL3NoaXBpbi9saXN0LUpWSUQuaHRtbA%3D%3D.html"),
 ("  SM调教","shipin","/cYcL3NoaXBpbi9saXN0LVNN6LCD5pWZLmh0bWw%3D.html"),
 ("最新精选","jingpin","/cYcL2ppbmdwaW4vbGlzdHMuaHRtbA%3D%3D.html"),
 ("  软萌福利姬","jingpin","/cYcL2ppbmdwaW4vbGlzdC3ova%2FokIznpo%2FliKnlp6wuaHRtbA%3D%3D.html"),
 ("  黑料头条","jingpin","/cYcL2ppbmdwaW4vbGlzdC3pu5HmlpnlpLTmnaEuaHRtbA%3D%3D.html"),
 ("  明星AI","jingpin","/cYcL2ppbmdwaW4vbGlzdC3mmI7mmJ9BSS5odG1s.html"),
 ("  人妖伪娘","jingpin","/cYcL2ppbmdwaW4vbGlzdC3kurrlppbkvKrlqJguaHRtbA%3D%3D.html"),
 ("  onlyfans","jingpin","/cYcL2ppbmdwaW4vbGlzdC1vbmx5ZmFucy5odG1s.html"),
 ("  探花系列","jingpin","/cYcL2ppbmdwaW4vbGlzdC3mjqLoirHns7vliJcuaHRtbA%3D%3D.html"),
 ("  主播大秀","jingpin","/cYcL2ppbmdwaW4vbGlzdC3kuLvmkq3lpKfnp4AuaHRtbA%3D%3D.html"),
 ("  韩国主播","jingpin","/cYcL2ppbmdwaW4vbGlzdC3pn6nlm73kuLvmkq0uaHRtbA%3D%3D.html"),
]

def _node_decrypt(enc_list):
    if not enc_list:return{}
    try:
        js="const C=require('crypto-js'),k=C.enc.Utf8.parse('IdTJq0HklpuI6mu8iB%%OO@!vd^4K&uXW'),i=C.enc.Utf8.parse('$0v@krH7V2883346');const a=%s;process.stdout.write(JSON.stringify(a.map(e=>{try{return C.AES.decrypt(e,k,{iv:i,mode:C.mode.CBC,padding:C.pad.Pkcs7}).toString(C.enc.Utf8)}catch(ex){return e}})))"%json.dumps(enc_list)
        r=subprocess.run(["node","-e",js],capture_output=True,timeout=30,cwd="H:/js_study")
        result=json.loads(r.stdout.decode("utf-8",errors="ignore").strip())
        return dict(zip(enc_list,result))
    except:return {e:e for e in enc_list}

class Spider(_B):
    def init(self,e=""):
        self.s=requests.Session();self.s.headers.update({"User-Agent":U})
        self.cache={}

    def getName(self):return"R3E2O"
    def isVideoFormat(self,u):return".m3u8"in u or".mp4"in u
    def manualVideoCheck(self):return False

    def _get(self,u):
        if not u.startswith("http"):u=H+u
        try:r=self.s.get(u,timeout=20);r.encoding='utf-8';return r.text
        except:return""

    def _proxy(self,kind,url):
        try:
            return self.getProxyUrl()+"&kind="+kind+"&url="+quote(url,safe="")
        except:
            return url

    def _image(self,path):
        # CDN returns `data:image/...;base64,...`, not an image response.
        return self._proxy("img",IMG_HOST+path) if path else ""

    def _hls(self,url):
        # Keep AES-HLS behind localProxy: playlist/key/segments are re-served locally.
        return self._proxy("hls",url)

    def _cards(self,h):
        v=[];enc={}
        for m in re.finditer(r'<a[^>]*class="video-item"[^>]*href="([^"]+)"[^>]*>',h,re.S):
            href=m.group(1)
            end=h.find('</a>',m.end());inner=h[m.end():end]if end>0 else""
            tm=re.search(r'class="video-item-title[^"]*"[^>]*title="([^"]*)"',inner)
            raw_title=tm.group(1).strip()if tm else""
            im=re.search(r'data-base64="([^"]+)"',inner)
            img=self._image(im.group(1)) if im else ""
            dm=re.search(r'class="video-item-date"[^>]*>([^<]+)',inner)
            date=dm.group(1).strip()if dm else""
            enc[href]=raw_title
            v.append({"vod_id":href,"vod_name":raw_title,"vod_pic":img,"vod_remarks":date})
        if enc:
            dec=_node_decrypt(list(enc.values()))
            for item in v:
                k=enc[item["vod_id"]]
                item["vod_name"]=dec.get(k,k)
                # Cache title+pic for detail page
                self.cache[item["vod_id"]]={"name":item["vod_name"],"pic":item["vod_pic"]}
        return v

    def homeContent(self,filter=False):
        return{"class":[{"type_id":str(i),"type_name":n}for i,(n,z,u)in enumerate(SUB)]}

    def homeVideoContent(self):
        h=self._get(H+SUB[0][2])
        return{"list":self._cards(h)if h else[]}

    def categoryContent(self,tid,pg=1,filter=False,extend=None):
        try:
            idx=int(str(tid));name,zone,path=SUB[idx]
            h=self._get(H+path)
            if not h:return{"list":[],"page":pg,"pagecount":1}
            return{"list":self._cards(h),"page":pg,"pagecount":1,"limit":len(self._cards(h)),"total":len(self._cards(h))}
        except Exception as e:print("[R3]cat:",e);return{"list":[],"page":pg,"pagecount":1}

    def detailContent(self,ids):
        play_url=str(ids[0])
        # Normalize: strip protocol+host prefix to match cache keys
        if play_url.startswith(H):
            cache_key=play_url[len(H):]
        else:
            cache_key=play_url
        if not play_url.startswith("http"):play_url=H+play_url
        cached=self.cache.get(cache_key,{})
        title=cached.get("name",play_url)
        img=cached.get("pic","")
        h=self._get(play_url)
        if not h:return{"list":[]}
        # m3u8: var video + var m3u8_host
        vm=re.search(r"var video\s*=\s*decodeString\('([^']+)'\)",h)
        hm=re.search(r"var m3u8_host\s*=\s*decodeString\('([^']+)'\)",h)
        src=""
        if vm and hm:
            try:vpath=base64.b64decode(vm.group(1)).decode()
            except:vpath=""
            try:hurl=base64.b64decode(hm.group(1)).decode()
            except:hurl=""
            if hurl and vpath:src=self._hls(hurl.rstrip("/")+"/"+vpath.lstrip("/"))
        pf=["线路1"];pu=["线路1$"+src]if src else["线路1$"+play_url]
        return{"list":[{"vod_id":play_url,"vod_name":title,"vod_pic":img,
            "type_name":"","vod_year":"","vod_area":"","vod_remarks":"",
            "vod_actor":"","vod_director":"","vod_content":"",
            "vod_play_from":"$$$".join(pf),"vod_play_url":"$$$".join(pu)}]}

    def playerContent(self,flag,id,vipFlags=None):
        if id and(".m3u8"in id or".mp4"in id):
            return{"url":id,"header":json.dumps({"User-Agent":U,"Referer":H+"/"})}
        d=self.detailContent([id])
        if d and d.get("list"):
            us=d["list"][0].get("vod_play_url","").split("$$$")
            if us:
                f=us[0];url=f.split("$",1)[1]if"$"in f else f
                return{"url":url,"header":json.dumps({"User-Agent":U,"Referer":H+"/"})}
        return{"url":""}

    def searchContent(self,key,quick=False,pg=1):
        return{"list":[]}

    def localProxy(self,param):
        try:
            raw=(param or {}).get("url","")
            kind=(param or {}).get("kind","")
            url=unquote(raw)
            if not url.startswith("https://"):
                return [404,"text/plain",b""]
            headers={"User-Agent":U,"Referer":H+"/"}
            r=self.s.get(url,headers=headers,timeout=30)
            if r.status_code!=200:return [r.status_code,"text/plain",b""]
            if kind=="img":
                text=r.text.strip()
                if text.startswith("data:image/") and "," in text:
                    meta,payload=text.split(",",1)
                    mime=meta[5:meta.index(";")]
                    return [200,mime,base64.b64decode(payload)]
                return [200,r.headers.get("Content-Type","image/jpeg"),r.content]
            if kind=="hls":
                # Only proxy the AES key. Segments stay on the CDN, preserving
                # the player's parallel downloads and native HLS performance.
                text=r.text
                out=[]
                for line in text.splitlines():
                    if line.startswith("#EXT-X-KEY:"):
                        line=re.sub(r'URI="([^"]+)"',lambda m:'URI="'+self._proxy("bin",urljoin(url,m.group(1)))+'"',line)
                    out.append(line)
                return [200,"application/vnd.apple.mpegurl","\n".join(out).encode()]
            return [200,r.headers.get("Content-Type","application/octet-stream"),r.content]
        except Exception as e:
            print("[R3]proxy:",e)
            return [500,"text/plain",b""]
