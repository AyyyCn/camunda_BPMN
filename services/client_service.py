from flask import Flask, request, jsonify
import uuid
from datetime import datetime

app = Flask(__name__)

# Mock database
clients = {}
complaints_db = {}

class ClientService:
    @app.route('/api/clients/create', methods=['POST'])
    def create_client():
        data = request.json
        client_id = str(uuid.uuid4())
        
        client = {
            'id': client_id,
            'first_name': data.get('first_name'),
            'last_name': data.get('last_name'),
            'email': data.get('email'),
            'phone': data.get('phone'),
            'loyalty_points': 0,
            'preferences': data.get('preferences', {})
        }
        
        clients[client_id] = client
        return jsonify({'client_id': client_id, 'status': 'created'})

    @app.route('/api/clients/<client_id>', methods=['GET'])
    def get_client(client_id):
        client = clients.get(client_id)
        if client:
            return jsonify(client)
        return jsonify({'error': 'Client not found'}), 404

    @app.route('/api/clients/<client_id>/loyalty', methods=['PUT'])
    def update_loyalty_points():
        data = request.json
        client_id = data.get('client_id')
        points = data.get('points', 0)
        
        if client_id in clients:
            clients[client_id]['loyalty_points'] += points
            return jsonify({'loyalty_points': clients[client_id]['loyalty_points']})
        return jsonify({'error': 'Client not found'}), 404

    @app.route('/api/clients/search', methods=['GET'])
    def search_clients():
        email = request.args.get('email')
        if email:
            found_clients = [client for client in clients.values() if client.get('email') == email]
            return jsonify(found_clients)
        return jsonify([])

    @app.route('/api/complaints/log', methods=['POST'])
    def log_complaint():
        data = request.json
        complaint_id = str(uuid.uuid4())
        complaint = {
            'id': complaint_id,
            'client_id': data.get('client_id'),
            'room_id': data.get('room_id'),
            'description': data.get('description'),
            'status': 'open',
            'created_at': datetime.now().isoformat()
        }
        # Store complaint in in‑memory dict (demo only)
        complaints_db[complaint_id] = complaint

        return jsonify({'complaint_id': complaint_id, 'status': 'logged'})

    @app.route('/api/complaints/<complaint_id>/close', methods=['PUT'])
    def close_complaint(complaint_id):
        # Mock closing
        return jsonify({'status': 'closed', 'closed_at': datetime.now().isoformat()})


if __name__ == '__main__':
    app.run(port=5004, debug=True)