import csv
import os
from datetime import datetime
from app.database import execute_query, get_connection
from app.logger import logger

def import_store_status(file_path):
    """Import store status data from CSV"""
    if not os.path.exists(file_path):
        logger.error(f"Error: File not found - {file_path}")
        return
    
    try:
        logger.info(f"Starting import of store status data from {file_path}")
        with open(file_path, 'r') as file:
            reader = csv.DictReader(file)
            batch_size = 1000
            batch = []
            count = 0
            
            for row in reader:
                try:
                    # Parse timestamp
                    timestamp = datetime.strptime(row['timestamp_utc'].replace(' UTC', ''), 
                                                '%Y-%m-%d %H:%M:%S.%f')
                    
                    batch.append((
                        row['store_id'],
                        row['status'],
                        timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    ))
                    count += 1
                    
                    if len(batch) >= batch_size:
                        _insert_store_status_batch(batch)
                        logger.info(f"Imported {count} store status records")
                        batch = []
                except Exception as e:
                    logger.error(f"Error processing row: {row} - {e}")
                    continue
            
            # Insert remaining records
            if batch:
                _insert_store_status_batch(batch)
                logger.info(f"Imported {count} store status records")
            
            logger.info(f"Completed importing store status data. Total records: {count}")
    except Exception as e:
        logger.error(f"Error importing store status data: {e}")

def _insert_store_status_batch(batch):
    """Insert a batch of store status records"""
    query = """
    INSERT INTO store_status (store_id, status, timestamp_utc)
    VALUES (%s, %s, %s)
    """
    connection = get_connection()
    cursor = connection.cursor()
    try:
        logger.debug(f"Executing batch insert of {len(batch)} store status records")
        cursor.executemany(query, batch)
        connection.commit()
        logger.debug("Batch insert successful")
    except Exception as e:
        connection.rollback()
        logger.error(f"Error in batch insert: {e}")
        raise e
    finally:
        cursor.close()
        connection.close()

def import_business_hours(file_path):
    """Import business hours data from CSV"""
    if not os.path.exists(file_path):
        logger.error(f"Error: File not found - {file_path}")
        return
    
    try:
        logger.info(f"Starting import of business hours data from {file_path}")
        with open(file_path, 'r') as file:
            reader = csv.DictReader(file)
            batch_size = 1000
            batch = []
            count = 0
            
            for row in reader:
                try:
                    batch.append((
                        row['store_id'],
                        int(row['dayOfWeek']),
                        row['start_time_local'],
                        row['end_time_local']
                    ))
                    count += 1
                    
                    if len(batch) >= batch_size:
                        _insert_business_hours_batch(batch)
                        logger.info(f"Imported {count} business hours records")
                        batch = []
                except Exception as e:
                    logger.error(f"Error processing row: {row} - {e}")
                    continue
            
            # Insert remaining records
            if batch:
                _insert_business_hours_batch(batch)
                logger.info(f"Imported {count} business hours records")
            
            logger.info(f"Completed importing business hours data. Total records: {count}")
    except Exception as e:
        logger.error(f"Error importing business hours data: {e}")

def _insert_business_hours_batch(batch):
    """Insert a batch of business hours records"""
    query = """
    INSERT INTO business_hours (store_id, day_of_week, start_time_local, end_time_local)
    VALUES (%s, %s, %s, %s)
    """
    connection = get_connection()
    cursor = connection.cursor()
    try:
        logger.debug(f"Executing batch insert of {len(batch)} business hours records")
        cursor.executemany(query, batch)
        connection.commit()
        logger.debug("Batch insert successful")
    except Exception as e:
        connection.rollback()
        logger.error(f"Error in batch insert: {e}")
        raise e
    finally:
        cursor.close()
        connection.close()

def import_store_timezones(file_path):
    """Import store timezone data from CSV"""
    if not os.path.exists(file_path):
        logger.error(f"Error: File not found - {file_path}")
        return
    
    try:
        logger.info(f"Starting import of timezone data from {file_path}")
        with open(file_path, 'r') as file:
            reader = csv.DictReader(file)
            batch_size = 1000
            batch = []
            count = 0
            
            for row in reader:
                try:
                    batch.append((
                        row['store_id'],
                        row['timezone_str']
                    ))
                    count += 1
                    
                    if len(batch) >= batch_size:
                        _insert_store_timezones_batch(batch)
                        logger.info(f"Imported {count} timezone records")
                        batch = []
                except Exception as e:
                    logger.error(f"Error processing row: {row} - {e}")
                    continue
            
            # Insert remaining records
            if batch:
                _insert_store_timezones_batch(batch)
                logger.info(f"Imported {count} timezone records")
            
            logger.info(f"Completed importing timezone data. Total records: {count}")
    except Exception as e:
        logger.error(f"Error importing timezone data: {e}")

def _insert_store_timezones_batch(batch):
    """Insert a batch of store timezone records"""
    query = """
    INSERT INTO store_timezones (store_id, timezone_str)
    VALUES (%s, %s)
    """
    connection = get_connection()
    cursor = connection.cursor()
    try:
        logger.debug(f"Executing batch insert of {len(batch)} timezone records")
        cursor.executemany(query, batch)
        connection.commit()
        logger.debug("Batch insert successful")
    except Exception as e:
        connection.rollback()
        logger.error(f"Error in batch insert: {e}")
        raise e
    finally:
        cursor.close()
        connection.close()

def import_all_data(data_dir):
    """Import all data from CSV files"""
    logger.info(f"Starting data import from {data_dir}")
    
    # Check if directory exists
    if not os.path.exists(data_dir):
        logger.error(f"Error: Data directory not found - {data_dir}")
        return
    
    # Check if files exist
    store_status_path = os.path.join(data_dir, 'store_status.csv')
    business_hours_path = os.path.join(data_dir, 'menu_hours.csv')
    timezones_path = os.path.join(data_dir, 'timezones.csv')
    
    if not os.path.exists(store_status_path):
        logger.error(f"Error: File not found - {store_status_path}")
    else:
        logger.info(f"Importing store status data from {store_status_path}")
        import_store_status(store_status_path)
    
    if not os.path.exists(business_hours_path):
        logger.error(f"Error: File not found - {business_hours_path}")
    else:
        logger.info(f"Importing business hours data from {business_hours_path}")
        import_business_hours(business_hours_path)
    
    if not os.path.exists(timezones_path):
        logger.error(f"Error: File not found - {timezones_path}")
    else:
        logger.info(f"Importing timezone data from {timezones_path}")
        import_store_timezones(timezones_path)
    
    logger.info("Data import completed") 