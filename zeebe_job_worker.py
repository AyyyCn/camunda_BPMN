from pyzeebe import ZeebeWorker, create_insecure_channel, create_camunda_cloud_client
from pyzeebe.task import task
import requests
from typing import Dict, Any, Optional
import os

class HotelServiceWorker:
    def __init__(self, 
                 zeebe_address: str = "localhost:26500",
                 services_base_url: str = "http://localhost",
                 use_camunda_cloud: bool = False,
                 **cloud_kwargs):
        """
        Initialize Zeebe job worker
        
        Args:
            zeebe_address: Zeebe broker address
            services_base_url: Base URL for Flask microservices
            use_camunda_cloud: Whether to use Camunda Cloud
            **cloud_kwargs: Camunda Cloud credentials
        """
        self.services_base_url = services_base_url
        
        if use_camunda_cloud:
            self.worker = ZeebeWorker(
                create_camunda_cloud_client(**cloud_kwargs)
            )
        else:
            channel = create_insecure_channel(zeebe_address)
            self.worker = ZeebeWorker(channel)
        
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all job handlers"""
        
        @self.worker.task(task_type="validate-input")
        async def validate_input(variables: Dict[str, Any]) -> Dict[str, Any]:
            """Validate reservation input"""
            required_fields = ["first_name", "last_name", "email", "check_in", "check_out"]
            missing_fields = [field for field in required_fields if not variables.get(field)]
            
            if missing_fields:
                raise ValueError(f"Missing required fields: {missing_fields}")
            
            return {"valid": True}
        
        @self.worker.task(task_type="search-client")
        async def search_client(variables: Dict[str, Any]) -> Dict[str, Any]:
            """Search for existing client by email"""
            email = variables.get("email")
            
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
        
        @self.worker.task(task_type="create-client")
        async def create_client(variables: Dict[str, Any]) -> Dict[str, Any]:
            """Create new client"""
            client_data = {
                "first_name": variables.get("first_name"),
                "last_name": variables.get("last_name"),
                "email": variables.get("email"),
                "phone": variables.get("phone")
            }
            
            url = f"{self.services_base_url}:5004/api/clients/create"
            response = requests.post(url, json=client_data)
            response.raise_for_status()
            
            result = response.json()
            return {"client_id": result.get("client_id")}
        
        @self.worker.task(task_type="check-room-availability")
        async def check_room_availability(variables: Dict[str, Any]) -> Dict[str, Any]:
            """Check room availability"""
            check_in = variables.get("check_in")
            check_out = variables.get("check_out")
            
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
        
        @self.worker.task(task_type="block-room")
        async def block_room(variables: Dict[str, Any]) -> Dict[str, Any]:
            """Block a room for booking"""
            room_id = variables.get("selected_room_id")
            
            if not room_id:
                raise ValueError("No selected_room_id provided")
            
            booking_id = variables.get("booking_id")
            if not booking_id:
                import time
                booking_id = f"temp_{int(time.time())}"
            
            url = f"{self.services_base_url}:5002/api/rooms/{room_id}/block"
            response = requests.post(url, json={
                "room_id": room_id,
                "booking_id": booking_id
            })
            response.raise_for_status()
            
            return {"room_id": room_id, "room_blocked": True}
        
        @self.worker.task(task_type="create-booking")
        async def create_booking(variables: Dict[str, Any]) -> Dict[str, Any]:
            """Create booking record"""
            booking_data = {
                "client_id": variables.get("client_id"),
                "room_id": variables.get("room_id"),
                "check_in": variables.get("check_in"),
                "check_out": variables.get("check_out"),
                "guests": variables.get("guests", 1)
            }
            
            url = f"{self.services_base_url}:5001/api/booking/create"
            response = requests.post(url, json=booking_data)
            response.raise_for_status()
            
            result = response.json()
            return {
                "booking_id": result.get("booking_id"),
                "status": "confirmed"
            }
        
        @self.worker.task(task_type="get-booking")
        async def get_booking(variables: Dict[str, Any]) -> Dict[str, Any]:
            """Get booking details"""
            booking_id = variables.get("booking_id")
            
            url = f"{self.services_base_url}:5001/api/booking/{booking_id}"
            response = requests.get(url)
            response.raise_for_status()
            
            return {"booking": response.json()}
        
        @self.worker.task(task_type="get-client-bookings")
        async def get_client_bookings(variables: Dict[str, Any]) -> Dict[str, Any]:
            """Get all bookings for a client"""
            client_id = variables.get("client_id")
            
            url = f"{self.services_base_url}:5001/api/booking/client/{client_id}"
            response = requests.get(url)
            response.raise_for_status()
            
            bookings = response.json()
            return {"bookings": bookings}
        
        @self.worker.task(task_type="get-restaurant-orders")
        async def get_restaurant_orders(variables: Dict[str, Any]) -> Dict[str, Any]:
            """Get restaurant orders for a booking"""
            booking_id = variables.get("booking_id")
            
            if not booking_id:
                booking = variables.get("booking")
                if isinstance(booking, dict):
                    booking_id = booking.get("id")
            
            if not booking_id:
                return {"orders": []}
            
            url = f"{self.services_base_url}:5003/api/restaurant/booking/{booking_id}/orders"
            response = requests.get(url)
            response.raise_for_status()
            
            return {"orders": response.json()}
    
    async def run(self):
        """Start the worker"""
        print("Zeebe Job Worker started...")
        print("Registered task types:")
        print("  - validate-input")
        print("  - search-client")
        print("  - create-client")
        print("  - check-room-availability")
        print("  - block-room")
        print("  - create-booking")
        print("  - get-booking")
        print("  - get-client-bookings")
        print("  - get-restaurant-orders")
        await self.worker.work()


if __name__ == "__main__":
    import asyncio
    
    worker = HotelServiceWorker()
    
    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        print("\nStopping worker...")


