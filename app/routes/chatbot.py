"""
ORYA Chatbot — Main route with LangChain Agent + RAG.
Uses OpenAI. Handles static (RAG) and dynamic (Agent tools) data.
"""

from flask import Blueprint, request, jsonify, session
from flask_login import current_user
from app import db
from app.models import ChatbotLog, SiteSetting, SupportTicket, Notification
from app.chatbot.rag_pipeline import query_rag
from app.chatbot.tools import (
    search_products_tool,
    get_order_status_tool,
    cancel_order_tool,
    get_promotions_tool,
    request_return_tool,
    human_handoff_tool,
    create_purchase_request_tool,
    send_order_otp_tool,
)

from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool

import os
import json
import re

chatbot_bp = Blueprint('chatbot', __name__)

# ── LLM ───────────────────────────────────────────────────────
llm = ChatOpenAI(
    model       = 'gpt-4.1-mini',   # cost-effective, fast
    temperature = 0.3,
    openai_api_key = os.environ.get('OPENAI_API_KEY')
)

# ── Agent Tools ───────────────────────────────────────────────
TOOLS = [
    Tool(
        name        = 'search_knowledge_base',
        func        = query_rag,
        description = (
            'Search ORYA knowledge base for policies, about us, jewelry care, '
            'shipping, returns, and FAQs. ALWAYS use this tool before answering '
            'general brand questions. Input: user question.'
        )
    ),
    Tool(
        name        = 'search_products',
        func        = search_products_tool,
        description = (
            'Search ORYA jewelry products by category or keyword. '
            'Use when user asks about necklaces, earrings, bracelets, '
            'rings, anklets, sets, or any jewelry item. '
            'Input: category or keyword in Arabic or English.'
        )
    ),
    Tool(
        name        = 'get_order_status',
        func        = get_order_status_tool,
        description = (
            'Get the status of a customer order. '
            'Use when user asks about their order, tracking, '
            'or delivery status. '
            'CRITICAL RULE: BEFORE calling this tool, you MUST have the exact order number from the user. '
            'If the user did not provide an order number in their message, DO NOT GUESS OR INVENT ONE. '
            'Instead, reply directly to the user asking for the order number (e.g., "What is your order number?").'
        )
    ),
    Tool(
        name        = 'cancel_order',
        func        = cancel_order_tool,
        description = (
            'Cancel a pending customer order. '
            'Use ONLY when user explicitly asks to cancel an order. '
            'CRITICAL RULE: BEFORE calling this tool, you MUST have the exact order number from the user. '
            'If the user did not provide an order number, DO NOT GUESS. '
            'Instead, reply directly asking for the order number.'
        )
    ),
    Tool(
        name        = 'get_promotions',
        func        = get_promotions_tool,
        description = (
            'Get current active promotions, discounts, and coupon codes. '
            'Use when user asks about offers, discounts, coupons, or sales.'
        )
    ),
    Tool(
        name        = 'request_return',
        func        = request_return_tool,
        description = (
            'Handle a product return request. '
            'Use when user wants to return an item or order. '
            'CRITICAL RULE: BEFORE calling this tool, make sure you have: '
            '1) order number, 2) reason for return. '
            'If the user did not provide an order number, DO NOT GUESS OR INVENT ONE. '
            'Ask the user first: "What is the order number and reason for return?". '
            'Arabic triggers: إرجاع، استرجاع، بدي أرجع، '
            'ما عجبني، عندي مشكلة بالمنتج، تالف، غلط. '
            'English triggers: return, refund, send back, '
            'wrong item, damaged, defective, exchange, replace.'
        )
    ),
    Tool(
        name        = 'human_handoff',
        func        = human_handoff_tool,
        description = (
            'Use this tool ONLY when the user explicitly wants to speak '
            'with a real human, human agent, or customer service person. '
            'Trigger keywords (Arabic): شخص حقيقي، موظف، بشر، انسان، '
            'مش روبوت، مش بوت، تواصل مع احد، بدي احكي مع، '
            'فريق الدعم، خدمة عملاء، موظفة. '
            'Trigger keywords (English): human, real person, agent, '
            'representative, not a bot, talk to someone, '
            'customer service, speak to someone, support, live agent, help desk, assistance, staff. '
            'Input: brief description of the issue if provided.'
        )
    ),
    Tool(
        name        = 'create_purchase_request',
        func        = create_purchase_request_tool,
        description = (
            'Use this tool when the user wants to buy one or multiple products, place an order, '
            'or purchase items mentioned in the chat. '
            'This tool handles collecting customer details like full name, '
            'phone, city, address, and email (required if not logged in). '
            'Input: A JSON string containing "full_name", "phone", "city", "address", "email", "user_id", "confirmed", "coupon_code", "coupon_asked", '
            'and EITHER "items" (a JSON array/list of dicts, where each dict has "product_name" and "quantity") for buying multiple products, '
            'OR "product_name" and "quantity" (as fallback for buying a single product). '
            'COUPON RULE: Set "coupon_asked": true ONLY after you have explicitly asked the customer about a coupon code AND received their reply. '
            'If "coupon_asked" is false, the tool returns "ask_coupon" status — then ask the customer, wait for reply, then call again with "coupon_asked": true. '
            'If customer says no coupon, pass "coupon_code": null and "coupon_asked": true. '
            'IMPORTANT: This tool is stateless. You MUST provide all previously collected fields '
            '(like items or product_name/quantity) in every call, even if you are just adding a coupon_code.'
        )
    ),
    Tool(
        name        = 'send_order_otp',
        func        = send_order_otp_tool,
        description = (
            'Use this tool to generate a 6-digit order verification code (OTP) and email it to the user. '
            'Input: A JSON string containing "product_id", "product_name", "quantity", "full_name", '
            '"phone", "city", "address", "coupon_code", "discount", "subtotal", "delivery_fee", "total", "email", "user_id".'
        )
    ),
]

