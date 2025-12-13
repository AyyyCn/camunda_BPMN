import requests
import json
from typing import Dict, Any, Optional

class CamundaClient:
    def __init__(self, base_url: str = "http://localhost:8080/engine-rest"):
        self.base_url = base_url
    
    def start_process(self, process_key: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Start a Camunda process instance"""
        url = f"{self.base_url}/process-definition/key/{process_key}/start"
        
        payload = {}
        if variables:
            payload["variables"] = self._format_variables(variables)
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    
    def get_process_instance(self, process_instance_id: str) -> Dict[str, Any]:
        """Get process instance details"""
        url = f"{self.base_url}/process-instance/{process_instance_id}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    
    def get_process_variables(self, process_instance_id: str) -> Dict[str, Any]:
        """Get process instance variables"""
        url = f"{self.base_url}/process-instance/{process_instance_id}/variables"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    
    def complete_external_task(self, task_id: str, variables: Dict[str, Any] = None) -> None:
        """Complete an external task"""
        url = f"{self.base_url}/external-task/{task_id}/complete"
        
        payload = {"workerId": "python-worker"}
        if variables:
            payload["variables"] = self._format_variables(variables)
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
    
    def fetch_and_lock_external_tasks(self, topic: str, max_tasks: int = 10, lock_duration: int = 60000) -> list:
        """Fetch and lock external tasks for a topic"""
        url = f"{self.base_url}/external-task/fetchAndLock"
        
        payload = {
            "workerId": "python-worker",
            "maxTasks": max_tasks,
            "topics": [{
                "topicName": topic,
                "lockDuration": lock_duration
            }]
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    
    def handle_bpmn_error(self, task_id: str, error_code: str, error_message: str = None) -> None:
        """Handle BPMN error for an external task"""
        url = f"{self.base_url}/external-task/{task_id}/bpmnError"
        
        payload = {
            "workerId": "python-worker",
            "errorCode": error_code
        }
        if error_message:
            payload["errorMessage"] = error_message
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
    
    def _format_variables(self, variables: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Format variables for Camunda API"""
        formatted = {}
        for key, value in variables.items():
            formatted[key] = {
                "value": json.dumps(value) if isinstance(value, (dict, list)) else value,
                "type": "Json" if isinstance(value, (dict, list)) else "String"
            }
        return formatted


class HotelReservationClient:
    def __init__(self, camunda_url: str = "http://localhost:8080/engine-rest"):
        self.camunda = CamundaClient(camunda_url)
    
    def create_reservation(self, reservation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a hotel reservation through Camunda process"""
        variables = {
            "first_name": reservation_data.get("first_name"),
            "last_name": reservation_data.get("last_name"),
            "email": reservation_data.get("email"),
            "phone": reservation_data.get("phone"),
            "check_in": reservation_data.get("check_in"),
            "check_out": reservation_data.get("check_out"),
            "guests": reservation_data.get("guests", 1),
            "room_type": reservation_data.get("room_type")
        }
        
        result = self.camunda.start_process("HotelReservationProcess", variables)
        return {
            "process_instance_id": result.get("id"),
            "process_definition_id": result.get("definitionId"),
            "status": "started"
        }
    
    def get_booking(self, booking_id: str) -> Dict[str, Any]:
        """Get booking details (requires external task worker to complete)"""
        variables = {"booking_id": booking_id}
        result = self.camunda.start_process("BookingQueryProcess", variables)
        return {
            "process_instance_id": result.get("id"),
            "status": "started"
        }
    
    def get_client_history(self, client_id: str) -> Dict[str, Any]:
        """Get client booking history with restaurant orders"""
        variables = {"client_id": client_id}
        result = self.camunda.start_process("ClientHistoryProcess", variables)
        return {
            "process_instance_id": result.get("id"),
            "status": "started"
        }


if __name__ == "__main__":
    client = HotelReservationClient()
    
    reservation = {
        "first_name": "Jean",
        "last_name": "Dubois",
        "email": "jean.dubois@email.com",
        "phone": "+33123456789",
        "check_in": "2024-01-15",
        "check_out": "2024-01-18",
        "guests": 2,
        "room_type": "standard"
    }
    
    result = client.create_reservation(reservation)
    print("Reservation Process Started:", result)

