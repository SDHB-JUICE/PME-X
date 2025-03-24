"""
ERC20 Token Deployer Service
Deploys custom ERC20 tokens to EVM chains
"""
import time
import json
import logging
from datetime import datetime
from web3 import Web3
from app import db
from app.models.trade import DeployedToken
from app.models.wallet import ChainInfo
from app.services.telegram_alert import send_alert, send_token_alert
from app.utils.web3_helper import get_web3, estimate_gas_cost_usd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DEX Factory Addresses (for listing tokens)
DEX_FACTORY_ADDRESSES = {
    'ethereum': {
        'uniswap': '0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f',
        'sushiswap': '0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac'
    },
    'polygon': {
        'quickswap': '0x5757371414417b8C6CAad45bAeF941aBc7d3Ab32',
        'sushiswap': '0xc35DADB65012eC5796536bD9864eD8773aBc74C4'
    },
    'bsc': {
        'pancakeswap': '0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73',
        'biswap': '0x858E3312ed3A876947EA49d572A7C42DE08af7EE'
    }
    # Add more chains as needed
}

# Sample ERC20 Token Contract (would be loaded from file in production)
ERC20_CONTRACT_BYTECODE = "0x60806040526012600360006101000a81548160ff021916908360ff16021790555034801561002c57600080fd5b5060405162001470380380620014708339818101604052810190610050919061017e565b81600090816200006191906102b0565b5080600190816200007291906102b0565b506200008a33600360009054906101000a900460ff1661009460201b60201c565b505061037d565b600073ffffffffffffffffffffffffffffffffffffffff168273ffffffffffffffffffffffffffffffffffffffff1603620000e7576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401620000de9061039a565b60405180910390fd5b620000fb60008383620001c060201b60201c565b8060026000828254620001109190610406565b9250508190555080600080848152602001908152602001600020600082825401925050819055508173ffffffffffffffffffffffffffffffffffffffff16600073ffffffffffffffffffffffffffffffffffffffff167fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef83604051620001989190610485565b60405180910390a3620001bc60008383620001c560201b60201c565b5050565b505050565b505050565b600080fd5b600080fd5b600080fd5b600080fd5b6000601f19601f8301169050919050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052604160045260246000fd5b6200022c82620001e1565b810181811067ffffffffffffffff821117156200024e576200024d620001f2565b5b80604052505050565b60006200026361016a565b9050620002718282620002... [truncated for brevity]"

