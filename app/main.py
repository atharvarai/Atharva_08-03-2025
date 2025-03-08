import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from app.services.report_service import trigger_report, get_report_status
from app.database import execute_query

app = FastAPI(title="Store Monitoring API")

@app.get("/")
def read_root():
    return {"message": "Welcome to Store Monitoring API"}

@app.post("/trigger_report")
def api_trigger_report():
    """Trigger a new report generation"""
    report_id = trigger_report()
    return {"report_id": report_id}

@app.get("/get_report")
def api_get_report(report_id: str):
    """Get the status of a report or download the report"""
    report = get_report_status(report_id)
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report['status'] == 'Running':
        return {"status": "Running"}
    
    if report['status'] == 'Error':
        return {"status": "Error", "message": "Report generation failed"}
    
    # Report is complete, return the file
    if not os.path.exists(report['file_path']):
        raise HTTPException(status_code=404, detail="Report file not found")
    
    return FileResponse(
        report['file_path'],
        media_type='text/csv',
        filename=f'report_{report_id}.csv'
    )

# For development/testing purposes
@app.get("/import_data")
def import_test_data():
    """Import test data from CSV files"""
    from app.services.data_service import import_all_data
    data_dir = os.path.join(os.getcwd(), 'data')
    import_all_data(data_dir)
    return {"message": "Data import finished"}

# Check data import status
@app.get("/debug_data")
def debug_data():
    """Debug endpoint to check data import status with detailed information"""
    try:
        # Check store_status table
        status_query = "SELECT COUNT(*) as count FROM store_status"
        status_result = execute_query(status_query, fetch=True)
        status_count = status_result[0]['count'] if status_result else 0
        
        # Check business_hours table
        hours_query = "SELECT COUNT(*) as count FROM business_hours"
        hours_result = execute_query(hours_query, fetch=True)
        hours_count = hours_result[0]['count'] if hours_result else 0
        
        # Check store_timezones table
        timezone_query = "SELECT COUNT(*) as count FROM store_timezones"
        timezone_result = execute_query(timezone_query, fetch=True)
        timezone_count = timezone_result[0]['count'] if timezone_result else 0
        
        # Get distinct store counts
        distinct_stores_query = "SELECT COUNT(DISTINCT store_id) as count FROM store_status"
        distinct_stores_result = execute_query(distinct_stores_query, fetch=True)
        distinct_stores_count = distinct_stores_result[0]['count'] if distinct_stores_result else 0
        
        # Check for active/inactive status distribution
        status_distribution_query = """
        SELECT status, COUNT(*) as count 
        FROM store_status 
        GROUP BY status
        """
        status_distribution = execute_query(status_distribution_query, fetch=True)
        
        # Check time range of data
        time_range_query = """
        SELECT 
            MIN(timestamp_utc) as earliest_timestamp,
            MAX(timestamp_utc) as latest_timestamp
        FROM store_status
        """
        time_range = execute_query(time_range_query, fetch=True)
        
        # Check business hours coverage
        business_hours_coverage_query = """
        SELECT 
            COUNT(DISTINCT store_id) as stores_with_hours
        FROM business_hours
        """
        business_hours_coverage = execute_query(business_hours_coverage_query, fetch=True)
        stores_with_hours = business_hours_coverage[0]['stores_with_hours'] if business_hours_coverage else 0
        
        # Check timezone coverage
        timezone_coverage_query = """
        SELECT 
            COUNT(DISTINCT store_id) as stores_with_timezone
        FROM store_timezones
        """
        timezone_coverage = execute_query(timezone_coverage_query, fetch=True)
        stores_with_timezone = timezone_coverage[0]['stores_with_timezone'] if timezone_coverage else 0
        
        # Get sample data
        sample_status = execute_query("SELECT * FROM store_status LIMIT 5", fetch=True)
        sample_hours = execute_query("SELECT * FROM business_hours LIMIT 5", fetch=True)
        sample_tz = execute_query("SELECT * FROM store_timezones LIMIT 5", fetch=True)
        
        # Determine import status
        import_status = "Success"
        issues = []
        
        if status_count == 0:
            import_status = "Failed"
            issues.append("No store status records found")
        
        if distinct_stores_count == 0:
            import_status = "Failed"
            issues.append("No store IDs found in status data")
        
        if hours_count == 0:
            issues.append("No business hours records found (will assume 24/7 operation)")
        
        if timezone_count == 0:
            issues.append("No timezone records found (will assume America/Chicago)")
        
        if stores_with_hours > 0 and stores_with_hours < distinct_stores_count:
            issues.append(f"Only {stores_with_hours}/{distinct_stores_count} stores have business hours")
        
        if stores_with_timezone > 0 and stores_with_timezone < distinct_stores_count:
            issues.append(f"Only {stores_with_timezone}/{distinct_stores_count} stores have timezone data")
        
        return {
            "import_status": import_status,
            "issues": issues,
            "counts": {
                "store_status": status_count,
                "business_hours": hours_count,
                "store_timezones": timezone_count,
                "distinct_stores": distinct_stores_count
            },
            "coverage": {
                "stores_with_business_hours": stores_with_hours,
                "stores_with_timezone": stores_with_timezone,
                "business_hours_coverage_percentage": round(stores_with_hours / distinct_stores_count * 100, 2) if distinct_stores_count > 0 else 0,
                "timezone_coverage_percentage": round(stores_with_timezone / distinct_stores_count * 100, 2) if distinct_stores_count > 0 else 0
            },
            "status_distribution": status_distribution,
            "time_range": time_range[0] if time_range else None,
            "samples": {
                "store_status": sample_status,
                "business_hours": sample_hours,
                "store_timezones": sample_tz
            }
        }
    except Exception as e:
        return {
            "import_status": "Error",
            "error": str(e)
        } 