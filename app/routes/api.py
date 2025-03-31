"""
API Routes
Flask Blueprint for API endpoints
"""
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required
from datetime import datetime
from app import db
from app.models.trade import Trade, YieldFarm, DeployedToken
from app.models.wallet import ChainInfo, Wallet, Token
from app.services.flash_loan import FlashLoanService
from app.services.multi_hop import MultiHopService
from app.services.cross_chain import CrossChainService
from app.services.yield_farming import YieldFarmingService
from app.services.ai_predictor import AIPredictorService
from app.utils.web3_helper import fetch_eth_gas_price, generate_wallet, encrypt_private_key, get_token_balance, get_token_price, get_web3_for_chain
import random

# Create blueprint
api_bp = Blueprint('api', __name__)
@api_bp.route('/execute/flash_loan', methods=['POST'])
@login_required
def execute_flash_loan():
    """API endpoint for executing a flash loan
    Executes a flash loan arbitrage strategy
    """
    # Get request data
    data = request.get_json()
    
    # Get parameters
    chain = data.get('chain')
    token = data.get('token')
    amount = data.get('amount')
    dex1 = data.get('dex1')
    dex2 = data.get('dex2')
    
    # Validate parameters
    if not chain or not token or not amount or not dex1 or not dex2:
        return jsonify({
            'success': False,
            'error': 'Missing required parameters'
        })
    
    try:
        # Get private key from environment (in production, this would be securely stored)
        private_key = current_app.config.get(f'{chain.upper()}_PRIVATE_KEY')
        if not private_key:
            return jsonify({
                'success': False,
                'error': f'Private key not found for chain {chain}'
            })
        
        # Get contract address from config
        contract_address = current_app.config.get(f'{chain.upper()}_FLASH_LOAN_CONTRACT')
        if not contract_address:
            return jsonify({
                'success': False,
                'error': f'Flash loan contract not deployed on {chain}. Deploy contract first.'
            })
        
        # Initialize flash loan service
        flash_loan_service = FlashLoanService(chain, private_key, contract_address)
        
        # Execute flash loan
        result = flash_loan_service.execute_flash_loan(token, amount, dex1, dex2)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@api_bp.route('/deploy/flash_loan_contract', methods=['POST'])
@login_required
def deploy_flash_loan_contract():
    """API endpoint for deploying a flash loan contract"""
    try:
        # Get request data
        data = request.get_json()
        
        # Get chain
        chain = data.get('chain')
        if not chain:
            return jsonify({
                'success': False,
                'error': 'Chain is required'
            })
        
        # Get private key
        private_key = current_app.config.get(f'{chain.upper()}_PRIVATE_KEY')
        if not private_key:
            return jsonify({
                'success': False,
                'error': f'Private key not found for chain {chain}'
            })
        
        # Load contract bytecode (from file in a real application)
        contract_bytecode = '0x...'  # Replace with actual bytecode or load from file
        
        # Initialize service
        flash_loan_service = FlashLoanService(chain, private_key)
        
        # Deploy contract
        contract_address = flash_loan_service.deploy_contract(contract_bytecode)
        
        # Save contract address to config
        # In a real application, you would save this to a database
        current_app.config[f'{chain.upper()}_FLASH_LOAN_CONTRACT'] = contract_address
        
        return jsonify({
            'success': True,
            'contract_address': contract_address,
            'message': f'Flash loan contract deployed successfully on {chain}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })
@api_bp.route('/execute/multi_hop', methods=['POST'])
@login_required
def execute_multi_hop():
    """API endpoint for executing a multi-hop arbitrage
    Executes a multi-hop arbitrage strategy
    """
    # Get request data
    data = request.get_json()
    
    # Get parameters
    chain = data.get('chain')
    amount = data.get('amount')
    max_hops = data.get('max_hops', 3)
    min_profit = data.get('min_profit', 0.5) / 100  # Convert from percentage
    
    # Validate parameters
    if not chain or not amount:
        return jsonify({
            'success': False,
            'error': 'Missing required parameters'
        })
    
    try:
        # Get private key from environment
        private_key = current_app.config.get(f'{chain.upper()}_PRIVATE_KEY')
        if not private_key:
            return jsonify({
                'success': False,
                'error': f'Private key not found for chain {chain}'
            })
        
        # Initialize multi-hop service
        multi_hop_service = MultiHopService(chain, private_key)
        
        # Execute multi-hop arbitrage
        result = multi_hop_service.execute_multi_hop_arbitrage(amount, max_hops, min_profit)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@api_bp.route('/execute/cross_chain', methods=['POST'])
@login_required
def execute_cross_chain():
    """API endpoint for executing a cross-chain arbitrage
    Executes a cross-chain arbitrage strategy
    """
    # Get request data
    data = request.get_json()
    
    # Get parameters
    source_chain = data.get('source_chain')
    target_chain = data.get('target_chain')
    token = data.get('token')
    amount = data.get('amount')
    min_profit = data.get('min_profit', 0.5) / 100  # Convert from percentage
    
    # Validate parameters
    if not source_chain or not target_chain or not amount:
        return jsonify({
            'success': False,
            'error': 'Missing required parameters'
        })
    
    try:
        # Get private key from environment
        private_key = current_app.config.get(f'{source_chain.upper()}_PRIVATE_KEY')
        if not private_key:
            return jsonify({
                'success': False,
                'error': f'Private key not found for chain {source_chain}'
            })
        
        # Initialize cross-chain service
        cross_chain_service = CrossChainService(source_chain, target_chain, private_key)
        
        # Execute cross-chain arbitrage
        result = cross_chain_service.execute_cross_chain_arbitrage(token, amount, min_profit)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@api_bp.route('/execute/yield_farm', methods=['POST'])
@login_required
def execute_yield_farm():
    """API endpoint for executing a yield farming strategy
    Deposits funds into a yield farm
    """
    # Get request data
    data = request.get_json()
    
    # Get parameters
    chain = data.get('chain')
    protocol = data.get('protocol')
    pool = data.get('pool')
    amount = data.get('amount')
    
    # Validate parameters
    if not chain or not protocol or not pool or not amount:
        return jsonify({
            'success': False,
            'error': 'Missing required parameters'
        })
    
    try:
        # Get private key from environment
        private_key = current_app.config.get(f'{chain.upper()}_PRIVATE_KEY')
        if not private_key:
            return jsonify({
                'success': False,
                'error': f'Private key not found for chain {chain}'
            })
        
        # Initialize yield farming service
        yield_farming_service = YieldFarmingService(chain, private_key)
        
        # Execute deposit
        result = yield_farming_service.execute_deposit(protocol, pool, amount)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@api_bp.route('/execute/harvest', methods=['POST'])
@login_required
def execute_harvest():
    """API endpoint for harvesting yield farming rewards
    Harvests rewards from a yield farm
    """
    # Get request data
    data = request.get_json()
    
    # Get parameters
    farm_id = data.get('farm_id')
    
    # Validate parameters
    if not farm_id:
        return jsonify({
            'success': False,
            'error': 'Missing required parameters'
        })
    
    try:
        # Get farm from database
        farm = YieldFarm.query.get(farm_id)
        if not farm:
            return jsonify({
                'success': False,
                'error': f'Farm with ID {farm_id} not found'
            })
        
        # Get private key from environment
        private_key = current_app.config.get(f'{farm.chain.upper()}_PRIVATE_KEY')
        if not private_key:
            return jsonify({
                'success': False,
                'error': f'Private key not found for chain {farm.chain}'
            })
        
        # Initialize yield farming service
        yield_farming_service = YieldFarmingService(farm.chain, private_key)
        
        # Execute harvest
        result = yield_farming_service.execute_harvest(farm_id)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@api_bp.route('/execute/withdraw', methods=['POST'])
@login_required
def execute_withdraw():
    """API endpoint for withdrawing from a yield farm
    Withdraws funds from a yield farm
    """
    # Get request data
    data = request.get_json()
    
    # Get parameters
    farm_id = data.get('farm_id')
    
    # Validate parameters
    if not farm_id:
        return jsonify({
            'success': False,
            'error': 'Missing required parameters'
        })
    
    try:
        # Get farm from database
        farm = YieldFarm.query.get(farm_id)
        if not farm:
            return jsonify({
                'success': False,
                'error': f'Farm with ID {farm_id} not found'
            })
        
        # Get private key from environment
        private_key = current_app.config.get(f'{farm.chain.upper()}_PRIVATE_KEY')
        if not private_key:
            return jsonify({
                'success': False,
                'error': f'Private key not found for chain {farm.chain}'
            })
        
        # Initialize yield farming service
        yield_farming_service = YieldFarmingService(farm.chain, private_key)
        
        # Execute withdraw
        result = yield_farming_service.execute_withdraw(farm_id)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@api_bp.route('/execute/all', methods=['POST'])
@login_required
def execute_all():
    """API endpoint for executing all strategies
    Executes all strategies across multiple chains
    """
    # Get request data
    data = request.get_json()
    
    # Get parameters
    chains = data.get('chains', [])
    strategies = data.get('strategies', [])
    
    # Implement the same logic as in strategies_bp.execute_full_cycle()
    try:
        # If no chains specified, use all active chains
        if not chains:
            chain_infos = ChainInfo.query.filter_by(status='active').all()
            chains = [chain.name for chain in chain_infos]
        
        # If no strategies specified, use all strategies
        if not strategies:
            strategies = ['flash_loan', 'multi_hop', 'cross_chain', 'yield_farming']
        
        # Initialize results
        results = {
            'success': True,
            'chains': [],
            'total_profit': 0
        }
        
        # Execute strategies on each chain
        for chain in chains:
            chain_result = {
                'chain': chain,
                'strategies': [],
                'total_profit': 0
            }
            
            # Get private key
            private_key = current_app.config.get(f'{chain.upper()}_PRIVATE_KEY')
            if not private_key:
                chain_result['error'] = 'Private key not found'
                results['chains'].append(chain_result)
                continue
            
            # Execute each strategy
            for strategy in strategies:
                if strategy == 'flash_loan' and 'flash_loan' in strategies:
                    contract_address = current_app.config.get(f'{chain.upper()}_FLASH_LOAN_CONTRACT')
                    if contract_address:
                        try:
                            flash_loan_service = FlashLoanService(chain, private_key, contract_address)
                            flash_result = flash_loan_service.execute_flash_loan('DAI', 1000000, 'uniswap', 'sushiswap')
                            
                            chain_result['strategies'].append({
                                'strategy': 'flash_loan',
                                'success': flash_result['success'],
                                'profit': flash_result.get('net_profit', 0)
                            })
                            
                            if flash_result['success']:
                                chain_result['total_profit'] += flash_result.get('net_profit', 0)
                        except Exception as e:
                            chain_result['strategies'].append({
                                'strategy': 'flash_loan',
                                'success': False,
                                'error': str(e)
                            })
                
                if strategy == 'multi_hop' and 'multi_hop' in strategies:
                    try:
                        multi_hop_service = MultiHopService(chain, private_key)
                        multi_hop_result = multi_hop_service.execute_multi_hop_arbitrage(10000, 3, 0.005)
                        
                        chain_result['strategies'].append({
                            'strategy': 'multi_hop',
                            'success': multi_hop_result['success'],
                            'profit': multi_hop_result.get('net_profit', 0)
                        })
                        
                        if multi_hop_result['success']:
                            chain_result['total_profit'] += multi_hop_result.get('net_profit', 0)
                    except Exception as e:
                        chain_result['strategies'].append({
                            'strategy': 'multi_hop',
                            'success': False,
                            'error': str(e)
                        })
            
            # Update total profit
            results['total_profit'] += chain_result['total_profit']
            results['chains'].append(chain_result)
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@api_bp.route('/stats')
@login_required
def stats():
    """API endpoint for dashboard stats
    Returns aggregate statistics for the dashboard
    """
    # Implement the same logic as in dashboard_bp.api_stats()
    from app.routes.dashboard import api_stats
    return api_stats()

@api_bp.route('/chains')
@login_required
def chains():
    """API endpoint for chain information
    Returns information about all supported chains
    """
    chains = ChainInfo.query.all()
    
    return jsonify({
        'success': True,
        'chains': [chain.to_dict() for chain in chains]
    })

@api_bp.route('/wallets')
@login_required
def wallets():
    """API endpoint for wallet information
    Returns information about all wallets
    """
    wallets = Wallet.query.all()
    
    return jsonify({
        'success': True,
        'wallets': [wallet.to_dict() for wallet in wallets]
    })

@api_bp.route('/trades')
@login_required
def trades():
    """API endpoint for trade information
    Returns information about trades with optional filtering
    """
    # Get query parameters
    strategy = request.args.get('strategy')
    chain = request.args.get('chain')
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # Build query
    query = Trade.query
    
    if strategy:
        query = query.filter(Trade.strategy_type == strategy)
    
    if chain:
        query = query.filter(Trade.chain == chain)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    trades = query.order_by(Trade.created_at.desc()).limit(limit).offset(offset).all()
    
    return jsonify({
        'success': True,
        'total': total,
        'limit': limit,
        'offset': offset,
        'trades': [trade.to_dict() for trade in trades]
    })

@api_bp.route('/farms')
@login_required
def farms():
    """API endpoint for yield farm information
    Returns information about yield farms
    """
    # Get query parameters
    status = request.args.get('status')
    chain = request.args.get('chain')
    
    # Build query
    query = YieldFarm.query
    
    if status:
        query = query.filter(YieldFarm.status == status)
    
    if chain:
        query = query.filter(YieldFarm.chain == chain)
    
    # Get farms
    farms = query.order_by(YieldFarm.start_date.desc()).all()
    
    return jsonify({
        'success': True,
        'farms': [farm.to_dict() for farm in farms]
    })

@api_bp.route('/tokens')
@login_required
def tokens():
    """API endpoint for token information
    Returns information about deployed tokens
    """
    # Get query parameters
    chain = request.args.get('chain')
    
    # Build query
    query = DeployedToken.query
    
    if chain:
        query = query.filter(DeployedToken.chain == chain)
    
    # Get tokens
    tokens = query.order_by(DeployedToken.created_at.desc()).all()
    
    return jsonify({
        'success': True,
        'tokens': [token.to_dict() for token in tokens]
    })

@api_bp.route('/gas')
@login_required
def gas():
    """API endpoint for gas prices
    Returns current gas prices for Ethereum
    """
    gas_prices = fetch_eth_gas_price()
    
    return jsonify({
        'success': True,
        'gas_prices': gas_prices
    })

@api_bp.route('/predict/strategy', methods=['POST'])
@login_required
def predict_strategy():
    """API endpoint for predicting best strategy
    Uses AI to predict the best trading strategy
    """
    # Get request data
    data = request.get_json()
    
    # Get parameters
    chains = data.get('chains')
    strategies = data.get('strategies')
    amount = data.get('amount', 10000)
    
    try:
        # Initialize AI predictor
        ai_predictor = AIPredictorService()
        
        # Make prediction
        prediction = ai_predictor.predict_best_strategy(chains, strategies, amount)
        
        return jsonify(prediction)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@api_bp.route('/predict/gas', methods=['POST'])
@login_required
def predict_gas():
    """API endpoint for predicting gas prices
    Uses AI to predict gas prices for the next 24 hours
    """
    # Get request data
    data = request.get_json()
    
    # Get parameters
    chain = data.get('chain', 'ethereum')
    
    try:
        # Initialize AI predictor
        ai_predictor = AIPredictorService()
        
        # Make prediction
        prediction = ai_predictor.predict_gas_prices(chain)
        
        return jsonify(prediction)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@api_bp.route('/predict/trade_time', methods=['POST'])
@login_required
def predict_trade_time():
    """API endpoint for predicting optimal trade time
    Uses AI to predict the best time to execute a trade
    """
    # Get request data
    data = request.get_json()
    
    # Get parameters
    chain = data.get('chain', 'ethereum')
    strategy_type = data.get('strategy_type', 'flash_loan')
    amount = data.get('amount', 10000)
    time_window = data.get('time_window', 24)
    
    try:
        # Initialize AI predictor
        ai_predictor = AIPredictorService()
        
        # Make prediction
        prediction = ai_predictor.get_optimal_trade_time(chain, strategy_type, amount, time_window)
        
        return jsonify(prediction)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

# Chain Management API endpoints
@api_bp.route('/chain/<int:chain_id>')
@login_required
def get_chain_details(chain_id):
    """Get details for a specific chain"""
    try:
        chain = ChainInfo.query.get(chain_id)
        if not chain:
            return jsonify({
                'success': False,
                'error': f'Chain with ID {chain_id} not found'
            })
        
        return jsonify(chain.to_dict())
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@api_bp.route('/chain_gas_history/<int:chain_id>')
@login_required
def get_chain_gas_history(chain_id):
    """Get gas price history for a chain"""
    try:
        chain = ChainInfo.query.get(chain_id)
        if not chain:
            return jsonify({
                'success': False,
                'error': f'Chain with ID {chain_id} not found'
            })
        
        # In a real application, you would query a time-series database or blockchain API
        # For demo purposes, we'll generate mock data
        now = datetime.utcnow()
        gas_history = []
        
        # Generate mock gas price history
        base_price = chain.avg_gas_price or 50.0
        
        for i in range(30, -1, -1):
            date = now - timedelta(days=i)
            
            # Generate a value with some variation around the base price
            variation = (random.random() - 0.5) * 0.4  # -20% to +20%
            gas_price = max(1, base_price * (1 + variation))
            
            gas_history.append({
                'date': date.strftime('%Y-%m-%d'),
                'gas_price': round(gas_price, 1)
            })
        
        return jsonify(gas_history)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@api_bp.route('/update_chain', methods=['POST'])
@login_required
def update_chain():
    """Update chain information"""
    try:
        chain_id = request.form.get('id')
        name = request.form.get('name')
        chain_id_value = request.form.get('chain_id')
        rpc_url = request.form.get('rpc_url')
        explorer_url = request.form.get('explorer_url')
        currency_symbol = request.form.get('currency_symbol')
        tatum_network = request.form.get('tatum_network')
        tatum_tier = request.form.get('tatum_tier')
        status = request.form.get('status')
        
        # Validate required fields
        if not chain_id or not name or not chain_id_value or not rpc_url or not currency_symbol or not status:
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            })
        
        # Get chain from database
        chain = ChainInfo.query.get(chain_id)
        if not chain:
            return jsonify({
                'success': False,
                'error': f'Chain with ID {chain_id} not found'
            })
        
        # Check if name is being changed and if there's a conflict
        if name != chain.name:
            existing_chain = ChainInfo.query.filter(ChainInfo.name == name, ChainInfo.id != chain.id).first()
            if existing_chain:
                return jsonify({
                    'success': False,
                    'error': f'Chain with name {name} already exists'
                })
        
        # Check if chain_id is being changed and if there's a conflict
        if int(chain_id_value) != chain.chain_id:
            existing_chain = ChainInfo.query.filter(ChainInfo.chain_id == int(chain_id_value), ChainInfo.id != chain.id).first()
            if existing_chain:
                return jsonify({
                    'success': False,
                    'error': f'Chain with chain ID {chain_id_value} already exists'
                })
        
        # Update chain information
        chain.name = name
        chain.chain_id = int(chain_id_value)
        chain.rpc_url = rpc_url
        chain.explorer_url = explorer_url
        chain.currency_symbol = currency_symbol
        chain.tatum_network = tatum_network
        chain.tatum_tier = int(tatum_tier) if tatum_tier else None
        chain.status = status
        chain.last_updated = datetime.utcnow()
        
        # Test connection to the new RPC URL
        try:
            web3 = get_web3(rpc_url)
            # Check if connection is successful by calling a method
            web3.eth.block_number
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to connect to RPC URL: {str(e)}'
            })
        
        # Save to database
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Chain {name} updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        })

