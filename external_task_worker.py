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
    
    def process_task(self, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single external task"""
        topic = task.get("topicName")
        task_id = task.get("id")
        
        handlers = {
            "validate-input": self.handle_validate_input,
            "search-client": self.handle_search_client,
            "create-client": self.handle_create_client,
            "check-room-availability": self.handle_check_room_availability,
            "block-room": self.handle_block_room,
            "create-booking": self.handle_create_booking,
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
                             "check-room-availability", "block-room", "create-booking",
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

