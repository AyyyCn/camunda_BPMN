from pyzeebe import ZeebeWorker, create_insecure_channel, create_camunda_cloud_channel, Job
from pyzeebe.task import task
import requests
from typing import Dict, Any, Optional
import os
import asyncio

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
                create_camunda_cloud_channel(**cloud_kwargs)
            )
        else:
            channel = create_insecure_channel(zeebe_address)
            self.worker = ZeebeWorker(channel)
        
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all job handlers"""
        
        @self.worker.task(task_type="validate-input")
        async def validate_input(job: Job, first_name: str, last_name: str, email: str, check_in: str, check_out: str) -> Dict[str, Any]:
            """Validate reservation input"""
            print(f"[Zeebe] Validating input for {email}...")
            # PyZeebe injects variables as arguments if names match
            if not email or not check_in:
                 raise ValueError(f"Missing required fields")
            
            return {"valid": True}
        
        @self.worker.task(task_type="search-client")
        async def search_client(job: Job, email: str) -> Dict[str, Any]:
            """Search for existing client by email"""
            print(f"[Zeebe] Searching client: {email}")
            
            url = f"{self.services_base_url}:5004/api/clients/search"
            try:
                response = requests.get(url, params={"email": email})
                if response.status_code == 200 and response.json():
                    client = response.json()[0]
                    return {
                        "clientFound": True,
                        "client_id": client.get("id")
                    }
            except Exception as e:
                print(f"Service Error: {e}")
            
            return {"clientFound": False}
        
        @self.worker.task(task_type="create-client")
        async def create_client(job: Job, first_name: str, last_name: str, email: str, phone: str) -> Dict[str, Any]:
            """Create new client"""
            print(f"[Zeebe] Creating client: {email}")
            client_data = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": phone
            }
            
            url = f"{self.services_base_url}:5004/api/clients/create"
            response = requests.post(url, json=client_data)
            response.raise_for_status()
            
            result = response.json()
            return {"client_id": result.get("client_id"), "clientFound": True}
        
        @self.worker.task(task_type="check-room-availability")
        async def check_room_availability(job: Job, check_in: str, check_out: str) -> Dict[str, Any]:
            """Check room availability"""
            print(f"[Zeebe] Checking rooms...")
            
            url = f"{self.services_base_url}:5002/api/rooms/available"
            params = {"check_in": check_in, "check_out": check_out}
            
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
        async def block_room(job: Job, selected_room_id: int) -> Dict[str, Any]:
            """Block a room for booking"""
            print(f"[Zeebe] Blocking room {selected_room_id}...")
            
            import time
            temp_booking_id = f"temp_{int(time.time())}"
            
            url = f"{self.services_base_url}:5002/api/rooms/{selected_room_id}/block"
            response = requests.post(url, json={
                "room_id": selected_room_id,
                "booking_id": temp_booking_id
            })
            response.raise_for_status()
            
            return {"room_blocked": True}
        
        @self.worker.task(task_type="create-booking")
        async def create_booking(job: Job, client_id: int, selected_room_id: int, check_in: str, check_out: str) -> Dict[str, Any]:
            """Create booking record"""
            print(f"[Zeebe] Creating Booking...")
            booking_data = {
                "client_id": client_id,
                "room_id": selected_room_id,
                "check_in": check_in,
                "check_out": check_out,
                "guests": 1
            }
            
            url = f"{self.services_base_url}:5001/api/booking/create"
            response = requests.post(url, json=booking_data)
            response.raise_for_status()
            
            result = response.json()
            booking_id = result.get("booking_id")
            print(f" >>> BOOKING CONFIRMED: ID {booking_id} <<<")
            
            return {
                "booking_id": booking_id,
                "status": "confirmed"
            }

        # --- NEW: Payment Handler ---
        @self.worker.task(task_type="process-payment")
        async def process_payment(job: Job, booking_id: int, email: str) -> Dict[str, Any]:
            """Process payment for the booking"""
            print(f"[Zeebe] Processing Payment for Booking {booking_id}...")
            
            # Using port 5005 for Payment Service
            url = f"{self.services_base_url}:5005/api/payments/process"
            
            payment_payload = {
                "booking_id": booking_id,
                "amount": 150.0, # Hardcoded for demo
                "currency": "USD",
                "client_email": email
            }

            try:
                response = requests.post(url, json=payment_payload)
                response.raise_for_status()
                data = response.json()
                print(f" >>> PAYMENT SUCCESS: {data.get('payment_id')} <<<")
                return {"payment_id": data.get("payment_id"), "payment_status": "PAID"}
            except Exception as e:
                # If payment fails, throw error so Zeebe can handle retries or incidents
                raise Exception(f"Payment Failed: {str(e)}")

        # --- NEW: Accounting Handler ---
        @self.worker.task(task_type="generate-accounting")
        async def generate_accounting(job: Job, booking_id: int, payment_id: int) -> Dict[str, Any]:
            """Generate Invoice"""
            print(f"[Zeebe] Generating Invoice for Payment {payment_id}...")
            
            # Using port 5006 for Accounting Service
            url = f"{self.services_base_url}:5006/api/invoices/create"
            
            invoice_payload = {
                "booking_id": booking_id,
                "payment_id": payment_id
            }

            response = requests.post(url, json=invoice_payload)
            response.raise_for_status()
            data = response.json()
            
            print(f" >>> INVOICE GENERATED: {data.get('invoice_id')} <<<")
            
            # Trigger ESB sync to HQ (Central DB + SAP)
            try:
                esb_url = f"{self.services_base_url}:8280/api/v1/finance/transaction"
                sync_payload = {
                    "booking_id": booking_id,
                    "amount": 150.0,
                    "date": "2024-01-15",
                    "invoice_id": data.get("invoice_id")
                }
                requests.post(esb_url, json=sync_payload, timeout=5)
                print(f" >>> ESB SYNC: Pushed to HQ <<<")
            except Exception as e:
                print(f" >>> ESB SYNC: Failed (non-blocking) - {e} <<<")
            
            return {"invoice_id": data.get("invoice_id")}

        # --- NEW: ESB Data Sync Handler (for manual sync triggers) ---
        @self.worker.task(task_type="sync-to-hq")
        async def sync_to_hq(job: Job, booking_id: str, client_id: str) -> Dict[str, Any]:
            """Sync data to HQ via ESB"""
            print(f"[Zeebe] Syncing to HQ via ESB...")
            
            esb_url = f"{self.services_base_url}:8280/api/v1/sync/guest-profile"
            
            try:
                response = requests.post(esb_url, json={
                    "client_id": client_id,
                    "booking_id": booking_id,
                    "branch": "SOUSSE"
                }, timeout=10)
                response.raise_for_status()
                print(f" >>> HQ SYNC COMPLETE <<<")
                return {"synced": True}
            except Exception as e:
                print(f" >>> HQ SYNC FAILED: {e} <<<")
                return {"synced": False, "error": str(e)}

    
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
        print("  - process-payment")
        print("  - generate-accounting")
        print("  - sync-to-hq (ESB integration)")
        await self.worker.work()


if __name__ == "__main__":
    worker = HotelServiceWorker()
    
    try:
        # Create event loop for asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(worker.run())
    except KeyboardInterrupt:
        print("\nStopping worker...")