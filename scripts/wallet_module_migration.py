"""
Database Migration for Wallet Module Enhancement
"""
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, Float, String, DateTime, Date, Text, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
import argparse

# Base class for declarative models
Base = declarative_base()

def create_migration_engine(connection_string):
    """Create SQLAlchemy engine for migration"""
    return create_engine(connection_string)

def run_migration(engine):
    """Run the migration to add new tables and columns"""
    # Create metadata
    metadata = MetaData()
    metadata.bind = engine
    
    # Define new tables
    
    # Enhanced Token model
    Token = Table(
        'token', metadata,
        Column('id', Integer, primary_key=True),
        Column('wallet_id', Integer, ForeignKey('wallet.id'), nullable=False),
        Column('chain', String(50), nullable=False),
        Column('address', String(100), nullable=False, index=True),
        Column('symbol', String(20), nullable=False),
        Column('name', String(100), nullable=True),
        Column('decimals', Integer, default=18),
        Column('balance', Float, default=0.0),
        Column('usd_value', Float, default=0.0),
        Column('logo_url', String(256), nullable=True),
        Column('contract_type', String(20), default="ERC20"),
        Column('is_verified', Boolean, default=False),
        Column('token_list_source', String(50), nullable=True),
        Column('current_price', Float, default=0.0),
        Column('price_24h_change', Float, default=0.0),
        Column('all_time_high', Float, default=0.0),
        Column('all_time_high_date', DateTime, nullable=True),
        Column('metadata', JSONB, default={}),
        Column('last_updated', DateTime, default=datetime.utcnow)
    )
    
    # Token Price History
    TokenPriceHistory = Table(
        'token_price_history', metadata,
        Column('id', Integer, primary_key=True),
        Column('token_id', Integer, ForeignKey('token.id', ondelete='CASCADE'), nullable=False),
        Column('timestamp', DateTime, default=datetime.utcnow, index=True),
        Column('price', Float, nullable=False),
        Column('volume_24h', Float, nullable=True),
        Column('market_cap', Float, nullable=True)
    )
    
    # Token List
    TokenList = Table(
        'token_list', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(50), nullable=False),
        Column('source', String(50), nullable=False),
        Column('chain', String(50), nullable=False),
        Column('tokens_count', Integer, default=0),
        Column('is_active', Boolean, default=True),
        Column('last_updated', DateTime, default=datetime.utcnow),
        Column('metadata', JSONB, default={})
    )
    
    # Token Transaction
    TokenTransaction = Table(
        'token_transaction', metadata,
        Column('id', Integer, primary_key=True),
        Column('wallet_id', Integer, ForeignKey('wallet.id'), nullable=False),
        Column('token_id', Integer, ForeignKey('token.id', ondelete='SET NULL'), nullable=True),
        Column('chain', String(50), nullable=False),
        Column('tx_hash', String(100), nullable=False, unique=True, index=True),
        Column('block_number', Integer, nullable=False),
        Column('timestamp', DateTime, nullable=False, index=True),
        Column('from_address', String(100), nullable=False),
        Column('to_address', String(100), nullable=False),
        Column('amount', Float, nullable=False),
        Column('usd_value', Float, nullable=True),
        Column('gas_used', Integer, nullable=True),
        Column('gas_price', Integer, nullable=True),
        Column('gas_cost_eth', Float, nullable=True),
        Column('gas_cost_usd', Float, nullable=True),
        Column('tx_type', String(20), nullable=True),
        Column('status', String(20), default="confirmed"),
        Column('error_message', String(256), nullable=True),
        Column('metadata', JSONB, default={})
    )
    
    # Wallet Balance History
    WalletBalanceHistory = Table(
        'wallet_balance_history', metadata,
        Column('id', Integer, primary_key=True),
        Column('wallet_id', Integer, ForeignKey('wallet.id'), nullable=False),
        Column('date', Date, nullable=False, index=True),
        Column('native_balance', Float, default=0.0),
        Column('usd_balance', Float, default=0.0),
        Column('token_balances', JSONB, default={}),
        Column('token_usd_values', JSONB, default={}),
        Column('last_updated', DateTime, default=datetime.utcnow)
    )
    
    # Strategy model
    Strategy = Table(
        'strategy', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(100), nullable=False),
        Column('type', String(50), nullable=False),
        Column('description', Text, nullable=True),
        Column('risk_level', String(20), default='medium'),
        Column('status', String(20), default='active'),
        Column('config', JSONB, default={}),
        Column('metadata', JSONB, default={}),
        Column('created_at', DateTime, default=datetime.utcnow),
        Column('updated_at', DateTime, default=datetime.utcnow)
    )
    
    # Wallet Strategy link
    WalletStrategy = Table(
        'wallet_strategy', metadata,
        Column('wallet_id', Integer, ForeignKey('wallet.id'), primary_key=True),
        Column('strategy_id', Integer, ForeignKey('strategy.id'), primary_key=True),
        Column('allocation', Float, default=0.0),
        Column('allocation_value', Float, default=0.0),
        Column('performance', Float, default=0.0),
        Column('status', String(20), default='active'),
        Column('last_run', DateTime, nullable=True),
        Column('created_at', DateTime, default=datetime.utcnow),
        Column('updated_at', DateTime, default=datetime.utcnow)
    )
    
    # Strategy Transaction
    StrategyTransaction = Table(
        'strategy_transaction', metadata,
        Column('id', Integer, primary_key=True),
        Column('wallet_id', Integer, ForeignKey('wallet.id'), nullable=False),
        Column('strategy_id', Integer, ForeignKey('strategy.id'), nullable=False),
        Column('tx_hash', String(100), nullable=True),
        Column('timestamp', DateTime, default=datetime.utcnow),
        Column('tx_type', String(50), nullable=False),
        Column('amount', Float, default=0.0),
        Column('token_address', String(100), nullable=True),
        Column('token_symbol', String(20), nullable=True),
        Column('usd_value', Float, default=0.0),
        Column('gas_cost', Float, default=0.0),
        Column('gas_cost_usd', Float, default=0.0),
        Column('profit_loss', Float, default=0.0),
        Column('status', String(20), default='confirmed'),
        Column('error', Text, nullable=True),
        Column('metadata', JSONB, default={})
    )
    
    # Strategy Asset
    StrategyAsset = Table(
        'strategy_asset', metadata,
        Column('id', Integer, primary_key=True),
        Column('strategy_id', Integer, ForeignKey('strategy.id'), nullable=False),
        Column('wallet_id', Integer, ForeignKey('wallet.id'), nullable=False),
        Column('token_address', String(100), nullable=True),
        Column('token_symbol', String(20), nullable=False),
        Column('token_name', String(100), nullable=True),
        Column('balance', Float, default=0.0),
        Column('usd_value', Float, default=0.0),
        Column('last_updated', DateTime, default=datetime.utcnow)
    )
    
    # Strategy Performance
    StrategyPerformance = Table(
        'strategy_performance', metadata,
        Column('id', Integer, primary_key=True),
        Column('strategy_id', Integer, ForeignKey('strategy.id'), nullable=False),
        Column('timestamp', DateTime, default=datetime.utcnow),
        Column('period', String(20), nullable=False),
        Column('roi', Float, default=0.0),
        Column('profit_loss', Float, default=0.0),
        Column('volume', Float, default=0.0),
        Column('gas_costs', Float, default=0.0),
        Column('tx_count', Integer, default=0),
        Column('success_rate', Float, default=0.0)
    )
    
    # Wallet Allocation History
    WalletAllocationHistory = Table(
        'wallet_allocation_history', metadata,
        Column('id', Integer, primary_key=True),
        Column('wallet_id', Integer, ForeignKey('wallet.id'), nullable=False),
        Column('date', Date, nullable=False, index=True),
        Column('native_percentage', Float, default=0.0),
        Column('token_percentages', JSONB, default={}),
        Column('total_value', Float, default=0.0),
        Column('last_updated', DateTime, default=datetime.utcnow)
    )
    
    # User Permission
    UserPermission = Table(
        'user_permission', metadata,
        Column('id', Integer, primary_key=True),
        Column('user_id', Integer, ForeignKey('user.id'), nullable=False),
        Column('resource_type', String(50), nullable=False),
        Column('resource_id', Integer, nullable=False),
        Column('permission_level', String(20), nullable=False),
        Column('created_at', DateTime, default=datetime.utcnow),
        Column('updated_at', DateTime, default=datetime.utcnow)
    )
    
    # Create tables
    metadata.create_all(engine, checkfirst=True)
    
    print("Migration completed. New tables created.")

