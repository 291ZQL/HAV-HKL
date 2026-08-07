# -*- coding: utf-8 -*-
import re,urllib.request,urllib.parse,html as htmllib,json,sys
try:
    from base.spider import Spider
except:
    class Spider: pass

class Spider(Spider):
    def getName(self): return '番号网'
    def init(self,extend=''): pass
    def isVideoFormat(self,url): return url.endswith(('.m3u8','.mp4','.flv','.avi','.mkv'))
    def manualVideoCheck(self): return False
    def destroy(self): pass
    def __init__(self):
        self.host='https://web.fanhaowang1.cc'
        self.headers={'User-Agent':'Mozilla/5.0','Accept-Language':'zh-CN'}
        self.cms_type='unknown'
        self.classes=[
            ('兔儿资源','286'),
            ('精品推荐','304'),
            ('主播秀色','305'),
            ('日本有码','306'),
            ('日本无码','307'),
            ('中文字幕','308'),
            ('童颜巨乳','309'),
            ('性感人妻','310'),
            ('强歼乱伦','311'),
            ('欧美情色','312'),
            ('三级伦理','313'),
            ('卡通动漫','314'),
            ('丝袜OL','315'),
            ('剧情介绍','316'),
            ('网曝系列','317'),
            ('相同性别','318'),
            ('探花','319'),
            ('国产人妻','320'),
            ('国产SM','321'),
            ('国产丝袜','322'),
        ]

    def fetch(self,url,headers=None,timeout=20):
        req=urllib.request.Request(url,headers=headers or self.headers)
        with urllib.request.urlopen(req,timeout=timeout) as r: return r.read().decode('utf-8','ignore')
    def clean(self,s): return re.sub(r'\s+',' ',htmllib.unescape(re.sub(r'<.*?>','',s or ''))).strip()
    def abs(self,u): return u if u.startswith('http') else self.host+u
    def pic_proxy(self,u):
        # 请自行修改图片代理
        u=htmllib.unescape(u or '').replace('&#x2F;','/').replace('&#x3D;','=')
        if u.startswith('//'): u='https:'+u
        return u

    def homeContent(self,filter):
        return {'class':[{'type_name':n,'type_id':i} for n,i in self.classes]}

    def categoryContent(self,tid,pg,filter,extend):
        result={}
        try:
            url=self.host+'/'+tid+(('?page='+str(pg)) if str(pg)!='1' else '')
            html=self.fetch(url)
            result['list']=self.parse_list(html)
            result['page']=int(pg)
            result['pagecount']=999
            result['limit']=len(result.get('list',[]))
            result['total']=999*24
        except:
            result['list']=[]
        return result

    def parse_list(self,html):
        arr=[];seen=set()
        for m in re.finditer(r'<a\s+href="([^"]+)"[^>]*>.*?<img[^>]+(?:data-src|src)="([^"]*)"[^>]*>.*?</a>',html,re.S|re.I):
            vid=m.group(1);pic=m.group(2)
            if vid in seen or not vid or vid.startswith('http'): continue
            seen.add(vid)
            title='';tm=re.search(r'<a[^>]*href="'+re.escape(vid)+r'"[^>]*>(.*?)</a>',html[m.start():m.start()+800],re.S)
            if tm: title=self.clean(tm.group(1))
            if len(title)<2: continue
            pic=self.pic_proxy(pic)
            dur='';dm=re.search(r'<span[^>]*>(\s*\d{1,2}:\d{2}(?::\d{2})?\s*)</span>',html[m.start():m.start()+600],re.S)
            if dm: dur=dm.group(1).strip()
            arr.append({'vod_id':vid,'vod_name':title,'vod_pic':pic,'vod_remarks':dur})
        return arr

    def detailContent(self,ids):
        result={}
        try:
            vid=ids[0] if isinstance(ids,list) else ids
            url=vid if vid.startswith('http') else self.host+vid
            html=self.fetch(url)
            title=self.clean((re.search(r'<meta property="og:title" content="([^"]*)"',html) or re.search(r'<title>(.*?)</title>',html,re.S) or ['',''])[1])
            pic='';pm=re.search(r'<meta property="og:image" content="([^"]*)"',html)
            pic=htmllib.unescape(pm.group(1)).replace('&#x2F;','/').replace('&#x3D;','=') if pm else ''
            desc=self.clean((re.search(r'<meta property="og:description"\s*content="([^"]*)"',html,re.S) or ['',''])[1])
            year=self.field(html,'发行日期') or self.field(html,'年份') or self.field(html,'上映时间')
            director=self.field(html,'导演')
            actresses=self.field(html,'演员') or self.field(html,'主演')
            sources=self.unpack_sources(html)
            play=[]
            if sources:
                for k,u in sources: play.append(k+'$'+u)
            else:
                play.append('播放$'+self.host+'/'+vid)
            vod={'vod_id':vid,'vod_name':title or vid.upper(),'vod_pic':pic,'vod_director':director,'vod_actor':actresses,'vod_content':desc,'vod_play_from':'$$$'.join([x.split('$')[0] for x in play]),'vod_play_url':'$$$'.join(play)}
            result['list']=[vod]
        except:
            result['list']=[]
        return result

    def unpack_sources(self,html):
        out=[]
        p=re.search(r"eval\(function\(p,a,c,k,e,d\).*?\('(.*?)',\s*(\d+),\s*(\d+),\s*'([^']*)'\.split\('\|'\)",html,re.S)
        if not p: return out
        s,base,count,keys=p.group(1).replace("\\'","'"),int(p.group(2)),int(p.group(3)),p.group(4).split('|')
        def b36(n):
            chars='0123456789abcdefghijklmnopqrstuvwxyz';n=int(n);r=''
            if n==0: return '0'
            while n: r=chars[n%36]+r;n//=36
            return r
        for c in range(count-1,-1,-1):
            k=keys[c] if c<len(keys) else ''
            if k: s=re.sub(r'\b'+b36(c)+r'\b',k,s)
        for name,url in re.findall(r"(source(?:842|1280)?)='(https?://[^']+?\.m3u8)'",s):
            label={'source':'原画','source842':'842x480','source1280':'1280x720'}.get(name,name)
            out.append((label,url))
        return out

    def searchContent(self,key,quick,pg='1'):
        try:
            url=self.host+'/search/'+urllib.parse.quote(key)
            html=self.fetch(url)
            return {'list':self.parse_list(html)}
        except:
            return {'list':[]}

    def playerContent(self,flag,id,vipFlags):
        if id.startswith('http') and '.m3u8' in id:
            return {'parse':0,'url':id,'header':self.headers}
        did=id.split('/')[-1]
        d=self.detailContent([did])['list'][0]
        u=d['vod_play_url'].split('$')[-1].split('$$$')[0]
        return {'parse':0,'url':u,'header':self.headers}

    def localProxy(self,param): return None
