"""Check that each published example clearly separates source and detector results."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess

from PIL import Image
from example_labels import SOURCES, OLD, NEW, MODES

ROOT=Path(__file__).resolve().parents[1]

class Node:
    def __init__(self,tag,attrs=()):self.tag=tag;self.attrs=dict(attrs);self.content=[]
    def text(self):return ' '.join(' '.join(c.text() if isinstance(c,Node) else c for c in self.content).split())
    def walk(self):
        yield self
        for child in self.content:
            if isinstance(child,Node):yield from child.walk()
    def has(self,cls):return cls in self.attrs.get('class','').split()

class Document(HTMLParser):
    def __init__(self):super().__init__();self.root=Node('root');self.stack=[self.root]
    def handle_starttag(self,tag,attrs):
        node=Node(tag,attrs);self.stack[-1].content.append(node)
        if tag not in {'img','br','hr','input','meta','link','source','wbr'}:self.stack.append(node)
    def handle_endtag(self,tag):
        if any(n.tag==tag for n in self.stack):
            while self.stack[-1].tag!=tag:self.stack.pop()
            self.stack.pop()
    def handle_data(self,data):self.stack[-1].content.append(data)

def main():
    data=json.loads((ROOT/'web/results.json').read_text());games={g['id']:g for g in data['games']}
    doc=Document();doc.feed((ROOT/'web/article-body.html').read_text());nodes=list(doc.root.walk())
    ids=[n.attrs['id'] for n in nodes if 'id' in n.attrs];assert len(ids)==len(set(ids))
    cases=[n for n in nodes if n.tag=='article' and n.has('brilly-static-case')]
    assert len(cases)==14
    for article in cases:
        gid=article.attrs['data-example-game'];ply=int(article.attrs['data-example-ply'])
        game=games[gid];case=next(c for c in game['cases'] if c['ply']==ply);assert case['landmark']
        content=list(article.walk());source=next(n for n in content if n.has('brilly-reference'))
        assert source.text().startswith('Published annotation Brilliant !!')
        for key in ('byline','publication','location'):assert SOURCES[gid][key] in source.text()
        assert any(n.tag=='a' and n.attrs.get('href')==game['source']['url'] for n in source.walk())
        table=next(n for n in content if n.tag=='table')
        rows=[[n.text() for n in row.content if isinstance(n,Node) and n.tag in ('th','td')] for row in table.walk() if row.tag=='tr']
        expected=[['Analysis mode',OLD,NEW]]+[[q.title(),data['grades'][case['modes'][q]['old'] or 'null'],data['grades'][case['modes'][q]['new'] or 'null']] for q in MODES]
        assert rows==expected,(gid,ply,rows)
        caption=next(n for n in content if n.tag=='figcaption').text()
        assert caption==f"Left: before {case['move']}. Right: after the same move."
        path=ROOT/f'figures/{gid}-{ply:03d}.png'
        with Image.open(path) as image:
            positions=json.loads(image.info['Position'])
            assert positions=={'before':case['before'],'after':case['after'],'uci':case['uci']}
            assert 'Source !! landmark' not in image.info['Caption']
    kasparov=next(c for c in games['kasparov-topalov-1999']['cases'] if c['ply']==47)
    assert kasparov['modes']['thorough']['new']=='brilliant'
    assert all(kasparov['modes'][q]['new']!='brilliant' for q in ('fast','balanced'))
    manifest=json.loads((ROOT/'figures/manifest.json').read_text())
    assert len(manifest['onlineIllustrations'])==2
    for row in manifest['landmarks']+manifest['onlineIllustrations']:
        assert hashlib.sha256((ROOT/'figures'/row['file']).read_bytes()).hexdigest()==row['sha256']
    for name in ['data/engine-runs.json','web/results.json','web/online-results.json','online/engine-runs.json.gz','ginger/engine-runs.json.gz']:
        path=ROOT/name
        original=subprocess.check_output(['git','-C',str(ROOT),'show',f'HEAD:{path.relative_to(ROOT.parents[1])}'])
        assert original==path.read_bytes(),('Measured data changed',name)
    print('PASS: all 14 examples name the source and both detectors, show the exact three-mode results and label the same move before/after; image positions/hashes and all recorded measurements preserved.')

if __name__=='__main__':main()
