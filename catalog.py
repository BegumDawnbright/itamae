#!/usr/bin/env python3
"""Builds a catalogue of every in-game object from the game source itself,
so the sheet can never drift from what the game actually draws."""
import re, sys, pathlib

src_path = pathlib.Path(sys.argv[1])
src = src_path.read_text(encoding="utf-8")

start = src.index("const svg = body")
end = src.index("const FINAL_IDS")
defs = src[start:end]

STYLE = """
:root{
  --bg:#12161c; --panel:#1f242a; --panel-alt:#262d33; --rice:#f3e9d2;
  --salmon:#f2907a; --wasabi:#7fa84c; --gold:#e8a33d;
  --text:#f3efe6; --muted:#9ba3a8; --border:rgba(243,233,210,0.12);
}
*{box-sizing:border-box}
body{
  margin:0;padding:22px 16px 48px;color:var(--text);
  font-family:"Zen Maru Gothic",system-ui,sans-serif;
  background:radial-gradient(120% 80% at 50% -10%,#1b2534 0%,transparent 60%),var(--bg);
}
.sheet{max-width:1000px;margin:0 auto;display:flex;flex-direction:column;gap:26px}
h1{font-family:"Shippori Mincho",serif;font-size:1.5rem;margin:0;color:var(--rice);font-weight:700}
.lede{margin:6px 0 0;color:var(--muted);font-size:0.85rem;max-width:62ch;line-height:1.5}
section{display:flex;flex-direction:column;gap:12px}
h2{font-family:"Shippori Mincho",serif;font-size:1.05rem;margin:0;color:var(--rice);font-weight:500}
h2 small{color:var(--muted);font-family:"Zen Maru Gothic",sans-serif;font-size:0.72rem;font-weight:400;margin-left:8px}
.grid{display:grid;gap:11px;grid-template-columns:repeat(auto-fill,minmax(150px,1fr))}
.card{
  background:var(--panel);border:1px solid var(--border);border-radius:11px;
  padding:12px 10px;display:flex;flex-direction:column;align-items:center;gap:8px;text-align:center;
}
.card.final{border-color:rgba(232,163,61,0.35)}
.card.mid{border-color:rgba(127,168,76,0.3)}
.box{
  width:76px;height:76px;border-radius:12px;display:flex;align-items:center;justify-content:center;
  border:1px solid rgba(0,0,0,0.3);
  box-shadow:0 2px 0 rgba(0,0,0,.35),inset 0 1px 0 rgba(255,255,255,.1);
}
.name{font-size:0.82rem;line-height:1.25}
.made{font-size:0.66rem;color:var(--muted);line-height:1.3}
.recipe{display:flex;align-items:center;gap:4px;flex-wrap:wrap;justify-content:center}
.chip{
  width:30px;height:30px;border-radius:7px;background:#161b1f;
  display:flex;align-items:center;justify-content:center;border:1px solid var(--border);
}
.op{color:var(--muted);font-size:0.75rem;font-family:"JetBrains Mono",monospace}
svg.ic{display:block;width:100%;height:100%}
.box > svg.ic{width:74%;height:74%}
.chip > svg.ic{width:78%;height:78%}

/* composed sushi piece, same construction the game uses */
.piece{position:relative;width:82%;height:82%}
.p-rice{position:absolute;left:8%;right:8%;bottom:6%;height:44%;
  border-radius:50% 50% 35% 35% / 70% 70% 30% 30%;
  box-shadow:0 2px 2px rgba(0,0,0,.3), inset 0 -3px 0 rgba(0,0,0,.08)}
.p-nori{position:absolute;left:8%;right:8%;bottom:24%;height:14%;border-radius:2px}
.p-toppings{position:absolute;top:2%;left:0;right:0;display:flex;justify-content:center;gap:3%}
.p-top{width:38%;aspect-ratio:1;border-radius:50%;display:flex;align-items:center;justify-content:center;
  background:#11161a;box-shadow:0 1px 2px rgba(0,0,0,.4);border:1.5px solid rgba(243,233,210,.25);overflow:hidden}
.p-top svg.ic{width:86%;height:86%}
.chip .piece{width:94%;height:94%}
.chip .p-rice{left:18%;right:18%;bottom:3%;height:32%}
.chip .p-nori{left:18%;right:18%;bottom:16%;height:10%}
.chip .p-top{width:48%;border-width:1px}
footer{color:var(--muted);font-size:0.72rem;text-align:center}
@media (max-width:520px){
  .grid{grid-template-columns:repeat(auto-fill,minmax(124px,1fr));gap:9px}
  .box{width:64px;height:64px}
}
"""

