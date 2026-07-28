/**
 * VITAL HUB - UNIFIED CORE LOGIC
 * Handles Cart, Currency Conversion, and Checkout UI
 */

// 1. Initialize State (Unified Key)
let cart = JSON.parse(localStorage.getItem('vitalHub_cart')) || [];
let currentCurrency = localStorage.getItem('selectedCurrency') || 'PKR';

const CURRENCY_CONFIG = {
    PKR: { symbol: "Rs.", rate: 1 },
    USD: { symbol: "$", rate: 0.0036 } 
};

document.addEventListener('DOMContentLoaded', () => {
    if (window.lucide) lucide.createIcons();
    updateCartUI();
    if (document.getElementById('checkout-list')) {
        renderCheckout();
    }
});

// 2. Helper: Format Price based on Currency
function formatPrice(amount) {
    const config = CURRENCY_CONFIG[currentCurrency];
    const converted = (amount * config.rate).toFixed(currentCurrency === 'USD' ? 2 : 0);
    return `${config.symbol} ${Number(converted).toLocaleString()}`;
}

// 3. Global UI Update (Badge)
function updateCartUI() {
    const badges = document.querySelectorAll('#cart-count');
    badges.forEach(badge => {
        badge.innerText = cart.length;
        badge.style.display = cart.length > 0 ? 'flex' : 'none';
    });
}

// 4. Add to Cart
window.addToCart = function(productId) {
    // 'products' must be defined in your products.js
    const productData = products.find(p => p.id === productId);
    
    if (productData) {
        const cartItem = {
            cartId: Date.now() + Math.random(),
            id: productData.id,
            name: productData.name,
            price: productData.price,
            img: productData.img
        };
        
        cart.push(cartItem);
        localStorage.setItem('vitalHub_cart', JSON.stringify(cart));
        updateCartUI();
        alert(`${productData.name} added to your health plan!`);
        if (document.getElementById('checkout-list')) renderCheckout();
    }
};

// 5. Render Checkout & Currency Toggle Logic
function renderCheckout() {
    const list = document.getElementById('checkout-list');
    const subtotalEl = document.getElementById('subtotal-price');
    const totalEl = document.getElementById('total-price');
    const btnPKR = document.getElementById('btn-pkr');
    const btnUSD = document.getElementById('btn-usd');

    if (!list) return;

    // Static prefix for resolving API image paths (e.g. "images/foo.avif" → "/static/frontend/images/foo.avif")
    const staticBase = document.querySelector('meta[name="static-prefix"]')?.content ?? '';

    // Update Currency Buttons Toggle UI
    if (btnPKR && btnUSD) {
        btnPKR.className = currentCurrency === 'PKR'
            ? 'px-4 py-2 rounded-xl text-[10px] font-black bg-slate-900 text-white transition-all shadow-md'
            : 'px-4 py-2 rounded-xl text-[10px] font-black bg-white text-slate-400 hover:text-slate-900 transition-all';
        btnUSD.className = currentCurrency === 'USD'
            ? 'px-4 py-2 rounded-xl text-[10px] font-black bg-slate-900 text-white transition-all shadow-md'
            : 'px-4 py-2 rounded-xl text-[10px] font-black bg-white text-slate-400 hover:text-slate-900 transition-all';
    }

    if (cart.length === 0) {
        list.innerHTML = `
            <div class="py-10 text-center border border-dashed border-white/10 rounded-3xl">
                <p class="text-slate-500 text-[10px] font-black uppercase tracking-widest">Your health plan is empty.</p>
            </div>`;
        if (subtotalEl) subtotalEl.innerText = formatPrice(0);
        if (totalEl) totalEl.innerText = formatPrice(0);
        return;
    }

    let total = 0;
    const fragment = document.createDocumentFragment();
    cart.forEach(item => {
        total += item.price;
        const row = document.createElement('div');
        row.className = 'flex gap-4 items-center group animate-in fade-in slide-in-from-right-4 duration-300';
        row.innerHTML = `
            <div class="w-14 h-14 bg-white rounded-2xl p-2 flex-shrink-0 flex items-center justify-center">
                <img class="w-full h-full object-contain">
            </div>
            <div class="flex-grow">
                <h4 class="text-[10px] font-black uppercase tracking-tight text-white/90 leading-tight"></h4>
                <p class="text-blue-400 text-[10px] font-black mt-1"></p>
            </div>
            <button class="p-2 text-slate-600 hover:text-red-400 transition-colors">
                <i data-lucide="trash-2" size="14"></i>
            </button>
        `;
        // Set dynamic values via DOM properties — never innerHTML — to prevent XSS
        const imgSrc = item.img ? (item.img.startsWith('http') || item.img.startsWith('/') ? item.img : staticBase + item.img) : '';
        row.querySelector('img').src                  = imgSrc;
        row.querySelector('h4').textContent           = item.name;
        row.querySelector('p').textContent            = formatPrice(item.price);
        row.querySelector('button').addEventListener('click', () => removeFromCart(item.cartId));
        fragment.appendChild(row);
    });
    list.innerHTML = '';
    list.appendChild(fragment);

    if (subtotalEl) subtotalEl.innerText = formatPrice(total);
    if (totalEl) totalEl.innerText = formatPrice(total);

    if (window.lucide) lucide.createIcons();
}

