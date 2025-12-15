from flask import Flask, request, jsonify
import uuid

app = Flask(__name__)

# Mock database
clients = {}

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

if __name__ == '__main__':
    app.run(port=5002, debug=True)