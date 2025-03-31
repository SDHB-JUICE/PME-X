/**
 * Wallet Strategies Module
 * Handles the execution of multiple strategies across selected wallets
 */
document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const selectAllBtn = document.getElementById('selectAllWallets');
    const deselectAllBtn = document.getElementById('deselectAllWallets');
    const activeWalletsOnly = document.getElementById('activeWalletsOnly');
    const walletCheckboxes = document.querySelectorAll('.wallet-selector');
    const strategyCheckboxes = document.querySelectorAll('.strategy-checkbox');
    const selectedWalletsCountEl = document.getElementById('selectedWalletsCount');
    const selectedStrategiesCountEl = document.getElementById('selectedStrategiesCount');
    const executeStrategiesBtnPre = document.getElementById('executeWalletStrategiesBtnPre');
    const executeStrategiesBtn = document.getElementById('executeWalletStrategiesBtn');
    const cancelExecutionBtn = document.getElementById('cancelExecutionBtn');
    const completeExecutionBtn = document.getElementById('completeExecutionBtn');
    const executionLogContainer = document.getElementById('executionLogContainer');
    const executionSummaryContainer = document.getElementById('executionSummaryContainer');
    const executeWalletStrategiesModal = document.getElementById('executeWalletStrategiesModal');
    const executionProgressModal = document.getElementById('executionProgressModal');
    
    // Modal instances
    let strategiesModal, progressModal;
    
    // Initialize modals
    if (executeWalletStrategiesModal) {
        strategiesModal = new bootstrap.Modal(executeWalletStrategiesModal);
    }
    
    if (executionProgressModal) {
        progressModal = new bootstrap.Modal(executionProgressModal);
    }
    
    // Wallet selection handlers
    if (selectAllBtn) {
        selectAllBtn.addEventListener('click', function() {
            walletCheckboxes.forEach(checkbox => {
                if (activeWalletsOnly.checked) {
                    // Only select active wallets
                    if (checkbox.closest('.wallet-selection-item').getAttribute('data-active') === 'true') {
                        checkbox.checked = true;
                        checkbox.disabled = false;
                    }
                } else {
                    checkbox.checked = true;
                    checkbox.disabled = false;
                }
            });
            updateWalletCount();
        });
    }
    
    if (deselectAllBtn) {
        deselectAllBtn.addEventListener('click', function() {
            walletCheckboxes.forEach(checkbox => {
                checkbox.checked = false;
            });
            updateWalletCount();
        });
    }
    
    // Active wallets filter
    if (activeWalletsOnly) {
        activeWalletsOnly.addEventListener('change', function() {
            const walletItems = document.querySelectorAll('.wallet-selection-item');
            
            walletItems.forEach(item => {
                const checkbox = item.querySelector('.wallet-selector');
                const isActive = item.getAttribute('data-active') === 'true';
                
                if (this.checked) {
                    // Show only active wallets
                    if (!isActive) {
                        checkbox.checked = false;
                        checkbox.disabled = true;
                    } else {
                        checkbox.disabled = false;
                    }
                } else {
                    // Show all wallets
                    checkbox.disabled = false;
                }
            });
            updateWalletCount();
        });
    }
    
    // Update wallet count when checkboxes change
    walletCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateWalletCount);
    });
    
    // Update strategy count when checkboxes change
    strategyCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            updateStrategyCount();
            updateStrategyParams();
        });
    });
    
    // Count selected wallets
    function updateWalletCount() {
        const selectedCount = document.querySelectorAll('.wallet-selector:checked').length;
        if (selectedWalletsCountEl) {
            selectedWalletsCountEl.textContent = selectedCount;
        }
        
        // Enable/disable execute button based on selection
        if (executeWalletStrategiesBtnPre) {
            executeWalletStrategiesBtnPre.disabled = selectedCount === 0;
        }
    }
    
    // Count selected strategies
    function updateStrategyCount() {
        const selectedCount = document.querySelectorAll('.strategy-checkbox:checked').length;
        if (selectedStrategiesCountEl) {
            selectedStrategiesCountEl.textContent = selectedCount;
        }
        
        // Enable/disable execute button based on selection
        if (executeStrategiesBtn) {
            executeStrategiesBtn.disabled = selectedCount === 0;
        }
    }
    
    // Update strategy parameters based on selected strategies
    function updateStrategyParams() {
        const paramsContainer = document.getElementById('strategyParamsContainer');
        if (!paramsContainer) return;
        
        paramsContainer.innerHTML = '';
        
        strategyCheckboxes.forEach(checkbox => {
            if (checkbox.checked) {
                const strategyType = checkbox.value;
                // Generate parameter inputs for this strategy
                const paramInputs = generateStrategyParamInputs(strategyType);
                paramsContainer.appendChild(paramInputs);
            }
        });
    }
    
    // Generate strategy-specific parameter inputs
    function generateStrategyParamInputs(strategyType) {
        const paramsDiv = document.createElement('div');
        paramsDiv.className = 'strategy-params mb-4 mt-3 p-3 border rounded bg-light';
        paramsDiv.dataset.strategy = strategyType;
        
        // Strategy-specific parameters
        let strategyTitle, strategyIcon, formFields;
        
        switch (strategyType) {
            case 'flash_loan':
                strategyTitle = 'Flash Loan Parameters';
                strategyIcon = 'bolt';
                formFields = `
                    <div class="row">
                        <div class="col-md-4">
                            <div class="mb-3">
                                <label class="form-label">Token</label>
                                <select class="form-select form-select-sm" name="token">
                                    <option value="DAI">DAI</option>
                                    <option value="USDC">USDC</option>
                                    <option value="USDT">USDT</option>
                                    <option value="ETH">ETH</option>
                                    <option value="WBTC">WBTC</option>
                                </select>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="mb-3">
                                <label class="form-label">Amount</label>
                                <input type="number" class="form-control form-control-sm" name="amount" value="1000000">
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="mb-3">
                                <label class="form-label">DEX Pair</label>
                                <div class="input-group input-group-sm">
                                    <select class="form-select" name="dex1">
                                        <option value="uniswap">Uniswap</option>
                                        <option value="sushiswap">Sushiswap</option>
                                        <option value="pancakeswap">PancakeSwap</option>
                                    </select>
                                    <span class="input-group-text">↔</span>
                                    <select class="form-select" name="dex2">
                                        <option value="sushiswap">Sushiswap</option>
                                        <option value="uniswap">Uniswap</option>
                                        <option value="pancakeswap">PancakeSwap</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                break;
                
            case 'multi_hop':
                strategyTitle = 'Multi-Hop Arbitrage Parameters';
                strategyIcon = 'route';
                formFields = `
                    <div class="row">
                        <div class="col-md-4">
                            <div class="mb-3">
                                <label class="form-label">Initial Amount</label>
                                <input type="number" class="form-control form-control-sm" name="amount" value="10000">
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="mb-3">
                                <label class="form-label">Max Hops</label>
                                <select class="form-select form-select-sm" name="max_hops">
                                    <option value="2">2 Hops</option>
                                    <option value="3" selected>3 Hops</option>
                                    <option value="4">4 Hops</option>
                                    <option value="5">5 Hops</option>
                                </select>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="mb-3">
                                <label class="form-label">Min Profit (%)</label>
                                <input type="number" class="form-control form-control-sm" name="min_profit" value="0.5">
                            </div>
                        </div>
                    </div>
                `;
                break;
                
            case 'cross_chain':
                strategyTitle = 'Cross-Chain Arbitrage Parameters';
                strategyIcon = 'exchange-alt';
                formFields = `
                    <div class="row">
                        <div class="col-md-3">
                            <div class="mb-3">
                                <label class="form-label">Target Chain</label>
                                <select class="form-select form-select-sm" name="target_chain">
                                    <option value="ethereum">Ethereum</option>
                                    <option value="binance">Binance Smart Chain</option>
                                    <option value="polygon">Polygon</option>
                                    <option value="avalanche">Avalanche</option>
                                    <option value="arbitrum">Arbitrum</option>
                                </select>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="mb-3">
                                <label class="form-label">Token</label>
                                <select class="form-select form-select-sm" name="token">
                                    <option value="USDC">USDC</option>
                                    <option value="USDT">USDT</option>
                                    <option value="DAI">DAI</option>
                                    <option value="ETH">ETH</option>
                                </select>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="mb-3">
                                <label class="form-label">Amount</label>
                                <input type="number" class="form-control form-control-sm" name="amount" value="10000">
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="mb-3">
                                <label class="form-label">Min Profit (%)</label>
                                <input type="number" class="form-control form-control-sm" name="min_profit" value="0.5">
                            </div>
                        </div>
                    </div>
                `;
                break;
                
            case 'yield_farming':
                strategyTitle = 'Yield Farming Parameters';
                strategyIcon = 'seedling';
                formFields = `
                    <div class="row">
                        <div class="col-md-3">
                            <div class="mb-3">
                                <label class="form-label">Protocol</label>
                                <select class="form-select form-select-sm" name="protocol">
                                    <option value="aave">Aave</option>
                                    <option value="compound">Compound</option>
                                    <option value="curve">Curve</option>
                                    <option value="yearn">Yearn</option>
                                </select>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="mb-3">
                                <label class="form-label">Pool</label>
                                <select class="form-select form-select-sm" name="pool">
                                    <option value="usdc">USDC</option>
                                    <option value="eth">ETH</option>
                                    <option value="dai">DAI</option>
                                    <option value="wbtc">WBTC</option>
                                </select>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="mb-3">
                                <label class="form-label">Amount</label>
                                <input type="number" class="form-control form-control-sm" name="amount" value="10000">
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="mb-3">
                                <label class="form-label">Duration (days)</label>
                                <input type="number" class="form-control form-control-sm" name="duration" value="30">
                            </div>
                        </div>
                    </div>
                `;
                break;
                
            default:
                strategyTitle = `${strategyType.replace('_', ' ')} Parameters`;
                strategyIcon = 'cog';
                formFields = '<p class="text-muted">No parameters needed for this strategy.</p>';
        }
        
        paramsDiv.innerHTML = `
            <h6 class="d-flex align-items-center mb-3">
                <i class="fas fa-${strategyIcon} me-2"></i>
                ${strategyTitle}
            </h6>
            ${formFields}
        `;
        
        return paramsDiv;
    }
    
    // Execute strategies handler
    if (executeStrategiesBtn) {
        executeStrategiesBtn.addEventListener('click', function() {
            // Collect selected wallets
            const selectedWallets = [];
            walletCheckboxes.forEach(checkbox => {
                if (checkbox.checked) {
                    selectedWallets.push(parseInt(checkbox.value));
                }
            });
            
            if (selectedWallets.length === 0) {
                alert('Please select at least one wallet');
                return;
            }
            
            // Collect selected strategies
            const selectedStrategies = [];
            const strategyParams = {};
            
            strategyCheckboxes.forEach(checkbox => {
                if (checkbox.checked) {
                    const strategyType = checkbox.value;
                    selectedStrategies.push(strategyType);
                    
                    // Collect strategy parameters
                    const paramsDiv = document.querySelector(`.strategy-params[data-strategy="${strategyType}"]`);
                    if (paramsDiv) {
                        const paramInputs = paramsDiv.querySelectorAll('input, select');
                        const params = {};
                        
                        paramInputs.forEach(input => {
                            params[input.name] = input.value;
                        });
                        
                        strategyParams[strategyType] = params;
                    }
                }
            });
            
            if (selectedStrategies.length === 0) {
                alert('Please select at least one strategy');
                return;
            }
            
            // Get execution mode
            const executionMode = document.querySelector('input[name="executionMode"]:checked').value;
            
            // Prepare request data
            const requestData = {
                wallet_ids: selectedWallets,
                strategy_types: selectedStrategies,
                execution_mode: executionMode,
                strategy_params: strategyParams
            };
            
            // Hide strategy modal and show progress modal
            if (strategiesModal) {
                strategiesModal.hide();
            }
            
            if (progressModal) {
                progressModal.show();
            }
            
            // Reset execution UI
            if (executionLogContainer) {
                executionLogContainer.innerHTML = '';
            }
            
            if (executionSummaryContainer) {
                executionSummaryContainer.innerHTML = `
                    <div class="text-center py-4">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <p class="mt-2">Executing strategies...</p>
                    </div>
                `;
            }
            
            // Reset progress bar
            const progressBar = document.querySelector('.progress-bar');
            if (progressBar) {
                progressBar.style.width = '0%';
            }
            
            // Start execution
            executeStrategies(requestData);
        });
    }
    
    // Function to execute strategies via API
    function executeStrategies(requestData) {
        // Log starting execution
        logExecution('Starting execution of selected strategies...');
        
        // Update progress bar
        const progressBar = document.querySelector('.progress-bar');
        if (progressBar) {
            progressBar.style.width = '25%';
        }
        
        // Get CSRF token - Fix the CSRF token retrieval
        let csrfToken = document.querySelector('input[name="csrf_token"]').value;
        
        // Call API
        fetch('/api/execute/wallet_strategies', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-TOKEN': csrfToken
            },
            body: JSON.stringify(requestData)
        })
        .then(response => {
            // Update progress bar
            if (progressBar) {
                progressBar.style.width = '75%';
            }
            return response.json();
        })
        .then(data => {
            // Update progress bar
            if (progressBar) {
                progressBar.style.width = '100%';
            }
            
            if (data.success) {
                // Log success
                logExecution('Execution completed successfully!');
                
                // Display summary
                displayExecutionSummary(data);
            } else {
                // Log error
                logExecution(`Error: ${data.error}`, 'error');
                
                // Display error summary
                if (executionSummaryContainer) {
                    executionSummaryContainer.innerHTML = `
                        <div class="alert alert-danger">
                            <i class="fas fa-exclamation-circle me-2"></i>
                            <strong>Execution Failed:</strong> ${data.error}
                        </div>
                    `;
                }
            }
            
            // Enable complete button
            if (completeExecutionBtn) {
                completeExecutionBtn.disabled = false;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            
            // Log error
            logExecution(`Error: ${error.message}`, 'error');
            
            // Display error summary
            if (executionSummaryContainer) {
                executionSummaryContainer.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-circle me-2"></i>
                        <strong>Execution Failed:</strong> ${error.message}
                    </div>
                `;
            }
            
            // Enable complete button
            if (completeExecutionBtn) {
                completeExecutionBtn.disabled = false;
            }
            
            // Update progress bar
            if (progressBar) {
                progressBar.style.width = '100%';
                progressBar.classList.remove('bg-primary');
                progressBar.classList.add('bg-danger');
            }
        });
    }
    
    // Function to log execution events
    function logExecution(message, type = 'info') {
        if (!executionLogContainer) return;
        
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry log-${type} mb-1`;
        
        const timestamp = new Date().toLocaleTimeString();
        logEntry.innerHTML = `<span class="log-time text-muted">[${timestamp}]</span> <span class="log-message">${message}</span>`;
        
        executionLogContainer.appendChild(logEntry);
        executionLogContainer.scrollTop = executionLogContainer.scrollHeight;
    }
    
    // Function to display execution summary
    function displayExecutionSummary(data) {
        if (!executionSummaryContainer) return;
        
        // Format profit value
        const totalProfit = parseFloat(data.total_profit || 0).toFixed(2);
        const isProfitable = parseFloat(totalProfit) > 0;
        
        let summaryHTML = `
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title d-flex justify-content-between align-items-center">
                        <span>Execution Results</span>
                        <span class="badge bg-${isProfitable ? 'success' : 'danger'}">
                            Total Profit: $${totalProfit}
                        </span>
                    </h5>
                    <div class="wallet-results">
                        <h6 class="mb-3">Results by Wallet</h6>
                        <div class="list-group">
        `;
        
        // Add wallet results
        if (data.wallets && data.wallets.length > 0) {
            data.wallets.forEach(wallet => {
                const walletProfit = parseFloat(wallet.profit || 0).toFixed(2);
                const walletProfitable = parseFloat(walletProfit) > 0;
                
                summaryHTML += `
                    <div class="list-group-item">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <strong>${wallet.address.substr(0, 8)}...${wallet.address.substr(-6)}</strong>
                                <span class="badge bg-secondary">${wallet.chain}</span>
                            </div>
                            <div>
                                <span class="badge bg-${walletProfitable ? 'success' : 'danger'}">
                                    $${walletProfit}
                                </span>
                            </div>
                        </div>
                `;
                
                // Add strategy results
                if (wallet.strategies && wallet.strategies.length > 0) {
                    summaryHTML += `<div class="strategy-results mt-2">`;
                    
                    wallet.strategies.forEach(strategy => {
                        const strategyProfit = parseFloat(strategy.profit || 0).toFixed(2);
                        
                        summaryHTML += `
                            <div class="strategy-result mb-1 small">
                                <span class="badge bg-${strategy.success ? 'success' : 'danger'} me-2">
                                    ${strategy.strategy}
                                </span>
                                <span>${strategy.success ? `$${strategyProfit}` : strategy.error || 'Failed'}</span>
                            </div>
                        `;
                    });
                    
                    summaryHTML += `</div>`;
                } else {
                    summaryHTML += `<div class="text-muted small mt-1">No strategies executed</div>`;
                }
                
                // Close list item
                summaryHTML += `</div>`;
            });
        } else {
            summaryHTML += `
                <div class="list-group-item text-center py-3">
                    <div class="text-muted">No wallets processed</div>
                </div>
            `;
        }
        
        // Close HTML
        summaryHTML += `
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        executionSummaryContainer.innerHTML = summaryHTML;
    }
    
    // Cancel execution handler
    if (cancelExecutionBtn) {
        cancelExecutionBtn.addEventListener('click', function() {
            // Log cancellation
            logExecution('Execution cancelled by user', 'warning');
            
            // Enable complete button
            if (completeExecutionBtn) {
                completeExecutionBtn.disabled = false;
            }
            
            // Update summary
            if (executionSummaryContainer) {
                executionSummaryContainer.innerHTML = `
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        <strong>Execution Cancelled</strong><br>
                        The operation was cancelled by the user. Some strategies may have already been executed.
                    </div>
                `;
            }
        });
    }
    
    // Initialize when page loads
    updateWalletCount();
    updateStrategyCount();
});