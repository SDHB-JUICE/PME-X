// Show/hide error details
                    const errorCard = document.getElementById('error-details-card');
                    if (status.toLowerCase() === 'failed') {
                        errorCard.style.display = 'block';
                        document.getElementById('tx-error-message').textContent = 'Transaction failed. See details on the explorer.';
                    } else {
                        errorCard.style.display = 'none';
                    }
                    
                    // Update explorer link
                    updateExplorerLink(txHash, chain);
                    
                    // Show modal
                    const modal = new bootstrap.Modal(document.getElementById('transactionDetailsModal'));
                    modal.show();
                }
            });
        });
    }
    
    // Update explorer link based on chain
    function updateExplorerLink(txHash, chain) {
        const explorerUrl = getExplorerUrl(chain);
        const link = document.getElementById('tx-explorer-link');
        link.href = `${explorerUrl}/tx/${txHash}`;
    }
    
    // Get explorer URL for chain
    function getExplorerUrl(chain) {
        const chainInfo = {
            'ethereum': 'https://etherscan.io',
            'polygon': 'https://polygonscan.com',
            'bsc': 'https://bscscan.com',
            'arbitrum-one': 'https://arbiscan.io',
            'optimism': 'https://optimistic.etherscan.io',
            'avalanche': 'https://snowtrace.io',
            'fantom': 'https://ftmscan.com',
            'base': 'https://basescan.org'
        };
        
        return chainInfo[chain.toLowerCase()] || 'https://etherscan.io';
    }
    
    // Gas Analytics
    const gasAnalyticsBtn = document.getElementById('gasAnalyticsBtn');
    const gasAnalyticsWalletSelect = document.getElementById('gas-analytics-wallet-select');
    const gasPeriodButtons = document.querySelectorAll('.gas-period');
    
    if (gasAnalyticsBtn) {
        gasAnalyticsBtn.addEventListener('click', function() {
            const modal = new bootstrap.Modal(document.getElementById('gasAnalyticsModalFull'));
            modal.show();
        });
    }
    
    if (gasAnalyticsWalletSelect) {
        gasAnalyticsWalletSelect.addEventListener('change', function() {
            const walletId = this.value;
            
            if (!walletId) {
                return;
            }
            
            // Get selected period
            let period = '30d';
            document.querySelectorAll('.gas-period').forEach(btn => {
                if (btn.classList.contains('active')) {
                    period = btn.getAttribute('data-period');
                }
            });
            
            // Load gas analytics
            loadGasAnalytics(walletId, period);
        });
    }
    
    if (gasPeriodButtons.length > 0) {
        gasPeriodButtons.forEach(button => {
            button.addEventListener('click', function() {
                // Update active state
                document.querySelectorAll('.gas-period').forEach(btn => {
                    btn.classList.remove('active');
                });
                this.classList.add('active');
                
                // Get selected wallet and period
                const walletId = document.getElementById('gas-analytics-wallet-select').value;
                const period = this.getAttribute('data-period');
                
                if (!walletId) {
                    return;
                }
                
                // Load gas analytics
                loadGasAnalytics(walletId, period);
            });
        });
    }
    
    function loadGasAnalytics(walletId, period) {
        // Show loading state
        document.getElementById('gas-analytics-loading').style.display = 'block';
        document.getElementById('gas-analytics-content').style.display = 'none';
        
        // Fetch gas analytics data
        fetch(`/api/wallet/${walletId}/gas_analytics?period=${period}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Generate gas analytics content
                    const analytics = data.analytics;
                    
                    // Create HTML content
                    let content = `
                        <div class="row mb-3">
                            <div class="col-md-3">
                                <div class="card bg-light">
                                    <div class="card-body text-center">
                                        <h6 class="card-title">Total Gas Used</h6>
                                        <h3>${analytics.total_gas_used.toLocaleString()}</h3>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card bg-light">
                                    <div class="card-body text-center">
                                        <h6 class="card-title">Gas Cost (ETH)</h6>
                                        <h3>${analytics.total_gas_cost_eth.toFixed(4)}</h3>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card bg-light">
                                    <div class="card-body text-center">
                                        <h6 class="card-title">Gas Cost (USD)</h6>
                                        <h3>${analytics.total_gas_cost_usd.toFixed(2)}</h3>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card bg-light">
                                    <div class="card-body text-center">
                                        <h6 class="card-title">Avg Gas (Gwei)</h6>
                                        <h3>${analytics.avg_gas_price_gwei.toFixed(2)}</h3>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="card mb-3">
                            <div class="card-body">
                                <h6 class="card-title">Gas Price Over Time</h6>
                                <canvas id="gas-price-chart" height="200"></canvas>
                            </div>
                        </div>
                        
                        <div class="row">
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-body">
                                        <h6 class="card-title">Gas Usage by Token</h6>
                                        <div class="table-responsive">
                                            <table class="table table-sm" id="gas-by-token-table">
                                                <thead>
                                                    <tr>
                                                        <th>Token</th>
                                                        <th>Tx Count</th>
                                                        <th>Gas Used</th>
                                                        <th>Gas Cost</th>
                                                    </tr>
                                                </thead>
                                                <tbody id="gas-by-token-body">
                    `;
                    
                    // Add gas by token rows
                    if (analytics.gas_by_token && analytics.gas_by_token.length > 0) {
                        analytics.gas_by_token.forEach(token => {
                            content += `
                                <tr>
                                    <td>${token.name || token.symbol || 'Unknown'}</td>
                                    <td>${token.transaction_count}</td>
                                    <td>${token.total_gas_used.toLocaleString()}</td>
                                    <td>${token.total_gas_cost_eth.toFixed(4)} ETH</td>
                                </tr>
                            `;
                        });
                    } else {
                        content += `<tr><td colspan="4" class="text-center">No data available</td></tr>`;
                    }
                    
                    content += `
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-body">
                                        <h6 class="card-title">Optimization Suggestions</h6>
                                        <ul class="list-group" id="optimization-suggestions">
                    `;
                    
                    // Add optimization suggestions
                    if (analytics.optimization_suggestions && analytics.optimization_suggestions.length > 0) {
                        analytics.optimization_suggestions.forEach(suggestion => {
                            content += `
                                <li class="list-group-item">
                                    <div class="d-flex justify-content-between">
                                        <div>
                                            <strong>${suggestion.title}</strong>
                                            <p class="mb-0">${suggestion.description}</p>
                                        </div>
                                        <span class="badge bg-${suggestion.priority === 'high' ? 'danger' : suggestion.priority === 'medium' ? 'warning' : 'info'}">${suggestion.priority}</span>
                                    </div>
                                </li>
                            `;
                        });
                    } else {
                        content += `<li class="list-group-item text-center">No suggestions available</li>`;
                    }
                    
                    content += `
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                    
                    // Display content
                    document.getElementById('gas-analytics-content').innerHTML = content;
                    document.getElementById('gas-analytics-loading').style.display = 'none';
                    document.getElementById('gas-analytics-content').style.display = 'block';
                    
                    // Initialize gas price chart
                    initGasPriceChart(analytics.gas_price_over_time);
                } else {
                    showNotification('danger', `Failed to load gas analytics: ${data.error}`);
                }
            })
            .catch(error => {
                console.error('Error loading gas analytics:', error);
                showNotification('danger', 'Failed to load gas analytics. Please try again.');
            });
    }
    
    // Transaction Patterns
    const transactionPatternsBtn = document.getElementById('transactionPatternsBtn');
    const patternsWalletSelect = document.getElementById('patterns-wallet-select');
    const patternPeriodButtons = document.querySelectorAll('.pattern-period');
    
    if (transactionPatternsBtn) {
        transactionPatternsBtn.addEventListener('click', function() {
            const modal = new bootstrap.Modal(document.getElementById('transactionPatternsModalFull'));
            modal.show();
        });
    }
    
    if (patternsWalletSelect) {
        patternsWalletSelect.addEventListener('change', function() {
            const walletId = this.value;
            
            if (!walletId) {
                return;
            }
            
            // Get selected period
            let period = 'all';
            document.querySelectorAll('.pattern-period').forEach(btn => {
                if (btn.classList.contains('active')) {
                    period = btn.getAttribute('data-period');
                }
            });
            
            // Load transaction patterns
            loadTransactionPatterns(walletId, period);
        });
    }
    
    if (patternPeriodButtons.length > 0) {
        patternPeriodButtons.forEach(button => {
            button.addEventListener('click', function() {
                // Update active state
                document.querySelectorAll('.pattern-period').forEach(btn => {
                    btn.classList.remove('active');
                });
                this.classList.add('active');
                
                // Get selected wallet and period
                const walletId = document.getElementById('patterns-wallet-select').value;
                const period = this.getAttribute('data-period');
                
                if (!walletId) {
                    return;
                }
                
                // Load transaction patterns
                loadTransactionPatterns(walletId, period);
            });
        });
    }
    
    function loadTransactionPatterns(walletId, period) {
        // Show loading state
        document.getElementById('patterns-loading').style.display = 'block';
        document.getElementById('patterns-content').style.display = 'none';
        
        // Fetch transaction patterns data
        fetch(`/api/wallet/${walletId}/transaction_patterns?period=${period}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Generate transaction patterns content
                    const patterns = data.patterns;
                    
                    // Update total transactions
                    document.getElementById('pattern-total-transactions').textContent = patterns.total_transactions;
                    
                    // Create HTML content
                    let content = `
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-body">
                                        <h6 class="card-title">Activity by Day</h6>
                                        <canvas id="activity-by-day-chart" height="200"></canvas>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-body">
                                        <h6 class="card-title">Activity by Hour</h6>
                                        <canvas id="activity-by-hour-chart" height="200"></canvas>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="row">
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-body">
                                        <h6 class="card-title">Transaction Types</h6>
                                        <canvas id="transaction-types-chart" height="200"></canvas>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-body">
                                        <h6 class="card-title">Frequent Interactions</h6>
                                        <div class="table-responsive">
                                            <table class="table table-sm" id="frequent-interactions-table">
                                                <thead>
                                                    <tr>
                                                        <th>Address</th>
                                                        <th>Sent</th>
                                                        <th>Received</th>
                                                        <th>Total</th>
                                                    </tr>
                                                </thead>
                                                <tbody id="frequent-interactions-body">
                    `;
                    
                    // Add frequent interactions rows
                    if (patterns.frequent_interactions && patterns.frequent_interactions.length > 0) {
                        patterns.frequent_interactions.forEach(interaction => {
                            content += `
                                <tr>
                                    <td class="text-truncate" style="max-width: 150px;">${interaction.address}</td>
                                    <td>${interaction.sent_count}</td>
                                    <td>${interaction.received_count}</td>
                                    <td>${interaction.sent_count + interaction.received_count}</td>
                                </tr>
                            `;
                        });
                    } else {
                        content += `<tr><td colspan="4" class="text-center">No data available</td></tr>`;
                    }
                    
                    content += `
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="card mt-3">
                            <div class="card-body">
                                <h6 class="card-title">Recurring Patterns</h6>
                                <ul class="list-group" id="recurring-patterns">
                    `;
                    
                    // Add recurring patterns
                    if (patterns.recurring_patterns && patterns.recurring_patterns.length > 0) {
                        patterns.recurring_patterns.forEach(pattern => {
                            content += `
                                <li class="list-group-item">
                                    <div class="d-flex justify-content-between align-items-center">
                                        <div>
                                            <strong>${pattern.pattern}</strong>
                                            <p class="mb-0">${pattern.description}</p>
                                        </div>
                                        <span class="badge bg-primary">${pattern.confidence}% confidence</span>
                                    </div>
                                </li>
                            `;
                        });
                    } else {
                        content += `<li class="list-group-item text-center">No recurring patterns detected</li>`;
                    }
                    
                    content += `
                                        </ul>
                                    </div>
                                </div>
                    `;
                    
                    // Display content
                    document.getElementById('patterns-content').innerHTML = content;
                    document.getElementById('patterns-loading').style.display = 'none';
                    document.getElementById('patterns-content').style.display = 'block';
                    
                    // Initialize charts
                    initActivityByDayChart(patterns.active_days);
                    initActivityByHourChart(patterns.active_hours);
                    initTransactionTypesChartInModal(patterns.transaction_types);
                    
                } else {
                    showNotification('danger', `Failed to load transaction patterns: ${data.error}`);
                }
            })
            .catch(error => {
                console.error('Error loading transaction patterns:', error);
                showNotification('danger', 'Failed to load transaction patterns. Please try again.');
            });
    }
    
    // Export Transactions
    const exportCsvBtn = document.getElementById('exportCsvBtn');
    const exportPdfBtn = document.getElementById('exportPdfBtn');
    const confirmExportBtn = document.getElementById('confirm-export-btn');
    
    if (exportCsvBtn) {
        exportCsvBtn.addEventListener('click', function() {
            // Set format
            document.getElementById('export-format').value = 'csv';
            
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('exportOptionsModal'));
            modal.show();
        });
    }
    
    if (exportPdfBtn) {
        exportPdfBtn.addEventListener('click', function() {
            // Set format
            document.getElementById('export-format').value = 'pdf';
            
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('exportOptionsModal'));
            modal.show();
        });
    }
    
    if (confirmExportBtn) {
        confirmExportBtn.addEventListener('click', function() {
            const walletId = document.getElementById('export-wallet-id').value;
            const tokenId = document.getElementById('export-token-id').value;
            const startDate = document.getElementById('export-start-date').value;
            const endDate = document.getElementById('export-end-date').value;
            const format = document.getElementById('export-format').value;
            
            if (!walletId) {
                showNotification('danger', 'Please select a wallet');
                return;
            }
            
            // Call API to export transactions
            fetch(`/api/wallet/${walletId}/export_transactions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': getCsrfToken()
                },
                body: JSON.stringify({
                    token_id: tokenId !== '' ? tokenId : null,
                    start_date: startDate !== '' ? startDate : null,
                    end_date: endDate !== '' ? endDate : null,
                    format: format
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Hide modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('exportOptionsModal'));
                    if (modal) {
                        modal.hide();
                    }
                    
                    // Handle export data
                    if (format === 'csv') {
                        // Create CSV blob and download
                        const blob = new Blob([data.data], { type: 'text/csv' });
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.style.display = 'none';
                        a.href = url;
                        a.download = `transactions_${new Date().toISOString().split('T')[0]}.csv`;
                        document.body.appendChild(a);
                        a.click();
                        window.URL.revokeObjectURL(url);
                    } else if (format === 'pdf') {
                        // Create PDF blob and download
                        // Note: This is a simplified example, in reality the PDF would be base64 encoded
                        const blob = new Blob([atob(data.data)], { type: 'application/pdf' });
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.style.display = 'none';
                        a.href = url;
                        a.download = `transactions_${new Date().toISOString().split('T')[0]}.pdf`;
                        document.body.appendChild(a);
                        a.click();
                        window.URL.revokeObjectURL(url);
                    }
                    
                    showNotification('success', `Transactions exported successfully as ${format.toUpperCase()}`);
                } else {
                    showNotification('danger', `Failed to export transactions: ${data.error}`);
                }
            })
            .catch(error => {
                console.error('Error exporting transactions:', error);
                showNotification('danger', 'Failed to export transactions. Please try again.');
            });
        });
    }
    
    // Export wallet filter change handler - update token options
    document.getElementById('export-wallet-id')?.addEventListener('change', function() {
        const walletId = this.value;
        const tokenSelect = document.getElementById('export-token-id');
        
        if (!walletId || !tokenSelect) {
            return;
        }
        
        // Clear token options except for the defaults
        while (tokenSelect.options.length > 2) {
            tokenSelect.remove(2);
        }
        
        // Fetch tokens for this wallet
        fetch(`/api/wallet/${walletId}/tokens`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Add token options
                    data.tokens.forEach(token => {
                        const option = document.createElement('option');
                        option.value = token.id;
                        option.textContent = token.symbol;
                        tokenSelect.appendChild(option);
                    });
                }
            })
            .catch(error => {
                console.error('Error fetching tokens:', error);
            });
    });
    
    // Refresh transactions button
    document.getElementById('refreshTransactionsBtn')?.addEventListener('click', function() {
        window.location.reload();
    });
    
    // Initialize transaction volume chart
    function initTransactionVolumeChart() {
        const ctx = document.getElementById('transactionVolumeChart');
        
        if (!ctx) return;
        
        // Sample data - replace with actual data from backend
        const days = Array.from({length: 30}, (_, i) => {
            const date = new Date();
            date.setDate(date.getDate() - 29 + i);
            return date.toLocaleDateString();
        });
        
        const volumes = Array.from({length: 30}, () => Math.floor(Math.random() * 1000));
        const counts = Array.from({length: 30}, () => Math.floor(Math.random() * 20));
        
        // Create gradient for volume
        const volumeGradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 300);
        volumeGradient.addColorStop(0, 'rgba(54, 162, 235, 0.2)');
        volumeGradient.addColorStop(1, 'rgba(54, 162, 235, 0)');
        
        // Create volume chart
        transactionVolumeChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: days,
                datasets: [
                    {
                        label: 'Volume (USD)',
                        data: volumes,
                        backgroundColor: volumeGradient,
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Transaction Count',
                        data: counts,
                        type: 'line',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        borderWidth: 2,
                        tension: 0.4,
                        pointRadius: 3,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    x: {
                        ticks: {
                            maxRotation: 0,
                            autoSkip: true,
                            maxTicksLimit: 10
                        }
                    },
                    y: {
                        type: 'linear',
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Volume (USD)'
                        },
                        ticks: {
                            callback: function(value) {
                                return '/**
 * Transaction History
 * JavaScript functionality for transaction history interface
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Chart.js instances
    let transactionVolumeChart;
    let transactionTypesChart;
    let gasUsageChart;
    let activityByDayChart;
    let activityByHourChart;
    
    // Initialize transaction volume chart
    initTransactionVolumeChart();
    
    // Initialize transaction types chart
    initTransactionTypesChart();
    
    // Filter transactions
    const walletFilter = document.getElementById('walletFilter');
    const tokenFilter = document.getElementById('tokenFilter');
    const typeFilter = document.getElementById('typeFilter');
    const startDateFilter = document.getElementById('startDateFilter');
    const endDateFilter = document.getElementById('endDateFilter');
    const searchFilter = document.getElementById('searchFilter');
    const applyFiltersBtn = document.getElementById('applyFiltersBtn');
    const resetFiltersBtn = document.getElementById('resetFiltersBtn');
    
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', applyFilters);
    }
    
    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', resetFilters);
    }
    
    // Wallet filter change handler - update token filter options
    if (walletFilter) {
        walletFilter.addEventListener('change', updateTokenFilterOptions);
    }
    
    // Load token options for selected wallet
    function updateTokenFilterOptions() {
        const walletId = walletFilter.value;
        
        if (walletId === 'all') {
            // Clear token options except for the defaults
            while (tokenFilter.options.length > 2) {
                tokenFilter.remove(2);
            }
            return;
        }
        
        // Fetch tokens for this wallet
        fetch(`/api/wallet/${walletId}/tokens`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Clear token options except for the defaults
                    while (tokenFilter.options.length > 2) {
                        tokenFilter.remove(2);
                    }
                    
                    // Add token options
                    data.tokens.forEach(token => {
                        const option = document.createElement('option');
                        option.value = token.id;
                        option.textContent = token.symbol;
                        tokenFilter.appendChild(option);
                    });
                }
            })
            .catch(error => {
                console.error('Error fetching tokens:', error);
            });
    }
    
    function applyFilters() {
        // Collect filter values
        const params = new URLSearchParams(window.location.search);
        
        if (walletFilter && walletFilter.value !== 'all') {
            params.set('wallet_id', walletFilter.value);
        } else {
            params.delete('wallet_id');
        }
        
        if (tokenFilter && tokenFilter.value !== 'all') {
            params.set('token_id', tokenFilter.value);
        } else {
            params.delete('token_id');
        }
        
        if (typeFilter && typeFilter.value !== 'all') {
            params.set('tx_type', typeFilter.value);
        } else {
            params.delete('tx_type');
        }
        
        if (startDateFilter && startDateFilter.value) {
            params.set('start_date', startDateFilter.value);
        } else {
            params.delete('start_date');
        }
        
        if (endDateFilter && endDateFilter.value) {
            params.set('end_date', endDateFilter.value);
        } else {
            params.delete('end_date');
        }
        
        if (searchFilter && searchFilter.value) {
            params.set('search', searchFilter.value);
        } else {
            params.delete('search');
        }
        
        // Navigate to new URL with filters
        window.location.href = `${window.location.pathname}?${params.toString()}`;
    }
    
    function resetFilters() {
        if (walletFilter) walletFilter.value = 'all';
        if (tokenFilter) tokenFilter.value = 'all';
        if (typeFilter) typeFilter.value = 'all';
        if (startDateFilter) startDateFilter.value = '';
        if (endDateFilter) endDateFilter.value = '';
        if (searchFilter) searchFilter.value = '';
        
        // Apply filters
        applyFilters();
    }
    
    // Initialize filter values from URL
    function initializeFilters() {
        const params = new URLSearchParams(window.location.search);
        
        if (params.has('wallet_id') && walletFilter) {
            walletFilter.value = params.get('wallet_id');
            // Update token options
            updateTokenFilterOptions();
        }
        
        if (params.has('token_id') && tokenFilter) {
            tokenFilter.value = params.get('token_id');
        }
        
        if (params.has('tx_type') && typeFilter) {
            typeFilter.value = params.get('tx_type');
        }
        
        if (params.has('start_date') && startDateFilter) {
            startDateFilter.value = params.get('start_date');
        }
        
        if (params.has('end_date') && endDateFilter) {
            endDateFilter.value = params.get('end_date');
        }
        
        if (params.has('search') && searchFilter) {
            searchFilter.value = params.get('search');
        }
    }
    
    // Call initialize filters
    initializeFilters();
    
    // Sync Transactions
    const syncTransactionsBtn = document.getElementById('syncTransactionsBtn');
    const emptySyncTransactionsBtn = document.getElementById('emptySyncTransactionsBtn');
    const startSyncBtn = document.getElementById('start-sync-btn');
    
    // Open sync modal
    if (syncTransactionsBtn) {
        syncTransactionsBtn.addEventListener('click', function() {
            const modal = new bootstrap.Modal(document.getElementById('syncTransactionsModal'));
            modal.show();
        });
    }
    
    // Open sync modal from empty state
    if (emptySyncTransactionsBtn) {
        emptySyncTransactionsBtn.addEventListener('click', function() {
            const modal = new bootstrap.Modal(document.getElementById('syncTransactionsModal'));
            modal.show();
        });
    }
    
    // Start sync process
    if (startSyncBtn) {
        startSyncBtn.addEventListener('click', function() {
            const walletId = document.getElementById('sync-wallet-id').value;
            const tokenId = document.getElementById('sync-token-id').value;
            const startBlock = document.getElementById('sync-start-block').value;
            
            if (!walletId) {
                showNotification('danger', 'Please select a wallet');
                return;
            }
            
            // Show progress
            document.getElementById('sync-progress').style.display = 'block';
            document.getElementById('sync-results').style.display = 'none';
            
            // Update progress bar animations
            const progressBar = document.querySelector('#sync-progress .progress-bar');
            progressBar.style.width = '0%';
            
            // Animate progress bar
            let progress = 0;
            const progressInterval = setInterval(() => {
                progress += 2;
                if (progress > 90) {
                    clearInterval(progressInterval);
                }
                progressBar.style.width = `${progress}%`;
            }, 500);
            
            // Update status
            document.getElementById('sync-status').textContent = 'Syncing transactions...';
            
            // Call API to sync transactions
            fetch(`/api/wallet/${walletId}/sync_transactions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': getCsrfToken()
                },
                body: JSON.stringify({
                    token_id: tokenId !== '' ? tokenId : null,
                    start_block: startBlock !== '' ? parseInt(startBlock) : null
                })
            })
            .then(response => response.json())
            .then(data => {
                clearInterval(progressInterval);
                progressBar.style.width = '100%';
                
                if (data.success) {
                    document.getElementById('sync-status').textContent = 'Sync completed successfully';
                    
                    // Show results
                    document.getElementById('sync-results').style.display = 'block';
                    
                    // Update result counters
                    const nativeResult = data.native_sync || { transactions_found: 0, transactions_added: 0, blocks_scanned: 0, errors: [] };
                    const tokenResult = data.token_sync || { transactions_found: 0, transactions_added: 0 };
                    
                    document.getElementById('transactions-found').textContent = 
                        nativeResult.transactions_found + (tokenResult.transactions_found || 0);
                    
                    document.getElementById('transactions-added').textContent = 
                        nativeResult.transactions_added + (tokenResult.transactions_added || 0);
                    
                    document.getElementById('blocks-scanned').textContent = nativeResult.blocks_scanned;
                    document.getElementById('sync-errors').textContent = nativeResult.errors.length;
                    
                    // Show notification
                    showNotification('success', 'Transactions synced successfully');
                    
                    // Reload page after 3 seconds
                    setTimeout(() => {
                        window.location.reload();
                    }, 3000);
                } else {
                    document.getElementById('sync-status').textContent = `Sync failed: ${data.error}`;
                    document.getElementById('sync-results').style.display = 'none';
                    showNotification('danger', `Sync failed: ${data.error}`);
                }
            })
            .catch(error => {
                clearInterval(progressInterval);
                progressBar.style.width = '100%';
                document.getElementById('sync-status').textContent = 'Sync failed. Check console for details.';
                console.error('Error syncing transactions:', error);
                showNotification('danger', 'Failed to sync transactions. Please try again.');
            });
        });
    }
    
    // Transaction details view
    const viewTxDetailsButtons = document.querySelectorAll('.view-tx-details-btn');
    
    if (viewTxDetailsButtons.length > 0) {
        viewTxDetailsButtons.forEach(button => {
            button.addEventListener('click', function() {
                const txHash = this.getAttribute('data-tx-hash');
                
                if (!txHash) {
                    return;
                }
                
                // Get transaction data from the table row
                const txRow = this.closest('.transaction-item');
                
                if (txRow) {
                    // Find all tds in the row
                    const cells = txRow.querySelectorAll('td');
                    
                    // Extract data
                    const date = cells[0].textContent;
                    const type = cells[1].querySelector('.badge').textContent;
                    const token = cells[2].textContent.trim();
                    const amount = cells[3].textContent;
                    const usdValue = cells[4].textContent;
                    const from = cells[5].textContent;
                    const to = cells[6].textContent;
                    const gasCost = cells[7].textContent;
                    const status = cells[8].querySelector('.badge').textContent;
                    
                    // Update modal with data
                    document.getElementById('tx-date').textContent = date;
                    
                    // Set type badge
                    const typeBadge = document.getElementById('tx-type');
                    typeBadge.textContent = type;
                    if (type.toLowerCase() === 'send') {
                        typeBadge.className = 'badge bg-danger';
                    } else if (type.toLowerCase() === 'receive') {
                        typeBadge.className = 'badge bg-success';
                    } else {
                        typeBadge.className = 'badge bg-secondary';
                    }
                    
                    // Set status badge
                    const statusBadge = document.getElementById('tx-status');
                    statusBadge.textContent = status;
                    if (status.toLowerCase() === 'confirmed') {
                        statusBadge.className = 'badge bg-success';
                    } else if (status.toLowerCase() === 'pending') {
                        statusBadge.className = 'badge bg-warning';
                    } else {
                        statusBadge.className = 'badge bg-danger';
                    }
                    
                    // Update other fields
                    document.getElementById('tx-hash').textContent = txHash;
                    document.getElementById('tx-from').textContent = from;
                    document.getElementById('tx-to').textContent = to;
                    document.getElementById('tx-token').textContent = token;
                    document.getElementById('tx-amount').textContent = amount;
                    document.getElementById('tx-usd-value').textContent = usdValue;
                    
                    // Chain info from data attribute
                    const chain = txRow.getAttribute('data-chain') || 'Unknown';
                    document.getElementById('tx-chain').textContent = chain;
                    
                    // Gas info
                    document.getElementById('tx-gas-cost').textContent = gasCost;
                    
                    // Show/hide error details
                    const errorCard = document.getElementById('error-details-card');
                    if (status.toLowerCase() === ' + value;
                            }
                        }
                    },
                    y1: {
                        type: 'linear',
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Transaction Count'
                        },
                        grid: {
                            drawOnChartArea: false
                        }
                    }
                }
            }
        });
    }
    
    // Initialize transaction types chart
    function initTransactionTypesChart() {
        const ctx = document.getElementById('transactionTypesChart');
        
        if (!ctx) return;
        
        // Sample data - replace with actual data from backend
        const data = {
            labels: ['Send', 'Receive', 'Contract Creation', 'Unknown'],
            datasets: [{
                data: [40, 35, 15, 10],
                backgroundColor: [
                    'rgba(255, 99, 132, 0.7)',
                    'rgba(75, 192, 192, 0.7)',
                    'rgba(255, 205, 86, 0.7)',
                    'rgba(201, 203, 207, 0.7)'
                ],
                borderColor: [
                    'rgb(255, 99, 132)',
                    'rgb(75, 192, 192)',
                    'rgb(255, 205, 86)',
                    'rgb(201, 203, 207)'
                ],
                borderWidth: 1
            }]
        };
        
        // Create chart
        transactionTypesChart = new Chart(ctx, {
            type: 'doughnut',
            data: data,
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'right'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.raw;
                                const total = context.dataset.data.reduce((acc, val) => acc + val, 0);
                                const percentage = Math.round(value / total * 100);
                                return `${context.label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Initialize transaction types chart in modal
    function initTransactionTypesChartInModal(typesData) {
        const ctx = document.getElementById('transaction-types-chart');
        
        if (!ctx) return;
        
        // Format data for chart
        const labels = [];
        const values = [];
        
        typesData.forEach(type => {
            labels.push(type.type.charAt(0).toUpperCase() + type.type.slice(1));
            values.push(type.count);
        });
        
        // Create chart
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.7)',
                        'rgba(75, 192, 192, 0.7)',
                        'rgba(255, 205, 86, 0.7)',
                        'rgba(201, 203, 207, 0.7)'
                    ],
                    borderColor: [
                        'rgb(255, 99, 132)',
                        'rgb(75, 192, 192)',
                        'rgb(255, 205, 86)',
                        'rgb(201, 203, 207)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'right'
                    }
                }
            }
        });
    }
    
    // Initialize gas price chart
    function initGasPriceChart(priceData) {
        const ctx = document.getElementById('gas-price-chart');
        
        if (!ctx) return;
        
        // Format data for chart
        const labels = [];
        const gasPrices = [];
        
        priceData.forEach(point => {
            labels.push(point.date);
            gasPrices.push(point.avg_gas_price_gwei);
        });
        
        // Create chart
        gasUsageChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Avg Gas Price (Gwei)',
                    data: gasPrices,
                    borderColor: 'rgba(255, 159, 64, 1)',
                    backgroundColor: 'rgba(255, 159, 64, 0.2)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        title: {
                            display: true,
                            text: 'Gas Price (Gwei)'
                        }
                    }
                }
            }
        });
    }
    
    // Initialize activity by day chart
    function initActivityByDayChart(daysData) {
        const ctx = document.getElementById('activity-by-day-chart');
        
        if (!ctx) return;
        
        // Format data for chart
        const labels = [];
        const counts = [];
        
        // Define order of days
        const dayOrder = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        
        // Sort days according to order
        daysData.sort((a, b) => dayOrder.indexOf(a.day) - dayOrder.indexOf(b.day));
        
        daysData.forEach(day => {
            labels.push(day.day);
            counts.push(day.count);
        });
        
        // Create chart
        activityByDayChart = new Chart/**
 * Transaction History
 * JavaScript functionality for transaction history interface
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Chart.js instances
    let transactionVolumeChart;
    let transactionTypesChart;
    let gasUsageChart;
    let activityByDayChart;
    let activityByHourChart;
    
    // Initialize transaction volume chart
    initTransactionVolumeChart();
    
    // Initialize transaction types chart
    initTransactionTypesChart();
    
    // Filter transactions
    const walletFilter = document.getElementById('walletFilter');
    const tokenFilter = document.getElementById('tokenFilter');
    const typeFilter = document.getElementById('typeFilter');
    const startDateFilter = document.getElementById('startDateFilter');
    const endDateFilter = document.getElementById('endDateFilter');
    const searchFilter = document.getElementById('searchFilter');
    const applyFiltersBtn = document.getElementById('applyFiltersBtn');
    const resetFiltersBtn = document.getElementById('resetFiltersBtn');
    
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', applyFilters);
    }
    
    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', resetFilters);
    }
    
    // Wallet filter change handler - update token filter options
    if (walletFilter) {
        walletFilter.addEventListener('change', updateTokenFilterOptions);
    }
    
    // Load token options for selected wallet
    function updateTokenFilterOptions() {
        const walletId = walletFilter.value;
        
        if (walletId === 'all') {
            // Clear token options except for the defaults
            while (tokenFilter.options.length > 2) {
                tokenFilter.remove(2);
            }
            return;
        }
        
        // Fetch tokens for this wallet
        fetch(`/api/wallet/${walletId}/tokens`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Clear token options except for the defaults
                    while (tokenFilter.options.length > 2) {
                        tokenFilter.remove(2);
                    }
                    
                    // Add token options
                    data.tokens.forEach(token => {
                        const option = document.createElement('option');
                        option.value = token.id;
                        option.textContent = token.symbol;
                        tokenFilter.appendChild(option);
                    });
                }
            })
            .catch(error => {
                console.error('Error fetching tokens:', error);
            });
    }
    
    function applyFilters() {
        // Collect filter values
        const params = new URLSearchParams(window.location.search);
        
        if (walletFilter && walletFilter.value !== 'all') {
            params.set('wallet_id', walletFilter.value);
        } else {
            params.delete('wallet_id');
        }
        
        if (tokenFilter && tokenFilter.value !== 'all') {
            params.set('token_id', tokenFilter.value);
        } else {
            params.delete('token_id');
        }
        
        if (typeFilter && typeFilter.value !== 'all') {
            params.set('tx_type', typeFilter.value);
        } else {
            params.delete('tx_type');
        }
        
        if (startDateFilter && startDateFilter.value) {
            params.set('start_date', startDateFilter.value);
        } else {
            params.delete('start_date');
        }
        
        if (endDateFilter && endDateFilter.value) {
            params.set('end_date', endDateFilter.value);
        } else {
            params.delete('end_date');
        }
        
        if (searchFilter && searchFilter.value) {
            params.set('search', searchFilter.value);
        } else {
            params.delete('search');
        }
        
        // Navigate to new URL with filters
        window.location.href = `${window.location.pathname}?${params.toString()}`;
    }
    
    function resetFilters() {
        if (walletFilter) walletFilter.value = 'all';
        if (tokenFilter) tokenFilter.value = 'all';
        if (typeFilter) typeFilter.value = 'all';
        if (startDateFilter) startDateFilter.value = '';
        if (endDateFilter) endDateFilter.value = '';
        if (searchFilter) searchFilter.value = '';
        
        // Apply filters
        applyFilters();
    }
    
    // Initialize filter values from URL
    function initializeFilters() {
        const params = new URLSearchParams(window.location.search);
        
        if (params.has('wallet_id') && walletFilter) {
            walletFilter.value = params.get('wallet_id');
            // Update token options
            updateTokenFilterOptions();
        }
        
        if (params.has('token_id') && tokenFilter) {
            tokenFilter.value = params.get('token_id');
        }
        
        if (params.has('tx_type') && typeFilter) {
            typeFilter.value = params.get('tx_type');
        }
        
        if (params.has('start_date') && startDateFilter) {
            startDateFilter.value = params.get('start_date');
        }
        
        if (params.has('end_date') && endDateFilter) {
            endDateFilter.value = params.get('end_date');
        }
        
        if (params.has('search') && searchFilter) {
            searchFilter.value = params.get('search');
        }
    }
    
    // Call initialize filters
    initializeFilters();
    
    // Sync Transactions
    const syncTransactionsBtn = document.getElementById('syncTransactionsBtn');
    const emptySyncTransactionsBtn = document.getElementById('emptySyncTransactionsBtn');
    const startSyncBtn = document.getElementById('start-sync-btn');
    
    // Open sync modal
    if (syncTransactionsBtn) {
        syncTransactionsBtn.addEventListener('click', function() {
            const modal = new bootstrap.Modal(document.getElementById('syncTransactionsModal'));
            modal.show();
        });
    }
    
    // Open sync modal from empty state
    if (emptySyncTransactionsBtn) {
        emptySyncTransactionsBtn.addEventListener('click', function() {
            const modal = new bootstrap.Modal(document.getElementById('syncTransactionsModal'));
            modal.show();
        });
    }
    
    // Start sync process
    if (startSyncBtn) {
        startSyncBtn.addEventListener('click', function() {
            const walletId = document.getElementById('sync-wallet-id').value;
            const tokenId = document.getElementById('sync-token-id').value;
            const startBlock = document.getElementById('sync-start-block').value;
            
            if (!walletId) {
                showNotification('danger', 'Please select a wallet');
                return;
            }
            
            // Show progress
            document.getElementById('sync-progress').style.display = 'block';
            document.getElementById('sync-results').style.display = 'none';
            
            // Update progress bar animations
            const progressBar = document.querySelector('#sync-progress .progress-bar');
            progressBar.style.width = '0%';
            
            // Animate progress bar
            let progress = 0;
            const progressInterval = setInterval(() => {
                progress += 2;
                if (progress > 90) {
                    clearInterval(progressInterval);
                }
                progressBar.style.width = `${progress}%`;
            }, 500);
            
            // Update status
            document.getElementById('sync-status').textContent = 'Syncing transactions...';
            
            // Call API to sync transactions
            fetch(`/api/wallet/${walletId}/sync_transactions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': getCsrfToken()
                },
                body: JSON.stringify({
                    token_id: tokenId !== '' ? tokenId : null,
                    start_block: startBlock !== '' ? parseInt(startBlock) : null
                })
            })
            .then(response => response.json())
            .then(data => {
                clearInterval(progressInterval);
                progressBar.style.width = '100%';
                
                if (data.success) {
                    document.getElementById('sync-status').textContent = 'Sync completed successfully';
                    
                    // Show results
                    document.getElementById('sync-results').style.display = 'block';
                    
                    // Update result counters
                    const nativeResult = data.native_sync || { transactions_found: 0, transactions_added: 0, blocks_scanned: 0, errors: [] };
                    const tokenResult = data.token_sync || { transactions_found: 0, transactions_added: 0 };
                    
                    document.getElementById('transactions-found').textContent = 
                        nativeResult.transactions_found + (tokenResult.transactions_found || 0);
                    
                    document.getElementById('transactions-added').textContent = 
                        nativeResult.transactions_added + (tokenResult.transactions_added || 0);
                    
                    document.getElementById('blocks-scanned').textContent = nativeResult.blocks_scanned;
                    document.getElementById('sync-errors').textContent = nativeResult.errors.length;
                    
                    // Show notification
                    showNotification('success', 'Transactions synced successfully');
                    
                    // Reload page after 3 seconds
                    setTimeout(() => {
                        window.location.reload();
                    }, 3000);
                } else {
                    document.getElementById('sync-status').textContent = `Sync failed: ${data.error}`;
                    document.getElementById('sync-results').style.display = 'none';
                    showNotification('danger', `Sync failed: ${data.error}`);
                }
            })
            .catch(error => {
                clearInterval(progressInterval);
                progressBar.style.width = '100%';
                document.getElementById('sync-status').textContent = 'Sync failed. Check console for details.';
                console.error('Error syncing transactions:', error);
                showNotification('danger', 'Failed to sync transactions. Please try again.');
            });
        });
    }
    
    // Transaction details view
    const viewTxDetailsButtons = document.querySelectorAll('.view-tx-details-btn');
    
    if (viewTxDetailsButtons.length > 0) {
        viewTxDetailsButtons.forEach(button => {
            button.addEventListener('click', function() {
                const txHash = this.getAttribute('data-tx-hash');
                
                if (!txHash) {
                    return;
                }
                
                // Get transaction data from the table row
                const txRow = this.closest('.transaction-item');
                
                if (txRow) {
                    // Find all tds in the row
                    const cells = txRow.querySelectorAll('td');
                    
                    // Extract data
                    const date = cells[0].textContent;
                    const type = cells[1].querySelector('.badge').textContent;
                    const token = cells[2].textContent.trim();
                    const amount = cells[3].textContent;
                    const usdValue = cells[4].textContent;
                    const from = cells[5].textContent;
                    const to = cells[6].textContent;
                    const gasCost = cells[7].textContent;
                    const status = cells[8].querySelector('.badge').textContent;
                    
                    // Update modal with data
                    document.getElementById('tx-date').textContent = date;
                    
                    // Set type badge
                    const typeBadge = document.getElementById('tx-type');
                    typeBadge.textContent = type;
                    if (type.toLowerCase() === 'send') {
                        typeBadge.className = 'badge bg-danger';
                    } else if (type.toLowerCase() === 'receive') {
                        typeBadge.className = 'badge bg-success';
                    } else {
                        typeBadge.className = 'badge bg-secondary';
                    }
                    
                    // Set status badge
                    const statusBadge = document.getElementById('tx-status');
                    statusBadge.textContent = status;
                    if (status.toLowerCase() === 'confirmed') {
                        statusBadge.className = 'badge bg-success';
                    } else if (status.toLowerCase() === 'pending') {
                        statusBadge.className = 'badge bg-warning';
                    } else {
                        statusBadge.className = 'badge bg-danger';
                    }
                    
                    // Update other fields
                    document.getElementById('tx-hash').textContent = txHash;
                    document.getElementById('tx-from').textContent = from;
                    document.getElementById('tx-to').textContent = to;
                    document.getElementById('tx-token').textContent = token;
                    document.getElementById('tx-amount').textContent = amount;
                    document.getElementById('tx-usd-value').textContent = usdValue;
                    
                    // Chain info from data attribute
                    const chain = txRow.getAttribute('data-chain') || 'Unknown';
                    document.getElementById('tx-chain').textContent = chain;
                    
                    // Gas info
                    document.getElementById('tx-gas-cost').textContent = gasCost;
                    
                    // Show/hide error details
                    const errorCard = document.getElementById('error-details-card');
                    if (status.toLowerCase() === 'failed') {
                        errorCard.style.display = 'block';
                        const errorMessage = cells[9].textContent;
                        document.getElementById('error-message').textContent = errorMessage || 'No error message available';
                    } else {
                        errorCard.style.display = 'none';
                    }
                    // Show modal
                    const modal = new bootstrap.Modal(document.getElementById('transactionDetailsModal')); 
                    modal.show();
                }
            }
        });
    }   
    // Helper function to get CSRF token
    function getCsrfToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    }

    // Helper function to show notifications
    function showNotification(type, message) {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        const container = document.getElementById('toast-container') || document.body;
        container.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }
});
