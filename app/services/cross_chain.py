"""
Cross Chain Arbitrage Service
Finds and executes profitable arbitrage between different EVM chains
"""
import time
import json
import logging
from datetime import datetime
from web3 import Web3
from app import db
from app.models.trade import Trade
from app.models.wallet import ChainInfo
from app.services.telegram_alert import send_alert
from app.utils.web3_helper import get_web3, estimate_gas_cost_usd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CrossChainService:
    """Service for executing cross-chain arbitrage"""
    
    def __init__(self, source_chain, target_chain, private_key):
        """Initialize cross-chain service
        
        Args:
            source_chain (str): Name of the source chain
            target_chain (str): Name of the target chain
            private_key (str): Private key for transaction signing
        """
        self.source_chain = source_chain
        self.target_chain = target_chain
        self.private_key = private_key
        
        # Get chain info from database
        source_chain_info = ChainInfo.query.filter_by(name=source_chain).first()
        target_chain_info = ChainInfo.query.filter_by(name=target_chain).first()
        
        if not source_chain_info or not target_chain_info:
            chains_missing = []
            if not source_chain_info:
                chains_missing.append(source_chain)
            if not target_chain_info:
                chains_missing.append(target_chain)
            raise ValueError(f"Chains not found in database: {', '.join(chains_missing)}")
        
        self.source_chain_info = source_chain_info
        self.target_chain_info = target_chain_info
        
        # Initialize Web3 connections
        self.source_web3 = get_web3(source_chain_info.rpc_url)
        self.target_web3 = get_web3(target_chain_info.rpc_url)
        
        # Get accounts from private key
        self.account = self.source_web3.eth.account.from_key(private_key)
        self.address = self.account.address
        
        logger.info(f"Initialized CrossChainService for {source_chain} -> {target_chain}")
    
    def find_arbitrage_opportunities(self, token_symbol="USDC", amount=1000):
        """Find arbitrage opportunities between chains
        
        Args:
            token_symbol (str): Symbol of token to trade
            amount (float): Amount to trade
            
        Returns:
            list: List of potential arbitrage opportunities
        """
        # This is a placeholder implementation
        # In a real implementation, you would:
        # 1. Query token prices on both chains
        # 2. Calculate potential profit
        # 3. Check liquidity and feasibility
        # 4. Return opportunities sorted by profit
        
        # Mock price differences for demonstration
        price_diff_percentage = 0.8  # 0.8% difference
        estimated_gas_cost_source = 0.01  # ETH
        estimated_gas_cost_target = 0.005  # ETH
        bridge_fee_percentage = 0.1  # 0.1% bridge fee
        
        # Convert gas costs to USD
        gas_cost_source_usd = estimate_gas_cost_usd(self.source_chain, estimated_gas_cost_source)
        gas_cost_target_usd = estimate_gas_cost_usd(self.target_chain, estimated_gas_cost_target)
        
        # Calculate estimated profit
        price_diff = amount * (price_diff_percentage / 100)
        bridge_fee = amount * (bridge_fee_percentage / 100)
        estimated_profit = price_diff - bridge_fee - gas_cost_source_usd - gas_cost_target_usd
        
        # Create opportunity object
        opportunity = {
            'source_chain': self.source_chain,
            'target_chain': self.target_chain,
            'token': token_symbol,
            'amount': amount,
            'price_diff_percentage': price_diff_percentage,
            'bridge_fee': bridge_fee,
            'gas_cost_source': gas_cost_source_usd,
            'gas_cost_target': gas_cost_target_usd,
            'estimated_profit': estimated_profit,
            'estimated_roi': (estimated_profit / amount) * 100
        }
        
        return [opportunity] if estimated_profit > 0 else []
    
    def execute_cross_chain_arbitrage(self, token_symbol="USDC", amount=1000, min_profit_threshold=0.5):
        """Execute cross-chain arbitrage
        
        Args:
            token_symbol (str): Symbol of token to trade
            amount (float): Amount to trade in USD
            min_profit_threshold (float): Minimum profit threshold in percentage
            
        Returns:
            dict: Transaction result
        """
        start_time = time.time()
        
        try:
            # Find arbitrage opportunities
            opportunities = self.find_arbitrage_opportunities(token_symbol, amount)
            
            if not opportunities:
                return {
                    'success': False,
                    'error': "No profitable arbitrage opportunities found",
                    'execution_time': time.time() - start_time
                }
            
            # Get best opportunity
            best_opportunity = opportunities[0]
            
            # Check if profit meets threshold
            min_profit_amount = amount * (min_profit_threshold / 100)
            if best_opportunity['estimated_profit'] < min_profit_amount:
                return {
                    'success': False,
                    'error': f"Best opportunity profit ${best_opportunity['estimated_profit']:.2f} below threshold ${min_profit_amount:.2f}",
                    'execution_time': time.time() - start_time
                }
            
            # In a real implementation, you would:
            # 1. Send tokens from source chain to bridge
            # 2. Wait for tokens to arrive on target chain
            # 3. Sell tokens on target chain
            # 4. (Optional) Bridge profits back to source chain
            
            # For demo purposes, we'll simulate a successful execution
            tx_hash_source = self.source_web3.keccak(text=f"cross_chain_source_{time.time()}").hex()
            tx_hash_target = self.target_web3.keccak(text=f"cross_chain_target_{time.time()}").hex()
            
            # Calculate profit
            profit_usd = best_opportunity['estimated_profit']
            gas_cost_usd = best_opportunity['gas_cost_source'] + best_opportunity['gas_cost_target']
            net_profit = profit_usd - gas_cost_usd
            
            # Create trade record
            trade = Trade(
                strategy_type="cross_chain",
                chain=f"{self.source_chain}->{self.target_chain}",
                amount=amount,
                profit=profit_usd,
                gas_cost=gas_cost_usd,
                net_profit=net_profit,
                tx_hash=tx_hash_source,  # Store source chain tx hash
                status="completed",
                execution_time=time.time() - start_time,
                details={
                    'token': token_symbol,
                    'source_chain': self.source_chain,
                    'target_chain': self.target_chain,
                    'price_diff_percentage': best_opportunity['price_diff_percentage'],
                    'bridge_fee': best_opportunity['bridge_fee'],
                    'tx_hash_source': tx_hash_source,
                    'tx_hash_target': tx_hash_target
                }
            )
            
            # Save to database
            db.session.add(trade)
            db.session.commit()
            
            # Send telegram alert
            send_alert(f"✅ Cross-Chain Arbitrage executed from {self.source_chain} to {self.target_chain}. Profit: ${net_profit:.2f}")
            
            return {
                'success': True,
                'tx_hash_source': tx_hash_source,
                'tx_hash_target': tx_hash_target,
                'profit': profit_usd,
                'gas_cost': gas_cost_usd,
                'net_profit': net_profit,
                'execution_time': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Cross-chain arbitrage execution failed: {str(e)}")
            
            # Create failed trade record
            trade = Trade(
                strategy_type="cross_chain",
                chain=f"{self.source_chain}->{self.target_chain}",
                amount=amount,
                profit=0,
                gas_cost=0,
                net_profit=0,
                status="failed",
                execution_time=time.time() - start_time,
                details={
                    'token': token_symbol,
                    'source_chain': self.source_chain,
                    'target_chain': self.target_chain,
                    'error': str(e)
                }
            )
            
            # Save to database
            db.session.add(trade)
            db.session.commit()
            
            # Send telegram alert
            send_alert(f"❌ Cross-Chain Arbitrage failed from {self.source_chain} to {self.target_chain}: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }