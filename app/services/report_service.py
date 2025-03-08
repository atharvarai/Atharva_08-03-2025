import os
import uuid
import csv
import pytz
from datetime import datetime, timedelta
from app.database import execute_query
import threading
from app.logger import logger
from app.utils.time_helper import TimeHelper

def trigger_report():
    """Trigger a new report generation"""
    report_id = str(uuid.uuid4())
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    logger.info(f"Triggering report generation with ID: {report_id}")
    
    query = """
    INSERT INTO reports (report_id, status, created_at)
    VALUES (%s, %s, %s)
    """
    execute_query(query, (report_id, 'Running', now))
    
    # Start report generation in a separate thread
    thread = threading.Thread(target=generate_report, args=(report_id,))
    thread.daemon = True
    thread.start()
    
    return report_id

def get_report_status(report_id):
    """Get the status of a report"""
    logger.info(f"Checking status of report: {report_id}")
    
    query = """
    SELECT status, file_path FROM reports
    WHERE report_id = %s
    """
    results = execute_query(query, (report_id,), fetch=True)
    
    if not results:
        logger.warning(f"Report not found: {report_id}")
        return None
    
    logger.info(f"Report status: {results[0]['status']}")
    return results[0]

def generate_report(report_id):
    """Generate the report"""
    try:
        logger.info(f"Starting report generation for ID: {report_id}")
        
        # Get current time (max timestamp from observations)
        max_time_result = execute_query(
            "SELECT MAX(timestamp_utc) as max_time FROM store_status",
            fetch=True
        )
        
        if not max_time_result or not max_time_result[0]['max_time']:
            logger.error("No data found in store_status table")
            update_query = """
            UPDATE reports
            SET status = %s, completed_at = %s
            WHERE report_id = %s
            """
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            execute_query(update_query, ('Error', now, report_id))
            return
            
        current_time = max_time_result[0]['max_time']
        logger.info(f"Using current time: {current_time}")
        
        # Get all store IDs
        store_ids = execute_query(
            "SELECT DISTINCT store_id FROM store_status",
            fetch=True
        )
        
        if not store_ids:
            logger.error("No store IDs found in store_status table")
            update_query = """
            UPDATE reports
            SET status = %s, completed_at = %s
            WHERE report_id = %s
            """
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            execute_query(update_query, ('Error', now, report_id))
            return
        
        # Process stores in batches
        batch_size = 50  # Process 50 stores at a time
        reports_dir = os.path.join(os.getcwd(), 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        file_path = os.path.join(reports_dir, f'report_{report_id}.csv')
        
        with open(file_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=[
                'store_id', 
                'uptime_last_hour(in minutes)', 
                'uptime_last_day(in hours)', 
                'uptime_last_week(in hours)', 
                'downtime_last_hour(in minutes)', 
                'downtime_last_day(in hours)', 
                'downtime_last_week(in hours)'
            ])
            writer.writeheader()
            
            for i in range(0, len(store_ids), batch_size):
                batch = store_ids[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1} of {(len(store_ids) + batch_size - 1)//batch_size}")
                
                for store in batch:
                    store_id = store['store_id']
                    logger.debug(f"Processing store: {store_id}")
                    
                    try:
                        metrics = calculate_store_metrics(store_id, current_time)
                        
                        writer.writerow({
                            'store_id': store_id,
                            'uptime_last_hour(in minutes)': metrics['uptime_last_hour'],
                            'uptime_last_day(in hours)': metrics['uptime_last_day'],
                            'uptime_last_week(in hours)': metrics['uptime_last_week'],
                            'downtime_last_hour(in minutes)': metrics['downtime_last_hour'],
                            'downtime_last_day(in hours)': metrics['downtime_last_day'],
                            'downtime_last_week(in hours)': metrics['downtime_last_week']
                        })
                    except Exception as e:
                        logger.error(f"Error processing store {store_id}: {e}")
                        # Continue with next store
        
        # Update report status
        update_query = """
        UPDATE reports
        SET status = %s, completed_at = %s, file_path = %s
        WHERE report_id = %s
        """
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        execute_query(update_query, ('Complete', now, file_path, report_id))
        logger.info(f"Report generation completed for ID: {report_id}")
        
    except Exception as e:
        logger.error(f"Error generating report: {e}", exc_info=True)
        update_query = """
        UPDATE reports
        SET status = %s, completed_at = %s
        WHERE report_id = %s
        """
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        execute_query(update_query, ('Error', now, report_id))

def calculate_store_metrics(store_id, current_time):
    """Calculate uptime/downtime metrics for a store"""
    try:
        # Get store timezone
        timezone_query = """
        SELECT timezone_str FROM store_timezones
        WHERE store_id = %s
        """
        timezone_result = execute_query(timezone_query, (store_id,), fetch=True)
        timezone_str = timezone_result[0]['timezone_str'] if timezone_result else 'America/Chicago'
        
        # Initialize time helper
        time_helper = TimeHelper(timezone_str)
        
        # Get business hours
        hours_query = """
        SELECT day_of_week, start_time_local, end_time_local 
        FROM business_hours
        WHERE store_id = %s
        """
        business_hours = execute_query(hours_query, (store_id,), fetch=True)
        
        # If no business hours, assume 24/7
        is_24x7 = len(business_hours) == 0
        
        # Calculate time ranges
        if isinstance(current_time, str):
            current_time = datetime.strptime(current_time, '%Y-%m-%d %H:%M:%S')
        
        last_hour = current_time - timedelta(hours=1)
        last_day = current_time - timedelta(days=1)
        last_week = current_time - timedelta(weeks=1)
        
        # Get observations
        observations_query = """
        SELECT timestamp_utc, status
        FROM store_status
        WHERE store_id = %s 
        AND timestamp_utc >= %s
        ORDER BY timestamp_utc
        """
        observations = execute_query(
            observations_query, 
            (store_id, last_week.strftime('%Y-%m-%d %H:%M:%S')),
            fetch=True
        )
        
        # Interpolation logic:
        # 1. For each time period, count observations during business hours
        # 2. Calculate uptime ratio based on these observations
        # 3. Apply ratio to total business hours in the period
        
        def calculate_period_metrics(start_time, end_time, total_time):
            """Calculate metrics for a specific time period"""
            active_count = 0
            total_count = 0
            
            for obs in observations:
                # Handle both string and datetime objects
                obs_time = obs['timestamp_utc']
                if isinstance(obs_time, str):
                    obs_time = datetime.strptime(obs_time, '%Y-%m-%d %H:%M:%S')
                
                if start_time <= obs_time <= end_time:
                    # Convert to local time for business hours check
                    local_time = time_helper.utc_to_local(obs_time)
                    
                    # Only count if within business hours
                    if is_24x7 or time_helper.is_within_business_hours(local_time, business_hours):
                        total_count += 1
                        if obs['status'] == 'active':
                            active_count += 1
            
            # Calculate uptime ratio
            uptime_ratio = active_count / total_count if total_count > 0 else 0
            
            # Apply ratio to total time
            return round(uptime_ratio * total_time, 2)
        
        # Calculate metrics for each period
        metrics = {}
        
        # Last hour (in minutes)
        metrics['uptime_last_hour'] = calculate_period_metrics(last_hour, current_time, 60)
        metrics['downtime_last_hour'] = 60 - metrics['uptime_last_hour']
        
        # Last day (in hours)
        metrics['uptime_last_day'] = calculate_period_metrics(last_day, current_time, 24)
        metrics['downtime_last_day'] = 24 - metrics['uptime_last_day']
        
        # Last week (in hours)
        metrics['uptime_last_week'] = calculate_period_metrics(last_week, current_time, 168)
        metrics['downtime_last_week'] = 168 - metrics['uptime_last_week']
        
        return metrics
    except Exception as e:
        logger.error(f"Error calculating metrics for store {store_id}: {e}", exc_info=True)
        # Return zeros in case of error
        return {
            'uptime_last_hour': 0,
            'uptime_last_day': 0,
            'uptime_last_week': 0,
            'downtime_last_hour': 60,
            'downtime_last_day': 24,
            'downtime_last_week': 168
        }

def calculate_uptime(observations, start_time, end_time, business_hours, timezone_str, is_24x7, unit='hours'):
    """
    Calculate uptime within a time range considering business hours
    """
    if not observations:
        return 0
    
    # Convert to timezone
    local_tz = pytz.timezone(timezone_str)
    
    # Count active observations
    active_count = 0
    total_count = len(observations)
    
    for o in observations:
        # Handle both string and datetime timestamps
        if o['status'] == 'active':
            active_count += 1
    
    if total_count == 0:
        return 0
    
    active_ratio = active_count / total_count
    
    # Calculate total business hours in the period
    total_business_time = 0
    
    if is_24x7:
        # If 24x7, use the entire time range
        total_seconds = (end_time - start_time).total_seconds()
        if unit == 'hours':
            total_business_time = total_seconds / 3600  # Convert seconds to hours
        else:  # minutes
            total_business_time = total_seconds / 60  # Convert seconds to minutes
    else:
        # Calculate business hours for each day in the range
        current_day = start_time
        while current_day <= end_time:
            day_of_week = current_day.weekday()  # 0 = Monday, 6 = Sunday
            
            # Find business hours for this day
            day_hours = [h for h in business_hours if h['day_of_week'] == day_of_week]
            
            for hours in day_hours:
                # Parse business hours - make sure we're working with strings
                start_time_str = hours['start_time_local']
                end_time_str = hours['end_time_local']
                
                # Handle different time formats
                if isinstance(start_time_str, str) and ':' in start_time_str:
                    start_parts = start_time_str.split(':')
                    start_hour = int(start_parts[0])
                    start_minute = int(start_parts[1]) if len(start_parts) > 1 else 0
                else:
                    # Default to midnight if format is unexpected
                    start_hour, start_minute = 0, 0
                
                if isinstance(end_time_str, str) and ':' in end_time_str:
                    end_parts = end_time_str.split(':')
                    end_hour = int(end_parts[0])
                    end_minute = int(end_parts[1]) if len(end_parts) > 1 else 0
                else:
                    # Default to midnight if format is unexpected
                    end_hour, end_minute = 0, 0
                
                # Calculate business hours for this day
                business_start = datetime(
                    current_day.year, current_day.month, current_day.day,
                    start_hour, start_minute
                )
                business_end = datetime(
                    current_day.year, current_day.month, current_day.day,
                    end_hour, end_minute
                )
                
                # Handle overnight business hours
                if end_hour < start_hour:
                    business_end = business_end + timedelta(days=1)
                
                # Adjust for time range
                if business_start < start_time:
                    business_start = start_time
                if business_end > end_time:
                    business_end = end_time
                
                if business_end > business_start:
                    business_seconds = (business_end - business_start).total_seconds()
                    if unit == 'hours':
                        total_business_time += business_seconds / 3600
                    else:  # minutes
                        total_business_time += business_seconds / 60
            
            current_day += timedelta(days=1)
    
    # Apply active ratio to total business time
    return round(active_ratio * total_business_time, 2) 