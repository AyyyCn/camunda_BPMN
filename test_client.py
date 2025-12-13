from camunda8_client import HotelReservationClient

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
    print(f"Process Instance ID: {result.get('process_instance_id')}")
    print("Note: External task workers need to be running to complete the process")