"""
Web3 Helper Utilities
Common functions for interacting with Web3 and blockchain
"""
import json
import os
import requests
from web3 import Web3, HTTPProvider
from eth_account import Account
from app.models.wallet import ChainInfo

# Cache for Web3 instances
web3_cache = {}

def get_web3(rpc_url):
    """Get Web3 instance for given RPC URL
    
    Args:
        rpc_url (str): RPC URL
        
    Returns:
        Web3: Web3 instance
    """
    if rpc_url in web3_cache:
        return web3_cache[rpc_url]
    
    web3 = Web3(HTTPProvider(rpc_url))
    web3_cache[rpc_url] = web3
    return web3

def get_web3_for_chain(chain_name):
    """Get Web3 instance for given chain name
    
    Args:
        chain_name (str): Chain name
        
    Returns:
        Web3: Web3 instance
    """
    chain_info = ChainInfo.query.filter_by(name=chain_name).first()
    if not chain_info:
        raise ValueError(f"Chain {chain_name} not found in database")
    
    return get_web3(chain_info.rpc_url)

def generate_wallet():
    """Generate new Ethereum wallet
    
    Returns:
        tuple: (address, private_key)
    """
    account = Account.create()
    return account.address, account.key.hex()

def encrypt_private_key(private_key, password):
    """Encrypt a private key with a password"""
    # Ensure private key is properly formatted
    if private_key.startswith('0x'):
        # Remove 0x prefix if present
        private_key = private_key[2:]
    
    # Verify it's a valid hexadecimal string
    try:
        # Attempt to convert to bytes to validate
        private_key_bytes = bytes.fromhex(private_key)
        if len(private_key_bytes) != 32:
            raise ValueError("Private key must be 32 bytes (64 hex characters)")
    except ValueError:
        raise ValueError("Invalid private key format: must be a hexadecimal string")
    
    # For demonstration, using a simple encryption
    # In production, use a proper encryption library
    from cryptography.fernet import Fernet
    import base64
    import hashlib
    
    # Create a key from password
    key = hashlib.sha256(password.encode()).digest()
    key_base64 = base64.urlsafe_b64encode(key)
    
    # Encrypt
    cipher = Fernet(key_base64)
    encrypted = cipher.encrypt(private_key.encode())
    
    return encrypted.decode()
def decrypt_private_key(encrypted_key, password):
    """Decrypt an encrypted private key with the password"""
    from cryptography.fernet import Fernet
    import base64
    import hashlib
    
    # Create a key from password (must match encrypt_private_key)
    key = hashlib.sha256(password.encode()).digest()
    key_base64 = base64.urlsafe_b64encode(key)
    
    # Decrypt
    cipher = Fernet(key_base64)
    decrypted = cipher.decrypt(encrypted_key.encode())
    
    return decrypted.decode()

def load_contract(web3, address, abi_path):
    """Load contract
    
    Args:
        web3 (Web3): Web3 instance
        address (str): Contract address
        abi_path (str): Path to ABI JSON file
        
    Returns:
        Contract: Contract instance
    """
    with open(abi_path, 'r') as f:
        abi = json.load(f)
    
    return web3.eth.contract(address=address, abi=abi)

def estimate_gas_cost_usd(chain_name, gas_cost_eth):
    """Estimate gas cost in USD
    
    Args:
        chain_name (str): Chain name
        gas_cost_eth (float): Gas cost in ETH (or native token)
        
    Returns:
        float: Gas cost in USD
    """
    # In a real application, you would fetch the current price from an API
    # For demo purposes, we'll use hardcoded prices
    prices = {
        'ethereum': 3000,  # ETH price in USD
        'polygon': 1,      # MATIC price in USD
        'bsc': 300,        # BNB price in USD
        'avalanche': 30,   # AVAX price in USD
        'arbitrum-one': 3000,  # ETH price in USD
        'optimism': 3000,  # ETH price in USD
    }
    
    price = prices.get(chain_name, 1)
    return gas_cost_eth * price

def get_token_price(token_address, chain_name='ethereum'):
    """Get token price in USD
    
    Args:
        token_address (str): Token address
        chain_name (str): Chain name
        
    Returns:
        float: Token price in USD
    """
    # In a real application, you would fetch the price from an API like CoinGecko
    # For demo purposes, we'll return mock prices
    mock_prices = {
        '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2': 3000,  # WETH
        '0x6B175474E89094C44Da98b954EedeAC495271d0F': 1,     # DAI
        '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48': 1,     # USDC
        '0xdAC17F958D2ee523a2206206994597C13D831ec7': 1,     # USDT
    }
    
    return mock_prices.get(token_address.lower(), 1)

def get_token_balance(web3, token_address, wallet_address):
    """Get token balance
    
    Args:
        web3 (Web3): Web3 instance
        token_address (str): Token address
        wallet_address (str): Wallet address
        
    Returns:
        float: Token balance
    """
    # ERC20 ABI (only balanceOf function)
    abi = json.loads('''[
        {
            "constant": true,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function"
        },
        {
            "constant": true,
            "inputs": [],
            "name": "decimals",
            "outputs": [{"name": "", "type": "uint8"}],
            "type": "function"
        }
    ]''')
    
    # Load contract
    token = web3.eth.contract(address=token_address, abi=abi)
    
    # Get decimals
    decimals = token.functions.decimals().call()
    
    # Get balance
    balance_wei = token.functions.balanceOf(wallet_address).call()
    
    # Convert to token units
    balance = balance_wei / (10 ** decimals)
    
    return balance

def fetch_eth_gas_price():
    """Fetch current ETH gas price
    
    Returns:
        dict: Gas price information
    """
    try:
        response = requests.get('https://api.etherscan.io/api?module=gastracker&action=gasoracle')
        data = response.json()
        
        if data['status'] == '1':
            return {
                'low': int(data['result']['SafeGasPrice']),
                'average': int(data['result']['ProposeGasPrice']),
                'high': int(data['result']['FastGasPrice'])
            }
        else:
            # Fallback values
            return {
                'low': 20,
                'average': 40,
                'high': 60
            }
    except Exception:
        # Fallback values
        return {
            'low': 20,
            'average': 40,
            'high': 60
        }

def get_chain_explorer_url(chain_name, tx_hash=None):
    """Get explorer URL for chain
    
    Args:
        chain_name (str): Chain name
        tx_hash (str, optional): Transaction hash
        
    Returns:
        str: Explorer URL
    """
    explorers = {
        'ethereum': 'https://etherscan.io',
        'polygon': 'https://polygonscan.com',
        'bsc': 'https://bscscan.com',
        'avalanche': 'https://snowtrace.io',
        'arbitrum-one': 'https://arbiscan.io',
        'optimism': 'https://optimistic.etherscan.io',
        'fantom': 'https://ftmscan.com',
        'harmony': 'https://explorer.harmony.one',
        'celo': 'https://explorer.celo.org',
        'gnosis': 'https://gnosisscan.io',
    }
    
    base_url = explorers.get(chain_name, 'https://etherscan.io')
    
    if tx_hash:
        return f"{base_url}/tx/{tx_hash}"
    else:
        return base_url