"""
Dashboard Routes
Flask Blueprint for dashboard-related routes with chain management functionality
"""
import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for
from flask_login import login_required
from sqlalchemy import func
from app import db
from app.models.trade import Trade, YieldFarm, DeployedToken
from app.models.wallet import ChainInfo, Wallet, Token

# Create blueprint
dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    """Dashboard home page"""
    # Get summary stats
    total_trades = Trade.query.count()
    total_profit = db.session.query(func.sum(Trade.net_profit)).scalar() or 0
    
    # Get recent trades
    recent_trades = Trade.query.order_by(Trade.created_at.desc()).limit(10).all()
    
    # Get active yield farms
    active_farms = YieldFarm.query.filter_by(status='active').all()
    
    # Get chain stats
    chains = ChainInfo.query.all()
    chain_stats = []
    for chain in chains:
        # Get trades for this chain
        chain_trades = Trade.query.filter_by(chain=chain.name).all()
        
        # Calculate stats
        total_chain_profit = sum(trade.net_profit for trade in chain_trades)
        trade_count = len(chain_trades)
        
        chain_stats.append({
            'name': chain.name,
            'profit': total_chain_profit,
            'trade_count': trade_count,
            'status': chain.status
        })
    
    # Calculate strategy performance
    strategies = Trade.query.with_entities(
        Trade.strategy_type,
        func.count(Trade.id).label('count'),
        func.sum(Trade.net_profit).label('profit')
    ).group_by(Trade.strategy_type).all()
    
    strategy_stats = []
    for strategy in strategies:
        strategy_stats.append({
            'name': strategy.strategy_type,
            'count': strategy.count,
            'profit': strategy.profit or 0
        })
    
    # Get time-based profit data for chart
    now = datetime.utcnow()
    one_month_ago = now - timedelta(days=30)
    
    daily_profits = db.session.query(
        func.date(Trade.created_at).label('date'),
        func.sum(Trade.net_profit).label('profit')
    ).filter(Trade.created_at >= one_month_ago).group_by(func.date(Trade.created_at)).all()
    
    chart_data = []
    for entry in daily_profits:
        chart_data.append({
            'date': entry.date.strftime('%Y-%m-%d'),
            'profit': float(entry.profit) if entry.profit else 0
        })
    
    return render_template('dashboard/index.html',
                           title='Dashboard',
                           total_trades=total_trades,
                           total_profit=total_profit,
                           recent_trades=recent_trades,
                           active_farms=active_farms,
                           chain_stats=chain_stats,
                           strategy_stats=strategy_stats,
                           chart_data=json.dumps(chart_data))

@dashboard_bp.route('/chains')
@login_required
def chains():
    """View and manage chains"""
    chains = ChainInfo.query.all()
    
    # Calculate chain-specific statistics for the table
    chain_info = {}
    for chain in chains:
        # Get trades for this chain
        chain_trades = Trade.query.filter_by(chain=chain.name).all()
        
        # Calculate average execution time and profit
        if chain_trades:
            avg_execution_time = sum(trade.execution_time or 0 for trade in chain_trades) / len(chain_trades)
            avg_profit = sum(trade.net_profit for trade in chain_trades) / len(chain_trades)
            trade_count = len(chain_trades)
        else:
            avg_execution_time = 0
            avg_profit = 0
            trade_count = 0
        
        chain_info[chain.name] = {
            'trade_count': trade_count,
            'avg_profit': avg_profit,
            'avg_execution_time': avg_execution_time
        }
    
    return render_template('dashboard/chains.html', 
                           title='Chains',
                           chains=chains,
                           chain_stats=chain_info)

@dashboard_bp.route('/chains/update', methods=['POST'])
@login_required
def update_chain():
    """Update chain information"""
    if request.method == 'POST':
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
            if not chain_id or not name or not chain_id_value or not rpc_url or not currency_symbol:
                flash('All required fields must be provided', 'danger')
                return redirect(url_for('dashboard.chains'))
            
            # Get chain from database
            chain = ChainInfo.query.get(chain_id)
            if not chain:
                flash(f'Chain with ID {chain_id} not found', 'danger')
                return redirect(url_for('dashboard.chains'))
            
            # Update chain information
            chain.name = name
            chain.chain_id = chain_id_value
            chain.rpc_url = rpc_url
            chain.explorer_url = explorer_url
            chain.currency_symbol = currency_symbol
            chain.tatum_network = tatum_network
            chain.tatum_tier = tatum_tier
            chain.status = status
            chain.last_updated = datetime.utcnow()
            
            # Save to database
            db.session.commit()
            
            flash(f'Chain {name} updated successfully', 'success')
            return redirect(url_for('dashboard.chains'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating chain: {str(e)}', 'danger')
            return redirect(url_for('dashboard.chains'))

@dashboard_bp.route('/chains/add', methods=['POST'])
@login_required
def add_chain():
    """Add a new chain"""
    if request.method == 'POST':
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
                flash('All required fields must be provided', 'danger')
                return redirect(url_for('dashboard.chains'))
            
            # Check if chain already exists
            existing_chain = ChainInfo.query.filter_by(name=name).first()
            if existing_chain:
                flash(f'Chain with name {name} already exists', 'danger')
                return redirect(url_for('dashboard.chains'))
            
            # Create new chain
            new_chain = ChainInfo(
                name=name,
                chain_id=chain_id_value,
                rpc_url=rpc_url,
                explorer_url=explorer_url,
                currency_symbol=currency_symbol,
                tatum_network=tatum_network,
                tatum_tier=tatum_tier,
                status=status,
                avg_gas_price=50.0,  # Default value
                avg_confirmation_time=10.0,  # Default value
                last_updated=datetime.utcnow()
            )
            
            # Save to database
            db.session.add(new_chain)
            db.session.commit()
            
            flash(f'Chain {name} added successfully', 'success')
            return redirect(url_for('dashboard.chains'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding chain: {str(e)}', 'danger')
            return redirect(url_for('dashboard.chains'))

@dashboard_bp.route('/chains/update_status', methods=['POST'])
@login_required
def update_chain_status():
    """Update chain status"""
    if request.method == 'POST':
        try:
            chain_id = request.form.get('chain_id')
            status = request.form.get('status')
            reason = request.form.get('reason', '')
            
            # Validate required fields
            if not chain_id or not status:
                flash('Chain ID and status are required', 'danger')
                return redirect(url_for('dashboard.chains'))
            
            # Get chain from database
            chain = ChainInfo.query.get(chain_id)
            if not chain:
                flash(f'Chain with ID {chain_id} not found', 'danger')
                return redirect(url_for('dashboard.chains'))
            
            # Update chain status
            chain.status = status
            chain.last_updated = datetime.utcnow()
            
            # Save to database
            db.session.commit()
            
            flash(f'Chain {chain.name} status updated to {status}', 'success')
            return redirect(url_for('dashboard.chains'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating chain status: {str(e)}', 'danger')
            return redirect(url_for('dashboard.chains'))

@dashboard_bp.route('/chains/refresh_gas', methods=['POST'])
@login_required
def refresh_gas_prices():
    """Refresh gas prices for chains"""
    if request.method == 'POST':
        try:
            selected_chains = request.form.getlist('chains')
            
            # If 'all' is selected, refresh all chains
            if 'all' in selected_chains:
                chains = ChainInfo.query.all()
            else:
                chains = ChainInfo.query.filter(ChainInfo.name.in_(selected_chains)).all()
            
            # Update gas prices for selected chains
            for chain in chains:
                # In a real implementation, this would call an API to get current gas prices
                # For the demo, we'll use random values
                import random
                chain.avg_gas_price = random.uniform(10.0, 100.0)
                chain.avg_confirmation_time = random.uniform(1.0, 30.0)
                chain.last_updated = datetime.utcnow()
                
                # Update status based on gas price
                if chain.avg_gas_price > 80.0:
                    chain.status = 'congested'
                elif chain.avg_gas_price < 20.0:
                    chain.status = 'active'
            
            # Save to database
            db.session.commit()
            
            flash(f'Gas prices refreshed for {len(chains)} chains', 'success')
            return redirect(url_for('dashboard.chains'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error refreshing gas prices: {str(e)}', 'danger')
            return redirect(url_for('dashboard.chains'))

@dashboard_bp.route('/wallets')
@login_required
def wallets():
    """View and manage wallets"""
    wallets = Wallet.query.all()
    chains = ChainInfo.query.all()
    
    # Create mapping of chain info for template
    chain_info = {}
    for chain in chains:
        chain_info[chain.name] = chain.to_dict()
    
    return render_template('dashboard/wallets.html', 
                           title='Wallets',
                           wallets=wallets,
                           chains=chains,
                           chain_info=chain_info)

@dashboard_bp.route('/trade_logs')
@login_required
def trade_logs():
    """View trade logs"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    strategy = request.args.get('strategy', None)
    chain = request.args.get('chain', None)
    
    # Base query
    query = Trade.query
    
    # Apply filters
    if strategy:
        query = query.filter(Trade.strategy_type == strategy)
    if chain:
        query = query.filter(Trade.chain == chain)
    
    # Paginate results
    trades = query.order_by(Trade.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('dashboard/trade_logs.html',
                           title='Trade Logs',
                           trades=trades,
                           chains=ChainInfo.query.all(),
                           strategy_types=['flash_loan', 'multi_hop', 'cross_chain', 'yield_farming'])

@dashboard_bp.route('/yield_farms')
@login_required
def yield_farms():
    """View yield farms"""
    farms = YieldFarm.query.all()
    return render_template('dashboard/yield_farms.html',
                           title='Yield Farms',
                           farms=farms)

@dashboard_bp.route('/tokens')
@login_required
def tokens():
    """View deployed tokens"""
    tokens = DeployedToken.query.all()
    return render_template('dashboard/tokens.html',
                           title='Deployed Tokens',
                           tokens=tokens)

@dashboard_bp.route('/settings')
@login_required
def settings():
    """Application settings"""
    return render_template('dashboard/settings.html',
                           title='Settings')

@dashboard_bp.route('/api/stats')
@login_required
def api_stats():
    """API endpoint for dashboard stats"""
    # Get summary stats
    total_trades = Trade.query.count()
    total_profit = db.session.query(func.sum(Trade.net_profit)).scalar() or 0
    
    # Get recent trades
    recent_trades = Trade.query.order_by(Trade.created_at.desc()).limit(10).all()
    recent_trades_data = [trade.to_dict() for trade in recent_trades]
    
    # Get chain stats
    chains = ChainInfo.query.all()
    chain_stats = []
    for chain in chains:
        # Get trades for this chain
        chain_trades = Trade.query.filter_by(chain=chain.name).all()
        
        # Calculate stats
        total_chain_profit = sum(trade.net_profit for trade in chain_trades)
        trade_count = len(chain_trades)
        
        chain_stats.append({
            'name': chain.name,
            'profit': total_chain_profit,
            'trade_count': trade_count,
            'status': chain.status
        })
    
    # Calculate strategy performance
    strategies = Trade.query.with_entities(
        Trade.strategy_type,
        func.count(Trade.id).label('count'),
        func.sum(Trade.net_profit).label('profit')
    ).group_by(Trade.strategy_type).all()
    
    strategy_stats = []
    for strategy in strategies:
        strategy_stats.append({
            'name': strategy.strategy_type,
            'count': strategy.count,
            'profit': float(strategy.profit) if strategy.profit else 0
        })
    
    # Get time-based profit data for chart
    now = datetime.utcnow()
    one_month_ago = now - timedelta(days=30)
    
    daily_profits = db.session.query(
        func.date(Trade.created_at).label('date'),
        func.sum(Trade.net_profit).label('profit')
    ).filter(Trade.created_at >= one_month_ago).group_by(func.date(Trade.created_at)).all()
    
    chart_data = []
    for entry in daily_profits:
        # Check if date is a string or datetime and handle accordingly
        date_str = entry.date
        if hasattr(entry.date, 'strftime'):
            date_str = entry.date.strftime('%Y-%m-%d')
            
        chart_data.append({
            'date': date_str,
            'profit': float(entry.profit) if entry.profit else 0
        })
    
    return jsonify({
        'total_trades': total_trades,
        'total_profit': total_profit,
        'recent_trades': recent_trades_data,
        'chain_stats': chain_stats,
        'strategy_stats': strategy_stats,
        'chart_data': chart_data
    })

@dashboard_bp.route('/api/chain/<int:chain_id>')
@login_required
def get_chain(chain_id):
    """API endpoint to get chain details"""
    chain = ChainInfo.query.get(chain_id)
    if not chain:
        return jsonify({"error": "Chain not found"}), 404
    
    return jsonify(chain.to_dict())

@dashboard_bp.route('/api/chain_gas_history/<int:chain_id>')
@login_required
def get_chain_gas_history(chain_id):
    """API endpoint to get chain gas price history"""
    chain = ChainInfo.query.get(chain_id)
    if not chain:
        return jsonify({"error": "Chain not found"}), 404
    
    # In a real implementation, this would query a time-series database
    # For the demo, we'll generate mock data
    
    # Generate mock gas price history
    now = datetime.utcnow()
    gas_history = []
    
    import random
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