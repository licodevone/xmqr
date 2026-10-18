#!/usr/bin/env node
// P220: real Chromium WebSocket MQTT/mTLS/Origin exercise; invoked by Python fixture.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require(path.join(__dirname, '..', 'dist', 'browser-playwright',
  'node_modules', 'playwright'));

const config = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const encoder = new TextEncoder();

async function main() {
  const browser = await chromium.launch({ headless: true });
  const certificate = [{ origin: config.wssOrigin, certPath: config.clientCert,
    keyPath: config.clientKey }];
  const context = await browser.newContext({ ignoreHTTPSErrors: true,
    clientCertificates: certificate });
  try {
    const page = await context.newPage();
    await page.goto(config.pageOrigin);
    for (const version of [4, 5]) {
      const result = await page.evaluate(async ({ url, version, password }) => {
        const enc = new TextEncoder();
        const field = bytes => new Uint8Array([bytes.length >> 8, bytes.length & 255, ...bytes]);
        const str = value => field(enc.encode(value));
        const packet = (header, body) => new Uint8Array([header, body.length, ...body]);
        const open = () => new Promise((resolve, reject) => {
          const ws = new WebSocket(url, 'mqtt');
          ws.binaryType = 'arraybuffer';
          const timer = setTimeout(() => reject(new Error('WSS open timeout')), 6000);
          ws.onopen = () => { clearTimeout(timer); resolve(ws); };
          ws.onerror = () => { clearTimeout(timer); reject(new Error('WSS open failed')); };
        });
        const message = ws => new Promise((resolve, reject) => {
          const timer = setTimeout(() => reject(new Error('MQTT reply timeout')), 6000);
          ws.addEventListener('message', event => {
            clearTimeout(timer);
            resolve(new Uint8Array(event.data));
          }, { once: true });
        });
        const connect = async (ws, id, secret) => {
          const body = new Uint8Array([0, 4, 77, 81, 84, 84, version, 0xc2, 0, 30,
            ...(version === 5 ? [0] : []), ...str(id), ...str('device'), ...str(secret)]);
          const reply = message(ws);
          ws.send(packet(0x10, body));
          return await reply;
        };
        const sub = await open();
        try {
          if (sub.protocol !== 'mqtt') throw new Error('missing mqtt subprotocol');
          const connack = await connect(sub, `p220-sub-${version}`, password);
          if (connack[0] !== 0x20 || connack[2] !== 0 || connack[3] !== 0)
            throw new Error(`subscriber CONNACK ${Array.from(connack)}`);
          const subscribe = message(sub);
          sub.send(packet(0x82, new Uint8Array([0, 1, ...(version === 5 ? [0] : []),
            ...str('p212/allowed'), 0])));
          const suback = await subscribe;
          if (suback[0] !== 0x90 || suback[suback.length - 1] !== 0)
            throw new Error(`SUBACK ${Array.from(suback)}`);
          const pub = await open();
          try {
            const publisher = await connect(pub, `p220-pub-${version}`, password);
            if (publisher[0] !== 0x20 || publisher[3] !== 0)
              throw new Error(`publisher CONNACK ${Array.from(publisher)}`);
            const payload = `browser-${version}`;
            const delivery = message(sub);
            pub.send(packet(0x30, new Uint8Array([...str('p212/allowed'),
              ...(version === 5 ? [0] : []), ...enc.encode(payload)])));
            const received = await delivery;
            if (received[0] !== 0x30 || !new TextDecoder().decode(received).endsWith(payload))
              throw new Error(`wrong delivery ${Array.from(received)}`);
            return { version, protocol: sub.protocol, payload };
          } finally { pub.close(); }
        } finally { sub.close(); }
      }, { url: config.wssUrl, version, password: config.password });
      assert.equal(result.protocol, 'mqtt');
      console.log(`BROWSER_MQTT_${version}_PASS`);
    }
    const badPassword = await page.evaluate(async ({ url }) => {
      const ws = new WebSocket(url, 'mqtt');
      ws.binaryType = 'arraybuffer';
      await new Promise((resolve, reject) => {
        ws.onopen = resolve; ws.onerror = () => reject(new Error('WSS did not open'));
      });
      const e = new TextEncoder();
      const field = s => [0, e.encode(s).length, ...e.encode(s)];
      const reply = new Promise(resolve => {
        ws.onmessage = event => resolve([...new Uint8Array(event.data)]);
        ws.onclose = () => resolve([]);
        setTimeout(() => resolve([]), 5000);
      });
      const body = [0, 4, 77, 81, 84, 84, 5, 0xc2, 0, 30, 0,
        ...field('p220-wrong-password'), ...field('device'), ...field('wrong-password')];
      ws.send(new Uint8Array([0x10, body.length, ...body]));
      const packet = await reply;
      ws.close();
      return packet.length >= 4 && packet[0] === 0x20 && packet[3] === 0;
    }, { url: config.wssUrl });
    assert.equal(badPassword, false, 'wrong MQTT password was accepted');

    const forbidden = await page.evaluate(async ({ url, password }) => {
      const e = new TextEncoder();
      const field = s => [0, e.encode(s).length, ...e.encode(s)];
      const ws = new WebSocket(url, 'mqtt');
      ws.binaryType = 'arraybuffer';
      await new Promise((resolve, reject) => {
        ws.onopen = resolve; ws.onerror = () => reject(new Error('WSS did not open'));
      });
      const reply = () => new Promise(resolve => {
        ws.addEventListener('message', event => resolve([...new Uint8Array(event.data)]),
          { once: true });
      });
      const body = [0, 4, 77, 81, 84, 84, 5, 0xc2, 0, 30, 0,
        ...field('p220-acl'), ...field('device'), ...field(password)];
      const connack = reply();
      ws.send(new Uint8Array([0x10, body.length, ...body]));
      const connected = await connack;
      if (connected[0] !== 0x20 || connected[3] !== 0) throw new Error('ACL connection failed');
      const suback = reply();
      const sub = [0, 2, 0, ...field('p212/denied'), 0];
      ws.send(new Uint8Array([0x82, sub.length, ...sub]));
      const denied = await suback;
      ws.close();
      return denied[0] === 0x90 && denied[denied.length - 1] === 0x87;
    }, { url: config.wssUrl, password: config.password });
    assert.equal(forbidden, true, 'forbidden MQTT topic was accepted');

    async function expectBlocked(testContext, pageOrigin, label) {
      const testPage = await testContext.newPage();
      try {
        await testPage.goto(pageOrigin);
        const opened = await testPage.evaluate(url => new Promise(resolve => {
          const ws = new WebSocket(url, 'mqtt');
          const timer = setTimeout(() => resolve(false), 5000);
          ws.onopen = () => { clearTimeout(timer); ws.close(); resolve(true); };
          ws.onerror = () => { clearTimeout(timer); resolve(false); };
        }), config.wssUrl);
        assert.equal(opened, false, `${label} bypassed WSS policy`);
      } finally { await testPage.close(); }
    }
    await expectBlocked(context, config.wrongPageOrigin, 'unlisted Origin');
    const noCert = await browser.newContext({ ignoreHTTPSErrors: true });
    try { await expectBlocked(noCert, config.pageOrigin, 'missing client certificate'); }
    finally { await noCert.close(); }
    console.log('P220_REAL_BROWSER_WSS_PASS');
  } finally { await context.close(); await browser.close(); }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
