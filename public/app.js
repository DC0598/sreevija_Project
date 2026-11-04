const $ = (s) => document.querySelector(s);
const app = $("#app");
const money = (n) => "₹" + n.toLocaleString("en-IN");
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const textileImages = {
  Kanjivaram: "https://images.unsplash.com/photo-1641699862936-be9f49b1c38d?auto=format&fit=crop&w=900&q=85",
  Silk: "https://images.unsplash.com/photo-1650324371896-f0b4bc2238dd?auto=format&fit=crop&w=900&q=85",
  Dharmavaram: "https://images.unsplash.com/photo-1635452141122-51866572620c?auto=format&fit=crop&w=900&q=85",
  Bridal: "https://images.unsplash.com/photo-1778148046511-27141f5f01ae?auto=format&fit=crop&w=900&q=85",
};
const defaultTextileImage = "https://images.unsplash.com/photo-1650324371896-f0b4bc2238dd?auto=format&fit=crop&w=900&q=85";
const featuredImages = [textileImages.Kanjivaram, textileImages.Silk, textileImages.Bridal, textileImages.Dharmavaram];
const swatchStyle = (p) => p.image
  ? `background: #eee url('${encodeURI(p.image)}') center/cover`
  : `background: #eee url('${textileImages[p.category] || defaultTextileImage}') center/cover`;
const discount = (p) => (p.mrp > 0 ? Math.max(0, Math.round((1 - p.price / p.mrp) * 100)) : 0);
const FREE_SHIP = 1999, SHIP_FEE = 99;

let PRODUCTS = [], CATEGORIES = [];
let wishlist = new Set();
async function loadWishlist() {
  wishlist = new Set();
  if (auth) try { wishlist = new Set(await api("/wishlist")); } catch {}
}
async function toggleWish(id) {
  if (!auth) { toast("Please login to use your wishlist"); location.hash = "#/login"; return; }
  const on = wishlist.has(id);
  try {
    await api("/wishlist/" + id, { method: on ? "DELETE" : "PUT" });
    on ? wishlist.delete(id) : wishlist.add(id);
    route(true);
  } catch (e) { toast(e.message); }
}
let auth = JSON.parse(localStorage.getItem("auth") || "null"); // { token, user }

async function api(path, opts = {}) {
  const headers = { ...(opts.body && !(opts.body instanceof FormData) ? { "Content-Type": "application/json" } : {}) };
  if (auth) headers.Authorization = "Bearer " + auth.token;
  const res = await fetch("/api" + path, {
    ...opts, headers,
    body: opts.body && !(opts.body instanceof FormData) ? JSON.stringify(opts.body) : opts.body,
  });
  const data = await res.json().catch(() => ({}));
  if (res.status === 401 && auth) { setAuth(null); }
  if (!res.ok) throw new Error(data.error || "Something went wrong");
  return data;
}
function setAuth(a) {
  auth = a;
  a ? localStorage.setItem("auth", JSON.stringify(a)) : localStorage.removeItem("auth");
  renderAuthLinks();
}
function renderAuthLinks() {
  $("#authLinks").innerHTML = auth
    ? `${auth.user.isAdmin ? '<a href="#/admin">Admin</a> ' : ""}<a href="#/wishlist">♥ Wishlist</a> <a href="#/orders">My Orders</a> <a href="#" id="logoutLink">Logout</a>`
    : `<a href="#/login">Login</a>`;
}
async function loadProducts() {
  PRODUCTS = await api("/products");
  CATEGORIES = [...new Set(PRODUCTS.map((p) => p.category))];
}

