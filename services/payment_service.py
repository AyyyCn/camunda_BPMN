from flask import Flask, request, jsonify
import uuid
import datetime

app = Flask(__name__)

# Mock database
transactions = {}

class PaymentService:
    @app.route('/api/payment/process', methods=['POST'])
    def process_payment():
        data = request.json
        booking_id = data.get('booking_id')
        amount = data.get('amount')
        payment_method = data.get('payment_method', 'credit_card')
        
        # Simulate payment processing logic
        transaction_id = str(uuid.uuid4())
        
        # Simple validation mock
        if amount <= 0:
             return jsonify({'error': 'Invalid amount'}), 400

        transaction = {
            'id': transaction_id,
            'booking_id': booking_id,
            'amount': amount,
            'status': 'completed',
            'method': payment_method,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        transactions[transaction_id] = transaction
        
        print(f"Payment processed for Booking {booking_id}: ${amount}")
        
        return jsonify({
            'transaction_id': transaction_id,
            'status': 'success',
            'message': 'Payment processed successfully'
        })

    @app.route('/api/payment/history/<booking_id>', methods=['GET'])
    def get_payment_history(booking_id):
        history = [t for t in transactions.values() if t['booking_id'] == booking_id]
        return jsonify(history)

if __name__ == '__main__':
    app.run(port=5005, debug=True)