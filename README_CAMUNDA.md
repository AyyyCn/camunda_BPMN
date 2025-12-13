# Camunda BPMN Process Definitions

This project has been migrated from WSO2 ESB orchestration to Camunda BPMN processes.

## Architecture Overview

The hotel reservation system now uses Camunda for process orchestration instead of WSO2 ESB. The microservices (Flask) remain unchanged and are integrated via Camunda External Tasks.

### Process Flow

```
Client Request → Camunda Process → External Tasks → Flask Microservices
```

> **📖 For detailed orchestration explanation, see [ORCHESTRATION.md](ORCHESTRATION.md)**

## BPMN Process Definitions

### 1. Hotel Reservation Process (`hotel-reservation-process.bpmn`)
Main process that orchestrates the complete reservation flow:
- Validates input
- Creates or finds client (calls subprocess)
- Checks room availability
- Blocks room
- Creates booking

### 2. Client Creation Process (`client-creation-process.bpmn`)
Subprocess for client management:
- Searches for existing client by email
- Creates new client if not found

### 3. Booking Query Process (`booking-query-process.bpmn`)
Simple process to query booking details

### 4. Client History Process (`client-history-process.bpmn`)
Process to retrieve client booking history with restaurant orders

## Setup Instructions

### Prerequisites
- Camunda Platform (Community or Enterprise)
- Python 3.7+
- Flask services running on ports 5001-5004

### 1. Deploy BPMN Processes to Camunda

Deploy the BPMN files to your Camunda instance:
- Via Camunda Modeler: Open and deploy each `.bpmn` file
- Via REST API: POST to `/engine-rest/deployment/create`
- Via Camunda Cockpit: Upload through the UI

### 2. Start Flask Microservices

```bash
# Terminal 1 - Booking Service
cd services
python booking_service.py

# Terminal 2 - Room Service
python room_service.py

# Terminal 3 - Client Service
python client_service.py

# Terminal 4 - Restaurant Service
python restaurant_service.py
```

### 3. Start External Task Worker

The external task worker polls Camunda for tasks and executes them by calling the Flask services:

```bash
python external_task_worker.py
```

### 4. Test the System

```bash
python test_client.py
```

Or use the Camunda client directly:

```python
from camunda_client import HotelReservationClient

client = HotelReservationClient()
result = client.create_reservation({
    "first_name": "Jean",
    "last_name": "Dubois",
    "email": "jean.dubois@email.com",
    "phone": "+33123456789",
    "check_in": "2024-01-15",
    "check_out": "2024-01-18",
    "guests": 2,
    "room_type": "standard"
})
```

## External Task Topics

The following topics are used for external tasks:

- `validate-input` - Validate reservation input
- `search-client` - Search for existing client
- `create-client` - Create new client
- `check-room-availability` - Check available rooms
- `block-room` - Block a room for booking
- `create-booking` - Create booking record
- `get-booking` - Get booking details
- `get-client-bookings` - Get all bookings for a client
- `get-restaurant-orders` - Get restaurant orders for a booking

## Monitoring

Use Camunda Cockpit to monitor:
- Active process instances
- Process execution history
- Failed tasks and incidents
- Process performance metrics

Access at: `http://localhost:8080/camunda/app/cockpit/`

## Migration from WSO2 ESB

### Key Differences

1. **Orchestration**: WSO2 ESB XML sequences → Camunda BPMN processes
2. **Service Calls**: ESB HTTP calls → Camunda External Tasks
3. **Error Handling**: ESB error sequences → Camunda error events and boundary events
4. **Monitoring**: ESB logs → Camunda Cockpit

### Benefits

- Visual process modeling with BPMN
- Built-in process monitoring and analytics
- Process versioning and deployment management
- Better error handling and retry mechanisms
- Support for human tasks and manual steps
- Process history and audit trail

## Configuration

Update these URLs in the code if your services run on different ports:

- `camunda_client.py`: Camunda REST API URL (default: `http://localhost:8080/engine-rest`)
- `external_task_worker.py`: Flask services base URL (default: `http://localhost`)