class ERC20DeployerService:
    """Service for deploying ERC20 tokens"""
    
    def __init__(self, chain_name, private_key):
        """Initialize ERC20 deployer service
        
        Args:
            chain_name (str): Name of the chain (ethereum, polygon, etc.)
            private_key (str): Private key for transaction signing
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
        
        # Get DEX factory addresses
        self.dex_factories = DEX_FACTORY_ADDRESSES.get(chain_name, {})
        
        logger.info(f"Initialized ERC20DeployerService for chain {chain_name}")
    
    def deploy_token(self, name, symbol, total_supply, decimals=18, transfer_fee_percent=0, holder_rewards_percent=0):
        """Deploy ERC20 token
        
        Args:
            name (str): Token name
            symbol (str): Token symbol
            total_supply (float): Total supply of tokens
            decimals (int): Token decimals
            transfer_fee_percent (float): Fee percentage on transfers (0-10%)
            holder_rewards_percent (float): Rewards percentage for holders (0-100% of fees)
            
        Returns:
            dict: Transaction result
        """
        start_time = time.time()
        
        try:
            # Validate inputs
            if not name or not symbol:
                raise ValueError("Token name and symbol are required")
            
            if total_supply <= 0:
                raise ValueError("Total supply must be greater than zero")
            
            if transfer_fee_percent < 0 or transfer_fee_percent > 10:
                raise ValueError("Transfer fee percentage must be between 0 and 10")
            
            if holder_rewards_percent < 0 or holder_rewards_percent > 100:
                raise ValueError("Holder rewards percentage must be between 0 and 100")
            
            # In a real implementation, you would:
            # 1. Compile the contract (or use pre-compiled bytecode)
            # 2. Prepare constructor arguments
            # 3. Deploy the contract with the bytecode and arguments
            
            # For demo purposes, we'll simulate a successful deployment
            # This would be the actual deployment code with web3.py:
            """
            # Load contract ABI and bytecode
            contract_json = json.loads(open('contracts/ERC20Token.json').read())
            abi = contract_json['abi']
            bytecode = contract_json['bytecode']
            
            # Create contract factory
            Token = self.web3.eth.contract(abi=abi, bytecode=bytecode)
            
            # Prepare constructor arguments
            constructor_args = [name, symbol, self.web3.to_wei(total_supply, 'ether'), decimals, transfer_fee_percent, holder_rewards_percent]
            
            # Build deployment transaction
            tx = Token.constructor(*constructor_args).build_transaction({
                'from': self.address,
                'nonce': self.web3.eth.get_transaction_count(self.address),
                'gas': 4000000,
                'gasPrice': self.web3.eth.gas_price
            })
            
            # Sign and send transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for receipt
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            token_address = receipt.contractAddress
            """
            
            # Simulate deployment for demo
            tx_hash = self.web3.keccak(text=f"deploy_token_{time.time()}").hex()
            token_address = "0x" + self.web3.keccak(text=f"{name}_{symbol}_{time.time()}").hex()[2:42]
            
            # Estimate gas cost
            gas_price = self.web3.eth.gas_price
            gas_limit = 3000000  # Deploy contracts typically use more gas
            gas_cost_wei = gas_price * gas_limit
            gas_cost_eth = self.web3.from_wei(gas_cost_wei, 'ether')
            gas_cost_usd = estimate_gas_cost_usd(self.chain_name, gas_cost_eth)
            
            # Create token record
            token = DeployedToken(
                name=name,
                symbol=symbol,
                chain=self.chain_name,
                address=token_address,
                created_at=datetime.utcnow(),
                total_supply=total_supply,
                deploy_tx=tx_hash,
                listed_on={}  # Will be updated when listed on DEXes
            )
            
            # Save to database
            db.session.add(token)
            db.session.commit()
            
            # Send telegram alert
            send_token_alert(token)
            
            return {
                'success': True,
                'token_id': token.id,
                'address': token_address,
                'tx_hash': tx_hash,
                'gas_cost': gas_cost_usd,
                'execution_time': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Token deployment failed: {str(e)}")
            
            # Send telegram alert
            send_alert(f"❌ Token deployment failed on {self.chain_name}: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    def list_on_dex(self, token_id, dex_name, liquidity_amount, token_ratio):
        """List token on DEX
        
        Args:
            token_id (int): ID of the deployed token
            dex_name (str): Name of the DEX to list on
            liquidity_amount (float): Amount of base token (ETH, MATIC, etc.) to add as liquidity
            token_ratio (float): How many tokens per base token
            
        Returns:
            dict: Transaction result
        """
        start_time = time.time()
        
        try:
            # Get token from database
            token = DeployedToken.query.get(token_id)
            if not token:
                raise ValueError(f"Token with ID {token_id} not found")
            
            # Check if DEX is supported
            if dex_name not in self.dex_factories:
                raise ValueError(f"DEX {dex_name} not supported on chain {self.chain_name}")
            
            # In a real implementation, you would:
            # 1. Create liquidity pool on the DEX
            # 2. Add initial liquidity (base token + your token)
            
            # For demo purposes, we'll simulate a successful listing
            tx_hash = self.web3.keccak(text=f"list_token_{time.time()}").hex()
            
            # Estimate gas cost
            gas_price = self.web3.eth.gas_price
            gas_limit = 250000
            gas_cost_wei = gas_price * gas_limit
            gas_cost_eth = self.web3.from_wei(gas_cost_wei, 'ether')
            gas_cost_usd = estimate_gas_cost_usd(self.chain_name, gas_cost_eth)
            
            # Calculate token amount
            token_amount = liquidity_amount * token_ratio
            
            # Update token record
            if not token.listed_on:
                token.listed_on = {}
            
            token.listed_on[dex_name] = {
                'listed_at': datetime.utcnow().isoformat(),
                'tx_hash': tx_hash,
                'liquidity_amount': liquidity_amount,
                'token_amount': token_amount,
                'initial_price': 1 / token_ratio
            }
            
            # Calculate current price based on ratio
            token.current_price = 1 / token_ratio
            
            # Save to database
            db.session.commit()
            
            # Send telegram alert
            send_alert(f"🦄 Token {token.symbol} listed on {dex_name} ({self.chain_name}). " +
                      f"Initial price: ${token.current_price:.8f}")
            
            return {
                'success': True,
                'token_id': token.id,
                'dex': dex_name,
                'tx_hash': tx_hash,
                'gas_cost': gas_cost_usd,
                'execution_time': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Token listing failed: {str(e)}")
            
            # Send telegram alert
            send_alert(f"❌ Token listing failed on {self.chain_name}: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }