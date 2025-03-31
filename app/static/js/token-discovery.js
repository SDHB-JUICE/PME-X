/**
 * Token Discovery and Management
 * JavaScript functionality for token management interface
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Chart.js instances
    let priceHistoryChart;
    
    // Toggle between grid and list view
    const viewGridBtn = document.getElementById('viewGrid');
    const viewListBtn = document.getElementById('viewList');
    const tokensGrid = document.getElementById('tokensGrid');
    const tokensList = document.getElementById('tokensList');
    
    if (viewGridBtn && viewListBtn && tokensGrid && tokensList) {
        viewGridBtn.addEventListener('click', function() {
            tokensGrid.style.display = 'flex';
            tokensList.style.display = 'none';
            viewGridBtn.classList.add('active');
            viewListBtn.classList.remove('active');
        });
        
        viewListBtn.addEventListener('click', function() {
            tokensGrid.style.display = 'none';
            tokensList.style.display = 'block';
            viewGridBtn.classList.remove('active');
            viewListBtn.classList.add('active');
        });
    }
    
    // Filter tokens by chain and wallet
    const chainFilter = document.getElementById('chainFilter');
    const walletFilter = document.getElementById('walletFilter');
    const tokenSearch = document.getElementById('tokenSearch');
    
    if (chainFilter) {
        chainFilter.addEventListener('change', applyFilters);
    }
    
    if (walletFilter) {
        walletFilter.addEventListener('change', applyFilters);
    }
    
    if (tokenSearch) {
        tokenSearch.addEventListener('input', applyFilters);
    }
    
    function applyFilters() {
        const selectedChain = chainFilter ? chainFilter.value : 'all';
        const selectedWallet = walletFilter ? walletFilter.value : 'all';
        const searchTerm = tokenSearch ? tokenSearch.value.toLowerCase() : '';
        
        const tokenItems = document.querySelectorAll('.token-item');
        
        tokenItems.forEach(item => {
            const chain = item.getAttribute('data-chain');
            const wallet = item.getAttribute('data-wallet');
            const tokenName = item.querySelector('.token-name')?.textContent.toLowerCase() || '';
            const tokenSymbol = item.querySelector('.text-truncate')?.textContent.toLowerCase() || '';
            
            const chainMatch = selectedChain === 'all' || chain === selectedChain;
            const walletMatch = selectedWallet === 'all' || wallet === selectedWallet;
            const searchMatch = 
                searchTerm === '' || 
                tokenName.includes(searchTerm) || 
                tokenSymbol.includes(searchTerm);
            
            if (chainMatch && walletMatch && searchMatch) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
    }
    
    // Refresh Token Balances
    const refreshTokensBtn = document.getElementById('refreshTokensBtn');
    
    if (refreshTokensBtn) {
        refreshTokensBtn.addEventListener('click', function() {
            showNotification('info', 'Refreshing token balances. This may take a moment...');
            
            // Get all wallet IDs
            const walletIds = [];
            document.querySelectorAll('.token-item').forEach(item => {
                const walletId = item.getAttribute('data-wallet');
                if (walletId && !walletIds.includes(walletId)) {
                    walletIds.push(walletId);
                }
            });
            
            // Refresh tokens for each wallet
            Promise.all(walletIds.map(walletId => {
                return fetch('/api/token/refresh', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-TOKEN': getCsrfToken()
                    },
                    body: JSON.stringify({ wallet_id: walletId })
                })
                .then(response => response.json());
            }))
            .then(results => {
                let totalTokens = 0;
                results.forEach(result => {
                    if (result.success) {
                        totalTokens += Object.keys(result.updated_tokens).length;
                    }
                });
                
                if (totalTokens > 0) {
                    showNotification('success', `Successfully refreshed ${totalTokens} tokens. Reloading page...`);
                    setTimeout(() => window.location.reload(), 2000);
                } else {
                    showNotification('warning', 'No tokens were refreshed. Try scanning for tokens instead.');
                }
            })
            .catch(error => {
                console.error('Error refreshing tokens:', error);
                showNotification('danger', 'Failed to refresh tokens. Please try again.');
            });
        });
    }
    
    // Start Token Scan
    const startScanBtn = document.getElementById('start-scan-btn');
    
    if (startScanBtn) {
        startScanBtn.addEventListener('click', function() {
            const walletId = document.getElementById('scan-wallet-id').value;
            const includeTokenLists = document.getElementById('include-token-lists').checked;
            
            if (!walletId) {
                showNotification('danger', 'Please select a wallet to scan');
                return;
            }
            
            // Show progress
            document.getElementById('scan-progress').style.display = 'block';
            document.getElementById('scan-results').style.display = 'none';
            
            // Update progress bar animations
            const progressBar = document.querySelector('#scan-progress .progress-bar');
            progressBar.style.width = '0%';
            
            // Animate progress bar
            let progress = 0;
            const progressInterval = setInterval(() => {
                progress += 5;
                if (progress > 90) {
                    clearInterval(progressInterval);
                }
                progressBar.style.width = `${progress}%`;
            }, 500);
            
            // Update status
            document.getElementById('scan-status').textContent = 'Scanning wallet for tokens...';
            
            // Call API to scan tokens
            fetch('/api/token/scan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': getCsrfToken()
                },
                body: JSON.stringify({
                    wallet_id: walletId,
                    include_token_lists: includeTokenLists
                })
            })
            .then(response => response.json())
            .then(data => {
                clearInterval(progressInterval);
                progressBar.style.width = '100%';
                
                if (data.success) {
                    document.getElementById('scan-status').textContent = `Scan completed. Found ${data.discovered_tokens.length} tokens, added ${data.added_tokens.length} to wallet.`;
                    
                    // Show results
                    document.getElementById('scan-results').style.display = 'block';
                    const tokensList = document.getElementById('discovered-tokens-list');
                    tokensList.innerHTML = '';
                    
                    if (data.added_tokens.length > 0) {
                        data.added_tokens.forEach(token => {
                            const listItem = document.createElement('li');
                            listItem.className = 'list-group-item d-flex justify-content-between align-items-center';
                            
                            let logo = token.logo_url || '/static/img/tokens/default.jpeg';
                            
                            listItem.innerHTML = `
                                <div class="d-flex align-items-center">
                                    <img src="${logo}" onerror="this.src='/static/img/tokens/default.jpeg';" alt="${token.symbol}" class="me-2" width="24" height="24">
                                    <div>
                                        <div><strong>${token.symbol}</strong></div>
                                        <small class="text-muted">${token.name}</small>
                                    </div>
                                </div>
                                <div>
                                    <span class="badge bg-primary">${token.balance.toFixed(4)}</span>
                                    <span class="badge bg-success">$${token.usd_value.toFixed(2)}</span>
                                </div>
                            `;
                            
                            tokensList.appendChild(listItem);
                        });
                    } else {
                        tokensList.innerHTML = '<li class="list-group-item text-center">No new tokens found</li>';
                    }
                    
                    // Show notification
                    showNotification('success', `Token scan completed. Found ${data.discovered_tokens.length} tokens, added ${data.added_tokens.length} to wallet.`);
                } else {
                    document.getElementById('scan-status').textContent = `Scan failed: ${data.error}`;
                    document.getElementById('scan-results').style.display = 'none';
                    showNotification('danger', `Scan failed: ${data.error}`);
                }
            })
            .catch(error => {
                clearInterval(progressInterval);
                progressBar.style.width = '100%';
                document.getElementById('scan-status').textContent = 'Scan failed. Check console for details.';
                console.error('Error scanning tokens:', error);
                showNotification('danger', 'Failed to scan tokens. Please try again.');
            });
        });
    }
    
    // Add custom token
    const addTokenBtn = document.getElementById('add-token-btn');
    
    if (addTokenBtn) {
        addTokenBtn.addEventListener('click', function() {
            const walletId = document.getElementById('add-token-wallet-id').value;
            const tokenAddress = document.getElementById('token-address').value;
            const symbol = document.getElementById('token-symbol').value;
            const name = document.getElementById('token-name').value;
            const decimals = document.getElementById('token-decimals').value;
            
            if (!walletId || !tokenAddress) {
                showNotification('danger', 'Wallet ID and token address are required');
                return;
            }
            
            // Call API to add custom token
            fetch('/api/token/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': getCsrfToken()
                },
                body: JSON.stringify({
                    wallet_id: walletId,
                    token_address: tokenAddress,
                    symbol: symbol || null,
                    name: name || null,
                    decimals: decimals || null
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('success', 'Token added successfully. Reloading page...');
                    setTimeout(() => window.location.reload(), 2000);
                } else {
                    showNotification('danger', `Failed to add token: ${data.error}`);
                }
            })
            .catch(error => {
                console.error('Error adding token:', error);
                showNotification('danger', 'Failed to add token. Please try again.');
            });
        });
    }
    
    // Import token list
    const importTokenListBtn = document.getElementById('import-token-list-btn');
    
    if (importTokenListBtn) {
        importTokenListBtn.addEventListener('click', function() {
            const name = document.getElementById('token-list-name').value;
            const url = document.getElementById('token-list-url').value;
            const chain = document.getElementById('token-list-chain').value;
            
            if (!name || !url || !chain) {
                showNotification('danger', 'Name, URL, and chain are required');
                return;
            }
            
            // Call API to import token list
            fetch('/api/token_list/import', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': getCsrfToken()
                },
                body: JSON.stringify({
                    name: name,
                    url: url,
                    chain: chain
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('success', `Token list imported successfully. Added ${data.token_list.tokens_count} tokens.`);
                    // Close modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('importTokenListModal'));
                    if (modal) {
                        modal.hide();
                    }
                } else {
                    showNotification('danger', `Failed to import token list: ${data.error}`);
                }
            })
            .catch(error => {
                console.error('Error importing token list:', error);
                showNotification('danger', 'Failed to import token list. Please try again.');
            });
        });
    }
    
    // View token details
    const viewTokenDetailsButtons = document.querySelectorAll('.view-token-details-btn');
    
    if (viewTokenDetailsButtons.length > 0) {
        viewTokenDetailsButtons.forEach(button => {
            button.addEventListener('click', function() {
                const tokenId = this.getAttribute('data-token-id');
                
                if (!tokenId) {
                    return;
                }
                
                // Show loading state
                document.getElementById('token-detail-symbol').textContent = 'Loading...';
                document.getElementById('token-detail-name').textContent = '';
                document.getElementById('token-detail-price').textContent = '$0.00';
                document.getElementById('token-detail-change').textContent = '0.00%';
                document.getElementById('token-detail-address').textContent = '';
                document.getElementById('token-detail-chain').textContent = '';
                document.getElementById('token-detail-wallet').textContent = '';
                document.getElementById('token-detail-decimals').textContent = '';
                document.getElementById('token-detail-balance').textContent = '';
                document.getElementById('token-detail-usd-value').textContent = '';
                document.getElementById('token-detail-last-updated').textContent = '';
                
                // Clear token transactions table
                document.getElementById('token-transactions-body').innerHTML = '<tr><td colspan="5" class="text-center">Loading transactions...</td></tr>';
                
                // Reset token explorer link
                document.getElementById('token-explorer-link').href = '#';
                
                // Show modal
                const modal = new bootstrap.Modal(document.getElementById('tokenDetailsModal'));
                modal.show();
                
                // Fetch token details
                fetch(`/api/token/${tokenId}/details`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            const token = data.token.token;
                            const metrics = data.token.metrics;
                            const priceHistory = data.token.price_history;
                            const transactions = data.token.recent_transactions;
                            
                            // Update token icon
                            const tokenIcon = document.getElementById('token-detail-icon');
                            tokenIcon.src = token.logo_url || '/static/img/tokens/default.jpeg';
                            tokenIcon.alt = token.symbol;
                            
                            // Update token details
                            document.getElementById('token-detail-symbol').textContent = token.symbol;
                            document.getElementById('token-detail-name').textContent = token.name;
                            document.getElementById('token-detail-price').textContent = `${token.current_price.toFixed(4)}`;
                            
                            const changeElement = document.getElementById('token-detail-change');
                            changeElement.textContent = `${token.price_24h_change >= 0 ? '+' : ''}${token.price_24h_change.toFixed(2)}%`;
                            changeElement.className = `badge ${token.price_24h_change >= 0 ? 'bg-success' : 'bg-danger'}`;
                            
                            document.getElementById('token-detail-address').textContent = token.address;
                            document.getElementById('token-detail-chain').textContent = token.chain;
                            document.getElementById('token-detail-wallet').textContent = token.wallet_address || 'Unknown';
                            document.getElementById('token-detail-decimals').textContent = token.decimals;
                            document.getElementById('token-detail-balance').textContent = token.balance.toFixed(6);
                            document.getElementById('token-detail-usd-value').textContent = `${token.usd_value.toFixed(2)}`;
                            document.getElementById('token-detail-last-updated').textContent = new Date(token.last_updated).toLocaleString();
                            
                            // Update token explorer link
                            const explorerLink = document.getElementById('token-explorer-link');
                            if (token.explorer_url) {
                                explorerLink.href = token.explorer_url;
                            } else {
                                // Construct URL based on chain
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
                                
                                const baseUrl = chainInfo[token.chain.toLowerCase()] || 'https://etherscan.io';
                                explorerLink.href = `${baseUrl}/token/${token.address}`;
                            }
                            
                            // Update price history chart
                            updatePriceHistoryChart(priceHistory);
                            
                            // Update transactions table
                            updateTransactionsTable(transactions);
                            
                            // Set up sync transactions button
                            const syncButton = document.getElementById('sync-token-transactions-btn');
                            syncButton.setAttribute('data-token-id', token.id);
                            syncButton.setAttribute('data-wallet-id', token.wallet_id);
                        } else {
                            showNotification('danger', `Failed to get token details: ${data.error}`);
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching token details:', error);
                        showNotification('danger', 'Failed to get token details. Please try again.');
                    });
            });
        });
    }
    
    // Function to update price history chart
    function updatePriceHistoryChart(priceHistory) {
        const ctx = document.getElementById('price-history-chart').getContext('2d');
        
        // Destroy existing chart if it exists
        if (priceHistoryChart) {
            priceHistoryChart.destroy();
        }
        
        // Prepare data
        const labels = [];
        const prices = [];
        
        if (priceHistory && priceHistory.length > 0) {
            priceHistory.forEach(point => {
                // Convert timestamp to readable date
                const date = new Date(point.timestamp);
                labels.push(date.toLocaleDateString());
                prices.push(point.price);
            });
            
            // Create gradient
            const gradient = ctx.createLinearGradient(0, 0, 0, 300);
            gradient.addColorStop(0, 'rgba(54, 162, 235, 0.2)');
            gradient.addColorStop(1, 'rgba(54, 162, 235, 0)');
            
            // Create chart
            priceHistoryChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Price (USD)',
                        data: prices,
                        borderColor: 'rgba(54, 162, 235, 1)',
                        backgroundColor: gradient,
                        borderWidth: 2,
                        pointRadius: 3,
                        pointBackgroundColor: 'rgba(54, 162, 235, 1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                label: function(context) {
                                    return `Price: ${context.raw.toFixed(6)}`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            ticks: {
                                maxRotation: 0,
                                autoSkip: true,
                                maxTicksLimit: 10
                            }
                        },
                        y: {
                            ticks: {
                                callback: function(value) {
                                    return ' + value.toFixed(6);
                                }
                            }
                        }
                    }
                }
            });
        } else {
            // No price history data
            document.getElementById('price-history-chart').innerHTML = 'No price history data available';
        }
    }
    
    // Function to update transactions table
    function updateTransactionsTable(transactions) {
        const tableBody = document.getElementById('token-transactions-body');
        tableBody.innerHTML = '';
        
        if (transactions && transactions.length > 0) {
            transactions.forEach(tx => {
                const row = document.createElement('tr');
                
                // Format date
                const date = new Date(tx.timestamp);
                const formattedDate = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
                
                // Create type badge
                const typeBadge = document.createElement('span');
                typeBadge.classList.add('badge');
                if (tx.tx_type === 'send') {
                    typeBadge.classList.add('bg-danger');
                    typeBadge.textContent = 'Send';
                } else if (tx.tx_type === 'receive') {
                    typeBadge.classList.add('bg-success');
                    typeBadge.textContent = 'Receive';
                } else {
                    typeBadge.classList.add('bg-secondary');
                    typeBadge.textContent = tx.tx_type || 'Unknown';
                }
                
                // Create status badge
                const statusBadge = document.createElement('span');
                statusBadge.classList.add('badge');
                if (tx.status === 'confirmed') {
                    statusBadge.classList.add('bg-success');
                    statusBadge.textContent = 'Confirmed';
                } else if (tx.status === 'pending') {
                    statusBadge.classList.add('bg-warning');
                    statusBadge.textContent = 'Pending';
                } else {
                    statusBadge.classList.add('bg-danger');
                    statusBadge.textContent = tx.status || 'Failed';
                }
                
                // Create shortened address
                let fromTo = tx.from_address;
                if (tx.tx_type === 'send') {
                    fromTo = tx.to_address;
                }
                
                const shortAddress = fromTo ? (fromTo.substring(0, 6) + '...' + fromTo.substring(fromTo.length - 4)) : '';
                
                // Create row cells
                row.innerHTML = `
                    <td>${formattedDate}</td>
                    <td>${typeBadge.outerHTML}</td>
                    <td>${tx.amount.toFixed(6)}</td>
                    <td>${shortAddress}</td>
                    <td>${statusBadge.outerHTML}</td>
                `;
                
                tableBody.appendChild(row);
            });
        } else {
            // No transactions
            tableBody.innerHTML = '<tr><td colspan="5" class="text-center">No transactions found</td></tr>';
        }
    }
    
    // View transactions
    const viewTransactionsButtons = document.querySelectorAll('.view-transactions-btn');
    
    if (viewTransactionsButtons.length > 0) {
        viewTransactionsButtons.forEach(button => {
            button.addEventListener('click', function() {
                const tokenId = this.getAttribute('data-token-id');
                
                if (!tokenId) {
                    return;
                }
                
                // TODO: Implement transactions view for specific token
                window.location.href = `/dashboard/transactions?token_id=${tokenId}`;
            });
        });
    }
    
    // Sync token transactions
    document.getElementById('sync-token-transactions-btn')?.addEventListener('click', function() {
        const tokenId = this.getAttribute('data-token-id');
        const walletId = this.getAttribute('data-wallet-id');
        
        if (!tokenId || !walletId) {
            showNotification('danger', 'Missing token or wallet ID');
            return;
        }
        
        showNotification('info', 'Syncing token transactions. This may take a moment...');
        
        // Call API to sync transactions
        fetch(`/api/wallet/${walletId}/sync_transactions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-TOKEN': getCsrfToken()
            },
            body: JSON.stringify({
                token_id: tokenId
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('success', 'Transactions synced successfully.');
                
                // Refresh token details
                fetch(`/api/token/${tokenId}/details`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            updateTransactionsTable(data.token.recent_transactions);
                        }
                    });
            } else {
                showNotification('danger', `Failed to sync transactions: ${data.error}`);
            }
        })
        .catch(error => {
            console.error('Error syncing transactions:', error);
            showNotification('danger', 'Failed to sync transactions. Please try again.');
        });
    });
    
    // Helper function to get CSRF token
    function getCsrfToken() {
        return document.querySelector('input[name="csrf_token"]')?.value || '';
    }
    
    // Helper function to show notifications
    function showNotification(type, message) {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
        notification.style.zIndex = '9999';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        document.body.appendChild(notification);
        
        // Auto-dismiss after 3 seconds
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
});