@api_bp.route('/add_chain', methods=['POST'])
@login_required
def add_chain():
    """Add a new chain"""
    try:
        name = request.form.get('name')
        chain_id_value = request.form.get('chain_id')
        rpc_url = request.form.get('rpc_url')
        explorer_url = request.form.get('explorer_url')
        currency_symbol = request.form.get('currency_symbol')
        tatum_network = request.form.get('tatum_network')
        tatum_tier = request.form.get('tatum_tier')
        status = request.form.get('status', 'active')
        
        # Validate required fields
        if not name or not chain_id_value or not rpc_url or not currency_symbol:
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            })
        
        # Check for existing chain with same name or chain ID
        existing_chain_name = ChainInfo.query.filter_by(name=name).first()
        if existing_chain_name:
            return jsonify({
                'success': False,
                'error': f'Chain with name {name} already exists'
            })
        
        existing_chain_id = ChainInfo.query.filter_by(chain_id=int(chain_id_value)).first()
        if existing_chain_id:
            return jsonify({
                'success': False,
                'error': f'Chain with chain ID {chain_id_value} already exists'
            })
        
        # Test connection to the new RPC URL
        try:
            web3 = get_web3(rpc_url)
            # Check if connection is successful by calling a method
            web3.eth.block_number
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to connect to RPC URL: {str(e)}'
            })
        
        # Create new chain
        new_chain = ChainInfo(
            name=name,
            chain_id=int(chain_id_value),
            rpc_url=rpc_url,
            explorer_url=explorer_url,
            currency_symbol=currency_symbol,
            tatum_network=tatum_network,
            tatum_tier=int(tatum_tier) if tatum_tier else None,
            status=status,
            avg_gas_price=50.0,  # Default value
            avg_confirmation_time=10.0,  # Default value
            last_updated=datetime.utcnow()
        )
        
        # Save to database
        db.session.add(new_chain)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Chain {name} added successfully',
            'chain': new_chain.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        })

