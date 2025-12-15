#!/usr/bin/env python3
"""
Hotel Bey - Full SI Urbanization Demo
======================================
Demonstrates the complete ESB + Camunda 8 architecture.

This script:
1. Starts all Flask microservices
2. Starts the Zeebe job worker
3. Sends a reservation request
4. Monitors the process in real-time
5. Shows the complete flow through all BPMN steps
"""

import subprocess
import sys
import time
import requests
import json
import threading
import os
from datetime import datetime

# Configuration
CAMUNDA_URL = "http://localhost:8080"
SERVICES = [
    {"name": "BeyBooking", "port": 5001, "file": "services/booking_service.py"},
    {"name": "BeyRooms", "port": 5002, "file": "services/room_service.py"},
    {"name": "BeyResto", "port": 5003, "file": "services/restaurant_service.py"},
    {"name": "BeyClient", "port": 5004, "file": "services/client_service.py"},
    {"name": "BeyPayment", "port": 5005, "file": "services/payment_service.py"},
    {"name": "BeyAccounting", "port": 5006, "file": "services/accounting_service.py"},
]

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}{Colors.END}\n")

def print_step(step_num, text, status=""):
    status_color = Colors.GREEN if status == "OK" else Colors.YELLOW if status == "RUNNING" else Colors.CYAN
    status_text = f" [{status}]" if status else ""
    print(f"{Colors.BOLD}[{step_num}]{Colors.END} {text}{status_color}{status_text}{Colors.END}")

def print_flow(text):
    print(f"    {Colors.CYAN}→{Colors.END} {text}")

def print_success(text):
    print(f"\n{Colors.GREEN}{Colors.BOLD}✓ {text}{Colors.END}")

def print_error(text):
    print(f"\n{Colors.RED}{Colors.BOLD}✗ {text}{Colors.END}")

def check_camunda():
    """Check if Camunda 8 is running"""
    try:
        response = requests.get(f"{CAMUNDA_URL}/v2/topology", timeout=5)
        return response.status_code == 200
    except:
        return False

def check_service(port):
    """Check if a service is running on a port"""
    try:
        response = requests.get(f"http://localhost:{port}/", timeout=2)
        return True
    except:
        try:
            # Try a common health endpoint
            response = requests.get(f"http://localhost:{port}/api/health", timeout=2)
            return True
        except:
            return False

