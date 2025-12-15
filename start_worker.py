#!/usr/bin/env python3
"""
Start the Zeebe Job Worker.
This connects to Camunda 8 and handles all BPMN service tasks.
"""

import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from zeebe_job_worker import HotelServiceWorker

def main():
    print("=" * 60)
    print("  HOTEL BEY - Zeebe Job Worker")
    print("=" * 60)
    print("\nConnecting to Camunda 8 (Zeebe) at localhost:26500...")
    print("Make sure Camunda 8 is running!\n")
    
    worker = HotelServiceWorker(
        zeebe_address="localhost:26500",
        services_base_url="http://localhost"
    )
    
    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        print("\nWorker stopped.")
    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure:")
        print("  1. Camunda 8 is running on localhost:8080")
        print("  2. Zeebe broker is available on localhost:26500")
        print("  3. BPMN processes are deployed")

if __name__ == "__main__":
    main()

