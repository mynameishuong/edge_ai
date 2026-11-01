"""Explain every model line plus the C++ loader/scorer. Does not edit runtime/model."""
import csv
import hashlib
from html import escape
import json
import math
from pathlib import Path
import struct

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs'/'inspect'
FEATURES=['fps','unique_ids','id_entropy','max_id_share','byte_mean','byte_std','bit_flip_mean','same_id_iat_ms']
NOTES={
135:'Hàm c(n) hiệu chỉnh path length theo số training samples còn lại ở leaf.',
136:'n≤1: leaf đã cô lập tối đa một training sample, correction bằng 0.',
137:'n=2: correction bằng 1.',
138:'Với n>2 dùng công thức xấp xỉ average path length; Euler gamma = 0.5772156649.',
139:'Kết thúc hàm correction; giá trị trả về được scorer dùng khi tới leaf và khi chuẩn hóa.',
140:'Node chứa 5 field: child trái/phải, feature index, split threshold, số training samples.',
141:'Forest giữ model trong RAM và cung cấp scorer.',
142:'Vector ngoài là các cây; mỗi vector trong chứa Node của một cây.',
143:'max_samples dùng chuẩn hóa path; threshold là ngưỡng anomaly, không phải ngưỡng split node.',
144:'Whitelist CAN ID phục vụ rule unknown_id; không phải node của cây.',
145:'Constructor nhận path model. Một lần tạo Forest đọc file một lần.',
146:'Mở file text stream. magic giữ tên/version của format; nếu mở lỗi thì bước đọc header sẽ fail.',
147:'nf=feature count, nt=tree count, nids=whitelist count; window tính microsecond.',
148:'Đọc 7 token header theo thứ tự. Operator >> bỏ whitespace/newline; thiếu token làm guard fail.',
149:'Bắt buộc magic đúng; nf=NF=8; window=WINDOW_US=100000 của binary.',
150:'Giới hạn nt=1..1024, max_samples=2..65536, nids=1..2048 để reject header sai.',
151:'Anomaly threshold phải finite và thuộc [0,1].',
152:'Header/schema sai thì ném lỗi; không tiếp tục load/inference.',
153:'Đọc nids ID theo decimal; kiểm 11-bit; insert vào set whitelist.',
154:'Lặp nt lần. Model này nt=64, tức 64 cây.',
155:'Đọc node_count của cây; kiểm size 1..2*max_samples trước cấp phát.',
156:'Cấp vector count Node. Index của node là thứ tự dòng node trong cây, bắt đầu 0.',
157:'Lặp qua từng node j. j reset về 0 cho mỗi cây mới.',
158:'Tham chiếu slot tree[j] để điền trực tiếp dữ liệu.',
159:'Đọc 5 token left, right, feature, threshold, samples vào Node.',
160:'Split threshold phải finite; samples trong 1..max_samples.',
161:'Node thiếu token/sai giá trị thì ném lỗi.',
162:'Leaf khi cả left và right đều -1. Feature/threshold sentinel không dùng để so nhánh.',
163:'Internal node phải có child sau j, nằm trong vector; feature trong 0..7. Chặn index sai/vòng lặp.',
164:'Topology sai thì ném lỗi thay vì tiếp tục chạy cây.',
165:'Đóng vòng đọc các node của cây hiện tại; cây đã có đủ count node.',
166:'Move vector cây vào trees: chuyển ownership, tránh copy toàn bộ node.',
167:'Đóng vòng nt cây; Forest hiện đã giữ toàn bộ model trong RAM.',
168:'Kết thúc constructor; caller có thể bắt đầu chấm vector mà không đọc lại file.',
169:'score(x) chấm một mảng 8 feature bằng dữ liệu model đã nằm trong RAM. const không sửa model.',
170:'Reject vector có NaN hoặc Inf trước khi so split threshold.',
171:'Khởi tạo tổng effective path length bằng 0.',
172:'Duyệt từng cây bằng const reference, không copy và không đọc lại file.',
173:'Mỗi cây bắt đầu tại root index 0, depth=0.',
174:'Còn left khác -1 tức chưa tới leaf, tiếp tục đi cây.',
175:'Lấy node hiện tại; x[feature]≤threshold đi left, ngược lại đi right; tăng depth một cạnh.',
176:'Đóng vòng đi nhánh; idx hiện trỏ leaf, depth là số cạnh đã đi từ root.',
177:'Tới leaf: cộng depth + c(samples ở leaf) vào tổng của toàn forest.',
178:'Kết thúc xử lý cây; quay lại cây tiếp theo cho tới hết forest.',
179:'Trả score = 2^(-total / (số cây*c(max_samples))). Score cao hơn nghĩa bất thường hơn.',
180:'Kết thúc hàm score. Không sửa node/samples/threshold đã load.',
181:'Kết thúc khai báo struct Forest.',
184:'Detector giữ const reference đến Forest. Không copy/load lại model mỗi window.',
189:'Gắn model reference và realtime flag cho Detector.',
193:'Window có frame mới gọi model.score(x); timer chỉ đo quanh bước này. Window rỗng dùng score=0.',
195:'Hard rule: ID ngoài whitelist hoặc fps>1800. Ngưỡng 1800 nằm trong code demo, không nằm trong forest.',
196:'abnormal = hard rule OR score lớn hơn anomaly threshold đọc từ header model.',
197:'Ưu tiên reason unknown_id, possible_flooding, ml_anomaly, normal.',
260:'main là điểm vào logic C++ sau khi OS/C++ runtime khởi tạo executable; argc tính cả tên binary.',
262:'Chạy chỉ ./build/ai-vids chưa đủ argument: code in usage qua lỗi và return 1.',
263:'argv[1] chọn mode features/score/replay/capture.',
271:'Mode score dùng feature CSV đã trích sẵn, không xử lý raw frame.',
272:'Ở mode score: model là argv[2]; feature CSV là argv[3]. Load Forest một lần.',
277:'Chấm x và in scalar. Không gọi rule hoặc state machine trong mode score.',
279:'Nhánh replay đọc raw CAN CSV.',
280:'Model ở argv[3] load vào m; Extractor tham chiếu whitelist; Detector tham chiếu m. Cả ba sống tới hết nhánh.',
281:'CSV argv[2] → Frame → Extractor → Window → Detector.emit; callback cùng luồng.',
282:'Nhánh capture nhận từ interface Linux thay vì CSV.',
284:'Model argv[3] load một lần rồi truyền const reference vào capture(argv[2], m).',
289:'Thoát bình thường trả 0 cho shell.',
290:'Bắt lỗi, in stderr với prefix ai-vids và return 1.',
}
def correction(n):
    return 0.0 if n<=1 else 1.0 if n==2 else 2*(math.log(n-1)+0.5772156649015329)-2*(n-1)/n

