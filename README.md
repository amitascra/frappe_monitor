### Frappe Monitor

Advanced system monitoring and alerting for Frappe/ERPNext

### Features

- **Real-time System Metrics**: Monitor CPU, Memory, Disk, and Network usage in real-time
- **Historical Data**: Track metrics over time with configurable retention periods
- **Smart Alerting**: Set threshold-based alerts with email and in-app notifications
- **Process Management**: View and manage running processes
- **Performance Insights**: Get AI-powered recommendations for system optimization
- **Beautiful Dashboard**: Modern, responsive UI with live updates
- **Socket.IO Integration**: Real-time metric streaming to connected clients

### Installation

```bash
# Get the app
cd frappe-bench
bench get-app https://github.com/yourusername/frappe_monitor
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/frappe_monitor
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


### License

mit
