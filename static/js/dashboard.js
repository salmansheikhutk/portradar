// PortRadar Dashboard JavaScript

// Global variables
let currentUser = 'demo_user';

// Utility functions
function showAlert(message, type = 'info', duration = 5000) {
    const alertContainer = document.getElementById('alert-container');
    const alertId = 'alert-' + Date.now();
    
    const alertHtml = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    alertContainer.insertAdjacentHTML('beforeend', alertHtml);
    
    // Auto-dismiss after duration
    setTimeout(() => {
        const alert = document.getElementById(alertId);
        if (alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }
    }, duration);
}

function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(value);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// API helper functions
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status}`);
        }
        
        return data;
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

// User management
function switchUser(userId) {
    currentUser = userId;
    document.getElementById('current-user').textContent = userId;
    showAlert(`Switched to user: ${userId}`, 'info');
    
    // Reload dashboard data
    if (typeof loadDashboardData === 'function') {
        loadDashboardData();
    }
}

// Dashboard data loading
async function loadDashboardData() {
    try {
        // Load all dashboard components
        await Promise.all([
            loadMetrics(),
            loadRecentAlerts(),
            loadActiveWatchlists(),
            loadSystemStatus(),
            loadQuickReference()
        ]);
        
        document.getElementById('last-updated').textContent = new Date().toLocaleTimeString();
    } catch (error) {
        showAlert('Failed to load dashboard data: ' + error.message, 'danger');
    }
}

async function loadMetrics() {
    try {
        // Load watchlists count
        const watchlistsResponse = await apiCall(`/watchlists?user_id=${currentUser}`);
        const watchlistsCount = watchlistsResponse.count || 0;
        document.getElementById('watchlists-count').textContent = watchlistsCount;
        
        // Load alerts count
        const alertsResponse = await apiCall(`/alerts?user_id=${currentUser}&limit=50`);
        const alertsCount = alertsResponse.count || 0;
        document.getElementById('alerts-count').textContent = alertsCount;
        
        // Load trade records count
        const tradeResponse = await apiCall('/stored-data?limit=1');
        document.getElementById('trade-records-count').textContent = tradeResponse.count || 0;
        
        // Calculate unique HS6 codes from watchlists
        let uniqueHS6s = new Set();
        if (watchlistsResponse.watchlists) {
            watchlistsResponse.watchlists.forEach(wl => {
                if (wl.hs6) {
                    wl.hs6.forEach(code => uniqueHS6s.add(code));
                }
            });
        }
        document.getElementById('hs6-count').textContent = uniqueHS6s.size;
        
    } catch (error) {
        console.error('Failed to load metrics:', error);
    }
}

async function loadRecentAlerts() {
    const container = document.getElementById('recent-alerts');
    
    try {
        const response = await apiCall(`/alerts?user_id=${currentUser}&limit=10`);
        const alerts = response.alerts || [];
        
        if (alerts.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="bi bi-bell fs-1"></i>
                    <p class="mt-2">No recent alerts</p>
                    <button class="btn btn-outline-primary btn-sm" onclick="generateAllAlerts()">
                        Generate Alerts
                    </button>
                </div>
            `;
            return;
        }
        
        const tableHTML = `
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Message</th>
                        <th>Score</th>
                        <th>Date</th>
                    </tr>
                </thead>
                <tbody>
                    ${alerts.map(alert => `
                        <tr>
                            <td>
                                <span class="badge ${alert.alert_type === 'mom_change' ? 'bg-warning' : 'bg-info'}">
                                    ${alert.alert_type === 'mom_change' ? 'MoM Change' : 'Volume Threshold'}
                                </span>
                            </td>
                            <td class="text-truncate-2">${alert.message || alert.details?.message || 'N/A'}</td>
                            <td>${alert.score ? alert.score.toFixed(1) : 'N/A'}</td>
                            <td>${formatDate(alert.created_at)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        
        container.innerHTML = tableHTML;
        
    } catch (error) {
        container.innerHTML = `
            <div class="text-center text-danger py-4">
                <i class="bi bi-exclamation-triangle fs-1"></i>
                <p class="mt-2">Failed to load alerts</p>
            </div>
        `;
    }
}

