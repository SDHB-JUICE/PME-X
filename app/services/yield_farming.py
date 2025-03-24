"""
Yield Farming Service
Handles the execution of yield farming strategies across multiple EVM chains
"""
import time
import json
import logging
from datetime import datetime
from web3 import Web3
from app import db
from app.models.trade import YieldFarm
from app.models.wallet import ChainInfo
from app.services.telegram_alert import send_alert, send_yield_farm_alert
from app.utils.web3_helper import get_web3, estimate_gas_cost_usd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Protocol contract addresses (would be moved to config or database)
PROTOCOL_ADDRESSES = {
    'ethereum': {
        'yearn': {
            'vault_registry': '0x50c1a2eA0a861A967D9d0FFE2AE4012c2E053804',
            'vaults': {
                'usdc': '0x5f18C75AbDAe578b483E5F43f12a39cF75b973a9',
                'dai': '0xdA816459F1AB5631232FE5e97a05BBBb94970c95',
                'eth': '0xa258C4606Ca8206D8aA700cE2143D7db854D168c'
            }
        },
        'curve': {
            'registry': '0x90E00ACe148ca3b23Ac1bC8C240C2a7Dd9c2d7f5',
            'pools': {
                '3pool': '0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7',
                'steth': '0xDC24316b9AE028F1497c275EB9192a3Ea0f67022',
                'frax': '0xd632f22692FaC7611d2AA1C0D552930D43CAEd3B'
            }
        }
    },
    'polygon': {
        'beefy': {
            'vault_registry': '0xF0D415189949d913264A454F57c2285600aB5F9F',
            'vaults': {
                'usdc': '0x2F4CdEd612b2F8D9B5DbCc9cd7Cae0E756a1eED6',
                'matic': '0x7A25252c92cAA37F67F04fE9aFB9f9c77AA576B6'
            }
        },
        'curve': {
            'registry': '0x094d12e5b541784701FD8d65F11fc0598FBC6332',
            'pools': {
                'atricrypto': '0x1d8b86e3D88cDb2d34688e87E72F388Cb541B7C8',
                'aave': '0x445FE580eF8d70FF569aB36e80c647af338db351'
            }
        }
    }
    # Add more chains as needed
}

