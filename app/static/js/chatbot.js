/**
 * ORYA Chatbot Client Logic
 */
window.ORYA = window.ORYA || {};

ORYA.chatbot = (function() {
    const ICON_PATH = "/static/images/icon%20with%20out%20back.png";
    let isOpen = false;
    const elements = {};

    function init() {
        console.log("Chatbot script loaded");
        // Create UI if not exists
        if (!document.getElementById('chatbot-widget')) {
            createUI();
        }

        elements.toggle = document.getElementById('chatbot-toggle');
        elements.window = document.getElementById('chatbot-window');
        elements.messages = document.getElementById('chatbot-messages');
        elements.input = document.getElementById('chatbot-input');
        elements.sendBtn = document.getElementById('chatbot-send-btn');
        elements.closeBtn = document.getElementById('chatbot-close');
        elements.clearBtn = document.getElementById('chatbot-clear');

        elements.toggle.addEventListener('click', () => {
            console.log("Chatbot toggle clicked");
            toggleChat();
        });
        elements.closeBtn.addEventListener('click', () => {
            console.log("Chatbot close clicked");
            toggleChat();
        });
        elements.clearBtn.addEventListener('click', clearChat);
        elements.sendBtn.addEventListener('click', sendMessage);
        elements.input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        window.addEventListener('languageChanged', () => {
            if (window.updateTranslations && elements.window) {
                window.updateTranslations(elements.window);
            }
            if (elements.messages && elements.messages.children.length === 1) {
                const welcomeAr = window.__ORYA_CHATBOT_WELCOME_AR__ || "أهلاً بكِ في أوريا 🌸 كيف يمكنني مساعدتكِ اليوم؟";
                const welcomeEn = window.__ORYA_CHATBOT_WELCOME_EN__ || "Welcome to ORYA 🌸 How can I help you today?";
                elements.messages.innerHTML = '';
                appendBotMessage(window.currentLang === 'ar' ? welcomeAr : welcomeEn);
            }
        });

        // Load History or Initial Greeting
        loadHistory();
    }

    async function loadHistory() {
        try {
            const sid = getSessionId();
            const uid = window.__ORYA_USER_ID__ || '';
            const response = await fetch(`/api/chatbot/history?session_id=${sid}&user_id=${uid}`);
            const data = await response.json();
            
            if (data.success && data.history && data.history.length > 0) {
                data.history.forEach(msg => {
                    if (msg.sender === 'user') {
                        appendUserMessage(msg.text, false);
                    } else {
                        appendBotMessage(msg.text, false);
                    }
                });
                scrollToBottom();
            } else {
                const welcomeAr = window.__ORYA_CHATBOT_WELCOME_AR__ || "أهلاً بكِ في أوريا 🌸 كيف يمكنني مساعدتكِ اليوم؟";
                const welcomeEn = window.__ORYA_CHATBOT_WELCOME_EN__ || "Welcome to ORYA 🌸 How can I help you today?";
                appendBotMessage(window.currentLang === 'ar' ? welcomeAr : welcomeEn);
            }
        } catch (e) {
            console.error("Failed to load chat history", e);
            const welcomeAr = window.__ORYA_CHATBOT_WELCOME_AR__ || "أهلاً بكِ في أوريا 🌸 كيف يمكنني مساعدتكِ اليوم؟";
            const welcomeEn = window.__ORYA_CHATBOT_WELCOME_EN__ || "Welcome to ORYA 🌸 How can I help you today?";
            appendBotMessage(window.currentLang === 'ar' ? welcomeAr : welcomeEn);
        }
    }

    function createUI() {
        const widget = document.createElement('div');
        widget.id = 'chatbot-widget';
        widget.innerHTML = `
            <div class="chatbot-toggle" id="chatbot-toggle">
                <svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
            </div>
            <div class="chatbot-window" id="chatbot-window">
                <div class="chatbot-header">
                    <div class="chatbot-header-info">
                        <div class="chatbot-avatar-main">
                            <img src="${ICON_PATH}" alt="ORYA AI">
                            <div class="online-status"></div>
                        </div>
                        <div class="chatbot-title">
                            <h4 data-i18n="chatbot_name">ORYA ChatBot</h4>
                            <span data-i18n="chatbot_online">Online</span>
                        </div>
                    </div>
                    <div class="chatbot-header-actions">
                        <div class="chatbot-clear" id="chatbot-clear" title="مسح المحادثة">
                            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                        </div>
                        <div class="chatbot-close" id="chatbot-close">✕</div>
                    </div>
                </div>
                <div class="chatbot-messages" id="chatbot-messages"></div>
                <div class="chatbot-input-container">
                    <div class="chatbot-input-area">
                        <input type="text" id="chatbot-input" data-i18n-placeholder="chatbot_placeholder" placeholder="Type your message here...">
                        <button class="chatbot-send-btn" id="chatbot-send-btn">
                            <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path></svg>
                        </button>
                    </div>
                </div>
                <div class="chatbot-footer-brand">Powered by ChatBot</div>
            </div>
        `;
        document.body.appendChild(widget);
        if (window.i18n && window.i18n.apply) window.i18n.apply();
    }

    function toggleChat() {
        isOpen = !isOpen;
        elements.window.classList.toggle('active', isOpen);
        if (isOpen) {
            elements.input.focus();
            scrollToBottom();
        }
    }

    async function sendMessage() {
        const text = elements.input.value.trim();
        if (!text) return;

        appendUserMessage(text);
        elements.input.value = '';

        // Typing indicator
        const typingId = appendTypingIndicator();

        try {
            const response = await fetch('/api/chatbot/message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: text,
                    lang: window.currentLang,
                    session_id: getSessionId(),
                    user_id: window.__ORYA_USER_ID__ || null
                })
            });

            const result = await response.json();
            removeTypingIndicator(typingId);

            if (result.success) {
                const { reply, action, data } = result.data;
                appendBotMessage(reply);

                if (action === 'show_products') {
                    appendProducts(data);
                } else if (action === 'human_handoff') {
                    showHandoffOptions(data);
                }
            } else {
                appendBotMessage(window.currentLang === 'ar' ? 'عذراً، حدث خطأ ما.' : 'Sorry, something went wrong.');
            }
        } catch (error) {
            removeTypingIndicator(typingId);
            appendBotMessage(window.currentLang === 'ar' ? 'عذراً، تعذر الاتصال بالسيرفر.' : 'Sorry, could not connect to server.');
        }
    }

    function appendUserMessage(text) {
        const container = document.createElement('div');
        container.className = 'chat-msg-container chat-msg-container-user';
        container.innerHTML = `<div class="chat-msg chat-msg-user">${text}</div>`;
        elements.messages.appendChild(container);
        scrollToBottom();
    }

    function formatBotMessage(text) {
        let out = text;

        // 1. Strikethrough: ~~text~~ → <s>text</s>
        out = out.replace(/~~(.+?)~~/g, '<s>$1</s>');

        // 2. Markdown links: [label](url) → <a href="url">label</a>
        out = out.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label, url) => {
            // Skip broken AI placeholders like /product/[PRODUCT_ID] or /product/ID
            if (/\[PRODUCT_?ID\]/i.test(url) || /\/product\/\[/i.test(url)) {
                // Return just the label text without a broken link
                return `<span class="chat-product-label">🔗 ${label}</span>`;
            }
            // Fix common AI mistake: /products/<id> → /product/<id>
            if (/^\/products\/\d+/.test(url)) {
                url = url.replace(/^\/products\//, '/product/');
            }
            const isExternal = url.startsWith('http');
            return `<a href="${url}" class="chat-product-link" ${isExternal ? 'target="_blank" rel="noopener"' : ''}>${label}</a>`;
        });

        // 3. Also fix any raw broken links that are NOT in markdown format
        // e.g. if AI writes plain text: /product/[PRODUCT_ID] — strip the placeholder
        out = out.replace(/\/product\/\[PRODUCT_?ID\]/gi, '');
        out = out.replace(/\/products\/(\d+)/g, '/product/$1');

        // 4. Newlines → <br>
        out = out.replace(/\n/g, '<br>');
        return out;
    }

    function appendBotMessage(text) {
        const container = document.createElement('div');
        container.className = 'chat-msg-container chat-msg-container-bot';
        container.innerHTML = `
            <div class="chat-mini-avatar">
                <img src="${ICON_PATH}" alt="AI">
            </div>
            <div class="chat-msg chat-msg-bot">${formatBotMessage(text)}</div>
        `;
        elements.messages.appendChild(container);
        scrollToBottom();
    }

    function appendTypingIndicator() {
        const id = 'typing-' + Date.now();
        const container = document.createElement('div');
        container.id = id;
        container.className = 'chat-msg-container chat-msg-container-bot';
        container.innerHTML = `
            <div class="chat-mini-avatar">
                <img src="${ICON_PATH}" alt="AI">
            </div>
            <div class="chat-msg chat-msg-bot"><span class="typing-dots">...</span></div>
        `;
        elements.messages.appendChild(container);
        scrollToBottom();
        return id;
    }

    function removeTypingIndicator(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function appendProducts(products) {
        const grid = document.createElement('div');
        grid.className = 'chat-products-grid';
        products.forEach(p => {
            const card = document.createElement('a');
            card.href = `/product/${p.id}`;
            card.className = 'chat-product-card';
            card.innerHTML = `
                <img src="${p.image}" class="chat-product-img">
                <div class="chat-product-info">
                    <span class="chat-product-name">${p.name}</span>
                    <span class="chat-product-price">${window.formatPrice(p.price)}</span>
                </div>
            `;
            grid.appendChild(card);
        });
        elements.messages.appendChild(grid);
        scrollToBottom();
    }

    function showHandoffOptions(data) {
        const whatsapp = data?.whatsapp || '9627XXXXXXXX';
        const lang = window.currentLang;
        const div = document.createElement('div');
        div.className = 'chat-msg chat-msg-bot';
        div.innerHTML = `
            <div class="chat-handoff-options">
                <a href="https://wa.me/${whatsapp.replace(/\D/g,'')}" target="_blank" class="chat-handoff-btn chat-handoff-whatsapp">
                    📱 ${lang === 'ar' ? 'واتساب مباشرة' : 'WhatsApp Now'}
                </a>
                <button class="chat-handoff-btn chat-handoff-ticket" onclick="ORYA.chatbot.showTicketForm()">
                    ✉️ ${lang === 'ar' ? 'اترك رسالة' : 'Leave a Message'}
                </button>
            </div>
        `;
        elements.messages.appendChild(div);
        scrollToBottom();
    }

    function showTicketForm() {
        const lang = window.currentLang;
        const div = document.createElement('div');
        div.className = 'chat-msg chat-msg-bot';
        div.innerHTML = `
            <div class="chat-ticket-form">
                <textarea id="ticket-desc" placeholder="${lang === 'ar' ? 'اكتبي مشكلتك هنا...' : 'Describe your issue here...'}" rows="3"></textarea>
                <button onclick="ORYA.chatbot.submitTicket()">${lang === 'ar' ? 'إرسال ✉️' : 'Send ✉️'}</button>
            </div>
        `;
        elements.messages.appendChild(div);
        scrollToBottom();
    }

    async function submitTicket() {
        const desc = document.getElementById('ticket-desc')?.value.trim();
        if (!desc) return;

        const response = await fetch('/api/chatbot/ticket', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                description: desc,
                user_id: window.__ORYA_USER_ID__ || null,
                session_id: getSessionId()
            })
        });

        const result = await response.json();
        if (result.success) {
            appendBotMessage(window.currentLang === 'ar' ? 'تم إرسال رسالتك ✅ سنتواصل معك قريباً 🌸' : 'Message sent ✅ We will contact you soon 🌸');
        }
    }

    function clearChat() {
        const confirmMsg = window.currentLang === 'ar' ? 'هل أنتِ متأكدة من مسح المحادثة؟' : 'Are you sure you want to clear the chat?';
        if (confirm(confirmMsg)) {
            const uid = window.__ORYA_USER_ID__ || 'guest';
            localStorage.removeItem('orya_chat_session_' + uid);
            if (elements.messages) {
                elements.messages.innerHTML = '';
            }
            loadHistory();
        }
    }

    function scrollToBottom() {
        if (!elements.messages) return;
        
        // Immediate scroll after DOM update
        requestAnimationFrame(() => {
            elements.messages.scrollTop = elements.messages.scrollHeight;
        });

        // Fallback timeout to account for animations and image loading
        setTimeout(() => {
            elements.messages.scrollTop = elements.messages.scrollHeight;
        }, 300);
    }

    function getSessionId() {
        const uid = window.__ORYA_USER_ID__ || 'guest';
        const key = 'orya_chat_session_' + uid;
        let sid = localStorage.getItem(key);
        if (!sid) {
            sid = 'sid-' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem(key, sid);
        }
        return sid;
    }

    return {
        init,
        showTicketForm,
        submitTicket
    };
})();

// Auto-init
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', ORYA.chatbot.init);
} else {
    ORYA.chatbot.init();
}
