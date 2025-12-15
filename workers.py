import asyncio
import requests
from pyzeebe import ZeebeWorker, create_insecure_channel

def validate_input(first_name: str = "", last_name: str = "", email: str = "", check_in: str = "", check_out: str = "", **kwargs):
    missing_fields = [f for f, val in zip(
        ["first_name", "last_name", "email", "check_in", "check_out"],
        [first_name, last_name, email, check_in, check_out]
    ) if not val]
    if missing_fields:
        raise ValueError(f"Missing required fields: {missing_fields}")
    return {"valid": True}


def search_client(email: str = "", **kwargs):
    if not email:
        return {"clientFound": False}
    response = requests.get("http://localhost:5002/api/clients/search", params={"email": email})
    if response.status_code == 200 and response.json():
        client_data = response.json()[0]
        return {"clientFound": True, "client_id": client_data.get("id")}
    return {"clientFound": False}


def create_client(first_name: str = "", last_name: str = "", email: str = "", phone: str = None, **kwargs):
    data = {"first_name": first_name, "last_name": last_name, "email": email, "phone": phone}
    response = requests.post("http://localhost:5002/api/clients/create", json=data)
    response.raise_for_status()
    return {"client_id": response.json().get("client_id")}


def check_room_availability(check_in: str = "", check_out: str = "", **kwargs):
    response = requests.get("http://localhost:5009/api/rooms/available", params={"check_in": check_in, "check_out": check_out})
    response.raise_for_status()
    rooms = response.json()
    return {"roomAvailable": bool(rooms), "selected_room_id": rooms[1]["id"] if rooms else None}


def check_reservation_type(guests: int = 1, room_type: str = "standard", **kwargs):
    res_type = "standard"
    if room_type.lower() == "suite" or guests > 5:
        res_type = "complex"
    return {"reservation_type": res_type, "requires_manager_approval": res_type == "complex"}


def check_meal_plan(meal_plan: str = "none", **kwargs):
    if meal_plan.lower() == "none":
        return {"meal_plan_valid": True, "meal_plan_daily_cost": 0}
    response = requests.get("http://localhost:5008/api/restaurant/menu", params={"category": meal_plan})
    items = response.json()
    if items:
        return {"meal_plan_valid": True, "meal_plan_daily_cost": items[0]["price"]}
    return {"meal_plan_valid": False, "meal_plan_daily_cost": 0}


def block_room(selected_room_id: str = "", booking_id = "", **kwargs):
    # Convert booking_id to string if it's not already
    booking_id_str = str(booking_id) if booking_id else ""
    
    print(f"Blocking room: room_id={selected_room_id}, booking_id={booking_id_str}")
    
    # Only send booking_id in the payload, room_id is in the URL
    payload = {"booking_id": booking_id_str}
    response = requests.post(f"http://localhost:5009/api/rooms/{selected_room_id}/block", json=payload)
    
    if response.status_code != 200:
        print(f"Error response from room service: {response.status_code}")
        print(f"Response body: {response.text}")
    
    response.raise_for_status()
    return {"room_blocked": True, "room_id": selected_room_id}

def create_booking(client_id: str = "", room_id: str = "", check_in: str = "", check_out: str = "", guests: int = 1, **kwargs):
    data = {
        "client_id": client_id,
        "room_id": room_id,
        "check_in": check_in,
        "check_out": check_out,
        "guests": guests
    }
    response = requests.post("http://localhost:5001/api/booking/create", json=data)
    response.raise_for_status()
    result = response.json()
    booking_id = result.get("booking_id")


    # Fetch the room price from room service
    room_resp = requests.get(f"http://localhost:5009/api/rooms/{room_id}")
    room_resp.raise_for_status()
    room = room_resp.json()
    
    total_amount = room.get("price", 0) 
    print("total_amount", total_amount)
    return {
        "booking_id": booking_id,
        "status": result.get("status"),
        "total_amount": total_amount
    }


def process_payment(booking_id: str = "", total_amount: float = 0, **kwargs):
    if total_amount <= 0:
        raise ValueError(f"Invalid total_amount: {total_amount}")
    
    data = {"booking_id": booking_id, "amount": total_amount, "payment_method": "credit_card"}
    response = requests.post("http://localhost:5007/api/payment/process", json=data)
    response.raise_for_status()
    result = response.json()
    return {"payment_status": result.get("status"), "transaction_id": result.get("transaction_id")}



def generate_accounting(booking_id: str = "", first_name: str = "", last_name: str = "", email: str = "", total_amount: float = 0, **kwargs):
    data = {"booking_id": booking_id, "client_data": {"first_name": first_name, "last_name": last_name, "email": email}, "total_amount": total_amount}
    response = requests.post("http://localhost:5006/api/accounting/generate-confirmation", json=data)
    response.raise_for_status()
    result = response.json()
    return {"confirmation_doc_id": result.get("document_id"), "confirmation_sent": True}


async def main():
    # Create channel inside the async context
    channel = create_insecure_channel(grpc_address="localhost:26500")
    worker = ZeebeWorker(channel)
    
    # Register all task handlers
    worker.task(task_type="validate-input")(validate_input)
    worker.task(task_type="search-client")(search_client)
    worker.task(task_type="create-client")(create_client)
    worker.task(task_type="check-room-availability")(check_room_availability)
    worker.task(task_type="check-reservation-type")(check_reservation_type)
    worker.task(task_type="check-meal-plan")(check_meal_plan)
    worker.task(task_type="block-room")(block_room)
    worker.task(task_type="create-booking")(create_booking)
    worker.task(task_type="process-payment")(process_payment)
    worker.task(task_type="generate-accounting")(generate_accounting)
    
    print("🚀 Camunda 8 workers running...")
    await worker.work()

if __name__ == "__main__":
    asyncio.run(main())