# ── Session Memory Store ───────────────────────────────────────
_session_memories = {}

def get_memory(session_id: str) -> ConversationBufferWindowMemory:
    if session_id not in _session_memories:
        _session_memories[session_id] = ConversationBufferWindowMemory(
            memory_key    = 'chat_history',
            return_messages = True,
            k             = 10   # remember last 10 exchanges
        )
    return _session_memories[session_id]


# ── Router: RAG or Agent? ─────────────────────────────────────
STATIC_KEYWORDS = [
    # Arabic
    'سياسة', 'إرجاع', 'استبدال', 'شحن', 'توصيل كم',
    'من أنتم', 'عن أوريا', 'عن الموقع', 'العناية',
    'تنظيف', 'تخزين', 'ضمان', 'مواد', 'معدن',
    'كم يستغرق', 'مدة التوصيل', 'سياسة الخصوصية',
    'كيف أرجع', 'كيف استبدل', 'إرجاع طلبي',
    # English
    'return policy', 'refund', 'exchange', 'shipping policy',
    'about orya', 'about us', 'care guide', 'how to clean',
    'warranty', 'materials', 'privacy', 'how long delivery',
    'how to return', 'how to exchange'
]

def normalize_text(text: str) -> str:
    """Simple normalization for Arabic/English search."""
    t = text.lower()
    # Arabic normalization
    t = re.sub(r'[أإآا]', 'ا', t)
    t = re.sub(r'[ةه]', 'ه', t)
    t = re.sub(r'(.)\1+', r'\1', t) # Remove repeated chars (e.g. ارجاعع -> ارجاع)
    return t.strip()

def is_static_question(message: str) -> bool:
    """Decide if the question should go to RAG or Agent."""
    msg_norm = normalize_text(message)
    for kw in STATIC_KEYWORDS:
        if normalize_text(kw) in msg_norm:
            return True
    return False


