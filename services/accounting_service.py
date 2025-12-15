from flask import Flask, request, jsonify
import uuid
from datetime import datetime

app = Flask(__name__)

# Mock database for invoices/documents
documents = {}

class AccountingService:
    @app.route('/api/invoices/create', methods=['POST'])
    def create_invoice():
        """Create invoice for a booking"""
        data = request.json
        booking_id = data.get('booking_id')
        payment_id = data.get('payment_id')
        
        invoice_id = str(uuid.uuid4())
        
        invoice = {
            'invoice_id': invoice_id,
            'booking_id': booking_id,
            'payment_id': payment_id,
            'type': 'invoice',
            'generated_at': datetime.now().isoformat(),
            'status': 'generated'
        }
        
        documents[invoice_id] = invoice
        
        print(f"Invoice {invoice_id} generated for booking {booking_id}")
        
        return jsonify({
            'invoice_id': invoice_id,
            'status': 'generated'
        })
    
    @app.route('/api/accounting/generate-confirmation', methods=['POST'])
    def generate_confirmation():
        """Generate booking confirmation"""
        data = request.json
        booking_id = data.get('booking_id')
        client_data = data.get('client_data', {})
        total_amount = data.get('total_amount')
        
        doc_id = str(uuid.uuid4())
        
        document = {
            'doc_id': doc_id,
            'type': 'booking_confirmation',
            'booking_id': booking_id,
            'client_name': f"{client_data.get('first_name')} {client_data.get('last_name')}",
            'amount_billed': total_amount,
            'generated_at': datetime.now().isoformat(),
            'status': 'sent',
            'download_url': f"/documents/{doc_id}.pdf" 
        }
        
        documents[doc_id] = document
        
        print(f"Confirmation generated and sent to {client_data.get('email')}")
        
        return jsonify({
            'document_id': doc_id,
            'status': 'generated',
            'download_url': document['download_url']
        })

if __name__ == '__main__':
    app.run(port=5006, debug=True)