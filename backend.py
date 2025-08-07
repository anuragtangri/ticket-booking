from flask import Flask, jsonify, request, send_from_directory, Response
import threading
import os
import json
import time
from queue import Queue

app = Flask(__name__)
booking_events = Queue()

class TicketBooking:
    def __init__(self):
        self.seat_matrix = [[None] * 5 for _ in range(10)]
        self.lock = threading.Lock()

    def book(self):
        # ... (booking logic remains unchanged) ...
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
                        self.seat_matrix[i][j] = {"name": name, "date": date}
                        booking_events.put({"row": i, "col": j, "data": self.seat_matrix[i][j]})
                        return jsonify({"message": f"Seat booked at ({i},{j}) for {name}"})
        
        return jsonify({"message": "No seats available"})

    def show(self):
        return jsonify(self.seat_matrix)
    
    # NEW: Method to reset all seats
    def reset(self):
        with self.lock:
            self.seat_matrix = [[None] * 50 for _ in range(50)]
        return jsonify({"message": "All seats have been reset."})

# ... (existing event stream logic remains unchanged) ...
def event_stream():
    while True:
        try:
            event = booking_events.get(timeout=10)
            yield f'data: {json.dumps(event)}\n\n'
        except Queue.Empty:
            yield 'data: {"event": "ping"}\n\n'

@app.route('/booking/stream')
def stream():
    return Response(event_stream(), mimetype="text/event-stream")

handler = TicketBooking()

app.add_url_rule('/booking', view_func=handler.book, methods=['POST'])
app.add_url_rule('/booking/show', view_func=handler.show, methods=['GET'])
# NEW: Add a route to reset the seats
app.add_url_rule('/booking/reset', view_func=handler.reset, methods=['POST'])

@app.route('/')
def serve_index():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'index.html')

if __name__ == '__main__':
    app.run(debug=True)