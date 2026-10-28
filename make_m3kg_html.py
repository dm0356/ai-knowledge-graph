# -*- coding: utf-8 -*-
"""一键把 m3kg.json 变成可交互的 m3kg.html(无需联网,双击就能看)"""
import json

rows = json.load(open("m3kg.json", encoding="utf-8"))

nodes, links = {}, []
skipped = 0
for r in rows:
    s, p, o = r.get("subject", ""), r.get("predicate", ""), r.get("object", "")
    if not s or not p or not o:
        skipped += 1
        continue
    for name, desc in ((s, r.get("description_h", "")), (o, r.get("description_o", ""))):
        if name not in nodes:
            nodes[name] = {"name": name, "desc": desc, "deg": 0}
    nodes[s]["deg"] += 1
    nodes[o]["deg"] += 1
    links.append({"source": s, "target": o, "label": p, "note": r.get("source", "")})

data = json.dumps({"nodes": list(nodes.values()), "links": links}, ensure_ascii=False)

html_page = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>M3KG 论文图知识图谱</title>
<style>
  body { margin:0; overflow:hidden; font-family:"Microsoft YaHei","PingFang SC",sans-serif; background:#f7f7f7; }
  #tip { position:fixed; pointer-events:none; background:rgba(30,30,30,.92); color:#fff;
         padding:8px 10px; border-radius:6px; font-size:12px; max-width:340px; display:none; z-index:9; white-space:pre-wrap; }
  #panel { position:fixed; left:12px; top:12px; background:rgba(255,255,255,.94); border:1px solid #ddd;
           border-radius:8px; padding:10px 14px; font-size:13px; max-width:400px; max-height:82vh; overflow:auto; z-index:8; }
  #panel h3 { margin:4px 0 6px; font-size:15px; }
  #panel .dim { color:#888; font-size:12px; }
  #panel li { margin:3px 0; }
</style>
</head>
<body>
<canvas id="c"></canvas>
<div id="tip"></div>
<div id="panel"><h3>M3KG 论文图知识图谱</h3><span class="dim" id="stat"></span><br>
<span class="dim">拖动节点移动 · 点击节点看详情 · 滚轮缩放 · 空白处拖动平移</span>
<div id="detail"></div></div>
<script>
const DATA = __DATA__;
document.getElementById('stat').textContent = DATA.nodes.length + ' 个实体 · ' + DATA.links.length + ' 条关系';

const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
const tip = document.getElementById('tip');
const detail = document.getElementById('detail');

const palette = ['#e15759','#4e79a7','#f28e2b','#59a14f','#76b7b2','#edc948','#b07aa1','#9c755f'];
function color(name){ let h=0; for(const ch of name) h=(h*31+ch.codePointAt(0))>>>0; return palette[h%palette.length]; }

const nodes = DATA.nodes.map(n => ({...n, x:(Math.random()-0.5)*500, y:(Math.random()-0.5)*350, vx:0, vy:0}));
const byName = {}; nodes.forEach(n => byName[n.name]=n);
const links = DATA.links.filter(l => byName[l.source] && byName[l.target]).map(l => ({...l, s:byName[l.source], t:byName[l.target]}));
const adj = {}; nodes.forEach(n => adj[n.name]=new Set());
links.forEach(l => { adj[l.s.name].add(l.t.name); adj[l.t.name].add(l.s.name); });

let alpha = 1, T = {s:1, tx:0, ty:0}, hover=null, selected=null, dragNode=null, panning=false, moved=0, lastMouse={x:0,y:0};

function resize(){ canvas.width = innerWidth; canvas.height = innerHeight; fit(); draw(); }
addEventListener('resize', resize);

function fit(){
  let minX=1e9,minY=1e9,maxX=-1e9,maxY=-1e9;
  nodes.forEach(n => { minX=Math.min(minX,n.x); maxX=Math.max(maxX,n.x); minY=Math.min(minY,n.y); maxY=Math.max(maxY,n.y); });
  if(maxX-minX<1||maxY-minY<1) return;
  const s = Math.min(innerWidth/(maxX-minX), innerHeight/(maxY-minY)) * 0.8;
  T.s = s; T.tx = innerWidth/2 - (minX+maxX)/2*s; T.ty = innerHeight/2 - (minY+maxY)/2*s;
}
const toScreen = p => ({x:p.x*T.s+T.tx, y:p.y*T.s+T.ty});
const toWorld  = p => ({x:(p.x-T.tx)/T.s, y:(p.y-T.ty)/T.s});

function step(){
  for(let i=0;i<nodes.length;i++) for(let j=i+1;j<nodes.length;j++){
    const a=nodes[i], b=nodes[j];
    let dx=a.x-b.x, dy=a.y-b.y, d2=dx*dx+dy*dy;
    if(d2<0.01){ dx=Math.random()-0.5; dy=Math.random()-0.5; d2=1; }
    const f=Math.min(2600/d2,40)*alpha, d=Math.sqrt(d2);
    a.vx+=dx/d*f; a.vy+=dy/d*f; b.vx-=dx/d*f; b.vy-=dy/d*f;
  }
  for(const l of links){
    const dx=l.t.x-l.s.x, dy=l.t.y-l.s.y, d=Math.sqrt(dx*dx+dy*dy)||1;
    const f=(d-120)*0.03*alpha;
    l.s.vx+=dx/d*f; l.s.vy+=dy/d*f; l.t.vx-=dx/d*f; l.t.vy-=dy/d*f;
  }
  for(const n of nodes){
    n.vx += -n.x*0.012*alpha; n.vy += -n.y*0.012*alpha;
    if(n!==dragNode){ n.vx*=0.8; n.vy*=0.8; n.x+=n.vx; n.y+=n.vy; }
  }
  alpha *= 0.985;
  fit(); draw();
  if(alpha>0.02) requestAnimationFrame(step); else { fit(); draw(); }
}