def build():
    raw=(ROOT/'models'/'demo.forest').read_text().splitlines();h=raw[0].split()
    meta=dict(magic=h[0],nf=int(h[1]),tree_count=int(h[2]),max_samples=int(h[3]),threshold=float(h[4]),window_us=int(h[5]),id_count=int(h[6]))
    records=[
      dict(line=1,raw=raw[0],tree=None,kind='header',why=f'{h[0]}: format/version. nf={h[1]} feature; nt={h[2]} cây; max_samples={h[3]} training windows/cây; anomaly threshold={h[4]}; window={h[5]} µs; whitelist count={h[6]}.'),
      dict(line=2,raw=raw[1],tree=None,kind='whitelist',why='Đọc số decimal: '+', '.join(f'{v} = 0x{int(v):03X}' for v in raw[1].split())+'. Dùng cho rule ID; không phải nhãn attack hoặc node.')
    ]
    pos=2;trees=[];stats=[]
    for ti in range(meta['tree_count']):
        count=int(raw[pos]);count_line=pos+1;pos+=1;first=pos+1;tree=[]
        records.append(dict(line=count_line,raw=raw[count_line-1],tree=ti,kind='count',
           why=f'Cây index {ti} (cây thứ {ti+1}) có {count} node. Node index 0..{count-1}; root ở dòng {first}; đọc đủ {count} dòng trước count của cây sau.'))
        for ni in range(count):
            a=raw[pos].split();left,right,feature=int(a[0]),int(a[1]),int(a[2]);split=float(a[3]);samples=int(a[4])
            leaf=left==right==-1
            rec=dict(line=pos+1,raw=raw[pos],tree=ti,node=ni,left=left,right=right,feature=feature,split=split,samples=samples,kind='leaf' if leaf else 'internal')
            if leaf:
                rec['why']=f'Cây {ti}, node {ni}: LEAF vì left=right=-1. feature={feature}, split={a[3]} là sentinel, không so sánh. samples={samples} là số training windows ở leaf; thêm c({samples})={correction(samples):.9f} vào depth. Leaf không chứa nhãn normal/attack.'
            else:
                rec['why']=f'Cây {ti}, node {ni}'+(' ROOT' if ni==0 else '')+f': if x[{feature}] ({FEATURES[feature]}) ≤ {a[3]} thì đi node {left} (dòng {first+left}); nếu lớn hơn thì node {right} (dòng {first+right}). samples={samples} là training windows tại node, không phải số CAN frame hiện tại.'
            records.append(rec);tree.append(rec);pos+=1
        trees.append(tree);stats.append(dict(tree=ti,count=count,count_line=count_line,first_line=first,last_line=pos))
    assert pos==len(raw)==len(records)
    meta.update(lines=len(raw),nodes=sum(len(t) for t in trees),trees=stats)
    with (ROOT/'data'/'demo_features.csv').open(newline='') as f:
        row=next(r for r in csv.DictReader(f) if int(r['t_us'])==40800000)
    x=[struct.unpack('f',struct.pack('f',float(row[k])))[0] for k in FEATURES]
    paths=[];lengths=[]
    for ti,tree in enumerate(trees):
        idx=0;steps=[]
        while tree[idx]['left']!=-1:
            n=tree[idx];left=x[n['feature']]<=n['split']
            steps.append(dict(line=n['line'],node=idx,feature=FEATURES[n['feature']],value=x[n['feature']],split=n['split'],direction='left' if left else 'right',next=n['left'] if left else n['right']))
            idx=n['left'] if left else n['right']
        leaf=tree[idx];length=len(steps)+correction(leaf['samples']);lengths.append(length)
        paths.append(dict(tree=ti,steps=steps,leaf=leaf,depth=len(steps),correction=correction(leaf['samples']),effective=length))
    score=2**(-sum(lengths)/(len(trees)*correction(meta['max_samples'])))
    assert abs(score-0.4615071300611855)<1e-12
    lines=(ROOT/'src'/'main.cpp').read_text(encoding='utf-8').splitlines()
    source=[dict(line=n,raw=lines[n-1],why=why) for n,why in sorted(NOTES.items())]
    trace=dict(features=dict(zip(FEATURES,x)),paths=paths,total=sum(lengths),mean=sum(lengths)/len(trees),normalizer=correction(meta['max_samples']),score=score,threshold=meta['threshold'])
    return dict(meta=meta,records=records,source=source,trace=trace,
                source_sha256=hashlib.sha256((ROOT/'src'/'main.cpp').read_bytes()).hexdigest(),
                model_sha256=hashlib.sha256((ROOT/'models'/'demo.forest').read_bytes()).hexdigest())

