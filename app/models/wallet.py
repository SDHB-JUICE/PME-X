"""
Wallet and Chain Models
"""
from datetime import datetime
from app import db

class Wallet(db.Model):
    """Model for tracking wallet addresses and balances"""
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(100), nullable=False, index=True)
    chain = db.Column(db.String(50), nullable=False)
    private_key_encrypted = db.Column(db.String(256), nullable=True)
    
    # Balance tracking
    native_balance = db.Column(db.Float, default=0.0)  # Balance in chain's native token (ETH, BNB, etc.)
    usd_balance = db.Column(db.Float, default=0.0)  # Estimated USD value
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Status flags
    is_active = db.Column(db.Boolean, default=True)
    is_contract = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f"<Wallet {self.address[:8]}...{self.address[-6:]} on {self.chain}>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'address': self.address,
            'chain': self.chain,
            'native_balance': self.native_balance,
            'usd_balance': self.usd_balance,
            'last_updated': self.last_updated.isoformat(),
            'is_active': self.is_active,
            'is_contract': self.is_contract
        }


class Token(db.Model):
    """Model for tracking ERC20 token balances"""
    id = db.Column(db.Integer, primary_key=True)
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallet.id'), nullable=False)
    chain = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(100), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=True)
    balance = db.Column(db.Float, default=0.0)
    usd_value = db.Column(db.Float, default=0.0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Create relationship with Wallet
    wallet = db.relationship('Wallet', backref=db.backref('tokens', lazy=True))
    
    def __repr__(self):
        return f"<Token {self.symbol} {self.balance} (${self.usd_value:.2f})>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'wallet_id': self.wallet_id,
            'chain': self.chain,
            'address': self.address,
            'symbol': self.symbol,
            'name': self.name,
            'balance': self.balance,
            'usd_value': self.usd_value,
            'last_updated': self.last_updated.isoformat()
        }


class ChainInfo(db.Model):
    """Model for storing EVM chain information"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    chain_id = db.Column(db.Integer, nullable=False, unique=True)
    rpc_url = db.Column(db.String(256), nullable=False)
    explorer_url = db.Column(db.String(256), nullable=True)
    currency_symbol = db.Column(db.String(10), nullable=False)
    
    # Gas and performance metrics
    avg_gas_price = db.Column(db.Float, nullable=True)  # in GWEI
    avg_confirmation_time = db.Column(db.Float, nullable=True)  # in seconds
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="active")  # active, inactive, congested
    
    # Tatum specific info
    tatum_network = db.Column(db.String(50), nullable=True)
    tatum_tier = db.Column(db.Integer, nullable=True)
    
    def __repr__(self):
        return f"<ChainInfo {self.name} (ID: {self.chain_id})>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'chain_id': self.chain_id,
            'rpc_url': self.rpc_url,
            'explorer_url': self.explorer_url,
            'currency_symbol': self.currency_symbol,
            'avg_gas_price': self.avg_gas_price,
            'avg_confirmation_time': self.avg_confirmation_time,
            'last_updated': self.last_updated.isoformat(),
            'status': self.status,
            'tatum_network': self.tatum_network,
            'tatum_tier': self.tatum_tier
        }