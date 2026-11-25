// 本機用的藍新金流 mock：驗簽、付款頁、簽 notify、交易時限。
// 只用 Node 內建模組（http、crypto、querystring），不得引入 npm 套件。
//
// X-Mock-Now：mock 專用的測試標頭（秒級 epoch），只影響本服務在 /MPG/pay 的逾時判斷，
// 讓測試不用真的等到 TradeLimit。backend 不得有任何對應邏輯。
const http = require('http');
const crypto = require('crypto');
const querystring = require('querystring');

const { MerchantID, HASHKEY, HASHIV } = process.env;
const PORT = 8080;
const sessions = new Map();

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function encrypt(plain) {
  const cipher = crypto.createCipheriv('aes-256-cbc', HASHKEY, HASHIV);
  return cipher.update(plain, 'utf8', 'hex') + cipher.final('hex');
}

function decrypt(hex) {
  const decipher = crypto.createDecipheriv('aes-256-cbc', HASHKEY, HASHIV);
  return decipher.update(hex, 'hex', 'utf8') + decipher.final('utf8');
}

function tradeSha(tradeInfoHex) {
  return crypto
    .createHash('sha256')
    .update(`HashKey=${HASHKEY}&${tradeInfoHex}&HashIV=${HASHIV}`)
    .digest('hex')
    .toUpperCase();
}

function safeEqual(a, b) {
  const x = Buffer.from(String(a));
  const y = Buffer.from(String(b));
  return x.length === y.length && crypto.timingSafeEqual(x, y);
}

function nowSeconds(req) {
  const header = req.headers['x-mock-now'];
  if (header !== undefined) {
    const n = Number(header);
    if (Number.isFinite(n)) return n;
  }
  return Date.now() / 1000;
}

function pad(n) {
  return String(n).padStart(2, '0');
}

function formatPayTime(d) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function page(body) {
  return `<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><title>藍新金流（mock）</title></head><body>${body}</body></html>`;
}

function send(res, status, body, type = 'text/html; charset=utf-8') {
  res.writeHead(status, { 'Content-Type': type });
  res.end(body);
}

function readForm(req) {
  return new Promise((resolve, reject) => {
    let raw = '';
    req.on('data', (chunk) => {
      raw += chunk;
      if (raw.length > 1e6) {
        reject(new Error('body too large'));
        req.destroy();
      }
    });
    req.on('end', () => resolve(querystring.parse(raw)));
    req.on('error', reject);
  });
}

function first(v) {
  return Array.isArray(v) ? v[0] : v;
}

async function handleGateway(req, res) {
  const form = await readForm(req);
  const tradeInfo = String(first(form.TradeInfo) || '');
  if (
    first(form.MerchantID) !== MerchantID ||
    !safeEqual(first(form.TradeSha) || '', tradeSha(tradeInfo))
  ) {
    return send(res, 400, page('<h1>簽章驗證失敗</h1>'));
  }
  let trade;
  try {
    const parsed = querystring.parse(decrypt(tradeInfo));
    trade = {};
    for (const k of Object.keys(parsed)) trade[k] = first(parsed[k]);
  } catch (e) {
    return send(res, 400, page('<h1>簽章驗證失敗</h1>'));
  }
  const limit = parseInt(trade.TradeLimit, 10);
  const id = crypto.randomBytes(16).toString('hex');
  sessions.set(id, {
    id,
    trade,
    version: first(form.Version) || trade.Version || '2.0',
    deadline: limit > 0 ? Date.now() / 1000 + limit : null,
    paid: false,
  });
  const body = `<h1>藍新金流（mock）付款頁</h1>
<p>訂單編號：${escapeHtml(trade.MerchantOrderNo)}</p>
<p>金額：${escapeHtml(trade.Amt)}</p>
<p>商品：${escapeHtml(trade.ItemDesc)}</p>
<form method="post" action="/MPG/pay"><input type="hidden" name="session" value="${escapeHtml(id)}"><input type="hidden" name="result" value="success"><button type="submit">付款成功</button></form>
<form method="post" action="/MPG/pay"><input type="hidden" name="session" value="${escapeHtml(id)}"><input type="hidden" name="result" value="fail"><button type="submit">付款失敗</button></form>`;
  return send(res, 200, page(body));
}

async function postNotify(url, fields) {
  try {
    const resp = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams(fields).toString(),
      signal: AbortSignal.timeout(10000),
    });
    console.log(`notify ${url} -> ${resp.status}`);
  } catch (e) {
    console.error(`notify ${url} failed: ${e.message}`);
  }
}

async function handlePay(req, res) {
  const form = await readForm(req);
  const session = sessions.get(String(first(form.session) || ''));
  if (!session) return send(res, 404, page('<h1>找不到交易</h1>'));
  if (session.deadline !== null && nowSeconds(req) > session.deadline) {
    return send(res, 200, page('<h1>交易逾時</h1>'));
  }
  if (session.paid) return send(res, 409, page('<h1>此交易已完成</h1>'));
  session.paid = true;

  const ok = first(form.result) === 'success';
  const status = ok ? 'SUCCESS' : 'MPG03009';
  const { trade } = session;
  const body = {
    Status: status,
    Message: ok ? '授權成功' : '交易失敗',
    Result: {
      MerchantID,
      Amt: Number(trade.Amt),
      TradeNo: `MOCK${crypto.randomBytes(6).toString('hex').toUpperCase()}`,
      MerchantOrderNo: trade.MerchantOrderNo,
      PaymentType: 'CREDIT',
      PayTime: formatPayTime(new Date()),
    },
  };
  const tradeInfo = encrypt(JSON.stringify(body));
  const fields = {
    Status: status,
    MerchantID,
    Version: session.version,
    TradeInfo: tradeInfo,
    TradeSha: tradeSha(tradeInfo),
  };
  if (trade.NotifyURL) await postNotify(trade.NotifyURL, fields);

  const inputs = Object.entries(fields)
    .map(([k, v]) => `<input type="hidden" name="${escapeHtml(k)}" value="${escapeHtml(v)}">`)
    .join('');
  return send(
    res,
    200,
    page(
      `<form id="return" method="post" action="${escapeHtml(trade.ReturnURL || '')}">${inputs}<noscript><button type="submit">返回商店</button></noscript></form><script>document.getElementById('return').submit();</script>`,
    ),
  );
}

const server = http.createServer(async (req, res) => {
  try {
    const path = (req.url || '').split('?')[0];
    if (req.method === 'GET' && path === '/health') return send(res, 200, 'ok', 'text/plain');
    if (req.method === 'POST' && path === '/MPG/mpg_gateway') return await handleGateway(req, res);
    if (req.method === 'POST' && path === '/MPG/pay') return await handlePay(req, res);
    return send(res, 404, 'not found', 'text/plain');
  } catch (e) {
    console.error(e);
    return send(res, 500, 'error', 'text/plain');
  }
});

server.listen(PORT, '0.0.0.0', () => console.log(`mock-newebpay listening on ${PORT}`));
