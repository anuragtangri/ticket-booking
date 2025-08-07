import uuid
import time
from datetime import datetime, timedelta

class Payment:
    def __init__(self):
        # Store pending payments with session IDs
        self.pending_payments = {}
        self.completed_payments = {}
        self.payment_sessions = {}
        
    def create_payment_session(self, seat_info, user_name, date):
        """Create a new payment session for a seat booking"""
        session_id = str(uuid.uuid4())
        payment_data = {
            'session_id': session_id,
            'seat_info': seat_info,
            'user_name': user_name,
            'date': date,
            'amount': 25.00,  # Fixed ticket price
            'created_at': datetime.now(),
            'expires_at': datetime.now() + timedelta(minutes=15),  # 15 minute expiry
            'status': 'pending'
        }
        
        self.payment_sessions[session_id] = payment_data
        return session_id, payment_data
    
    def get_payment_session(self, session_id):
        """Get payment session by ID"""
        return self.payment_sessions.get(session_id)
    
    def process_payment(self, session_id, payment_method="card"):
        """Process payment for a session"""
        if session_id not in self.payment_sessions:
            return False, "Invalid session ID"
        
        session = self.payment_sessions[session_id]
        
        # Check if session has expired
        if datetime.now() > session['expires_at']:
            return False, "Payment session expired"
        
        # Simulate payment processing
        if payment_method in ["card", "paypal", "wallet"]:
            # Mark payment as completed
            session['status'] = 'completed'
            session['payment_method'] = payment_method
            session['completed_at'] = datetime.now()
            
            # Move to completed payments
            self.completed_payments[session_id] = session
            
            return True, "Payment successful"
        else:
            return False, "Invalid payment method"
    
    def check_payment_status(self, session_id):
        """Check if payment is completed for a session"""
        if session_id in self.completed_payments:
            return True, self.completed_payments[session_id]
        elif session_id in self.payment_sessions:
            session = self.payment_sessions[session_id]
            if session['status'] == 'completed':
                return True, session
            else:
                return False, session
        else:
            return False, None
    
    def cancel_payment_session(self, session_id):
        """Cancel a payment session"""
        if session_id in self.payment_sessions:
            del self.payment_sessions[session_id]
            return True
        return False
    
    def cleanup_expired_sessions(self):
        """Remove expired payment sessions"""
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.payment_sessions.items():
            if current_time > session['expires_at']:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.payment_sessions[session_id]
        
        return len(expired_sessions)

# Global payment instance
payment_system = Payment()