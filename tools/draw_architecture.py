"""Create editable code-native SVG architecture; no external rendering dependency."""
from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
plan_path=ROOT/'docs'/'REVIEW_PLAN.json'
plan=json.loads(plan_path.read_text(encoding='utf-8')) if plan_path.exists() else {}
node_meta={node['title']:node for node in plan.get('nodes',[])}
parts = ['''<svg xmlns="http://www.w3.org/2000/svg" width="1680" height="1500" viewBox="0 0 1680 1500" role="img" aria-labelledby="title desc">
<title id="title">AI-VIDS end-to-end architecture</title><desc id="desc">CAN lab and datasets feed a local C++ edge pipeline. An offline training pipeline exports Isolation Forest trees to the edge. Local dashboard shows evidence and metrics. Planned Raspberry Pi production stages are distinguished from the implemented local demo.</desc>
<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#6c97b5"/></marker><marker id="green" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#54e3c2"/></marker></defs>
<rect width="1680" height="1500" rx="18" fill="#0b1424"/>
<style>text{font-family:'Segoe UI',Arial,sans-serif} .h{font-size:19px;font-weight:650;fill:#e7f1fc}.b{font-size:15px;fill:#afc1d8}.tag{font-size:11px;letter-spacing:1.3px;fill:#54e3c2}.label{font-size:13px;fill:#8ca6c0}g:target>rect{stroke:#ffc46b;stroke-width:3}</style>''']


def text(x, y, value, cls='b', **attrs):
    extra = ' '.join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    parts.append(f'<text x="{x}" y="{y}" class="{cls}" {extra}>{escape(value)}</text>')


def box(x, y, w, h, title, lines=(), tag=None, planned=False):
    node=node_meta.get(title)
    if node:
        parts.append(f'<g id="arch-{node["id"]}" data-arch-ref="{node["id"]}">')
        tag=f'{node["id"]} / {node["weight"]}% · {tag or ""}'
    stroke = '#40526b' if planned else '#326c75'
    fill = '#142033' if planned else '#122c37'
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="11" fill="{fill}" stroke="{stroke}"/>')
    ty = y + 29
    if tag:
        text(x+18, y+23, tag, 'tag');ty += 22
    text(x+18, ty, title, 'h')
    for i, line in enumerate(lines):
        text(x+18, ty+27+i*23, line)
    if node:
        parts.append('</g>')


