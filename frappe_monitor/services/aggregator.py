# -*- coding: utf-8 -*-
# Copyright (c) 2024, Amit Kumar and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now_datetime, add_to_date


def aggregate_hourly_metrics():
	"""Aggregate metrics for the past hour"""
	try:
		from_time = add_to_date(now_datetime(), hours=-1)
		to_time = now_datetime()
		
		# Aggregate key metrics
		aggregate_metric_type('CPU', 'percent', from_time, to_time, 'hourly')
		aggregate_metric_type('Memory', 'percent', from_time, to_time, 'hourly')
		aggregate_metric_type('Disk', 'percent', from_time, to_time, 'hourly')
		
		frappe.db.commit()
		
	except Exception as e:
		frappe.log_error(f"Error aggregating hourly metrics: {str(e)}", "Frappe Monitor - Aggregator")


def aggregate_daily_metrics():
	"""Aggregate metrics for the past day"""
	try:
		from_time = add_to_date(now_datetime(), days=-1)
		to_time = now_datetime()
		
		# Aggregate key metrics
		aggregate_metric_type('CPU', 'percent', from_time, to_time, 'daily')
		aggregate_metric_type('Memory', 'percent', from_time, to_time, 'daily')
		aggregate_metric_type('Disk', 'percent', from_time, to_time, 'daily')
		
		frappe.db.commit()
		
	except Exception as e:
		frappe.log_error(f"Error aggregating daily metrics: {str(e)}", "Frappe Monitor - Aggregator")


def aggregate_metric_type(metric_type, metric_name, from_time, to_time, interval):
	"""Aggregate a specific metric type over a time period"""
	from frappe_monitor.services.storage import get_metrics_history
	
	aggregated = get_metrics_history(metric_type, metric_name, from_time, to_time, interval)
	
	# Store aggregated data (could be in a separate table for efficiency)
	# For now, we'll just log it
	frappe.logger().info(f"Aggregated {len(aggregated)} {interval} data points for {metric_type}.{metric_name}")