@api_bp.route('/update_chain_status', methods=['POST'])
@login_required
def update_chain_status():
    """Update chain status"""
    try:
        chain_id = request.form.get('chain_id')
        status = request.form.get('status')
        reason = request.form.get('reason', '')
        
        # Validate required fields
        if not chain_id or not status:
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            })
        
        # Get chain from database
        chain = ChainInfo.query.get(chain_id)
        if not chain:
            return jsonify({
                'success': False,
                'error': f'Chain with ID {chain_id} not found'
            })
        
        # Update chain status
        chain.status = status
        chain.last_updated = datetime.utcnow()
        
        # Save to database
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Chain {chain.name} status updated to {status}'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        })

@api_bp.route('/refresh_gas_prices', methods=['POST'])
@login_required
def refresh_gas_prices():
    """Refresh gas prices for chains"""
    try:
        selected_chains = request.form.getlist('chains')
        
        # If 'all' is selected, refresh all chains
        if 'all' in selected_chains:
            chains = ChainInfo.query.all()
        else:
            chains = ChainInfo.query.filter(ChainInfo.name.in_(selected_chains)).all()
        
        # Update gas prices for selected chains
        updated_chains = []
        
        for chain in chains:
            try:
                # For Ethereum, we can use a real gas price API
                if chain.name.lower() == 'ethereum':
                    gas_prices = fetch_eth_gas_price()
                    chain.avg_gas_price = gas_prices.get('average', chain.avg_gas_price)
                else:
                    # For other chains, use random values for demo
                    chain.avg_gas_price = max(1, chain.avg_gas_price * (1 + (random.random() - 0.5) * 0.2))
                    chain.avg_confirmation_time = max(1, random.uniform(2, 30))
                
                # Update status based on gas price
                old_status = chain.status
                if chain.avg_gas_price > 80.0:
                    chain.status = 'congested'
                elif chain.avg_gas_price < 20.0 and chain.status == 'congested':
                    chain.status = 'active'
                
                chain.last_updated = datetime.utcnow()
                updated_chains.append({
                    'name': chain.name,
                    'gas_price': chain.avg_gas_price,
                    'confirmation_time': chain.avg_confirmation_time,
                    'status': chain.status,
                    'status_changed': chain.status != old_status
                })
            except Exception as e:
                # Log error but continue with other chains
                print(f"Error updating gas price for chain {chain.name}: {str(e)}")
        
        # Save to database
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Gas prices refreshed for {len(updated_chains)} chains',
            'updated_chains': updated_chains
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        })

