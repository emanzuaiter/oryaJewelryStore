import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_order_confirmation(order, lang='ar'):
    """Sends order confirmation email to the customer."""
    logger.info(f"Sending order confirmation to {order.full_name} ({order.user.email}) for Order #{order.id}")
    # In a real app, you'd use Flask-Mail or an API like SendGrid here.
    pass

def send_admin_new_order(order):
    """Notifies admins about a new order."""
    logger.info(f"Notifying admin about new Order #{order.id} from {order.full_name}")
    pass

def send_order_cancellation(order, lang='ar'):
    """Sends order cancellation email to the customer."""
    logger.info(f"Sending cancellation notice to {order.full_name} for Order #{order.id}")
    pass

def send_admin_cancellation(order):
    """Notifies admins about an order cancellation."""
    logger.info(f"Notifying admin about cancellation of Order #{order.id}")
    pass

def send_admin_contact_message(name, phone, message):
    """Notifies admins about a new contact form submission."""
    logger.info(f"New contact message from {name} ({phone}): {message[:50]}...")
    pass