// ---------- cart (persisted) ----------
let cart = JSON.parse(localStorage.getItem("cart") || "[]");
const saveCart = () => { localStorage.setItem("cart", JSON.stringify(cart)); updateCount(); };
const updateCount = () => { $("#cartCount").textContent = cart.reduce((s, i) => s + i.qty, 0); };
function addToCart(id, qty = 1) {
  const p = PRODUCTS.find((x) => x.id === id);
  const line = cart.find((i) => i.id === id);
  const next = (line ? line.qty : 0) + qty;
  if (next > p.stock) { toast(p.stock <= 0 ? "Out of stock" : `Only ${p.stock} left in stock`); return false; }
  line ? (line.qty = next) : cart.push({ id, qty });
  saveCart();
  toast("Added to cart");
  return true;
}
const cartTotals = () => {
  const subtotal = cart.reduce((s, i) => s + PRODUCTS.find((p) => p.id === i.id).price * i.qty, 0);
  const shipping = subtotal === 0 || subtotal >= FREE_SHIP ? 0 : SHIP_FEE;
  return { subtotal, shipping, total: subtotal + shipping };
};
let toastTimer;
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 1800);
}

// ---------- components ----------
const stockLabel = (p) => p.stock <= 0 ? `<b class="low">Out of stock</b>` : p.stock <= 5 ? `<b class="low">Only ${p.stock} left</b>` : `<span class="ok">${p.stock} in stock</span>`;
const heart = (p) => `<button class="heart ${wishlist.has(p.id) ? "on" : ""}" data-wish="${p.id}" aria-label="Wishlist">${wishlist.has(p.id) ? "♥" : "♡"}</button>`;
const card = (p) => `
  <div class="card">
    <div class="swatch-wrap"><a href="#/product/${p.id}"><div class="swatch" style="${swatchStyle(p)}"><span class="badge">${discount(p)}% OFF</span></div></a>${heart(p)}</div>
    <div class="info">
      <a href="#/product/${p.id}" class="name">${esc(p.name)}</a>
      <span class="muted">${esc(p.fabric)} · ★ ${p.rating}</span>
      <span class="price">${money(p.price)}<s>${money(p.mrp)}</s></span>
      <span class="muted">${stockLabel(p)}</span>
      <button class="btn" data-add="${p.id}" ${p.stock <= 0 ? "disabled" : ""}>${p.stock <= 0 ? "Out of Stock" : "Add to Cart"}</button>
    </div>
  </div>`;
const featureCard = (p, index) => {
  const image = p.image || featuredImages[index % featuredImages.length];
  return `
    <article class="feature-card">
      <a class="feature-image-link" href="#/product/${p.id}" aria-label="View ${esc(p.name)}">
        <div class="feature-image" role="img" aria-label="${esc(p.name)}" style="background: #eee url('${encodeURI(image)}') center/cover"></div>
      </a>
      <div class="feature-info">
        <a class="feature-name" href="#/product/${p.id}">${esc(p.name)}</a>
        <strong>${money(p.price)}</strong>
        <button class="bag-button" data-add="${p.id}" aria-label="Add ${esc(p.name)} to cart" ${p.stock <= 0 ? "disabled" : ""}>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 8h14l1 13H4L5 8Z"/><path d="M9 9V6a3 3 0 0 1 6 0v3"/></svg>
        </button>
      </div>
    </article>`;
};

