#!/usr/bin/env python3
"""TRAG24: local, deterministic, image-text Reels generator. Zero image AI calls."""
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / 'templates'
PROGRAMS = {
    '0800': '0800_srbija_se_budi.jpg',
    '1100': '1100_verovali_ili_ne.jpg',
    '1400': '1400_novac_i_zivot.jpg',
    '1700': '1700_pitanje_dana.jpg',
    '2000': '2000_vesti_u_20.jpg',
    '2300': '2300_arena.jpg',
}
W, H = 1080, 1920
X1, X2 = 105, 975
TITLE_TOP = 685
BODY_BOTTOM = 1480   # Leaves room for Reel UI and attribution
WHITE = '#FFFFFF'
MUTED = '#DFE7EF'
ACCENT = '#EE334D'


def get_font(size, bold=False):
    choices = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/Library/Fonts/Arial Bold.ttf' if bold else '/Library/Fonts/Arial.ttf',
        'C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf',
    ]
    for loc in choices:
        if Path(loc).exists():
            return ImageFont.truetype(loc, size)
    raise RuntimeError('Potrebno je instalirati font DejaVu Sans.')


def break_long_word(draw, word, font, width):
    parts = []
    part = ''
    for ch in word:
        if part and draw.textlength(part + ch, font=font) > width:
            parts.append(part)
            part = ch
        else:
            part += ch
    if part:
        parts.append(part)
    return parts


def wrap(draw, text, face, max_w):
    lines=[]
    for par in str(text).split('\n'):
        if not par.strip():
            lines.append('')
            continue
        line=''
        for word in par.split():
            pieces = break_long_word(draw, word, face, max_w)
            for piece in pieces:
                candidate = (line + ' ' + piece).strip()
                if line and draw.textlength(candidate,font=face)>max_w:
                    lines.append(line)
                    line=piece
                else:
                    line=candidate
        if line:
            lines.append(line)
    return lines


def draw_shadow(draw, xy, txt, font, fill, stroke=False):
    x,y=xy
    draw.text((x+2,y+3),txt,font=font,fill='#051020',stroke_width=0)
    draw.text((x,y),txt,font=font,fill=fill,stroke_width=1 if stroke else 0,stroke_fill='#0B1829')


def paginate(draw, title, body):
    title_face = get_font(60,True)
    # Enforce legibility; a very long headline is paginated by the caller upstream.
    title_lines=wrap(draw,title,title_face,X2-X1)
    if len(title_lines)>4:
        raise ValueError('Naslov je predugačak za Reel. Skrati ga na najviše 4 reda.')
    body_face = get_font(45)
    body_lines=wrap(draw,body,body_face,X2-X1)
    title_height=len(title_lines)*79
    first_body_y=TITLE_TOP+title_height+85
    num_lines=max(1,(BODY_BOTTOM-first_body_y)//66)
    if num_lines<3:
        raise ValueError('Nema dovoljno mesta za tekst — skratiti naslov.')
    # For subsequent pages, repeat same title (clear editorial context).
    pages=[]
    for i in range(0,len(body_lines),num_lines):
        pages.append((title_lines,body_lines[i:i+num_lines],first_body_y))
    return pages or [(title_lines,[],first_body_y)]


def render(program,title,body,out_dir,source='',label='DEMO',video=False,sec=15):
    if program not in PROGRAMS:
        raise ValueError(f'Nepoznat program: {program}')
    bg_path=TEMPLATES/PROGRAMS[program]
    if not bg_path.exists():
        raise FileNotFoundError(f'Nedostaje podloga: {bg_path}')
    if not title.strip() or not body.strip():
        raise ValueError('Naslov i tekst su obavezni.')
    out_dir.mkdir(parents=True,exist_ok=True)
    bg=Image.open(bg_path).convert('RGB')
    if bg.size!=(W,H):
        bg=bg.resize((W,H),Image.Resampling.LANCZOS)
    scratch=ImageDraw.Draw(bg)
    pages=paginate(scratch,title,body)
    outputs=[]
    for index,(title_lines,body_lines,body_y) in enumerate(pages,1):
        image=bg.copy()
        draw=ImageDraw.Draw(image)
        ty=TITLE_TOP
        for line in title_lines:
            draw_shadow(draw,(X1,ty),line,get_font(60,True),WHITE)
            ty+=79
        rule_y=ty+24
        draw.rounded_rectangle((X1,rule_y,X1+320,rule_y+5),radius=2,fill=ACCENT)
        yy=body_y
        for line in body_lines:
            if line:
                draw_shadow(draw,(X1,yy),line,get_font(45),MUTED)
            yy+=66
        # Provenance is required, and always visible inside the protected content panel.
        if label:
            draw.text((X1,1531),label.upper()[:32],font=get_font(22,True),fill='#ADB8C7')
        if source:
            origin=re.sub(r'\s+',' ',source).strip()[:65]
            draw.text((X1,1563),'IZVOR: '+origin,font=get_font(21),fill='#C0CAD7')
        if len(pages)>1:
            count=f'{index}/{len(pages)}'
            draw.text((950,1531),count,font=get_font(24,True),fill=WHITE,anchor='ra')
        file=out_dir/f'{program}_{index:02d}.png'
        image.save(file,optimize=True)
        outputs.append(file)
    movie=None
    if video:
        if not shutil.which('ffmpeg'):
            raise RuntimeError('Za MP4 je potreban besplatni FFmpeg.')
        movie=out_dir/(program+'_reel.mp4')
        cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',f'1/{sec}',
             '-start_number','1','-i',str(out_dir/f'{program}_%02d.png'),
             '-vf','fps=24,format=yuv420p','-c:v','libx264','-preset','veryfast',
             '-crf','25','-movflags','+faststart','-pix_fmt','yuv420p',str(movie)]
        subprocess.run(cmd,check=True)
    return outputs,movie


def main():
    parser=argparse.ArgumentParser(description='Besplatno generisanje TRAG24 Reels iz šest odobrenih podloga')
    parser.add_argument('--content',required=True,help='JSON datoteka sa poljima program, naslov, tekst, izvor, oznaka')
    parser.add_argument('--out',default='demo',help='Izlazni folder')
    parser.add_argument('--video',action='store_true')
    parser.add_argument('--seconds',type=int,default=15)
    args=parser.parse_args()
    if not 15<=args.seconds<=30:
        parser.error('--seconds treba da bude od 15 do 30')
    obj=json.loads(Path(args.content).read_text(encoding='utf-8'))
    if isinstance(obj,dict): obj=[obj]
    for item in obj:
        paths,video=render(str(item['program']),str(item['naslov']),str(item['tekst']),
                            Path(args.out),str(item.get('izvor','')),str(item.get('oznaka','DEMO')),
                            args.video,args.seconds)
        print(f"{item['program']}: {len(paths)} kadrova; video: {video or 'nije pravljen'}")

if __name__=='__main__':
    main()