def start_service(service, processes):
    """Start a Flask service"""
    if check_service(service["port"]):
        print_flow(f"{service['name']} already running on :{service['port']}")
        return None
    
    print_flow(f"Starting {service['name']} on :{service['port']}...")
    
    # Start the service in a subprocess
    proc = subprocess.Popen(
        [sys.executable, service["file"]],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    processes.append(proc)
    time.sleep(0.5)
    return proc

def start_job_worker(processes):
    """Start the Zeebe job worker"""
    print_flow("Starting Zeebe Job Worker...")
    
    proc = subprocess.Popen(
        [sys.executable, "zeebe_job_worker.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=os.path.dirname(os.path.abspath(__file__)),
        text=True,
        bufsize=1
    )
    processes.append(proc)
    return proc

def monitor_worker_output(proc, output_lines):
    """Monitor job worker output in a separate thread"""
    try:
        for line in iter(proc.stdout.readline, ''):
            if line:
                output_lines.append(line.strip())
    except:
        pass

def get_process_status(process_key):
    """Get the status of a process instance"""
    try:
        # Query for the process instance
        response = requests.post(
            f"{CAMUNDA_URL}/v2/process-instances/search",
            json={"filter": {"processInstanceKey": process_key}},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("items"):
                return data["items"][0]
    except Exception as e:
        pass
    return None

def wait_for_completion(process_key: int, timeout_sec: int = 60) -> str:
    """
    Poll Camunda 8 for this process instance and return its final state.
    Returns one of: 'COMPLETED', 'ACTIVE', 'TERMINATED', 'FAILED', or 'UNKNOWN'.
    """
    end = time.time() + timeout_sec
    last_state = "UNKNOWN"

    while time.time() < end:
        try:
            resp = requests.post(
                f"{CAMUNDA_URL}/v2/process-instances/search",
                json={"filter": {"processInstanceKey": process_key}},
                headers={"Content-Type": "application/json"},
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items") or []
                if items:
                    last_state = items[0].get("state", last_state)
                    if last_state in ("COMPLETED", "TERMINATED", "FAILED"):
                        return last_state
        except Exception:
            pass

        time.sleep(1)

    return last_state

def run_demo():
    """Run the full demo"""
    processes = []
    worker_output = []
    
    try:
        print_header("HOTEL BEY - SI URBANIZATION DEMO")
        print(f"  Branch: Sousse")
        print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Architecture: ESB (WSO2) + Camunda 8 (Zeebe)")
        
        # Step 1: Check Camunda
        print_header("STEP 1: Checking Camunda 8 (Zeebe)")
        if not check_camunda():
            print_error("Camunda 8 is not running!")
            print("\nPlease start Camunda 8 first:")
            print("  docker run -p 8080:8080 -p 26500:26500 camunda/camunda:latest")
            print("\nOr use Camunda Desktop Modeler with embedded Zeebe.")
            return
        print_success("Camunda 8 is running")
        
        # Step 2: Start services
        print_header("STEP 2: Starting Local App Services")
        for service in SERVICES:
            start_service(service, processes)
        time.sleep(2)
        print_success("All services started")
        
        # Step 3: Start job worker
        print_header("STEP 3: Starting Zeebe Job Worker")
        worker_proc = start_job_worker(processes)
        
        # Start monitoring worker output in background
        monitor_thread = threading.Thread(
            target=monitor_worker_output, 
            args=(worker_proc, worker_output),
            daemon=True
        )
        monitor_thread.start()
        time.sleep(3)
        print_success("Job Worker started")
        
        # Step 4: Create reservation
        print_header("STEP 4: Creating Reservation Request")
        
        reservation = {
            "first_name": "Jean",
            "last_name": "Dubois",
            "email": "jean.dubois@hotelbey.com",
            "phone": "+216 71 234 567",
            "check_in": "2024-01-15",
            "check_out": "2024-01-18",
            "guests": 2,
            "room_type": "standard"
        }
        
        print(f"  Guest: {reservation['first_name']} {reservation['last_name']}")
        print(f"  Email: {reservation['email']}")
        print(f"  Check-in: {reservation['check_in']}")
        print(f"  Check-out: {reservation['check_out']}")
        print(f"  Guests: {reservation['guests']}")
        print(f"  Room Type: {reservation['room_type']}")
        
        # Start the process
        print_header("STEP 5: Starting BPMN Process")
        
        # Camunda 8 REST API v2 - simple key-value variables
        variables = {
            "first_name": reservation["first_name"],
            "last_name": reservation["last_name"],
            "email": reservation["email"],
            "phone": reservation["phone"],
            "check_in": reservation["check_in"],
            "check_out": reservation["check_out"],
            "guests": reservation["guests"],
            "room_type": reservation["room_type"]
        }
        
        try:
            response = requests.post(
                f"{CAMUNDA_URL}/v2/process-instances",
                json={
                    "processDefinitionId": "HotelReservationProcess",
                    "variables": variables
                },
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code not in [200, 201]:
                print_error(f"Failed to start process: {response.text}")
                return
            
            result = response.json()
            process_key = result.get("processInstanceKey")
            print_success(f"Process started: {process_key}")
            
        except Exception as e:
            print_error(f"Failed to start process: {e}")
            return
        
        # Step 6: Monitor execution
        print_header("STEP 6: Monitoring Process Execution")
        print("  Watching job worker output...\n")
        
        steps = [
            ("validate-input", "Validating reservation input"),
            ("search-client", "Searching for existing client"),
            ("create-client", "Creating new client (if needed)"),
            ("check-room-availability", "Checking room availability"),
            ("block-room", "Blocking selected room"),
            ("create-booking", "Creating booking record"),
            ("process-payment", "Processing payment"),
            ("generate-accounting", "Generating invoice"),
        ]
        
        completed_steps = set()
        timeout = 60
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check worker output for completed steps
            for line in worker_output:
                for step_id, step_name in steps:
                    if step_id in line.lower() and step_id not in completed_steps:
                        completed_steps.add(step_id)
                        status = "✓" if ">>>" in line or "complete" in line.lower() else "→"
                        print(f"  {Colors.GREEN}{status}{Colors.END} {step_name}")
                        
                        # Show special messages
                        if "BOOKING CONFIRMED" in line:
                            booking_id = line.split("ID")[-1].strip().replace("<<<", "").strip()
                            print(f"    {Colors.CYAN}Booking ID: {booking_id}{Colors.END}")
                        if "PAYMENT SUCCESS" in line:
                            print(f"    {Colors.CYAN}Payment processed successfully{Colors.END}")
                        if "INVOICE GENERATED" in line:
                            print(f"    {Colors.CYAN}Invoice generated{Colors.END}")
                        if "ESB SYNC" in line:
                            print(f"    {Colors.CYAN}Synced to HQ{Colors.END}")
            
            # Check if process completed
            if len(completed_steps) >= len(steps) - 2:  # Allow some flexibility
                break
            
            time.sleep(1)
        
        # Step 7: Ask the engine for the real final state
        print_header("STEP 7: Checking Engine State")
        final_state = wait_for_completion(process_key, timeout_sec=60)
        print(f"  Final engine state: {final_state}")

        if final_state != "COMPLETED":
            print_error("Process did not complete successfully.")
            print("  Check Camunda Operate for incidents and worker logs for errors.")
            # Do not print a fake confirmation banner
            return

        # Only now is it safe to say the reservation is confirmed
        print_header("RESERVATION COMPLETED")
        print(f"  Guest: {reservation['first_name']} {reservation['last_name']}")
        print(f"  Email: {reservation['email']}")
        print(f"  Check-in: {reservation['check_in']}")
        print(f"  Check-out: {reservation['check_out']}")
        print(f"  Room Type: {reservation['room_type']}")
        
        # Show architecture flow (executed for a real completed instance)
        print_header("ARCHITECTURE FLOW EXECUTED")
        print(f"""
  {Colors.CYAN}┌─────────────┐     ┌─────────────┐     ┌─────────────┐
  │  Front Desk │ ──▶ │  Camunda 8  │ ──▶ │ Job Workers │
  └─────────────┘     └─────────────┘     └──────┬──────┘
                                                  │
        ┌─────────────────────────────────────────┤
        │                                         │
        ▼                                         ▼
  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
  │  BeyClient  │  │  BeyRooms   │  │ BeyBooking  │  │ BeyPayment  │
  │    :5004    │  │    :5002    │  │    :5001    │  │    :5005    │
  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
                                                  │
                                                  ▼
                                          ┌─────────────┐
                                          │  ESB Sync   │
                                          │  → HQ Tunis │
                                          └─────────────┘{Colors.END}
        """)
        
        print_success("Demo completed successfully!")
        print(f"\n  Process Key: {process_key}")
        print(f"  Monitor in Camunda Operate: {CAMUNDA_URL}")
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    finally:
        # Cleanup
        print("\n" + "-" * 70)
        print("Cleaning up...")
        for proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except:
                try:
                    proc.kill()
                except:
                    pass
        print("Done.")


if __name__ == "__main__":
    run_demo()

