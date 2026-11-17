import test from 'node:test';
import assert from 'node:assert/strict';
import { sendChat, checkMessage, checkSessionToken, ChatError } from './client.mjs';

const TOKEN = 'ab.cd.ef';
const ok = (reply = 'Xin chào!') => ({
  ok: true, status: 200, headers: { get: () => null },
  text: async () => JSON.stringify({reply}),
});

test('sends only message to same-origin /chat, not the API key', async () => {
  let captured;
  const result = await sendChat({message: 'Hello', token: TOKEN, fetchImpl: async (...args) => {
    captured = args;
    return ok();
  }});
  assert.equal(result, 'Xin chào!');
  assert.equal(captured[0], '/chat');
  const opts = captured[1];
  assert.equal(opts.method, 'POST');
  assert.equal(opts.credentials, 'omit');
  assert.equal(opts.mode, 'same-origin');
  assert.equal(opts.redirect, 'error');
  assert.equal(opts.headers.Authorization, 'Bearer ' + TOKEN);
  assert.deepEqual(JSON.parse(opts.body), {message: 'Hello'});
});

test('rejects invalid messages and tokens without a network request', async () => {
  let calls = 0;
  const never = async () => { calls++; return ok(); };
  for (const message of ['', '  ', 'x'.repeat(2001), '\u0000'.repeat(1800)]) {
    await assert.rejects(sendChat({message, token: TOKEN, fetchImpl: never}), ChatError);
  }
  for (const token of ['', 'gog-id-token', 'not-a-session', 'a.b.c'.repeat(1000)]) {
    await assert.rejects(sendChat({message: 'hi', token, fetchImpl: never}), ChatError);
  }
  assert.equal(calls, 0);
});

test('HTTP authentication, HOLD and quota failures never reveal server body', async () => {
  for (const status of [401, 429, 503, 502]) {
    await assert.rejects(
      sendChat({message:'Hi', token:TOKEN, fetchImpl:async()=>({ok:false,status, headers:{get:()=>null}, text:async()=> 'sensitive details'})}),
      err => err instanceof ChatError && err.code === 'http_' + status && !err.message.includes('sensitive')
    );
  }
});

test('network failures do not echo secrets', async () => {
  await assert.rejects(sendChat({message:'hi', token:TOKEN, fetchImpl: async()=>{throw Error('private token ' + TOKEN);}}),
    err => err instanceof ChatError && !err.message.includes(TOKEN));
});

test('rejects invalid and overlarge provider responses', async () => {
  for (const response of [
    {ok:true,headers:{get:()=>null},text:async()=>'{not json'},
    {ok:true,headers:{get:()=>null},text:async()=>JSON.stringify({reply:'',other:1})},
    {ok:true,headers:{get:()=>null},text:async()=>JSON.stringify({reply:'y'.repeat(4001)})},
    {ok:true,headers:{get:()=>String(9000)},text:async()=>JSON.stringify({reply:'ok'})},
    {ok:true,headers:{get:()=>null},text:async()=> 'x'.repeat(9000)},
  ]) {
    await assert.rejects(sendChat({message:'Hi',token:TOKEN,fetchImpl:async()=>response}), ChatError);
  }
});

test('multilingual messages preserve content, and whitespace is trimmed', async () => {
  let captured;
  const reply = await sendChat({message:'  Cảm ơn bạn 🙏  ',token:TOKEN,fetchImpl:async(_url,options)=>{
    captured=options.body;
    return ok('Không có gì!');
  }});
  assert.deepEqual(JSON.parse(captured),{message:'Cảm ơn bạn 🙏'});
  assert.equal(reply,'Không có gì!');
});

test('pure validators preserve fail-closed behavior', () => {
  assert.equal(checkMessage('  hi  ').clean, 'hi');
  assert.equal(checkSessionToken(TOKEN), TOKEN);
  assert.throws(()=>checkSessionToken('bad'), ChatError);
});