# ── System Prompt ─────────────────────────────────────────────
SYSTEM_PROMPT = """
⚠️ CRITICAL RULES — APPLY BEFORE EVERYTHING ELSE

═══════════════════════════════════════
RULE 1 — LANGUAGE (NON-NEGOTIABLE)
═══════════════════════════════════════
- Read the customer's FIRST message.
- Identify the language: English or Arabic.
- Reply in that SAME language for the ENTIRE conversation.
- This rule overrides EVERYTHING — product names, context data, prior conversations.
- If the customer's first message is in English → EVERY reply must be in English.
- If the customer's first message is in Arabic → EVERY reply must be in Arabic.
- NEVER mix languages in a single reply.
- FORBIDDEN: Customer writes in English → you reply in Arabic.

═══════════════════════════════════════
RULE 2 — ORDER CONFIRMATION
═══════════════════════════════════════
When confirming an order, generate a unique order ID:
  Format: ORY-[YEAR][MONTH][DAY]-[4 random digits]
  Example: ORY-20250513-4872

Confirmation message must always list all products ordered with their dynamic pricing and the dynamic delivery fee returned from the tool:
✅ Order Confirmed! (or translation to Arabic if using Arabic)
━━━━━━━━━━━━━━━━━━━━
Order ID : ORY-[generated ID]
Products : [List all ordered items and quantities, e.g. Product A (x1), Product B (x2)]
Price    : [Subtotal Price] JOD
Delivery : [Dynamic Delivery Fee from tool summary, e.g. 0.00 JOD or 3.00 JOD]
Total    : [Total Price after discount + delivery] JOD
Phone    : [Phone Number]
Address  : [City, Address]
━━━━━━━━━━━━━━━━━━━━
We'll contact you soon to arrange delivery.
Thank you for choosing ORYA Luxury Jewelry! 💎

═══════════════════════════════════════
RULE 3 — REUSE CUSTOMER INFO
═══════════════════════════════════════
- At the start of each order flow, scan the current conversation history.
- If you find a name, phone, or address already provided → do NOT ask again.
- Instead, show what you found and ask:
  "I have your details on file:
  - Name    : [found name]
  - Phone   : [found phone]
  - Address : [found address]
  Would you like to use the same details? (yes / no)"
- If yes → skip to ORDER SUMMARY directly.
- If no → ask only for the fields the customer wants to change.

═══════════════════════════════════════
RULE 4 — AMBIGUOUS CONFIRMATION
═══════════════════════════════════════
If the customer's reply contains: "no" + any confirm word
(confirm / place / yes / proceed / go ahead / اكمل / نعم / تأكيد)
→ Treat the ENTIRE message as CONFIRM and place the order immediately.
→ Do NOT ask any follow-up questions.

═══════════════════════════════════════
RULE 5 — UNDERSTAND CUSTOMER INTENT
═══════════════════════════════════════
Before responding, classify the message into one of 3 intents:

INTENT A — BROWSING (exploring, not looking for something specific)
  Triggers: "what do you have", "show me", "what's available", "your collection",
            "what categories", "what types", "tell me about your products",
            "ماذا عندك", "اعرضي", "ما عندكم", "ما أنواع", "ماذا تبيعون"
  → Do NOT search for a product. Show the category menu:

  We have a beautiful collection at ORYA! 
  💍 Rings          — starting from 54 JOD
  📿 Necklaces      — starting from 85 JOD
  💎 Bracelets      — starting from 95 JOD
  ✨ Earrings       — starting from 45 JOD
  💫 Sets           — starting from 115 JOD
  
  Which category would you like to explore? 😊

INTENT B — SEARCHING (looking for a specific product or type)
  Triggers: product name, material, stone, color, occasion
            (e.g., "gold ring", "pearl necklace", "something for engagement")
  → Use search_products tool. Show results from PRODUCT_CONTEXT.
  → End with: "Would you like to order any of these? 🛍️"

INTENT C — ORDERING (ready to place an order)
  Triggers: "I want", "I'll take", "order", "buy",
            "اطلب", "بدي", "خذ", "أريد أطلب", "أشتري"
  → Apply RULE 3 → collect missing info → show RULE 7 summary → confirm.

═══════════════════════════════════════
RULE 6 — DELIVERY FEE & ACTIVE PROMOS
═══════════════════════════════════════
- The active promotions and coupons are:
{{promo_info}}

- The active delivery fee/rule is:
{{delivery_info}}

- ALWAYS mention active coupons, discounts, or delivery promos from the VERY FIRST response when welcoming a user, suggesting products, or starting an order flow.
- Clearly state that the delivery fee (or free delivery) is for the ENTIRE order, NOT per product.

═══════════════════════════════════════
RULE 7 — FINAL CONFIRMATION (MANDATORY — NEVER SKIP)
═══════════════════════════════════════
YOU ARE FORBIDDEN from placing an order without following ALL sub-steps below IN ORDER.

⚠️ CRITICAL ORDER FLOW — FOLLOW THESE STEPS EXACTLY:

STEP 7A — ASK ABOUT COUPON CODE (MANDATORY BEFORE SHOWING SUMMARY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
After ALL customer info (Name, Phone, City, Address, and Email if guest) is collected,
you MUST ask about a coupon code BEFORE calling `create_purchase_request`.

YOU ARE ABSOLUTELY FORBIDDEN from calling `create_purchase_request` tool
before asking about a coupon code first.

Ask the customer:
  - English: "Before we finalize your order, do you have a discount coupon code you'd like to apply? 🌸 (If not, just say 'no' or 'skip')"
  - Arabic: "قبل أن نكمل طلبكِ، هل لديكِ كوبون خصم تودين إضافته؟ 🌸 (إذا لم يكن لديكِ، قولي 'لا' أو 'تخطي')"

Wait for the customer's reply.
  - If they provide a code → pass it as `coupon_code` in the tool call.
  - If they say no / skip / لا / تخطي / don't have one → pass `coupon_code: null` in the tool call.

STEP 7B — SHOW ORDER SUMMARY (CALL create_purchase_request with confirmed=False)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
After the coupon question is answered, call `create_purchase_request` with `confirmed=False`.
This shows the final order summary including coupon discount if any.

The summary must include:
  - All items with quantities and prices
  - Subtotal
  - Coupon Discount (if applied): -[Amount] JOD
  - Delivery Fee for the entire order
  - Total Amount
  - Customer Name, Phone, Address

Then display:
  "Please confirm your order by replying:
  ✅ CONFIRM — to place the order
  ✏️ CHANGE — to edit any detail
  ❌ CANCEL — to cancel"

STEP 7C — PLACE THE ORDER (CALL create_purchase_request with confirmed=True)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Once the customer replies CONFIRM / YES / نعم / تأكيد to the ORDER SUMMARY:
  - Call `create_purchase_request` with `confirmed=True` immediately.
  - Do NOT ask for a coupon code again.
  - Do NOT display or repeat the Order Summary again.
  - Do NOT call the tool with `confirmed=False` once they say CONFIRM.

FORBIDDEN PATTERNS (NEVER DO THESE):
  ❌ Calling create_purchase_request BEFORE asking about a coupon
  ❌ Skipping the coupon question for any reason
  ❌ Assuming the customer doesn't have a coupon without asking
  ❌ Going straight to CONFIRM step without showing the summary first

Rules:
- If the customer is a guest (unauthenticated), you MUST collect their email address along with the other details.
- Triggering create_purchase_request with confirmed=True will automatically generate a 6-digit OTP code, email it, and prompt: "I have sent a verification code to your email. Please reply with the code to confirm your order." (or its Arabic translation).
- If the user types their 6-digit OTP, the backend will immediately intercept it, verify, and complete their order. Do NOT trigger tools for the OTP entry.
- If anything is unclear → show the 3 options again.
- "no" + confirm word → apply RULE 4 → place immediately.
- This step can NEVER be skipped, even if the customer seems very sure.

---

You are Layla 💎, the AI shopping assistant for ORYA Luxury Jewelry, a premium jewelry brand based in Jordan.

---

YOUR ONLY SOURCE OF TRUTH

<PRODUCT_CONTEXT>
{{context}}
</PRODUCT_CONTEXT>

Rules you must never break:
- Answer product questions ONLY using information inside PRODUCT_CONTEXT.
- If PRODUCT_CONTEXT is empty or has no match, say:
  "I could not find an exact match. Could you describe what you are looking for? (e.g., material, category, budget)"
- NEVER invent product names, prices, or details not in PRODUCT_CONTEXT.
- Do NOT browse the internet or use any external tool to find products.

---

HOW TO PRESENT PRODUCTS

When a product is found, show:
1. Name (in the customer language per RULE 1)
2. Price (show sale price with strikethrough if on sale)
3. Delivery: Mention the active delivery rule/fee (specify that it is for the ENTIRE order, and if free shipping is active or available, highlight it)
4. Material (Gold / Silver / Gold-Plated)
5. Category
6. End with: "Would you like to order this? 🛍️"

---

ORDER FLOW

STEP 1: Classify intent (RULE 5)
STEP 2: Check saved info (RULE 3), collect missing details in ONE message
STEP 3: Show ORDER SUMMARY with delivery fee (RULE 6 + RULE 7)
STEP 4: Wait for CONFIRM. Apply RULE 4 for ambiguous replies. Use RULE 2 format on success.

---

EDGE CASES

- Product not in context: Ask for category / budget / material
- Customer asks for discount: "Our prices are already competitive ✨"
- Customer asks about stock: Only mention if stated in context
- General jewelry care: Answer from general knowledge only
- Customer changes mind mid-order: Go back to Step 1 with the new product

---

═══════════════════════════════════════
RULE 8 — NEVER DENY A PRODUCT SHOWN IN THIS CONVERSATION
═══════════════════════════════════════
This is a CRITICAL rule — violation destroys customer trust.

- Before every reply, scan the current conversation history.
- If a product was already shown or added to an ORDER SUMMARY in THIS conversation → it EXISTS.
- You are FORBIDDEN from saying "I couldn't find", "this product doesn't exist", or any denial
  for a product already mentioned in the conversation.
- If the customer says CONFIRM and a product was in the summary → confirm the order immediately.
  Do NOT re-search RAG.
- Re-searching RAG only happens when the customer asks about a NEW product not yet discussed.

BAD (FORBIDDEN):
→ Bot shows "Shiny Silver Ring" in summary
→ Customer says CONFIRM
→ Bot says "Sorry, I couldn't find Shiny Silver Ring" ← NEVER DO THIS

CORRECT:
→ Bot shows "Shiny Silver Ring" in summary
→ Customer says CONFIRM
→ Bot confirms the order immediately ✅

═══════════════════════════════════════
RULE 9 — SALE PRICE FORMAT IN ORDER SUMMARY
═══════════════════════════════════════
When a product HAS a sale price, show both the original and sale prices for that product:
- Luxury Diamond Ring (x1) : ~~250.00 JOD~~ 210.00 JOD 🏷️

When displaying the final ORDER SUMMARY:
- Lists all products with their quantities and prices (displaying both original and sale price if applicable).
- Subtotal: [Sum of all items prices] JOD
- Coupon Discount (if applied): -[Discount Amount] JOD
- Delivery Fee: [Dynamic Delivery Fee from the tool, e.g. 0.00 JOD or 3.00 JOD]
- Total Amount: [Subtotal - Coupon Discount + Delivery Fee] JOD
- Name: [Customer Name]
- Phone: [Phone Number]
- Address: [City, Full Address]

═══════════════════════════════════════
RULE 10 — CATEGORY SEARCH: SHOW ALL RESULTS
═══════════════════════════════════════
When a customer asks about a CATEGORY (rings, necklaces, bracelets, etc.):
- Do NOT say "I couldn't find an exact match" — this is a browse request.
- Show ALL products found in PRODUCT_CONTEXT for that category.
- Use this format:

  Here's our [category] collection ✨

  1. [Name EN] / [Name AR]
     - Price: [X] JOD  (or: ~~X JOD~~ → Sale: Y JOD 🏷️)
     - Material: [material]
     - 🔗 [View Product](/product/[PRODUCT_ID])

  2. [Name EN] / [Name AR]
     - Price: [X] JOD
     - Material: [material]
     - 🔗 [View Product](/product/[PRODUCT_ID])

  [...all products found...]

  Which one catches your eye? 💎

CRITICAL: Always include the 🔗 [View Product](/product/[PRODUCT_ID]) line for EVERY product.
Replace [PRODUCT_ID] with the actual numeric ID from PRODUCT_CONTEXT (e.g. PRODUCT ID: 42 → /product/42).
- If context has fewer products than expected, add:
  "These are the top matches. Would you like to filter by material or price range?"


═══════════════════════════════════════
RULE 11 — ORDER STATE LOCK (NO RE-SEARCH AFTER SUMMARY)
═══════════════════════════════════════
Once an ORDER SUMMARY has been shown in the conversation:
- The product details are LOCKED from that summary.
- Do NOT call the search tool again for the same product.
- Continue the order flow using the exact details already in the summary.
- Only re-search if the customer explicitly asks to CHANGE the product.

═══════════════════════════════════════
RULE 12 — MULTIPLE PRODUCTS IN A SINGLE ORDER
═══════════════════════════════════════
If the customer wants to buy multiple products (e.g. "I want to order Trendy Gold-Plated Ring and Luxury Diamond Ring"):
- You MUST pass the complete list of items in the "items" parameter of the `create_purchase_request` tool instead of the single "product_name" parameter.
- The "items" list format MUST be a list of dictionaries, where each dictionary contains:
  `{{"product_name": "Product A", "quantity": X}}`
- In the final Order Summary, list all products and their quantities clearly.
- Do NOT make separate tool calls for each product. Combine them into one single call to `create_purchase_request` with the "items" parameter.

---

TONE

- Warm, elegant, and helpful like a personal jeweler.
- Never pushy. Never repeat confirmation questions unnecessarily.
- Use tasteful emojis sparingly: 💎 🏷️ ✨ 🛍️ ✅

"""


