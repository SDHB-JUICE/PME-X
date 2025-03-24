"""
Strategy Routes
Flask Blueprint for strategy-related routes
"""
import json
from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models.trade import Trade, YieldFarm, DeployedToken
from app.models.wallet import ChainInfo
from app.services.flash_loan import FlashLoanService
from app.services.multi_hop import MultiHopService
from app.services.cross_chain import CrossChainService
from app.services.yield_farming import YieldFarmingService
from app.services.erc20_deployer import ERC20DeployerService
from app.services.auto_harvest import AutoHarvestService
from app.services.telegram_alert import send_alert
from app.utils.web3_helper import get_web3

# Create blueprint
strategies_bp = Blueprint('strategies', __name__)

@strategies_bp.route('/execute_flash_loan', methods=['GET', 'POST'])
@login_required
def execute_flash_loan():
    """Execute flash loan strategy"""
    if request.method == 'POST':
        try:
            # Get form data
            chain_name = request.form.get('chain')
            token_symbol = request.form.get('token')
            amount = float(request.form.get('amount'))
            dex1 = request.form.get('dex1')
            dex2 = request.form.get('dex2')
            
            # Validate inputs
            if not chain_name or not token_symbol or not amount or not dex1 or not dex2:
                flash('All fields are required', 'danger')
                return redirect(url_for('strategies.flash_loan'))
            
            # Get chain info
            chain_info = ChainInfo.query.filter_by(name=chain_name).first()
            if not chain_info:
                flash(f'Chain {chain_name} not found', 'danger')
                return redirect(url_for('strategies.flash_loan'))
            
            # Get private key from environment (in production, this would be securely stored)
            private_key = current_app.config.get(f'{chain_name.upper()}_PRIVATE_KEY')
            if not private_key:
                flash(f'Private key not found for chain {chain_name}', 'danger')
                return redirect(url_for('strategies.flash_loan'))
            
            # Get contract address (in production, this would be stored in database)
            contract_address = current_app.config.get(f'{chain_name.upper()}_FLASH_LOAN_CONTRACT')
            if not contract_address:
                flash(f'Flash loan contract not deployed on {chain_name}', 'danger')
                return redirect(url_for('strategies.flash_loan'))
            
            # Initialize flash loan service
            flash_loan_service = FlashLoanService(chain_name, private_key, contract_address)
            
            # Execute flash loan
            result = flash_loan_service.execute_flash_loan(token_symbol, amount, dex1, dex2)
            
            if result['success']:
                flash(f'Flash loan executed successfully. Profit: ${result["net_profit"]:.2f}', 'success')
            else:
                flash(f'Flash loan execution failed: {result["error"]}', 'danger')
            
            return redirect(url_for('strategies.flash_loan'))
            
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('strategies.flash_loan'))
    
    # GET request
    chains = ChainInfo.query.all()
    recent_trades = Trade.query.filter_by(strategy_type='flash_loan').order_by(Trade.created_at.desc()).limit(10).all()
    
    return render_template('strategies/flash_loan.html', 
                           chains=chains, 
                           recent_trades=recent_trades,
                           title='Flash Loan')

@strategies_bp.route('/multi_hop_arbitrage', methods=['GET', 'POST'])
@login_required
def multi_hop_arbitrage():
    """Execute multi-hop arbitrage strategy"""
    if request.method == 'POST':
        try:
            # Get form data
            chain_name = request.form.get('chain')
            amount = float(request.form.get('amount'))
            max_hops = int(request.form.get('max_hops', 3))
            min_profit = float(request.form.get('min_profit', 0.5)) / 100  # Convert from percentage
            
            # Validate inputs
            if not chain_name or not amount:
                flash('Chain and amount are required', 'danger')
                return redirect(url_for('strategies.multi_hop_arbitrage'))
            
            # Get chain info
            chain_info = ChainInfo.query.filter_by(name=chain_name).first()
            if not chain_info:
                flash(f'Chain {chain_name} not found', 'danger')
                return redirect(url_for('strategies.multi_hop_arbitrage'))
            
            # Get private key from environment (in production, this would be securely stored)
            private_key = current_app.config.get(f'{chain_name.upper()}_PRIVATE_KEY')
            if not private_key:
                flash(f'Private key not found for chain {chain_name}', 'danger')
                return redirect(url_for('strategies.multi_hop_arbitrage'))
            
            # Initialize multi-hop service
            multi_hop_service = MultiHopService(chain_name, private_key)
            
            # Execute multi-hop arbitrage
            result = multi_hop_service.execute_multi_hop_arbitrage(amount, max_hops, min_profit)
            
            if result['success']:
                flash(f'Multi-hop arbitrage executed successfully. Profit: ${result["net_profit"]:.2f}', 'success')
            else:
                flash(f'Multi-hop arbitrage execution failed: {result["error"]}', 'danger')
            
            return redirect(url_for('strategies.multi_hop_arbitrage'))
            
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('strategies.multi_hop_arbitrage'))
    
    # GET request
    chains = ChainInfo.query.all()
    recent_trades = Trade.query.filter_by(strategy_type='multi_hop').order_by(Trade.created_at.desc()).limit(10).all()
    
    return render_template('strategies/multi_hop.html', 
                           chains=chains, 
                           recent_trades=recent_trades,
                           title='Multi-Hop Arbitrage')

@strategies_bp.route('/cross_chain_arbitrage', methods=['GET', 'POST'])
@login_required
def cross_chain_arbitrage():
    """Execute cross-chain arbitrage strategy"""
    # Implement similar to flash_loan and multi_hop
    return render_template('strategies/cross_chain.html', title='Cross-Chain Arbitrage')

@strategies_bp.route('/execute_yield_farm', methods=['GET', 'POST'])
@login_required
def execute_yield_farm():
    """Execute yield farming strategy"""
    # Implement similar to flash_loan and multi_hop
    return render_template('strategies/yield_farming.html', title='Yield Farming')

@strategies_bp.route('/deploy_erc20', methods=['GET', 'POST'])
@login_required
def deploy_erc20():
    """Deploy custom ERC20 token"""
    # Implement similar to flash_loan and multi_hop
    return render_template('strategies/erc20_deployer.html', title='ERC20 Deployer')

@strategies_bp.route('/harvest_rewards', methods=['GET', 'POST'])
@login_required
def harvest_rewards():
    """Harvest yield farming rewards"""
    # Implement similar to flash_loan and multi_hop
    return render_template('strategies/auto_harvest.html', title='Auto Harvest')

@strategies_bp.route('/ai_predictor', methods=['GET', 'POST'])
@login_required
def ai_predictor():
    """Use AI to predict best trading opportunities"""
    # Implement AI prediction logic
    return render_template('strategies/ai_predictor.html', title='AI Predictor')

@strategies_bp.route('/send_telegram_alert', methods=['POST'])
@login_required
def send_telegram_alert_route():
    """Send custom Telegram alert"""
    if request.method == 'POST':
        try:
            message = request.form.get('message')
            if not message:
                flash('Message is required', 'danger')
                return redirect(url_for('dashboard.index'))
            
            # Send alert
            send_alert(message)
            
            flash('Alert sent successfully', 'success')
            return redirect(url_for('dashboard.index'))
            
        except Exception as e:
            flash(f'Error sending alert: {str(e)}', 'danger')
            return redirect(url_for('dashboard.index'))

@strategies_bp.route('/execute_full_cycle', methods=['POST'])
@login_required
def execute_full_cycle():
    """Execute full trading cycle across all chains"""
    try:
        # Get chains to execute on
        chains = request.form.getlist('chains')
        if not chains:
            chains = ChainInfo.query.filter_by(status='active').all()
            chains = [chain.name for chain in chains]
        
        # Execute strategies on each chain
        results = []
        for chain in chains:
            # Get private key
            private_key = current_app.config.get(f'{chain.upper()}_PRIVATE_KEY')
            if not private_key:
                results.append({
                    'chain': chain,
                    'success': False,
                    'error': 'Private key not found'
                })
                continue
            
            # Execute flash loan if contract is deployed
            contract_address = current_app.config.get(f'{chain.upper()}_FLASH_LOAN_CONTRACT')
            if contract_address:
                try:
                    flash_loan_service = FlashLoanService(chain, private_key, contract_address)
                    flash_result = flash_loan_service.execute_flash_loan('DAI', 1000000, 'uniswap', 'sushiswap')
                    results.append({
                        'chain': chain,
                        'strategy': 'flash_loan',
                        'success': flash_result['success'],
                        'profit': flash_result.get('net_profit', 0)
                    })
                except Exception as e:
                    results.append({
                        'chain': chain,
                        'strategy': 'flash_loan',
                        'success': False,
                        'error': str(e)
                    })
            
            # Execute multi-hop arbitrage
            try:
                multi_hop_service = MultiHopService(chain, private_key)
                multi_hop_result = multi_hop_service.execute_multi_hop_arbitrage(10000, 3, 0.005)
                results.append({
                    'chain': chain,
                    'strategy': 'multi_hop',
                    'success': multi_hop_result['success'],
                    'profit': multi_hop_result.get('net_profit', 0)
                })
            except Exception as e:
                results.append({
                    'chain': chain,
                    'strategy': 'multi_hop',
                    'success': False,
                    'error': str(e)
                })
        
        # Send summary alert
        successful = sum(1 for r in results if r['success'])
        total_profit = sum(r.get('profit', 0) for r in results if r['success'])
        
        send_alert(f"✅ Full cycle executed on {len(chains)} chains. {successful} successful strategies. Total profit: ${total_profit:.2f}")
        
        return jsonify({
            'success': True,
            'results': results,
            'total_profit': total_profit
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })