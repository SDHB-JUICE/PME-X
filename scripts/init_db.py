#!/usr/bin/env python3
"""
Database Initialization Script
Populates the database with initial data
"""
import os
import sys
import json
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.user import User, Settings
from app.models.wallet import Wallet, Token, ChainInfo
from app.models.trade import Trade, YieldFarm, DeployedToken

# Import enhanced models
# Note: Make sure these imports correspond to your file structure
from app.models.enhanced_token import EnhancedToken, TokenPriceHistory, TokenList, TokenTransaction
from app.models.balance_history import WalletBalanceHistory, StrategyBalanceHistory, WalletAllocationHistory
from app.models.strategy import Strategy, WalletStrategy, StrategyTransaction, StrategyAsset, StrategyPerformance

from werkzeug.security import generate_password_hash

# EVM Chain data
EVM_CHAINS = [
    {
        "name": "ethereum",
        "chain_id": 1,
        "rpc_url": "https://ethereum.tatum.io/",
        "explorer_url": "https://etherscan.io",
        "currency_symbol": "ETH",
        "avg_gas_price": 40.0,
        "avg_confirmation_time": 15.0,
        "status": "active",
        "tatum_network": "ethereum-mainnet",
        "tatum_tier": 1
    },
    {
        "name": "polygon",
        "chain_id": 137,
        "rpc_url": "https://polygon.tatum.io/",
        "explorer_url": "https://polygonscan.com",
        "currency_symbol": "MATIC",
        "avg_gas_price": 60.0,
        "avg_confirmation_time": 5.0,
        "status": "active",
        "tatum_network": "polygon-mainnet",
        "tatum_tier": 1
    },
    {
        "name": "bsc",
        "chain_id": 56,
        "rpc_url": "https://bsc.tatum.io/",
        "explorer_url": "https://bscscan.com",
        "currency_symbol": "BNB",
        "avg_gas_price": 5.0,
        "avg_confirmation_time": 5.0,
        "status": "active",
        "tatum_network": "bsc-mainnet",
        "tatum_tier": 1
    },
    {
        "name": "avalanche",
        "chain_id": 43114,
        "rpc_url": "https://avax.tatum.io/",
        "explorer_url": "https://snowtrace.io",
        "currency_symbol": "AVAX",
        "avg_gas_price": 30.0,
        "avg_confirmation_time": 2.0,
        "status": "active",
        "tatum_network": "avax-mainnet",
        "tatum_tier": 1
    },
    {
        "name": "arbitrum-one",
        "chain_id": 42161,
        "rpc_url": "https://arb-one.tatum.io/",
        "explorer_url": "https://arbiscan.io",
        "currency_symbol": "ETH",
        "avg_gas_price": 0.25,
        "avg_confirmation_time": 0.5,
        "status": "active",
        "tatum_network": "arbitrum-one-mainnet",
        "tatum_tier": 1
    },
    {
        "name": "optimism",
        "chain_id": 10,
        "rpc_url": "https://op.tatum.io/",
        "explorer_url": "https://optimistic.etherscan.io",
        "currency_symbol": "ETH",
        "avg_gas_price": 0.1,
        "avg_confirmation_time": 0.5,
        "status": "active",
        "tatum_network": "optimism-mainnet",
        "tatum_tier": 1
    },
    {
        "name": "fantom",
        "chain_id": 250,
        "rpc_url": "https://ftm.tatum.io/",
        "explorer_url": "https://ftmscan.com",
        "currency_symbol": "FTM",
        "avg_gas_price": 100.0,
        "avg_confirmation_time": 1.0,
        "status": "active",
        "tatum_network": "fantom-mainnet",
        "tatum_tier": 1
    },
    {
        "name": "harmony",
        "chain_id": 1666600000,
        "rpc_url": "https://one-mainnet.tatum.io/",
        "explorer_url": "https://explorer.harmony.one",
        "currency_symbol": "ONE",
        "avg_gas_price": 5.0,
        "avg_confirmation_time": 2.0,
        "status": "active",
        "tatum_network": "harmony-mainnet-s0",
        "tatum_tier": 3
    },
    # Additional EVM chains
    {
        "name": "base",
        "chain_id": 8453,
        "rpc_url": "https://base-mainnet.publicnode.com",
        "explorer_url": "https://basescan.org",
        "currency_symbol": "ETH",
        "avg_gas_price": 0.15,
        "avg_confirmation_time": 2.0,
        "status": "active",
        "tatum_network": "base-mainnet",
        "tatum_tier": 2
    },
    {
        "name": "zksync",
        "chain_id": 324,
        "rpc_url": "https://mainnet.era.zksync.io",
        "explorer_url": "https://explorer.zksync.io",
        "currency_symbol": "ETH",
        "avg_gas_price": 0.25,
        "avg_confirmation_time": 1.0,
        "status": "active",
        "tatum_network": "zksync-mainnet",
        "tatum_tier": 2
    },
    {
        "name": "cronos",
        "chain_id": 25,
        "rpc_url": "https://evm.cronos.org",
        "explorer_url": "https://cronoscan.com",
        "currency_symbol": "CRO",
        "avg_gas_price": 5000.0,
        "avg_confirmation_time": 5.0,
        "status": "active",
        "tatum_network": "cronos-mainnet",
        "tatum_tier": 2
    },
    {
        "name": "celo",
        "chain_id": 42220,
        "rpc_url": "https://forno.celo.org",
        "explorer_url": "https://explorer.celo.org",
        "currency_symbol": "CELO",
        "avg_gas_price": 0.1,
        "avg_confirmation_time": 5.0,
        "status": "active",
        "tatum_network": "celo-mainnet",
        "tatum_tier": 2
    },
    {
        "name": "gnosis",
        "chain_id": 100,
        "rpc_url": "https://rpc.gnosischain.com",
        "explorer_url": "https://gnosisscan.io",
        "currency_symbol": "xDAI",
        "avg_gas_price": 1.0,
        "avg_confirmation_time": 5.0,
        "status": "active",
        "tatum_network": "gnosis-mainnet",
        "tatum_tier": 2
    },
    {
        "name": "aurora",
        "chain_id": 1313161554,
        "rpc_url": "https://mainnet.aurora.dev",
        "explorer_url": "https://explorer.aurora.dev",
        "currency_symbol": "ETH",
        "avg_gas_price": 0.1,
        "avg_confirmation_time": 2.0,
        "status": "active",
        "tatum_network": "aurora-mainnet",
        "tatum_tier": 2
    },
    {
        "name": "arbitrum-nova",
        "chain_id": 42170,
        "rpc_url": "https://nova.arbitrum.io/rpc",
        "explorer_url": "https://nova-explorer.arbitrum.io",
        "currency_symbol": "ETH",
        "avg_gas_price": 0.1,
        "avg_confirmation_time": 0.5,
        "status": "active",
        "tatum_network": "arbitrum-nova-mainnet",
        "tatum_tier": 2
    }
]