# ── History Route ────────────────────────────────────────────────
@chatbot_bp.route('/api/chatbot/history', methods=['GET'])
def chatbot_history():
    session_id = request.args.get('session_id')
    user_id = request.args.get('user_id')
    if not session_id:
        return jsonify({'success': False, 'message': 'No session ID provided'})
        
    if user_id and user_id.strip():
        # Respect session_id even for logged-in users to allow "Clear Chat" to work
        logs = ChatbotLog.query.filter_by(session_id=session_id, user_id=user_id).order_by(ChatbotLog.created_at.asc()).all()
    else:
        logs = ChatbotLog.query.filter_by(session_id=session_id, user_id=None).order_by(ChatbotLog.created_at.asc()).all()
    
    history = []
    for log in logs:
        history.append({
            'sender': 'user',
            'text': log.user_message,
            'created_at': log.created_at.isoformat()
        })
        history.append({
            'sender': 'bot',
            'text': log.bot_reply,
            'created_at': log.created_at.isoformat()
        })
        
    return jsonify({'success': True, 'history': history})


def get_delivery_info_message(lang='ar'):
    """
    Get a dynamic message describing active delivery rules and fee.
    """
    from app.models import SiteSetting
    try:
        rule_setting = SiteSetting.query.filter_by(key='free_delivery_rule').first()
        rule = rule_setting.value_en.strip().lower() if rule_setting and rule_setting.value_en else 'disabled'
        
        fee_setting = SiteSetting.query.filter_by(key='delivery_fee_jod').first()
        fee = float(fee_setting.value_en) if fee_setting and fee_setting.value_en else 3.0
        
        if rule == 'always':
            return (
                "التوصيل مجاني لجميع الطلبات! 🚚"
                if lang == 'ar' else
                "Delivery is FREE for all orders! 🚚"
            )
        elif rule == 'min_amount':
            amount_setting = SiteSetting.query.filter_by(key='free_delivery_min_amount').first()
            min_amount = float(amount_setting.value_en) if amount_setting and amount_setting.value_en else 0.0
            if min_amount > 0:
                return (
                    f"رسوم التوصيل {fee:.2f} JOD للطلب كامل، ومجاني للطلبات بقيمة {min_amount:.2f} JOD أو أكثر! 🚚"
                    if lang == 'ar' else
                    f"Delivery fee is {fee:.2f} JOD for the entire order, and FREE for orders of {min_amount:.2f} JOD or more! 🚚"
                )
        elif rule == 'min_quantity':
            qty_setting = SiteSetting.query.filter_by(key='free_delivery_min_quantity').first()
            min_qty = int(qty_setting.value_en) if qty_setting and qty_setting.value_en else 2
            return (
                f"رسوم التوصيل {fee:.2f} JOD للطلب كامل، ومجاني عند شراء {min_qty} قطع أو أكثر! 🚚"
                if lang == 'ar' else
                f"Delivery fee is {fee:.2f} JOD for the entire order, and FREE for {min_qty} or more items! 🚚"
            )
            
        return (
            f"رسوم التوصيل {fee:.2f} JOD للطلب كامل! 🚚"
            if lang == 'ar' else
            f"Delivery fee is {fee:.2f} JOD for the entire order! 🚚"
        )
    except Exception as e:
        print(f"[get_delivery_info_message Error] {e}")
        return (
            "رسوم التوصيل 3 JOD للطلب كامل! 🚚"
            if lang == 'ar' else
            "Delivery fee is 3 JOD for the entire order! 🚚"
        )


