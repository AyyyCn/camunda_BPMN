# Orchestration in Camunda

## Overview

This system uses **Camunda as the Orchestrator** with an **External Task Pattern**. Camunda manages the process flow, while external workers execute the actual business logic by calling microservices.

## Architecture Pattern

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ Start Process
       ▼
┌─────────────────────────────────┐
│      Camunda Engine             │
│  (Process Orchestrator)         │
│                                 │
│  ┌───────────────────────────┐ │
│  │  BPMN Process Instance     │ │
│  │  - Manages flow           │ │
│  │  - Stores variables       │ │
│  │  - Tracks state           │ │
│  └───────────────────────────┘ │
└──────┬─────────────────────────┘
       │ Creates External Tasks
       │ (when service task reached)
       ▼
┌─────────────────────────────────┐
│   External Task Queue           │
│  (in Camunda Database)          │
└──────┬─────────────────────────┘
       │ Worker polls & locks
       ▼
┌─────────────────────────────────┐
│   External Task Worker          │
│  (Python - Polling Loop)        │
│                                 │
│  1. Poll for tasks              │
│  2. Lock task                   │
│  3. Execute handler              │
│  4. Call Flask microservice     │
│  5. Complete task with result   │
└──────┬─────────────────────────┘
       │ HTTP Request
       ▼
┌─────────────────────────────────┐
│   Flask Microservices          │
│  - Booking Service (5001)       │
│  - Room Service (5002)          │
│  - Restaurant Service (5003)    │
│  - Client Service (5004)        │
└─────────────────────────────────┘
```

## How Orchestration Works

### 1. Process Start

When a client starts a reservation:

```python
# Client calls Camunda REST API
client = HotelReservationClient()
result = client.create_reservation({
    "first_name": "Jean",
    "email": "jean@example.com",
    # ... other fields
})
```

**What happens:**
1. Camunda creates a new process instance
2. Process variables are stored in Camunda database
3. Process execution starts at the start event
4. Engine moves to first service task

### 2. External Task Creation

When the process reaches a service task (e.g., "Validate Input"):

```xml
<bpmn:serviceTask id="Task_ValidateInput" 
                 camunda:type="external" 
                 camunda:topic="validate-input">
```

**What happens:**
1. Camunda creates an external task record in the database
2. Task is associated with the process instance
3. Task contains all process variables
4. Task waits in the queue for a worker

### 3. Worker Polling (Pull Pattern)

The external task worker continuously polls Camunda:

```python
def run(self, interval: int = 5):
    while self.running:
        for topic in ["validate-input", "search-client", ...]:
            # Poll Camunda for tasks
            tasks = self.camunda.fetch_and_lock_external_tasks(topic, max_tasks=1)
            for task in tasks:
                self.process_task(task)
        time.sleep(interval)
```

**What happens:**
1. Worker sends `POST /external-task/fetchAndLock` to Camunda
2. Camunda returns available tasks for that topic
3. Tasks are **locked** (prevented from being picked by other workers)
4. Lock duration: 60 seconds (configurable)
5. Worker receives task with all process variables

### 4. Task Execution

Worker processes the task:

```python
def process_task(self, task: Dict[str, Any]):
    topic = task.get("topicName")  # e.g., "validate-input"
    task_id = task.get("id")
    variables = task.get("variables")  # All process variables
    
    # Route to appropriate handler
    handler = handlers.get(topic)
    result = handler(task)  # Execute business logic
    
    # Call Flask microservice
    response = requests.post("http://localhost:5001/api/booking/create", ...)
    
    # Complete task with result
    self.camunda.complete_external_task(task_id, result)
```

**What happens:**
1. Worker extracts variables from task
2. Calls appropriate handler function
3. Handler makes HTTP request to Flask microservice
4. Handler processes response
5. Worker completes task with result variables

### 5. Process Continuation

When task is completed:

```python
# Worker sends completion
POST /external-task/{task_id}/complete
{
    "workerId": "python-worker",
    "variables": {
        "client_id": {"value": "123", "type": "String"},
        "roomAvailable": {"value": true, "type": "Boolean"}
    }
}
```

**What happens:**
1. Camunda receives task completion
2. Result variables are merged into process instance variables
3. Process execution continues to next step
4. If gateway: evaluates condition using variables
5. If next service task: creates new external task

## Variable Flow

Variables flow through the process automatically:

```
Start Process
  ↓
Variables: {first_name, last_name, email, ...}
  ↓
Validate Input (external task)
  ↓
Variables: {first_name, last_name, email, ..., valid: true}
  ↓
Create Client (subprocess)
  ↓
Variables: {first_name, last_name, email, ..., client_id: "abc123"}
  ↓
Check Room Availability (external task)
  ↓
