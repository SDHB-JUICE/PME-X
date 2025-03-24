"""
Trade and Strategy Models
"""
from datetime import datetime
from app import db

class Trade(db.Model):
    """Model for tracking trade executions and profits"""
    id = db.Column(db.Integer, primary_key=True)
    strategy_type = db.Column(db.String(50), nullable=False)  # flash_loan, multi_hop, cross_chain, etc.
    chain = db.Column(db.String(50), nullable=False)  # ethereum, bsc, polygon, etc.
    amount = db.Column(db.Float, nullable=False)  # Amount in USD
    profit = db.Column(db.Float, nullable=False)  # Profit in USD
    gas_cost = db.Column(db.Float, nullable=False)  # Gas cost in USD
    net_profit = db.Column(db.Float, nullable=False)  # Net profit after gas
    tx_hash = db.Column(db.String(100), nullable=True)  # Transaction hash
    status = db.Column(db.String(20), nullable=False, default="completed")  # pending, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    execution_time = db.Column(db.Float, nullable=True)  # Execution time in seconds
    
    # Additional details stored as JSON
    details = db.Column(db.JSON, nullable=True)
    
    def __repr__(self):
        return f"<Trade {self.id} {self.strategy_type} on {self.chain} profit:{self.net_profit}>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'strategy_type': self.strategy_type,
            'chain': self.chain,
            'amount': self.amount,
            'profit': self.profit,
            'gas_cost': self.gas_cost,
            'net_profit': self.net_profit,
            'tx_hash': self.tx_hash,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'execution_time': self.execution_time,
            'details': self.details
        }


class YieldFarm(db.Model):
    """Model for tracking active yield farming positions"""
    id = db.Column(db.Integer, primary_key=True)
    chain = db.Column(db.String(50), nullable=False)
    protocol = db.Column(db.String(50), nullable=False)  # Yearn, Beefy, Curve, etc.
    pool_name = db.Column(db.String(100), nullable=False)
    deposit_amount = db.Column(db.Float, nullable=False)  # Amount in USD
    current_value = db.Column(db.Float, nullable=False)  # Current value in USD
    apy = db.Column(db.Float, nullable=False)  # Current APY
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_harvest = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default="active")  # active, closed
    
    # Transaction hashes
    deposit_tx = db.Column(db.String(100), nullable=True)
    last_harvest_tx = db.Column(db.String(100), nullable=True)
    withdraw_tx = db.Column(db.String(100), nullable=True)
    
    def __repr__(self):
        return f"<YieldFarm {self.id} {self.protocol} on {self.chain} apy:{self.apy}>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'chain': self.chain,
            'protocol': self.protocol,
            'pool_name': self.pool_name,
            'deposit_amount': self.deposit_amount,
            'current_value': self.current_value,
            'apy': self.apy,
            'start_date': self.start_date.isoformat(),
            'last_harvest': self.last_harvest.isoformat() if self.last_harvest else None,
            'status': self.status,
            'deposit_tx': self.deposit_tx,
            'last_harvest_tx': self.last_harvest_tx,
            'withdraw_tx': self.withdraw_tx
        }


class DeployedToken(db.Model):
    """Model for tracking deployed ERC20 tokens"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    chain = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    total_supply = db.Column(db.Float, nullable=False)
    current_price = db.Column(db.Float, nullable=True)
    
    # DEX listings
    listed_on = db.Column(db.JSON, nullable=True)  # List of DEXes where token is listed
    deploy_tx = db.Column(db.String(100), nullable=True)
    
    def __repr__(self):
        return f"<DeployedToken {self.symbol} on {self.chain}>"