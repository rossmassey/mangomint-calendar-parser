#!/usr/bin/env python3
"""
Schedule Data Parser
Extracts staff information and their available times from JSON schedule data
Creates a comprehensive data structure suitable for API access
"""

import json
import glob
from datetime import datetime
from typing import Dict, List

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

def find_schedule_files() -> List[str]:
    """Find all multi-provider-view JSON files."""
    files = glob.glob("multi-provider-view.*.json")
    return sorted(files)

def format_time(time_str: str) -> str:
    """Convert ISO time format to readable format."""
    try:
        # Parse the ISO format datetime string
        dt = datetime.fromisoformat(time_str.replace('T', ' '))
        # Return just the time part in HH:MM format
        return dt.strftime('%H:%M')
    except:
        return time_str

def format_date(date_str: str) -> str:
    """Convert date string to readable format."""
    try:
        # Convert from YYYY-MM-DD to M/D format
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        # Use manual formatting to avoid platform-specific issues
        return f"{dt.month}/{dt.day}"
    except:
        return date_str

def get_service_type(service_id: str, calendar_data: Dict) -> str:
    """Get service type from service ID."""
    services = calendar_data.get('services', {}).get('servicesById', {})
    service = services.get(str(service_id), {})
    return service.get('name', 'Unknown Service')

def build_comprehensive_data(app_startup_data: Dict, schedule_files: List[str]) -> Dict:
    """Build comprehensive data structure from all schedule files."""
    
    # Get staff data
    staff_data = app_startup_data.get('auth', {}).get('sharedData', {}).get('selectors', {}).get('staff', {}).get('byId', {})
    
    # Initialize result structure
    result = {
        'staff': {},
        'schedules': {}
    }
    
    # Build staff directory (service providers only)
    for staff_id, staff_info in staff_data.items():
        if staff_info.get('serviceProvider', False):
            first_name = staff_info.get('firstName', 'Unknown')
            last_name = staff_info.get('lastName', '') or ''
            full_name = f"{first_name} {last_name}".strip()
            
            result['staff'][staff_id] = {
                'id': staff_id,
                'name': full_name,
                'email': staff_info.get('email', 'No email')
            }
    
    # Load calendar data for service names (from any schedule file)
    calendar_data = {}
    if schedule_files:
        calendar_data = load_json_file('calendar-page-metadata.json')
    
    # Process each schedule file
    for filename in schedule_files:
        print(f"Processing {filename}...")
        schedule_data = load_json_file(filename)
        
        if not schedule_data:
            continue
            
        date = schedule_data.get('date', 'Unknown')
        shifts_data = schedule_data.get('shiftsByStaffIdAndDay', {})
        appointments_data = schedule_data.get('appointments', {}).get('byId', {})
        
        result['schedules'][date] = {}
        
        # Process each service provider
        for staff_id in result['staff'].keys():
            staff_schedule = {
                'shifts': [],
                'appointments': []
            }
            
            # Get shifts
            staff_shifts = shifts_data.get(staff_id, {})
            day_shifts = staff_shifts.get(date, [])
            
            for shift in day_shifts:
                staff_schedule['shifts'].append({
                    'start': format_time(shift.get('startAtLocal', '')),
                    'end': format_time(shift.get('endAtLocal', '')),
                    'location_id': shift.get('locationId', 1)
                })
            
            # Get appointments
            for appointment_id, appointment in appointments_data.items():
                appointment_parts = appointment.get('appointmentParts', [])
                
                for part in appointment_parts:
                    if str(part.get('staffId', '')) == staff_id:
                        client = appointment.get('client', {})
                        client_name = f"{client.get('firstName', '')} {client.get('lastName', '') or ''}".strip()
                        
                        service_type = get_service_type(part.get('serviceId', ''), calendar_data)
                        
                        staff_schedule['appointments'].append({
                            'start': format_time(part.get('startAtLocal', '')),
                            'end': format_time(part.get('endAtLocal', '')),
                            'service': service_type,
                            'client_name': client_name or 'Unknown Client',
                            'client_email': client.get('email', ''),
                            'price': appointment.get('totalPrice', '0'),
                            'status': appointment.get('workflowStatus', 'Unknown')
                        })
            
            # Sort appointments by start time
            staff_schedule['appointments'].sort(key=lambda x: x['start'])
            
            result['schedules'][date][staff_id] = staff_schedule
    
    return result

def print_staff_directory(data: Dict):
    """Print staff directory table."""
    print("STAFF LIST:")
    print("-" * 50)
    
    # Sort by staff ID
    sorted_staff = sorted(data['staff'].items(), key=lambda x: int(x[0]))
    
    for staff_id, staff_info in sorted_staff:
        print(f"{staff_id}: {staff_info['name']} - {staff_info['email']}")

def print_daily_schedules(data: Dict):
    """Print schedules for each day."""
    
    # Sort dates
    sorted_dates = sorted(data['schedules'].keys())
    
    for date in sorted_dates:
        formatted_date = format_date(date)
        print(f"\n{formatted_date} SCHEDULE")
        print("-" * 50)
        
        day_data = data['schedules'][date]
        
        # Sort staff by ID
        sorted_staff = sorted(day_data.items(), key=lambda x: int(x[0]))
        
        for staff_id, schedule in sorted_staff:
            staff_name = data['staff'][staff_id]['name']
            
            # Show shifts
            if schedule['shifts']:
                shifts_str = ", ".join([f"{s['start']}-{s['end']}" for s in schedule['shifts']])
                print(f"\n{staff_name} {shifts_str}:")
            else:
                print(f"\n{staff_name} (no shifts):")
            
            # Show appointments
            if schedule['appointments']:
                for appt in schedule['appointments']:
                    client_contact = appt['client_email'] if appt['client_email'] else appt['client_name']
                    print(f"  - {appt['start']}-{appt['end']}: {appt['service']}, {client_contact}")
            else:
                print("  (no appointments)")
        
        print()  # Extra space between days

def main():
    """Main function to run the schedule parser."""
    print("Multi-Day Schedule Data Parser")
    print("Reading schedule data from JSON files...\n")
    
    # Load staff data
    app_startup_data = load_json_file('app-startup-check-auth.json')
    if not app_startup_data:
        print("Failed to load app-startup-check-auth.json")
        return
    
    # Find all schedule files
    schedule_files = find_schedule_files()
    if not schedule_files:
        print("No multi-provider-view.*.json files found")
        return
    
    print(f"Found schedule files: {', '.join(schedule_files)}\n")
    
    # Build comprehensive data structure
    data = build_comprehensive_data(app_startup_data, schedule_files)
    
    # Print staff directory
    print_staff_directory(data)
    
    # Print daily schedules
    print_daily_schedules(data)
    
    print("\n" + "=" * 60)
    print("Data structure is now available in 'data' variable for API access")
    print("=" * 60)
    
    # Example of how to access the data programmatically:
    # data['staff']['11']['name'] -> "Sasha"
    # data['schedules']['2025-07-26']['11']['shifts'] -> list of shifts
    # data['schedules']['2025-07-26']['11']['appointments'] -> list of appointments
    
    # Return data for potential API use
    return data

if __name__ == "__main__":
    main() 