# Sample strategies data
STRATEGIES = [
    {
        "name": "Flash Loan Arbitrage",
        "type": "flash_loan",
        "description": "Executes flash loan arbitrage between DEXs",
        "risk_level": "medium",
        "status": "active",
        "config": {
            "min_profit_threshold": 0.5,
            "max_gas_price": 100,
            "platforms": ["uniswap", "sushiswap"]
        }
    },
    {
        "name": "Multi-Hop Trading",
        "type": "multi_hop",
        "description": "Executes multi-hop trades across multiple DEXs",
        "risk_level": "medium",
        "status": "active",
        "config": {
            "max_hops": 3,
            "min_profit_threshold": 0.3,
            "max_gas_price": 80
        }
    },
    {
        "name": "Cross-Chain Arbitrage",
        "type": "cross_chain",
        "description": "Executes arbitrage trades across multiple chains",
        "risk_level": "high",
        "status": "active",
        "config": {
            "chains": ["ethereum", "polygon", "arbitrum"],
            "min_profit_threshold": 1.0,
            "max_gas_price": 120
        }
    },
    {
        "name": "Stablecoin Yield Farming",
        "type": "yield_farming",
        "description": "Optimizes yield farming strategies for stablecoins",
        "risk_level": "low",
        "status": "active",
        "config": {
            "platforms": ["aave", "compound", "curve"],
            "tokens": ["USDC", "DAI", "USDT"],
            "max_gas_price": 60
        }
    },
    {
        "name": "ETH 2.0 Staking",
        "type": "yield_farming",
        "description": "Optimizes ETH staking strategies",
        "risk_level": "low",
        "status": "active",
        "config": {
            "platforms": ["lido", "rocket_pool"],
            "tokens": ["ETH"],
            "max_gas_price": 50
        }
    }
]

