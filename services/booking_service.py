from flask import Flask, request, jsonify
import uuid
from datetime import datetime, timedelta
import json

app = Flask(__name__)

# Mock database
bookings = {}
clients = {}

class BookingService:
    @app.route('/api/booking/create', methods=['POST'])
    def create_booking():
        data = request.json
        booking_id = str(uuid.uuid4())
        
        booking = {
            'id': booking_id,
            'client_id': data.get('client_id'),
            'room_id': data.get('room_id'),
            'check_in': data.get('check_in'),
            'check_out': data.get('check_out'),
            'guests': data.get('guests', 1),
            'status': 'confirmed',
            'total_amount': data.get('total_amount', 0),
            'created_at': datetime.now().isoformat()
        }
        
        bookings[booking_id] = booking
        return jsonify({'booking_id': booking_id, 'status': 'success'})

    @app.route('/api/booking/<booking_id>', methods=['GET'])
    def get_booking(booking_id):
        booking = bookings.get(booking_id)
        if booking:
            return jsonify(booking)
        return jsonify({'error': 'Booking not found'}), 404

    @app.route('/api/booking/<booking_id>/cancel', methods=['PUT'])
    def cancel_booking(booking_id):
        if booking_id in bookings:
            bookings[booking_id]['status'] = 'cancelled'
            return jsonify({'status': 'cancelled'})
        return jsonify({'error': 'Booking not found'}), 404

    @app.route('/api/booking/client/<client_id>', methods=['GET'])
    def get_client_bookings(client_id):
        client_bookings = [b for b in bookings.values() if b['client_id'] == client_id]
        return jsonify(client_bookings)

if __name__ == '__main__':
    app.run(port=5001, debug=True)