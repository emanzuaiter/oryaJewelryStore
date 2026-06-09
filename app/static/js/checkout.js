/**
 * ORYA Luxury Jewelry - Checkout Logic (VERSION 13 - FIXED DOM TIMING)
 */

(function() {
    console.log('--- ORYA CHECKOUT JS V13 LOADED ---');

    let cart = [];
    let appliedCoupon = null; 
    let currentSubtotal = 0;
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
    let otpTimerInterval = null;

    // DOM Elements - initialized in init()
    let elements = {};

    function tx(key) {
        if (window.t && typeof window.t === 'function') return window.t(key);
        return key;
    }

    function notify(message, type = 'info') {
        console.log(`Notification [${type}]: ${message}`);
        if (window.showToast && typeof window.showToast === 'function') {
            window.showToast(message, type);
        } else {
            alert(message);
        }
    }

    function showCouponMsg(text, isSuccess) {
        if (!elements.couponMsg) return;
        elements.couponMsg.textContent = text;
        elements.couponMsg.style.color = isSuccess ? '#27ae60' : '#e74c3c';
        elements.couponMsg.style.display = 'block';
    }

    function loadCart() {
        if (window.getCartItems) {
            cart = window.getCartItems();
        } else {
            cart = [];
        }
        
        if (window.getAppliedCoupon) {
            appliedCoupon = window.getAppliedCoupon();
            if (appliedCoupon && elements.couponInput) {
                elements.couponInput.value = appliedCoupon.code;
            }
        }
    }

    function renderSummary() {
        console.log('Rendering summary with cart size:', cart.length);
        if (cart.length === 0) {
            if (window.location.pathname.includes('/checkout')) {
                window.location.href = '/products/all';
            }
            return;
        }

        let html = '';
        let subtotal = 0;

        cart.forEach(item => {
            const name = window.currentLang === 'ar' ? (item.name_ar || item.name) : (item.name_en || item.name);
            const lineTotal = item.price * item.quantity;
            subtotal += lineTotal;

            html += `
                <div class="summary-item" style="display:flex; gap:15px; margin-bottom:15px; align-items:center;">
                    <div style="width:50px; height:50px; border-radius:6px; overflow:hidden; border:1px solid var(--border); flex-shrink:0;">
                        <img src="${item.image}" alt="${name}" style="width:100%; height:100%; object-fit:cover;">
                    </div>
                    <div style="flex:1; min-width:0;">
                        <div style="font-size:14px; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${name}</div>
                        <div style="font-size:12px; color:var(--text-muted);">${item.quantity} × ${window.formatPrice(item.price)}</div>
                    </div>
                    <div style="font-weight:600; font-size:14px; flex-shrink:0;">${window.formatPrice(lineTotal)}</div>
                </div>
            `;
        });

        if (elements.checkoutItemsContainer) elements.checkoutItemsContainer.innerHTML = html;
        currentSubtotal = subtotal;
        updateTotals();
    }

    function updateTotals() {
        const discount = appliedCoupon ? appliedCoupon.discount : 0;
        const afterDisc = Math.max(0, currentSubtotal - discount);
        const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
        const delivery = currentSubtotal > 0 ? getActiveDeliveryFee(currentSubtotal, totalItems, cart) : 0;
        const total = afterDisc + delivery;

        if (elements.summarySubtotal) elements.summarySubtotal.textContent = window.formatPrice(currentSubtotal);
        if (elements.summaryDelivery) {
            if (currentSubtotal > 0 && delivery === 0) {
                elements.summaryDelivery.textContent = (window.currentLang === 'ar' ? 'توصيل مجاني' : 'Free Delivery');
            } else {
                elements.summaryDelivery.textContent = window.formatPrice(delivery);
            }
        }
        if (elements.summaryTotal) elements.summaryTotal.textContent = window.formatPrice(total);

        if (discount > 0 && elements.summaryDiscRow && elements.summaryDiscount) {
            elements.summaryDiscount.textContent = '-' + window.formatPrice(discount);
            elements.summaryDiscRow.style.display = 'flex';
        } else if (elements.summaryDiscRow) {
            elements.summaryDiscRow.style.display = 'none';
        }
    }

    // --- Separated Function: Validate Coupon ---
    async function validateCoupon(e) {
        if (e) {
            e.preventDefault();
        }
        
        console.log('--- COUPON VALIDATION STARTED ---');
        
        const code = elements.couponInput ? elements.couponInput.value.trim().toUpperCase() : '';
        
        // Variable Validation
        if (!code || code === '') {
            console.error('Coupon code is empty because input is missing or empty.', { couponInputNode: elements.couponInput });
            notify(tx('coupon_invalid'), 'error');
            return;
        }

        if (typeof currentSubtotal === 'undefined' || currentSubtotal === null) {
            console.error('Validation failed: currentSubtotal is undefined or null');
            return;
        }

        console.log('Data to send:', { code, subtotal: currentSubtotal });

        if (elements.couponBtn) {
            elements.couponBtn.disabled = true;
            elements.couponBtn.dataset.originalText = elements.couponBtn.textContent;
            elements.couponBtn.textContent = '...';
        }

        try {
            console.log('Sending fetch request to /api/coupons/validate');
            // URL Check: leading slash included
            const response = await fetch('/api/coupons/validate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code: code, subtotal: currentSubtotal })
            });
            
            const json = await response.json();
            console.log('API Response received:', json);

            if (json.success && json.data && json.data.valid) {
                appliedCoupon = { code: json.data.code, discount: json.data.discount };
                updateTotals();
                showCouponMsg(tx('coupon_applied'), true);
                notify(tx('coupon_applied'), 'success');
                
                if (elements.couponInput) elements.couponInput.readOnly = true;
                if (elements.couponBtn) {
                    elements.couponBtn.textContent = '✓';
                    elements.couponBtn.style.background = '#27ae60';
                }
            } else {
                appliedCoupon = null;
                updateTotals();
                const errorMsg = json.message || tx('coupon_invalid');
                showCouponMsg(errorMsg, false);
                notify(errorMsg, 'error');
                
                if (elements.couponBtn) {
                    elements.couponBtn.disabled = false;
                    elements.couponBtn.textContent = elements.couponBtn.dataset.originalText || tx('apply_coupon');
                }
            }
        } catch (err) {
            console.error('Coupon validation fetch error:');
            console.dir(err);
            notify('Connection Error', 'error');
            if (elements.couponBtn) {
                elements.couponBtn.disabled = false;
                elements.couponBtn.textContent = elements.couponBtn.dataset.originalText || tx('apply_coupon');
            }
        }
    }

    // --- OTP Verification Modal Helpers ---
    function openOtpModal() {
        const modal = document.getElementById('order-otp-modal');
        if (modal) {
            modal.style.display = 'flex';
            setupOtpInputs();
            startOtpTimer(300); // 5 minutes
        }
    }

    function closeOtpModal() {
        const modal = document.getElementById('order-otp-modal');
        if (modal) {
            modal.style.display = 'none';
            stopOtpTimer();
            const submitBtn = elements.checkoutForm.querySelector('[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = tx('checkout_submit') || 'Place Order';
            }
        }
    }

    function setupOtpInputs() {
        const inputs = document.querySelectorAll('#order-otp-modal .otp-field');
        if (!inputs.length) return;

        inputs.forEach(input => input.value = '');
        inputs[0].focus();

        inputs.forEach((input, index) => {
            input.addEventListener('input', (e) => {
                if (input.value && index < inputs.length - 1) {
                    inputs[index + 1].focus();
                }
            });

            input.addEventListener('keydown', (e) => {
                if (e.key === 'Backspace' && !input.value && index > 0) {
                    inputs[index - 1].focus();
                }
            });

            input.addEventListener('paste', (e) => {
                e.preventDefault();
                const pasteData = (e.clipboardData || window.clipboardData).getData('text').trim();
                if (pasteData.length === 6 && /^\d+$/.test(pasteData)) {
                    for (let i = 0; i < 6; i++) {
                        inputs[i].value = pasteData[i];
                    }
                    inputs[5].focus();
                }
            });
        });
    }

    function startOtpTimer(duration) {
        stopOtpTimer();
        const timerDisplay = document.getElementById('order-otp-timer');
        const verifyBtn = document.getElementById('verify-order-otp-btn');
        const resendContainer = document.getElementById('resend-order-otp-container');

        if (verifyBtn) verifyBtn.disabled = false;
        if (resendContainer) resendContainer.style.display = 'none';

        let timer = duration;
        function updateTimer() {
            let minutes = Math.floor(timer / 60);
            let seconds = timer % 60;

            minutes = minutes < 10 ? '0' + minutes : minutes;
            seconds = seconds < 10 ? '0' + seconds : seconds;

            if (timerDisplay) timerDisplay.textContent = minutes + ':' + seconds;

            if (--timer < 0) {
                clearInterval(otpTimerInterval);
                if (timerDisplay) timerDisplay.textContent = '00:00';
                if (verifyBtn) verifyBtn.disabled = true;
                if (resendContainer) resendContainer.style.display = 'block';
            }
        }

        updateTimer();
        otpTimerInterval = setInterval(updateTimer, 1000);
    }

    function stopOtpTimer() {
        if (otpTimerInterval) {
            clearInterval(otpTimerInterval);
            otpTimerInterval = null;
        }
    }

    async function verifyOrderOtp() {
        const inputs = document.querySelectorAll('#order-otp-modal .otp-field');
        let otpCode = '';
        inputs.forEach(input => otpCode += input.value.trim());

        if (otpCode.length !== 6) {
            notify(window.currentLang === 'ar' ? 'يرجى إدخال رمز التحقق كاملاً (6 أرقام)' : 'Please enter the full 6-digit verification code.', 'error');
            return;
        }

        const verifyBtn = document.getElementById('verify-order-otp-btn');
        if (verifyBtn) {
            verifyBtn.disabled = true;
            verifyBtn.textContent = '...';
        }

        try {
            const response = await fetch('/verify-order-otp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ otp: otpCode })
            });

            const result = await response.json();
            if (result.success) {
                if (window.clearCart) window.clearCart();
                notify(result.message || 'Order confirmed!', 'success');
                window.location.href = result.redirect || '/';
            } else {
                notify(result.message || 'Verification failed', 'error');
                if (verifyBtn) {
                    verifyBtn.disabled = false;
                    verifyBtn.textContent = window.currentLang === 'ar' ? 'تأكيد وإتمام الطلب' : 'Confirm & Complete Order';
                }
            }
        } catch (err) {
            console.error('Order verification fetch error:', err);
            notify('Connection Error', 'error');
            if (verifyBtn) {
                verifyBtn.disabled = false;
                verifyBtn.textContent = window.currentLang === 'ar' ? 'تأكيد وإتمام الطلب' : 'Confirm & Complete Order';
            }
        }
    }

    async function resendOrderOtp(e) {
        if (e) e.preventDefault();

        try {
            const response = await fetch('/resend-order-otp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const result = await response.json();
            if (result.success) {
                notify(result.message || 'Verification code resent!', 'success');
                startOtpTimer(300);
                setupOtpInputs();
            } else {
                notify(result.message || 'Failed to resend code', 'error');
            }
        } catch (err) {
            console.error('Resend order OTP error:', err);
            notify('Connection Error', 'error');
        }
    }

    // --- Separated Function: Create Order (Initiates Verification) ---
    async function createOrder(e) {
        e.preventDefault();
        console.log('--- ORDER CREATION STARTED ---');
        
        const formData = new FormData(elements.checkoutForm);
        const data = {
            full_name: formData.get('full_name'),
            phone: formData.get('phone'),
            city: formData.get('city'),
            address: formData.get('address'),
            national_id: formData.get('national_id'),
            notes: formData.get('notes'),
            coupon_code: appliedCoupon ? appliedCoupon.code : '',
            items: cart.map(item => ({ product_id: item.id, quantity: item.quantity }))
        };

        const submitBtn = elements.checkoutForm.querySelector('[type="submit"]');
        if (submitBtn) { 
            submitBtn.disabled = true; 
            submitBtn.textContent = '...'; 
        }

        try {
            console.log('Sending fetch request to /place-order');
            const response = await fetch('/place-order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            console.log('Order initialization response:', result);
            
            if (result.success) {
                notify(result.message || 'Verification code sent!', 'success');
                openOtpModal();
            } else {
                notify(result.message || 'Error creating order', 'error');
                if (submitBtn) { 
                    submitBtn.disabled = false; 
                    submitBtn.textContent = tx('checkout_submit'); 
                }
            }
        } catch (err) {
            console.error('Order creation fetch error:', err);
            notify('Connection Error', 'error');
            if (submitBtn) { 
                submitBtn.disabled = false; 
                submitBtn.textContent = tx('checkout_submit'); 
            }
        }
    }

    function bindEvents() {
        if (elements.couponBtn) {
            elements.couponBtn.addEventListener('click', validateCoupon);
        }

        if (elements.couponInput) {
            elements.couponInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') validateCoupon(e);
            });
        }

        if (elements.checkoutForm) {
            elements.checkoutForm.addEventListener('submit', createOrder);
        }

        const closeBtn = document.getElementById('close-otp-modal');
        if (closeBtn) closeBtn.addEventListener('click', closeOtpModal);

        const verifyBtn = document.getElementById('verify-order-otp-btn');
        if (verifyBtn) verifyBtn.addEventListener('click', verifyOrderOtp);

        const resendLink = document.getElementById('resend-order-otp-link');
        if (resendLink) resendLink.addEventListener('click', resendOrderOtp);
    }

    function init() {
        console.log('--- ORYA CHECKOUT INIT V13 STARTING ---');
        
        // IMPORTANT: Initialize elements here, when DOM is ready
        elements = {
            checkoutItemsContainer: document.getElementById('checkout-items'),
            summarySubtotal: document.getElementById('summary-subtotal'),
            summaryDelivery: document.getElementById('summary-delivery'),
            summaryDiscRow: document.getElementById('summary-discount-row'),
            summaryDiscount: document.getElementById('summary-discount'),
            summaryTotal: document.getElementById('summary-total'),
            couponInput: document.getElementById('checkout-coupon-input'),
            couponBtn: document.getElementById('checkout-coupon-btn'),
            couponMsg: document.getElementById('checkout-coupon-msg'),
            checkoutForm: document.getElementById('checkout-form')
        };
        
        loadCart();
        bindEvents();
        renderSummary();
    }

    window.renderSummary = renderSummary;

    // Re-render summary on language toggle
    window.addEventListener('languageChanged', () => {
        loadCart();
        renderSummary();
    });

    // Initialize logic safely
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        setTimeout(init, 100);
    }

})();