Variables: {..., client_id, roomAvailable: true, selected_room_id: "101"}
  ↓
Block Room (external task)
  ↓
Variables: {..., room_id: "101", room_blocked: true}
  ↓
Create Booking (external task)
  ↓
Variables: {..., booking_id: "xyz789", status: "confirmed"}
```

**Key Points:**
- All variables are stored in Camunda database
- Variables are passed to external tasks automatically
- Task completion returns new/updated variables
- Variables persist across process execution

## Subprocess Orchestration

The call activity (`ClientCreationProcess`) works similarly:

```xml
<bpmn:callActivity id="SubProcess_CreateClient" 
                  calledElement="ClientCreationProcess">
```

**What happens:**
1. Main process creates subprocess instance
2. All process variables are copied to subprocess
3. Subprocess executes independently
4. Subprocess creates its own external tasks
5. When subprocess completes, variables are merged back
6. Main process continues

## Error Handling

### Task-Level Errors

```python
try:
    result = handler(task)
    self.camunda.complete_external_task(task_id, result)
except Exception as e:
    # Report BPMN error
    self.camunda.handle_bpmn_error(task_id, "TASK_ERROR", str(e))
```

**What happens:**
1. Error is caught in worker
2. BPMN error is reported to Camunda
3. Process triggers boundary error event (if configured)
4. Process can continue or end with error

### Process-Level Errors

```xml
<bpmn:boundaryEvent id="BoundaryEvent_Error" 
                    attachedToRef="Task_ValidateInput">
    <bpmn:errorEventDefinition />
</bpmn:boundaryEvent>
```

**What happens:**
1. Error event is triggered
2. Process flow diverts to error path
3. Process ends with error end event
4. Error is logged in Camunda

## State Management

Camunda manages all process state:

- **Process Instance State**: Active, Completed, Terminated
- **Task State**: Created, Locked, Completed, Failed
- **Variable State**: Stored in database, versioned
- **Execution State**: Which step the process is on

**Benefits:**
- Process can be paused/resumed
- State survives worker restarts
- Full audit trail
- Can query state via REST API

## Polling vs Push

This system uses **Polling (Pull Pattern)**:

**Advantages:**
- Simple to implement
- Worker controls when to fetch
- No need for message broker
- Easy to scale workers

**Alternative: Push Pattern:**
- Camunda sends webhooks/events
- Requires message broker (RabbitMQ, Kafka)
- More complex setup
- Better for high-throughput

## Scaling Workers

Multiple workers can run simultaneously:

```
Worker 1 ──┐
           ├──> Camunda Engine ──> External Task Queue
Worker 2 ──┘
           │
Worker 3 ──┘
```

**How it works:**
1. Each worker polls independently
2. Camunda locks tasks when fetched
3. Only one worker can process a task
4. Lock prevents duplicate processing
5. If worker crashes, lock expires and task becomes available again

## Monitoring Orchestration

### Camunda Cockpit

View:
- Active process instances
- Current execution state
- Process variables
- External tasks (pending/completed)
- Error incidents

### REST API Queries

```python
# Get all active process instances
GET /process-instance?processDefinitionKey=HotelReservationProcess

# Get external tasks
GET /external-task?topicName=validate-input&locked=false

# Get process variables
GET /process-instance/{id}/variables
```

## Comparison: ESB vs Camunda Orchestration

### WSO2 ESB (Previous)
- **Push-based**: ESB actively calls services
- **Synchronous**: Waits for response
- **No state persistence**: State in memory
- **Limited monitoring**: Logs only

### Camunda (Current)
- **Pull-based**: Workers poll for tasks
- **Asynchronous**: Tasks can wait
- **State persistence**: Database-backed
- **Rich monitoring**: Cockpit, REST API, metrics

## Best Practices

1. **Idempotent Handlers**: Make handlers safe to retry
2. **Lock Duration**: Set appropriate lock timeouts
3. **Error Handling**: Always handle errors gracefully
4. **Variable Naming**: Use consistent variable names
5. **Topic Naming**: Use descriptive topic names
6. **Worker Scaling**: Run multiple workers for high load
7. **Monitoring**: Monitor task completion times
8. **Retry Logic**: Implement retries in workers if needed

## Summary

**Orchestration Flow:**
1. Client → Starts process in Camunda
2. Camunda → Creates external tasks
3. Worker → Polls and locks tasks
4. Worker → Executes business logic (calls microservices)
5. Worker → Completes task with results
6. Camunda → Continues process with updated variables
7. Repeat steps 2-6 until process completes

**Key Benefits:**
- Decoupled: Microservices don't know about Camunda
- Resilient: State persists, can recover from failures
- Observable: Full visibility into process execution
- Scalable: Add more workers as needed
- Flexible: Easy to change process flow



