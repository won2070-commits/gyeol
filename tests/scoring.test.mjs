import test from 'node:test';
import assert from 'node:assert/strict';
import {questions,extraQuestions,score,followups,quality,validDraft,VERSION,typeNames,typeProfiles} from '../docs/data.js';
const answer=(fn)=>Object.fromEntries(questions.map(q=>[q.id,fn(q)]));
test('32 unique questions, balanced directions for each dimension',()=>{assert.equal(questions.length,32);assert.equal(new Set(questions.map(q=>q.id)).size,32);for(let a=0;a<4;a++){assert.equal(questions.filter(q=>q.axis===a&&q.direction===1).length,4);assert.equal(questions.filter(q=>q.axis===a&&q.direction===-1).length,4);}});
test('strong left preference including reverse scoring gives ESTJ',()=>{const r=score(answer(q=>q.direction===1?5:1));assert.equal(r.type,'ESTJ');assert.deepEqual(r.axes.map(a=>a.position),[0,0,0,0]);});
test('strong right preference gives INFP',()=>{const r=score(answer(q=>q.direction===1?1:5));assert.equal(r.type,'INFP');assert.deepEqual(r.axes.map(a=>a.position),[100,100,100,100]);});
test('all neutral does not fabricate a type',()=>{const a=answer(()=>3);assert.equal(score(a).type,'XXXX');assert.equal(followups(a).length,8);assert.equal(quality(a).neutral,32);});
test('same option everywhere produces balanced scores and quality flag',()=>{const a=answer(()=>5);assert.equal(score(a).type,'XXXX');assert.equal(quality(a).inconsistent,16);});
test('coherent reverse answers do not trigger consistency flag',()=>assert.equal(quality(answer(q=>q.direction===1?5:1)).inconsistent,0));
test('only ambiguous axis receives additional questions',()=>{const a=answer(q=>q.axis===2?3:q.direction===1?5:1);assert.deepEqual(followups(a).map(q=>q.axis),[2,2]);});
test('additional answers contribute to correct dimension',()=>{const a=answer(()=>3);extraQuestions.filter(q=>q.axis===0).forEach(q=>a[q.id]=q.direction===1?5:1);const r=score(a);assert.equal(r.axes[0].count,10);assert.equal(r.axes[0].position,40);assert.equal(r.type,'EXXX');assert.equal(r.axes[1].position,50);});
test('all sixteen clear types can be produced',()=>{const seen=new Set;for(let mask=0;mask<16;mask++){const r=score(answer(q=>((mask>>q.axis)&1)?q.direction===1?1:5:q.direction===1?5:1));seen.add(r.type);}assert.equal(seen.size,16);});
test('invalid values excluded from scoring',()=>{const r=score({'q0-0':99,'q0-1':'5','q0-2':NaN});assert.equal(r.axes[0].count,0);assert.equal(r.type,'XXXX');});
test('restored draft validates schema and questionnaire version',()=>{assert.ok(validDraft({version:VERSION,answers:answer(()=>3)}));assert.ok(!validDraft({version:'old',answers:{}}));assert.ok(!validDraft({version:VERSION,answers:{fake:3}}));assert.ok(!validDraft({version:VERSION,answers:{'q0-0':0}}));assert.ok(!validDraft({version:VERSION,answers:[]}));});
test('scores remain bounded for deterministic generated responses',()=>{for(let k=0;k<100;k++){const a=Object.fromEntries(questions.map((q,i)=>[q.id,1+((k*7+i*3)%5)]));score(a).axes.forEach(s=>assert.ok(s.position>=0&&s.position<=100));}});

test('every producible type has a written profile', () => {
  const keys = Object.keys(typeNames);
  assert.equal(keys.length, 16);
  for (const key of keys) {
    const profile = typeProfiles[key];
    assert.ok(profile, `${key} 해설 없음`);
    assert.ok(profile.summary.length > 30);
    assert.equal(profile.strengths.length, 3);
    assert.equal(profile.growth.length, 2);
    assert.ok(profile.fit.length > 5);
  }
});
