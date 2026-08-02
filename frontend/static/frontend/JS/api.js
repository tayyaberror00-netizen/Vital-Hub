/**
 * VITAL HUB - API CLIENT
 * Central helper for all backend communication.
 */

const API_BASE = '/api';

// --- Token helpers ---
const Auth = {
    getToken: () => localStorage.getItem('vh_token'),
    getUser:  () => JSON.parse(localStorage.getItem('vh_user') || 'null'),
    save: (token, user) => {
        localStorage.setItem('vh_token', token);
        localStorage.setItem('vh_user', JSON.stringify(user));
    },
    clear: () => {
        localStorage.removeItem('vh_token');
        localStorage.removeItem('vh_user');
    },
    isLoggedIn: () => !!localStorage.getItem('vh_token')
};

// --- Core fetch wrapper ---
async function apiFetch(endpoint, { method = 'GET', body, auth = false } = {}) {
    const headers = { 'Content-Type': 'application/json', 'Accept': 'application/json' };

    if (auth) {
        const token = Auth.getToken();
        if (!token) {
            window.location.href = '/auth.html';
            return;
        }
        headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(`${API_BASE}${endpoint}`, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined
    });

    // Guard against HTML error pages (Django 404/500, APPEND_SLASH redirects gone wrong, etc.)
    const contentType = res.headers.get('content-type') || '';
    if (!contentType.includes('application/json')) {
        throw new Error(`Server error (${res.status}). Please try again.`);
    }

    const data = await res.json();

    if (!res.ok) {
        const errors = data.errors;
        const msg = (errors && typeof errors === 'object' && !Array.isArray(errors))
            ? Object.values(errors).flat()[0]
            : (Array.isArray(errors) ? errors[0]?.msg : null)
            || data.message || data.detail || 'Something went wrong';
        throw new Error(msg);
    }

    return data;
}

// --- Auth API ---
// Trailing slashes are required — Django's APPEND_SLASH raises an error on POST without them.
const AuthAPI = {
    login:    (email, password)        => apiFetch('/auth/login/',    { method: 'POST', body: { email, password } }),
    register: (name, email, password)  => apiFetch('/auth/register/', { method: 'POST', body: { name, email, password } }),
    logout:   ()                       => apiFetch('/auth/logout/',   { method: 'POST', auth: true }),
    me:       ()                       => apiFetch('/auth/me/',       { auth: true })
};

// --- Products API ---
const ProductsAPI = {
    list:    (params = {}) => apiFetch('/products/?' + new URLSearchParams(params)),
    getById: (id)          => apiFetch(`/products/${id}/`)
};

// --- Orders API ---
const OrdersAPI = {
    place: (payload) => apiFetch('/orders/',  { method: 'POST', body: payload, auth: true }),
    mine:  ()        => apiFetch('/orders/',  { auth: true })
};

// --- Likes / Wishlist API ---
const LikesAPI = {
    check:  (id) => apiFetch(`/products/${id}/like/`,  { auth: true }),
    toggle: (id) => apiFetch(`/products/${id}/like/`,  { method: 'POST', auth: true }),
    mine:   ()   => apiFetch('/products/liked/',        { auth: true }),
};

// --- Appointments API ---
const AppointmentsAPI = {
    book:   (payload) => apiFetch('/appointments/',              { method: 'POST',   body: payload, auth: true }),
    mine:   ()        => apiFetch('/appointments/',              { auth: true }),
    slots:  (date)    => apiFetch(`/appointments/slots/?date=${date}`),
    cancel: (id)      => apiFetch(`/appointments/${id}/`,        { method: 'DELETE', auth: true })
};