def get_promo_info_message(lang='ar'):
    """
    Get a dynamic message listing active coupons and announcements.
    """
    from app.models import Coupon, Announcement
    try:
        coupons = Coupon.query.filter_by(is_active=True).all()
        ann = Announcement.query.filter_by(is_active=True).first()
        
        parts_ar = []
        parts_en = []
        
        if ann:
            parts_ar.append(ann.text_ar)
            parts_en.append(ann.text_en)
            
        for c in coupons:
            sym = "%" if c.type == 'percentage' else "JOD"
            min_order_msg_ar = f" (للطلبات فوق {c.min_order_jod:.2f} JOD)" if c.min_order_jod and float(c.min_order_jod) > 0 else ""
            min_order_msg_en = f" (for orders over {c.min_order_jod:.2f} JOD)" if c.min_order_jod and float(c.min_order_jod) > 0 else ""
            
            parts_ar.append(f"🏷️ كوبون {c.code}: خصم {c.value} {sym}{min_order_msg_ar}")
            parts_en.append(f"🏷️ Coupon {c.code}: {c.value}" + ("% off" if c.type == 'percentage' else " JOD off") + min_order_msg_en)
            
        if not parts_ar:
            return "لا توجد عروض أو كوبونات نشطة حالياً 🌸" if lang == 'ar' else "No active promotions or coupons currently 🌸"
            
        return "\n".join(parts_ar) if lang == 'ar' else "\n".join(parts_en)
    except Exception as e:
        print(f"[get_promo_info_message Error] {e}")
        return ""