// ---------- pages ----------
function home() {
  const bestsellers = [...PRODUCTS].sort((a, b) => b.rating - a.rating).slice(0, 4);
  const categories = [
    { title: "Silk Sarees", category: "Silk", image: textileImages.Kanjivaram },
    { title: "Handloom Sarees", category: "Dharmavaram", image: textileImages.Silk },
    { title: "Festive Collection", category: "Bridal", image: textileImages.Bridal },
  ];
  app.innerHTML = `
    <section class="hero">
      <div class="hero-copy">
        <span class="eyebrow">Woven with devotion</span>
        <h1>Weaving Tradition,<br>Celebrating Elegance</h1>
        <div class="hero-flourish" aria-hidden="true"><span></span>✿<span></span></div>
        <p>Discover sarees crafted for every story,<br>every celebration.</p>
        <a class="btn alt" href="#/shop">Explore Collection <span aria-hidden="true">›</span></a>
      </div>
      <a class="hero-image-credit" href="#/shop" aria-label="Explore the saree collection"></a>
      <div class="hero-dots" aria-hidden="true"><i></i><i></i><i></i></div>
    </section>
    <section class="category-section" aria-label="Shop collections">
      <div class="category-cards">${categories.map((c) => `
        <a class="category-card" href="#/shop?category=${encodeURIComponent(c.category)}" style="--category-image:url('${c.image}')">
          <span>${esc(c.title)} <b aria-hidden="true">›</b></span>
        </a>`).join("")}
      </div>
    </section>
    <div class="heritage-line"><span aria-hidden="true">✿</span><p>Timeless Weaves <b>·</b> Thoughtful Craftsmanship <b>·</b> Made to Be Cherished</p><span aria-hidden="true">✿</span></div>
    <section class="section bestsellers" id="bestsellers">
      <div class="section-title"><span></span><h2>Bestsellers</h2><span></span></div>
      <div class="grid featured-grid">${bestsellers.map(featureCard).join("")}</div>
    </section>
    <section class="story-section" id="story">
      <span class="eyebrow">A legacy in every thread</span>
      <h2>Tradition, treasured for generations</h2>
      <p>We bring together heirloom-worthy silks and handloom sarees, chosen for the artistry, care and stories woven into every drape.</p>
      <a class="text-link" href="#/shop">Discover the collection <span aria-hidden="true">→</span></a>
    </section>`;
}

function shop(params) {
  const f = {
    category: params.get("category") || "", fabric: params.get("fabric") || "", occasion: params.get("occasion") || "",
    maxPrice: +params.get("max") || 20000, sort: params.get("sort") || "popular", q: (params.get("q") || "").toLowerCase(), sale: params.get("sale"),
  };
  let list = PRODUCTS.filter((p) =>
    (!f.category || p.category === f.category) && (!f.fabric || p.fabric === f.fabric) && (!f.occasion || p.occasion === f.occasion) &&
    p.price <= f.maxPrice && (!f.sale || discount(p) >= 20) &&
    (!f.q || `${p.name} ${p.fabric} ${p.color} ${p.category}`.toLowerCase().includes(f.q)));
  const sorters = { popular: (a, b) => b.rating - a.rating, low: (a, b) => a.price - b.price, high: (a, b) => b.price - a.price, new: (a, b) => b.date - a.date };
  list.sort(sorters[f.sort]);
  const uniq = (k) => [...new Set(PRODUCTS.map((p) => p[k]))];
  const opts = (vals, cur) => `<option value="">All</option>` + vals.map((v) => `<option ${v === cur ? "selected" : ""}>${esc(v)}</option>`).join("");
  app.innerHTML = `
    <section class="section shop">
      <aside class="filters" id="filters">
        <h3>Filters</h3>
        <h4>Category</h4><select name="category">${opts(CATEGORIES, f.category)}</select>
        <h4>Fabric</h4><select name="fabric">${opts(uniq("fabric"), f.fabric)}</select>
        <h4>Occasion</h4><select name="occasion">${opts(uniq("occasion"), f.occasion)}</select>
        <h4>Max price: <span id="maxLbl">${money(f.maxPrice)}</span></h4>
        <input type="range" name="max" min="1000" max="20000" step="500" value="${f.maxPrice}" style="width:100%">
        <p><a href="#/shop" class="muted">Clear all</a></p>
      </aside>
      <div>
        <div class="toolbar"><b>${list.length} sarees${f.q ? ` for "${esc(f.q)}"` : ""}</b>
          <select name="sort">${[["popular", "Popularity"], ["new", "Newest"], ["low", "Price: Low to High"], ["high", "Price: High to Low"]].map(([v, l]) => `<option value="${v}" ${v === f.sort ? "selected" : ""}>${l}</option>`).join("")}</select></div>
        ${list.length ? `<div class="grid">${list.map(card).join("")}</div>` : `<div class="empty">No sarees match your filters.</div>`}
      </div>
    </section>`;
  const update = () => {
    const q = new URLSearchParams(params);
    document.querySelectorAll("#filters [name], .toolbar [name]").forEach((el) => {
      const v = el.value;
      v && !(el.name === "max" && +v === 20000) ? q.set(el.name, v) : q.delete(el.name);
    });
    location.hash = "#/shop?" + q;
  };
  document.querySelectorAll("#filters select, .toolbar select, #filters input").forEach((el) => el.addEventListener("change", update));
  $("#filters input").addEventListener("input", (e) => ($("#maxLbl").textContent = money(+e.target.value)));
}