// --- Mini Cart ---
(function () {
    function _cart()  { return JSON.parse(localStorage.getItem('vitalHub_cart') || '[]'); }
    function _save(c) {
        localStorage.setItem('vitalHub_cart', JSON.stringify(c));
        document.querySelectorAll('#cart-count').forEach(b => {
            b.textContent = c.length;
            b.style.display = c.length > 0 ? 'flex' : 'none';
        });
    }

    window._mcRemove = function (cartId) {
        _save(_cart().filter(i => String(i.cartId) !== String(cartId)));
        _mcRender();
    };

    function _mcRender() {
        const body    = document.getElementById('_mc_body');
        const footer  = document.getElementById('_mc_footer');
        if (!body) return;
        const staticBase = document.querySelector('meta[name="static-prefix"]')?.content ?? '';
        const items = _cart();

        if (!items.length) {
            body.innerHTML = `<div class="py-8 text-center">
                <svg class="w-10 h-10 text-slate-200 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 3h1.386c.51 0 .955.343 1.087.835l.383 1.437M7.5 14.25a3 3 0 00-3 3h15.75m-12.75-3h11.218c1.121-2.3 2.1-4.684 2.924-7.138a60.114 60.114 0 00-16.536-1.84M7.5 14.25L5.106 5.272M6 20.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm12.75 0a.75.75 0 11-1.5 0 .75.75 0 011.5 0z"/></svg>
                <p class="text-sm font-bold text-slate-400">Your cart is empty</p>
                <a href="/store.html" class="text-blue-600 text-xs font-bold hover:underline mt-1 inline-block">Browse store →</a>
            </div>`;
            if (footer) footer.classList.add('hidden');
            return;
        }

        const subtotal = items.reduce((s, i) => s + Number(i.price) * (i.quantity || 1), 0);
        body.innerHTML = items.map(item => {
            const src = item.img
                ? (item.img.startsWith('http') || item.img.startsWith('/') ? item.img : staticBase + item.img)
                : '';
            return `<div class="flex items-center gap-3 py-3 border-b border-slate-50 last:border-0">
                <div class="w-12 h-12 bg-slate-50 rounded-xl flex-shrink-0 overflow-hidden flex items-center justify-center">
                    ${src ? `<img src="${src}" class="w-full h-full object-contain p-1">` : ''}
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-xs font-black text-slate-800 leading-tight truncate">${item.name || ''}</p>
                    <p class="text-xs text-blue-600 font-bold mt-0.5">Rs. ${Number(item.price).toLocaleString('en-IN', {maximumFractionDigits:0})}</p>
                </div>
                <button onclick="_mcRemove('${item.cartId}')" title="Remove"
                    class="p-1.5 text-slate-300 hover:text-red-500 transition-colors flex-shrink-0">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/>
                    </svg>
                </button>
            </div>`;
        }).join('');

        if (footer) {
            footer.classList.remove('hidden');
            const el = document.getElementById('_mc_subtotal');
            if (el) el.textContent = `Rs. ${subtotal.toLocaleString('en-IN', {maximumFractionDigits:0})}`;
        }
    }

    function _mcOpen(anchor) {
        const popup = document.getElementById('_mini_cart');
        if (!popup) return;
        _mcRender();
        popup.classList.remove('hidden');
        // Position below cart icon, aligned to its right edge
        const rect = anchor.getBoundingClientRect();
        popup.style.top   = (rect.bottom + 10) + 'px';
        popup.style.right = (window.innerWidth - rect.right) + 'px';
        popup.style.left  = 'auto';
    }

    window._mcClose = function () {
        const p = document.getElementById('_mini_cart');
        if (p) p.classList.add('hidden');
    };

    function _buildPopup() {
        const onCheckout = window.location.pathname.includes('checkout');
        const ctaHtml = onCheckout
            ? `<button onclick="_mcClose()" class="block w-full bg-slate-900 text-white text-center py-3 rounded-xl font-black text-[10px] uppercase tracking-widest hover:bg-blue-600 transition-all">Continue to Payment</button>`
            : `<a href="/checkout.html" class="block w-full bg-blue-600 text-white text-center py-3 rounded-xl font-black text-[10px] uppercase tracking-widest hover:bg-slate-900 transition-all">Proceed to Checkout →</a>`;

        const popup = document.createElement('div');
        popup.id = '_mini_cart';
        popup.className = 'fixed hidden z-[300] w-80 bg-white rounded-2xl shadow-2xl border border-slate-100 overflow-hidden';
        popup.innerHTML = `
            <div class="flex items-center justify-between px-5 py-4 border-b border-slate-100">
                <span class="font-black text-sm text-slate-900 uppercase tracking-wider">Cart</span>
                <button onclick="_mcClose()" class="text-slate-400 hover:text-slate-700 transition">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
            </div>
            <div id="_mc_body" class="px-5 overflow-y-auto" style="max-height:280px;"></div>
            <div id="_mc_footer" class="px-5 py-4 border-t border-slate-100 space-y-3 hidden">
                <div class="flex justify-between items-center">
                    <span class="text-[10px] font-black uppercase tracking-widest text-slate-400">Subtotal</span>
                    <span id="_mc_subtotal" class="font-black text-slate-900 text-sm"></span>
                </div>
                ${ctaHtml}
            </div>`;
        document.body.appendChild(popup);
    }

    function _initMiniCart() {
        _buildPopup();

        // Intercept cart icon clicks (the <a> wrapping #cart-count)
        const badge = document.getElementById('cart-count');
        const anchor = badge ? badge.closest('a') : null;
        if (anchor) {
            anchor.addEventListener('click', e => {
                e.preventDefault();
                const popup = document.getElementById('_mini_cart');
                if (popup && !popup.classList.contains('hidden')) {
                    _mcClose();
                } else {
                    _mcOpen(anchor);
                }
            });
        }

        // Close on outside click
        document.addEventListener('click', e => {
            const popup = document.getElementById('_mini_cart');
            if (!popup || popup.classList.contains('hidden')) return;
            if (!popup.contains(e.target) && !(anchor && anchor.contains(e.target))) {
                _mcClose();
            }
        });

        // Close on ESC
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') _mcClose();
        });

        // Sync badge count on load
        const c = _cart();
        document.querySelectorAll('#cart-count').forEach(b => {
            b.textContent = c.length;
            b.style.display = c.length > 0 ? 'flex' : 'none';
        });
    }

    _initMiniCart();
})();

