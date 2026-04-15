# -*- coding: utf-8 -*-
# Copyright (c) 2024, Amit Kumar and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now_datetime


def check_alerts():
	"""Check all active alerts and trigger notifications if thresholds are breached"""
	if not frappe.db.exists('DocType', 'Monitor Alert'):
		# DocType not created yet, skip
		return
	
	try:
		# Get all active alerts
		alerts = frappe.get_all(
			'Monitor Alert',
			filters={'status': 'Active'},
			fields=['name', 'alert_name', 'metric_type', 'metric_name', 'threshold_value', 
			        'threshold_type', 'alert_frequency', 'notification_channels', 'recipients']
		)
		
		# Get current metrics
		from frappe_monitor.services.collector import collect_system_metrics
		current_metrics = collect_system_metrics()
		
		if not current_metrics:
			return
		
		for alert in alerts:
			check_single_alert(alert, current_metrics)
			
	except Exception as e:
		frappe.log_error(f"Error checking alerts: {str(e)}", "Frappe Monitor - Alert Engine")


def check_single_alert(alert, current_metrics):
	"""Check a single alert against current metrics"""
	try:
		# Get the metric value based on alert configuration
		metric_value = get_metric_value(alert.metric_type, alert.metric_name, current_metrics)
		
		if metric_value is None:
			return
		
		# Check if threshold is breached
		is_breached = False
		if alert.threshold_type == 'Above':
			is_breached = metric_value > alert.threshold_value
		elif alert.threshold_type == 'Below':
			is_breached = metric_value < alert.threshold_value
		
		if is_breached:
			# Check if we should send alert (debouncing)
			if should_send_alert(alert.name, alert.alert_frequency):
				send_alert_notification(alert, metric_value)
				log_alert(alert.name, metric_value, 'Triggered')
		else:
			# Check if alert was previously triggered and now resolved
			if was_alert_triggered(alert.name):
				log_alert(alert.name, metric_value, 'Resolved')
				
	except Exception as e:
		frappe.log_error(f"Error checking alert {alert.name}: {str(e)}", "Frappe Monitor - Alert Engine")


def get_metric_value(metric_type, metric_name, metrics):
	"""Extract metric value from collected metrics"""
	try:
		if metric_type == 'CPU':
			if metric_name == 'percent':
				return metrics.cpu.percent
			elif metric_name == 'load_average_1':
				return metrics.cpu.load_average[0]
		elif metric_type == 'Memory':
			if metric_name == 'percent':
				return metrics.memory.percent
		elif metric_type == 'Disk':
			if metric_name == 'percent' and metrics.disk.partitions:
				return metrics.disk.partitions[0].percent
		elif metric_type == 'Network':
			if metric_name == 'connections_count':
				return metrics.network.connections_count
		
		return None
	except Exception as e:
		frappe.log_error(f"Error getting metric value: {str(e)}", "Frappe Monitor - Alert Engine")
		return None


def should_send_alert(alert_name, frequency):
	"""Check if alert should be sent based on frequency settings"""
	if frequency == 'Once':
		# Check if alert was already sent
		last_alert = frappe.get_all(
			'Alert Log',
			filters={'alert': alert_name, 'status': 'Triggered'},
			fields=['creation'],
			order_by='creation desc',
			limit=1
		)
		return len(last_alert) == 0
	else:
		# For 'Repeated', always send
		return True


def was_alert_triggered(alert_name):
	"""Check if alert was previously triggered"""
	last_alert = frappe.get_all(
		'Alert Log',
		filters={'alert': alert_name},
		fields=['status'],
		order_by='creation desc',
		limit=1
	)
	return len(last_alert) > 0 and last_alert[0].status == 'Triggered'


def send_alert_notification(alert, metric_value):
	"""Send alert notification through configured channels"""
	try:
		message = f"Alert: {alert.alert_name}\n"
		message += f"Metric: {alert.metric_type} - {alert.metric_name}\n"
		message += f"Current Value: {metric_value:.2f}\n"
		message += f"Threshold: {alert.threshold_type} {alert.threshold_value}\n"
		message += f"Time: {now_datetime()}"
		
		channels = alert.notification_channels.split(',') if alert.notification_channels else []
		
		# Send email notification
		if 'Email' in channels:
			send_email_alert(alert, message)
		
		# Send in-app notification
		if 'System Notification' in channels:
			send_system_notification(alert, message)
		
		# Webhook notification
		if 'Webhook' in channels:
			send_webhook_alert(alert, message, metric_value)
			
	except Exception as e:
		frappe.log_error(f"Error sending alert notification: {str(e)}", "Frappe Monitor - Alert Engine")


def send_email_alert(alert, message):
	"""Send email alert to recipients"""
	try:
		recipients = alert.recipients.split(',') if alert.recipients else []
		if not recipients:
			return
		
		frappe.sendmail(
			recipients=recipients,
			subject=f"System Alert: {alert.alert_name}",
			message=message,
			delayed=False
		)
	except Exception as e:
		frappe.log_error(f"Error sending email alert: {str(e)}", "Frappe Monitor - Alert Engine")


def send_system_notification(alert, message):
	"""Send in-app notification"""
	try:
		recipients = alert.recipients.split(',') if alert.recipients else []
		for recipient in recipients:
			frappe.publish_realtime(
				'show_alert',
				{
					'message': f"{alert.alert_name}: {message}",
					'indicator': 'red'
				},
				user=recipient.strip()
			)
	except Exception as e:
		frappe.log_error(f"Error sending system notification: {str(e)}", "Frappe Monitor - Alert Engine")


def send_webhook_alert(alert, message, metric_value):
	"""Send webhook notification"""
	try:
		# Get webhook URL from settings
		settings = frappe.get_single('System Monitor Settings')
		if not settings.webhook_url:
			return
		
		import requests
		import json
		
		payload = {
			'alert_name': alert.alert_name,
			'metric_type': alert.metric_type,
			'metric_name': alert.metric_name,
			'current_value': metric_value,
			'threshold_value': alert.threshold_value,
			'threshold_type': alert.threshold_type,
			'message': message,
			'timestamp': str(now_datetime())
		}
		
		requests.post(settings.webhook_url, json=payload, timeout=10)
		
	except Exception as e:
		frappe.log_error(f"Error sending webhook alert: {str(e)}", "Frappe Monitor - Alert Engine")


def log_alert(alert_name, metric_value, status):
	"""Log alert trigger/resolution"""
	try:
		doc = frappe.get_doc({
			'doctype': 'Alert Log',
			'alert': alert_name,
			'metric_value': metric_value,
			'status': status,
			'timestamp': now_datetime()
		})
		doc.insert(ignore_permissions=True)
		frappe.db.commit()
	except Exception as e:
		frappe.log_error(f"Error logging alert: {str(e)}", "Frappe Monitor - Alert Engine")
