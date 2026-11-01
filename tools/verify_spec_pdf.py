"""Validate the actual PDF and rasterize pages for visual review."""
import json
from pathlib import Path
import re
import unicodedata
from pypdf import PdfReader
import pypdfium2 as pdfium
from PIL import Image, ImageOps, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'docs'/'spec'
STEM='AI-VIDS_Spec_VMware_Ubuntu_RaspberryPi_Production_v1.0'


def norm(s):
    return re.sub(r'\s+','',unicodedata.normalize('NFC',s))


def main():
    path=FOLDER/(STEM+'.pdf');reader=PdfReader(path)
    plan=json.loads((FOLDER/'spec-pages.json').read_text(encoding='utf-8'))
    assert len(reader.pages)==len(plan)==26
    texts=[p.extract_text() for p in reader.pages]
    all_text='\n'.join(texts)
    for word in ['Raspberry','Ubuntu','cảnh báo','cửa sổ','đầu ra','PI-BOOT-03','T38']:
        assert word in all_text,repr(word)
    for i,(text,meta) in enumerate(zip(texts,plan)):
        assert norm(meta['title']) in norm(text),f'Heading mismatch on page {i+1}'
        assert norm(f'{i+1:02} / 26') in norm(text),f'Footer mismatch on page {i+1}'
        box=reader.pages[i].mediabox
        assert abs(float(box.width)-595.276)<1 and abs(float(box.height)-841.89)<1
    for i in range(1,39):assert f'T{i:02}' in all_text
    assert len(reader.outline)==26
    layout=json.loads((FOLDER/'layout-validation.json').read_text())
    assert not layout['overflow']
    preview=FOLDER/'preview';preview.mkdir(exist_ok=True)
    doc=pdfium.PdfDocument(str(path));selected=[0,1,6,7,12,14,18,21,25];thumbs=[]
    for i in range(len(doc)):
        page=doc[i];bitmap=page.render(scale=1.4);image=bitmap.to_pil().convert('RGB')
        image.save(preview/f'page-{i+1:02}.png')
        if i in selected:
            thumb=ImageOps.contain(image,(440,625))
            tile=Image.new('RGB',(460,665),'#e2e9ee')
            tile.paste(thumb,((460-thumb.width)//2,25))
            ImageDraw.Draw(tile).text((12,5),f'Page {i+1:02}',fill='#142f46');thumbs.append(tile)
        bitmap.close();page.close()
    contact=Image.new('RGB',(1380,1995),'#d7e2e9')
    for n,tile in enumerate(thumbs):contact.paste(tile,((n%3)*460,(n//3)*665))
    contact.save(preview/'contact-sheet.png');doc.close()
    report={'status':'PASS','pages':len(reader.pages),'bookmarks':len(reader.outline),
            'toc_links':len(reader.pages[1].get('/Annots',[])),
            'text_characters':len(all_text),'unicode_checks':'PASS',
            'a4_size':'PASS','headings_and_footers':'PASS','html_layout_overflow':False,
            'rasterized_pages':26,'preview_contact_pages':[i+1 for i in selected],
            'pdf_bytes':path.stat().st_size}
    (FOLDER/'pdf-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
