/**
 * PME-X Dashboard JavaScript
 * Handles dynamic functionality for the dashboard
 */

document.addEventListener('DOMContentLoaded', function() {
    // Refresh button functionality
    const refreshBtn = document.getElementById('refreshData');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing...';
            refreshBtn.disabled = true;
            
            // Reload the page after a short delay
            setTimeout(function() {
                window.location.reload();
            }, 1000);
        });
    }
    
    // Chain selector dropdown
    const chainSelector = document.getElementById('chainSelector');
    if (chainSelector) {
        // Fetch available chains
        fetch('/api/stats')
            .then(response => response.json())
            .then(data => {
                // Create dropdown menu
                const dropdown = document.createElement('ul');
                dropdown.className = 'dropdown-menu';
                
                // Add "All Chains" option
                const allChainsItem = document.createElement('li');
                const allChainsLink = document.createElement('a');
                allChainsLink.className = 'dropdown-item';
                allChainsLink.href = '#';
                allChainsLink.textContent = 'All Chains';
                allChainsLink.addEventListener('click', function(e) {
                    e.preventDefault();
                    filterByChain('all');
                    chainSelector.innerHTML = '<i class="fas fa-filter"></i> All Chains';
                });
                allChainsItem.appendChild(allChainsLink);
                dropdown.appendChild(allChainsItem);
                
                // Add divider
                const divider = document.createElement('li');
                divider.innerHTML = '<hr class="dropdown-divider">';
                dropdown.appendChild(divider);
                
                // Add chains
                if (data.chain_stats) {
                    data.chain_stats.forEach(chain => {
                        const item = document.createElement('li');
                        const link = document.createElement('a');
                        link.className = 'dropdown-item';
                        link.href = '#';
                        
                        // Add status indicator
                        let statusClass = '';
                        if (chain.status === 'active') {
                            statusClass = 'text-success';
                        } else if (chain.status === 'inactive') {
                            statusClass = 'text-secondary';
                        } else if (chain.status === 'congested') {
                            statusClass = 'text-warning';
                        }
                        
                        link.innerHTML = `<i class="fas fa-circle ${statusClass}" style="font-size: 8px;"></i> ${chain.name}`;
                        
                        link.addEventListener('click', function(e) {
                            e.preventDefault();
                            filterByChain(chain.name);
                            chainSelector.innerHTML = `<i class="fas fa-filter"></i> ${chain.name}`;
                        });
                        
                        item.appendChild(link);
                        dropdown.appendChild(item);
                    });
                }
                
                // Create dropdown
                const dropdownContainer = document.createElement('div');
                dropdownContainer.className = 'dropdown';
                
                chainSelector.parentNode.insertBefore(dropdownContainer, chainSelector.nextSibling);
                dropdownContainer.appendChild(chainSelector);
                dropdownContainer.appendChild(dropdown);
                
                // Initialize Bootstrap dropdown
                new bootstrap.Dropdown(chainSelector);
            })
            .catch(error => console.error('Error fetching chains:', error));
    }
    
    // Function to filter content by chain
    function filterByChain(chainName) {
        // Update UI based on selected chain
        if (chainName === 'all') {
            // Show all chains
            document.querySelectorAll('[data-chain]').forEach(el => {
                el.style.display = '';
            });
        } else {
            // Show only selected chain
            document.querySelectorAll('[data-chain]').forEach(el => {
                if (el.getAttribute('data-chain') === chainName) {
                    el.style.display = '';
                } else {
                    el.style.display = 'none';
                }
            });
        }
        
        // If on dashboard, update stats
        updateDashboardStats(chainName);
    }
    
    // Update dashboard stats based on selected chain
    function updateDashboardStats(chainName) {
        const totalProfitEl = document.querySelector('.stats-card .total-profit');
        const totalTradesEl = document.querySelector('.stats-card .total-trades');
        
        if (!totalProfitEl || !totalTradesEl) {
            return;
        }
        
        // Fetch stats
        fetch('/api/stats')
            .then(response => response.json())
            .then(data => {
                if (chainName === 'all') {
                    // Show totals
                    if (totalProfitEl) {
                        totalProfitEl.textContent = '$' + data.total_profit.toFixed(2);
                    }
                    if (totalTradesEl) {
                        totalTradesEl.textContent = data.total_trades;
                    }
                } else {
                    // Show chain-specific stats
                    const chainData = data.chain_stats.find(chain => chain.name === chainName);
                    if (chainData) {
                        if (totalProfitEl) {
                            totalProfitEl.textContent = '$' + chainData.profit.toFixed(2);
                        }
                        if (totalTradesEl) {
                            totalTradesEl.textContent = chainData.trade_count;
                        }
                    }
                }
            })
            .catch(error => console.error('Error updating stats:', error));
    }
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Handle alert dismissal
    document.querySelectorAll('.alert .btn-close').forEach(button => {
        button.addEventListener('click', function() {
            this.closest('.alert').remove();
        });
    });
    
    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        document.querySelectorAll('.alert:not(.alert-permanent)').forEach(alert => {
            // Create and trigger a fade-out transition
            alert.style.transition = 'opacity 1s';
            alert.style.opacity = '0';
            
            // Remove from DOM after transition
            setTimeout(function() {
                if (alert.parentNode) {
                    alert.parentNode.removeChild(alert);
                }
            }, 1000);
        });
    }, 5000);
    
    // Dark mode toggle
    const darkModeToggle = document.querySelector('.dark-mode-toggle');
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', function() {
            document.body.classList.toggle('dark-mode');
            
            // Save preference to localStorage
            if (document.body.classList.contains('dark-mode')) {
                localStorage.setItem('darkMode', 'enabled');
            } else {
                localStorage.setItem('darkMode', 'disabled');
            }
        });
        
        // Check for saved preference
        if (localStorage.getItem('darkMode') === 'enabled') {
            document.body.classList.add('dark-mode');
        }
    }
    
    // Handle auto-refresh
    function setupAutoRefresh() {
        // Check if auto-refresh is enabled
        const autoRefreshEnabled = localStorage.getItem('autoRefresh') === 'enabled';
        const autoRefreshInterval = parseInt(localStorage.getItem('autoRefreshInterval')) || 60; // Default to 60 seconds
        
        if (autoRefreshEnabled) {
            // Set up interval
            const refreshIntervalId = setInterval(function() {
                // Only refresh if the page is visible
                if (!document.hidden) {
                    // Fetch fresh data
                    fetchDashboardData();
                }
            }, autoRefreshInterval * 1000);
            
            // Store interval ID
            window.autoRefreshIntervalId = refreshIntervalId;
        }
    }
    
    // Fetch dashboard data without reloading the page
    function fetchDashboardData() {
        // Only run on dashboard page
        if (!window.location.pathname.endsWith('/dashboard') && !window.location.pathname.endsWith('/')) {
            return;
        }
        
        fetch('/api/stats')
            .then(response => response.json())
            .then(data => {
                // Update cards with new data
                updateDashboardUI(data);
            })
            .catch(error => console.error('Error fetching dashboard data:', error));
    }
    
    // Update dashboard UI with new data
    function updateDashboardUI(data) {
        // Update total profit
        const totalProfitEl = document.querySelector('.total-profit');
        if (totalProfitEl) {
            totalProfitEl.textContent = '$' + data.total_profit.toFixed(2);
        }
        
        // Update total trades
        const totalTradesEl = document.querySelector('.total-trades');
        if (totalTradesEl) {
            totalTradesEl.textContent = data.total_trades;
        }
        
        // Update recent trades table
        const recentTradesTable = document.querySelector('.recent-trades-table tbody');
        if (recentTradesTable && data.recent_trades) {
            // Clear existing rows
            recentTradesTable.innerHTML = '';
            
            // Add new rows
            data.recent_trades.forEach(trade => {
                const row = document.createElement('tr');
                
                // Format date
                const date = new Date(trade.created_at);
                const formattedDate = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
                
                // Format strategy type
                const strategyType = trade.strategy_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                
                // Create row HTML
                row.innerHTML = `
                    <td>${formattedDate}</td>
                    <td>${strategyType}</td>
                    <td>${trade.chain}</td>
                    <td class="${trade.net_profit > 0 ? 'text-success' : 'text-danger'} text-end">
                        $${trade.net_profit.toFixed(2)}
                    </td>
                `;
                
                recentTradesTable.appendChild(row);
            });
        }
        
        // Update charts if they exist
        if (window.profitChart && data.chart_data) {
            window.profitChart.data.labels = data.chart_data.map(item => item.date);
            window.profitChart.data.datasets[0].data = data.chart_data.map(item => item.profit);
            window.profitChart.update();
        }
    }
    
    // Start auto-refresh
    setupAutoRefresh();
});