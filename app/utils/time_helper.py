import pytz
from datetime import datetime, timedelta

class TimeHelper:
    def __init__(self, timezone_str='America/Chicago'):
        self.timezone = pytz.timezone(timezone_str)
    
    def utc_to_local(self, utc_time):
        """Convert UTC time to local time"""
        # Handle string timestamps
        if isinstance(utc_time, str):
            utc_time = datetime.strptime(utc_time, '%Y-%m-%d %H:%M:%S')
        
        # Add UTC timezone if not present
        if utc_time.tzinfo is None:
            utc_time = pytz.UTC.localize(utc_time)
            
        # Convert to local time
        return utc_time.astimezone(self.timezone)
    
    def is_within_business_hours(self, local_time, business_hours):
        """Check if time falls within business hours"""
        day_of_week = local_time.weekday()
        time_str = local_time.strftime('%H:%M')
        
        # If no business hours, assume 24/7
        if not business_hours:
            return True
        
        # Check each business hours entry for this day
        for hours in business_hours:
            if hours['day_of_week'] == day_of_week:
                # Make sure we're working with strings
                start_time_str = hours['start_time_local']
                end_time_str = hours['end_time_local']
                
                # Handle different formats
                if isinstance(start_time_str, str) and ':' in start_time_str:
                    start_parts = start_time_str.split(':')
                    start_time = start_parts[0] + ':' + start_parts[1]
                elif isinstance(start_time_str, timedelta):
                    # Convert timedelta to string in HH:MM format
                    total_seconds = int(start_time_str.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    start_time = f"{hours:02d}:{minutes:02d}"
                else:
                    # Default
                    start_time = "00:00"
                
                if isinstance(end_time_str, str) and ':' in end_time_str:
                    end_parts = end_time_str.split(':')
                    end_time = end_parts[0] + ':' + end_parts[1]
                elif isinstance(end_time_str, timedelta):
                    # Convert timedelta to string in HH:MM format
                    total_seconds = int(end_time_str.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    end_time = f"{hours:02d}:{minutes:02d}"
                else:
                    # Default
                    end_time = "23:59"
                
                # Handle overnight hours (end time earlier than start time)
                if end_time < start_time:
                    # Either before midnight after start time, or after midnight before end time
                    if time_str >= start_time or time_str <= end_time:
                        return True
                else:
                    # Normal case: start_time <= time_str <= end_time
                    if start_time <= time_str <= end_time:
                        return True
        
        return False 