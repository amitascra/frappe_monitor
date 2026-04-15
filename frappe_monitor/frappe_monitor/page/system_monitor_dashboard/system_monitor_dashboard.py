# -*- coding: utf-8 -*-
# Copyright (c) 2024, Amit Kumar and contributors
# For license information, please see license.txt

import frappe
import psutil
from frappe_monitor.services.collector import collect_system_metrics

no_cache = 1

def get_context(context):
	context.no_cache = 1
	
	# Collect initial metrics for server-side rendering
	try:
		metrics = collect_system_metrics()
		
		# Get top processes directly
		top_cpu_processes = get_top_processes('cpu', 10)
		top_memory_processes = get_top_processes('memory', 10)
		
		# Get performance insights
		insights = get_insights(metrics)
		
		# Calculate health score
		health_score = calculate_health_score(metrics)
		
		# Pass data to template
		context.metrics = metrics
		context.top_cpu_processes = top_cpu_processes
		context.top_memory_processes = top_memory_processes
		context.insights = insights
		context.health_score = health_score
		
	except Exception as e:
		frappe.log_error(f"Error in get_context: {str(e)}", "Frappe Monitor - Page")
		context.metrics = None
		context.top_cpu_processes = []
		context.top_memory_processes = []
		context.insights = []
		context.health_score = 0
	
	return context


def get_top_processes(sort_by='cpu', limit=10):
	"""Get top processes without permission checks"""
	processes = []
	for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status', 'username']):
		try:
			info = proc.info
			processes.append({
				'pid': info['pid'],
				'name': info['name'],
				'cpu_percent': info['cpu_percent'] or 0,
				'memory_percent': info['memory_percent'] or 0,
				'status': info['status'],
				'username': info['username']
			})
		except (psutil.NoSuchProcess, psutil.AccessDenied):
			continue
	
	if sort_by == 'memory':
		processes.sort(key=lambda x: x['memory_percent'], reverse=True)
	else:
		processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
	
	return processes[:limit]


def get_insights(metrics):
	"""Get performance insights without permission checks"""
	insights = []
	
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
	
	return insights


def calculate_health_score(metrics):
	"""Calculate overall system health score (0-100)"""
	if not metrics:
		return 0
	
	score = 100
	
	# CPU penalty
	if metrics.cpu.percent > 90:
		score -= 30
	elif metrics.cpu.percent > 75:
		score -= 20
	elif metrics.cpu.percent > 50:
		score -= 10
	
	# Memory penalty
	if metrics.memory.percent > 95:
		score -= 30
	elif metrics.memory.percent > 85:
		score -= 20
	elif metrics.memory.percent > 70:
		score -= 10
	
	# Disk penalty
	if metrics.disk.partitions:
		disk_percent = metrics.disk.partitions[0].percent
		if disk_percent > 95:
			score -= 30
		elif disk_percent > 85:
			score -= 20
		elif disk_percent > 70:
			score -= 10
	
	return max(0, score)