function product(id) {
  const p = PRODUCTS.find((x) => x.id === id);
  if (!p) return notFound();
  let qty = 1;
  const related = PRODUCTS.filter((x) => x.category === p.category && x.id !== p.id).slice(0, 4);
  app.innerHTML = `
    <section class="section detail">
      <div class="swatch" style="${swatchStyle(p)}"></div>
      <div>
        <p class="muted"><a href="#/shop">Shop</a> / <a href="#/shop?category=${encodeURIComponent(p.category)}">${esc(p.category)}</a></p>
        <h1>${esc(p.name)}</h1>
        <span class="muted">★ ${p.rating} · ${stockLabel(p)}</span> ${heart(p)}
        <p class="price">${money(p.price)}<s>${money(p.mrp)}</s> <span class="muted">(${discount(p)}% off)</span></p>
        <p>${esc(p.description)}</p>
        <div class="dots">${p.colors.map((c) => `<span class="dot" style="background:${esc(c)}"></span>`).join("")}</div>
        <div class="row">
          <div class="qty"><button id="minus">−</button><span id="qty">1</span><button id="plus">+</button></div>
          <button class="btn" id="add" ${p.stock <= 0 ? "disabled" : ""}>Add to Cart</button>
          <button class="btn alt" id="buy" ${p.stock <= 0 ? "disabled" : ""}>Buy Now</button>
        </div>
        <div class="pin"><input id="pin" maxlength="6" placeholder="Enter pincode"><button class="btn ghost" id="pinBtn">Check</button></div>
        <p id="pinMsg" class="muted"></p>
        <table class="specs">
          <tr><td class="muted">Fabric</td><td>${esc(p.fabric)}</td></tr><tr><td class="muted">Colour</td><td>${esc(p.color)}</td></tr>
          <tr><td class="muted">Occasion</td><td>${esc(p.occasion)}</td></tr><tr><td class="muted">Length</td><td>5.5 m + 0.8 m blouse piece</td></tr>
          <tr><td class="muted">Care</td><td>Dry clean only</td></tr>
        </table>
      </div>
    </section>
    ${related.length ? `<section class="section"><h2>You may also like</h2><div class="grid">${related.map(card).join("")}</div></section>` : ""}`;
  $("#minus").onclick = () => { qty = Math.max(1, qty - 1); $("#qty").textContent = qty; };
  $("#plus").onclick = () => { qty = Math.min(p.stock, qty + 1); $("#qty").textContent = qty; };
  $("#add").onclick = () => addToCart(p.id, qty);
  $("#buy").onclick = () => { if (addToCart(p.id, qty)) location.hash = "#/checkout"; };
  $("#pinBtn").onclick = async () => {
    try {
      const r = await api("/pincode/" + encodeURIComponent($("#pin").value.trim()));
      $("#pinMsg").textContent = `✅ Delivery available in ${r.days} days`;
    } catch (e) { $("#pinMsg").textContent = e.message; }
  };
}

