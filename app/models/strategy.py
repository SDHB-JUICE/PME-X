"""
Strategy Models
"""

from datetime import datetime
import json
from app import db

# Use SQLite-compatible JSON type
JSON_Type = db.JSON().with_variant(db.String, "sqlite")

class Strategy(db.Model):
    """Model for trading strategies"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # flash_loan, multi_hop, cross_chain, yield_farming
    description = db.Column(db.Text, nullable=True)
    risk_level = db.Column(db.String(20), default='medium')  # low, medium, high
    status = db.Column(db.String(20), default='active')  # active, paused, deprecated
    config = db.Column(JSON_Type, default={})
    strategy_metadata = db.Column(JSON_Type, default={})  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Strategy {self.name} type={self.type} risk={self.risk_level}>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'description': self.description,
            'risk_level': self.risk_level,
            'status': self.status,
            'config': self.config,
            'metadata': self.strategy_metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class WalletStrategy(db.Model):
    """Model for linking wallets to strategies"""
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallet.id'), primary_key=True)
    strategy_id = db.Column(db.Integer, db.ForeignKey('strategy.id'), primary_key=True)
    allocation = db.Column(db.Float, default=0.0)  # Percentage of wallet allocated to this strategy
    allocation_value = db.Column(db.Float, default=0.0)  # USD value of allocation
    performance = db.Column(db.Float, default=0.0)  # Performance in percentage
    status = db.Column(db.String(20), default='active')  # active, paused
    last_run = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Create relationships
    wallet = db.relationship('Wallet', backref=db.backref('strategies', lazy=True, cascade="all, delete-orphan"))
    strategy = db.relationship('Strategy', backref=db.backref('wallets', lazy=True, cascade="all, delete-orphan"))
    
    def __repr__(self):
        return f"<WalletStrategy wallet={self.wallet_id} strategy={self.strategy_id} allocation={self.allocation}%>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'wallet_id': self.wallet_id,
            'strategy_id': self.strategy_id,
            'allocation': self.allocation,
            'allocation_value': self.allocation_value,
            'performance': self.performance,
            'status': self.status,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class StrategyTransaction(db.Model):
    """Model for tracking strategy transactions"""
    id = db.Column(db.Integer, primary_key=True)
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallet.id'), nullable=False)
    strategy_id = db.Column(db.Integer, db.ForeignKey('strategy.id'), nullable=False)
    tx_hash = db.Column(db.String(100), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    tx_type = db.Column(db.String(50), nullable=False)  # deposit, withdraw, harvest, trade
    amount = db.Column(db.Float, default=0.0)
    token_address = db.Column(db.String(100), nullable=True)
    token_symbol = db.Column(db.String(20), nullable=True)
    usd_value = db.Column(db.Float, default=0.0)
    gas_cost = db.Column(db.Float, default=0.0)  # Gas cost in ETH
    gas_cost_usd = db.Column(db.Float, default=0.0)  # Gas cost in USD
    profit_loss = db.Column(db.Float, default=0.0)  # Profit/loss in USD
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    error = db.Column(db.Text, nullable=True)
    transaction_metadata = db.Column(JSON_Type, default={})  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    
    # Create relationships
    wallet = db.relationship('Wallet', backref=db.backref('strategy_transactions', lazy=True))
    strategy = db.relationship('Strategy', backref=db.backref('transactions', lazy=True))
    
    def __repr__(self):
        return f"<StrategyTransaction strategy={self.strategy_id} type={self.tx_type} value=${self.usd_value:.2f}>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'wallet_id': self.wallet_id,
            'strategy_id': self.strategy_id,
            'tx_hash': self.tx_hash,
            'timestamp': self.timestamp.isoformat(),
            'tx_type': self.tx_type,
            'amount': self.amount,
            'token_address': self.token_address,
            'token_symbol': self.token_symbol,
            'usd_value': self.usd_value,
            'gas_cost': self.gas_cost,
            'gas_cost_usd': self.gas_cost_usd,
            'profit_loss': self.profit_loss,
            'status': self.status,
            'error': self.error,
            'metadata': self.transaction_metadata
        }


class StrategyAsset(db.Model):
    """Model for tracking strategy assets"""
    id = db.Column(db.Integer, primary_key=True)
    strategy_id = db.Column(db.Integer, db.ForeignKey('strategy.id'), nullable=False)
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallet.id'), nullable=False)
    token_address = db.Column(db.String(100), nullable=True)  # Null for native currency
    token_symbol = db.Column(db.String(20), nullable=False)
    token_name = db.Column(db.String(100), nullable=True)
    balance = db.Column(db.Float, default=0.0)
    usd_value = db.Column(db.Float, default=0.0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Create relationships
    strategy = db.relationship('Strategy', backref=db.backref('assets', lazy=True))
    wallet = db.relationship('Wallet', backref=db.backref('strategy_assets', lazy=True))
    
    def __repr__(self):
        return f"<StrategyAsset strategy={self.strategy_id} token={self.token_symbol} balance={self.balance}>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'strategy_id': self.strategy_id,
            'wallet_id': self.wallet_id,
            'token_address': self.token_address,
            'token_symbol': self.token_symbol,
            'token_name': self.token_name,
            'balance': self.balance,
            'usd_value': self.usd_value,
            'last_updated': self.last_updated.isoformat()
        }


class StrategyPerformance(db.Model):
    """Model for tracking strategy performance"""
    id = db.Column(db.Integer, primary_key=True)
    strategy_id = db.Column(db.Integer, db.ForeignKey('strategy.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    period = db.Column(db.String(20), nullable=False)  # 1h, 1d, 7d, 30d, all
    roi = db.Column(db.Float, default=0.0)  # Return on investment (percentage)
    profit_loss = db.Column(db.Float, default=0.0)  # Profit/loss in USD
    volume = db.Column(db.Float, default=0.0)  # Total volume in USD
    gas_costs = db.Column(db.Float, default=0.0)  # Total gas costs in USD
    tx_count = db.Column(db.Integer, default=0)  # Number of transactions
    success_rate = db.Column(db.Float, default=0.0)  # Percentage of successful transactions
    
    # Create relationships
    strategy = db.relationship('Strategy', backref=db.backref('performance', lazy=True))
    
    def __repr__(self):
        return f"<StrategyPerformance strategy={self.strategy_id} period={self.period} roi={self.roi}%>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'strategy_id': self.strategy_id,
            'timestamp': self.timestamp.isoformat(),
            'period': self.period,
            'roi': self.roi,
            'profit_loss': self.profit_loss,
            'volume': self.volume,
            'gas_costs': self.gas_costs,
            'tx_count': self.tx_count,
            'success_rate': self.success_rate
        }