# Store Monitoring System
A robust backend system for monitoring restaurant uptime and downtime, providing detailed reports on store availability during business hours.

## Tech Stack
- Backend Framework: Python FastAPI
- Database: MySQL
- Libraries:
    - fastapi: API framework
    - mysql-connector-python: Database connectivity
    - pytz: Timezone handling

## Features
- Import store data from CSV files
- Generate reports on store uptime/downtime
- Consider business hours and timezones
- Asynchronous report generation
- Batch processing for performance optimization
- Detailed logging and error handling

## API Endpoints (Use following CURL requests or use POSTMAN)
### *1. Check API Status*
```bash
curl http://localhost:8000/
```

Response:
```json
{"message":"Welcome to Store Monitoring API"}
```

### *2. Import Store Data*
```bash
curl http://localhost:8000/import_data
```

Response:
```json
{"message":"Data import finished"}
```

### *3. Debug Data Import Status*
```bash
curl http://localhost:8000/debug_data
```

Response: Detailed information about imported data and its status.


### *4. Trigger Report Generation*
```bash
curl -X POST http://localhost:8000/trigger_report
```

Response:
```json
{"report_id":"371a640e-3aef-4d25-b472-ba218fff8533"}
```

### *5. Check Report Status / Download Report*
```bash
curl http://localhost:8000/get_report?report_id=371a640e-3aef-4d25-b472-ba218fff8533
```

Response:
- If running: {"status":"Running"}
- If error: {"status":"Error","message":"Report generation failed"}
- If complete: Downloads the CSV file


## Data Processing Logic
### Extrapolation Logic
The system uses a straightforward ratio-based extrapolation approach:

**1. Data Collection:**
- retrieve all status observations for a store within the time period
- Filter observations to only include those during business hours

**2. Ratio Calculation:**
- Calculate the ratio of "active" observations to total observations
- This ratio represents the estimated uptime percentage

**3. Extrapolation:**
- Apply this ratio to the total business hours in the period
- For example, if 75% of observations show "active" status and there are 8 business hours in a day, the estimated uptime is 6 hours

**4. Time Period Handling:**
- Last hour: Extrapolate to 60 minutes
- Last day: Extrapolate to 24 hours
Last week: Extrapolate to 168 hours (7 days)

### Timezone Handling
The system properly accounts for timezone differences:
1. Store status observations are in UTC
2. Business hours are in local time
3. The system converts between these using the store's timezone
4. For stores without timezone data, America/Chicago is used as default

### Business Hours Consideration
1. If a store has defined business hours, only observations during those hours are counted
2. If no business hours are defined, the store is assumed to be open 24/7
3. The system handles overnight business hours (e.g., 10 PM to 2 AM)

## Workflow
**1. Data Import:**
- CSV files are imported into MySQL database
- Store status observations, business hours, and timezones are stored
- Default values are applied for missing data

**2. Report Generation:**
- User triggers report generation via API
- System generates a unique report ID
- Background thread processes the report asynchronously
- Stores are processed in batches for better performance and for better logging and monitoring progress

**3. Uptime Calculation:**
- For each store, the system:
    - Retrieves timezone and business hours
    - Gets status observations for the last hour, day, and week
    - Filters observations to only include those during business hours
    - Calculates uptime ratio based on active vs. inactive observations
    - Applies this ratio to the total business hours in each period

**4. Report Retrieval:**
- User polls for report status using the report ID
- Once complete, the system returns the CSV file with uptime/downtime metrics

## Sample Output
A sample report can be found in the repository at `reports/report_b588d239-62c1-4804-9b73-b15c3b7f4d82.csv`

The report includes the following columns:
- `store_id`: Unique identifier for each store
- `uptime_last_hour`(in minutes): Minutes the store was operational in the last hour
- `uptime_last_day`(in hours): Hours the store was operational in the last day
- `uptime_last_week`(in hours): Hours the store was operational in the last week
- `downtime_last_hour`(in minutes): Minutes the store was non-operational in the last hour
- `downtime_last_day`(in hours): Hours the store was non-operational in the last day
- `downtime_last_week`(in hours): Hours the store was non-operational in the last week

## Improvement Ideas
- **Advanced Interpolation Logic:**
    - Implement weighted interpolation based on observation proximity
    - Use machine learning to predict status during gaps in observations
- **Performance Optimizations:**
    - Add caching for frequently accessed data
    - Add data Validation checks eg) start_time_local < end_time_local
- **Monitoring and Alerting:**
    - Add real-time monitoring of store status
    - Implement alerting for extended downtime periods

## Setup and Installation
1. Clone the repository
2. Create a virtual environment:
   ```bash
    python -m venv venv
    venv\Scripts\activate # On Linux: source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up the database:

   ```bash
   Create a MySQL database using Mysql workbench or using MySQL command line client and update .env file with credentials
   ```

### Using MySQL command line client

- Log in to MySQL and create the database:

```bash
mysql -u root -p
```

- In MySQL:

```bash
CREATE DATABASE store_monitoring;
USE store_monitoring;

CREATE TABLE store_status (
    id INT AUTO_INCREMENT PRIMARY KEY,
    store_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    timestamp_utc DATETIME NOT NULL,
    INDEX idx_store_id (store_id),
    INDEX idx_timestamp (timestamp_utc)
);

CREATE TABLE business_hours (
    id INT AUTO_INCREMENT PRIMARY KEY,
    store_id VARCHAR(255) NOT NULL,
    day_of_week INT NOT NULL,
    start_time_local TIME NOT NULL,
    end_time_local TIME NOT NULL,
    INDEX idx_store_id (store_id),
    INDEX idx_day_of_week (day_of_week)
);

CREATE TABLE store_timezones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    store_id VARCHAR(255) NOT NULL,
    timezone_str VARCHAR(100) NOT NULL,
    INDEX idx_store_id (store_id)
);

CREATE TABLE reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at DATETIME NOT NULL,
    completed_at DATETIME NULL,
    file_path VARCHAR(255) NULL,
    INDEX idx_report_id (report_id)
);
```
   
5. Run the application:
   ```bash
    python run.py
   ```