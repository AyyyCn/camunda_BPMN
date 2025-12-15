import asyncio
import requests
from pyzeebe import ZeebeWorker, create_insecure_channel

# --- Configuration ---
# Ports based on the service code you provided:
ROOM_SERVICE_URL = "http://localhost:5002/api"
CLIENT_SERVICE_URL = "http://localhost:5004/api"
ACCOUNTING_SERVICE_URL = "http://localhost:5006/api"
# Mock Maintenance URL (since no code was provided for it)
MAINTENANCE_SERVICE_URL = "http://localhost:5010/api" 

# --- Worker Functions ---

def receive_and_log_complaint(client_id: str = "", room_id: str = "", description: str = "", **kwargs):
    print(f"📝 Logging complaint for Client {client_id} in Room {room_id}")
    
    payload = {
        "client_id": client_id,
        "room_id": room_id,
        "description": description,
        "status": "received"
    }
    
    # Calls the updated ClientService
    response = requests.post(f"{CLIENT_SERVICE_URL}/complaints/log", json=payload)
    response.raise_for_status()
    result = response.json()
    
    return {
        "complaint_id": result.get("complaint_id"),
        "complaint_logged": True
    }

def classify_and_redirect(complaint_id: str, description: str, **kwargs):
    print(f"fw Categorizing complaint {complaint_id}...")
    
    # Simple logic to classify based on keywords
    category = "general"
    service_target = "client_service"
    
    desc_lower = description.lower()
    if any(x in desc_lower for x in ["water", "leak", "broken", "dirty", "ac", "light"]):
        category = "technical"
        service_target = "room_service"
    elif "bill" in desc_lower or "money" in desc_lower:
        category = "billing"
        service_target = "payment_service"
        
    return {
        "category": category,
        "service_target": service_target
    }

def assess_issue_severity(category: str, description: str, **kwargs):
    # Logic: Technical issues are usually High severity in this context
    severity = "low"
    if category == "technical":
        severity = "high"
    
    print(f"⚖️ Issue assessed as: {severity.upper()}")
    
    return {
        "severity": severity,
        "requires_relocation": severity == "high",
        "requires_immediate_repair": severity == "high"
    }

def redirect_to_other_service(service_target: str, **kwargs):
    print(f"↪️ Redirecting to external service: {service_target}")
    # Logic to notify other departments would go here
    return {"redirected": True}

def update_defective_room_status(room_id: str, **kwargs):
    print(f"🚫 Marking Room {room_id} as Defective/Maintenance")
    
    payload = {"status": "maintenance", "reason": "client_complaint"}
    response = requests.put(f"{ROOM_SERVICE_URL}/rooms/{room_id}/status", json=payload)
    
    # We don't raise error here if room not found, just log it, 
    # but strictly we should check response.status_code
    if response.status_code == 200:
        return {"room_status": "maintenance"}
    return {"room_status": "error"}

def execute_immediate_repair(room_id: str, description: str, **kwargs):
    print(f"🛠️ Dispatching Maintenance team to Room {room_id} for: {description}")
    # Mocking a call to a maintenance service
    # requests.post(f"{MAINTENANCE_SERVICE_URL}/tickets/create", ...)
    return {"repair_ticket_created": True}

def check_room_availability_for_relocation(room_id: str, **kwargs):
    # First, get the type of the current room
    room_resp = requests.get(f"{ROOM_SERVICE_URL}/rooms/{room_id}")
    current_type = "standard"
    if room_resp.status_code == 200:
        current_type = room_resp.json().get('type', 'standard')

    # Check for available rooms of same type
    response = requests.get(f"{ROOM_SERVICE_URL}/rooms/available")
    available_rooms = response.json()
    
    # Find a different room of similar type
    candidates = [r for r in available_rooms if r['type'] == current_type and r['id'] != room_id]
    
    if candidates:
        print(f"✅ Found replacement room: {candidates[0]['id']}")
        return {"new_room_available": True, "new_room_id": candidates[0]['id']}
    
    print("❌ No replacement rooms available.")
    return {"new_room_available": False, "new_room_id": None}

def initiate_guest_relocation(client_id: str, room_id: str, **kwargs):
    print(f"bellhop Initiating relocation protocol for Guest {client_id} from {room_id}")
    return {"relocation_initiated": True}

def assign_new_room_to_guest(client_id: str, new_room_id: str, **kwargs):
    if not new_room_id:
        return {"relocation_success": False}
        
    print(f"🔑 Assigning Key for Room {new_room_id} to Guest {client_id}")
    
    payload = {"client_id": client_id, "room_id": new_room_id}
    response = requests.post(f"{ROOM_SERVICE_URL}/rooms/assign", json=payload)
    
    return {"relocation_success": response.status_code == 200}

def propose_compensation(client_id: str, severity: str, **kwargs):
    amount = 0
    if severity == "high":
        amount = 100 # 100$ voucher
    elif severity == "medium":
        amount = 50
        
    print(f"💰 Proposing compensation of ${amount} for Guest {client_id}")
    
    # Using Accounting Service
    payload = {"client_id": client_id, "amount": amount, "reason": "complaint_compensation"}
    requests.post(f"{ACCOUNTING_SERVICE_URL}/compensation/create", json=payload)
    
    return {"compensation_amount": amount, "compensation_offered": True}

def issue_closed(complaint_id: str, **kwargs):
    print(f"🏁 Closing Complaint Ticket {complaint_id}")
    
    requests.put(f"{CLIENT_SERVICE_URL}/complaints/{complaint_id}/close")
    return {"process_status": "closed"}

# --- Main Execution ---

async def main():
    channel = create_insecure_channel(grpc_address="localhost:26500")
    worker = ZeebeWorker(channel)
    
    # Mapping tasks to BPMN Service Task Types
    worker.task(task_type="receive-log-complaint")(receive_and_log_complaint)
    worker.task(task_type="classify-redirect")(classify_and_redirect)
    worker.task(task_type="assess-severity")(assess_issue_severity)
    worker.task(task_type="redirect-service")(redirect_to_other_service)
    
    worker.task(task_type="update-defective-status")(update_defective_room_status)
    worker.task(task_type="execute-repair")(execute_immediate_repair)
    
    worker.task(task_type="initiate-relocation")(initiate_guest_relocation)
    worker.task(task_type="check-relocation-availability")(check_room_availability_for_relocation)
    worker.task(task_type="assign-new-room")(assign_new_room_to_guest)
    
    worker.task(task_type="propose-compensation")(propose_compensation)
    worker.task(task_type="issue-closed")(issue_closed)

    print("🚀 Complaint Handling Workers running...")
    await worker.work()

if __name__ == "__main__":
    asyncio.run(main())