function cartPage() {
  if (!cart.length) { app.innerHTML = `<section class="section empty"><h2>Your cart is empty</h2><a class="btn" href="#/shop">Continue shopping</a></section>`; return; }
  const t = cartTotals();
  app.innerHTML = `
    <section class="section"><h2>Shopping Cart</h2>
      ${cart.map((i) => { const p = PRODUCTS.find((x) => x.id === i.id); return `
        <div class="cart-item">
          <div class="swatch" style="${swatchStyle(p)}"></div>
          <div><a href="#/product/${p.id}"><b>${esc(p.name)}</b></a><br><span class="muted">${esc(p.fabric)}</span></div>
          <div class="qty"><button data-dec="${p.id}">−</button><span>${i.qty}</span><button data-inc="${p.id}">+</button></div>
          <div><b>${money(p.price * i.qty)}</b><br><a href="#" data-rm="${p.id}" class="muted">Remove</a></div>
        </div>`; }).join("")}
      <div class="summary">
        <div><span>Subtotal</span><span>${money(t.subtotal)}</span></div>
        <div><span>Shipping</span><span>${t.shipping ? money(t.shipping) : "FREE"}</span></div>
        <div class="total"><span>Total</span><span>${money(t.total)}</span></div>
        <a class="btn" style="width:100%;text-align:center;margin-top:12px" href="#/checkout">Proceed to Checkout</a>
      </div>
    </section>`;
}

function checkout() {
  if (!cart.length) return (location.hash = "#/cart");
  const t = cartTotals();
  app.innerHTML = `
    <section class="section checkout">
      <form class="form" id="coForm">
        <h2>Delivery Details</h2>
        <div class="two"><input required name="name" placeholder="Full name"><input required name="phone" pattern="[6-9][0-9]{9}" placeholder="Mobile (10 digits)"></div>
        <input required type="email" name="email" placeholder="Email">
        <textarea required name="address" rows="2" placeholder="Address"></textarea>
        <div class="two"><input required name="city" placeholder="City"><input required name="pincode" pattern="[1-9][0-9]{5}" placeholder="Pincode"></div>
        <h3>Payment</h3>
        <select name="payment_method"><option>UPI</option><option>Credit / Debit Card</option><option>Net Banking</option><option>Cash on Delivery</option></select>
        <button class="btn">Place Order · ${money(t.total)}</button>
        <p class="muted" id="coErr" style="color:#c2506b"></p>
        <p class="muted">Online payment gateway is not connected yet: pay on delivery or via manual confirmation.</p>
      </form>
      <div class="summary" style="margin:0;height:fit-content">
        <h3>Order Summary</h3>
        ${cart.map((i) => { const p = PRODUCTS.find((x) => x.id === i.id); return `<div><span>${esc(p.name)} × ${i.qty}</span><span>${money(p.price * i.qty)}</span></div>`; }).join("")}
        <div><span>Shipping</span><span>${t.shipping ? money(t.shipping) : "FREE"}</span></div>
        <div class="total"><span>Total</span><span>${money(t.total)}</span></div>
      </div>
    </section>`;
  if (auth) { $("#coForm [name=name]").value = auth.user.name; $("#coForm [name=email]").value = auth.user.email; }
  $("#coForm").onsubmit = async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector("button");
    btn.disabled = true;
    try {
      const data = Object.fromEntries(new FormData(e.target));
      const o = await api("/orders", { method: "POST", body: { ...data, items: cart } });
      cart = []; saveCart();
      await loadProducts();
      app.innerHTML = `<section class="section empty"><h1>🎉 Thank you!</h1><p>Your order <b>${esc(o.id)}</b> has been placed. Total ${money(o.total)}.</p><a class="btn" href="#/">Back to home</a></section>`;
    } catch (err) {
      $("#coErr").textContent = err.message;
      btn.disabled = false;
      await loadProducts();
    }
  };
}

function authPage(mode) {
  const reg = mode === "register";
  app.innerHTML = `
    <section class="section" style="max-width:420px;margin:auto">
      <form class="form" id="authForm">
        <h2>${reg ? "Create account" : "Login"}</h2>
        ${reg ? '<input required name="name" placeholder="Full name">' : ""}
        <input required type="email" name="email" placeholder="Email">
        <input required type="password" name="password" minlength="${reg ? 8 : 1}" placeholder="Password${reg ? " (min 8 characters)" : ""}">
        <button class="btn">${reg ? "Register" : "Login"}</button>
        <p class="muted" id="authErr" style="color:#c2506b"></p>
        <p class="muted">${reg ? 'Have an account? <a href="#/login"><u>Login</u></a>' : 'New here? <a href="#/register"><u>Create an account</u></a>'}</p>
      </form>
    </section>`;
  $("#authForm").onsubmit = async (e) => {
    e.preventDefault();
    try {
      const r = await api(`/auth/${reg ? "register" : "login"}`, { method: "POST", body: Object.fromEntries(new FormData(e.target)) });
      setAuth(r);
      await loadWishlist();
      location.hash = r.user.isAdmin ? "#/admin" : "#/";
    } catch (err) { $("#authErr").textContent = err.message; }
  };
}

