"""Shared data-presentation pieces for grindwright's pages (grind_report.py, grw_status.py).

A "generated at" stamp (relative, absolute in the title), empty states, long text that expands, and a small
vanilla-JS enhancer: any element marked data-ui (a table, or a list whose children are rows) gets a filter box,
sortable headers (th[data-sort], aria-sort), and paging (page size, prev/next, "showing X-Y of N", page in the
URL hash). State is kept per id, so a page that redraws itself every few seconds keeps its page, filter and
sort; call RUI.enhance() after each redraw. Without JS every row shows. Standard library only.
"""
import html
from datetime import datetime, timezone

CSS = """
:focus-visible{outline:2px solid var(--t,var(--acc));outline-offset:2px}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important;scroll-behavior:auto!important}}
.n,td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
thead th{position:sticky;top:0;background:var(--card);z-index:1}
th[data-sort] button{all:inherit;cursor:pointer;padding:0}
th[aria-sort=ascending] button::after{content:" \\25B2"}th[aria-sort=descending] button::after{content:" \\25BC"}
.rui-tools{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 8px;font-size:12px;color:var(--mute)}
.rui-tools input,.rui-tools select,.rui-tools button,.retry{font:inherit;font-size:13px;padding:3px 8px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink);min-height:30px}
.rui-tools button:disabled{opacity:.45}.rui-count{margin-left:auto;font-variant-numeric:tabular-nums}
.empty{border:1px dashed var(--line);border-radius:10px;padding:12px;color:var(--mute)}
.gen{color:var(--mute);font-size:12px}.clip summary{cursor:pointer;color:var(--mute);list-style:none}.clip summary::-webkit-details-marker{display:none}
.clip[open] .more-l{display:none}.err{color:var(--bad)}
.loading{color:var(--mute)}.loading::before{content:"";display:inline-block;width:10px;height:10px;margin-right:6px;border:2px solid var(--line);border-top-color:var(--t,var(--acc));border-radius:50%;animation:rui-spin 1s linear infinite;vertical-align:-1px}
@keyframes rui-spin{to{transform:rotate(360deg)}}
@media (max-width:600px){.rui-count{margin-left:0}}
"""

