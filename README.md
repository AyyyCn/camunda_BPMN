# Hotel Bey - SI Urbanization Demo

A complete demonstration of **ESB + Camunda 8** architecture for hotel reservation management.

## Architecture

```
Front Desk → Local ESB (WSO2) → Camunda 8 (Zeebe) → Job Workers → Microservices
                    ↓
              HQ Sync (SAP)
```

## Quick Start

### Prerequisites

1. **Python 3.8+** with pip
2. **Camunda 8** running locally

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Start Camunda 8

Option A - Docker:
```bash
docker run -d --name camunda8 -p 8080:8080 -p 26500:26500 camunda/camunda:latest
```

Option B - Camunda Desktop Modeler with embedded Zeebe

### Step 3: Deploy BPMN Processes

Using Camunda Modeler or Web UI, deploy:
- `hotel-reservation-process.bpmn`
- `client-creation-process.bpmn`
- `booking-query-process.bpmn`
- `client-history-process.bpmn`

### Step 4: Run the Demo

**Option A - Full Demo (automated)**
```bash
python run_demo.py
```

**Option B - Manual (3 terminals)**

Terminal 1 - Start services:
```bash
python start_services.py
```

Terminal 2 - Start job worker:
```bash
python start_worker.py
```

Terminal 3 - Send test request:
```bash
python quick_test.py
```

## Project Structure

```
urba/
├── BPMN Processes
│   ├── hotel-reservation-process.bpmn   # Main workflow
│   ├── client-creation-process.bpmn     # Client subprocess
│   ├── booking-query-process.bpmn       # Query process
│   └── client-history-process.bpmn      # History process
│
├── ESB Configuration (WSO2)
│   ├── esb-camunda-integration.xml      # ESB ↔ Camunda
│   ├── booking-api.xml
│   └── hotel-service-api.xml
│
├── Camunda Integration
│   ├── zeebe_job_worker.py              # Job workers
│   └── camunda8_client.py               # Python client
│
├── Microservices
│   └── services/
│       ├── booking_service.py           # :5001
│       ├── room_service.py              # :5002
│       ├── restaurant_service.py        # :5003
│       ├── client_service.py            # :5004
│       ├── payment_service.py           # :5005
│       └── accounting_service.py        # :5006
│
├── Demo Scripts
│   ├── run_demo.py                      # Full automated demo
│   ├── start_services.py                # Start all services
│   ├── start_worker.py                  # Start job worker
│   └── quick_test.py                    # Quick test
│
└── Documentation
    ├── README.md                        # This file
    ├── ARCHITECTURE.md                  # Architecture details
    └── ORCHESTRATION.md                 # Orchestration patterns
```

## Process Flow

1. **Validate Input** - Check required fields
2. **Search Client** - Look up by email
3. **Create Client** - If not found, create new
4. **Check Availability** - Find available rooms
5. **Block Room** - Reserve the room
6. **Create Booking** - Generate booking record
7. **Process Payment** - Charge the guest
8. **Generate Invoice** - Create accounting entry
9. **Sync to HQ** - Push to central systems

## Ports

| Service | Port |
|---------|------|
| Camunda 8 REST | 8080 |
| Zeebe gRPC | 26500 |
| ESB (WSO2) | 8280 |
| BeyBooking | 5001 |
| BeyRooms | 5002 |
| BeyResto | 5003 |
| BeyClient | 5004 |
| BeyPayment | 5005 |
| BeyAccounting | 5006 |

## License

Educational / Demo project for SI Urbanization studies.

