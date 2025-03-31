"""
Wallet Strategy Executor Service
Handles the execution of strategies across multiple wallets
"""
from datetime import datetime
import concurrent.futures
from app import db
from app.models.trade import Trade
from app.models.wallet import Wallet, ChainInfo
from app.services.flash_loan import FlashLoanService
from app.services.multi_hop import MultiHopService
from app.services.cross_chain import CrossChainService
from app.services.yield_farming import YieldFarmingService
from app.utils.web3_helper import get_web3_for_chain
import logging
from flask import current_app
logger = logging.getLogger(__name__)
class WalletStrategyExecutor:
    """Service for executing strategies across multiple wallets"""
    
    def __init__(self):
        """Initialize the executor"""
        self.services = {
            'flash_loan': FlashLoanService,
            'multi_hop': MultiHopService,
            'cross_chain': CrossChainService,
            'yield_farming': YieldFarmingService
        }
    
    

    def execute_strategies(self, wallet_ids, strategy_types, execution_mode='parallel', strategy_params=None):
        """Execute strategies across specified wallets"""
        logger.info(f"Starting strategy execution: {len(wallet_ids)} wallets, {len(strategy_types)} strategies")
        logger.info(f"Strategy types: {strategy_types}")
        logger.info(f"Execution mode: {execution_mode}")
        
        # Default strategy parameters
        if strategy_params is None:
            strategy_params = {}
        
        # Get wallets
        wallets = Wallet.query.filter(Wallet.id.in_(wallet_ids)).all()
        logger.info(f"Found {len(wallets)} wallets")
        
        # Initialize results
        results = {
            'success': True,
            'wallets': [],
            'total_profit': 0
        }
        
        # Execute strategies
        if execution_mode == 'parallel':
            logger.info("Using parallel execution mode")
            # Execute in parallel - get the application context
            app = current_app._get_current_object()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # Submit wallet execution tasks with application context
                future_to_wallet = {
                    executor.submit(self._execute_wallet_with_app_context, app, wallet, strategy_types, strategy_params): wallet
                    for wallet in wallets
                }
                
                # Process results as they complete
                for future in concurrent.futures.as_completed(future_to_wallet):
                    wallet = future_to_wallet[future]
                    try:
                        logger.info(f"Processing results for wallet {wallet.address}")
                        wallet_result = future.result()
                        results['wallets'].append(wallet_result)
                        results['total_profit'] += wallet_result['profit']
                    except Exception as e:
                        logger.error(f"Error processing wallet {wallet.address}: {str(e)}", exc_info=True)
                        results['wallets'].append({
                            'id': wallet.id,
                            'address': wallet.address,
                            'chain': wallet.chain,
                            'profit': 0,
                            'strategies': [],
                            'error': str(e),
                            'message': "Execution failed - see error details"
                        })
        else:
            # Sequential execution doesn't need app context handling
            for wallet in wallets:
                try:
                    wallet_result = self._execute_wallet_strategies(wallet, strategy_types, strategy_params)
                    results['wallets'].append(wallet_result)
                    results['total_profit'] += wallet_result['profit']
                except Exception as e:
                    logger.error(f"Error processing wallet {wallet.address}: {str(e)}", exc_info=True)
                    results['wallets'].append({
                        'id': wallet.id,
                        'address': wallet.address,
                        'chain': wallet.chain,
                        'profit': 0,
                        'strategies': [],
                        'error': str(e),
                        'message': "Execution failed - see error details"
                    })
        
        logger.info(f"Execution completed. Total profit: {results['total_profit']}")
        return results

    def _execute_wallet_with_app_context(self, app, wallet, strategy_types, strategy_params):
        """Execute strategies for a wallet with application context"""
        with app.app_context():
            return self._execute_wallet_strategies(wallet, strategy_types, strategy_params)
    
    def _execute_wallet_strategies(self, wallet, strategy_types, strategy_params):
        """Execute strategies for a specific wallet"""
        logger.info(f"Executing strategies for wallet {wallet.address} on chain {wallet.chain}")
        
        # Initialize wallet result
        wallet_result = {
            'id': wallet.id,
            'address': wallet.address,
            'chain': wallet.chain,
            'profit': 0,
            'strategies': []
        }
        
        # Get chain info
        chain_info = ChainInfo.query.filter_by(name=wallet.chain).first()
        if not chain_info:
            logger.error(f"Chain {wallet.chain} not found in database")
            wallet_result['message'] = f"Chain {wallet.chain} not found in database"
            return wallet_result
        
        # Get private key (in a production environment, this would be securely retrieved)
        private_key = wallet.private_key_encrypted  # In production, this would be decrypted
        if not private_key:
            logger.error(f"Wallet {wallet.address} does not have a private key")
            wallet_result['message'] = "Wallet does not have a private key - required for execution"
            return wallet_result
        
        # Check wallet balance
        try:
            web3 = get_web3_for_chain(wallet.chain)
            balance = web3.eth.get_balance(wallet.address)
            balance_eth = web3.from_wei(balance, 'ether')
            logger.info(f"Wallet balance: {balance_eth} {wallet.chain.upper()}")
            
            # Check if balance is too low for gas fees
            if balance_eth < 0.01:  # Example threshold
                logger.warning(f"Wallet balance might be too low for gas fees: {balance_eth}")
                wallet_result['message'] = f"Low balance ({balance_eth}) may not cover gas fees"
        except Exception as e:
            logger.error(f"Error checking wallet balance: {str(e)}")
        
        # Execute each strategy
        for strategy_type in strategy_types:
            logger.info(f"Executing strategy {strategy_type} for wallet {wallet.address}")
            try:
                # Get strategy parameters
                params = strategy_params.get(strategy_type, {})
                logger.info(f"Strategy parameters: {params}")
                
                # Execute strategy
                result = None
                if strategy_type == 'flash_loan':
                    result = self._execute_flash_loan(wallet, private_key, params)
                elif strategy_type == 'multi_hop':
                    result = self._execute_multi_hop(wallet, private_key, params)
                elif strategy_type == 'cross_chain':
                    result = self._execute_cross_chain(wallet, private_key, params)
                elif strategy_type == 'yield_farming':
                    result = self._execute_yield_farming(wallet, private_key, params)
                else:
                    logger.warning(f"Unknown strategy type: {strategy_type}")
                    continue
                
                if result:
                    logger.info(f"Strategy {strategy_type} result: {result}")
                else:
                    logger.warning(f"Strategy {strategy_type} returned no result")
                    result = {
                        'success': False,
                        'error': 'No result returned from strategy execution',
                        'net_profit': 0
                    }
                
                # Add strategy result
                wallet_result['strategies'].append({
                    'strategy': strategy_type,
                    'success': result.get('success', False),
                    'profit': result.get('net_profit', 0),
                    'details': result
                })
                
                # Update total profit
                if result.get('success', False):
                    wallet_result['profit'] += result.get('net_profit', 0)
                
                # Record trade in database if successful
                if result.get('success', False):
                    try:
                        trade = Trade(
                            wallet_address=wallet.address,
                            chain=wallet.chain,
                            strategy_type=strategy_type,
                            tx_hash=result.get('tx_hash'),
                            gas_used=result.get('gas_used', 0),
                            gas_price=result.get('gas_price', 0),
                            net_profit=result.get('net_profit', 0),
                            execution_time=result.get('execution_time', 0),
                            status='completed',
                            created_at=datetime.utcnow()
                        )
                        db.session.add(trade)
                        db.session.commit()
                        logger.info(f"Trade record created for strategy {strategy_type}")
                    except Exception as e:
                        logger.error(f"Error creating trade record: {str(e)}")
                
            except Exception as e:
                logger.error(f"Error executing strategy {strategy_type}: {str(e)}", exc_info=True)
                # Record failed strategy
                wallet_result['strategies'].append({
                    'strategy': strategy_type,
                    'success': False,
                    'profit': 0,
                    'error': str(e)
                })
        
        # Add message if no strategies were executed
        if not wallet_result['strategies']:
            wallet_result['message'] = "No strategies were executed - check logs for details"
        elif all(not s.get('success', False) for s in wallet_result['strategies']):
            wallet_result['message'] = "All strategies failed - check individual strategy errors"
        
        return wallet_result
    
    def _execute_flash_loan(self, wallet, private_key, params):
        """Execute flash loan strategy"""
        logger.info(f"Executing flash loan for wallet {wallet.address[:8]}...{wallet.address[-6:]}")
        logger.info(f"Parameters: token={params.get('token')}, amount={params.get('amount')}, dexes={params.get('dex1')}-{params.get('dex2')}")
        
        # Check wallet balance before execution
        web3 = get_web3_for_chain(wallet.chain)
        balance = web3.eth.get_balance(wallet.address)
        balance_eth = web3.from_wei(balance, 'ether')
        logger.info(f"Wallet balance: {balance_eth} {wallet.chain.upper()}")
        
        # Get parameters
        token = params.get('token', 'DAI')
        amount = float(params.get('amount', 1000000))
        dex1 = params.get('dex1', 'uniswap')
        dex2 = params.get('dex2', 'sushiswap')
        
        try:
            # Get contract address from config
            from flask import current_app
            contract_address = current_app.config.get(f'{wallet.chain.upper()}_FLASH_LOAN_CONTRACT')
            
            if not contract_address:
                logger.error(f"No flash loan contract found for chain {wallet.chain}")
                return {
                    'success': False,
                    'net_profit': 0,
                    'error': f'Flash loan contract not deployed on {wallet.chain}. Deploy contract first.',
                    'details': 'Deploy a flash loan contract for this chain in the settings'
                }
            
            # Initialize service
            service = FlashLoanService(wallet.chain, private_key, contract_address)
            
            # Execute flash loan
            result = service.execute_flash_loan(token, amount, dex1, dex2)
            logger.info(f"Flash loan execution complete: {result}")
            return result
        except Exception as e:
            logger.error(f"Flash loan execution failed: {str(e)}", exc_info=True)
            return {
                'success': False,
                'net_profit': 0,
                'error': str(e)
            }
    
    def _execute_multi_hop(self, wallet, private_key, params):
        """Execute multi-hop strategy"""
        # Get parameters
        amount = float(params.get('amount', 10000))
        max_hops = int(params.get('max_hops', 3))
        min_profit = float(params.get('min_profit', 0.5)) / 100  # Convert from percentage
        
        # Initialize service
        service = MultiHopService(wallet.chain, private_key)
        
        # Execute multi-hop
        result = service.execute_multi_hop_arbitrage(amount, max_hops, min_profit)
        
        return result
    
    def _execute_cross_chain(self, wallet, private_key, params):
        """Execute cross-chain strategy"""
        # Get parameters
        target_chain = params.get('target_chain', 'ethereum')
        token = params.get('token', 'USDC')
        amount = float(params.get('amount', 10000))
        min_profit = float(params.get('min_profit', 0.5)) / 100  # Convert from percentage
        
        # Initialize service
        service = CrossChainService(wallet.chain, target_chain, private_key)
        
        # Execute cross-chain
        result = service.execute_cross_chain_arbitrage(token, amount, min_profit)
        
        return result
    
    def _execute_yield_farming(self, wallet, private_key, params):
        """Execute yield farming strategy"""
        # Get parameters
        protocol = params.get('protocol', 'aave')
        pool = params.get('pool', 'usdc')
        amount = float(params.get('amount', 10000))
        
        # Initialize service
        service = YieldFarmingService(wallet.chain, private_key)
        
        # Execute yield farming
        result = service.execute_deposit(protocol, pool, amount)
        
        return result