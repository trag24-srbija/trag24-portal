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

def render(day, article, i, total):
    """Premium 9:16 morning template, with legible text for mobile viewing."""
    im=Image.new("RGB",(1080,1920),"#08182C")
    d=ImageDraw.Draw(im,"RGBA")
    WHITE="#F6F8FC"; GOLD="#F1BE61"; MUTED="#E0E7F0"; RED="#DE354C"
    for y in range(1920):
        t=y/1920
        d.line((0,y,1080,y),fill=(int(7+5*t),int(22+7*t),int(42+11*t),255))
    # Faint globe and editorial curves
    d.ellipse((615,45,1060,490),outline=(158,188,221,72),width=2)
    for factor in (.37,.7):
        r=int(222*factor)
        d.ellipse((838-r,45,838+r,490),outline=(158,188,221,48),width=2)
    d.arc((-320,1370,1350,2000),10,165,fill=(213,164,83,45),width=2)

    def wrapped(text,face,max_width):
        result=[]; current=""
        for word in str(text).split():
            test=(current+" "+word).strip()
            if current and d.textbbox((0,0),test,font=face)[2]>max_width:
                result.append(current);current=word
            else:current=test
        if current:result.append(current)
        return result

    def fit(text,max_width,max_height,start,minimum,bold,leading=1.24):
        for size in range(start,minimum-1,-1):
            face=font(size,bold); parts=wrapped(text,face,max_width)
            step=round(size*leading)
            if len(parts)*step<=max_height and all(
                    d.textbbox((0,0),part,font=face)[2]<=max_width for part in parts):
                return face,parts,step
        face=font(minimum,bold); parts=wrapped(text,face,max_width)
        step=round(minimum*leading)
        if len(parts)*step>max_height:
            parts=parts[:max(1,max_height//step)]
            last=parts[-1]
            while last and d.textbbox((0,0),last+"…",font=face)[2]>max_width:
                last=last[:-1]
            parts[-1]=last.rstrip()+"…"
        return face,parts,step

    def gold(x,y,text,face):
        d.text((x+2,y+3),text,font=face,fill=(0,0,0,110))
        d.text((x,y),text,font=face,fill=GOLD)

    # TRAG 24 brand: red mark, white wordmark, gold show title
    d.rectangle((75,127,100,190),fill=RED)
    d.text((125,113),"TRAG 24",font=font(74,True),fill=WHITE)
    show="SRBIJA SE BUDI"
    show_face=font(89,True)
    while d.textbbox((0,0),show,font=show_face)[2]>932:
        show_face=font(show_face.size-1,True)
    gold(75,344,show,show_face)
    meta=f"08:00  |  JUTARNJI PREGLED  |  {day:%d.%m.%Y.}"
    meta_face=font(36,True)
    while d.textbbox((0,0),meta,font=meta_face)[2]>935:
        meta_face=font(meta_face.size-1,True)
    d.text((77,462),meta,font=meta_face,fill="#E7EAF0")
    d.line((74,543,1006,543),fill=RED,width=5)

    # Main article panel
    d.rounded_rectangle((64,614,1026,1605),radius=40,fill=(0,0,0,75))
    d.rounded_rectangle((58,607,1020,1598),radius=40,
                        fill="#112B4B",outline="#B79459",width=3)
    d.line((100,613,978,613),fill=(251,207,115,100),width=2)
    d.rounded_rectangle((101,655,462,731),radius=12,fill="#E4B45C")
    if article is None:
        d.text((121,669),"JUTARNJI PREGLED",font=font(28,True),fill="#0A1A2C")
        gold(102,821,"DOBRO JUTRO, SRBIJO",font(50,True))
        d.text((102,957),"Najvažnije teme dana",font=font(44,True),fill=WHITE)
        d.text((102,1031),"iz više objavljenih izvora",font=font(39),fill=MUTED)
    else:
        d.text((121,663),f"TEMA {i:02d} / {total:02d}",
               font=font(42,True),fill="#091B31")
        headline=str(article.get("title",""))
        face,parts,step=fit(headline,865,320,59,41,True,1.23)
        y=766
        for part in parts:
            d.text((101,y),part,font=face,fill=WHITE)
            y+=step

        # Summary is almost headline-sized, not tiny fine print.
        summary_y=max(1122,y+22)
        summary_height=max(100,1481-summary_y)
        summary=str(article.get("summary",""))
        face,parts,step=fit(summary,860,summary_height,48,38,False,1.24)
        for part in parts:
            d.text((101,summary_y),part,font=face,fill=WHITE)
            summary_y+=step

        d.line((101,1491,976,1491),fill=(243,193,97,175),width=2)
        sources="IZVORI: "+", ".join(article.get("sources",[]))
        face=font(32,True)
        while d.textbbox((0,0),sources,font=face)[2]>867 and face.size>24:
            face=font(face.size-1,True)
        gold(101,1517,sources,face)

    # Readable, aligned source note and footer
    d.rectangle((75,1691,82,1786),fill=GOLD)
    d.text((104,1675),"PREGLED OBJAVLJENIH IZVORA",
           font=font(38,True),fill=WHITE)
    d.text((104,1740),"Detalji i izvorni linkovi: TRAG 24",
           font=font(35),fill=MUTED)
    d.rectangle((0,1824,1080,1920),fill="#081324")
    d.line((0,1824,1080,1824),fill=RED,width=5)
    d.text((76,1851),"TRAG24  |  JUTRO",font=font(34,True),fill=WHITE)
    gold(878,1849,"08:00",font(36,True))
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
