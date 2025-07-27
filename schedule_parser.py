#!/usr/bin/env python3
"""
Schedule Data Parser
Extracts staff information and their available times from JSON schedule data
"""

import json
from datetime import datetime
from typing import Dict, List, Optional

def load_json_file(filename: str) -> Dict:
    """Load and parse a JSON file."""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in file '{filename}'")
        return {}

def format_time(time_str: str) -> str:
    """Convert ISO time format to readable format."""
    try:
        # Parse the ISO format datetime string
        dt = datetime.fromisoformat(time_str.replace('T', ' '))
        # Return just the time part in HH:MM format
        return dt.strftime('%H:%M')
    except:
        return time_str

def print_staff_info(app_startup_data: Dict):
    """Print all staff members and their IDs."""
    print("=" * 60)
    print("STAFF DIRECTORY")
    print("=" * 60)
    
    staff_data = app_startup_data.get('auth', {}).get('sharedData', {}).get('selectors', {}).get('staff', {}).get('byId', {})
    
    if not staff_data:
        print("No staff data found")
        return
    
    # Sort staff by ID for consistent output
    sorted_staff = sorted(staff_data.items(), key=lambda x: int(x[0]))
    
    for staff_id, staff_info in sorted_staff:
        first_name = staff_info.get('firstName', 'Unknown')
        last_name = staff_info.get('lastName', '') or ''
        email = staff_info.get('email', 'No email')
        is_service_provider = staff_info.get('serviceProvider', False)
        
        full_name = f"{first_name} {last_name}".strip()
        provider_status = "Service Provider" if is_service_provider else "Non-Service Provider"
        
        print(f"ID: {staff_id:2} | Name: {full_name:25} | Email: {email:30} | {provider_status}")

def get_appointments_by_staff(appointments_data: Dict) -> Dict[str, List]:
    """Group appointments by staff ID."""
    appointments_by_staff = {}
    
    for appointment_id, appointment in appointments_data.items():
        appointment_parts = appointment.get('appointmentParts', [])
        
        for part in appointment_parts:
            staff_id = str(part.get('staffId', ''))
            if staff_id:
                if staff_id not in appointments_by_staff:
                    appointments_by_staff[staff_id] = []
                
                # Create appointment info
                client = appointment.get('client', {})
                client_name = f"{client.get('firstName', '')} {client.get('lastName', '') or ''}".strip()
                
                appointment_info = {
                    'id': appointment_id,
                    'start_time': part.get('startAtLocal', ''),
                    'end_time': part.get('endAtLocal', ''),
                    'duration': part.get('durationInMins', 0),
                    'client_name': client_name or 'Unknown Client',
                    'client_phone': client.get('phone', ''),
                    'service_id': part.get('serviceId', ''),
                    'price': part.get('price', '0'),
                    'total_price': appointment.get('totalPrice', '0'),
                    'status': appointment.get('workflowStatus', 'Unknown'),
                    'notes': appointment.get('notes', ''),
                    'client_notes': client.get('notes', '')
                }
                
                appointments_by_staff[staff_id].append(appointment_info)
    
    # Sort appointments by start time for each staff member
    for staff_id in appointments_by_staff:
        appointments_by_staff[staff_id].sort(key=lambda x: x['start_time'])
    
    return appointments_by_staff

def print_staff_schedules(app_startup_data: Dict, multi_provider_data: Dict):
    """Print staff schedules and appointments for the day."""
    print("\n" + "=" * 60)
    print("STAFF SCHEDULES & APPOINTMENTS FOR THE DAY")
    print("=" * 60)
    
    staff_data = app_startup_data.get('auth', {}).get('sharedData', {}).get('selectors', {}).get('staff', {}).get('byId', {})
    shifts_data = multi_provider_data.get('shiftsByStaffIdAndDay', {})
    appointments_data = multi_provider_data.get('appointments', {}).get('byId', {})
    date = multi_provider_data.get('date', 'Unknown date')
    
    print(f"Date: {date}")
    print("-" * 60)
    
    if not staff_data or not shifts_data:
        print("No staff or shift data found")
        return
    
    # Group appointments by staff
    appointments_by_staff = get_appointments_by_staff(appointments_data)
    
    # Get service providers only and sort by ID
    service_providers = {
        staff_id: staff_info 
        for staff_id, staff_info in staff_data.items() 
        if staff_info.get('serviceProvider', False)
    }
    
    sorted_providers = sorted(service_providers.items(), key=lambda x: int(x[0]))
    
    for staff_id, staff_info in sorted_providers:
        first_name = staff_info.get('firstName', 'Unknown')
        last_name = staff_info.get('lastName', '') or ''
        full_name = f"{first_name} {last_name}".strip()
        
        print(f"\nStaff ID {staff_id}: {full_name}")
        print("-" * 40)
        
        # Get shifts for this staff member
        staff_shifts = shifts_data.get(staff_id, {})
        day_shifts = staff_shifts.get(date, [])
        
        # Print shifts
        print("  SHIFTS:")
        if not day_shifts:
            print("    No shifts scheduled")
        else:
            for i, shift in enumerate(day_shifts, 1):
                start_time = format_time(shift.get('startAtLocal', ''))
                end_time = format_time(shift.get('endAtLocal', ''))
                location_id = shift.get('locationId', 'Unknown')
                
                print(f"    Shift {i}: {start_time} - {end_time} (Location {location_id})")
        
        # Print appointments
        print("  APPOINTMENTS:")
        staff_appointments = appointments_by_staff.get(staff_id, [])
        if not staff_appointments:
            print("    No appointments scheduled")
        else:
            for i, appt in enumerate(staff_appointments, 1):
                start_time = format_time(appt['start_time'])
                end_time = format_time(appt['end_time'])
                client_name = appt['client_name']
                duration = appt['duration']
                price = appt['total_price']
                status = appt['status']
                
                print(f"    Appt {i}: {start_time}-{end_time} | {client_name} | {duration}min | ${price} | {status}")
                
                # Show client notes if available
                if appt['client_notes']:
                    # Truncate long notes for readability
                    notes = appt['client_notes'][:80] + "..." if len(appt['client_notes']) > 80 else appt['client_notes']
                    print(f"           Notes: {notes}")
                
                # Show phone number
                if appt['client_phone']:
                    print(f"           Phone: {appt['client_phone']}")
        
        print()  # Add space between staff members

def main():
    """Main function to run the schedule parser."""
    print("Schedule Data Parser")
    print("Reading schedule data from JSON files...\n")
    
    # Load the JSON files
    app_startup_data = load_json_file('app-startup-check-auth.json')
    multi_provider_data = load_json_file('multi-provider-view.json')
    
    if not app_startup_data or not multi_provider_data:
        print("Failed to load required data files")
        return
    
    # Print staff information
    print_staff_info(app_startup_data)
    
    # Print staff schedules
    print_staff_schedules(app_startup_data, multi_provider_data)
    
    print("\n" + "=" * 60)
    print("End of Report")
    print("=" * 60)

if __name__ == "__main__":
    main() 