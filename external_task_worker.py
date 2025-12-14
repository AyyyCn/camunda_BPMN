import requests
import json
import time
from typing import Dict, Any, Optional
from camunda_client import CamundaClient

class ExternalTaskWorker:
    def __init__(self, camunda_url: str = "http://localhost:8080/engine-rest", 
                 services_base_url: str = "http://localhost"):
        self.camunda = CamundaClient(camunda_url)
        self.services_base_url = services_base_url
        self.running = False
    
    def handle_validate_input(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Validate reservation input"""
        variables = task.get("variables", {})
        
        required_fields = ["first_name", "last_name", "email", "check_in", "check_out"]
        missing_fields = [field for field in required_fields if not variables.get(field, {}).get("value")]
        
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")
        
        return {"valid": True}
    
    def handle_search_client(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Search for existing client by email"""
        variables = task.get("variables", {})
        email = variables.get("email", {}).get("value")
        
        if not email:
            return {"clientFound": False}
        
        url = f"{self.services_base_url}:5004/api/clients/search"
        response = requests.get(url, params={"email": email})
        
        if response.status_code == 200 and response.json():
            client = response.json()[0]
            return {
                "clientFound": True,
                "client_id": client.get("id")
            }
        
        return {"clientFound": False}
    
    def handle_create_client(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Create new client"""
        variables = task.get("variables", {})
        
        client_data = {
            "first_name": variables.get("first_name", {}).get("value"),
            "last_name": variables.get("last_name", {}).get("value"),
            "email": variables.get("email", {}).get("value"),
            "phone": variables.get("phone", {}).get("value")
        }
        
        url = f"{self.services_base_url}:5004/api/clients/create"
        response = requests.post(url, json=client_data)
        response.raise_for_status()
        
        result = response.json()
        return {"client_id": result.get("client_id")}
    
    def handle_check_room_availability(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Check room availability"""
        variables = task.get("variables", {})
        check_in = variables.get("check_in", {}).get("value")
        check_out = variables.get("check_out", {}).get("value")
        
        url = f"{self.services_base_url}:5002/api/rooms/available"
        params = {}
        if check_in:
            params["check_in"] = check_in
        if check_out:
            params["check_out"] = check_out
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        available_rooms = response.json()
        room_available = len(available_rooms) > 0
        
        result = {
            "roomAvailable": room_available
        }
        
        if room_available:
            result["selected_room_id"] = available_rooms[0].get("id")
        
        return result
    
    # ... inside ExternalTaskWorker class ...

    def handle_check_reservation_type(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        BPMN Task: check reservation type
        Logic: Determine if this is a standard booking or needs special handling
        """
        variables = task.get("variables", {})
        guests = variables.get("guests", {}).get("value", 1)
        room_type = variables.get("room_type", {}).get("value", "standard")
        
        # Simple Logic: Suites or groups > 5 are 'complex', others 'standard'
        res_type = "standard"
        if room_type == "suite" or guests > 5:
            res_type = "complex"
            
        print(f"Checked Reservation Type: {res_type}")
        
        return {
            "reservation_type": res_type,
            "requires_manager_approval": res_type == "complex"
        }

    def handle_check_meal_plan(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        BPMN Task: check meal plan
        Logic: Validate if the requested meal plan exists in the Restaurant Service
        """
        variables = task.get("variables", {})
        requested_plan = variables.get("meal_plan", {}).get("value", "none")
        
        if requested_plan == "none":
             return {"meal_plan_valid": True, "meal_cost": 0}

        # Query Restaurant Service to check if the category exists (e.g., 'breakfast')
        url = f"{self.services_base_url}:5003/api/restaurant/menu"
        try:
            response = requests.get(url, params={'category': requested_plan})
            items = response.json()
            
            if items:
                # Mock logic: take the price of the first item in that category as the daily add-on
                daily_cost = items[0]['price']
                return {
                    "meal_plan_valid": True, 
                    "meal_plan_daily_cost": daily_cost
                }
            else:
                print(f"Meal plan '{requested_plan}' not found.")
                return {"meal_plan_valid": False, "meal_cost": 0}
                
        except Exception as e:
            print(f"Failed to check meal plan: {e}")
            # Default to valid to not block process in demo, but log error
            return {"meal_plan_valid": True, "meal_cost": 0}


    
    def handle_block_room(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Block a room for booking"""
        variables = task.get("variables", {})
        room_id = variables.get("selected_room_id", {}).get("value")
        
        if not room_id:
            raise ValueError("No room_id provided")
        
        booking_id = variables.get("booking_id", {}).get("value")
        if not booking_id:
            booking_id = f"temp_{int(time.time())}"
        
        url = f"{self.services_base_url}:5002/api/rooms/{room_id}/block"
        response = requests.post(url, json={
            "room_id": room_id,
            "booking_id": booking_id
        })
        response.raise_for_status()
        
        return {"room_id": room_id, "room_blocked": True}
    
    def handle_create_booking(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Create booking record"""
        variables = task.get("variables", {})
        
        booking_data = {
            "client_id": variables.get("client_id", {}).get("value"),
            "room_id": variables.get("room_id", {}).get("value"),
            "check_in": variables.get("check_in", {}).get("value"),
            "check_out": variables.get("check_out", {}).get("value"),
            "guests": variables.get("guests", {}).get("value", 1)
        }
        
        url = f"{self.services_base_url}:5001/api/booking/create"
        response = requests.post(url, json=booking_data)
        response.raise_for_status()
        
        result = response.json()
        return {
            "booking_id": result.get("booking_id"),
            "status": "confirmed"
        }
    
    def handle_get_booking(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get booking details"""
        variables = task.get("variables", {})
        booking_id = variables.get("booking_id", {}).get("value")
        
        url = f"{self.services_base_url}:5001/api/booking/{booking_id}"
        response = requests.get(url)
        response.raise_for_status()
        
        return {"booking": response.json()}
    
    def handle_get_client_bookings(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get all bookings for a client"""
        variables = task.get("variables", {})
        client_id = variables.get("client_id", {}).get("value")
        
        url = f"{self.services_base_url}:5001/api/booking/client/{client_id}"
        response = requests.get(url)
        response.raise_for_status()
        
        bookings = response.json()
        return {"bookings": bookings}
    
    def handle_get_restaurant_orders(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get restaurant orders for a booking"""
        variables = task.get("variables", {})
        booking_id = variables.get("booking_id", {}).get("value")
        
        if not booking_id:
            booking = variables.get("booking", {}).get("value")
            if isinstance(booking, dict):
                booking_id = booking.get("id")
        
        if not booking_id:
            return {"orders": []}
           
        url = f"{self.services_base_url}:5003/api/restaurant/booking/{booking_id}/orders"
        response = requests.get(url)
        response.raise_for_status()
        
        return {"orders": response.json()}
    
    
    def handle_process_payment(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        BPMN Task: process payment
        Logic: Call the new Payment Service
        """
        variables = task.get("variables", {})
        booking_id = variables.get("booking_id", {}).get("value")
        
        # Calculate amount (mock logic: Room Price * Nights + Meal Cost)
        # In a real scenario, you'd fetch the room price from RoomService
        room_price = 100 # Default fallback
        nights = 2 # Default fallback
        meal_cost = variables.get("meal_plan_daily_cost", {}).get("value", 0)
        
        total_amount = (room_price + meal_cost) * nights
        
        url = f"{self.services_base_url}:5005/api/payment/process"
        payload = {
            "booking_id": booking_id,
            "amount": total_amount,
            "payment_method": "credit_card" # Simplified
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        
        return {
            "payment_status": result.get("status"),
            "transaction_id": result.get("transaction_id"),
            "total_amount_paid": total_amount
        }

    def handle_generate_confirmation(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        BPMN Task: generate confirmation
        Logic: Call the new Accounting Service
        """
        variables = task.get("variables", {})
        booking_id = variables.get("booking_id", {}).get("value")
        total_amount = variables.get("total_amount_paid", {}).get("value")
        
        client_data = {
            "first_name": variables.get("first_name", {}).get("value"),
            "last_name": variables.get("last_name", {}).get("value"),
            "email": variables.get("email", {}).get("value")
        }
        
        url = f"{self.services_base_url}:5006/api/accounting/generate-confirmation"
        payload = {
            "booking_id": booking_id,
            "client_data": client_data,
            "total_amount": total_amount
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        
        return {
            "confirmation_doc_id": result.get("document_id"),
            "confirmation_sent": True
        }
        
        
    def process_task(self, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single external task"""
        topic = task.get("topicName")
        task_id = task.get("id")
        
        handlers = {
            "validate-input": self.handle_validate_input,
            "search-client": self.handle_search_client,
            "create-client": self.handle_create_client,
            "check-room-availability": self.handle_check_room_availability,
            "check-reservation-type": self.handle_check_reservation_type, 
            "check-meal-plan": self.handle_check_meal_plan, 
            "block-room": self.handle_block_room,
            "create-booking": self.handle_create_booking,
            "process-payment": self.handle_process_payment, 
            "generate-confirmation": self.handle_generate_confirmation,
            "get-booking": self.handle_get_booking,
            "get-client-bookings": self.handle_get_client_bookings,
            "get-restaurant-orders": self.handle_get_restaurant_orders
        }
        
        handler = handlers.get(topic)
        if not handler:
            print(f"No handler for topic: {topic}")
            return None
        
        try:
            result = handler(task)
            self.camunda.complete_external_task(task_id, result)
            print(f"Completed task {task_id} for topic {topic}")
            return result
        except Exception as e:
            print(f"Error processing task {task_id}: {e}")
            self.camunda.handle_bpmn_error(task_id, "TASK_ERROR", str(e))
            return None
    
    def run(self, interval: int = 5):
        """Run the worker loop"""
        self.running = True
        print("External Task Worker started...")
        
        while self.running:
            try:
                for topic in ["validate-input", "search-client", "create-client", 
                                "check-room-availability", "check-reservation-type", 
                                "check-meal-plan", "block-room", "create-booking",
                                "process-payment", "generate-confirmation",
                                "get-booking", "get-client-bookings", "get-restaurant-orders"]:
                    tasks = self.camunda.fetch_and_lock_external_tasks(topic, max_tasks=1)
                    for task in tasks:
                        self.process_task(task)
                
                time.sleep(interval)
            except KeyboardInterrupt:
                print("\nStopping worker...")
                self.running = False
            except Exception as e:
                print(f"Error in worker loop: {e}")
                time.sleep(interval)


if __name__ == "__main__":
    worker = ExternalTaskWorker()
    worker.run()