def add_sample_data(engine):
    """Add sample data to the database"""
    # Create session
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Add sample strategies
        strategies = [
            {
                'name': 'Flash Loan Arbitrage',
                'type': 'flash_loan',
                'description': 'Executes flash loan arbitrage between DEXs',
                'risk_level': 'medium',
                'config': {
                    'min_profit_threshold': 0.5,
                    'max_gas_price': 100,
                    'platforms': ['uniswap', 'sushiswap']
                }
            },
            {
                'name': 'Multi-Hop Trading',
                'type': 'multi_hop',
                'description': 'Executes multi-hop trades across multiple DEXs',
                'risk_level': 'medium',
                'config': {
                    'max_hops': 3,
                    'min_profit_threshold': 0.3,
                    'max_gas_price': 80
                }
            },
            {
                'name': 'Cross-Chain Arbitrage',
                'type': 'cross_chain',
                'description': 'Executes arbitrage trades across multiple chains',
                'risk_level': 'high',
                'config': {
                    'chains': ['ethereum', 'polygon', 'arbitrum'],
                    'min_profit_threshold': 1.0,
                    'max_gas_price': 120
                }
            },
            {
                'name': 'Stablecoin Yield Farming',
                'type': 'yield_farming',
                'description': 'Optimizes yield farming strategies for stablecoins',
                'risk_level': 'low',
                'config': {
                    'platforms': ['aave', 'compound', 'curve'],
                    'tokens': ['USDC', 'DAI', 'USDT'],
                    'max_gas_price': 60
                }
            },
            {
                'name': 'ETH 2.0 Staking',
                'type': 'yield_farming',
                'description': 'Optimizes ETH staking strategies',
                'risk_level': 'low',
                'config': {
                    'platforms': ['lido', 'rocket_pool'],
                    'tokens': ['ETH'],
                    'max_gas_price': 50
                }
            }
        ]
        
        for strategy_data in strategies:
            # Check if strategy already exists
            stmt = f"SELECT id FROM strategy WHERE name = '{strategy_data['name']}'"
            result = engine.execute(stmt).fetchone()
            
            if not result:
                # Insert strategy
                stmt = f"""
                INSERT INTO strategy (name, type, description, risk_level, config, status, created_at, updated_at)
                VALUES (
                    '{strategy_data['name']}',
                    '{strategy_data['type']}',
                    '{strategy_data['description']}',
                    '{strategy_data['risk_level']}',
                    '{str(strategy_data['config']).replace("'", "''").replace("True", "true").replace("False", "false")}',
                    'active',
                    '{datetime.utcnow()}',
                    '{datetime.utcnow()}'
                )
                """
                engine.execute(stmt)
                print(f"Added strategy: {strategy_data['name']}")
            else:
                print(f"Strategy already exists: {strategy_data['name']}")
        
        # Add sample token lists
        token_lists = [
            {
                'name': 'Ethereum Mainnet Tokens',
                'source': 'coingecko',
                'chain': 'ethereum',
                'tokens_count': 100,
                'is_active': True,
                'metadata': {
                    'url': 'https://tokens.coingecko.com/ethereum/all.json',
                    'description': 'Top 100 Ethereum tokens by market cap'
                }
            },
            {
                'name': 'Polygon Tokens',
                'source': 'coingecko',
                'chain': 'polygon',
                'tokens_count': 50,
                'is_active': True,
                'metadata': {
                    'url': 'https://tokens.coingecko.com/polygon/all.json',
                    'description': 'Top 50 Polygon tokens by market cap'
                }
            },
            {
                'name': 'Stablecoins',
                'source': 'custom',
                'chain': 'ethereum',
                'tokens_count': 5,
                'is_active': True,
                'metadata': {
                    'description': 'Major stablecoins',
                    'token_addresses': [
                        '0x6B175474E89094C44Da98b954EedeAC495271d0F',  # DAI
                        '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',  # USDC
                        '0xdAC17F958D2ee523a2206206994597C13D831ec7',  # USDT
                        '0x4Fabb145d64652a948d72533023f6E7A623C7C53',  # BUSD
                        '0x956F47F50A910163D8BF957Cf5846D573E7f87CA'   # FEI
                    ]
                }
            }
        ]
        
        for token_list_data in token_lists:
            # Check if token list already exists
            stmt = f"SELECT id FROM token_list WHERE name = '{token_list_data['name']}'"
            result = engine.execute(stmt).fetchone()
            
            if not result:
                # Insert token list
                stmt = f"""
                INSERT INTO token_list (name, source, chain, tokens_count, is_active, metadata, last_updated)
                VALUES (
                    '{token_list_data['name']}',
                    '{token_list_data['source']}',
                    '{token_list_data['chain']}',
                    {token_list_data['tokens_count']},
                    {str(token_list_data['is_active']).lower()},
                    '{str(token_list_data['metadata']).replace("'", "''").replace("True", "true").replace("False", "false")}',
                    '{datetime.utcnow()}'
                )
                """
                engine.execute(stmt)
                print(f"Added token list: {token_list_data['name']}")
            else:
                print(f"Token list already exists: {token_list_data['name']}")
        
        print("Sample data added successfully.")
    
    except Exception as e:
        print(f"Error adding sample data: {e}")
        session.rollback()
    finally:
        session.close()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Run database migrations for wallet module enhancement')
    parser.add_argument('--db-url', dest='db_url', help='Database connection URL')
    parser.add_argument('--sample-data', dest='sample_data', action='store_true', help='Add sample data after migration')
    
    args = parser.parse_args()
    
    # Get database URL from argument or environment variable
    db_url = args.db_url or os.environ.get('DATABASE_URL')
    
    if not db_url:
        print("Error: Database URL not provided. Use --db-url or set DATABASE_URL environment variable.")
        return
    
    # Create engine
    engine = create_migration_engine(db_url)
    
    # Run migration
    run_migration(engine)
    
    # Add sample data if requested
    if args.sample_data:
        add_sample_data(engine)

if __name__ == '__main__':
    main()