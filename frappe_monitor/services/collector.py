# -*- coding: utf-8 -*-
# Copyright (c) 2024, Amit Kumar and contributors
# For license information, please see license.txt

import frappe
import psutil
import platform
import datetime
from frappe.utils import now_datetime, get_datetime


def collect_system_metrics():
	"""Collect comprehensive system metrics using psutil"""
	try:
		metrics = frappe._dict({
			'timestamp': now_datetime(),
			'cpu': get_cpu_metrics(),
			'memory': get_memory_metrics(),
			'disk': get_disk_metrics(),
			'network': get_network_metrics(),
			'processes': get_process_metrics(),
			'system': get_system_info()
		})
		return metrics
	except Exception as e:
		frappe.log_error(f"Error collecting system metrics: {str(e)}", "Frappe Monitor - Collector")
		return None


def get_cpu_metrics():
	"""Get CPU usage metrics"""
	cpu_freq = psutil.cpu_freq()
	return frappe._dict({
		'percent': psutil.cpu_percent(interval=1),
		'count': psutil.cpu_count(),
		'count_logical': psutil.cpu_count(logical=True),
		'count_physical': psutil.cpu_count(logical=False),
		'frequency_current': cpu_freq.current if cpu_freq else 0,
		'frequency_min': cpu_freq.min if cpu_freq else 0,
		'frequency_max': cpu_freq.max if cpu_freq else 0,
		'per_cpu_percent': psutil.cpu_percent(interval=1, percpu=True),
		'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
	})


def get_memory_metrics():
	"""Get memory usage metrics"""
	virtual_mem = psutil.virtual_memory()
	swap_mem = psutil.swap_memory()
	
	return frappe._dict({
		'total': virtual_mem.total,
		'available': virtual_mem.available,
		'used': virtual_mem.used,
		'free': virtual_mem.free,
		'percent': virtual_mem.percent,
		'swap_total': swap_mem.total,
		'swap_used': swap_mem.used,
		'swap_free': swap_mem.free,
		'swap_percent': swap_mem.percent
	})


def get_disk_metrics():
	"""Get disk usage metrics for all partitions"""
	partitions = []
	
	for partition in psutil.disk_partitions():
		try:
			usage = psutil.disk_usage(partition.mountpoint)
			partitions.append(frappe._dict({
				'device': partition.device,
				'mountpoint': partition.mountpoint,
				'fstype': partition.fstype,
				'total': usage.total,
				'used': usage.used,
				'free': usage.free,
				'percent': usage.percent
			}))
		except PermissionError:
			# Skip partitions we don't have permission to access
			continue
	
	# Get disk I/O counters
	disk_io = psutil.disk_io_counters()
	
	return frappe._dict({
		'partitions': partitions,
		'io_read_count': disk_io.read_count if disk_io else 0,
		'io_write_count': disk_io.write_count if disk_io else 0,
		'io_read_bytes': disk_io.read_bytes if disk_io else 0,
		'io_write_bytes': disk_io.write_bytes if disk_io else 0,
		'io_read_time': disk_io.read_time if disk_io else 0,
		'io_write_time': disk_io.write_time if disk_io else 0
	})


def get_network_metrics():
	"""Get network usage metrics"""
	net_io = psutil.net_io_counters()
	
	return frappe._dict({
		'bytes_sent': net_io.bytes_sent,
		'bytes_recv': net_io.bytes_recv,
		'packets_sent': net_io.packets_sent,
		'packets_recv': net_io.packets_recv,
		'errin': net_io.errin,
		'errout': net_io.errout,
		'dropin': net_io.dropin,
		'dropout': net_io.dropout,
		'connections_count': len(psutil.net_connections())
	})


def get_process_metrics(limit=10):
	"""Get top processes by CPU and memory usage"""
	processes = []
	
	for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status', 'username']):
		try:
			processes.append(frappe._dict({
				'pid': proc.info['pid'],
				'name': proc.info['name'],
				'cpu_percent': proc.info['cpu_percent'] or 0,
				'memory_percent': proc.info['memory_percent'] or 0,
				'status': proc.info['status'],
				'username': proc.info['username']
			}))
		except (psutil.NoSuchProcess, psutil.AccessDenied):
			continue
	
	# Sort by CPU usage and get top N
	top_cpu = sorted(processes, key=lambda x: x.cpu_percent, reverse=True)[:limit]
	# Sort by memory usage and get top N
	top_memory = sorted(processes, key=lambda x: x.memory_percent, reverse=True)[:limit]
	
	return frappe._dict({
		'total_count': len(processes),
		'top_cpu': top_cpu,
		'top_memory': top_memory
	})


def get_system_info():
	"""Get system information"""
	boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
	uptime = datetime.datetime.now() - boot_time
	
	return frappe._dict({
		'platform': platform.system(),
		'platform_release': platform.release(),
		'platform_version': platform.version(),
		'architecture': platform.machine(),
		'hostname': platform.node(),
		'processor': platform.processor(),
		'boot_time': boot_time.strftime("%Y-%m-%d %H:%M:%S"),
		'uptime_seconds': int(uptime.total_seconds()),
		'uptime_string': str(uptime).split('.')[0]  # Remove microseconds
	})


def collect_and_store_metrics():
	"""Scheduler task to collect and store metrics"""
	try:
		metrics = collect_system_metrics()
		if metrics:
			from frappe_monitor.services.storage import store_metrics
			store_metrics(metrics)
			
			# Broadcast to ALL connected clients via Socket.IO
			frappe.publish_realtime(
				'system_metrics_update',
				metrics,
				after_commit=True
			)
			
			frappe.logger().info("Metrics collected and broadcasted via Socket.IO")
	except Exception as e:
		frappe.log_error(f"Error in collect_and_store_metrics: {str(e)}", "Frappe Monitor - Collector")
