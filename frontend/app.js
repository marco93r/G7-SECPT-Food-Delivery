(() => {
  const $ = (sel) => document.querySelector(sel);
  const state = { apiKey: localStorage.getItem('apiKey') || 'changeme', menus: [], cart: {} };

  const fmt = (n) => (Math.round(n * 100) / 100).toFixed(2);

  function saveKey() {
    state.apiKey = $('#apiKey').value.trim();
    localStorage.setItem('apiKey', state.apiKey);
    $('#keyStatus').textContent = 'gespeichert';
    setTimeout(() => $('#keyStatus').textContent = '', 1500);
  }

  async function loadMenus() {
    $('#menusStatus').textContent = 'lädt…';
    try {
      const res = await fetch('/api/restaurants/menus', {
        headers: { 'X-API-Key': state.apiKey },
      });
      if (!res.ok) throw new Error(await res.text());
      state.menus = await res.json();
      renderMenus();
      $('#menusStatus').textContent = `geladen (${state.menus.length})`;
    } catch (e) {
      $('#menusStatus').textContent = 'Fehler beim Laden';
      console.error(e);
    }
  }

  function addToCart(item) {
    const key = item.id;
    if (!state.cart[key]) state.cart[key] = { ...item, quantity: 0 };
    state.cart[key].quantity += 1;
    renderCart();
  }

  function changeQty(id, delta) {
    if (!state.cart[id]) return;
    state.cart[id].quantity = Math.max(0, state.cart[id].quantity + delta);
    if (state.cart[id].quantity === 0) delete state.cart[id];
    renderCart();
  }

  function renderMenus() {
    const root = $('#menus');
    root.innerHTML = '';
    state.menus.forEach(m => {
      const card = document.createElement('div');
      card.className = 'card';
      card.innerHTML = `<h3>${m.name}</h3><div>${fmt(m.price)} €</div>`;
      const actions = document.createElement('div');
      actions.className = 'qty';
      const btn = document.createElement('button');
      btn.textContent = 'Hinzufügen';
      btn.onclick = () => addToCart(m);
      actions.appendChild(btn);
      card.appendChild(actions);
      root.appendChild(card);
    });
  }

  function renderCart() {
    const list = $('#cartList');
    list.innerHTML = '';
    let total = 0;
    Object.values(state.cart).forEach(ci => {
      total += ci.price * ci.quantity;
      const row = document.createElement('div');
      row.innerHTML = `<strong>${ci.name}</strong> – ${fmt(ci.price)} € × ${ci.quantity}`;
      const minus = document.createElement('button'); minus.textContent = '-'; minus.onclick = () => changeQty(ci.id, -1);
      const plus = document.createElement('button'); plus.textContent = '+'; plus.onclick = () => changeQty(ci.id, +1);
      row.appendChild(minus); row.appendChild(plus);
      list.appendChild(row);
    });
    $('#cartTotal').textContent = fmt(total);
  }

  async function placeOrder() {
    const items = Object.values(state.cart).map(ci => ({ name: ci.name, price: ci.price, quantity: ci.quantity }));
    if (items.length === 0) { $('#orderStatus').textContent = 'Warenkorb ist leer'; return; }
    $('#orderStatus').textContent = 'sende…';
    try {
      const res = await fetch('/api/orders/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': state.apiKey },
        body: JSON.stringify({ customer_id: $('#customerId').value || 'c-frontend', items }),
      });
      const txt = await res.text();
      let data;
      try { data = JSON.parse(txt); } catch { data = { raw: txt }; }
      if (!res.ok) throw new Error(typeof data === 'string' ? data : (data.detail || JSON.stringify(data)));
      $('#orderResult').classList.remove('hidden');
      $('#orderResult').textContent = JSON.stringify(data, null, 2);
      $('#orderId').value = data.id || '';
      $('#orderStatus').textContent = data.status || 'OK';
    } catch (e) {
      $('#orderStatus').textContent = `Fehler: ${e.message}`;
      console.error(e);
    }
  }

  async function checkStatus() {
    const id = ($('#orderId').value || '').trim();
    if (!id) return;
    try {
      const res = await fetch(`/api/orders/orders/${encodeURIComponent(id)}`, { headers: { 'X-API-Key': state.apiKey } });
      const txt = await res.text();
      let data; try { data = JSON.parse(txt); } catch { data = { raw: txt }; }
      if (!res.ok) throw new Error(typeof data === 'string' ? data : (data.detail || JSON.stringify(data)));
      $('#orderResult').classList.remove('hidden');
      $('#orderResult').textContent = JSON.stringify(data, null, 2);
      $('#orderStatus').textContent = data.status || '';
    } catch (e) {
      $('#orderStatus').textContent = `Fehler: ${e.message}`;
    }
  }

  // wire UI
  $('#apiKey').value = state.apiKey;
  $('#saveKey').onclick = saveKey;
  $('#loadMenus').onclick = loadMenus;
  $('#placeOrder').onclick = placeOrder;
  $('#checkStatus').onclick = checkStatus;

  // initial
  loadMenus();
})();
