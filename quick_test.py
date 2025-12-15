#!/usr/bin/env python3
"""
Quick test - sends a reservation request to Camunda.
Use this to test if everything is working.

Prerequisites:
1. Camunda 8 running on localhost:8080
2. BPMN processes deployed
3. Job worker running (python start_worker.py)
4. Services running (python start_services.py)
"""

import requests
import json
import sys

CAMUNDA_URL = "http://localhost:8080"

def main():
    print("\n" + "=" * 60)
    print("  HOTEL BEY - Quick Test")
    print("=" * 60)
    
    # Check Camunda
    print("\n[1] Checking Camunda 8...")
    try:
        r = requests.get(f"{CAMUNDA_URL}/v2/topology", timeout=5)
        if r.status_code == 200:
            print("    ✓ Camunda 8 is running")
        else:
            print("    ✗ Camunda 8 returned error")
            return
    except:
        print("    ✗ Camunda 8 is not running!")
        print("    Start Camunda 8 first.")
        return
    
    # Send reservation
    print("\n[2] Sending reservation request...")
    
    # Camunda 8 REST API v2 format - simple key-value variables
    variables = {
        "first_name": "Test",
        "last_name": "User",
        "email": "test@hotel.com",
        "phone": "+216123456",
        "check_in": "2024-02-01",
        "check_out": "2024-02-03",
        "guests": 1,
        "room_type": "standard"
    }
    
    try:
        # Camunda 8 REST API v2 format
        response = requests.post(
            f"{CAMUNDA_URL}/v2/process-instances",
            json={
                "processDefinitionId": "HotelReservationProcess",
                "variables": variables
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            print("    ✓ Process started!")
            print(f"\n    Process Key: {result.get('processInstanceKey')}")
            print(f"    Process ID:  HotelReservationProcess")
            print("\n    Check job worker output for progress...")
        else:
            print(f"    ✗ Error: {response.status_code}")
            print(f"    {response.text}")
            
            if "NOT_FOUND" in response.text:
                print("\n    → BPMN process not deployed!")
                print("    Deploy hotel-reservation-process.bpmn first.")
            elif "cannot be parsed" in response.text:
                print("\n    → API format issue. Check Camunda 8 version.")
    
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()