# ── Main Route ─────────────────────────────────────────────────
@chatbot_bp.route('/api/chatbot/message', methods=['POST'])
def chatbot_message():
    data       = request.get_json()
    message    = data.get('message', '').strip()
    user_id    = data.get('user_id')
    session_id = data.get('session_id', 'anonymous')
    lang       = data.get('lang', session.get('lang', 'ar'))
    session['lang'] = lang

    if not message:
        return jsonify({'success': False, 'message': 'رسالة فارغة'}), 400

    # ── OTP Message Interceptor ──────────────────────────────────
    import re
    import time
    import random
    import string
    import datetime
    from app.models import Order, OrderItem, Product, Notification
    from flask_mail import Message
    from app import mail

    pending_order = session.get('chatbot_pending_order')
    if pending_order:
        # Check if user message is exactly a 6-digit OTP code (digits only)
        clean_msg = message.replace(' ', '').replace('-', '').strip()
        if re.match(r'^\d{6}$', clean_msg):
            # Check expiry (5 minutes = 300 seconds)
            elapsed = time.time() - pending_order['timestamp']
            if elapsed > 300:
                session.pop('chatbot_pending_order', None)
                reply_text = (
                    'انتهت صلاحية رمز التحقق. يرجى إرسال طلبكِ مجدداً لتلقي رمز جديد 🌸'
                    if lang == 'ar' else
                    'The verification code has expired. Please place your order again to receive a new code 🌸'
                )
                try:
                    log = ChatbotLog(
                        user_id      = user_id,
                        session_id   = session_id,
                        user_message = message,
                        bot_reply    = reply_text,
                        lang         = lang
                    )
                    db.session.add(log)
                    db.session.commit()
                except Exception as ex:
                    print(f'[Chatbot Log Error] {ex}')

                return jsonify({
                    'success': True,
                    'data': {
                        'reply': reply_text,
                        'action': None,
                        'data': None
                    }
                })

            # Check if correct code
            if clean_msg == pending_order['otp']:
                try:
                    # Order ID will be generated from database ID after flush
                    order_id_str = ""

                    # Determine items list
                    pending_items = pending_order.get('items')
                    if not pending_items:
                        # Fallback for single item from older session format or older code
                        pending_items = [{
                            'product_id': pending_order['product_id'],
                            'product_name': pending_order['product_name'],
                            'quantity': pending_order['quantity'],
                            'unit_price': pending_order['subtotal'] / pending_order['quantity'] if pending_order['quantity'] else 0.0
                        }]

                    # Verify product and decrement stock for ALL items first
                    order_items_to_create = []
                    for pi in pending_items:
                        prod = Product.query.get(pi['product_id'])
                        if not prod:
                            session.pop('chatbot_pending_order', None)
                            reply_text = (
                                'عذراً، لم نعد نجد هذا المنتج في نظامنا. 🌸'
                                if lang == 'ar' else
                                'Sorry, we could not find this product in our system. 🌸'
                            )
                            return jsonify({'success': True, 'data': {'reply': reply_text, 'action': None, 'data': None}})
                        
                        qty = pi['quantity']
                        if prod.stock_qty is not None and prod.stock_qty >= qty:
                            prod.stock_qty -= qty
                        else:
                            session.pop('chatbot_pending_order', None)
                            reply_text = (
                                f"عذراً، لم يتبقَ مخزون كافٍ من {prod.name_ar} لإتمام طلبكِ. 🌸"
                                if lang == 'ar' else
                                f"Sorry, there is not enough stock of {prod.name_en} left to fulfill your order. 🌸"
                            )
                            return jsonify({'success': True, 'data': {'reply': reply_text, 'action': None, 'data': None}})
                        
                        order_items_to_create.append((prod, qty, pi['unit_price']))

                    # Dynamic guest account lookup/creation to avoid nullable foreign key violation
                    order_user_id = None
                    if current_user.is_authenticated:
                        order_user_id = current_user.id
                    else:
                        from app.models import User
                        existing_user = User.query.filter(
                            (User.email == pending_order['email']) | (User.phone == pending_order['phone'])
                        ).first()
                        if existing_user:
                            order_user_id = existing_user.id
                        else:
                            from app import bcrypt
                            temp_pw = "".join([random.choice(string.ascii_letters + string.digits) for _ in range(12)])
                            hashed = bcrypt.generate_password_hash(temp_pw).decode('utf-8')
                            guest_username = f"guest_{pending_order['phone']}"
                            guest_user = User(
                                username=guest_username,
                                email=pending_order['email'],
                                full_name=pending_order['full_name'],
                                phone=pending_order['phone'],
                                password_hash=hashed
                            )
                            db.session.add(guest_user)
                            db.session.flush()
                            order_user_id = guest_user.id

                    # Create DB Order
                    new_order = Order(
                        user_id=order_user_id,
                        status='pending',
                        subtotal_jod=pending_order['subtotal'],
                        discount_jod=pending_order['discount'],
                        coupon_code=pending_order['coupon_code'] if pending_order['discount'] > 0 else None,
                        delivery_fee_jod=pending_order['delivery_fee'],
                        total_jod=pending_order['total'],
                        full_name=pending_order['full_name'],
                        phone=pending_order['phone'],
                        city=pending_order['city'],
                        area='-',
                        address=pending_order['address'],
                        payment_method='cash_on_delivery',
                        notes=""
                    )
                    db.session.add(new_order)
                    db.session.flush()

                    order_id_str = f"ORY-{new_order.id}"
                    new_order.notes = f"Chatbot verified order ID: {order_id_str}"

                    # Create Order Items
                    for prod, qty, unit_price in order_items_to_create:
                        item = OrderItem(
                            order_id=new_order.id,
                            product_id=prod.id,
                            quantity=qty,
                            unit_price_jod=unit_price
                        )
                        db.session.add(item)

                    # List products for notification and email
                    products_str_ar = ", ".join([f"{prod.name_ar} (x{qty})" for prod, qty, _ in order_items_to_create])
                    products_str_en = ", ".join([f"{prod.name_en} (x{qty})" for prod, qty, _ in order_items_to_create])

                    # Notify Admin
                    notif = Notification(
                        type='order',
                        message=f"طلب جديد في انتظار تأكيد المشرف #{order_id_str}: {products_str_ar}",
                        link=f"/admin/orders/{new_order.id}",
                        is_read=False
                    )
                    db.session.add(notif)
                    db.session.commit()

                    # Send Confirmation Email to Customer
                    recipient_email = pending_order.get('email')
                    if recipient_email:
                        try:
                            msg = Message(f"ORYA - Order Confirmed! #{order_id_str}", recipients=[recipient_email])
                            msg.body = (
                                f"Dear {pending_order['full_name']},\n\n"
                                f"Thank you for shopping at ORYA Luxury Jewelry! 💎\n"
                                f"Your order has been verified and confirmed.\n\n"
                                f"Order Summary:\n"
                                f"----------------------------------------\n"
                                f"Order ID : {order_id_str}\n"
                                f"Products : {products_str_en}\n"
                                f"Price    : {pending_order['subtotal']:.2f} JOD\n"
                                f"Delivery : {pending_order['delivery_fee']:.2f} JOD\n"
                                f"Total    : {pending_order['total']:.2f} JOD\n"
                                f"Phone    : {pending_order['phone']}\n"
                                f"Address  : {pending_order['city']}, {pending_order['address']}\n"
                                f"----------------------------------------\n\n"
                                f"We will contact you soon to arrange delivery.\n\n"
                                f"Best regards,\nORYA Luxury Jewelry Store"
                            )
                            mail.send(msg)
                        except Exception as email_err:
                            print(f"[SMTP Confirm Email Error] {email_err}")

                    # Clear chatbot pending order
                    session.pop('chatbot_pending_order', None)

                    # Build bilingual response
                    if lang == 'ar':
                        reply_text = (
                            f"شكراً لكِ! تم استلام طلبك وهو الآن بانتظار موافقة المشرف. 🌸\n\n"
                            f"✅ طلبك في الانتظار للمراجعة.\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"رقم الطلب : {order_id_str}\n"
                            f"المنتجات  : {products_str_ar}\n"
                            f"السعر    : {pending_order['subtotal']:.2f} JOD\n"
                            f"التوصيل  : {pending_order['delivery_fee']:.2f} JOD\n"
                            f"المجموع  : {pending_order['total']:.2f} JOD\n"
                            f"الهاتف    : {pending_order['phone']}\n"
                            f"العنوان  : {pending_order['city']}, {pending_order['address']}\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"سنتصل بكِ قريباً لترتيب التوصيل. شكراً لاختياركِ أوريا للمجوهرات الفاخرة! 💎"
                        )
                    else:
                        reply_text = (
                            f"Thank you! Your order has been received and is pending admin approval. 🌸\n\n"
                            f"✅ Order pending admin review.\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"Order ID : {order_id_str}\n"
                            f"Products : {products_str_en}\n"
                            f"Price    : {pending_order['subtotal']:.2f} JOD\n"
                            f"Delivery : {pending_order['delivery_fee']:.2f} JOD\n"
                            f"Total    : {pending_order['total']:.2f} JOD\n"
                            f"Phone    : {pending_order['phone']}\n"
                            f"Address  : {pending_order['city']}, {pending_order['address']}\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"We'll contact you soon to arrange delivery. Thank you for choosing ORYA Luxury Jewelry! 💎"
                        )

                    # Log to DB
                    try:
                        log = ChatbotLog(
                            user_id      = user_id,
                            session_id   = session_id,
                            user_message = message,
                            bot_reply    = reply_text,
                            lang         = lang
                        )
                        db.session.add(log)
                        db.session.commit()
                    except Exception as ex:
                        print(f'[Chatbot Log Error] {ex}')

                    return jsonify({
                        'success': True,
                        'data': {
                            'reply': reply_text,
                            'action': None,
                            'data': None
                        }
                    })

                except Exception as db_err:
                    db.session.rollback()
                    print(f"[Chatbot OTP DB Create Error] {db_err}")
                    reply_text = (
                        'عذراً، حدث خطأ أثناء تأكيد الطلب في قاعدة البيانات. يرجى المحاولة مجدداً 🌸'
                        if lang == 'ar' else
                        'Sorry, an error occurred while confirming the order in the database. Please try again 🌸'
                    )
                    return jsonify({'success': True, 'data': {'reply': reply_text, 'action': None, 'data': None}})

            else:
                # Incorrect OTP code
                reply_text = (
                    'رمز التحقق غير صحيح. يرجى إعادة إدخال الرمز المكون من 6 أرقام المرسل لبريدك الإلكتروني، أو كتابة "تغيير" لتعديل الطلب 🌸'
                    if lang == 'ar' else
                    'Incorrect verification code. Please enter the 6-digit code sent to your email, or reply "change" to edit your order details 🌸'
                )
                try:
                    log = ChatbotLog(
                        user_id      = user_id,
                        session_id   = session_id,
                        user_message = message,
                        bot_reply    = reply_text,
                        lang         = lang
                    )
                    db.session.add(log)
                    db.session.commit()
                except Exception as ex:
                    print(f'[Chatbot Log Error] {ex}')

                return jsonify({
                    'success': True,
                    'data': {
                        'reply': reply_text,
                        'action': None,
                        'data': None
                    }
                })

    action      = None
    action_data = None
    reply_text  = ""

    try:
        is_static = is_static_question(message)
        
        if is_static:
            # ── RAG path ───────────────────────────────────────
            context = query_rag(message)

            if context:
                rag_prompt = f"""
You are the ORYA assistant. Answer the customer's question based ONLY on the information provided below.

Information available:
{context}

Customer's question: {message}

Answer briefly and clearly in {'Arabic' if lang == 'ar' else 'English'}.
"""
                response   = llm.invoke(rag_prompt)
                reply_text = response.content
            else:
                reply_text = (
                    'عذراً، لم أجد معلومات كافية. يرجى التواصل معنا مباشرة 🌸'
                    if lang == 'ar' else
                    'Sorry, I could not find enough information. Please contact us directly 🌸'
                )

        else:
            # ── Agent path ─────────────────────────────────────
            # Inject RAG context into the system prompt (fills {{context}} placeholder)
            rag_context = query_rag(message)
            # Must escape curly braces because LangChain treats them as prompt variables
            rag_context_safe = (rag_context or 'No product context found.').replace('{', '{{').replace('}', '}}')
            # Format custom language lock in Rule 1 dynamically
            rule_1_locked = f"""═══════════════════════════════════════
RULE 1 — LANGUAGE (NON-NEGOTIABLE)
═══════════════════════════════════════
- The user is conversing with you in: {"ARABIC" if lang == "ar" else "ENGLISH"}.
- You MUST reply ONLY and completely in {"Arabic (العربية)" if lang == "ar" else "English"}.
- NEVER translate to or write in the other language.
- Ensure all summaries, prices, names, and general conversations are strictly in {"Arabic" if lang == "ar" else "English"}."""

            promo_info_str = get_promo_info_message(lang)
            delivery_info_str = get_delivery_info_message(lang)
            # Must escape curly braces because LangChain treats them as prompt variables
            promo_info_safe = promo_info_str.replace('{', '{{').replace('}', '}}')
            delivery_info_safe = delivery_info_str.replace('{', '{{').replace('}', '}}')

            system_prompt_with_context = SYSTEM_PROMPT.replace('{{context}}', rag_context_safe)
            system_prompt_with_context = system_prompt_with_context.replace('{{promo_info}}', promo_info_safe)
            system_prompt_with_context = system_prompt_with_context.replace('{{delivery_info}}', delivery_info_safe)
            # Locate the original Rule 1 text and replace it with rule_1_locked
            system_prompt_with_context = system_prompt_with_context.replace("""═══════════════════════════════════════
RULE 1 — LANGUAGE (NON-NEGOTIABLE)
═══════════════════════════════════════
- Read the customer's FIRST message.
- Identify the language: English or Arabic.
- Reply in that SAME language for the ENTIRE conversation.
- This rule overrides EVERYTHING — product names, context data, prior conversations.
- If the customer's first message is in English → EVERY reply must be in English.
- If the customer's first message is in Arabic → EVERY reply must be in Arabic.
- NEVER mix languages in a single reply.
- FORBIDDEN: Customer writes in English → you reply in Arabic.""", rule_1_locked)

            memory = get_memory(session_id)
            agent  = initialize_agent(
                tools        = TOOLS,
                llm          = llm,
                agent        = AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
                memory       = memory,
                verbose      = False,
                agent_kwargs = {'system_message': system_prompt_with_context},
                handle_parsing_errors = True
            )
            # Inject user context if logged in
            user_context = ""
            if user_id:
                from app.models import User
                user = User.query.get(user_id)
                if user:
                    user_context = f" [Context: User is {user.full_name}, Phone: {user.phone}, ID: {user.id}]"
            
            raw_reply  = agent.run(input=message + user_context)

            # Check if tool returned a JSON
            try:
                parsed = json.loads(raw_reply)
                if parsed.get('action') == 'human_handoff':
                    action      = 'human_handoff'
                    action_data = {
                        'whatsapp': parsed.get('whatsapp', '')
                    }
                    reply_text = (
                        parsed.get('message_ar')
                        if lang == 'ar'
                        else parsed.get('message_en')
                    )
                elif parsed.get('status') == 'success' and parsed.get('confirmation_ar'):
                    # request_return success
                    reply_text = (
                        parsed.get('confirmation_ar')
                        if lang == 'ar'
                        else parsed.get('confirmation_en')
                    )
                elif parsed.get('status') in ('need_info', 'out_of_stock', 'insufficient_stock'):
                    reply_text = (
                        parsed.get('message_ar')
                        if lang == 'ar'
                        else parsed.get('message_en')
                    )
                elif parsed.get('status') == 'awaiting_confirmation':
                    reply_text = (
                        parsed.get('summary_ar')
                        if lang == 'ar'
                        else parsed.get('summary_en')
                    )
                elif parsed.get('status') == 'not_found' and parsed.get('message_ar'):
                    reply_text = (
                        parsed.get('message_ar')
                        if lang == 'ar'
                        else parsed.get('message_en')
                    )
                elif parsed.get('action') == 'show_products':
                    action      = 'show_products'
                    action_data = parsed.get('data', [])
                    reply_text  = (
                        'إليكِ ما وجدته ✅ 🌸'
                        if lang == 'ar'
                        else 'Here is what I found ✅ 🌸'
                    )
                else:
                    reply_text = raw_reply
            except (json.JSONDecodeError, AttributeError):
                reply_text = raw_reply

    except Exception as e:
        import traceback
        from datetime import datetime
        with open('error_log.txt', 'a', encoding='utf-8') as f:
            f.write(f"\n--- Error at {datetime.now()} ---\n")
            f.write(traceback.format_exc())
            f.write(f"Error Message: {str(e)}\n")
        reply_text = (
            'حدث خطأ مؤقت، يرجى المحاولة مجدداً 🌸'
            if lang == 'ar' else
            'Temporary error, please try again 🌸'
        )

    # ── Log to DB ──────────────────────────────────────────────
    try:
        log = ChatbotLog(
            user_id      = user_id,
            session_id   = session_id,
            user_message = message,
            bot_reply    = reply_text,
            lang         = lang
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f'[Chatbot Log Error] {e}')

    return jsonify({
        'success': True,
        'data': {
            'reply':  reply_text,
            'action': action,
            'data':   action_data
        }
    })


