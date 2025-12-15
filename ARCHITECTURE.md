# Hotel Bey SI Urbanization Architecture

## Overview

This architecture follows **SI Urbanization** principles, organizing the information system into distinct zones with clear responsibilities.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Hotel Bey Headquarters - Tunis                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌─────────────────────┐  ┌────────────────────────────┐  │
│  │ Website      │  │ Central Data        │  │ Corporate ERP Cluster      │  │
│  │ Server       │  │ Warehouse           │  │                            │  │
│  │              │  │                     │  │ ┌──────────┐ ┌──────────┐  │  │
│  │ Online       │  │ Central DB Master   │  │ │PeopleSoft│ │BillMaster│  │  │
│  │ Booking      │  │ - Guest Profiles    │  │ │Global HR │ │Central   │  │  │
│  │              │  │ - Loyalty Points    │  │ └──────────┘ └──────────┘  │  │
│  └──────────────┘  └─────────────────────┘  │ ┌────────────────────────┐ │  │
│                                              │ │ SAP Business One       │ │  │
│                                              │ │ Finance                │ │  │
│                                              │ └────────────────────────┘ │  │
│                                              └────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Hotel Bey WAN
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Local Hotel Branch - Sousse                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    End User Devices                                  │    │
│  │     ┌──────────────┐              ┌──────────────┐                  │    │
│  │     │  Front Desk  │              │  Resto POS   │                  │    │
│  │     └──────────────┘              └──────────────┘                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Local Orchestration Layer                         │    │
│  │  ┌────────────────────────────────────────────────────────────────┐ │    │
│  │  │                         LOCAL ESB                               │ │    │
│  │  │                    (WSO2 Micro Integrator)                      │ │    │
│  │  │                                                                  │ │    │
│  │  │  • API Gateway & Routing                                        │ │    │
│  │  │  • Data Transformation                                          │ │    │
│  │  │  • Sync to Central DB                                           │ │    │
│  │  │  • Push Financial Transactions to HQ                            │ │    │
│  │  └──────────────────────────┬─────────────────────────────────────┘ │    │
│  │                              │                                       │    │
│  │  ┌────────────────────────────────────────────────────────────────┐ │    │
│  │  │                       CAMUNDA 8                                 │ │    │
│  │  │                  (Zeebe Process Engine)                         │ │    │
│  │  │                                                                  │ │    │
│  │  │  • Business Process Orchestration                               │ │    │
│  │  │  • Hotel Reservation Process                                    │ │    │
│  │  │  • Client Management Process                                    │ │    │
│  │  │  • Booking Query Process                                        │ │    │
│  │  └──────────────────────────┬─────────────────────────────────────┘ │    │
│  └─────────────────────────────┼───────────────────────────────────────┘    │
│                                │                                             │
│                                ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Local App Services                                │    │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────┐   │    │
│  │  │ BeyRooms   │ │BeyComplaints│ │ BeyResto  │ │  BeyBooking    │   │    │
│  │  │ Local Room │ │   Local    │ │ Local F&B │ │    Local       │   │    │
│  │  │  :5002     │ │   :5005    │ │  :5003    │ │    :5001       │   │    │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────────┘   │    │
│  │  ┌────────────┐ ┌────────────┐                                      │    │
│  │  │ BeyClient  │ │ BeyPayment │                                      │    │
│  │  │  :5004     │ │  :5006     │                                      │    │
│  │  └────────────┘ └────────────┘                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                │                                             │
│                                ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Local Data Store                                  │    │
│  │                    ┌────────────────┐                                │    │
│  │                    │    Local DB    │                                │    │
│  │                    │                │                                │    │
│  │                    │ - Reservations │                                │    │
│  │                    │ - Tables       │                                │    │
│  │                    │ - Stay & Occ.  │                                │    │
│  │                    │ - Room Maint.  │                                │    │
│  │                    └────────────────┘                                │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Request Flow

### 1. Reservation Request Flow

```
┌───────────┐     ┌─────────┐     ┌──────────┐     ┌─────────────┐     ┌──────────┐
│Front Desk │────▶│Local ESB│────▶│ Camunda  │────▶│Job Workers  │────▶│ Services │
│           │     │         │     │ (Zeebe)  │     │             │     │          │
└───────────┘     └────┬────┘     └──────────┘     └─────────────┘     └──────────┘
                       │
                       │ Async
                       ▼
              ┌─────────────────┐
              │  Central Sync   │
              │  - Guest Data   │
              │  - Fin. Trans.  │
              └─────────────────┘
```

### 2. Component Responsibilities

| Component             | Responsibility                                   |
| --------------------- | ------------------------------------------------ |
| **Local ESB (WSO2)**  | API Gateway, Routing, Transformation, Sync to HQ |
| **Camunda 8 (Zeebe)** | Business Process Orchestration, BPMN Execution   |
| **Job Workers**       | Execute service tasks, call local microservices  |
| **Local Services**    | Domain logic (Rooms, Booking, Restaurant, etc.)  |
| **Local DB**          | Operational data storage                         |
| **Central DB**        | Master data, Guest profiles, Loyalty points      |
| **SAP Business One**  | Financial transactions, Accounting               |