// 6. Change Currency
window.changeCurrency = function(currencyCode) {
    currentCurrency = currencyCode;
    localStorage.setItem('selectedCurrency', currencyCode);
    renderCheckout();
};

// 7. Remove Item
window.removeFromCart = function(cartId) {
    cart = cart.filter(item => item.cartId !== cartId);
    localStorage.setItem('vitalHub_cart', JSON.stringify(cart));
    updateCartUI();
    renderCheckout();
};

// 8. Process Order — calls the real backend
window.processOrder = async function() {
    const errorBox = document.getElementById('checkout-error');
    if (errorBox) errorBox.classList.add('hidden');

    if (cart.length === 0) {
        if (errorBox) { errorBox.textContent = 'Your health plan is empty.'; errorBox.classList.remove('hidden'); }
        return;
    }

    // Require login
    if (typeof Auth !== 'undefined' && !Auth.isLoggedIn()) {
        window.location.href = 'auth.html';
        return;
    }

    // Collect shipping
    const firstName = document.getElementById('ship-first')?.value.trim();
    const lastName  = document.getElementById('ship-last')?.value.trim();
    const email     = document.getElementById('ship-email')?.value.trim();
    const address   = document.getElementById('ship-address')?.value.trim();

    if (!firstName || !lastName || !email || !address) {
        if (errorBox) { errorBox.textContent = 'Please complete all shipping details.'; errorBox.classList.remove('hidden'); }
        return;
    }

    const btn = document.getElementById('place-order-btn');
    if (btn) {
        btn.innerHTML = `<i data-lucide="loader-2" class="animate-spin w-4 h-4"></i> Processing...`;
        btn.disabled = true;
        if (window.lucide) lucide.createIcons();
    }

    try {
        const payload = {
            shipping_name:    `${firstName} ${lastName}`,
            shipping_email:   email,
            shipping_address: address,
            items: cart.map(item => ({
                product_id: item.id,
                name:       item.name,
                price:      item.price,
                quantity:   item.quantity || 1,
                img:        item.img || '',
            })),
        };

        let orderId = '';
        if (typeof OrdersAPI !== 'undefined') {
            const result = await OrdersAPI.place(payload);
            orderId = result?.order?.id || '';
        }

        localStorage.removeItem('vitalHub_cart');
        window.location.href = orderId ? `thank-you.html?order=${orderId}` : 'thank-you.html';
    } catch (err) {
        if (errorBox) { errorBox.textContent = err.message; errorBox.classList.remove('hidden'); }
        if (btn) { btn.innerHTML = 'Complete Purchase'; btn.disabled = false; }
    }
};