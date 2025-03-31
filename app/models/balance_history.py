"""
Balance History Models
"""
from datetime import datetime
from app import db
JSON_Type = db.JSON().with_variant(db.String, "sqlite")
class WalletBalanceHistory(db.Model):
    """Model for tracking wallet balance history"""
    id = db.Column(db.Integer, primary_key=True)
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallet.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    native_balance = db.Column(db.Float, default=0.0)
    usd_balance = db.Column(db.Float, default=0.0)
    token_balances = db.Column(JSON_Type, default={})  # Map of token_id -> balance
    token_usd_values = db.Column(JSON_Type, default={})  # Map of token_id -> usd_value
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Create relationship with Wallet
    wallet = db.relationship('Wallet', backref=db.backref('balance_history', lazy=True, cascade="all, delete-orphan"))
    
    def __repr__(self):
        return f"<WalletBalanceHistory wallet_id={self.wallet_id} date={self.date} usd=${self.usd_balance:.2f}>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'wallet_id': self.wallet_id,
            'date': self.date.isoformat(),
            'native_balance': self.native_balance,
            'usd_balance': self.usd_balance,
            'token_balances': self.token_balances,
            'token_usd_values': self.token_usd_values,
            'last_updated': self.last_updated.isoformat(),
            'estimated': False  # Base entry is never estimated
        }


class StrategyBalanceHistory(db.Model):
    """Model for tracking strategy balance history"""
    id = db.Column(db.Integer, primary_key=True)
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallet.id'), nullable=False)
    strategy_id = db.Column(db.Integer, db.ForeignKey('strategy.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    initial_value = db.Column(db.Float, default=0.0)  # Initial allocation value
    current_value = db.Column(db.Float, default=0.0)  # Current value with profit/loss
    profit_loss = db.Column(db.Float, default=0.0)
    profit_loss_percentage = db.Column(db.Float, default=0.0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Create relationships
    wallet = db.relationship('Wallet', backref=db.backref('strategy_history', lazy=True))
    strategy = db.relationship('Strategy', backref=db.backref('balance_history', lazy=True))
    
    def __repr__(self):
        return f"<StrategyBalanceHistory wallet_id={self.wallet_id} strategy_id={self.strategy_id} date={self.date} value=${self.current_value:.2f}>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'wallet_id': self.wallet_id,
            'strategy_id': self.strategy_id,
            'date': self.date.isoformat(),
            'initial_value': self.initial_value,
            'current_value': self.current_value,
            'profit_loss': self.profit_loss,
            'profit_loss_percentage': self.profit_loss_percentage,
            'last_updated': self.last_updated.isoformat()
        }


class WalletAllocationHistory(db.Model):
    """Model for tracking wallet asset allocation history"""
    id = db.Column(db.Integer, primary_key=True)
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallet.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    native_percentage = db.Column(db.Float, default=0.0)
    token_percentages = db.Column(JSON_Type, default={})  # Map of token_id -> percentage
    total_value = db.Column(db.Float, default=0.0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Create relationship with Wallet
    wallet = db.relationship('Wallet', backref=db.backref('allocation_history', lazy=True, cascade="all, delete-orphan"))
    
    def __repr__(self):
        return f"<WalletAllocationHistory wallet_id={self.wallet_id} date={self.date} total_value=${self.total_value:.2f}>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'wallet_id': self.wallet_id,
            'date': self.date.isoformat(),
            'native_percentage': self.native_percentage,
            'token_percentages': self.token_percentages,
            'total_value': self.total_value,
            'last_updated': self.last_updated.isoformat()
        }