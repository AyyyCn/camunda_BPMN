from pyzeebe import ZeebeClient, create_camunda_cloud_client, create_insecure_channel
from typing import Dict, Any, Optional
import os

class Camunda8Client:
    def __init__(self, 
                 zeebe_address: str = "localhost:26500",
                 use_camunda_cloud: bool = False,
                 camunda_cloud_client_id: Optional[str] = None,
                 camunda_cloud_client_secret: Optional[str] = None,
                 camunda_cloud_cluster_id: Optional[str] = None,
                 camunda_cloud_region: Optional[str] = None):
        """
        Initialize Camunda 8 client
        
        Args:
            zeebe_address: Zeebe broker address (default: localhost:26500)
            use_camunda_cloud: Whether to use Camunda Cloud
            camunda_cloud_*: Camunda Cloud credentials (if using cloud)
        """
        if use_camunda_cloud:
            if not all([camunda_cloud_client_id, camunda_cloud_client_secret, 
                       camunda_cloud_cluster_id, camunda_cloud_region]):
                raise ValueError("Camunda Cloud credentials required when use_camunda_cloud=True")
            
            self.client = create_camunda_cloud_client(
                client_id=camunda_cloud_client_id,
                client_secret=camunda_cloud_client_secret,
                cluster_id=camunda_cloud_cluster_id,
                region=camunda_cloud_region
            )
        else:
            channel = create_insecure_channel(zeebe_address)
            self.client = ZeebeClient(channel)
    
    def start_process(self, bpmn_process_id: str, variables: Dict[str, Any] = None, version: int = -1) -> Dict[str, Any]:
        """
        Start a process instance
        
        Args:
            bpmn_process_id: The BPMN process ID (from BPMN file)
            variables: Process variables
            version: Process version (-1 for latest)
        
        Returns:
            Process instance result with process_instance_key
        """
        if variables is None:
            variables = {}
        
        result = self.client.run_process(
            bpmn_process_id=bpmn_process_id,
            variables=variables,
            version=version
        )
        
        return {
            "process_instance_key": result.process_instance_key,
            "bpmn_process_id": bpmn_process_id,
            "version": result.version
        }
    
    def deploy_process(self, bpmn_file_path: str) -> Dict[str, Any]:
        """
        Deploy a BPMN process definition
        
        Args:
            bpmn_file_path: Path to BPMN file
        
        Returns:
            Deployment result
        """
        result = self.client.deploy_process(bpmn_file_path)
        
        return {
            "key": result.key,
            "processes": [p.bpmn_process_id for p in result.processes]
        }
    
    def cancel_process_instance(self, process_instance_key: int) -> None:
        """Cancel a process instance"""
        self.client.cancel_process_instance(process_instance_key)
    
    def publish_message(self, name: str, correlation_key: str, variables: Dict[str, Any] = None, 
                       time_to_live: int = 60000) -> None:
        """
        Publish a message to trigger message start events
        
        Args:
            name: Message name
            correlation_key: Correlation key
            variables: Message variables
            time_to_live: TTL in milliseconds
        """
        if variables is None:
            variables = {}
        
        self.client.publish_message(
            name=name,
            correlation_key=correlation_key,
            variables=variables,
            time_to_live=time_to_live
        )


class HotelReservationClient:
    def __init__(self, 
                 zeebe_address: str = "localhost:26500",
                 use_camunda_cloud: bool = False,
                 **cloud_kwargs):
        self.camunda = Camunda8Client(zeebe_address, use_camunda_cloud, **cloud_kwargs)
    
    def create_reservation(self, reservation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a hotel reservation through Camunda 8 process"""
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
            "process_instance_key": result.get("process_instance_key"),
            "bpmn_process_id": result.get("bpmn_process_id"),
            "status": "started"
        }
    
    def get_booking(self, booking_id: str) -> Dict[str, Any]:
        """Get booking details"""
        variables = {"booking_id": booking_id}
        result = self.camunda.start_process("BookingQueryProcess", variables)
        return {
            "process_instance_key": result.get("process_instance_key"),
            "status": "started"
        }
    
    def get_client_history(self, client_id: str) -> Dict[str, Any]:
        """Get client booking history with restaurant orders"""
        variables = {"client_id": client_id}
        result = self.camunda.start_process("ClientHistoryProcess", variables)
        return {
            "process_instance_key": result.get("process_instance_key"),
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

