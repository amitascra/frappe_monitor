# -*- coding: utf-8 -*-
# Copyright (c) 2024, Amit Kumar and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now_datetime, add_to_date


@frappe.whitelist()
def get_current_metrics():
	"""Get current system metrics - API endpoint for dashboard"""
	if not has_permission():
		frappe.throw(_("You don't have permission to access system metrics"), frappe.PermissionError)
	
	from frappe_monitor.services.collector import collect_system_metrics
	metrics = collect_system_metrics()
	
	if not metrics:
		frappe.throw(_("Failed to collect system metrics"))
	
	return metrics


@frappe.whitelist()
def get_historical_metrics(metric_type, metric_name, period='1h', granularity='raw'):
	"""Get historical metrics data
	
	Args:
		metric_type: CPU, Memory, Disk, Network
		metric_name: percent, bytes_sent, etc.
		period: 1h, 6h, 24h, 7d, 30d
		granularity: raw, hourly, daily
	"""
	if not has_permission():
		frappe.throw(_("You don't have permission to access system metrics"), frappe.PermissionError)
	
	# Calculate date range based on period
	to_date = now_datetime()
	if period == '1h':
		from_date = add_to_date(to_date, hours=-1)
	elif period == '6h':
		from_date = add_to_date(to_date, hours=-6)
	elif period == '24h':
		from_date = add_to_date(to_date, days=-1)
	elif period == '7d':
		from_date = add_to_date(to_date, days=-7)
	elif period == '30d':
		from_date = add_to_date(to_date, days=-30)
	else:
		from_date = add_to_date(to_date, hours=-1)
	
	from frappe_monitor.services.storage import get_metrics_history
	metrics = get_metrics_history(metric_type, metric_name, from_date, to_date, granularity)
	
	return metrics


@frappe.whitelist()
def get_process_list(sort_by='cpu', limit=20):
	"""Get list of running processes
	
	Args:
		sort_by: cpu or memory
		limit: number of processes to return
	"""
	if not has_permission():
		frappe.throw(_("You don't have permission to access system metrics"), frappe.PermissionError)
	
	import psutil
	
	processes = []
	for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status', 'username', 'create_time']):
		try:
			info = proc.info
			processes.append({
				'pid': info['pid'],
				'name': info['name'],
				'cpu_percent': info['cpu_percent'] or 0,
				'memory_percent': info['memory_percent'] or 0,
				'status': info['status'],
				'username': info['username'],
				'create_time': info['create_time']
			})
		except (psutil.NoSuchProcess, psutil.AccessDenied):
			continue
	
	# Sort processes
	if sort_by == 'memory':
		processes.sort(key=lambda x: x['memory_percent'], reverse=True)
	else:
		processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
	
	return processes[:int(limit)]


@frappe.whitelist()
def kill_process(pid):
	"""Kill a process by PID (requires System Manager role)"""
	if not has_permission():
		frappe.throw(_("You don't have permission to kill processes"), frappe.PermissionError)
	
	import psutil
	
	try:
		process = psutil.Process(int(pid))
		process_name = process.name()
		process.terminate()
		
		frappe.log_error(
			f"Process {pid} ({process_name}) terminated by {frappe.session.user}",
			"Frappe Monitor - Process Killed"
		)
		
		return {
			'success': True,
			'message': f'Process {pid} ({process_name}) terminated successfully'
		}
	except psutil.NoSuchProcess:
		frappe.throw(_("Process not found"))
	except psutil.AccessDenied:
		frappe.throw(_("Access denied. Cannot kill this process."))
	except Exception as e:
		frappe.throw(_(f"Error killing process: {str(e)}"))


@frappe.whitelist()
def get_system_info():
	"""Get detailed system information"""
	if not has_permission():
		frappe.throw(_("You don't have permission to access system information"), frappe.PermissionError)
	
	from frappe_monitor.services.collector import get_system_info
	import psutil
	
	system_info = get_system_info()
	
	# Add additional Frappe-specific info
	system_info.update({
		'frappe_version': frappe.__version__,
		'python_version': frappe.utils.get_system_info()['python_version'],
		'database_size': get_database_size(),
		'redis_status': get_redis_status()
	})
	
	return system_info


@frappe.whitelist()
def get_performance_insights():
	"""Get performance insights and recommendations"""
	if not has_permission():
		frappe.throw(_("You don't have permission to access performance insights"), frappe.PermissionError)
	
	insights = []
	
	from frappe_monitor.services.collector import collect_system_metrics
	metrics = collect_system_metrics()
	
	if not metrics:
		return insights
	
	# CPU insights
	if metrics.cpu.percent > 80:
		insights.append({
			'type': 'warning',
			'category': 'CPU',
			'message': f'High CPU usage detected: {metrics.cpu.percent}%',
			'recommendation': 'Consider scaling up CPU resources or optimizing background jobs'
		})
	
	# Memory insights
	if metrics.memory.percent > 85:
		insights.append({
			'type': 'warning',
			'category': 'Memory',
			'message': f'High memory usage detected: {metrics.memory.percent}%',
			'recommendation': 'Consider increasing RAM or optimizing memory-intensive processes'
		})
	
	# Disk insights
	if metrics.disk.partitions:
		for partition in metrics.disk.partitions:
			if partition.percent > 90:
				insights.append({
					'type': 'critical',
					'category': 'Disk',
					'message': f'Critical disk usage on {partition.mountpoint}: {partition.percent}%',
					'recommendation': 'Clean up old files, logs, or backups immediately'
				})
			elif partition.percent > 80:
				insights.append({
					'type': 'warning',
					'category': 'Disk',
					'message': f'High disk usage on {partition.mountpoint}: {partition.percent}%',
					'recommendation': 'Plan for disk cleanup or expansion'
				})
	
	# Swap usage
	if metrics.memory.swap_percent > 50:
		insights.append({
			'type': 'warning',
			'category': 'Memory',
			'message': f'High swap usage: {metrics.memory.swap_percent}%',
			'recommendation': 'System is using swap memory heavily. Consider adding more RAM.'
		})
	
	return insights


def has_permission():
	"""Check if user has System Manager role"""
	return 'System Manager' in frappe.get_roles(frappe.session.user)


def get_database_size():
	"""Get database size in bytes"""
	try:
		result = frappe.db.sql("""
			SELECT 
				SUM(data_length + index_length) as size
			FROM information_schema.TABLES
			WHERE table_schema = %s
		""", (frappe.conf.db_name,), as_dict=True)
		
		return result[0].size if result else 0
	except Exception:
		return 0


def get_redis_status():
	"""Check Redis connection status"""
	try:
		from frappe.utils.redis_wrapper import RedisWrapper
		redis = frappe.cache()
		redis.ping()
		return 'Connected'
	except Exception:
		return 'Disconnected'


@frappe.whitelist()
def broadcast_metrics():
	"""Broadcast current metrics to all connected clients - Manual trigger for testing"""
	if not has_permission():
		frappe.throw(_("You don't have permission to broadcast metrics"), frappe.PermissionError)
	
	from frappe_monitor.services.collector import collect_and_store_metrics
	collect_and_store_metrics()
	
	return {
		'success': True,
		'message': 'Metrics collected and broadcasted via Socket.IO'
	}
