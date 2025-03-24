"""
API Routes
Flask Blueprint for API endpoints
"""
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required
from app import db
from app.models.trade import Trade, YieldFarm, DeployedToken
from app.models.wallet import ChainInfo, Wallet
from app.services.flash_loan import FlashLoanService
from app.services.multi_hop import MultiHopService
from app.services.cross_chain import CrossChainService
from app.services.yield_farming import YieldFarmingService
from app.services.ai_predictor import AIPredictorService
from app.utils.web3_helper import fetch_eth_gas_price

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
        
        # Get contract address
        contract_address = current_app.config.get(f'{chain.upper()}_FLASH_LOAN_CONTRACT')
        if not contract_address:
            return jsonify({
                'success': False,
                'error': f'Flash loan contract not deployed on {chain}'
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
    
    # Initialize AI predictor
    ai_predictor = AIPredictorService()
    
    # Make prediction
    prediction = ai_predictor.predict_best_strategy(chains, strategies, amount)
    
    return jsonify(prediction)

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
    
    # Initialize AI predictor
    ai_predictor = AIPredictorService()
    
    # Make prediction
    prediction = ai_predictor.predict_gas_prices(chain)
    
    return jsonify(prediction)

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
    
    # Initialize AI predictor
    ai_predictor = AIPredictorService()
    
    # Make prediction
    prediction = ai_predictor.get_optimal_trade_time(chain, strategy_type, amount, time_window)
    
    return jsonify(prediction)

