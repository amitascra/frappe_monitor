# Frappe Monitor - Implementation Summary

## Overview

Successfully implemented **frappe_monitor** - an advanced system monitoring application for Frappe/ERPNext with real-time metrics, historical data tracking, alerting, and performance insights.

## What Was Built

### 1. Backend Services (Phase 1 - Completed)

#### Metric Collection Service (`services/collector.py`)
- Collects comprehensive system metrics using `psutil`
- CPU: Usage %, core count, frequency, load average
- Memory: Total, used, available, swap usage
- Disk: Partition usage, I/O statistics
- Network: Bytes sent/received, connection count
- Processes: Top processes by CPU and memory
- System Info: Platform, uptime, hostname

#### Storage Service (`services/storage.py`)
- Stores metrics in `System Metric Log` DocType
- Time-series data management
- Historical data aggregation (hourly, daily)
- Automatic cleanup of old metrics based on retention period
- Efficient querying with granularity options

#### Alert Engine (`services/alert_engine.py`)
- Monitors metric thresholds in real-time
- Supports "Above" and "Below" threshold types
- Multiple notification channels:
  - Email alerts
  - In-app notifications
  - Webhook integration (Slack, Discord, etc.)
- Alert debouncing (Once vs Repeated)
- Alert history logging with resolution tracking

#### Aggregator Service (`services/aggregator.py`)
- Hourly metric aggregation
- Daily metric rollups
- Optimized for long-term data storage

### 2. API Layer (`api/metrics.py`)

All endpoints require System Manager role:

- `get_current_metrics()` - Real-time system metrics
- `get_historical_metrics(metric_type, metric_name, period, granularity)` - Historical data
- `get_process_list(sort_by, limit)` - Running processes
- `kill_process(pid)` - Terminate processes
- `get_system_info()` - Detailed system information
- `get_performance_insights()` - AI-powered recommendations
- `broadcast_metrics()` - Socket.IO real-time broadcasting

### 3. DocTypes

#### System Monitor Settings (Single DocType)
- Monitoring interval configuration
- Data retention period
- Default alert thresholds (CPU, Memory, Disk)
- Email and notification preferences
- Webhook URL for external integrations

#### System Metric Log
- Stores time-series metric data
- Fields: metric_type, metric_name, value, timestamp, server_name
- Auto-increment naming
- Indexed for fast queries

#### Monitor Alert
- Alert configuration
- Threshold settings
- Notification channel selection
- Recipient management
- Active/Inactive status

#### Alert Log
- Alert trigger history
- Resolution tracking
- Metric value at trigger time

### 4. Dashboard (Phase 2 - Completed)

#### System Monitor Dashboard Page (`/app/system-monitor-dashboard`)

**Overview Cards:**
- CPU Usage with color-coded status (green/yellow/red)
- Memory Usage with GB used display
- Disk Usage with partition information
- Network statistics with connection count

**System Information Panel:**
- Platform and OS details
- Hostname and uptime
- Frappe version
- Database and Redis status

**Process Monitor:**
- Top 10 processes by CPU usage
- Top 10 processes by Memory usage
- Sortable, scrollable tables

**Performance Insights:**
- Real-time performance warnings
- Intelligent recommendations
- Color-coded severity (warning/critical)

**Features:**
- Auto-refresh every 30 seconds
- Real-time Socket.IO updates
- Responsive design
- Beautiful modern UI with animations
- Quick access to Settings

### 5. Scheduled Tasks

Configured in `hooks.py`:

```python
scheduler_events = {
    "cron": {
        "*/1 * * * *": [  # Every minute
            "frappe_monitor.services.alert_engine.check_alerts"
        ]
    },
    "all": [  # Every 5 minutes (Frappe default)
        "frappe_monitor.services.collector.collect_and_store_metrics"
    ],
    "daily": [
        "frappe_monitor.services.aggregator.aggregate_daily_metrics",
        "frappe_monitor.services.storage.cleanup_old_metrics"
    ],
    "hourly": [
        "frappe_monitor.services.aggregator.aggregate_hourly_metrics"
    ]
}
```

### 6. Real-Time Features

- Socket.IO integration via `frappe.realtime`
- Automatic metric broadcasting to connected clients
- Live dashboard updates without page refresh
- Real-time alert notifications

## File Structure

```
frappe_monitor/
├── frappe_monitor/
│   ├── api/
│   │   ├── __init__.py
│   │   └── metrics.py                    # API endpoints
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── collector.py                  # Metric collection
│   │   ├── storage.py                    # Data persistence
│   │   ├── alert_engine.py               # Alert processing
│   │   └── aggregator.py                 # Data aggregation
│   │
│   ├── frappe_monitor/
│   │   ├── doctype/
│   │   │   ├── system_monitor_settings/
│   │   │   ├── system_metric_log/
│   │   │   ├── monitor_alert/
│   │   │   └── alert_log/
│   │   │
│   │   └── page/
│   │       └── system_monitor_dashboard/
│   │           ├── system_monitor_dashboard.json
│   │           ├── system_monitor_dashboard.py
│   │           ├── system_monitor_dashboard.js
│   │           └── system_monitor_dashboard.css
│   │
│   └── hooks.py                          # App configuration
│
├── requirements.txt                       # psutil, redis
└── README.md
```

## How to Use

### 1. Access the Dashboard

Navigate to: **Desk → System Monitor Dashboard**

The dashboard will automatically:
- Load current system metrics
- Display top processes
- Show performance insights
- Auto-refresh every 30 seconds

### 2. Configure Settings

Go to: **System Monitor Settings**

Configure:
- Monitoring interval (default: 30 seconds)
- Data retention (default: 30 days)
- Alert thresholds
- Notification preferences

### 3. Create Alerts

Go to: **Monitor Alert → New**

Example alert configuration:
```
Alert Name: High CPU Usage
Metric Type: CPU
Metric Name: percent
Threshold Type: Above
Threshold Value: 80
Notification Channels: Email, System Notification
Recipients: admin@example.com
```

### 4. View Historical Data

Use the API to query historical metrics:

```javascript
frappe.call({
    method: 'frappe_monitor.api.metrics.get_historical_metrics',
    args: {
        metric_type: 'CPU',
        metric_name: 'percent',
        period: '24h',
        granularity: 'hourly'
    },
    callback: (r) => {
        console.log(r.message);
    }
});
```

## Key Improvements Over frappe_system_monitor

1. ✅ **Historical Data Storage** - Time-series metrics with configurable retention
2. ✅ **Smart Alerting** - Threshold-based alerts with multiple notification channels
3. ✅ **Modern UI** - Responsive dashboard with real-time updates
4. ✅ **Performance Insights** - AI-powered recommendations
5. ✅ **Process Management** - View and manage running processes
6. ✅ **Socket.IO Integration** - Real-time metric streaming
7. ✅ **Configurable** - Extensive settings for customization
8. ✅ **Production Ready** - Proper error handling and logging
9. ✅ **Role-Based Access** - System Manager role required
10. ✅ **Scalable** - Efficient data storage and aggregation

## Testing

### Manual Testing Steps

1. **Dashboard Access**
   ```
   Navigate to /app/system-monitor-dashboard
   Verify all metric cards display correctly
   Check that values update automatically
   ```

2. **Metric Collection**
   ```
   Check System Metric Log list
   Verify metrics are being stored every ~5 minutes
   ```

3. **Alert Testing**
   ```
   Create alert with low threshold (e.g., CPU > 1%)
   Wait 1 minute
   Check Alert Log for triggered alerts
   Verify email/notification received
   ```

4. **Process Monitor**
   ```
   Verify top processes display correctly
   Check sorting by CPU and Memory
   ```

5. **Performance Insights**
   ```
   Verify insights appear when thresholds exceeded
   Check recommendations are relevant
   ```

## Next Steps (Optional Enhancements)

### Phase 3: Historical Analytics
- Add chart visualizations (Chart.js or ECharts)
- Time-series graphs for CPU, Memory, Disk
- Trend analysis and predictions
- Comparative analysis (day-over-day)

### Phase 4: Advanced Features
- Multi-server monitoring
- Custom metrics framework
- Bench Manager integration
- MySQL slow query detection
- Redis performance metrics
- Background job queue monitoring

### Phase 5: Reporting
- Scheduled reports
- PDF export
- Custom dashboards
- Metric correlation analysis

## Dependencies

- **Python**: psutil >= 5.9.0, redis >= 4.0.0
- **Frappe**: Built-in Socket.IO, scheduler, background jobs
- **Frontend**: Native Frappe UI components

## Performance Considerations

- Metric collection runs every ~5 minutes (configurable)
- Alert checking runs every minute
- Dashboard auto-refreshes every 30 seconds
- Historical data aggregated hourly/daily
- Old metrics cleaned up daily based on retention period

## Security

- All endpoints require System Manager role
- Process termination requires explicit permission
- Sensitive data (passwords) never logged
- Webhook URLs validated before use

## Troubleshooting

### Metrics not collecting
```bash
# Check scheduler is running
bench --site bench.manager doctor

# Check logs
tail -f logs/worker.log
```

### Dashboard not loading
```bash
# Rebuild assets
bench build --app frappe_monitor

# Clear cache
bench --site bench.manager clear-cache
```

### Alerts not triggering
```bash
# Check alert configuration
bench --site bench.manager console
>>> frappe.get_all('Monitor Alert', filters={'status': 'Active'})

# Check alert engine logs
tail -f logs/worker.log | grep "Alert Engine"
```

## Conclusion

Successfully implemented a production-ready system monitoring solution for Frappe/ERPNext with:
- ✅ Real-time monitoring
- ✅ Historical data tracking
- ✅ Smart alerting
- ✅ Beautiful dashboard
- ✅ Performance insights
- ✅ Comprehensive API

The app is ready for use and can be extended with additional features as needed.
