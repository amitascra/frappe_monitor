frappe.pages['system-monitor-dashboard'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('System Monitor Dashboard'),
		single_column: true,
	});

	// Render template
	$(frappe.render_template('system_monitor_dashboard')).appendTo(page.body.addClass('no-border'));

	// Action button handlers
	$('#refresh-btn').on('click', function() {
		window.location.reload();
	});
	
	$('#test-socketio-btn').on('click', function() {
		frappe.call({
			method: 'frappe_monitor.api.metrics.broadcast_metrics',
			callback: function(r) {
				if (r.message) {
					frappe.show_alert({
						message: __('Socket.IO broadcast triggered! Check console for 🔴 emoji'),
						indicator: 'green'
					});
				}
			}
		});
	});
	
	$('#alerts-btn').on('click', function() {
		frappe.set_route('List', 'Monitor Alert');
	});
	
	$('#settings-btn').on('click', function() {
		frappe.set_route('Form', 'System Monitor Settings');
	});
	
	$('#clear-cache-btn').on('click', function() {
		frappe.call({
			method: 'frappe.sessions.clear',
			callback: function() {
				frappe.show_alert({message: __('Cache Cleared'), indicator: 'green'});
			}
		});
	});

	// Load Google Charts
	frappe.require('/assets/frappe_monitor/js/loader.js', () => {
		function waitForGoogle() {
			if (typeof google !== 'undefined' && google.charts) {
				google.charts.load('current', {'packages':['gauge', 'corechart']});
				google.charts.setOnLoadCallback(function() {
					console.log('Google Charts loaded successfully');
					initialize_all();
				});
			} else {
				setTimeout(waitForGoogle, 100);
			}
		}
		waitForGoogle();
	});

	// Setup Socket.IO real-time listener
	frappe.realtime.on('system_metrics_update', function(data) {
		console.log('🔴 LIVE Socket.IO update received:', data);
		update_all_sections(data);
	});
};

// Initialize all sections
function initialize_all() {
	frappe.call({
		method: 'frappe_monitor.api.metrics.get_current_metrics',
		callback: function(r) {
			if (r.message) {
				update_all_sections(r.message);
			}
		}
	});
	
	load_processes();
	load_insights();
}

// Update all sections with new data
function update_all_sections(data) {
	update_health_score(data);
	update_system_info(data);
	render_gauge(data);
	update_network_stats(data.network);
	render_cpu_frequency(data.cpu);
}

// Render gauge charts
function render_gauge(r) {
	if (typeof google === 'undefined' || !google.visualization) {
		return;
	}

	let disk_percent = 0;
	if (r.disk.partitions && r.disk.partitions.length > 0) {
		disk_percent = r.disk.partitions[0].percent;
	}

	var data = google.visualization.arrayToDataTable([
		['Label', 'Value'],
		['RAM', r.memory.percent],
		['CPU', r.cpu.percent],
		['Disk', disk_percent]
	]);

	var options = {
		width: '100%', 
		height: 280,
		redFrom: 90, 
		redTo: 100,
		yellowFrom: 75, 
		yellowTo: 90,
		minorTicks: 5
	};

	var chart = new google.visualization.Gauge(document.getElementById('chart_div'));
	chart.draw(data, options);
}

// Render CPU frequency chart
function render_cpu_frequency(cpu_data) {
	if (typeof google === 'undefined' || !google.visualization) {
		return;
	}

	let cpu_freq_list = [['CPU']];
	let per_cpu = cpu_data.per_cpu_percent || [];
	
	for (let i = 0; i < per_cpu.length; i++) {
		cpu_freq_list[0].push(`Core ${i + 1}`);
	}
	
	let values = [''];
	for (let i = 0; i < per_cpu.length; i++) {
		values.push(per_cpu[i]);
	}
	cpu_freq_list.push(values);

	var data = google.visualization.arrayToDataTable(cpu_freq_list);

	var options = {
		title: `CPU Usage per Core (Max: ${cpu_data.frequency_max || 'N/A'} MHz)`,
		hAxis: {title: 'CPU Core', titleTextStyle: {color: '#333'}},
		vAxis: {minValue: 0, maxValue: 100, title: 'Usage %'},
		colors: ['#4285F4']
	};

	var chart = new google.visualization.AreaChart(document.getElementById('cpu_frequency_div'));
	chart.draw(data, options);
}