# Sample token lists data
TOKEN_LISTS = [
    {
        "name": "Ethereum Mainnet Tokens",
        "source": "coingecko",
        "chain": "ethereum",
        "tokens_count": 100,
        "is_active": True,
        "metadata": {
            "url": "https://tokens.coingecko.com/ethereum/all.json",
            "description": "Top 100 Ethereum tokens by market cap"
        }
    },
    {
        "name": "Polygon Tokens",
        "source": "coingecko",
        "chain": "polygon",
        "tokens_count": 50,
        "is_active": True,
        "metadata": {
            "url": "https://tokens.coingecko.com/polygon/all.json",
            "description": "Top 50 Polygon tokens by market cap"
        }
    },
    {
        "name": "Stablecoins",
        "source": "custom",
        "chain": "ethereum",
        "tokens_count": 5,
        "is_active": True,
        "metadata": {
            "description": "Major stablecoins",
            "token_addresses": [
                "0x6B175474E89094C44Da98b954EedeAC495271d0F",  # DAI
                "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC
                "0xdAC17F958D2ee523a2206206994597C13D831ec7",  # USDT
                "0x4Fabb145d64652a948d72533023f6E7A623C7C53",  # BUSD
                "0x956F47F50A910163D8BF957Cf5846D573E7f87CA"   # FEI
            ]
        }
    }
]

def init_chains():
    """Initialize chain information"""
    print("Initializing chain information...")
    
    for chain_data in EVM_CHAINS:
        # Check if chain already exists
        chain = ChainInfo.query.filter_by(name=chain_data["name"]).first()
        
        if chain:
            print(f"Chain {chain_data['name']} already exists, updating...")
            
            # Update chain information
            for key, value in chain_data.items():
                setattr(chain, key, value)
        else:
            print(f"Creating chain {chain_data['name']}...")
            
            # Create new chain
            chain = ChainInfo(**chain_data)
            db.session.add(chain)
    
    # Commit changes
    db.session.commit()
    print(f"Initialized {len(EVM_CHAINS)} chains.")

def init_admin_user():
    """Initialize admin user"""
    print("Initializing admin user...")
    
    # Check if admin user already exists
    admin = User.query.filter_by(username="admin").first()
    
    if admin:
        print("Admin user already exists.")
    else:
        print("Creating admin user...")
        
        # Create admin user
        admin = User(
            username="admin",
            email="admin@example.com",
            password_hash=generate_password_hash("password"),
            created_at=datetime.utcnow(),
            telegram_enabled=True,
            max_gas_price=100.0,
            auto_reinvest=True,
            risk_level="medium",
            api_key="admin-api-key"
        )
        
        # Add to database
        db.session.add(admin)
        db.session.commit()
        print("Admin user created.")