function radius(n){ return (6 + Math.min(n.deg,12)*0.9) / T.s; }

function draw(){
  ctx.setTransform(1,0,0,1,0,0);
  ctx.clearRect(0,0,canvas.width,canvas.height);
  ctx.setTransform(T.s,0,0,T.s,T.tx,T.ty);
  const focus = hover || selected;
  const focusAdj = focus ? adj[focus.name] : null;

  for(const l of links){
    const on = focus && (l.s===focus||l.t===focus);
    ctx.strokeStyle = focus ? (on ? '#999' : 'rgba(200,200,200,.25)') : '#ccc';
    ctx.lineWidth = (on?2:1)/T.s;
    ctx.beginPath(); ctx.moveTo(l.s.x,l.s.y); ctx.lineTo(l.t.x,l.t.y); ctx.stroke();
    if(on){
      const mx=(l.s.x+l.t.x)/2, my=(l.s.y+l.t.y)/2;
      ctx.font = (11/T.s)+'px sans-serif';
      ctx.lineWidth = 3/T.s; ctx.strokeStyle='rgba(255,255,255,.9)';
      ctx.strokeText(l.label, mx, my);
      ctx.fillStyle='#555'; ctx.fillText(l.label, mx, my);
    }
  }
  for(const n of nodes){
    const dim = focus && n!==focus && !focusAdj.has(n.name);
    ctx.globalAlpha = dim ? 0.15 : 1;
    const r = radius(n);
    ctx.beginPath(); ctx.arc(n.x,n.y,r,0,7);
    ctx.fillStyle = color(n.name); ctx.fill();
    if(n===focus){ ctx.lineWidth=2.5/T.s; ctx.strokeStyle='#333'; ctx.stroke(); }
    ctx.font = (12/T.s)+'px sans-serif';
    ctx.lineWidth=3.5/T.s; ctx.strokeStyle='rgba(255,255,255,.85)';
    ctx.strokeText(n.name, n.x, n.y+r+14/T.s);
    ctx.fillStyle='#222'; ctx.fillText(n.name, n.x, n.y+r+14/T.s);
    ctx.globalAlpha = 1;
  }
}

function nearest(sp, maxPx){
  let best=null, bd=maxPx;
  for(const n of nodes){
    const p=toScreen(n), d=Math.hypot(p.x-sp.x,p.y-sp.y);
    if(d<bd){ bd=d; best=n; }
  }
  return best;
}

canvas.addEventListener('mousedown', e => {
  moved=0; lastMouse={x:e.clientX,y:e.clientY};
  const w=toWorld({x:e.clientX,y:e.clientY});
  dragNode = nearest({x:e.clientX,y:e.clientY}, 15);
  if(!dragNode) panning=true;
});
addEventListener('mousemove', e => {
  const dx=e.clientX-lastMouse.x, dy=e.clientY-lastMouse.y;
  moved += Math.abs(dx)+Math.abs(dy);
  if(dragNode){
    const w=toWorld({x:e.clientX,y:e.clientY});
    dragNode.x=w.x; dragNode.y=w.y; draw();
  } else if(panning){
    T.tx+=dx; T.ty+=dy; lastMouse={x:e.clientX,y:e.clientY}; draw();
  } else {
    const n=nearest({x:e.clientX,y:e.clientY}, 15);
    if(n!==hover){ hover=n; draw(); }
    if(n){
      tip.style.display='block';
      tip.style.left=(e.clientX+14)+'px'; tip.style.top=(e.clientY+14)+'px';
      tip.textContent = n.name + (n.desc ? '\\n' + n.desc : '');
      canvas.style.cursor='pointer';
    } else { tip.style.display='none'; canvas.style.cursor='default'; }
  }
  if(dragNode||panning) lastMouse={x:e.clientX,y:e.clientY};
});
addEventListener('mouseup', e => {
  if(dragNode||panning){
    if(moved<4 && dragNode){ selected=dragNode; showDetail(dragNode); }
    dragNode=null; panning=false; draw();
  }
});
canvas.addEventListener('wheel', e => {
  e.preventDefault();
  const k = e.deltaY<0 ? 1.12 : 1/1.12;
  const m=toWorld({x:e.clientX,y:e.clientY});
  T.s*=k; T.tx=e.clientX-m.x*T.s; T.ty=e.clientY-m.y*T.s;
  draw();
},{passive:false});

function showDetail(n){
  let h='<h3>'+n.name+'</h3>';
  if(n.desc) h+='<p>'+n.desc+'</p>';
  h+='<ul>';
  links.forEach(l=>{
    if(l.s===n) h+='<li><b>'+l.label+'</b> → '+l.t.name+(l.note?' <span class="dim">('+l.note+')</span>':'')+'</li>';
    if(l.t===n) h+='<li><span class="dim">←</span> '+l.s.name+' <b>'+l.label+'</b></li>';
  });
  h+='</ul>';
  detail.innerHTML=h;
}

resize();
step();
</script>
</body>
</html>
"""

out = html_page.replace("__DATA__", data)
open("m3kg.html", "w", encoding="utf-8").write(out)
print(f"已生成 m3kg.html: {len(nodes)} 个实体, {len(links)} 条关系" +
      (f", 跳过缺字段 {skipped} 条" if skipped else ""))