# Wallet Management API endpoints
@api_bp.route('/wallet/<int:wallet_id>/tokens')
@login_required
def get_wallet_tokens(wallet_id):
    """Get tokens for a specific wallet"""
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with ID {wallet_id} not found'
            })
        
        tokens = Token.query.filter_by(wallet_id=wallet_id).all()
        
        return jsonify({
            'success': True,
            'tokens': [token.to_dict() for token in tokens]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@api_bp.route('/wallet/<int:wallet_id>/refresh-tokens', methods=['POST'])
@login_required
def refresh_wallet_tokens(wallet_id):
    """Refresh token balances for a wallet"""
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with ID {wallet_id} not found'
            })
        
        # Get Web3 connection for the chain
        web3 = get_web3_for_chain(wallet.chain)
        
        # Update native balance
        native_balance = web3.eth.get_balance(wallet.address)
        wallet.native_balance = web3.from_wei(native_balance, 'ether')
        
        # Get chain info for currency price
        chain_info = ChainInfo.query.filter_by(name=wallet.chain).first()
        if chain_info:
            # Update USD value based on current token price
            # This is a simplified example - in a real app, you'd get the actual price from an API
            usd_value = wallet.native_balance * 1500  # Assuming price of 1500 USD per token
            wallet.usd_balance = usd_value
        
        # Update token balances
        tokens = Token.query.filter_by(wallet_id=wallet_id).all()
        for token in tokens:
            try:
                # Get current token balance
                balance = get_token_balance(web3, token.address, wallet.address)
                token.balance = balance
                
                # Get current token price and update USD value
                token_price = get_token_price(token.address, wallet.chain)
                token.usd_value = balance * token_price
            except Exception as e:
                # Log error but continue with other tokens
                print(f"Error updating token {token.symbol}: {str(e)}")
        
        # Update last updated timestamp
        wallet.last_updated = datetime.utcnow()
        
        # Save to database
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Wallet tokens refreshed successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        })

