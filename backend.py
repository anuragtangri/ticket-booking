from flask import Flask, jsonify, request, send_from_directory
import threading
import os

app = Flask(__name__)

# ... (your existing TicketBooking class remains unchanged) ...
class TicketBooking:
    def __init__(self):
        # The seat matrix will now store booking details
        self.seat_matrix = [[None] * 50 for _ in range(50)]
        self.lock = threading.Lock()

    def book(self):
        # Get the JSON data from the POST request
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()
        name = data.get('name')
        date = data.get('date')
        
        if not name or not date:
            return jsonify({"error": "Missing name or date"}), 400

        with self.lock:
            for i in range(len(self.seat_matrix)):
                for j in range(len(self.seat_matrix[i])):
                    if self.seat_matrix[i][j] is None:
                        # Store the booking data directly in the matrix
                        self.seat_matrix[i][j] = {"name": name, "date": date}
                        return jsonify({"message": f"Seat booked at ({i},{j}) for {name}"})
        
        return jsonify({"message": "No seats available"})

    def show(self):
        # Return seat matrix as JSON
        return jsonify(self.seat_matrix)

handler = TicketBooking()

# ... (your existing route definitions) ...
app.add_url_rule('/booking', view_func=handler.book, methods=['POST'])
app.add_url_rule('/booking/show', view_func=handler.show, methods=['GET'])

# NEW: Add a route to serve the HTML file from the root URL
@app.route('/')
def serve_index():
    # Make sure your HTML file is in the same directory as backend.py
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'index.html')

if __name__ == '__main__':
    app.run(debug=True)