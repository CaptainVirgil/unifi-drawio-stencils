#!/usr/bin/env python3
"""Convert a native-cell .drawio (the editable gear files in drawio/) to a clean vector SVG.
Handles the shapes the gear files use: rounded/plain rects, groups (coord nesting),
triangles (direction), ellipses, text, and mxgraph.basic.flash (PoE bolt).
Usage: drawio_to_svg.py in.drawio out.svg
"""
import sys, re, html
from xml.etree import ElementTree as ET

def parse_style(s):
    d={}
    for tok in (s or "").split(";"):
        if not tok: continue
        if "=" in tok: k,v=tok.split("=",1); d[k]=v
        else: d[k_flag(tok)]=True if False else tok  # bare flag → store as key
    # bare flags: also record presence
    for tok in (s or "").split(";"):
        if tok and "=" not in tok: d[tok]=True
    return d
def k_flag(t): return t

def num(v,default=0.0):
    try: return float(v)
    except: return default

FLASH=[(42,2),(2,56),(38,56),(22,98),(98,40),(56,40),(80,2)]  # mxgraph.basic.flash bolt (0..100)

def main(src,out):
    root=ET.parse(src).getroot()
    model=root.find(".//mxGraphModel")
    W=num(model.get("pageWidth"),1000); H=num(model.get("pageHeight"),90)
    cells={}; order=[]
    for c in model.iter("mxCell"):
        cid=c.get("id"); g=c.find("mxGeometry")
        cells[cid]={"id":cid,"parent":c.get("parent"),"style":c.get("style","") or "",
                    "value":c.get("value","") or "","vertex":c.get("vertex"),
                    "x":num(g.get("x")) if g is not None else 0,"y":num(g.get("y")) if g is not None else 0,
                    "w":num(g.get("width")) if g is not None else 0,"h":num(g.get("height")) if g is not None else 0}
        order.append(cid)
    def absxy(cid):
        c=cells.get(cid);
        if not c or c["parent"] in (None,"0","1"): return (c["x"],c["y"]) if c else (0,0)
        px,py=absxy(c["parent"]); return (px+c["x"],py+c["y"])
    el=[]
    for cid in order:
        c=cells[cid]
        if c["vertex"]!="1": continue
        st=parse_style(c["style"])
        if st.get("group"): continue        # container only
        ax,ay=absxy(cid); w,h=c["w"],c["h"]
        fill=st.get("fillColor","none"); fill="none" if fill in ("none",None) else fill
        stroke=st.get("strokeColor","none"); stroke="none" if stroke in ("none",None) else stroke
        sw=num(st.get("strokeWidth"),1.0)
        sattr=(f' stroke="{stroke}" stroke-width="{sw}"' if stroke!="none" else "")
        if "ellipse" in st:
            el.append(f'<ellipse cx="{ax+w/2:.2f}" cy="{ay+h/2:.2f}" rx="{w/2:.2f}" ry="{h/2:.2f}" fill="{fill}"{sattr}/>')
        elif "triangle" in st:
            dr=st.get("direction","east")
            if dr=="north": p=[(ax+w/2,ay),(ax,ay+h),(ax+w,ay+h)]
            elif dr=="south": p=[(ax,ay),(ax+w,ay),(ax+w/2,ay+h)]
            elif dr=="west": p=[(ax+w,ay),(ax+w,ay+h),(ax,ay+h/2)]
            else: p=[(ax,ay),(ax,ay+h),(ax+w,ay+h/2)]
            pts=" ".join(f"{x:.2f},{y:.2f}" for x,y in p)
            el.append(f'<polygon points="{pts}" fill="{fill}"{sattr}/>')
        elif "shape" in st and "flash" in st.get("shape",""):
            pts=" ".join(f"{ax+x/100*w:.2f},{ay+y/100*h:.2f}" for x,y in FLASH)
            el.append(f'<polygon points="{pts}" fill="{fill}"{sattr} stroke-linejoin="round"/>')
        elif "text" in st:
            txt=re.sub(r"<[^>]+>","",html.unescape(c["value"])).strip()
            if txt:
                size=num(st.get("fontSize"),11); col=st.get("fontColor","#000000")
                al=st.get("align","center"); anchor={"left":"start","right":"end"}.get(al,"middle")
                tx=ax if al=="left" else (ax+w if al=="right" else ax+w/2)
                el.append(f'<text x="{tx:.2f}" y="{ay+h/2:.2f}" font-family="sans-serif" font-size="{size:.0f}" '
                          f'fill="{col}" text-anchor="{anchor}" dominant-baseline="central">{html.escape(txt)}</text>')
        else:  # rect (rounded or plain)
            rx=0.0
            if st.get("absoluteArcSize")=="1": rx=num(st.get("arcSize"),0)
            elif st.get("rounded")=="1": rx=min(w,h)*min(num(st.get("arcSize"),20),50)/100
            el.append(f'<rect x="{ax:.2f}" y="{ay:.2f}" width="{w:.2f}" height="{h:.2f}" '
                      f'rx="{rx:.2f}" fill="{fill}"{sattr}/>')
    svg=(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}">'+"".join(el)+"</svg>")
    open(out,"w").write(svg); print(f"{src} → {out} ({len(svg)}B, {len(el)} shapes)")

if __name__=="__main__":
    main(sys.argv[1],sys.argv[2])