function wishlistPage() {
  if (!auth) { location.hash = "#/login"; return; }
  const list = PRODUCTS.filter((p) => wishlist.has(p.id));
  app.innerHTML = `<section class="section"><h2>My Wishlist</h2>${list.length ? `<div class="grid">${list.map(card).join("")}</div>` : `<div class="empty">Your wishlist is empty. <a href="#/shop"><u>Browse sarees</u></a></div>`}</section>`;
}

async function ordersPage() {
  if (!auth) return (location.hash = "#/login");
  app.innerHTML = `<section class="section"><h2>My Orders</h2><div id="ol">Loading…</div></section>`;
  try {
    const orders = await api("/orders");
    $("#ol").innerHTML = orders.length ? orders.map((o) => `
      <div class="cart-item" style="grid-template-columns:1fr auto">
        <div><b>${esc(o.id)}</b> · ${new Date(o.created_at * 1000).toLocaleDateString("en-IN")}<br>
          <span class="muted">${o.items.map((i) => `${esc(i.name)} × ${i.qty}`).join(", ")}</span></div>
        <div style="text-align:right"><b>${money(o.total)}</b><br><span class="muted">${esc(o.status)} · ${esc(o.payment_method)}</span></div>
      </div>`).join("") : `<div class="empty">No orders yet.</div>`;
  } catch (e) { $("#ol").textContent = e.message; }
}

