(() => {
  const $ = (s) => document.querySelector(s);
  const state = { apiKey: localStorage.getItem('apiKey') || 'changeme' };

  $('#apiKey').value = state.apiKey;
  $('#saveKey').onclick = () => {
    state.apiKey = $('#apiKey').value.trim();
    localStorage.setItem('apiKey', state.apiKey);
    $('#keyStatus').textContent = 'gespeichert';
    setTimeout(() => $('#keyStatus').textContent = '', 1500);
  };

  function out(el, label, data) {
    const ts = new Date().toISOString();
    el.textContent += `\n[${ts}] ${label}:\n` + (typeof data === 'string' ? data : JSON.stringify(data, null, 2)) + "\n";
    el.scrollTop = el.scrollHeight;
  }

  async function get(url, headers = {}) {
    const r = await fetch(url, { headers });
    const t = await r.text();
    try { return { ok: r.ok, data: JSON.parse(t) }; } catch { return { ok: r.ok, data: t }; }
  }

  async function post(url, body, headers = {}) {
    const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', ...headers }, body: JSON.stringify(body) });
    const t = await r.text();
    try { return { ok: r.ok, data: JSON.parse(t) }; } catch { return { ok: r.ok, data: t }; }
  }

  $('#checkWaf').onclick = async () => {
    const res = await get('/healthz');
    out($('#healthOut'), 'WAF /healthz', res.data);
  };
  $('#checkOrders').onclick = async () => {
    const res = await get('/api/orders/healthz', { 'X-API-Key': state.apiKey });
    out($('#healthOut'), 'Orders /healthz', res.data);
  };
  $('#checkRestaurants').onclick = async () => {
    const res = await get('/api/restaurants/healthz', { 'X-API-Key': state.apiKey });
    out($('#healthOut'), 'Restaurants /healthz', res.data);
  };
  $('#checkPayments').onclick = async () => {
    const res = await get('/api/payments/healthz', { 'X-API-Key': state.apiKey });
    out($('#healthOut'), 'Payments /healthz', res.data);
  };

  $('#checkMenus').onclick = async () => {
    const res = await get('/api/restaurants/menus', { 'X-API-Key': state.apiKey });
    out($('#apiOut'), 'GET /menus', res.data);
  };

  $('#testOrder').onclick = async () => {
    const payload = {
      customer_id: 'c-checks',
      items: [ { name: 'Pizza Margherita', price: 10.5, quantity: 1 } ]
    };
    const res = await post('/api/orders/orders', payload, { 'X-API-Key': state.apiKey });
    out($('#apiOut'), 'POST /orders', res.data);
  };
})();

