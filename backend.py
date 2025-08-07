from flask import Flask, jsonify, request, send_from_directory, Response, render_template_string
import threading
import os, logging
import json
import time
from seat import TicketBooking
from queue import Queue, Empty
from payment import payment_system

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

# Create logger for this module
logger = logging.getLogger(__name__)

app = Flask(__name__)
booking_events = Queue()

# Configure Flask's logger
app.logger.setLevel(logging.INFO)

# ... (existing event stream logic remains unchanged) ...
def event_stream(client_id):
    logger.info(f"New SSE client connected: {client_id}")
    
    while True:
        try:
            event = booking_events.get(timeout=10)
            logger.debug(f"Sending event to client {client_id}: {event}")
            yield f'data: {json.dumps(event)}\n\n'
        except Empty:
            logger.debug(f"Sending ping to client {client_id}")
            yield 'data: {"event": "ping"}\n\n'
        except Exception as e:
            logger.error(f"Error in event stream for client {client_id}: {str(e)}")
            break
    
    logger.info(f"SSE client disconnected: {client_id}")

@app.route('/booking/stream')
def stream():
    client_id = request.remote_addr
    logger.info(f"SSE stream requested by {client_id}")
    return Response(event_stream(client_id), mimetype="text/event-stream")

handler = TicketBooking()

# Custom wrapper functions to add logging
def book_with_logging():
    client_ip = request.remote_addr
    logger.info(f"Booking request received from {client_ip}")
    
    if not request.is_json:
        logger.warning(f"Non-JSON request from {client_ip}")
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    logger.debug(f"Request data from {client_ip}: {data}")
    
    name = data.get('name')
    date = data.get('date')
    
    try:
        result, status_code = handler.book(name, date)
        
        if result.get('success'):
            logger.info(f"Booking successful for {client_ip}: {result['message']}")
            
            # Add event to queue for SSE
            booking_events.put({
                "event": "booking_update",
                "timestamp": time.time(),
                "client": client_ip,
                "seat": result['seat']
            })
        else:
            logger.info(f"Booking failed for {client_ip}: {result['message']}")
        
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Error processing booking for {client_ip}: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500

