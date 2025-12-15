from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import json

app = Flask(__name__)

# Mock database
rooms = {
    '101': {'id': '101', 'type': 'standard', 'price': 250, 'status': 'available', 'features': ['TV', 'WiFi']},
    '102': {'id': '102', 'type': 'standard', 'price': 250, 'status': 'available', 'features': ['TV', 'WiFi']},
    '201': {'id': '201', 'type': 'superior', 'price': 350, 'status': 'available', 'features': ['TV', 'WiFi', 'MiniBar']},
    '202': {'id': '202', 'type': 'superior', 'price': 350, 'status': 'available', 'features': ['TV', 'WiFi', 'MiniBar']},
    '301': {'id': '301', 'type': 'suite', 'price': 600, 'status': 'available', 'features': ['TV', 'WiFi', 'MiniBar', 'Jacuzzi']}
}

room_bookings = []

class RoomService:
    @app.route('/api/rooms/available', methods=['GET'])
    def get_available_rooms():
        check_in = request.args.get('check_in')
        check_out = request.args.get('check_out')
        
        # Simple availability check
        available_rooms = [room for room in rooms.values() if room['status'] == 'available']
        return jsonify(available_rooms)

    @app.route('/api/rooms/<room_id>/block', methods=['POST'])
    def block_room():
        data = request.json
        room_id = data.get('room_id')
        booking_id = data.get('booking_id')
        
        if room_id in rooms and rooms[room_id]['status'] == 'available':
            rooms[room_id]['status'] = 'blocked'
            room_bookings.append({
                'room_id': room_id,
                'booking_id': booking_id,
                'blocked_until': datetime.now() + timedelta(hours=24)
            })
            return jsonify({'status': 'room_blocked', 'room_id': room_id})
        return jsonify({'error': 'Room not available'}), 400

    @app.route('/api/rooms/<room_id>/release', methods=['POST'])
    def release_room(room_id):
        if room_id in rooms:
            rooms[room_id]['status'] = 'available'
            # Remove from room_bookings
            global room_bookings
            room_bookings = [rb for rb in room_bookings if rb['room_id'] != room_id]
            return jsonify({'status': 'room_released', 'room_id': room_id})
        return jsonify({'error': 'Room not found'}), 404

    @app.route('/api/rooms/<room_id>', methods=['GET'])
    def get_room(room_id):
        room = rooms.get(room_id)
        if room:
            return jsonify(room)
        return jsonify({'error': 'Room not found'}), 404

    @app.route('/api/rooms', methods=['GET'])
    def get_all_rooms():
        return jsonify(list(rooms.values()))
    
    @app.route('/api/rooms/<room_id>/status', methods=['PUT'])
    def update_room_status(room_id):
        data = request.json
        new_status = data.get('status')

        if room_id in rooms:
            rooms[room_id]['status'] = new_status
            return jsonify({'id': room_id, 'status': new_status})
        return jsonify({'error': 'Room not found'}), 404

    @app.route('/api/rooms/assign', methods=['POST'])
    def assign_room():
        data = request.json
        room_id = data.get('room_id')
        client_id = data.get('client_id')

        if room_id in rooms and rooms[room_id]['status'] == 'available':
            rooms[room_id]['status'] = 'occupied'
            rooms[room_id]['current_guest'] = client_id
            return jsonify({'status': 'assigned', 'room_id': room_id})
        return jsonify({'error': 'Room not available'}), 400


if __name__ == '__main__':
    app.run(port=5002, debug=True)