# ── Ticket Route (from UI form) ────────────────────────────────
@chatbot_bp.route('/api/chatbot/ticket', methods=['POST'])
def create_ticket():
    """
    Called when user chooses 'leave a message' in human_handoff.
    Creates SupportTicket + admin Notification.
    """
    data        = request.get_json()
    description = data.get('description', '').strip()
    user_id     = data.get('user_id')
    session_id  = data.get('session_id', 'anonymous')
    lang        = data.get('lang', 'ar')

    if not description:
        msg = 'الرسالة فارغة' if lang == 'ar' else 'Message cannot be empty'
        return jsonify({'success': False, 'message': msg}), 400

    try:
        # Create Support Ticket
        ticket = SupportTicket(
            user_id     = user_id,
            session_id  = session_id,
            description = description,
            status      = 'open'
        )
        db.session.add(ticket)
        db.session.flush()

        # Create Admin Notification (always stored in Arabic for admin panel)
        notif = Notification(
            type    = 'support_ticket',
            message = f'رسالة دعم جديدة من العميل (تذكرة #{ticket.id}): {description[:100]}',
            link    = f'/admin/chatbot?session={session_id}',
            is_read = False
        )
        db.session.add(notif)
        db.session.commit()

        success_msg = (
            'تم استلام رسالتك، سنتواصل معك قريباً 🌸'
            if lang == 'ar' else
            'Your message has been received. We will contact you shortly 🌸'
        )
        return jsonify({'success': True, 'message': success_msg})

    except Exception as e:
        print(f'[Ticket Error] {e}')
        err_msg = 'حدث خطأ' if lang == 'ar' else 'An error occurred. Please try again.'
        return jsonify({'success': False, 'message': err_msg}), 500
