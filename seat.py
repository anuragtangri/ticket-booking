import threading
import json
from payment import payment_system

class TicketBooking:
    def __init__(self):
        # Use consistent dimensions - 10 rows x 5 columns
        self.seat_matrix = [[None] * 5 for _ in range(10)]
        self.lock = threading.Lock()

    def reserve_seat(self, name, date):
        """Reserve a seat and create payment session"""
        if not name or not date:
            return {"error": "Missing name or date"}, 400

        with self.lock:
            for i in range(len(self.seat_matrix)):
                for j in range(len(self.seat_matrix[i])):
                    if self.seat_matrix[i][j] is None:
                        # Create payment session
                        seat_info = {"row": i, "col": j}
                        session_id, payment_data = payment_system.create_payment_session(
                            seat_info, name, date
                        )
                        
                        # Temporarily reserve the seat
                        self.seat_matrix[i][j] = {
                            "name": name, 
                            "date": date, 
                            "session_id": session_id,
                            "status": "reserved"
                        }
                        
                        return {
                            "success": True,
                            "message": f"Seat reserved at ({i},{j}) for {name}. Please complete payment.",
                            "session_id": session_id,
                            "payment_url": f"/payment/{session_id}",
                            "seat": {"row": i, "col": j, "data": self.seat_matrix[i][j]}
                        }, 200
        
        return {"success": False, "message": "No seats available"}, 200

    def confirm_booking(self, session_id):
        """Confirm booking after successful payment"""
        with self.lock:
            # Find the seat with this session ID
            for i in range(len(self.seat_matrix)):
                for j in range(len(self.seat_matrix[i])):
                    seat = self.seat_matrix[i][j]
                    if seat and seat.get('session_id') == session_id:
                        # Check if payment is completed
                        payment_success, payment_data = payment_system.check_payment_status(session_id)
                        
                        if payment_success:
                            # Mark seat as confirmed
                            seat['status'] = 'confirmed'
                            seat['payment_method'] = payment_data.get('payment_method', 'unknown')
                            seat['payment_completed_at'] = payment_data.get('completed_at')
                            
                            return {
                                "success": True,
                                "message": f"Booking confirmed for seat at ({i},{j})",
                                "seat": {"row": i, "col": j, "data": seat}
                            }, 200
                        else:
                            return {
                                "success": False,
                                "message": "Payment not completed"
                            }, 400
            
            return {
                "success": False,
                "message": "Session not found"
            }, 404

    def book(self, name, date):
        """Legacy booking method - now redirects to reservation"""
        return self.reserve_seat(name, date)

    def show(self):
        """Return current seat matrix"""
        with self.lock:
            # Return a deep copy to prevent external modification
            return [row[:] for row in self.seat_matrix]
    
    def reset(self):
        """Reset all seats to empty"""
        with self.lock:
            # Keep consistent dimensions: 10x5
            self.seat_matrix = [[None] * 5 for _ in range(10)]
        return {"message": "All seats have been reset."}, 200

    def get_available_count(self):
        """Get count of available seats"""
        with self.lock:
            count = 0
            for row in self.seat_matrix:
                for seat in row:
                    if seat is None:
                        count += 1
            return count

    def get_booked_count(self):
        """Get count of booked seats"""
        with self.lock:
            count = 0
            for row in self.seat_matrix:
                for seat in row:
                    if seat is not None:
                        count += 1
            return count