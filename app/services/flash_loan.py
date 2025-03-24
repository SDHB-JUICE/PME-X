"""
Flash Loan Service
Handles the execution of flash loans across multiple EVM chains
"""
import time
import json
import logging
from datetime import datetime
from web3 import Web3
from web3.exceptions import ContractLogicError
from app import db
from app.models.trade import Trade
from app.models.wallet import ChainInfo
from app.services.telegram_alert import send_alert
from app.utils.web3_helper import get_web3, load_contract, estimate_gas_cost_usd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Contract addresses for major protocols (could be moved to config or database)
AAVE_LENDING_POOL_ADDRESSES = {
    'ethereum': '0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9',
    'polygon': '0x8dFf5E27EA6b7AC08EbFdf9eB090F32ee9a30fcf',
    'avalanche': '0x4F01AeD16D97E3aB5ab2B501154DC9bb0F1A5A2C',
    'arbitrum-one': '0x794a61358D6845594F94dc1DB02A252b5b4814aD',
    'optimism': '0x794a61358D6845594F94dc1DB02A252b5b4814aD',
}

# Token addresses for major tokens
TOKEN_ADDRESSES = {
    'ethereum': {
        'DAI': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
        'USDC': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
        'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
        'WETH': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
    },
    'polygon': {
        'DAI': '0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063',
        'USDC': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
        'USDT': '0xc2132D05D31c914a87C6611C10748AEb04B58e8F',
        'WMATIC': '0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270',
    },
    # Add more chains as needed
}