HTML=r'''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI-VIDS · Binary/model từng dòng</title>
<style>:root{--ink:#16374e;--muted:#527086;--line:#cbdce5;--green:#087e76}*{box-sizing:border-box}body{margin:0;background:#eef4f7;color:var(--ink);font:15px/1.6 'Segoe UI',sans-serif}main{max-width:1480px;margin:auto;padding:26px}h1{font-size:31px;line-height:1.2}h2{font-size:21px}p{color:var(--muted)}nav,.controls{display:flex;gap:9px;flex-wrap:wrap;margin:20px 0}button,select,input{font:inherit}button{cursor:pointer}nav button,select,input,.pager button{border:1px solid var(--line);background:white;color:var(--ink);padding:9px 13px;border-radius:6px}nav .active{background:var(--green);color:white}.panel{background:white;border:1px solid var(--line);border-radius:11px;padding:20px;margin:15px 0;min-width:0}.note{padding:14px 17px;background:#fff5db;border-left:4px solid #bf881a;border-radius:5px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:15px}.hidden{display:none}.wrap{overflow-x:auto;background:white;border:1px solid var(--line);border-radius:8px}table{width:100%;border-collapse:collapse;font-size:13px}.wrap table{min-width:850px}th,td{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid var(--line)}th{background:#173d54;color:white}tr:nth-child(even){background:#f5f9fa}.ln{width:65px;color:var(--green);font-family:Consolas,monospace}.raw{width:43%;white-space:pre-wrap;font:12px/1.6 Consolas,monospace;overflow-wrap:anywhere}.why{width:51%;overflow-wrap:anywhere}.link{border:0;background:none;color:var(--green);padding:0;text-decoration:underline;text-align:left}.controls input{flex:1;min-width:180px;max-width:100%}select{max-width:100%}.pager{display:flex;gap:14px;align-items:center;margin:14px 0}.focus{background:#fff0b9!important}pre{background:#eaf1f5;padding:15px;border-radius:7px;white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.6 Consolas,monospace}.sub{font-size:12px;color:var(--muted);overflow-wrap:anywhere}a{color:var(--green)}footer{margin:22px 0;font-size:12px;color:var(--muted)}@media(max-width:800px){main{padding:17px}.grid{grid-template-columns:1fr}h1{font-size:25px}}</style>
<main><div class="sub">AI–VIDS / BINARY + MODEL · 01/11/2026</div><h1>ai-vids chạy thuật toán.<br>demo.forest cung cấp dữ liệu đã train.</h1><p>Đọc một chỗ: C++ loader/scorer có chú giải từng dòng; toàn bộ 7.514 dòng model; trace thực qua cả 64 cây.</p><nav><button class="active" data-tab="overview">1 · Hai file phối hợp</button><button data-tab="source">2 · C++ từng dòng</button><button data-tab="model">3 · Model từng dòng</button><button data-tab="trace">4 · Trace score thực</button></nav>
<section id="overview"><div class="note">./build/ai-vids là binary được compile từ src/main.cpp, không phải file source text. Chú giải C++ bên dưới tập trung vào main, loader/scorer và điểm quyết định dùng model.</div><div class="grid"><div class="panel"><h2>Executable chứa logic</h2><pre>src/main.cpp + CMakeLists.txt + compiler/linker
→ build/ai-vids</pre><p>Parse arguments, frame, window, feature, inference, rule, state và JSON. Sửa logic C++ cần build lại executable đúng OS/CPU.</p></div><div class="panel"><h2>Model chứa tham số</h2><pre>Train normal windows trên PC
→ export tree nodes + threshold
→ models/demo.forest</pre><p>64 cây, 7.448 node; loader đọc một lần khi khởi tạo Forest. Từng window dùng dữ liệu đã nằm trong RAM.</p></div></div><div class="panel"><h2>Luồng replay</h2><pre>argv[1] = replay
argv[2] = data/demo.csv
argv[3] = models/demo.forest
argv[4] = --realtime

main → Forest(argv[3]) → đọc header/IDs/cây → RAM
     → Extractor(model.whitelist) + Detector(model)
     → CSV → Frame → window → x[8] → Forest.score(x)
     → score + anomaly threshold + rule → state → JSON</pre><p>Không load lại 7.514 dòng mỗi lần score. Sửa model trên disk không tự reload process đang chạy. Có thể thay model tương thích mà không build lại binary, nhưng phải version/validate.</p><button class="link" onclick="sourceJump(280)">Mở đúng dòng main tạo Forest/Extractor/Detector →</button></div><div class="panel"><h2>Ba loại số dễ nhầm</h2><table><tr><th>Giá trị</th><th>Vai trò</th></tr><tr><td>threshold 0.608136… ở header</td><td>Ngưỡng quyết định anomaly của model bundle.</td></tr><tr><td>threshold 2.908064… ở node</td><td>Ngưỡng split feature để đi trái/phải.</td></tr><tr><td>samples 128/30… ở node</td><td>Số training windows tại node/leaf; không phải frame hiện tại.</td></tr></table></div><p class="sub">Source SHA-256: __SH__<br>Model SHA-256: __MH__<br>Nguồn thuật toán tham chiếu: <a href="https://github.com/scikit-learn/scikit-learn/blob/main/sklearn/ensemble/_iforest.py">scikit-learn _iforest.py</a>. Các số và dòng trong viewer lấy từ model/source của dự án.</p></section>
<section id="source" class="hidden"><h2>Source tạo binary: từng dòng liên quan model</h2><p>Giữ nguyên dòng C++ gốc; không thêm comment vào file runtime. Có cả guard lỗi để thấy khi nào model bị từ chối.</p><div class="wrap"><table><thead><tr><th>Dòng C++</th><th>Source nguyên văn</th><th>Ý nghĩa</th></tr></thead><tbody id="source-rows"></tbody></table></div></section>
<section id="model" class="hidden"><h2>Toàn bộ model có chú giải</h2><div class="note">left/right là node index trong từng cây, không phải số dòng file. Bấm nhánh để nhảy tới child. Parser >> đọc token theo whitespace, còn số dòng ở đây để bạn tra cứu.</div><div class="controls"><select id="tree-filter"></select><select id="kind-filter"><option value="all">Mọi loại dòng</option><option value="header">Header</option><option value="whitelist">Whitelist</option><option value="count">Node count</option><option value="internal">Internal node</option><option value="leaf">Leaf</option></select><input id="search" placeholder="Tìm số, feature hoặc lời giải thích…"></div><p id="count" class="sub"></p><div class="pager"><button id="prev">← Trước</button><span id="page-label"></span><button id="next">Sau →</button></div><div class="wrap"><table><thead><tr><th>Dòng file</th><th>Nguyên văn</th><th>Giải thích từng field / nhánh</th></tr></thead><tbody id="model-rows"></tbody></table></div></section>
<section id="trace" class="hidden"><h2>92 frame ở 40,8–40,9 s → score 0,461507</h2><p>Input tái dựng từ CSV/model gốc, cast float32 giống C++ runtime. Bấm dòng/node để mở đúng chỗ trong model.</p><div class="grid"><div class="panel"><h2>Input vector</h2><pre id="features"></pre></div><div class="panel"><h2>Tổng 64 cây</h2><pre id="result"></pre><p>Code lấy tổng effective path rồi chuẩn hóa/lũy thừa; không lấy trung bình score từng cây.</p></div></div><div class="controls"><select id="trace-tree"></select></div><div class="wrap"><table><thead><tr><th>Dòng / node</th><th>So sánh</th><th>Đi tới</th></tr></thead><tbody id="trace-rows"></tbody></table></div><div id="leaf" class="panel"></div></section><footer>Đây là chú giải snapshot. Score không phải xác suất tấn công; model demo vẫn còn hạn chế payload shift. Viewer mở offline, không cần server, không thay model hay triển khai lên thiết bị.</footer></main>
<script>const D=__DATA__;const $=id=>document.getElementById(id);let pg=0,focus=null;const SIZE=200;function el(tag,txt,cls){const x=document.createElement(tag);if(txt!==undefined)x.textContent=txt;if(cls)x.className=cls;return x}function show(tab){document.querySelectorAll('main>section').forEach(x=>x.classList.toggle('hidden',x.id!==tab));document.querySelectorAll('nav button').forEach(x=>x.classList.toggle('active',x.dataset.tab===tab))}document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>show(b.dataset.tab));function option(s,v,txt){const x=el('option',txt);x.value=v;s.append(x)}
for(const r of D.source){const tr=el('tr');tr.id='source-'+r.line;tr.append(el('td',r.line,'ln'),el('td',r.raw,'raw'),el('td',r.why,'why'));$('source-rows').append(tr)}function sourceJump(line){show('source');document.querySelectorAll('#source-rows tr').forEach(x=>x.classList.remove('focus'));const r=$('source-'+line);r.classList.add('focus');r.scrollIntoView({behavior:'smooth',block:'center'})}
option($('tree-filter'),'0','Cây 0 · 95 node + header');option($('tree-filter'),'all','Toàn file · 7.514 dòng');for(let i=1;i<D.meta.tree_count;i++)option($('tree-filter'),i,'Cây '+i+' · '+D.meta.trees[i].count+' node');for(let i=0;i<D.meta.tree_count;i++)option($('trace-tree'),i,'Trace cây '+i);
function filtered(){const t=$('tree-filter').value,k=$('kind-filter').value,q=$('search').value.trim().toLowerCase();return D.records.filter(r=>(t==='all'||r.tree===Number(t)||r.tree===null)&&(k==='all'||r.kind===k)&&(!q||(r.raw+' '+r.why+' '+r.line).toLowerCase().includes(q)))}function renderModel(){const rows=filtered(),pages=Math.max(1,Math.ceil(rows.length/SIZE));pg=Math.max(0,Math.min(pg,pages-1));$('count').textContent=rows.length+' dòng đang lọc / '+D.meta.lines+' dòng · '+D.meta.nodes+' node · '+D.meta.tree_count+' cây';$('page-label').textContent=(pg+1)+' / '+pages+' · tối đa '+SIZE+' dòng/trang';$('prev').disabled=pg===0;$('next').disabled=pg===pages-1;$('model-rows').replaceChildren();for(const r of rows.slice(pg*SIZE,(pg+1)*SIZE)){const tr=el('tr');tr.id='model-'+r.line;if(r.line===focus)tr.className='focus';tr.append(el('td',r.line,'ln'),el('td',r.raw,'raw'));const td=el('td',r.why,'why');if(r.kind==='internal'){const a=el('p');for(const [label,node]of [['Đi trái',r.left],['Đi phải',r.right]]){const b=el('button',label+' → node '+node,'link');b.style.marginRight='15px';b.onclick=()=>nodeJump(r.tree,node);a.append(b)}td.append(a)}tr.append(td);$('model-rows').append(tr)}}function nodeJump(tree,node){const r=D.records.find(r=>r.tree===tree&&r.node===node);focus=r.line;$('tree-filter').value=String(tree);$('kind-filter').value='all';$('search').value='';pg=Math.floor(filtered().indexOf(r)/SIZE);renderModel();show('model');$('model-'+r.line)?.scrollIntoView({behavior:'smooth',block:'center'})}
function renderTrace(){const t=Number($('trace-tree').value),p=D.trace.paths[t];$('trace-rows').replaceChildren();for(const s of p.steps){const tr=el('tr'),td=el('td'),b=el('button','Dòng '+s.line+' / node '+s.node,'link');b.onclick=()=>nodeJump(t,s.node);td.append(b);tr.append(td,el('td',s.feature+': '+s.value.toPrecision(9)+' '+(s.direction==='left'?'≤':'>')+' '+s.split.toPrecision(10)),el('td',(s.direction==='left'?'Trái':'Phải')+' → node '+s.next));$('trace-rows').append(tr)}$('leaf').replaceChildren(el('h2','Leaf node '+p.leaf.node+' · dòng '+p.leaf.line),el('pre',p.leaf.raw+'\n\ndepth = '+p.depth+'\nleaf samples = '+p.leaf.samples+' training windows\nc(samples) = '+p.correction+'\neffective path = '+p.effective));const b=el('button','Mở leaf trong file model','link');b.onclick=()=>nodeJump(t,p.leaf.node);$('leaf').append(b)}
$('features').textContent=Object.entries(D.trace.features).map(([k,v],i)=>'x['+i+'] '+k+' = '+v).join('\n');$('result').textContent='sum paths = '+D.trace.total+'\nmean path = '+D.trace.mean+'\nc(128) = '+D.trace.normalizer+'\nscore = 2^(-mean/c(128))\n      = '+D.trace.score+'\nanomaly threshold = '+D.trace.threshold+'\n\nWindow này: no hard rule,\nscore < threshold → HEALTHY trong log';for(const id of ['tree-filter','kind-filter'])$(id).onchange=()=>{pg=0;renderModel()};$('search').oninput=()=>{pg=0;renderModel()};$('prev').onclick=()=>{pg--;renderModel()};$('next').onclick=()=>{pg++;renderModel()};$('trace-tree').onchange=renderTrace;renderModel();renderTrace();</script></html>'''

def main():
    OUT.mkdir(parents=True,exist_ok=True);data=build()
    payload=json.dumps(data,ensure_ascii=False).replace('</','<\\/')
    target=OUT/'AI_VIDS_BINARY_MODEL_LINE_BY_LINE.vi.html'
    target.write_text(HTML.replace('__DATA__',payload).replace('__SH__',data['source_sha256']).replace('__MH__',data['model_sha256']),encoding='utf-8')
    (OUT/'binary-model-guide.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    with (OUT/'demo.forest.annotated.vi.tsv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f,delimiter='\t');w.writerow(['file_line','tree','node','raw','explanation_vi'])
        for r in data['records']:w.writerow([r['line'],r['tree'],r.get('node',''),r['raw'],r['why']])
    print(json.dumps({'html':target.name,'model_lines':data['meta']['lines'],'nodes':data['meta']['nodes'],'trees':data['meta']['tree_count'],'source_lines_explained':len(data['source']),'score':data['trace']['score'],'bytes':target.stat().st_size}))

if __name__=='__main__':main()