def arrow(points, label=None, lx=0, ly=0, dashed=False, green=False):
    pts = ' '.join(f'{x},{y}' for x,y in points)
    color = '#54e3c2' if green else '#6c97b5'
    dash = 'stroke-dasharray="7 6"' if dashed else ''
    parts.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2" {dash} marker-end="url(#{"green" if green else "arrow"})"/>')
    if label: text(lx, ly, label, 'label')


text(42, 49, 'AI–VIDS / A–Z SYSTEM ARCHITECTURE', 'tag')
text(42, 97, 'Automotive Edge AI Intrusion Detection', 'h', style='font-size:32px')
text(42, 129, 'LOCAL REVIEW v0.1  •  Target: Raspberry Pi 4 / Linux 64-bit  •  No cloud in the inference path')
text(42, 175, 'A  INPUTS & HARDWARE / 18% EFFORT', 'tag')
text(440, 175, 'B  EDGE RUNTIME / 30% EFFORT', 'tag')
text(1240, 175, 'C  EVIDENCE & REVIEW / 22% EFFORT', 'tag')
parts.append('<rect x="420" y="195" width="780" height="804" rx="16" fill="#0d1c2d" stroke="#2d4661"/>')
box(42,210,330,120,'Recorded / synthetic traffic',['CSV frames with source timestamps','Implemented: local replay'],tag='LOCAL · IMPLEMENTED')
box(42,380,330,130,'Isolated Linux lab',['Virtual ECUs → vcan0','Same executable: capture mode'],tag='LINUX · VALIDATION PENDING',planned=True)
box(42,560,330,177,'Physical CAN testbench',['ECU A ── CAN_H / CAN_L ── ECU B','Two bus-end terminators only','USB-CAN controller + transceiver','Pi GPIO cannot read CAN directly'],tag='HARDWARE · PLANNED',planned=True)
box(42,790,330,166,'CAN adapter → Pi 4',['USB-CAN → Linux driver → can0','Monitor: controller listen-only','Inference service never sends CAN','Exact bitrate follows testbench'],tag='RASPBERRY PI · PLANNED',planned=True)
box(450,220,720,110,'Frame acquisition / source adapter',['Local CSV replay  |  Linux SocketCAN receiver','Classic CAN, standard 11-bit, 0–8 bytes in prototype'],tag='C++ · IMPLEMENTED / SOCKETCAN NOT RUNTIME-TESTED')
box(450,370,720,105,'Validate → timestamp → window',['Reject malformed CSV; skip RTR / EFF / error frames on Linux','Monotonic receipt time live; original timestamps on replay'],tag='C++ · IMPLEMENTED')
box(450,515,720,110,'Feature extraction / schema v1',['100 ms tumbling window · 8 global features · float32','Rate / ID diversity / entropy / payload stats / timing'],tag='C++ · SHARED BY TRAINING AND RUNTIME')
box(450,665,345,117,'Isolation Forest',['64 trees · normal-only training','Score high = more anomalous'],tag='C++ · IMPLEMENTED')
box(825,665,345,117,'Rule baseline',['Unknown ID / high frame rate','Demo thresholds only'],tag='C++ · IMPLEMENTED')
box(450,823,720,140,'Decision + health state machine',['HEALTHY → SUSPECT → ALERT; 5 normal windows to clear','2 anomalous windows to confirm; hard rule alerts immediately','NO_DATA for silent windows; rx drop / ignored frame counters'],tag='C++ · IMPLEMENTED')
box(1240,220,396,130,'Review dashboard',['Loopback HTTP server: 127.0.0.1','Traffic / score / state / model P95','Replay UI; live capture UI pending'],tag='REPLAY UI · IMPLEMENTED')
box(1240,405,396,132,'Event stream / evidence',['NDJSON window events implemented','Raw evidence / retention planned','Alert lifecycle / context pending'],tag='WINDOW EVENTS · IMPLEMENTED')
box(1240,590,396,156,'Operational visibility',['Detection delay ≠ model latency','CPU / RAM / temperature / rx drops','False alerts per hour; drift review','No online model self-learning'],tag='PI MEASUREMENTS · PLANNED',planned=True)
box(1240,805,396,151,'Production hardening gate',['Bounded queues + logger rotation','Kernel timestamp / DBC / per-ID model','Supervisor + health + model rollback','Only after user review and approval'],tag='NOT DEPLOYED',planned=True)
arrow([(372,270),(450,270)])
arrow([(372,445),(402,445),(402,300),(450,300)],dashed=True)
arrow([(207,737),(207,790)],dashed=True)
arrow([(372,875),(410,875),(410,315),(450,315)],dashed=True)
arrow([(810,330),(810,370)])
arrow([(810,475),(810,515)])
arrow([(625,625),(625,665)])
arrow([(990,625),(990,665)])
arrow([(625,782),(625,823)])
arrow([(990,782),(990,823)])
arrow([(1170,898),(1218,898),(1218,470),(1240,470)],'events',1178,795)
arrow([(1438,405),(1438,350)],'HTTP poll',1450,382)
text(42,1043,'D  OFFLINE TRAINING & RELEASE LIFECYCLE / 30% EFFORT', 'tag')
box(42,1075,296,165,'Collect & curate',['HCRL / ROAD / own lab captures','Normalize timestamp + CAN fields','Split by capture/session first','Real datasets: not evaluated'],tag='REAL DATA · PENDING',planned=True)
box(374,1075,296,165,'Build normal feature sets',['Same C++ extractor as runtime','Train normal sessions only','Validation normal: pick threshold','Hold out entire test sessions'],tag='DEMO ONLY · PARTIAL')
box(706,1075,296,165,'Train → export → verify',['Python / scikit-learn on PC','Export tree nodes, not pickle','Compare Python vs C++ scores','Payload shift: 1/40 above threshold'],tag='LOCAL MODEL · QUALITY GAP')
box(1038,1075,296,165,'Versioned artifact',['Model + feature schema + profile','Threshold + fingerprint + report','Candidate version for review','No automatic promotion'],tag='BUNDLE · PARTIAL')
box(1370,1075,266,165,'Review → Pi → release',['Local review approval','Linux vcan + testbench','Pi performance validation','Separate production approval'],tag='FUTURE GATES',planned=True)
arrow([(338,1148),(374,1148)])
arrow([(670,1148),(706,1148)])
arrow([(1002,1148),(1038,1148)])
arrow([(1334,1148),(1370,1148)],dashed=True)
arrow([(1186,1075),(1186,647),(622,647),(622,665)],'load exported forest',983,640,green=True)
parts.append('<rect x="42" y="1265" width="1594" height="136" rx="12" fill="#251f1b" stroke="#665032"/>')
text(62,1295,'BOUNDARIES THAT MATTER', 'tag')
text(62,1324,'An anomaly score does not identify an attacker or prove spoofing/replay. Signal-level checks require DBC and context.')
text(62,1351,'Local prototype is synchronous. Bounded capture/logging queues, storage retention and automated rollback are future work.')
text(62,1378,'100 ms aggregation + processing + debounce determines detection delay. Model P95 alone is not end-to-end latency.')
text(42,1454,'Teal boxes: implemented local path     Muted boxes / dashed links: target architecture or unvalidated hardware path','label')
text(42,1478,'Percentages = estimated effort allocation across the review plan, NOT completion, accuracy or measured timing.','label')
parts.append('</svg>')
(ROOT/'docs').mkdir(exist_ok=True)
(ROOT/'docs'/'architecture.svg').write_text('\n'.join(parts), encoding='utf-8')
print('docs/architecture.svg')
