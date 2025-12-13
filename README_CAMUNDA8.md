# Camunda 8 Migration Guide

This project has been upgraded from Camunda 7 to **Camunda 8** (Zeebe).

## Key Changes

### Architecture

**Camunda 7:**
- REST API based (`/engine-rest`)
- External Task polling pattern
- Synchronous task completion

**Camunda 8 (Zeebe):**
- gRPC based (Zeebe broker on port 26500)
- Job worker pattern (push-based)
- Asynchronous job handling

### BPMN Changes

Service tasks now use Zeebe task definitions:

**Before (Camunda 7):**
```xml
<bpmn:serviceTask camunda:type="external" camunda:topic="validate-input">
```

**After (Camunda 8):**
```xml
<bpmn:serviceTask>
  <bpmn:extensionElements>
    <zeebe:taskDefinition type="validate-input" />
  </bpmn:extensionElements>
</bpmn:serviceTask>
```

## Setup Instructions

### Prerequisites

1. **Install Camunda 8**
   - Download from: https://camunda.com/download/
   - Or use Docker: `docker run -p 26500:26500 camunda/zeebe:latest`
   - Or use Camunda Cloud (SaaS)

2. **Install Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### 1. Deploy BPMN Processes

Deploy processes to Zeebe using the client:

```python
from camunda8_client import Camunda8Client

client = Camunda8Client()
client.deploy_process("hotel-reservation-process.bpmn")
client.deploy_process("client-creation-process.bpmn")
client.deploy_process("booking-query-process.bpmn")
client.deploy_process("client-history-process.bpmn")
```

Or use Zeebe CLI:
```bash
zbctl deploy hotel-reservation-process.bpmn
```

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

### 3. Start Zeebe Job Worker

The job worker connects to Zeebe and handles jobs:

```bash
python zeebe_job_worker.py
```

**What happens:**
- Worker connects to Zeebe broker (gRPC)
- Registers handlers for each task type
- Zeebe pushes jobs to worker when available
- Worker executes handler and completes job

### 4. Test the System

```bash
python test_client.py
```

## Code Changes

### Client Code

**Before (Camunda 7):**
```python
from camunda_client import HotelReservationClient
client = HotelReservationClient("http://localhost:8080/engine-rest")
```

**After (Camunda 8):**
```python
from camunda8_client import HotelReservationClient
client = HotelReservationClient("localhost:26500")  # Zeebe broker address
```

### Worker Code

**Before (Camunda 7):**
- Polling loop: `fetch_and_lock_external_tasks()`
- Manual task completion: `complete_external_task()`

**After (Camunda 8):**
- Decorator-based handlers: `@worker.task(task_type="...")`
- Automatic job completion
- Async/await pattern

## Camunda Cloud Setup

To use Camunda Cloud instead of self-hosted Zeebe:

```python
from camunda8_client import HotelReservationClient

client = HotelReservationClient(
    use_camunda_cloud=True,
    camunda_cloud_client_id="your-client-id",
    camunda_cloud_client_secret="your-secret",
    camunda_cloud_cluster_id="your-cluster-id",
    camunda_cloud_region="your-region"
)
```

## Monitoring

### Camunda Operate

Access Camunda Operate UI:
- Self-hosted: `http://localhost:8081` (if running Operate)
- Camunda Cloud: Provided in your cluster details

View:
- Process instances
- Job status
- Process variables
- Execution history

### Zeebe CLI

```bash
# List process instances
zbctl status

# View process instance
zbctl get process-instance <key>

# View jobs
zbctl get jobs
```

## Key Differences Summary

| Feature | Camunda 7 | Camunda 8 (Zeebe) |
|---------|-----------|-------------------|
| **API** | REST (HTTP) | gRPC |
| **Port** | 8080 | 26500 |
| **Tasks** | External Tasks | Jobs |
| **Pattern** | Polling (Pull) | Push (Job Workers) |
| **Client** | `camunda_client.py` | `camunda8_client.py` |
| **Worker** | `external_task_worker.py` | `zeebe_job_worker.py` |
| **BPMN** | `camunda:type="external"` | `zeebe:taskDefinition` |

## Migration Checklist

- [x] Updated BPMN files with Zeebe task definitions
- [x] Created Camunda 8 client (`camunda8_client.py`)
- [x] Created Zeebe job worker (`zeebe_job_worker.py`)
- [x] Updated test client
- [x] Updated requirements.txt
- [ ] Deploy processes to Zeebe
- [ ] Test all process flows
- [ ] Update monitoring dashboards

## Troubleshooting

### Worker Not Receiving Jobs

1. Check Zeebe broker is running: `zbctl status`
2. Verify processes are deployed
3. Check worker logs for connection errors
4. Ensure task types match between BPMN and worker

### Process Not Starting

1. Verify process is deployed: `zbctl get process`
2. Check process ID matches in client code
3. Verify variables are correctly formatted

### Connection Issues

1. Check Zeebe broker address (default: `localhost:26500`)
2. For Camunda Cloud, verify credentials
3. Check firewall/network settings

## Additional Resources

- [Camunda 8 Documentation](https://docs.camunda.io/)
- [Zeebe Python Client](https://github.com/camunda-community-hub/pyzeebe)
- [Zeebe Documentation](https://docs.camunda.io/docs/components/zeebe/)