def init_settings():
    """Initialize application settings"""
    print("Initializing application settings...")
    
    # Default settings
    default_settings = {
        "auto_harvest_enabled": "true",
        "auto_harvest_interval": "3600",
        "harvest_threshold_hours": "24",
        "max_gas_price": "100",
        "min_profit_threshold": "0.5",
        "telegram_notifications": "true",
        "risk_level": "medium",
        "version": "1.0.0",
        "wallet_protection_level": "high",
        "default_encryption_method": "AES-256-CBC",
        "cross_chain_transfer_enabled": "true",
        "token_discovery_interval": "86400",
        "balance_history_retention_days": "365"
    }
    
    # Initialize settings
    for key, value in default_settings.items():
        # Check if setting already exists
        setting = Settings.query.filter_by(key=key).first()
        
        if setting:
            print(f"Setting {key} already exists, updating...")
            setting.value = value
        else:
            print(f"Creating setting {key}...")
            setting = Settings(key=key, value=value)
            db.session.add(setting)
    
    # Commit changes
    db.session.commit()
    print(f"Initialized {len(default_settings)} settings.")

def init_strategies():
    """Initialize trading strategies"""
    print("Initializing trading strategies...")
    
    for strategy_data in STRATEGIES:
        # Check if strategy already exists
        strategy = Strategy.query.filter_by(name=strategy_data["name"]).first()
        
        if strategy:
            print(f"Strategy {strategy_data['name']} already exists, updating...")
            
            # Update strategy information
            for key, value in strategy_data.items():
                if key == 'config':
                    # Convert dict to JSON-serialized string for SQLite
                    setattr(strategy, key, json.dumps(value))
                else:
                    setattr(strategy, key, value)
        else:
            print(f"Creating strategy {strategy_data['name']}...")
            
            # Prepare config as JSON string
            config_json = json.dumps(strategy_data["config"])
            
            # Create new strategy
            strategy = Strategy(
                name=strategy_data["name"],
                type=strategy_data["type"],
                description=strategy_data["description"],
                risk_level=strategy_data["risk_level"],
                status=strategy_data["status"],
                config=config_json,  # Use JSON string instead of dict
                strategy_metadata="{}",  # Empty JSON object as string
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(strategy)
    
    # Commit changes
    db.session.commit()
    print(f"Initialized {len(STRATEGIES)} strategies.")
def init_token_lists():
    """Initialize token lists"""
    print("Initializing token lists...")
    
    for token_list_data in TOKEN_LISTS:
        # Check if token list already exists
        token_list = TokenList.query.filter_by(name=token_list_data["name"]).first()
        
        if token_list:
            print(f"Token list {token_list_data['name']} already exists, updating...")
            
            # Update token list information
            for key, value in token_list_data.items():
                if key == 'metadata':
                    # Convert to JSON string for SQLite
                    token_list.list_metadata = json.dumps(value)
                elif key != 'list_metadata':  # Skip if already handled via 'metadata'
                    setattr(token_list, key, value)
        else:
            print(f"Creating token list {token_list_data['name']}...")
            
            # Create new token list with properly serialized JSON
            token_list = TokenList(
                name=token_list_data["name"],
                source=token_list_data["source"],
                chain=token_list_data["chain"],
                tokens_count=token_list_data["tokens_count"],
                is_active=token_list_data["is_active"],
                list_metadata=json.dumps(token_list_data["metadata"]),  # Serialize to JSON string
                last_updated=datetime.utcnow()
            )
            db.session.add(token_list)
    
    # Commit changes
    db.session.commit()
    print(f"Initialized {len(TOKEN_LISTS)} token lists.")
def main():
    """Main function"""
    print("Initializing database...")
    
    # Create application context
    app = create_app()
    
    with app.app_context():
        # Drop all tables if they exist to ensure fresh database
        print("Dropping existing tables...")
        db.drop_all()
        
        # Initialize database tables
        print("Creating new tables...")
        db.create_all()
        print("Database tables created.")
        
        # Initialize data
        init_chains()
        init_admin_user()
        init_settings()
        init_strategies()
        init_token_lists()
        
        print("Database initialization complete.")

if __name__ == "__main__":
    main()