def show_with_logging():
    client_ip = request.remote_addr
    logger.info(f"Show seats request from {client_ip}")
    
    try:
        result = handler.show()
        logger.info(f"Show seats processed successfully for {client_ip}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error showing seats for {client_ip}: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500

def reset_with_logging():
    client_ip = request.remote_addr
    logger.info(f"Reset seats request from {client_ip}")
    
    try:
        result, status_code = handler.reset()
        logger.info(f"Seats reset successfully by {client_ip}")
        
        # Add event to queue for SSE
        booking_events.put({
            "event": "seats_reset",
            "timestamp": time.time(),
            "client": client_ip
        })
        
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"Error resetting seats for {client_ip}: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500

# Register routes with logging wrappers
app.add_url_rule('/booking', view_func=book_with_logging, methods=['POST'])
app.add_url_rule('/booking/show', view_func=show_with_logging, methods=['GET'])
app.add_url_rule('/booking/reset', view_func=reset_with_logging, methods=['POST'])

# Payment routes
@app.route('/payment/<session_id>')
def payment_page(session_id):
    """Payment page for a specific session"""
    client_ip = request.remote_addr
    logger.info(f"Payment page requested for session {session_id} by {client_ip}")
    
    session = payment_system.get_payment_session(session_id)
    if not session:
        return jsonify({"error": "Invalid session"}), 404
    
    # Check if session has expired
    if session['status'] == 'expired':
        return jsonify({"error": "Payment session expired"}), 400
    
    payment_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Payment - Ticket Booking</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: 50px auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .payment-card {{
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .booking-details {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 5px;
                margin-bottom: 20px;
            }}
            .amount {{
                font-size: 24px;
                font-weight: bold;
                color: #28a745;
                text-align: center;
                margin: 20px 0;
            }}
            .payment-methods {{
                display: grid;
                gap: 10px;
                margin: 20px 0;
            }}
            .payment-method {{
                padding: 15px;
                border: 2px solid #ddd;
                border-radius: 5px;
                cursor: pointer;
                text-align: center;
                transition: all 0.3s;
            }}
            .payment-method:hover {{
                border-color: #007bff;
                background-color: #f8f9fa;
            }}
            .payment-method.selected {{
                border-color: #007bff;
                background-color: #e3f2fd;
            }}
            .btn {{
                background: #007bff;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                width: 100%;
                margin-top: 20px;
            }}
            .btn:hover {{
                background: #0056b3;
            }}
            .btn:disabled {{
                background: #6c757d;
                cursor: not-allowed;
            }}
            .status {{
                padding: 10px;
                border-radius: 5px;
                margin: 10px 0;
                display: none;
            }}
            .status.success {{
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }}
            .status.error {{
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }}
            .timer {{
                text-align: center;
                color: #dc3545;
                font-weight: bold;
                margin: 10px 0;
            }}
        </style>
    </head>
    <body>
        <div class="payment-card">
            <div class="header">
                <h1>Complete Your Payment</h1>
                <p>Session expires in <span id="timer">15:00</span></p>
            </div>
            
            <div class="booking-details">
                <h3>Booking Details</h3>
                <p><strong>Name:</strong> {session['user_name']}</p>
                <p><strong>Date:</strong> {session['date']}</p>
                <p><strong>Seat:</strong> Row {session['seat_info']['row'] + 1}, Column {session['seat_info']['col'] + 1}</p>
            </div>
            
            <div class="amount">
                Total Amount: $<span id="amount">{session['amount']:.2f}</span>
            </div>
            
            <div class="payment-methods">
                <div class="payment-method" data-method="card">
                    <h4>💳 Credit/Debit Card</h4>
                    <p>Pay with Visa, MasterCard, or American Express</p>
                </div>
                <div class="payment-method" data-method="paypal">
                    <h4>📱 PayPal</h4>
                    <p>Pay with your PayPal account</p>
                </div>
                <div class="payment-method" data-method="wallet">
                    <h4>💰 Digital Wallet</h4>
                    <p>Pay with Apple Pay, Google Pay, or Samsung Pay</p>
                </div>
            </div>
            
            <button class="btn" id="payButton" disabled>Pay $<span id="payAmount">{session['amount']:.2f}</span></button>
            
            <div id="status" class="status"></div>
        </div>
        
        <script>
            const sessionId = '{session_id}';
            let selectedMethod = null;
            let timeLeft = 15 * 60; // 15 minutes in seconds
            
            // Timer countdown
            function updateTimer() {{
                const minutes = Math.floor(timeLeft / 60);
                const seconds = timeLeft % 60;
                document.getElementById('timer').textContent = 
                    `${{minutes.toString().padStart(2, '0')}}:${{seconds.toString().padStart(2, '0')}}`;
                
                if (timeLeft <= 0) {{
                    showStatus('Payment session expired. Please try booking again.', 'error');
                    document.getElementById('payButton').disabled = true;
                    return;
                }}
                
                timeLeft--;
                setTimeout(updateTimer, 1000);
            }}
            
            // Payment method selection
            document.querySelectorAll('.payment-method').forEach(method => {{
                method.addEventListener('click', () => {{
                    document.querySelectorAll('.payment-method').forEach(m => m.classList.remove('selected'));
                    method.classList.add('selected');
                    selectedMethod = method.dataset.method;
                    document.getElementById('payButton').disabled = false;
                }});
            }});
            
            // Payment processing
            document.getElementById('payButton').addEventListener('click', async () => {{
                if (!selectedMethod) {{
                    showStatus('Please select a payment method', 'error');
                    return;
                }}
                
                const button = document.getElementById('payButton');
                button.disabled = true;
                button.textContent = 'Processing Payment...';
                
                try {{
                    const response = await fetch(`/payment/${{sessionId}}/process`, {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            payment_method: selectedMethod
                        }})
                    }});
                    
                    const result = await response.json();
                    
                    if (result.success) {{
                        showStatus('Payment successful! Redirecting to booking confirmation...', 'success');
                        setTimeout(() => {{
                            window.location.href = '/';
                        }}, 2000);
                    }} else {{
                        showStatus(result.message || 'Payment failed', 'error');
                        button.disabled = false;
                        button.textContent = `Pay ${{document.getElementById('payAmount').textContent}}`;
                    }}
                }} catch (error) {{
                    showStatus('Payment failed. Please try again.', 'error');
                    button.disabled = false;
                    button.textContent = `Pay ${{document.getElementById('payAmount').textContent}}`;
                }}
            }});
            
            function showStatus(message, type) {{
                const statusDiv = document.getElementById('status');
                statusDiv.textContent = message;
                statusDiv.className = `status ${{type}}`;
                statusDiv.style.display = 'block';
            }}
            
            // Start timer
            updateTimer();
        </script>
    </body>
    </html>
    """
    
    return payment_html

@app.route('/payment/<session_id>/process', methods=['POST'])
def process_payment(session_id):
    """Process payment for a session"""
    client_ip = request.remote_addr
    logger.info(f"Payment processing requested for session {session_id} by {client_ip}")
    
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    payment_method = data.get('payment_method', 'card')
    
    try:
        success, message = payment_system.process_payment(session_id, payment_method)
        
        if success:
            # Confirm the booking
            result, status_code = handler.confirm_booking(session_id)
            
            if result.get('success'):
                logger.info(f"Payment and booking successful for session {session_id}")
                
                # Add event to queue for SSE
                booking_events.put({
                    "event": "booking_update",
                    "timestamp": time.time(),
                    "client": client_ip,
                    "seat": result['seat']
                })
                
                return jsonify({
                    "success": True,
                    "message": "Payment successful and booking confirmed!",
                    "booking": result
                }), 200
            else:
                return jsonify({
                    "success": False,
                    "message": "Payment successful but booking confirmation failed"
                }), 500
        else:
            return jsonify({
                "success": False,
                "message": message
            }), 400
            
    except Exception as e:
        logger.error(f"Error processing payment for session {session_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/payment/<session_id>/status')
def payment_status(session_id):
    """Check payment status for a session"""
    client_ip = request.remote_addr
    logger.info(f"Payment status requested for session {session_id} by {client_ip}")
    
    try:
        success, data = payment_system.check_payment_status(session_id)
        return jsonify({
            "success": success,
            "data": data
        }), 200
    except Exception as e:
        logger.error(f"Error checking payment status for session {session_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/')
def serve_index():
    client_ip = request.remote_addr
    logger.info(f"Index page requested by {client_ip}")
    try:
        return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'index.html')
    except Exception as e:
        logger.error(f"Error serving index page to {client_ip}: {str(e)}")
        raise

# Error handlers with logging
@app.errorhandler(404)
def not_found_error(error):
    logger.warning(f"404 error: {request.url} requested by {request.remote_addr}")
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {str(error)} for {request.url} by {request.remote_addr}")
    return jsonify({'error': 'Internal server error'}), 500

# Request logging middleware
@app.before_request
def log_request():
    logger.info(f"{request.method} {request.path} from {request.remote_addr} - User-Agent: {request.headers.get('User-Agent', 'Unknown')}")

@app.after_request
def log_response(response):
    logger.info(f"Response: {response.status_code} for {request.method} {request.path}")
    return response

if __name__ == '__main__':
    logger.info("Starting Flask application...")
    logger.info(f"Debug mode: {True}")
    logger.info(f"Log file: app.log")
    logger.info(f"Seat matrix dimensions: 10 rows x 5 columns (50 total seats)")
    
    try:
        app.run(debug=True, port=5001)
    except Exception as e:
        logger.critical(f"Failed to start Flask application: {str(e)}")
        raise