## Data Flow Patterns

### Pattern 1: Process Orchestration (via Camunda)

```
ESB receives request
    │
    ├──▶ Start Camunda Process (HotelReservationProcess)
    │         │
    │         ├──▶ validate-input (Job Worker)
    │         ├──▶ search-client (Job Worker → BeyClient Service)
    │         ├──▶ create-client (Job Worker → BeyClient Service)
    │         ├──▶ check-room-availability (Job Worker → BeyRooms Service)
    │         ├──▶ block-room (Job Worker → BeyRooms Service)
    │         ├──▶ create-booking (Job Worker → BeyBooking Service)
    │         ├──▶ process-payment (Job Worker → BeyPayment Service)
    │         └──▶ generate-accounting (Job Worker → triggers ESB sync)
    │
    └──▶ ESB syncs to Central DB & SAP
```

### Pattern 2: Data Synchronization (via ESB)

```
Local Service emits event
    │
    ├──▶ ESB intercepts
    │         │
    │         ├──▶ Transform to Central DB format
    │         ├──▶ Push to Central Data Warehouse
    │         │
    │         ├──▶ Transform to SAP format
    │         └──▶ Push Financial Transaction to HQ
```

### Pattern 3: Master Data Lookup (via ESB)

```
Local Service needs loyalty points
    │
    ├──▶ ESB calls Central DB
    │         │
    │         └──▶ Returns enriched data
    │
    └──▶ Process continues with loyalty discount applied
```

## File Structure

```
urba/
├── BPMN Processes (Camunda 8)
│   ├── hotel-reservation-process.bpmn    # Main reservation workflow
│   ├── client-creation-process.bpmn      # Client management subprocess
│   ├── booking-query-process.bpmn        # Booking lookup
│   └── client-history-process.bpmn       # Client history with orders
│
├── ESB Configurations (WSO2)
│   ├── esb-camunda-integration.xml       # ESB ↔ Camunda integration
│   ├── booking-api.xml                   # Booking API routes
│   ├── hotel-service-api.xml             # Hotel service API
│   ├── client-creation-sequence.xml      # Client sequence
│   └── room-reservation-sequence.xml     # Room sequence
│
├── Camunda Integration
│   ├── camunda8_client.py                # Camunda 8 Python client
│   └── zeebe_job_worker.py               # Job workers for service tasks
│
├── Local App Services (Flask)
│   ├── services/
│   │   ├── booking_service.py            # BeyBooking (port 5001)
│   │   ├── room_service.py               # BeyRooms (port 5002)
│   │   ├── restaurant_service.py         # BeyResto (port 5003)
│   │   ├── client_service.py             # BeyClient (port 5004)
│   │   ├── payment_service.py            # BeyPayment (port 5006)
│   │   └── accounting_service.py         # Accounting (port 5007)
│
└── Documentation
    ├── ARCHITECTURE.md                   # This file
    ├── ORCHESTRATION.md                  # Camunda orchestration details
    └── README_CAMUNDA8.md                # Camunda 8 setup
```

## Why ESB + Camunda?

### ESB Strengths (WSO2)
- Protocol mediation (REST, SOAP, JMS)
- Data transformation (JSON ↔ XML ↔ SAP format)
- Routing and load balancing
- Integration with legacy systems (SAP, PeopleSoft)
- Message queuing and async patterns

### Camunda Strengths (Zeebe)
- Visual process modeling (BPMN)
- Long-running process support
- Process monitoring and analytics
- Human task management
- Process versioning and deployment

### Combined Benefits
- **Clear separation**: ESB handles integration, Camunda handles orchestration
- **Flexibility**: Change process logic without touching integration
- **Visibility**: Full audit trail of business processes
- **Scalability**: Each layer scales independently
- **Resilience**: Process state persists across failures

## Deployment

### Local Branch (Sousse)

1. **WSO2 Micro Integrator** (ESB)
   - Port: 8280 (HTTP), 8243 (HTTPS)
   - Deploys: `*.xml` ESB configurations

2. **Camunda 8 / Zeebe**
   - Port: 26500 (gRPC), 8080 (REST)
   - Deploys: `*.bpmn` process definitions

3. **Job Workers**
   - Python async workers
   - Connect to Zeebe on port 26500

4. **Local Services**
   - Ports: 5001-5007
   - Flask microservices

5. **Local Database**
   - PostgreSQL or MySQL
   - Stores operational data

### HQ (Tunis)

1. **Central Data Warehouse**
   - Master guest profiles
   - Aggregated analytics

2. **SAP Business One**
   - Financial transactions
   - Accounting integration

3. **PeopleSoft**
   - HR management
   - Global employee data

