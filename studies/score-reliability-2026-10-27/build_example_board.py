"""Render the recorded example before and after 26.Rd1 (chess 1.11.2)."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET
import chess
import chess.svg
ROOT=Path(__file__).resolve().parent
case=json.loads((ROOT/'data/known-case-consistency.json').read_text())
board=chess.Board(case['fen']);move=chess.Move.from_uci('d7d1')
assert board.fullmove_number==26 and board.turn==chess.WHITE
assert board.legal_moves.count()==26 and move in board.legal_moves
child=board.copy();child.push(move)
record=next(r for r in case['moves'] if r['elo']==1600 and r['uci']=='d7d1')
assert child.fen()==record['childFen']
s=next(r for r in case['summary'] if r['elo']==1600)
ns='http://www.w3.org/2000/svg';ET.register_namespace('',ns)
root=ET.Element('{'+ns+'}svg',{'viewBox':'0 0 1100 740','width':'1100','height':'740'})
def elem(tag,attrs,text=None):
 e=ET.SubElement(root,'{'+ns+'}'+tag,attrs);e.text=text;return e
elem('rect',{'width':'1100','height':'740','fill':'#f6f4ee'})
def label(x,y,text,size=24,color='#192f3e',bold=False):
 elem('text',{'x':str(x),'y':str(y),'font-family':'Arial, sans-serif','font-size':str(size),'fill':color,'font-weight':'bold' if bold else 'normal'},text)
label(40,46,'White to move: the rook can retreat from d7 to d1',30,bold=True)
label(40,80,'A position from a Mobile Maia game • Move 26 • Maia 1600, history on',20)
for x,b,title,score in [(40,board,'Before: White to move',s['parentWhiteScore']),(610,child,'After 26.Rd1: Black to move',s['rd1WhiteScore'])]:
 label(x,124,title,24,bold=True)
 svg=ET.fromstring(chess.svg.board(b,size=450,coordinates=True,arrows=[chess.svg.Arrow(chess.D7,chess.D1,color='#167dcccc')] if b is board else [],lastmove=move if b is child else None))
 svg.set('x',str(x));svg.set('y','144');root.append(svg)
 label(x,640,f"White’s forecast: {score*100:.1f}%",29,color='#4966aa',bold=True)
label(40,690,'The arrow marks Rd1: White moves the rook from d7 down to d1.',22)
label(40,721,'Both percentages describe White’s expected score, even after it becomes Black’s turn.',19)
(ROOT/'figures/example-board.svg').write_text(ET.tostring(root,encoding='unicode'))