// --- Shared header update ---
// Swaps the "Join Now" CTA for a user avatar + dropdown once logged in,
// and routes admins straight to the dashboard instead of the customer area.
function updateHeaderAuth() {
    const user = Auth.getUser();
    const joinBtn = document.getElementById('join-now-btn');
    const mobileLink = document.getElementById('mobile-join-now-link');
    const heroBtn = document.getElementById('hero-cta-btn');

    if (!user) {
        return; // not logged in — leave the default "Join Now" CTA as-is
    }

    const firstName = (user.name || 'Account').split(' ')[0];
    const initial = (user.name || '?')[0].toUpperCase();
    const isAdmin = user.role === 'admin';
    const dashboardHref = isAdmin ? '/admin-panel/' : '/dashboard.html';
    const dashboardLabel = isAdmin ? 'Admin Console' : 'My Dashboard';

    if (joinBtn) {
        const wrapper = document.createElement('div');
        wrapper.id = 'auth-user-block';
        wrapper.className = 'relative flex items-center gap-2';
        wrapper.innerHTML = `
            <button id="auth-user-toggle" class="flex items-center gap-2 px-2 py-1.5 rounded-xl hover:bg-slate-100 transition-colors">
                <span class="vh-avatar-3d ${isAdmin ? 'is-admin' : ''}" id="vh-avatar-3d">
                    <span>${initial}</span>
                </span>
                <span class="hidden sm:inline text-xs font-bold text-slate-700">${firstName}</span>
                <i data-lucide="chevron-down" class="w-3 h-3 text-slate-400 hidden sm:inline"></i>
            </button>
            <div id="auth-user-dropdown" class="hidden absolute right-0 top-full mt-2 w-48 bg-white rounded-2xl shadow-xl border border-slate-100 py-2 z-[200]">
                <a href="${dashboardHref}" class="flex items-center gap-2 px-4 py-2.5 text-xs font-bold text-slate-700 hover:bg-slate-50 transition-colors">
                    <i data-lucide="${isAdmin ? 'shield' : 'layout-dashboard'}" class="w-3.5 h-3.5"></i> ${dashboardLabel}
                </a>
                <button onclick="AuthAPI.logout().catch(()=>{}).finally(()=>{Auth.clear();window.location.href='/index.html';})"
                        class="w-full flex items-center gap-2 px-4 py-2.5 text-xs font-bold text-red-500 hover:bg-red-50 transition-colors text-left">
                    <i data-lucide="log-out" class="w-3.5 h-3.5"></i> Logout
                </button>
            </div>`;
        joinBtn.replaceWith(wrapper);
        if (window.lucide) lucide.createIcons();

        document.getElementById('auth-user-toggle').addEventListener('click', (e) => {
            e.stopPropagation();
            document.getElementById('auth-user-dropdown').classList.toggle('hidden');
        });
        document.addEventListener('click', () => {
            document.getElementById('auth-user-dropdown')?.classList.add('hidden');
        });

        // 3D tilt-on-hover for the avatar sphere (Apple-icon style), pure CSS
        // transforms driven by pointer position — no WebGL/model loading cost.
        const avatar = document.getElementById('vh-avatar-3d');
        if (avatar) {
            avatar.addEventListener('mousemove', (e) => {
                const rect = avatar.getBoundingClientRect();
                const x = (e.clientX - rect.left) / rect.width - 0.5;
                const y = (e.clientY - rect.top) / rect.height - 0.5;
                avatar.style.transform = `perspective(300px) rotateY(${x * 30}deg) rotateX(${-y * 30}deg)`;
            });
            avatar.addEventListener('mouseleave', () => {
                avatar.style.transform = 'perspective(300px) rotateX(0deg) rotateY(0deg)';
            });
        }
    }

    if (mobileLink) {
        mobileLink.textContent = dashboardLabel;
        mobileLink.href = dashboardHref;
    }

    if (heroBtn) {
        heroBtn.href = isAdmin ? '/admin-panel/' : 'store.html';
        heroBtn.textContent = isAdmin ? 'Open Admin Console' : 'Browse the Store';
    }
}

document.addEventListener('DOMContentLoaded', updateHeaderAuth);