@api_bp.route('/wallet/<int:wallet_id>/delete', methods=['POST'])
@login_required
def delete_wallet(wallet_id):
    """Delete a wallet"""
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with ID {wallet_id} not found'
            })
        
        # Delete associated tokens
        Token.query.filter_by(wallet_id=wallet_id).delete()
        
        # Delete wallet
        db.session.delete(wallet)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Wallet deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        })

@api_bp.route('/wallet/toggle_active', methods=['POST'])
@login_required
def toggle_wallet_active():
    """Toggle wallet active state"""
    try:
        data = request.get_json()
        wallet_id = data.get('wallet_id')
        is_active = data.get('is_active')
        
        if wallet_id is None or is_active is None:
            return jsonify({
                'success': False,
                'error': 'Missing required parameters'
            })
        
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with ID {wallet_id} not found'
            })
        
        wallet.is_active = is_active
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Wallet active state set to {is_active}'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        })
@api_bp.route('/wallets/refresh', methods=['POST'])
@login_required
def refresh_all_wallets():
    """Refresh balances for all wallets"""
    try:
        wallets = Wallet.query.all()
        updated_wallets = []
        
        for wallet in wallets:
            try:
                print(f"Refreshing wallet {wallet.id} on chain {wallet.chain}")
                
                # Get chain info and RPC URL
                chain_info = ChainInfo.query.filter_by(name=wallet.chain).first()
                print(f"Using RPC URL: {chain_info.rpc_url if chain_info else 'Chain not found'}")
                
                # Get Web3 connection for the chain
                web3 = get_web3_for_chain(wallet.chain)
                
                # Test connection
                block_number = web3.eth.block_number
                print(f"Connected to blockchain. Current block: {block_number}")
                
                # Convert address to checksum format
                checksum_address = web3.to_checksum_address(wallet.address)
                
                # Update native balance
                old_balance = wallet.native_balance
                native_balance = web3.eth.get_balance(checksum_address)
                wallet.native_balance = float(web3.from_wei(native_balance, 'ether'))
                
                print(f"Updated balance: {old_balance} -> {wallet.native_balance}")
                
                # Get chain info for currency price
                if chain_info:
                    # Update USD value based on current token price
                    usd_value = wallet.native_balance * 1500
                    wallet.usd_balance = usd_value
                
                # Update last updated timestamp
                wallet.last_updated = datetime.utcnow()
                updated_wallets.append({
                    'address': wallet.address,
                    'chain': wallet.chain,
                    'balance': float(wallet.native_balance)
                })
            except Exception as e:
                # Log error but continue with other wallets
                print(f"Error updating wallet {wallet.id}: {str(e)}")
        
        # Save to database
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'All wallets refreshed successfully',
            'updated_wallets': updated_wallets
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        })
@api_bp.route('/create_wallet', methods=['POST'])
@login_required
def create_wallet():
    """Create a new wallet"""
    try:
        chain = request.form.get('chain')
        
        if not chain:
            return jsonify({
                'success': False,
                'error': 'Chain is required'
            })
        
        # Get chain info
        chain_info = ChainInfo.query.filter_by(name=chain).first()
        if not chain_info:
            return jsonify({
                'success': False,
                'error': f'Chain {chain} not found'
            })
        
        # Generate new wallet
        address, private_key = generate_wallet()
        
        # Encrypt private key if a password was provided
        # In a production system, you would use a more secure method
        private_key_encrypted = None
        if request.form.get('encryption_password'):
            private_key_encrypted = encrypt_private_key(private_key, request.form.get('encryption_password'))
        
        # Create new wallet in database
        new_wallet = Wallet(
            address=address,
            chain=chain,
            private_key_encrypted=private_key_encrypted,
            native_balance=0.0,
            usd_balance=0.0,
            is_active=True,
            is_contract=False,
            last_updated=datetime.utcnow()
        )
        
        db.session.add(new_wallet)
        db.session.commit()
        
        # Return success with new wallet info and private key for the user to save
        return jsonify({
            'success': True,
            'message': 'Wallet created successfully',
            'wallet': {
                'id': new_wallet.id,
                'address': address,
                'chain': chain,
                'private_key': private_key  # Only return this once for user to save
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        })

@api_bp.route('/add_wallet', methods=['POST'])
@login_required
def add_wallet():
    """Add an existing wallet"""
    try:
        chain = request.form.get('existing-chain')
        address = request.form.get('address')
        private_key = request.form.get('private-key')
        
        if not chain or not address:
            return jsonify({
                'success': False,
                'error': 'Chain and address are required'
            })
        
        # Validate address format
        if not address.startswith('0x') or len(address) != 42:
            return jsonify({
                'success': False,
                'error': 'Invalid wallet address format'
            })
        
        # Get chain info
        chain_info = ChainInfo.query.filter_by(name=chain).first()
        if not chain_info:
            return jsonify({
                'success': False,
                'error': f'Chain {chain} not found'
            })
            
        # Get web3 instance to convert address to checksum format
        web3 = get_web3_for_chain(chain)
        checksum_address = web3.to_checksum_address(address)
        
        # Check if wallet already exists
        existing_wallet = Wallet.query.filter_by(address=checksum_address, chain=chain).first()
        if existing_wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with address {checksum_address} already exists on chain {chain}'
            })
        
        # Encrypt private key if provided
        private_key_encrypted = None
        if private_key:
            # In a production system, you would use a more secure method
            private_key_encrypted = encrypt_private_key(private_key, 'default_password')
        
        # Create new wallet in database with checksum address
        new_wallet = Wallet(
            address=checksum_address,  # Use checksum address
            chain=chain,
            private_key_encrypted=private_key_encrypted,
            native_balance=0.0,
            usd_balance=0.0,
            is_active=True,
            is_contract=False,
            last_updated=datetime.utcnow()
        )
        
        db.session.add(new_wallet)
        db.session.commit()
        
        # Get initial balance (optional)
        try:
            # Update native balance immediately
            native_balance = web3.eth.get_balance(checksum_address)
            new_wallet.native_balance = float(web3.from_wei(native_balance, 'ether'))
            
            # Update USD value
            new_wallet.usd_balance = new_wallet.native_balance * 1500
            db.session.commit()
        except Exception as e:
            print(f"Error fetching initial balance: {str(e)}")
            # Continue without initial balance refresh
        
        # Return success
        return jsonify({
            'success': True,
            'message': 'Wallet added successfully',
            'wallet': {
                'id': new_wallet.id,
                'address': checksum_address,
                'chain': chain,
                'balance': float(new_wallet.native_balance)
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        })
@api_bp.route('/execute/wallet_strategies', methods=['POST'])
@login_required
def execute_wallet_strategies():
    """API endpoint for executing selected strategies across specified wallets
    Executes multiple strategies on a selection of wallets
    """
    try:
        # Get request data
        data = request.get_json()
        
        # Get parameters
        wallet_ids = data.get('wallet_ids', [])
        strategy_types = data.get('strategy_types', [])
        execution_mode = data.get('execution_mode', 'parallel')  # 'parallel' or 'sequential'
        strategy_params = data.get('strategy_params', {})
        
        # Validation
        if not wallet_ids:
            return jsonify({
                'success': False,
                'error': 'No wallets selected'
            })
            
        if not strategy_types:
            return jsonify({
                'success': False,
                'error': 'No strategies selected'
            })
        
        # Handle 'all' wallets option
        if 'all' in wallet_ids:
            wallets = Wallet.query.filter_by(is_active=True).all()
            wallet_ids = [wallet.id for wallet in wallets]
        
        # Initialize wallet strategy executor
        from app.services.wallet_strategy_executor import WalletStrategyExecutor
        executor = WalletStrategyExecutor()
        
        # Execute strategies
        results = executor.execute_strategies(
            wallet_ids=wallet_ids,
            strategy_types=strategy_types,
            execution_mode=execution_mode,
            strategy_params=strategy_params
        )
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@api_bp.route('/wallet/update', methods=['POST'])
@login_required
def update_wallet():
    """Update wallet information"""
    try:
        wallet_id = request.form.get('wallet_id')
        private_key = request.form.get('private_key')
        is_active = request.form.get('is_active') == 'on'
        
        if not wallet_id:
            return jsonify({
                'success': False,
                'error': 'Wallet ID is required'
            })
        
        # Get wallet from database
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with ID {wallet_id} not found'
            })
        
        # Update wallet information
        if private_key:
            try:
                # Clean up the private key input - this is crucial
                private_key = private_key.strip()
                
                # Remove 0x prefix if present
                if private_key.startswith('0x'):
                    private_key = private_key[2:]
                
                # Check if private key is valid hexadecimal
                try:
                    int(private_key, 16)
                except ValueError:
                    return jsonify({
                        'success': False,
                        'error': f'Private key must be a valid hexadecimal string'
                    })
                
                # Check length
                if len(private_key) != 64:
                    return jsonify({
                        'success': False, 
                        'error': f'Private key must be 64 hex characters (got {len(private_key)})'
                    })
                
                # In a production system, use a secure method to encrypt the private key
                wallet.private_key_encrypted = encrypt_private_key(private_key, 'default_password')
            
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Invalid private key format: {str(e)}'
                })
        
        wallet.is_active = is_active
        wallet.last_updated = datetime.utcnow()
        
        # Save to database
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Wallet updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        })

@api_bp.route('/import_wallet', methods=['POST'])
@login_required
def import_wallet():
    """Import wallet using keystore, mnemonic, or private key"""
    try:
        import_method = request.form.get('import_method')
        import_chains = request.form.getlist('import_chains')
        
        if not import_method:
            return jsonify({
                'success': False,
                'error': 'Import method is required'
            })
        
        if not import_chains:
            return jsonify({
                'success': False,
                'error': 'At least one chain must be selected'
            })
        
        # Generate address and private key based on import method
        address = None
        private_key = None
        
        if import_method == 'keystore':
            # In a real implementation, you would parse the keystore file and decrypt it
            keystore_file = request.files.get('keystore_file')
            keystore_password = request.form.get('keystore_password')
            
            if not keystore_file or not keystore_password:
                return jsonify({
                    'success': False,
                    'error': 'Keystore file and password are required'
                })
            
            # Parse keystore file and extract address and private key
            # This is a simplified example
            address = '0x' + ''.join([f'{i:x}' for i in range(20)])
            private_key = '0x' + ''.join([f'{i:x}' for i in range(32)])
            
        elif import_method == 'mnemonic':
            mnemonic_phrase = request.form.get('mnemonic_phrase')
            derivation_path = request.form.get('derivation_path')
            
            if not mnemonic_phrase:
                return jsonify({
                    'success': False,
                    'error': 'Mnemonic phrase is required'
                })
            
            # Derive address and private key from mnemonic
            # This is a simplified example
            address = '0x' + ''.join([f'{i:x}' for i in range(20)])
            private_key = '0x' + ''.join([f'{i:x}' for i in range(32)])
            
        elif import_method == 'private_key':
            private_key = request.form.get('private_key')
            
            if not private_key:
                return jsonify({
                    'success': False,
                    'error': 'Private key is required'
                })
            
            # Derive address from private key
            # This is a simplified example
            address = '0x' + ''.join([f'{i:x}' for i in range(20)])
        
        else:
            return jsonify({
                'success': False,
                'error': f'Unknown import method: {import_method}'
            })
        
        # Encrypt private key
        # In a production system, you would use a more secure method
        private_key_encrypted = encrypt_private_key(private_key, 'default_password')
        
        # Create wallets for each selected chain
        wallets = []
        
        for chain_name in import_chains:
            # Get chain info
            chain_info = ChainInfo.query.filter_by(name=chain_name).first()
            if not chain_info:
                continue  # Skip chains that don't exist
            
            # Check if wallet already exists
            existing_wallet = Wallet.query.filter_by(address=address, chain=chain_name).first()
            if existing_wallet:
                continue  # Skip existing wallets
            
            # Create new wallet in database
            new_wallet = Wallet(
                address=address,
                chain=chain_name,
                private_key_encrypted=private_key_encrypted,
                native_balance=0.0,
                usd_balance=0.0,
                is_active=True,
                is_contract=False,
                last_updated=datetime.utcnow()
            )
            
            db.session.add(new_wallet)
            wallets.append({
                'chain': chain_name,
                'address': address
            })
        
        db.session.commit()
        
        # Return success
        return jsonify({
            'success': True,
            'message': f'Imported wallet to {len(wallets)} chains',
            'wallets': wallets
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        })

@api_bp.route('/delete_chain/<int:chain_id>', methods=['POST'])
@login_required
def delete_chain(chain_id):
    """Delete a chain"""
    try:
        chain = ChainInfo.query.get(chain_id)
        if not chain:
            return jsonify({
                'success': False,
                'error': f'Chain with ID {chain_id} not found'
            })
        
        # Check if chain has associated wallets
        wallets = Wallet.query.filter_by(chain=chain.name).all()
        if wallets:
            return jsonify({
                'success': False,
                'error': f'Cannot delete chain {chain.name} because it has {len(wallets)} associated wallets'
            })
        
        # Get chain name for confirmation message
        chain_name = chain.name
        
        # Delete chain
        db.session.delete(chain)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Chain {chain_name} deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        })
        