async function adminPage() {
  if (!auth || !auth.user.isAdmin) { location.hash = "#/login"; return; }
  app.innerHTML = `<section class="section"><h2>Admin Dashboard</h2>
    <div class="perks" id="stats"></div>
    <h3>Orders</h3><div id="orders">Loading…</div>
    <h3>Products</h3>
    <form class="form" id="pForm" style="margin-bottom:16px">
      <input type="hidden" name="id">
      <div class="two"><input required name="name" placeholder="Name"><input required name="category" placeholder="Category (Kanjivaram, Dharmavaram, Silk, Bridal)"></div>
      <div class="two"><input required name="fabric" placeholder="Fabric"><input required name="color" placeholder="Colour"></div>
      <div class="two"><input required name="occasion" placeholder="Occasion"><input required type="number" min="0" name="stock" placeholder="Stock"></div>
      <div class="two"><input required type="number" min="0" name="price" placeholder="Price ₹"><input required type="number" min="0" name="mrp" placeholder="MRP ₹"></div>
      <div class="two"><input name="c1" type="color" value="#e8a0b4" title="Colour 1"><input name="c2" type="color" value="#f3c4b3" title="Colour 2"></div>
      <textarea name="description" rows="2" placeholder="Description"></textarea>
      <input type="file" name="file" accept="image/jpeg,image/png,image/webp">
      <input type="hidden" name="image">
      <div><button class="btn" id="pSave">Add product</button> <button type="button" class="btn ghost" id="pReset">Clear</button></div>
      <p id="pErr" class="muted" style="color:#c2506b"></p>
    </form>
    <div id="products"></div></section>`;
  const form = $("#pForm");
  const refresh = async () => {
    try {
      const [st, orders, prods] = await Promise.all([api("/admin/stats"), api("/admin/orders"), api("/admin/products")]);
      $("#stats").innerHTML = [["Orders", st.orders], ["Revenue", money(st.revenue)], ["Products", st.products], ["Low stock", st.lowStock]]
        .map(([k, v]) => `<div><b>${v}</b><br><span class="muted">${k}</span></div>`).join("");
      $("#orders").innerHTML = orders.map((o) => `
        <div class="cart-item" style="grid-template-columns:1fr auto">
          <div><b>${esc(o.id)}</b> · ${esc(o.name)} · ${esc(o.phone)}<br>
            <span class="muted">${esc(o.address)}, ${esc(o.city)} ${esc(o.pincode)}<br>${o.items.map((i) => `${esc(i.name)} × ${i.qty}`).join(", ")}</span></div>
          <div style="text-align:right"><b>${money(o.total)}</b> <span class="muted">${esc(o.payment_method)} (${esc(o.payment_status)})</span><br>
            <select data-order="${esc(o.id)}">${["Placed", "Confirmed", "Shipped", "Delivered", "Cancelled"].map((s) => `<option ${s === o.status ? "selected" : ""}>${s}</option>`).join("")}</select>
            <button class="btn ghost" data-paid="${esc(o.id)}" ${o.payment_status === "Paid" ? "disabled" : ""}>Mark paid</button></div>
        </div>`).join("") || `<div class="empty">No orders yet.</div>`;
      $("#products").innerHTML = prods.map((p) => `
        <div class="cart-item" style="grid-template-columns:64px 1fr auto">
          <div class="swatch" style="${swatchStyle(p)}"></div>
          <div><b>${esc(p.name)}</b> ${p.active ? "" : '<span class="muted">(hidden)</span>'}<br><span class="muted">${esc(p.category)} · ${money(p.price)} · stock ${p.stock}</span></div>
          <div><button class="btn ghost" data-edit="${p.id}">Edit</button> ${p.active ? `<button class="btn ghost" data-hide="${p.id}">Hide</button>` : `<button class="btn ghost" data-show="${p.id}">Show</button>`}</div>
        </div>`).join("");
      $("#products").onclick = async (e) => {
        const id = +(e.target.dataset.edit || e.target.dataset.hide || e.target.dataset.show);
        if (!id) return;
        const p = prods.find((x) => x.id === id);
        if (e.target.dataset.edit) {
          for (const k of ["id", "name", "category", "fabric", "color", "occasion", "stock", "price", "mrp", "description", "image"]) form.elements[k].value = p[k];
          form.elements.c1.value = p.colors[0]; form.elements.c2.value = p.colors[1] || p.colors[0];
          $("#pSave").textContent = "Save changes";
          form.scrollIntoView({ behavior: "smooth" });
        } else {
          await api("/admin/products/" + id, { method: "PUT", body: { active: !!e.target.dataset.show } });
          await refresh(); await loadProducts();
        }
      };
      $("#orders").onchange = async (e) => {
        if (!e.target.dataset.order) return;
        try { await api("/admin/orders/" + e.target.dataset.order, { method: "PATCH", body: { status: e.target.value } }); toast("Order updated"); await refresh(); await loadProducts(); }
        catch (er) { toast(er.message); }
      };
      $("#orders").onclick = async (e) => {
        if (!e.target.dataset.paid) return;
        await api("/admin/orders/" + e.target.dataset.paid, { method: "PATCH", body: { payment_status: "Paid" } });
        await refresh();
      };
    } catch (e) { toast(e.message); }
  };
  const reset = () => { form.reset(); form.elements.id.value = ""; form.elements.image.value = ""; $("#pSave").textContent = "Add product"; };
  $("#pReset").onclick = reset;
  form.onsubmit = async (e) => {
    e.preventDefault();
    const f = form.elements;
    try {
      let image = f.image.value;
      if (f.file.files[0]) {
        const fd = new FormData(); fd.append("file", f.file.files[0]);
        image = (await api("/admin/upload", { method: "POST", body: fd })).url;
      }
      const payload = {
        name: f.name.value, category: f.category.value, fabric: f.fabric.value, color: f.color.value, occasion: f.occasion.value,
        stock: f.stock.value, price: f.price.value, mrp: f.mrp.value, description: f.description.value, image, colors: [f.c1.value, f.c2.value],
      };
      const id = f.id.value;
      await api(id ? "/admin/products/" + id : "/admin/products", { method: id ? "PUT" : "POST", body: payload });
      toast("Saved"); reset(); await refresh(); await loadProducts();
    } catch (er) { $("#pErr").textContent = er.message; }
  };
  refresh();
}