class FlashLoanService:
    """Service for executing flash loans"""
    
    def __init__(self, chain_name, private_key, contract_address=None):
        """Initialize flash loan service
        
        Args:
            chain_name (str): Name of the chain (ethereum, polygon, etc.)
            private_key (str): Private key for transaction signing
            contract_address (str, optional): Address of deployed FlashYieldArb contract
        """
        self.chain_name = chain_name
        self.private_key = private_key
        
        # Get chain info from database
        chain_info = ChainInfo.query.filter_by(name=chain_name).first()
        if not chain_info:
            raise ValueError(f"Chain {chain_name} not found in database")
        
        self.chain_info = chain_info
        self.web3 = get_web3(chain_info.rpc_url)
        
        # Get account from private key
        self.account = self.web3.eth.account.from_key(private_key)
        self.address = self.account.address
        
        # Set contract address
        self.contract_address = contract_address
        
        # Set lending pool address
        self.lending_pool_address = AAVE_LENDING_POOL_ADDRESSES.get(chain_name)
        if not self.lending_pool_address:
            raise ValueError(f"Lending pool address not found for chain {chain_name}")
        
        logger.info(f"Initialized FlashLoanService for chain {chain_name}")
    
    def execute_flash_loan(self, token_symbol, amount, dex1, dex2):
        """Execute a flash loan and arbitrage between two DEXes
        
        Args:
            token_symbol (str): Symbol of token to borrow (DAI, USDC, etc.)
            amount (float): Amount to borrow in token units
            dex1 (str): DEX to buy from
            dex2 (str): DEX to sell to
            
        Returns:
            dict: Transaction result
        """
        start_time = time.time()
        
        try:
            # Validate inputs
            if not self.contract_address:
                raise ValueError("Contract address not set. Deploy contract first.")
            
            token_address = TOKEN_ADDRESSES.get(self.chain_name, {}).get(token_symbol)
            if not token_address:
                raise ValueError(f"Token {token_symbol} not found for chain {self.chain_name}")
            
            # Load contract ABI (would be loaded from file in production)
            contract_abi = json.loads('''[
                {
                    "inputs": [
                        {"internalType": "address", "name": "token", "type": "address"},
                        {"internalType": "uint256", "name": "amount", "type": "uint256"},
                        {"internalType": "address", "name": "dex1", "type": "address"},
                        {"internalType": "address", "name": "dex2", "type": "address"}
                    ],
                    "name": "executeArbitrage",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                }
            ]''')
            
            # Load contract
            contract = self.web3.eth.contract(address=self.contract_address, abi=contract_abi)
            
            # Convert amount to wei
            token_decimals = 18  # Most ERC20 tokens use 18 decimals (would query this in production)
            amount_wei = int(amount * (10 ** token_decimals))
            
            # Estimate gas cost
            gas_price = self.web3.eth.gas_price
            
            # Build transaction
            tx = contract.functions.executeArbitrage(
                token_address,
                amount_wei,
                dex1,
                dex2
            ).build_transaction({
                'from': self.address,
                'gas': 3000000,  # Gas limit
                'gasPrice': gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.address)
            })
            
            # Sign transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
            
            # Send transaction
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for transaction receipt
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            # Calculate gas cost
            gas_used = receipt.gasUsed
            gas_cost_wei = gas_used * gas_price
            gas_cost_eth = self.web3.from_wei(gas_cost_wei, 'ether')
            gas_cost_usd = estimate_gas_cost_usd(self.chain_name, gas_cost_eth)
            
            # Check transaction status
            if receipt.status != 1:
                raise Exception("Transaction failed")
            
            # Calculate profit (would parse events from contract in production)
            # This is a placeholder - in reality you'd parse the profit from transaction logs
            profit = amount * 0.01  # Assuming 1% profit
            profit_usd = profit * 1500  # Assuming token price of $1500 (would query this in production)
            
            # Calculate net profit
            net_profit = profit_usd - gas_cost_usd
            
            # Create trade record
            trade = Trade(
                strategy_type="flash_loan",
                chain=self.chain_name,
                amount=amount,
                profit=profit_usd,
                gas_cost=gas_cost_usd,
                net_profit=net_profit,
                tx_hash=tx_hash.hex(),
                status="completed",
                execution_time=time.time() - start_time,
                details={
                    'token': token_symbol,
                    'dex1': dex1,
                    'dex2': dex2,
                    'gas_used': gas_used,
                    'gas_price': self.web3.from_wei(gas_price, 'gwei')
                }
            )
            
            # Save to database
            db.session.add(trade)
            db.session.commit()
            
            # Send telegram alert
            send_alert(f"✅ Flash Loan executed on {self.chain_name}. Profit: ${net_profit:.2f}")
            
            return {
                'success': True,
                'tx_hash': tx_hash.hex(),
                'profit': profit_usd,
                'gas_cost': gas_cost_usd,
                'net_profit': net_profit,
                'execution_time': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Flash loan execution failed: {str(e)}")
            
            # Create failed trade record
            trade = Trade(
                strategy_type="flash_loan",
                chain=self.chain_name,
                amount=amount,
                profit=0,
                gas_cost=0,
                net_profit=0,
                status="failed",
                execution_time=time.time() - start_time,
                details={
                    'token': token_symbol,
                    'dex1': dex1,
                    'dex2': dex2,
                    'error': str(e)
                }
            )
            
            # Save to database
            db.session.add(trade)
            db.session.commit()
            
            # Send telegram alert
            send_alert(f"❌ Flash Loan failed on {self.chain_name}: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    def deploy_contract(self, contract_bytecode):
        """Deploy flash loan contract
        
        Args:
            contract_bytecode (str): Contract bytecode
            
        Returns:
            str: Contract address if successful
        """
        try:
            # Create contract factory
            FlashYieldArb = self.web3.eth.contract(abi=[], bytecode=contract_bytecode)
            
            # Build constructor transaction
            construct_txn = FlashYieldArb.constructor(self.lending_pool_address).build_transaction({
                'from': self.address,
                'gas': 4000000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.address)
            })
            
            # Sign transaction
            signed_txn = self.web3.eth.account.sign_transaction(construct_txn, self.private_key)
            
            # Send transaction
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for transaction receipt
            tx_receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            
            # Check transaction status
            if tx_receipt.status != 1:
                raise Exception("Contract deployment failed")
            
            # Get contract address
            contract_address = tx_receipt.contractAddress
            
            # Set contract address
            self.contract_address = contract_address
            
            # Send telegram alert
            send_alert(f"✅ Flash Loan contract deployed on {self.chain_name}: {contract_address}")
            
            return contract_address
            
        except Exception as e:
            logger.error(f"Contract deployment failed: {str(e)}")
            
            # Send telegram alert
            send_alert(f"❌ Contract deployment failed on {self.chain_name}: {str(e)}")
            
            raise e