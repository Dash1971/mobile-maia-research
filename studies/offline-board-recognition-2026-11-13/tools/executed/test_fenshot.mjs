import {spawn} from 'node:child_process';
import {createInterface} from 'node:readline';
import {readFileSync,writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {recognizeGray} from './fenshot-node/recognize.ts';
import {rgbaToGray,extractTiles} from './fenshot-node/tiles.ts';
import {probsToPlacement,resolveOrientation} from './fenshot-node/fen.ts';
const dir=path.dirname(fileURLToPath(import.meta.url));
const worker=spawn(path.join(dir,'runtime/bin/python'),['-u',path.join(dir,'worker.py'),path.join(dir,'fenshot/chess-tiles-v2.onnx')]);
const pending=[];const rl=createInterface({input:worker.stdout});let readyResolve;const ready=new Promise(r=>readyResolve=r);
rl.on('line',line=>{const data=JSON.parse(line);if(data.ready){console.log('WORKER',JSON.stringify(data));readyResolve();}else{const resolve=pending.shift();if(data.error)throw Error(data.error);resolve(data.probs);}});
worker.stderr.on('data',b=>process.stderr.write(b));await ready;
let seq=0;
async function infer(tiles){const id=seq++;const file=path.join(dir,'tiles.f32');writeFileSync(file,Buffer.from(tiles.buffer,tiles.byteOffset,tiles.byteLength));const result=new Promise(r=>pending.push(r));worker.stdin.write(JSON.stringify({id,file})+'\n');return probsToPlacement(Float32Array.from(await result));}
function expand(fen){return [...fen].flatMap(c=>c==='/'?[]:/[1-8]/.test(c)?Array(Number(c)).fill('.'):c);}
const rows=[];
for(const c of JSON.parse(readFileSync(path.join(dir,process.argv.includes('--frames')?'frames.json':'cases.json')))){
 const buf=readFileSync(c.rgba);const gray=rgbaToGray(new Uint8ClampedArray(buf),c.width,c.height);let calls=0;
 const t=Date.now();const scan=process.argv.includes('--frames') ? {...await infer(extractTiles(gray,{x0:0,y0:0,x1:c.width,y1:c.height})),corners:{x0:0,y0:0,x1:c.width,y1:c.height}} : await recognizeGray(gray,async corners=>{calls++;return infer(extractTiles(gray,corners));});
 let row={id:c.id,scan,modelCalls:calls,elapsedMs:Date.now()-t};
 if(scan){const truth=expand(c.expected),got=expand(scan.placement);row.correct=got.filter((x,i)=>x===truth[i]).length;row.errors=got.flatMap((x,i)=>x===truth[i]?[]:[{square:'abcdefgh'[i%8]+(8-Math.floor(i/8)),actual:x,expected:truth[i]}]);row.resolvedOrientation=resolveOrientation(scan.placement);}
 rows.push(row);console.log(c.id,scan?.placement, row.correct,scan?.reliable, 'calls',calls);
}
writeFileSync(path.join(dir,process.argv.includes('--frames')?'../evidence/fenshot-framed.json':'../evidence/fenshot-end-to-end.json'),JSON.stringify(rows,null,2)+'\n');worker.stdin.end();await new Promise(r=>worker.on('exit',r));
