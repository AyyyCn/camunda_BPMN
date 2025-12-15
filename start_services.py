#!/usr/bin/env python3
"""
Start all Hotel Bey services for development/testing.
Run this before running the demo.
"""

import subprocess
import sys
import time
import os

SERVICES = [
    ("BeyBooking", 5001, "services/booking_service.py"),
    ("BeyRooms", 5002, "services/room_service.py"),
    ("BeyResto", 5003, "services/restaurant_service.py"),
    ("BeyClient", 5004, "services/client_service.py"),
    ("BeyPayment", 5005, "services/payment_service.py"),
    ("BeyAccounting", 5006, "services/accounting_service.py"),
]

def main():
    print("=" * 60)
    print("  HOTEL BEY - Starting All Services")
    print("=" * 60)
    
    processes = []
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    for name, port, file in SERVICES:
        print(f"  Starting {name} on port {port}...")
        proc = subprocess.Popen(
            [sys.executable, file],
            cwd=base_dir
        )
        processes.append((name, proc))
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print("  All services started!")
    print("=" * 60)
    print("\nServices running:")
    for name, port, _ in SERVICES:
        print(f"  - {name}: http://localhost:{port}")
    
    print("\nPress Ctrl+C to stop all services...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping services...")
        for name, proc in processes:
            proc.terminate()
        print("Done.")

if __name__ == "__main__":
    main()