JS = r"""<script>
(function(){
var S={};
function rel(d){var s=(Date.now()-d)/1000,a=Math.abs(s),u=[[60,'s',1],[3600,'min',60],[86400,'h',3600],[2592000,'d',86400],[1e12,'mo',2592000]];
for(var i=0;i<u.length;i++)if(a<u[i][0]){var v=Math.round(a/u[i][2]);return s>=0?v+' '+u[i][1]+' ago':'in '+v+' '+u[i][1]}return''}
function stamps(){document.querySelectorAll('time[data-rel]').forEach(function(t){var d=Date.parse(t.getAttribute('datetime'));
if(!isNaN(d)){if(!t.title)t.title=t.textContent;t.textContent=(t.dataset.rel||'')+rel(d)}})}
function key(r,i,t){var c=r.children[i];if(!c)return'';var v=c.getAttribute('data-v');if(v===null)v=c.textContent.trim();
return t==='num'?(parseFloat(String(v).replace(/[^0-9.\-]/g,''))||0):v.toLowerCase()}
function hashGet(id){var m=location.hash.match(new RegExp('[#&]'+id+'=(\\d+)'));return m?+m[1]:1}
function hashSet(id,p){var h=location.hash.replace(/^#/,'').split('&').filter(function(x){return x&&x.indexOf(id+'=')!==0});
if(p>1)h.push(id+'='+p);history.replaceState(null,'',h.length?'#'+h.join('&'):location.pathname+location.search)}
function one(box){if(box.dataset.rui)return;box.dataset.rui='1';
var id=box.id,st=S[id]||(S[id]={page:hashGet(id),q:'',size:+box.dataset.page||25,col:-1,asc:true}),
body=box.tagName==='TABLE'?box.tBodies[0]:box,rows=[].slice.call(body.children);if(!rows.length)return;
var bar=document.createElement('div');bar.className='rui-tools';
bar.innerHTML=(rows.length>8?'<label>Filter <input type="search" aria-controls="'+id+'"></label>':'')+
(rows.length>st.size||st.size<25?'<label>Rows <select><option>10</option><option>25</option><option>50</option><option>100</option></select></label>'+
'<button type="button" data-d="-1" aria-label="Previous page">Prev</button><button type="button" data-d="1" aria-label="Next page">Next</button>':'')+
'<span class="rui-count" role="status" aria-live="polite"></span>';
box.parentNode.insertBefore(bar,box);
var inp=bar.querySelector('input'),sel=bar.querySelector('select'),cnt=bar.querySelector('.rui-count'),btn=bar.querySelectorAll('button');
if(inp){inp.value=st.q;if(st.focus){inp.focus();inp.setSelectionRange(st.q.length,st.q.length)}}
if(sel){sel.value=String(st.size);if(sel.value!==String(st.size)){var o=document.createElement('option');o.textContent=st.size;sel.prepend(o);sel.value=String(st.size)}}
var ths=box.tagName==='TABLE'?[].slice.call(box.querySelectorAll('thead th')):[];
function sort(){if(st.col<0)return;var t=ths[st.col].dataset.sort;ths.forEach(function(h){if(h.hasAttribute('data-sort'))h.setAttribute('aria-sort','none')});
ths[st.col].setAttribute('aria-sort',st.asc?'ascending':'descending');
rows.sort(function(x,y){var p=key(x,st.col,t),r=key(y,st.col,t);return(p<r?-1:p>r?1:0)*(st.asc?1:-1)});rows.forEach(function(r){body.appendChild(r)})}
function draw(){var q=st.q.toLowerCase(),shown=rows.filter(function(r){return!q||r.textContent.toLowerCase().indexOf(q)>=0});
var n=shown.length,pages=Math.max(1,Math.ceil(n/st.size));st.page=Math.min(Math.max(1,st.page),pages);var a=(st.page-1)*st.size;
rows.forEach(function(r){r.hidden=true});shown.slice(a,a+st.size).forEach(function(r){r.hidden=false});
cnt.textContent=n?('Showing '+(a+1)+'-'+Math.min(a+st.size,n)+' of '+n+(n<rows.length?' (filtered from '+rows.length+')':'')):'No rows match the filter. Clear it to see all '+rows.length+'.';
if(btn.length){btn[0].disabled=st.page<=1;btn[1].disabled=st.page>=pages}hashSet(id,st.page)}
if(inp){inp.oninput=function(){st.q=inp.value;st.page=1;draw()};inp.onfocus=function(){st.focus=1};inp.onblur=function(){st.focus=0}}
if(sel)sel.onchange=function(){st.size=+sel.value;st.page=1;draw()};
btn.forEach(function(b){b.onclick=function(){st.page+=+b.dataset.d;draw()}});
ths.forEach(function(th,i){if(!th.hasAttribute('data-sort'))return;if(!th.hasAttribute('aria-sort'))th.setAttribute('aria-sort','none');
var b=document.createElement('button');b.type='button';b.innerHTML=th.innerHTML;th.textContent='';th.appendChild(b);
b.onclick=function(){st.asc=st.col===i?!st.asc:true;st.col=i;sort();st.page=1;draw()}});
sort();draw()}
window.RUI={enhance:function(){document.querySelectorAll('[data-ui]').forEach(one);stamps()},rel:rel};
window.addEventListener('hashchange',function(){Object.keys(S).forEach(function(id){S[id].page=hashGet(id)});
document.querySelectorAll('[data-ui]').forEach(function(b){var t=b.previousElementSibling;if(t&&t.className==='rui-tools')t.remove();delete b.dataset.rui});RUI.enhance()});
RUI.enhance();setInterval(stamps,30000)})();
</script>"""


def stamp(now=None, label="Generated "):
    """A <time> with the absolute build time; the script turns its text into 'Generated 5 min ago'."""
    now = now or datetime.now(timezone.utc).astimezone()
    absolute = now.strftime("%Y-%m-%d %H:%M")
    return (f'<time class="gen" datetime="{now.isoformat(timespec="seconds")}" data-rel="{html.escape(label, quote=True)}" '
            f'title="{absolute}">{html.escape(label)}{absolute}</time>')


def empty(what, next_step):
    """An empty state that says what is missing and what to do next."""
    return f'<p class="empty"><b>{html.escape(what)}</b> {html.escape(next_step)}</p>'


def clip(text, limit=220):
    """Long text cut at `limit` characters with a native expander for the rest; short text unchanged."""
    text = text or ""
    if len(text) <= limit:
        return html.escape(text)
    return (f'<details class="clip"><summary>{html.escape(text[:limit])}<span class="more-l">... more</span></summary>'
            f'{html.escape(text[limit:])}</details>')


def rel_time(iso, text=None):
    """A date shown as written, absolute in the title, relative once the script runs."""
    iso = iso or ""
    shown = text if text is not None else iso[:16].replace("T", " ")
    return (f'<time data-rel="" datetime="{html.escape(iso, quote=True)}" title="{html.escape(shown, quote=True)}">'
            f'{html.escape(shown)}</time>')