BODY = """
<div class="sheet">
  <header>
    <h1>Itamae — Malzeme ve Tarif Kataloğu</h1>
    <p class="lede">Oyundaki her nesnenin görseli, adı ve nasıl elde edildiği.
      Görseller doğrudan oyunun kaynağından alınır, oyunda gördüğünün birebir aynısıdır.</p>
  </header>
  <section><h2>Ham Malzemeler <small>tezgaha bunlar düşer</small></h2><div class="grid" id="rawGrid"></div></section>
  <section><h2>Ara Ürünler <small>birleştirince oluşur, sipariş olmaz</small></h2><div class="grid" id="midGrid"></div></section>
  <section><h2>Sushiler <small>siparişlerde bunlar istenir</small></h2><div class="grid" id="finalGrid"></div></section>
  <footer>Bir ürünün kimliği, içindeki ham malzeme kümesidir — hangi sırayla birleştirdiğin fark etmez.</footer>
</div>
"""

SCRIPT = """
(function(){
%s

const RECIPE={};
Object.keys(COMBOS).forEach(k=>{ RECIPE[COMBOS[k]]=k.split("+"); });

function pieceHTML(id){
  const comps=COMPONENTS[id]||[];
  const tops=comps.filter(c=>c!=="PR"&&c!=="NR");
  let h='<div class="piece">';
  if(comps.includes("PR")) h+=`<div class="p-rice" style="background:${ITEMS.PR.bg}"></div>`;
  if(comps.includes("NR")) h+=`<div class="p-nori" style="background:${ITEMS.NR.bg}"></div>`;
  if(tops.length){
    h+='<div class="p-toppings">';
    tops.slice(0,3).forEach(t=>{ h+=`<div class="p-top">${ITEMS[t].icon}</div>`; });
    h+='</div>';
  }
  return h+'</div>';
}

const visual=id=>ITEMS[id].tier==="raw" ? ITEMS[id].icon : pieceHTML(id);
const boxStyle=id=>ITEMS[id].tier==="raw"
  ? `background:${ITEMS[id].bg}26;border-color:${ITEMS[id].bg}59;`
  : "background:var(--panel-alt);";

function recipeHTML(id){
  const pair=RECIPE[id];
  if(!pair) return '<span class="made">tezgaha hazır düşer</span>';
  return '<div class="recipe">'
    + `<div class="chip">${visual(pair[0])}</div><span class="op">+</span>`
    + `<div class="chip">${visual(pair[1])}</div><span class="op">=</span>`
    + `<div class="chip">${visual(id)}</div></div>`
    + `<span class="made">${ITEMS[pair[0]].name} + ${ITEMS[pair[1]].name}</span>`;
}

function card(id){
  const it=ITEMS[id];
  const extra = it.tier==="raw"
    ? (id==="PR" ? '<span class="made">tencerede haşlayınca çıkar</span>'
                 : '<span class="made">tezgaha düşer</span>')
    : recipeHTML(id);
  return `<div class="card ${it.tier}">
      <div class="box" style="${boxStyle(id)}">${visual(id)}</div>
      <span class="name">${it.name}</span>${extra}</div>`;
}

const byTier=t=>Object.keys(ITEMS).filter(id=>ITEMS[id].tier===t);
document.getElementById("rawGrid").innerHTML   = byTier("raw").map(card).join("");
document.getElementById("midGrid").innerHTML   = byTier("mid").map(card).join("");
document.getElementById("finalGrid").innerHTML = byTier("final").map(card).join("");
})();
""" % defs

head = ('<title>Itamae Katalog</title>\n'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
        'family=Shippori+Mincho:wght@500;700&family=Zen+Maru+Gothic:wght@400;500;700'
        '&family=JetBrains+Mono:wght@500&display=swap">\n'
        f"<style>{STYLE}</style>\n")

artifact = head + BODY + f"\n<script>{SCRIPT}</script>\n"
pathlib.Path(sys.argv[2]).write_text(artifact, encoding="utf-8")

if len(sys.argv) > 3:
    full = ('<!doctype html>\n<html lang="tr">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            + head + "</head>\n<body>\n" + BODY
            + f"\n<script>{SCRIPT}</script>\n</body>\n</html>\n")
    pathlib.Path(sys.argv[3]).write_text(full, encoding="utf-8")

print("catalogue built")