async function loadActiveWatchlists() {
    const container = document.getElementById('active-watchlists');
    
    try {
        const response = await apiCall(`/watchlists?user_id=${currentUser}`);
        const watchlists = response.watchlists || [];
        
        if (watchlists.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="bi bi-binoculars fs-1"></i>
                    <p class="mt-2">No watchlists created yet</p>
                    <button class="btn btn-primary btn-sm" onclick="showCreateWatchlistModal()">
                        Create Your First Watchlist
                    </button>
                </div>
            `;
            return;
        }
        
        const tableHTML = `
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>HS6 Codes</th>
                        <th>Ports</th>
                        <th>Rules</th>
                        <th>Created</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${watchlists.map(wl => `
                        <tr>
                            <td><strong>${wl.name}</strong></td>
                            <td>${(wl.hs6 || []).join(', ') || 'All'}</td>
                            <td>${(wl.ports || []).join(', ') || 'All'}</td>
                            <td>
                                ${wl.rules?.mom_change_threshold ? `MoM: ${wl.rules.mom_change_threshold}%` : ''}
                                ${wl.rules?.volume_threshold ? `Vol: ${formatCurrency(wl.rules.volume_threshold)}` : ''}
                            </td>
                            <td>${formatDate(wl.created_at)}</td>
                            <td>
                                <button class="btn btn-sm btn-outline-primary" onclick="generateWatchlistAlerts(${wl.id})">
                                    <i class="bi bi-bell"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-secondary" onclick="editWatchlist(${wl.id})">
                                    <i class="bi bi-pencil"></i>
                                </button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        
        container.innerHTML = tableHTML;
        
    } catch (error) {
        container.innerHTML = `
            <div class="text-center text-danger py-4">
                <i class="bi bi-exclamation-triangle fs-1"></i>
                <p class="mt-2">Failed to load watchlists</p>
            </div>
        `;
    }
}

async function loadSystemStatus() {
    try {
        // Check database status
        const dbResponse = await apiCall('/test-db');
        const dbStatus = document.getElementById('db-status');
        dbStatus.textContent = dbResponse.status === 'success' ? 'Online' : 'Offline';
        dbStatus.className = `badge ${dbResponse.status === 'success' ? 'bg-success' : 'bg-danger'}`;
        
        // Check API status
        const apiResponse = await apiCall('/test-api');
        const apiStatus = document.getElementById('api-status');
        apiStatus.textContent = apiResponse.success ? 'Online' : 'Offline';
        apiStatus.className = `badge ${apiResponse.success ? 'bg-success' : 'bg-danger'}`;
        
    } catch (error) {
        document.getElementById('db-status').textContent = 'Error';
        document.getElementById('db-status').className = 'badge bg-danger';
        document.getElementById('api-status').textContent = 'Error';
        document.getElementById('api-status').className = 'badge bg-danger';
    }
}

// Dashboard actions
function refreshDashboard() {
    showAlert('Refreshing dashboard...', 'info', 2000);
    loadDashboardData();
}

function showCreateWatchlistModal() {
    const modal = new bootstrap.Modal(document.getElementById('createWatchlistModal'));
    modal.show();
    
    // Load commodity and port data for the dropdowns
    loadWatchlistFormData();
}

async function createWatchlist() {
    const name = document.getElementById('watchlist-name').value.trim();
    const hs6Select = document.getElementById('hs6-codes');
    const portSelect = document.getElementById('port-codes');
    const momThreshold = document.getElementById('mom-threshold').value;
    const volumeThreshold = document.getElementById('volume-threshold').value;
    
    if (!name) {
        showAlert('Please enter a watchlist name', 'warning');
        return;
    }
    
    // Get selected values from multi-select dropdowns
    const hs6Codes = Array.from(hs6Select.selectedOptions).map(option => option.value);
    const portCodes = Array.from(portSelect.selectedOptions).map(option => option.value);
    
    const rules = {};
    if (momThreshold) rules.mom_change_threshold = parseFloat(momThreshold);
    if (volumeThreshold) rules.volume_threshold = parseFloat(volumeThreshold);
    
    try {
        await apiCall('/watchlists', {
            method: 'POST',
            body: JSON.stringify({
                user_id: currentUser,
                name: name,
                hs6: hs6Codes,
                ports: portCodes,
                rules: rules
            })
        });
        
        showAlert('Watchlist created successfully!', 'success');
        
        // Close modal and reset form
        const modal = bootstrap.Modal.getInstance(document.getElementById('createWatchlistModal'));
        modal.hide();
        document.getElementById('createWatchlistForm').reset();
        
        // Reload dashboard
        loadDashboardData();
        
    } catch (error) {
        showAlert('Failed to create watchlist: ' + error.message, 'danger');
    }
}

async function loadWatchlistFormData() {
    try {
        // Load commodities
        const commoditiesResponse = await fetch('/commodities');
        const commodities = await commoditiesResponse.json();
        
        const hs6Select = document.getElementById('hs6-codes');
        hs6Select.innerHTML = ''; // Clear existing options
        
        if (commodities && commodities.length > 0) {
            commodities.forEach(commodity => {
                const option = document.createElement('option');
                option.value = commodity.hs6;
                option.textContent = `${commodity.hs6} - ${commodity.description || 'N/A'}`;
                hs6Select.appendChild(option);
            });
        } else {
            hs6Select.innerHTML = '<option disabled>No commodities available</option>';
        }
        
        // Load ports
        const portsResponse = await fetch('/ports');
        const ports = await portsResponse.json();
        
        const portSelect = document.getElementById('port-codes');
        portSelect.innerHTML = ''; // Clear existing options
        
        if (ports && ports.length > 0) {
            ports.forEach(port => {
                const option = document.createElement('option');
                option.value = port.port_code;
                option.textContent = `${port.port_code} - ${port.port_name || 'N/A'}`;
                portSelect.appendChild(option);
            });
        } else {
            portSelect.innerHTML = '<option disabled>No ports available</option>';
        }
        
    } catch (error) {
        console.error('Failed to load form data:', error);
        // Set fallback options
        document.getElementById('hs6-codes').innerHTML = '<option disabled>Failed to load commodities</option>';
        document.getElementById('port-codes').innerHTML = '<option disabled>Failed to load ports</option>';
    }
}

async function generateAllAlerts() {
    try {
        showAlert('Generating alerts...', 'info', 2000);
        
        const response = await apiCall('/alerts', {
            method: 'POST',
            body: JSON.stringify({
                user_id: currentUser
            })
        });
        
        const alertsGenerated = response.alerts_generated || 0;
        showAlert(`Generated ${alertsGenerated} alert(s)`, alertsGenerated > 0 ? 'success' : 'info');
        
        // Reload dashboard
        loadDashboardData();
        
    } catch (error) {
        showAlert('Failed to generate alerts: ' + error.message, 'danger');
    }
}

async function generateWatchlistAlerts(watchlistId) {
    try {
        showAlert(`Generating alerts for watchlist ${watchlistId}...`, 'info', 2000);
        
        const response = await apiCall('/alerts', {
            method: 'POST',
            body: JSON.stringify({
                watchlist_id: watchlistId
            })
        });
        
        const alertsGenerated = response.alerts_generated || 0;
        showAlert(`Generated ${alertsGenerated} alert(s)`, alertsGenerated > 0 ? 'success' : 'info');
        
        // Reload dashboard
        loadDashboardData();
        
    } catch (error) {
        showAlert('Failed to generate alerts: ' + error.message, 'danger');
    }
}

async function loadQuickReference() {
    try {
        const response = await apiCall('/quick-reference');
        
        if (response.success) {
            // Update commodity badges with names and click handlers
            const commodityContainer = document.getElementById('commodity-badges');
            if (commodityContainer && response.commodities && response.commodities.length > 0) {
                commodityContainer.innerHTML = response.commodities.map(item => 
                    `<span class="badge bg-secondary clickable-badge" 
                           title="${item.description}" 
                           data-hs6="${item.code}"
                           onclick="searchByHS6('${item.code}')">${item.description ? item.description.substring(0, 30) + '...' : item.code}</span>`
                ).join('');
            }
            
            // Update port badges with names and click handlers
            const portContainer = document.getElementById('port-badges');
            if (portContainer && response.ports && response.ports.length > 0) {
                portContainer.innerHTML = response.ports.map(item =>
                    `<span class="badge bg-success clickable-badge" 
                           title="${item.name}" 
                           data-port="${item.code}"
                           onclick="searchByPort('${item.code}')">${item.name || item.code}</span>`
                ).join('');
            }
            
            // Reinitialize tooltips
            if (typeof bootstrap !== 'undefined') {
                const tooltipTriggerList = [].slice.call(document.querySelectorAll('[title]'));
                tooltipTriggerList.map(function (tooltipTriggerEl) {
                    return new bootstrap.Tooltip(tooltipTriggerEl);
                });
            }
        }
    } catch (error) {
        console.warn('Failed to load quick reference:', error);
        // Keep the default static data if API fails
    }
}

async function showHealthStatus() {
    try {
        const [dbResponse, apiResponse, healthResponse] = await Promise.all([
            apiCall('/test-db'),
            apiCall('/test-api'),
            apiCall('/health')
        ]);
        
        const status = `
            Database: ${dbResponse.status === 'success' ? '✅ Online' : '❌ Offline'}\n
            Census API: ${apiResponse.success ? '✅ Online' : '❌ Offline'}\n
            Health: ${healthResponse.status === 'healthy' ? '✅ Healthy' : '❌ Unhealthy'}\n
            Tables: ${dbResponse.tables ? dbResponse.tables.length : 0}
        `;
        
        alert('System Status:\n\n' + status);
        
    } catch (error) {
        showAlert('Failed to check system status: ' + error.message, 'danger');
    }
}

// Placeholder functions for future implementation
function editWatchlist(watchlistId) {
    showAlert(`Edit watchlist ${watchlistId} - Coming soon!`, 'info');
}

// Search functions for quick reference badges
function searchByHS6(hs6Code) {
    // Redirect to trade data page with HS6 filter
    window.location.href = `/trade-data-page?hs6=${hs6Code}`;
}

function searchByPort(portCode) {
    // Redirect to trade data page with port filter
    window.location.href = `/trade-data-page?port=${portCode}`;
}

// Load sample data function
window.loadSampleData = async function() {
    try {
        showAlert('Loading sample trade data...', 'info');
        const response = await fetch('/trade-data?hs6_codes=850440,847130,854230&time_period=2024-01');
        const data = await response.json();
        
        if (data.success) {
            showAlert('Sample trade data loaded successfully! Refreshing dashboard...', 'success');
            // Refresh the dashboard after a short delay
            setTimeout(() => {
                location.reload();
            }, 2000);
        } else {
            showAlert('Failed to load sample data: ' + data.message, 'danger');
        }
    } catch (error) {
        showAlert('Error loading sample data: ' + error.message, 'danger');
    }
};

// Initialize tooltips for badges if Bootstrap is available
document.addEventListener('DOMContentLoaded', function() {
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[title]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
});