class YieldFarmingService:
    """Service for executing yield farming strategies"""
    
    def __init__(self, chain_name, private_key):
        """Initialize yield farming service
        
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
        
        # Get protocol addresses
        self.protocol_addresses = PROTOCOL_ADDRESSES.get(chain_name, {})
        if not self.protocol_addresses:
            raise ValueError(f"No protocol addresses found for chain {chain_name}")
        
        logger.info(f"Initialized YieldFarmingService for chain {chain_name}")
    
    def get_available_protocols(self):
        """Get available yield farming protocols for this chain
        
        Returns:
            dict: Available protocols and pools
        """
        return self.protocol_addresses
    
    def get_protocol_apy(self, protocol, pool):
        """Get current APY for protocol and pool
        
        Args:
            protocol (str): Protocol name (yearn, curve, beefy, etc.)
            pool (str): Pool name
            
        Returns:
            float: Current APY
        """
        # This is a placeholder - would fetch APY from on-chain or API
        # Mock APYs for demo purposes
        apy_mock = {
            'yearn': {
                'usdc': 5.8,
                'dai': 4.9,
                'eth': 3.2
            },
            'curve': {
                '3pool': 6.7,
                'steth': 8.2,
                'frax': 11.5,
                'atricrypto': 15.3,
                'aave': 5.2
            },
            'beefy': {
                'usdc': 9.4,
                'matic': 12.8
            }
        }
        
        return apy_mock.get(protocol, {}).get(pool, 0.0)
    
    def execute_deposit(self, protocol, pool, amount):
        """Deposit funds into yield farm
        
        Args:
            protocol (str): Protocol name (yearn, curve, beefy, etc.)
            pool (str): Pool name
            amount (float): Amount to deposit in USD
            
        Returns:
            dict: Transaction result
        """
        start_time = time.time()
        
        try:
            # Validate protocol and pool
            if protocol not in self.protocol_addresses:
                raise ValueError(f"Protocol {protocol} not available on chain {self.chain_name}")
            
            if pool not in self.protocol_addresses.get(protocol, {}).get('pools', {}):
                raise ValueError(f"Pool {pool} not available for protocol {protocol} on chain {self.chain_name}")
            
            # In a real implementation, you would:
            # 1. Convert amount to token amount
            # 2. Approve token spending
            # 3. Deposit into the vault/pool
            
            # For demo purposes, we'll simulate a successful deposit
            tx_hash = self.web3.keccak(text=f"yield_farm_deposit_{time.time()}").hex()
            
            # Estimate gas cost
            gas_price = self.web3.eth.gas_price
            gas_limit = 200000
            gas_cost_wei = gas_price * gas_limit
            gas_cost_eth = self.web3.from_wei(gas_cost_wei, 'ether')
            gas_cost_usd = estimate_gas_cost_usd(self.chain_name, gas_cost_eth)
            
            # Get APY
            apy = self.get_protocol_apy(protocol, pool)
            
            # Create yield farm record
            farm = YieldFarm(
                chain=self.chain_name,
                protocol=protocol,
                pool_name=pool,
                deposit_amount=amount,
                current_value=amount,  # Initially equal to deposit
                apy=apy,
                start_date=datetime.utcnow(),
                status="active",
                deposit_tx=tx_hash
            )
            
            # Save to database
            db.session.add(farm)
            db.session.commit()
            
            # Send telegram alert
            send_yield_farm_alert(farm, "deposit")
            
            return {
                'success': True,
                'farm_id': farm.id,
                'tx_hash': tx_hash,
                'gas_cost': gas_cost_usd,
                'apy': apy,
                'execution_time': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Yield farm deposit failed: {str(e)}")
            
            # Send telegram alert
            send_alert(f"❌ Yield Farm deposit failed on {self.chain_name}: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    def execute_harvest(self, farm_id):
        """Harvest rewards from yield farm
        
        Args:
            farm_id (int): ID of the yield farm
            
        Returns:
            dict: Transaction result
        """
        start_time = time.time()
        
        try:
            # Get farm from database
            farm = YieldFarm.query.get(farm_id)
            if not farm:
                raise ValueError(f"Farm with ID {farm_id} not found")
            
            if farm.status != "active":
                raise ValueError(f"Farm with ID {farm_id} is not active")
            
            # In a real implementation, you would:
            # 1. Claim rewards from the vault/pool
            # 2. Reinvest or convert rewards
            
            # For demo purposes, we'll simulate a successful harvest
            tx_hash = self.web3.keccak(text=f"yield_farm_harvest_{time.time()}").hex()
            
            # Estimate gas cost
            gas_price = self.web3.eth.gas_price
            gas_limit = 150000
            gas_cost_wei = gas_price * gas_limit
            gas_cost_eth = self.web3.from_wei(gas_cost_wei, 'ether')
            gas_cost_usd = estimate_gas_cost_usd(self.chain_name, gas_cost_eth)
            
            # Calculate current value (deposit + accrued interest)
            # In a real implementation, you would query the actual value from the contract
            time_elapsed = (datetime.utcnow() - farm.start_date).total_seconds() / (365 * 24 * 60 * 60)  # years
            interest = farm.deposit_amount * (farm.apy / 100) * time_elapsed
            current_value = farm.deposit_amount + interest
            
            # Update farm record
            farm.current_value = current_value
            farm.last_harvest = datetime.utcnow()
            farm.last_harvest_tx = tx_hash
            
            # Save to database
            db.session.commit()
            
            # Send telegram alert
            send_yield_farm_alert(farm, "harvest")
            
            return {
                'success': True,
                'farm_id': farm.id,
                'tx_hash': tx_hash,
                'gas_cost': gas_cost_usd,
                'current_value': current_value,
                'profit': current_value - farm.deposit_amount,
                'execution_time': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Yield farm harvest failed: {str(e)}")
            
            # Send telegram alert
            send_alert(f"❌ Yield Farm harvest failed on {self.chain_name}: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    def execute_withdraw(self, farm_id):
        """Withdraw funds from yield farm
        
        Args:
            farm_id (int): ID of the yield farm
            
        Returns:
            dict: Transaction result
        """
        start_time = time.time()
        
        try:
            # Get farm from database
            farm = YieldFarm.query.get(farm_id)
            if not farm:
                raise ValueError(f"Farm with ID {farm_id} not found")
            
            if farm.status != "active":
                raise ValueError(f"Farm with ID {farm_id} is not active")
            
            # In a real implementation, you would:
            # 1. Withdraw funds from the vault/pool
            # 2. Transfer tokens back to wallet
            
            # For demo purposes, we'll simulate a successful withdrawal
            tx_hash = self.web3.keccak(text=f"yield_farm_withdraw_{time.time()}").hex()
            
            # Estimate gas cost
            gas_price = self.web3.eth.gas_price
            gas_limit = 180000
            gas_cost_wei = gas_price * gas_limit
            gas_cost_eth = self.web3.from_wei(gas_cost_wei, 'ether')
            gas_cost_usd = estimate_gas_cost_usd(self.chain_name, gas_cost_eth)
            
            # Calculate current value (deposit + accrued interest)
            # In a real implementation, you would query the actual value from the contract
            time_elapsed = (datetime.utcnow() - farm.start_date).total_seconds() / (365 * 24 * 60 * 60)  # years
            interest = farm.deposit_amount * (farm.apy / 100) * time_elapsed
            current_value = farm.deposit_amount + interest
            
            # Update farm record
            farm.current_value = current_value
            farm.status = "closed"
            farm.withdraw_tx = tx_hash
            
            # Save to database
            db.session.commit()
            
            # Send telegram alert
            send_yield_farm_alert(farm, "withdraw")
            
            return {
                'success': True,
                'farm_id': farm.id,
                'tx_hash': tx_hash,
                'gas_cost': gas_cost_usd,
                'final_value': current_value,
                'profit': current_value - farm.deposit_amount,
                'execution_time': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Yield farm withdrawal failed: {str(e)}")
            
            # Send telegram alert
            send_alert(f"❌ Yield Farm withdrawal failed on {self.chain_name}: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }