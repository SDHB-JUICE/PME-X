"""
Dashboard Routes
Flask Blueprint for dashboard-related routes
"""
import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, current_app
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
    return render_template('dashboard/chains.html', 
                           title='Chains',
                           chains=chains)

@dashboard_bp.route('/wallets')
@login_required
def wallets():
    """View and manage wallets"""
    wallets = Wallet.query.all()
    return render_template('dashboard/wallets.html', 
                           title='Wallets',
                           wallets=wallets)

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
        chart_data.append({
            'date': entry.date.strftime('%Y-%m-%d'),
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