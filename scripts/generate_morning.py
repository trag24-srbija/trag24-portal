#!/usr/bin/env python3
"""Automatic morning video from multi-source TRAG 24 analyses."""
import json, re, math, datetime as dt, argparse, subprocess
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont

TZ=ZoneInfo("Europe/Belgrade")
KEYS=re.compile(r"srbij|beograd|zemun|smederev|novi sad|niš|kragujev|subotic|pančev|leskov|kraljev|vojvodin|kosov|skupštin|polumaraton",re.I)

def recent(day):
    end=dt.datetime.combine(day,dt.time(8),TZ)
    start=end-dt.timedelta(hours=25)
    data=json.loads(Path("analize.json").read_text(encoding="utf-8"))["analize"]
    found=[]
    for a in data:
        try:
            stamp=dt.datetime.fromisoformat(a["objavljeno_u"].replace("Z","+00:00")).astimezone(TZ)
        except (KeyError,TypeError,ValueError):
            continue
        title=str(a.get("naslov",""))
        urls=a.get("izvori",[])
        if not isinstance(urls,list): continue
        urls=[x for x in urls if isinstance(x,str) and x.startswith("https://")]
        hosts=list(dict.fromkeys(urlparse(u).netloc.removeprefix("www.") for u in urls))
        if a.get("status")!="objavljeno" or not start<=stamp<=end or len(hosts)<2 or not KEYS.search(title):
            continue
        body=a.get("tekst",[])
        if not isinstance(body,list):body=[body]
        brief=next((str(t).split(": ",1)[-1] for t in body if len(str(t))>50),"")
        brief=" ".join(brief.split())
        if len(brief)>190:brief=brief[:190].rsplit(" ",1)[0].rstrip(".,;")+"…"
        found.append((stamp,{"title":title,"summary":brief,"sources":hosts[:3],"urls":urls[:3]}))
    found.sort(key=lambda x:x[0],reverse=True)
    chosen=[]
    for _,x in found:
        def words(y):return set(re.findall(r"[a-zčćžšđ0-9]{4,}",y.lower()))
        w=words(x["title"])
        if any(len(w&words(old["title"]))/max(1,len(w|words(old["title"])))>.48 for old in chosen):continue
        chosen.append(x)
        if len(chosen)==3:break
    return chosen

def font(size,bold=False):
    f="DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/"+f,size)

def lines(draw,text,f,width,n):
    result=[];line=""
    for word in text.split():
        trial=(line+" "+word).strip()
        if line and draw.textbbox((0,0),trial,font=f)[2]>width:
            result.append(line);line=word
        else:line=trial
    if line:result.append(line)
    return result[:n]

def render(day,article,i,total):
    im=Image.new("RGB",(1080,1920))
    d=ImageDraw.Draw(im,"RGBA")
    for y in range(1920): d.line((0,y,1080,y),fill=(12+y//160,24+y//180,42+y//160,255))
    cx,cy,r=830,260,210
    d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=(168,190,222,65),width=3)
    for factor in (.4,.7):
        x=int(r*factor)
        d.ellipse((cx-x,cy-r,cx+x,cy+r),outline=(168,190,222,35),width=2)
    d.rectangle((75,133,100,187),fill="#CF3544")
    d.text((124,116),"TRAG 24",font=font(70,True),fill="#F5F7FA")
    d.text((74,344),"SRBIJA SE BUDI",font=font(72,True),fill="#F5F7FA")
    d.text((76,447),f"08:00  |  JUTARNJI PREGLED  |  {day:%d.%m.%Y.}",font=font(30),fill="#DAB562")
    d.line((75,512,1005,512),fill="#CE354A",width=5)
    d.rounded_rectangle((70,613,1010,1500),radius=42,fill=(26,43,69,255),outline=(112,138,180,135),width=2)
    if article is None:
        d.text((116,790),"DOBRO JUTRO, SRBIJO",font=font(49,True),fill="#DAB562")
        d.text((116,935),"Najvažnije teme dana",font=font(42),fill="#F5F7FA")
        d.text((116,1009),"iz više objavljenih izvora",font=font(35),fill="#F5F7FA")
    else:
        d.text((116,678),f"TEMA {i:02d} / {total:02d}",font=font(36,True),fill="#DAB562")
        f=font(47,True);y=787
        for ln in lines(d,article["title"],f,826,5):
            d.text((116,y),ln,font=f,fill="#F5F7FA");y+=72
        y=max(1195,y+25);f2=font(29)
        for ln in lines(d,article["summary"],f2,820,3):
            d.text((116,y),ln,font=f2,fill="#BAC6D8");y+=47
        d.line((116,1393,956,1393),fill=(164,182,207,85),width=2)
        d.text((116,1435),"IZVORI: "+", ".join(article["sources"]),font=font(23),fill="#DAB562")
    d.text((75,1633),"PREGLED OBJAVLJENIH IZVORA",font=font(34,True),fill="#F5F7FA")
    d.text((75,1698),"Detalji i izvorni linkovi: TRAG 24",font=font(29),fill="#BAC6D8")
    d.rectangle((0,1800,1080,1920),fill="#091324")
    d.line((0,1800,1080,1800),fill="#CF3544",width=5)
    d.text((75,1845),"TRAG24  |  JUTRO",font=font(30,True),fill="#F5F7FA")
    d.text((855,1845),"08:00",font=font(32,True),fill="#DAB562")
    return im

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--date",default="")
    args=p.parse_args()
    day=dt.date.fromisoformat(args.date) if args.date else dt.datetime.now(TZ).date()
    chosen=recent(day)
    if not chosen:
        print("SKIP: nema svežih analiza o Srbiji sa najmanje dva izvora")
        return
    root=Path("morning_output");root.mkdir(exist_ok=True)
    cards=[None]+chosen
    durations=[2.4]+[7.6]*len(chosen)
    listfile=root/"slides.ffconcat"
    with listfile.open("w",encoding="utf-8") as f:
        f.write("ffconcat version 1.0\n")
        for i,(item,seconds) in enumerate(zip(cards,durations)):
            render(day,item,i,len(chosen)).save(root/f"slide-{i}.png")
            f.write(f"file 'slide-{i}.png'\nduration {seconds}\n")
        f.write(f"file 'slide-{len(cards)-1}.png'\n")
    import imageio_ffmpeg
    ff=imageio_ffmpeg.get_ffmpeg_exe()
    bg=Path("trag24-vesti-podloga.mov")
    if not bg.exists():bg=Path("trag24-vesti-podloga.mp4")
    mp4=root/"SRBIJA-SE-BUDI.mp4"
    cmd=[ff,"-hide_banner","-loglevel","error","-nostdin","-y","-safe","0","-f","concat","-i",str(listfile)]
    if bg.exists():cmd+=["-stream_loop","-1","-i",str(bg),"-map","0:v:0","-map","1:a?"]
    dur=sum(durations)
    cmd+=["-vf","fps=24,scale=1080:1920,format=yuv420p","-t",str(dur),"-c:v","libx264","-preset","veryfast","-crf","24","-pix_fmt","yuv420p"]
    if bg.exists():cmd+=["-c:a","aac","-b:a","128k","-af",f"volume=0.20,afade=t=out:st={dur-1.2:.2f}:d=1.2"]
    cmd+=["-movflags","+faststart",str(mp4)]
    subprocess.run(cmd,check=True)
    if mp4.stat().st_size<10000:raise RuntimeError("Video nije napravljen")
    meta={"program":"Srbija se budi","datum":day.isoformat(),"vreme":"08:00 Europe/Belgrade","status":"nacrt","teme":chosen,"napomena":"Pregled objavljenih analiza sa najmanje dva navedena izvora; bez nezavisne potvrde"}
    (root/"opis.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    print("OK, jutarnji video:",mp4,"tema:",len(chosen))

if __name__=="__main__":main()