const notFound = () => (app.innerHTML = `<section class="section empty"><h2>Page not found</h2><a class="btn" href="#/">Home</a></section>`);

// ---------- router ----------
function route(keepScroll) {
  const [path, qs] = (location.hash.slice(1) || "/").split("?");
  const params = new URLSearchParams(qs || "");
  $("#nav").classList.remove("open");
  $("#menuBtn").setAttribute("aria-expanded", "false");
  if (keepScroll !== true) window.scrollTo(0, 0);
  const m = path.match(/^\/product\/(\d+)$/);
  if (path === "/") home();
  else if (path === "/story" || path === "/contact") {
    home();
    requestAnimationFrame(() => document.getElementById(path === "/story" ? "story" : "contact")?.scrollIntoView({ behavior: "smooth" }));
  }
  else if (path === "/shop") shop(params);
  else if (m) product(+m[1]);
  else if (path === "/cart") cartPage();
  else if (path === "/checkout") checkout();
  else if (path === "/login") authPage("login");
  else if (path === "/register") authPage("register");
  else if (path === "/orders") ordersPage();
  else if (path === "/wishlist") wishlistPage();
  else if (path === "/admin") adminPage();
  else notFound();
}

document.addEventListener("click", (e) => {
  const t = e.target instanceof Element ? e.target.closest("[data-add], [data-wish], [data-inc], [data-dec], [data-rm]") : null;
  if (!t) return;
  if (t.dataset.add) return void addToCart(+t.dataset.add);
  if (t.dataset.wish) { e.preventDefault(); return void toggleWish(+t.dataset.wish); }
  const change = (id, d) => {
    const line = cart.find((i) => i.id === id), p = PRODUCTS.find((x) => x.id === id);
    line.qty = Math.min(p.stock, line.qty + d);
    if (line.qty < 1) cart = cart.filter((i) => i.id !== id);
    saveCart(); cartPage();
  };
  if (t.dataset.inc) change(+t.dataset.inc, 1);
  if (t.dataset.dec) change(+t.dataset.dec, -1);
  if (t.dataset.rm) { e.preventDefault(); cart = cart.filter((i) => i.id !== +t.dataset.rm); saveCart(); cartPage(); }
});
$("#searchForm").addEventListener("submit", (e) => { e.preventDefault(); location.hash = "#/shop?q=" + encodeURIComponent($("#searchInput").value.trim()); });
$("#menuBtn").addEventListener("click", () => {
  const open = $("#nav").classList.toggle("open");
  $("#menuBtn").setAttribute("aria-expanded", String(open));
});
$("#newsletter").addEventListener("submit", (e) => { e.preventDefault(); e.target.reset(); toast("Thanks for subscribing!"); });
$("#authLinks").addEventListener("click", async (e) => {
  if (e.target.id !== "logoutLink") return;
  e.preventDefault();
  await api("/auth/logout", { method: "POST" }).catch(() => {});
  setAuth(null);
  wishlist = new Set();
  location.hash = "#/";
});
window.addEventListener("hashchange", route);

(async function boot() {
  renderAuthLinks();
  try {
    await loadProducts();
  } catch {
    app.innerHTML = `<section class="section empty"><h2>Could not load products. Is the server running?</h2></section>`;
    return;
  }
  cart = cart.filter((i) => PRODUCTS.some((p) => p.id === i.id));
  saveCart();
  if (auth) {
    try { const r = await api("/auth/me"); setAuth({ token: auth.token, user: r.user }); } catch {}
    await loadWishlist();
  }
  route();
})();
