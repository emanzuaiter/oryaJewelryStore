/**
 * ORYA Luxury Jewelry - Language Management
 */

(function() {
    // 1. Initial State
    // Sync localStorage with the language rendered by the server (Jinja) on first load
    const serverLang = document.documentElement.lang || 'ar';
    let currentLang = localStorage.getItem('orya_lang');
    
    if (!currentLang || currentLang !== serverLang) {
        currentLang = serverLang;
        localStorage.setItem('orya_lang', currentLang);
    }

    /**
     * Translate a key based on current language
     * @param {string} key 
     * @returns {string}
     */
    window.t = function(key) {
        if (!window.TRANSLATIONS) {
            console.warn('ORYA: TRANSLATIONS constant not found. Ensure i18n.js is loaded.');
            return key;
        }
        return window.TRANSLATIONS[currentLang][key] || key;
    };

    /**
     * Format a price according to current language currency
     * @param {number|string} amount 
     * @returns {string}
     */
    window.formatPrice = function(amount) {
        const currency = window.t('price_currency') || 'JOD';
        return parseFloat(amount).toFixed(3) + ' ' + currency;
    };

    /**
     * Update all translatable elements in the DOM
     */
    function updateDOM() {
        // UI specific logic: Temporarily disable drawer transitions to prevent them sliding across the screen when direction changes
        const drawers = document.querySelectorAll('.drawer, .cart-drawer, .nav-drawer');
        const originalTransitions = [];
        const activeStates = [];

        drawers.forEach((drawer, idx) => {
            originalTransitions[idx] = drawer.style.transition;
            // Save and temporarily remove 'active' class to prevent any visual glitch
            activeStates[idx] = drawer.classList.contains('active');
            drawer.style.transition = 'none';
            // Ensure drawer stays in its current open/closed state by freezing it
            if (!activeStates[idx]) {
                drawer.style.visibility = 'hidden';
            }
        });

        // Set document attributes for CSS and RTL/LTR support
        document.documentElement.lang = currentLang;
        document.documentElement.dir = (currentLang === 'ar') ? 'rtl' : 'ltr';

        // Update all elements with [data-i18n] attribute
        const elements = document.querySelectorAll('[data-i18n]');
        elements.forEach(el => {
            const key = el.getAttribute('data-i18n');
            const translation = window.t(key);
            
            if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                el.placeholder = translation;
            } else {
                el.textContent = translation;
            }
        });

        // Update elements with dynamic server-side configurations
        const dynamicElements = document.querySelectorAll('[data-dynamic-ar][data-dynamic-en]');
        dynamicElements.forEach(el => {
            const arText = el.getAttribute('data-dynamic-ar') || '';
            const enText = el.getAttribute('data-dynamic-en') || '';
            const rawText = (currentLang === 'ar') ? arText : enText;
            el.innerHTML = rawText.replace(/\r\n|\r|\n/g, '<br>');
        });

        // Update elements with specific placeholder attribute
        const placeholders = document.querySelectorAll('[data-i18n-placeholder]');
        placeholders.forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            el.placeholder = window.t(key);
        });

        // UI specific logic: Flip cart drawer direction
        drawers.forEach((drawer, idx) => {
            if (currentLang === 'ar') {
                drawer.classList.add('rtl');
                drawer.classList.remove('ltr');
            } else {
                drawer.classList.add('ltr');
                drawer.classList.remove('rtl');
            }
            
            // Force a reflow to apply styles instantly
            void drawer.offsetHeight;
            
            // Restore transition and visibility
            drawer.style.transition = originalTransitions[idx];
            if (!activeStates[idx]) {
                drawer.style.visibility = '';
            }
        });
        
        // Update lang toggle buttons text
        const langToggleBtns = document.querySelectorAll('#lang-toggle');
        langToggleBtns.forEach(btn => {
            btn.textContent = (currentLang === 'ar') ? 'EN' : 'AR';
        });

    }

    /**
     * Toggle between Arabic and English
     */
    window.toggleLang = function() {
        currentLang = (currentLang === 'ar') ? 'en' : 'ar';
        localStorage.setItem('orya_lang', currentLang);
        
        // Update UI immediately
        updateDOM();

        // Dispatch custom event for other scripts to react (only on manual toggle)
        window.dispatchEvent(new CustomEvent('languageChanged', { detail: { lang: currentLang } }));

        // Sync preference with backend API
        fetch('/api/set-language', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ lang: currentLang })
        })
        .then(response => response.json())
        .then(data => {
            if (!data.success) console.error('ORYA: Server failed to sync language preference.');
        })
        .catch(err => console.error('ORYA: Language sync error:', err));
    };

    /**
     * Getter for current language
     */
    Object.defineProperty(window, 'currentLang', {
        get: function() { return currentLang; },
        enumerable: true
    });

    /**
     * Update all translatable elements in the DOM (aliased for other scripts)
     */
    window.updateTranslations = function(root = document) {
        // Update all elements with [data-i18n] attribute within the root
        const elements = root.querySelectorAll('[data-i18n]');
        elements.forEach(el => {
            const key = el.getAttribute('data-i18n');
            const translation = window.t(key);
            
            if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                el.placeholder = translation;
            } else {
                el.textContent = translation;
            }
        });

        // Update elements with dynamic server-side configurations within the root
        const dynamicElements = root.querySelectorAll('[data-dynamic-ar][data-dynamic-en]');
        dynamicElements.forEach(el => {
            const arText = el.getAttribute('data-dynamic-ar') || '';
            const enText = el.getAttribute('data-dynamic-en') || '';
            const rawText = (currentLang === 'ar') ? arText : enText;
            el.innerHTML = rawText.replace(/\r\n|\r|\n/g, '<br>');
        });

        // Update elements with specific placeholder attribute
        const placeholders = root.querySelectorAll('[data-i18n-placeholder]');
        placeholders.forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            el.placeholder = window.t(key);
        });
        
        // If root is document, also run the rest of updateDOM logic
        if (root === document) {
            updateDOM();
        }
    };

    // Expose i18n.apply as an alias
    window.i18n = {
        apply: window.updateTranslations
    };

    // Initialize on DOMContentLoaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', updateDOM);
    } else {
        updateDOM();
    }

})();
