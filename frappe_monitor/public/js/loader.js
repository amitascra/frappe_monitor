// Load Google Charts from CDN
(function() {
	if (typeof google === 'undefined' || typeof google.charts === 'undefined') {
		var script = document.createElement('script');
		script.src = 'https://www.gstatic.com/charts/loader.js';
		script.async = true;
		document.head.appendChild(script);
	}
})();
