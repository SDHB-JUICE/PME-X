"""
Enhanced Token Models
"""
from datetime import datetime
from app import db
import json

# Use SQLite-compatible JSON type
JSON_Type = db.JSON().with_variant(db.String, "sqlite")

class EnhancedToken(db.Model):
    __tablename__ = 'enhanced_token'
    """Enhanced model for tracking ERC20 token balances with price history and metadata"""
    id = db.Column(db.Integer, primary_key=True)
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallet.id'), nullable=False)
    chain = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(100), nullable=False, index=True)
    symbol = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=True)
    decimals = db.Column(db.Integer, default=18)
    balance = db.Column(db.Float, default=0.0)
    usd_value = db.Column(db.Float, default=0.0)
    
    # Token metadata
    logo_url = db.Column(db.String(256), nullable=True)
    contract_type = db.Column(db.String(20), default="ERC20")  # ERC20, ERC721, ERC1155
    is_verified = db.Column(db.Boolean, default=False)
    token_list_source = db.Column(db.String(50), nullable=True)  # coingecko, 1inch, manual, etc.
    
    # Price tracking
    current_price = db.Column(db.Float, default=0.0)
    price_24h_change = db.Column(db.Float, default=0.0)
    all_time_high = db.Column(db.Float, default=0.0)
    all_time_high_date = db.Column(db.DateTime, nullable=True)
    
    # Custom metadata - Use SQLite-compatible JSON type
    token_metadata = db.Column(JSON_Type, default={})
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Create relationship with Wallet
    wallet = db.relationship('Wallet', backref=db.backref('enhanced_tokens', lazy=True, cascade="all, delete-orphan"))
    
    def __repr__(self):
        return f"<EnhancedToken {self.symbol} {self.balance} (${self.usd_value:.2f})>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'wallet_id': self.wallet_id,
            'chain': self.chain,
            'address': self.address,
            'symbol': self.symbol,
            'name': self.name,
            'decimals': self.decimals,
            'balance': self.balance,
            'usd_value': self.usd_value,
            'logo_url': self.logo_url,
            'contract_type': self.contract_type,
            'is_verified': self.is_verified,
            'token_list_source': self.token_list_source,
            'current_price': self.current_price,
            'price_24h_change': self.price_24h_change,
            'all_time_high': self.all_time_high,
            'all_time_high_date': self.all_time_high_date.isoformat() if self.all_time_high_date else None,
            'token_metadata': self.token_metadata,
            'last_updated': self.last_updated.isoformat()
        }


class TokenPriceHistory(db.Model):
    """Model for tracking token price history"""
    id = db.Column(db.Integer, primary_key=True)
    token_id = db.Column(db.Integer, db.ForeignKey('enhanced_token.id', ondelete='CASCADE'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    price = db.Column(db.Float, nullable=False)
    volume_24h = db.Column(db.Float, nullable=True)
    market_cap = db.Column(db.Float, nullable=True)
    
    # Create relationship with EnhancedToken
    token = db.relationship('EnhancedToken', backref=db.backref('price_history', lazy=True, cascade="all, delete-orphan"))
    
    def __repr__(self):
        return f"<TokenPrice {self.token.symbol if self.token else 'Unknown'} ${self.price} at {self.timestamp}>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'token_id': self.token_id,
            'timestamp': self.timestamp.isoformat(),
            'price': self.price,
            'volume_24h': self.volume_24h,
            'market_cap': self.market_cap
        }


class TokenList(db.Model):
    """Model for managing token lists"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    source = db.Column(db.String(50), nullable=False)  # coingecko, 1inch, custom, etc.
    chain = db.Column(db.String(50), nullable=False)
    tokens_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    list_metadata = db.Column(JSON_Type, default={})
    
    def __repr__(self):
        return f"<TokenList {self.name} ({self.source}) on {self.chain}>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'source': self.source,
            'chain': self.chain,
            'tokens_count': self.tokens_count,
            'is_active': self.is_active,
            'last_updated': self.last_updated.isoformat(),
            'list_metadata': self.list_metadata
        }


class TokenTransaction(db.Model):
    """Model for tracking token transactions"""
    id = db.Column(db.Integer, primary_key=True)
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallet.id'), nullable=False)
    token_id = db.Column(db.Integer, db.ForeignKey('enhanced_token.id', ondelete='SET NULL'), nullable=True)
    chain = db.Column(db.String(50), nullable=False)
    tx_hash = db.Column(db.String(100), nullable=False, unique=True, index=True)
    block_number = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    from_address = db.Column(db.String(100), nullable=False)
    to_address = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    usd_value = db.Column(db.Float, nullable=True)
    gas_used = db.Column(db.Integer, nullable=True)
    gas_price = db.Column(db.BigInteger, nullable=True)  # In wei
    gas_cost_eth = db.Column(db.Float, nullable=True)
    gas_cost_usd = db.Column(db.Float, nullable=True)
    
    # Transaction type and status
    tx_type = db.Column(db.String(20), nullable=True)  # transfer, approval, etc.
    status = db.Column(db.String(20), default="confirmed")  # confirmed, pending, failed
    error_message = db.Column(db.String(256), nullable=True)
    
    # Metadata - Use SQLite-compatible JSON type
    transaction_metadata = db.Column(JSON_Type, default={})
    
    # Relationships
    wallet = db.relationship('Wallet', backref=db.backref('token_transactions', lazy=True))
    token = db.relationship('EnhancedToken', backref=db.backref('transactions', lazy=True))
    
    def __repr__(self):
        return f"<TokenTransaction {self.tx_hash[:8]}...{self.tx_hash[-6:]} on {self.chain}>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'wallet_id': self.wallet_id,
            'token_id': self.token_id,
            'chain': self.chain,
            'tx_hash': self.tx_hash,
            'block_number': self.block_number,
            'timestamp': self.timestamp.isoformat(),
            'from_address': self.from_address,
            'to_address': self.to_address,
            'amount': self.amount,
            'usd_value': self.usd_value,
            'gas_used': self.gas_used,
            'gas_price': self.gas_price,
            'gas_cost_eth': self.gas_cost_eth,
            'gas_cost_usd': self.gas_cost_usd,
            'tx_type': self.tx_type,
            'status': self.status,
            'error_message': self.error_message,
            'transaction_metadata': self.transaction_metadata
        }