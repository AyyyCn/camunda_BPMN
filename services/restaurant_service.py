from flask import Flask, request, jsonify
import uuid
from datetime import datetime

app = Flask(__name__)

# Mock database
menu_items = {
    '1': {'id': '1', 'name': 'Breakfast Buffet', 'price': 45, 'category': 'breakfast'},
    '2': {'id': '2', 'name': 'Lunch Buffet', 'price': 75, 'category': 'lunch'},
    '3': {'id': '3', 'name': 'Dinner Buffet', 'price': 95, 'category': 'dinner'},
    '4': {'id': '4', 'name': 'Room Service - Continental', 'price': 60, 'category': 'room_service'},
    '5': {'id': '5', 'name': 'Room Service - Premium', 'price': 120, 'category': 'room_service'}
}

restaurant_orders = {}
tables = {'1': 'available', '2': 'available', '3': 'available', '4': 'available', '5': 'available'}

class RestaurantService:
    @app.route('/api/restaurant/menu', methods=['GET'])
    def get_menu():
        category = request.args.get('category')
        if category:
            filtered_menu = [item for item in menu_items.values() if item['category'] == category]
            return jsonify(filtered_menu)
        return jsonify(list(menu_items.values()))

    @app.route('/api/restaurant/order', methods=['POST'])
    def create_order():
        data = request.json
        order_id = str(uuid.uuid4())
        
        order = {
            'id': order_id,
            'booking_id': data.get('booking_id'),
            'room_number': data.get('room_number'),
            'items': data.get('items', []),
            'total_amount': sum(menu_items[item_id]['price'] for item_id in data.get('items', [])),
            'status': 'pending',
            'order_type': data.get('order_type', 'room_service'),  # room_service or restaurant
            'created_at': datetime.now().isoformat()
        }
        
        restaurant_orders[order_id] = order
        return jsonify({'order_id': order_id, 'status': 'created'})

    @app.route('/api/restaurant/order/<order_id>', methods=['GET'])
    def get_order(order_id):
        order = restaurant_orders.get(order_id)
        if order:
            return jsonify(order)
        return jsonify({'error': 'Order not found'}), 404

    @app.route('/api/restaurant/order/<order_id>/status', methods=['PUT'])
    def update_order_status(order_id):
        data = request.json
        if order_id in restaurant_orders:
            restaurant_orders[order_id]['status'] = data.get('status')
            return jsonify({'status': 'updated'})
        return jsonify({'error': 'Order not found'}), 404

    @app.route('/api/restaurant/tables/available', methods=['GET'])
    def get_available_tables():
        available_tables = [table_id for table_id, status in tables.items() if status == 'available']
        return jsonify(available_tables)

    @app.route('/api/restaurant/booking/<booking_id>/orders', methods=['GET'])
    def get_booking_orders(booking_id):
        booking_orders = [order for order in restaurant_orders.values() if order.get('booking_id') == booking_id]
        return jsonify(booking_orders)

if __name__ == '__main__':
    app.run(port=5003, debug=True)