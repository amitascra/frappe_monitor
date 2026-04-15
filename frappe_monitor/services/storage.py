# -*- coding: utf-8 -*-
# Copyright (c) 2024, Amit Kumar and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.utils import now_datetime, add_to_date


def store_metrics(metrics):
	"""Store collected metrics in the database"""
	if not metrics:
		return
	
	try:
		# Store CPU metrics
		store_metric('CPU', 'percent', metrics.cpu.percent, metrics.timestamp)
		store_metric('CPU', 'load_average_1', metrics.cpu.load_average[0], metrics.timestamp)
		store_metric('CPU', 'load_average_5', metrics.cpu.load_average[1], metrics.timestamp)
		store_metric('CPU', 'load_average_15', metrics.cpu.load_average[2], metrics.timestamp)
		
		# Store Memory metrics
		store_metric('Memory', 'percent', metrics.memory.percent, metrics.timestamp)
		store_metric('Memory', 'used_bytes', metrics.memory.used, metrics.timestamp)
		store_metric('Memory', 'swap_percent', metrics.memory.swap_percent, metrics.timestamp)
		
		# Store Disk metrics (primary partition only)
		if metrics.disk.partitions:
			primary_disk = metrics.disk.partitions[0]
			store_metric('Disk', 'percent', primary_disk.percent, metrics.timestamp)
			store_metric('Disk', 'used_bytes', primary_disk.used, metrics.timestamp)
		
		# Store Network metrics
		store_metric('Network', 'bytes_sent', metrics.network.bytes_sent, metrics.timestamp)
		store_metric('Network', 'bytes_recv', metrics.network.bytes_recv, metrics.timestamp)
		
		frappe.db.commit()
		
	except Exception as e:
		frappe.log_error(f"Error storing metrics: {str(e)}", "Frappe Monitor - Storage")


def store_metric(metric_type, metric_name, value, timestamp):
	"""Store a single metric value"""
	try:
		doc = frappe.get_doc({
			'doctype': 'System Metric Log',
			'metric_type': metric_type,
			'metric_name': metric_name,
			'value': value,
			'timestamp': timestamp
		})
		doc.insert(ignore_permissions=True)
	except Exception as e:
		frappe.log_error(f"Error storing metric {metric_type}.{metric_name}: {str(e)}", "Frappe Monitor - Storage")


def get_metrics_history(metric_type, metric_name, from_date, to_date, granularity='raw'):
	"""Get historical metrics data"""
	filters = {
		'metric_type': metric_type,
		'metric_name': metric_name,
		'timestamp': ['between', [from_date, to_date]]
	}
	
	metrics = frappe.get_all(
		'System Metric Log',
		filters=filters,
		fields=['timestamp', 'value'],
		order_by='timestamp asc'
	)
	
	if granularity == 'hourly':
		return aggregate_metrics(metrics, 'hour')
	elif granularity == 'daily':
		return aggregate_metrics(metrics, 'day')
	else:
		return metrics


def aggregate_metrics(metrics, interval='hour'):
	"""Aggregate metrics by time interval"""
	from collections import defaultdict
	import datetime
	
	aggregated = defaultdict(list)
	
	for metric in metrics:
		timestamp = metric['timestamp']
		if interval == 'hour':
			key = timestamp.replace(minute=0, second=0, microsecond=0)
		elif interval == 'day':
			key = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
		else:
			key = timestamp
		
		aggregated[key].append(metric['value'])
	
	result = []
	for timestamp, values in sorted(aggregated.items()):
		result.append({
			'timestamp': timestamp,
			'value': sum(values) / len(values),  # Average
			'min': min(values),
			'max': max(values),
			'count': len(values)
		})
	
	return result


def cleanup_old_metrics():
	"""Delete metrics older than retention period"""
	try:
		settings = frappe.get_single('System Monitor Settings')
		retention_days = settings.data_retention_days or 30
		
		cutoff_date = add_to_date(now_datetime(), days=-retention_days)
		
		frappe.db.delete('System Metric Log', {
			'timestamp': ['<', cutoff_date]
		})
		
		frappe.db.commit()
		frappe.log_error(f"Cleaned up metrics older than {retention_days} days", "Frappe Monitor - Cleanup")
		
	except Exception as e:
		frappe.log_error(f"Error cleaning up old metrics: {str(e)}", "Frappe Monitor - Cleanup")