// Update health score
function update_health_score(data) {
	let score = 100;
	
	if (data.cpu.percent > 90) score -= 30;
	else if (data.cpu.percent > 75) score -= 20;
	else if (data.cpu.percent > 50) score -= 10;
	
	if (data.memory.percent > 95) score -= 30;
	else if (data.memory.percent > 85) score -= 20;
	else if (data.memory.percent > 70) score -= 10;
	
	if (data.disk.partitions && data.disk.partitions.length > 0) {
		let disk_percent = data.disk.partitions[0].percent;
		if (disk_percent > 95) score -= 30;
		else if (disk_percent > 85) score -= 20;
		else if (disk_percent > 70) score -= 10;
	}
	
	score = Math.max(0, score);
	$('#health-score').text(score + '/100');
	
	let icon = $('#health-icon');
	let badge = $('#health-badge');
	
	icon.removeClass('fa-check-circle fa-exclamation-triangle fa-times-circle');
	badge.removeClass('badge-success badge-warning badge-danger');
	
	if (score >= 80) {
		icon.addClass('fa-check-circle').css('color', '#28a745');
		badge.addClass('badge-success').text('Excellent');
	} else if (score >= 60) {
		icon.addClass('fa-exclamation-triangle').css('color', '#ffc107');
		badge.addClass('badge-warning').text('Fair');
	} else {
		icon.addClass('fa-times-circle').css('color', '#dc3545');
		badge.addClass('badge-danger').text('Poor');
	}
}

// Update system info
function update_system_info(data) {
	let html = `
		<table class="table table-bordered">
			<tr>
				<th>Platform</th>
				<td>${data.system.platform} ${data.system.platform_release}</td>
			</tr>
			<tr>
				<th>Hostname</th>
				<td>${data.system.hostname}</td>
			</tr>
			<tr>
				<th>Uptime</th>
				<td>${data.system.uptime_string}</td>
			</tr>
			<tr>
				<th>Boot Time</th>
				<td>${data.system.boot_time}</td>
			</tr>
		</table>
	`;
	$('#system-info-table').html(html);
}

// Update network stats
function update_network_stats(network) {
	let html = `
		<div class="stat-item">
			<div class="stat-label">Bytes Sent</div>
			<div class="stat-value">${(network.bytes_sent / 1073741824).toFixed(2)} GB</div>
		</div>
		<div class="stat-item">
			<div class="stat-label">Bytes Received</div>
			<div class="stat-value">${(network.bytes_recv / 1073741824).toFixed(2)} GB</div>
		</div>
		<div class="stat-item">
			<div class="stat-label">Active Connections</div>
			<div class="stat-value">${network.connections_count}</div>
		</div>
		<div class="stat-item">
			<div class="stat-label">Packets Sent</div>
			<div class="stat-value">${network.packets_sent.toLocaleString()}</div>
		</div>
		<div class="stat-item">
			<div class="stat-label">Packets Received</div>
			<div class="stat-value">${network.packets_recv.toLocaleString()}</div>
		</div>
	`;
	$('#network-stats').html(html);
}

// Load processes
function load_processes() {
	frappe.call({
		method: 'frappe_monitor.api.metrics.get_process_list',
		args: {sort_by: 'cpu', limit: 10},
		callback: function(r) {
			if (r.message) {
				update_process_table('#top-cpu-processes', r.message, 'cpu_percent');
			}
		}
	});
	
	frappe.call({
		method: 'frappe_monitor.api.metrics.get_process_list',
		args: {sort_by: 'memory', limit: 10},
		callback: function(r) {
			if (r.message) {
				update_process_table('#top-memory-processes', r.message, 'memory_percent');
			}
		}
	});
}

// Update process table
function update_process_table(selector, processes, metric) {
	let html = `
		<table class="table table-sm table-bordered">
			<thead>
				<tr>
					<th>PID</th>
					<th>Name</th>
					<th>User</th>
					<th>${metric === 'cpu_percent' ? 'CPU %' : 'Memory %'}</th>
				</tr>
			</thead>
			<tbody>
	`;
	
	processes.forEach(proc => {
		html += `<tr>
			<td>${proc.pid}</td>
			<td>${proc.name}</td>
			<td>${proc.username}</td>
			<td>${proc[metric].toFixed(1)}%</td>
		</tr>`;
	});
	
	html += '</tbody></table>';
	$(selector).html(html);
}

// Load insights
function load_insights() {
	frappe.call({
		method: 'frappe_monitor.api.metrics.get_performance_insights',
		callback: function(r) {
			if (r.message && r.message.length > 0) {
				let html = '';
				r.message.forEach(insight => {
					let icon = insight.type === 'critical' ? 'fa-exclamation-circle' : 'fa-exclamation-triangle';
					html += `
						<div class="insight-item insight-${insight.type}">
							<div class="insight-icon">
								<i class="fa ${icon}"></i>
							</div>
							<div class="insight-content">
								<strong>${insight.category}:</strong> ${insight.message}
								<div class="insight-recommendation">
									<i class="fa fa-lightbulb-o"></i> ${insight.recommendation}
								</div>
							</div>
						</div>
					`;
				});
				$('#insights-container').html(html);
			} else {
				$('#insights-container').html('<p class="text-muted">No performance issues detected. System is running smoothly.</p>');
			}
		}
	});
}
