/**
 * ORYA Luxury Jewelry - Shopping Cart Logic
 * Handles persistence via localStorage, dynamic rendering, and totals.
 */

(function() {
    let cart = [];
    let appliedCoupon = null; // Store the currently applied coupon
    // Dynamic delivery configuration loaded from base.html
    function getActiveDeliveryFee(subtotal, totalItems, cartItems) {
        const defaultFee = window.__ORYA_DELIVERY_FEE__ ?? 3.0;
        const rule = window.__ORYA_FREE_DELIVERY_RULE__ || 'disabled';
        
        if (rule === 'always') return 0.0;
        
        if (rule === 'min_amount') {
            const minAmount = window.__ORYA_FREE_DELIVERY_MIN_AMOUNT__ ?? 0.0;
            if (minAmount > 0 && subtotal >= minAmount) return 0.0;
        }
        
        if (rule === 'min_quantity') {
            const minQty = window.__ORYA_FREE_DELIVERY_MIN_QUANTITY__ ?? 2;
            if (minQty > 0 && totalItems >= minQty) return 0.0;
        }
        
        if (rule === 'date_range') {
            const startDate = window.__ORYA_FREE_DELIVERY_START_DATE__;
            const endDate = window.__ORYA_FREE_DELIVERY_END_DATE__;
            if (startDate && endDate) {
                const today = new Date();
                const year = today.getFullYear();
                const month = String(today.getMonth() + 1).padStart(2, '0');
                const day = String(today.getDate()).padStart(2, '0');
                const todayStr = `${year}-${month}-${day}`;
                if (todayStr >= startDate && todayStr <= endDate) {
                    return 0.0;
                }
            }
        }
        
        if (rule === 'category') {
            const targetCategory = window.__ORYA_FREE_DELIVERY_CATEGORY__ || '';
            if (targetCategory && cartItems && cartItems.length > 0) {
                const hasCategory = cartItems.some(item => (item.category || '').toLowerCase() === targetCategory.toLowerCase());
                if (hasCategory) return 0.0;
            }
        }

        return defaultFee;
    }

    // Each user gets their own isolated cart key
    function getStorageKey() {
        const uid = window.__ORYA_USER_ID__ || 'guest';
        return 'orya_cart_' + uid;
    }

    // Load cart on init
    function init() {
        const stored = localStorage.getItem(getStorageKey());
        if (stored) {
            try {
                cart = JSON.parse(stored);
            } catch (e) {
                cart = [];
            }
        }
        
        // Also check if a coupon was stored
        const storedCoupon = localStorage.getItem(getStorageKey() + '_coupon');
        if (storedCoupon) {
            try {
                appliedCoupon = JSON.parse(storedCoupon);
            } catch (e) {}
        }

        updateCartCount();
        renderCart();
        setupCouponListener();
    }

    function setupCouponListener() {
        const applyBtn = document.getElementById('apply-coupon');
        if (applyBtn) {
            applyBtn.addEventListener('click', async () => {
                const input = document.getElementById('coupon-input');
                const code = input ? input.value.trim() : '';
                if (!code) return;

                const subtotal = cart.reduce((acc, item) => acc + (item.price * item.quantity), 0);
                
                try {
                    const res = await fetch('/api/coupons/validate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ code: code, subtotal: subtotal })
                    });
                    const result = await res.json();
                    
                    if (result.success && result.data.valid) {
                        appliedCoupon = { code: result.data.code, discount: result.data.discount };
                        localStorage.setItem(getStorageKey() + '_coupon', JSON.stringify(appliedCoupon));
                        window.showToast(window.t('coupon_applied') || 'Coupon applied successfully', 'success');
                        renderCart(); // Re-render to update totals
                    } else {
                        window.showToast(result.message || window.t('coupon_invalid') || 'Invalid coupon', 'error');
                        appliedCoupon = null;
                        localStorage.removeItem(getStorageKey() + '_coupon');
                        renderCart();
                    }
                } catch (e) {
                    console.error('Coupon error:', e);
                    window.showToast('Error validating coupon', 'error');
                }
            });
        }
    }

    function saveCart() {
        localStorage.setItem(getStorageKey(), JSON.stringify(cart));
        updateCartCount();
    }

    window.addToCart = function(id, qty = 1) {
        const existing = cart.find(item => item.id == id);
        if (existing) {
            existing.quantity += qty;
            saveCart();
            renderCart();
            window.showToast(window.t('product_added'), 'success');
        } else {
            // Fetch product details for better UX (or we could pass them from the button)
            fetch(`/api/products/${id}`)
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        const p = data.data;
                        cart.push({
                            id: p.id,
                            name_ar: p.name_ar,
                            name_en: p.name_en,
                            price: p.sale_price || p.price,
                            image: p.primary_image,
                            material: p.material,
                            category: p.category,
                            quantity: qty
                        });
                        saveCart();
                        renderCart();
                        window.showToast(window.t('product_added'), 'success');
                    }
                })
                .catch(err => {
                    console.error('Add to cart error:', err);
                    window.showToast('Error adding to cart', 'error');
                });
        }
    };

    window.removeFromCart = function(id) {
        cart = cart.filter(item => item.id != id);
        saveCart();
        
        // Re-validate coupon if cart changes
        if (appliedCoupon) revalidateCoupon();
        else renderCart();
        
        window.showToast(window.t('removed_from_cart'), 'info');
    };

    window.updateQuantity = function(id, delta) {
        const item = cart.find(i => i.id == id);
        if (item) {
            item.quantity += delta;
            if (item.quantity <= 0) {
                window.removeFromCart(id);
            } else {
                saveCart();
                if (appliedCoupon) revalidateCoupon();
                else renderCart();
            }
        }
    };

    async function revalidateCoupon() {
        const subtotal = cart.reduce((acc, item) => acc + (item.price * item.quantity), 0);
        if (subtotal === 0) {
            appliedCoupon = null;
            localStorage.removeItem(getStorageKey() + '_coupon');
            renderCart();
            return;
        }

        try {
            const res = await fetch('/api/coupons/validate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code: appliedCoupon.code, subtotal: subtotal })
            });
            const result = await res.json();
            if (result.success && result.data.valid) {
                appliedCoupon.discount = result.data.discount;
                localStorage.setItem(getStorageKey() + '_coupon', JSON.stringify(appliedCoupon));
            } else {
                appliedCoupon = null;
                localStorage.removeItem(getStorageKey() + '_coupon');
                window.showToast(window.t('coupon_invalid') || 'Coupon removed: conditions no longer met', 'error');
            }
        } catch (e) {
            console.error(e);
        }
        renderCart();
    }

    function updateCartCount() {
        const count = cart.reduce((acc, item) => acc + item.quantity, 0);
        const el = document.getElementById('cart-count');
        if (el) {
            el.textContent = count;
            el.style.display = count > 0 ? 'flex' : 'none';
        }
    }

    function renderCart() {
        const container = document.getElementById('cart-items');
        if (!container) return;

        if (cart.length === 0) {
            container.innerHTML = `
                <div class="empty-cart-state" style="text-align:center; padding:40px 20px;">
                    <p data-i18n="cart_empty">${window.t('cart_empty')}</p>
                    <a href="/products/all" class="btn-gold" style="margin-top:20px; display:inline-block;" data-i18n="hero_cta">${window.t('hero_cta')}</a>
                </div>
            `;
            updateTotals(0);
            return;
        }

        let html = '';
        let subtotal = 0;

        cart.forEach(item => {
            const name = window.currentLang === 'ar' ? item.name_ar : item.name_en;
            const lineTotal = item.price * item.quantity;
            subtotal += lineTotal;

            html += `
                <div class="cart-item">
                    <div class="cart-item-main">
                        <div class="cart-item-img-wrap">
                            <img src="${item.image}" alt="${name}">
                        </div>
                        <div class="cart-item-details">
                            <h4 class="cart-item-name">${name}</h4>
                            <div class="cart-item-meta">
                                <span>${window.formatPrice(item.price)}</span>
                                ${item.material ? ` • <span>${item.material}</span>` : ''}
                            </div>
                        </div>
                    </div>
                    
                    <div class="cart-item-actions">
                        <div class="cart-item-qty">
                            <button onclick="updateQuantity(${item.id}, -1)">−</button>
                            <input type="text" value="${item.quantity}" readonly>
                            <button onclick="updateQuantity(${item.id}, 1)">+</button>
                        </div>
                        
                        <div class="cart-item-price-total">
                            ${window.formatPrice(lineTotal)}
                        </div>
                        
                        <button class="cart-item-remove-btn" onclick="removeFromCart(${item.id})" aria-label="Remove">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"></path><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path></svg>
                        </button>
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
        updateTotals(subtotal);
    }

    function updateTotals(subtotal) {
        const subtotalEl = document.getElementById('cart-subtotal');
        const deliveryEl = document.getElementById('cart-delivery');
        const totalEl = document.getElementById('cart-total');
        const discountRow = document.getElementById('discount-row');
        const discountEl = document.getElementById('cart-discount');
        const couponInput = document.getElementById('coupon-input');

        const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
        const activeDeliveryFee = subtotal > 0 ? getActiveDeliveryFee(subtotal, totalItems, cart) : 0;

        if (subtotalEl) subtotalEl.textContent = window.formatPrice(subtotal);
        if (deliveryEl) {
            if (subtotal > 0 && activeDeliveryFee === 0) {
                deliveryEl.textContent = (window.currentLang === 'ar' ? 'توصيل مجاني' : 'Free Delivery');
            } else {
                deliveryEl.textContent = window.formatPrice(activeDeliveryFee);
            }
        }
        
        let discount = 0;
        if (appliedCoupon && subtotal > 0) {
            discount = appliedCoupon.discount;
            if (discountRow) discountRow.style.display = 'flex';
            if (discountEl) discountEl.textContent = '-' + window.formatPrice(discount);
            if (couponInput) couponInput.value = appliedCoupon.code;
        } else {
            if (discountRow) discountRow.style.display = 'none';
            if (couponInput && !appliedCoupon) couponInput.value = '';
        }

        if (totalEl) {
            const total = subtotal > 0 ? Math.max(0, subtotal - discount + activeDeliveryFee) : 0;
            totalEl.textContent = window.formatPrice(total);
        }
    }

    // Export to window for global access
    window.getCartItems = () => cart;
    window.getAppliedCoupon = () => appliedCoupon; // Used by checkout page
    window.clearCart = () => {
        cart = [];
        appliedCoupon = null;
        localStorage.removeItem(getStorageKey());
        localStorage.removeItem(getStorageKey() + '_coupon');
        renderCart();
        updateCartCount();
    };
    window.renderCart = renderCart;

    // Listen to language changes to update cart display
    window.addEventListener('languageChanged', () => {
        renderCart();
    });

    // Initialize on load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
