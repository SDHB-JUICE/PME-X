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
from app.models.wallet import ChainInfo
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
    }
    # Additional chains can be added here
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
        "version": "1.0.0"
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

def main():
    """Main function"""
    print("Initializing database...")
    
    # Create application context
    app = create_app()
    
    with app.app_context():
        # Initialize database tables
        db.create_all()
        print("Database tables created.")
        
        # Initialize data
        init_chains()
        init_admin_user()
        init_settings()
        
        print("Database initialization complete.")

if __name__ == "__main__":
    main()