def is_valid_transition(current_status, new_status):
    """Validate allowed status transitions.
    Sequence: pending_verification -> pending -> confirmed -> processing -> delivered.
    Cancellation allowed from pending_verification or pending.
    """
    allowed = {
        'pending_verification': ['pending', 'cancelled'],
        'pending': ['confirmed', 'processing', 'cancelled'],
        'confirmed': ['processing'],
        'processing': ['delivered'],
        'delivered': [],
        'cancelled': []
    }
    return new_status in allowed.get(current_status, [])

def can_cancel(current_status):
    """Return True if order can be cancelled from current status."""
    return current_status in ['pending_verification', 'pending']
