"""
Token Discovery Service
Service for token discovery, management, and tracking
"""
import json
import requests
import time
from datetime import datetime, timedelta
from web3 import Web3
from eth_utils import is_address
from concurrent.futures import ThreadPoolExecutor
from app import db
from app.models.wallet import Wallet, ChainInfo
from app.models.enhanced_token import Token, TokenPriceHistory, TokenList, TokenTransaction
from app.utils.web3_helper import get_web3_for_chain, get_token_balance, get_token_price, get_chain_explorer_url

# Standard ERC20 Token ABI (minimal interface)
ERC20_ABI = json.loads('''[
    {"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"type":"function"},
    {"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"type":"function"},
    {"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},
    {"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}
]''')

# Cache for token info
token_info_cache = {}

class TokenDiscoveryService:
    """Service for token discovery and management"""
    
    def __init__(self, chain_name=None):
        """Initialize token discovery service
        
        Args:
            chain_name (str, optional): Chain name to use for operations
        """
        self.chain_name = chain_name
        self.web3 = None
        
        if chain_name:
            self.web3 = get_web3_for_chain(chain_name)
    
    def scan_wallet_for_tokens(self, wallet_address, max_tokens=100):
        """Scan a wallet for tokens using block explorer APIs
        
        Args:
            wallet_address (str): Wallet address to scan
            max_tokens (int, optional): Maximum number of tokens to return
            
        Returns:
            list: List of discovered tokens
        """
        if not self.chain_name:
            raise ValueError("Chain name not set")
        
        chain_info = ChainInfo.query.filter_by(name=self.chain_name).first()
        if not chain_info:
            raise ValueError(f"Chain {self.chain_name} not found")
        
        # Different chains have different APIs for token discovery
        # Here's a generic implementation that can be extended
        discovered_tokens = []
        
        # Try supported chain-specific APIs
        try:
            if self.chain_name.lower() == 'ethereum':
                # Etherscan API
                discovered_tokens = self._scan_etherscan(wallet_address, chain_info.explorer_url, max_tokens)
            elif self.chain_name.lower() == 'polygon':
                # Polygonscan API
                discovered_tokens = self._scan_etherscan(wallet_address, chain_info.explorer_url, max_tokens, 'polygonscan')
            elif self.chain_name.lower() == 'bsc':
                # BSCScan API
                discovered_tokens = self._scan_etherscan(wallet_address, chain_info.explorer_url, max_tokens, 'bscscan')
            # Add more chain-specific APIs as needed
            else:
                # Fallback to generic Etherscan-like API (many chains use this format)
                discovered_tokens = self._scan_etherscan(wallet_address, chain_info.explorer_url, max_tokens, 'generic')
        except Exception as e:
            print(f"Error scanning using explorer API: {str(e)}")
        
        # If no tokens found or API failed, try scanning using Covalent or similar
        if not discovered_tokens:
            try:
                discovered_tokens = self._scan_covalent(wallet_address, chain_info.chain_id, max_tokens)
            except Exception as e:
                print(f"Error scanning using Covalent API: {str(e)}")
        
        # As a last resort, try checking for tokens from known token lists
        if not discovered_tokens:
            discovered_tokens = self._check_common_tokens(wallet_address, max_tokens)
        
        return discovered_tokens
    
    def _scan_etherscan(self, wallet_address, explorer_url, max_tokens=100, explorer_type='etherscan'):
        """Scan wallet for tokens using Etherscan-like APIs
        
        Args:
            wallet_address (str): Wallet address to scan
            explorer_url (str): Explorer base URL
            max_tokens (int): Maximum number of tokens to return
            explorer_type (str): Type of explorer API
            
        Returns:
            list: List of discovered tokens
        """
        # This is a simplified implementation
        # In a real scenario, you'd need to handle API keys, rate limiting, etc.
        discovered_tokens = []
        
        # Form API URL
        api_url = None
        if explorer_type == 'etherscan':
            api_url = f"{explorer_url}/api?module=account&action=tokentx&address={wallet_address}&sort=desc&page=1&offset={max_tokens}"
        elif explorer_type in ['polygonscan', 'bscscan', 'generic']:
            api_url = f"{explorer_url}/api?module=account&action=tokentx&address={wallet_address}&sort=desc&page=1&offset={max_tokens}"
        
        if not api_url:
            return discovered_tokens
        
        # Make API request
        response = requests.get(api_url)
        if response.status_code != 200:
            return discovered_tokens
        
        # Parse response
        data = response.json()
        if data.get('status') != '1':
            return discovered_tokens
        
        # Extract unique tokens
        token_addresses = set()
        for tx in data.get('result', []):
            token_address = tx.get('contractAddress')
            if token_address and token_address not in token_addresses:
                token_addresses.add(token_address)
                
                # Basic token info from transaction data
                token_info = {
                    'address': token_address,
                    'name': tx.get('tokenName', ''),
                    'symbol': tx.get('tokenSymbol', ''),
                    'decimals': int(tx.get('tokenDecimal', 18)),
                    'chain': self.chain_name
                }
                
                # Get current balance
                try:
                    balance = get_token_balance(self.web3, token_address, wallet_address)
                    token_info['balance'] = balance
                except Exception as e:
                    print(f"Error getting token balance: {str(e)}")
                    token_info['balance'] = 0
                
                # Skip tokens with zero balance
                if token_info['balance'] > 0:
                    discovered_tokens.append(token_info)
        
        return discovered_tokens
    
    def _scan_covalent(self, wallet_address, chain_id, max_tokens=100):
        """Scan wallet for tokens using Covalent API
        
        Args:
            wallet_address (str): Wallet address to scan
            chain_id (int): Chain ID
            max_tokens (int): Maximum number of tokens to return
            
        Returns:
            list: List of discovered tokens
        """
        # This is a simplified implementation
        # In a real scenario, you'd need to handle API keys, rate limiting, etc.
        discovered_tokens = []
        
        # Covalent API URL
        api_url = f"https://api.covalenthq.com/v1/{chain_id}/address/{wallet_address}/balances_v2/"
        
        # Make API request (would need an API key in production)
        try:
            response = requests.get(api_url)
            if response.status_code != 200:
                return discovered_tokens
            
            # Parse response
            data = response.json()
            if not data.get('data'):
                return discovered_tokens
            
            # Extract token data
            for item in data['data'].get('items', [])[:max_tokens]:
                if item.get('type') == 'cryptocurrency' and float(item.get('balance', 0)) > 0:
                    token_info = {
                        'address': item.get('contract_address'),
                        'name': item.get('contract_name', ''),
                        'symbol': item.get('contract_ticker_symbol', ''),
                        'decimals': item.get('contract_decimals', 18),
                        'balance': float(item.get('balance', 0)) / (10 ** item.get('contract_decimals', 18)),
                        'chain': self.chain_name,
                        'logo_url': item.get('logo_url')
                    }
                    discovered_tokens.append(token_info)
        except Exception as e:
            print(f"Error scanning using Covalent API: {str(e)}")
        
        return discovered_tokens
    
    def _check_common_tokens(self, wallet_address, max_tokens=20):
        """Check balance of common tokens from token lists
        
        Args:
            wallet_address (str): Wallet address to check
            max_tokens (int): Maximum number of tokens to check
            
        Returns:
            list: List of tokens with non-zero balance
        """
        discovered_tokens = []
        
        # Get active token lists for the chain
        token_lists = TokenList.query.filter_by(chain=self.chain_name, is_active=True).all()
        if not token_lists:
            return discovered_tokens
        
        # Get token addresses from the lists
        token_addresses = []
        for token_list in token_lists:
            # In a real implementation, you'd retrieve token addresses from the token list
            # For this example, we'll assume the metadata contains token addresses
            addresses = token_list.metadata.get('token_addresses', [])
            token_addresses.extend(addresses[:max_tokens])
        
        # Check balance for each token
        for token_address in token_addresses:
            try:
                # Get token contract
                token_contract = self.web3.eth.contract(address=token_address, abi=ERC20_ABI)
                
                # Get token info
                name = token_contract.functions.name().call()
                symbol = token_contract.functions.symbol().call()
                decimals = token_contract.functions.decimals().call()
                
                # Get balance
                balance_wei = token_contract.functions.balanceOf(wallet_address).call()
                balance = balance_wei / (10 ** decimals)
                
                # Skip tokens with zero balance
                if balance > 0:
                    token_info = {
                        'address': token_address,
                        'name': name,
                        'symbol': symbol,
                        'decimals': decimals,
                        'balance': balance,
                        'chain': self.chain_name
                    }
                    discovered_tokens.append(token_info)
            except Exception as e:
                print(f"Error checking token {token_address}: {str(e)}")
        
        return discovered_tokens
    
    def add_discovered_tokens_to_wallet(self, wallet_id, discovered_tokens):
        """Add discovered tokens to wallet
        
        Args:
            wallet_id (int): Wallet ID
            discovered_tokens (list): List of discovered tokens
            
        Returns:
            list: List of added token IDs
        """
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet with ID {wallet_id} not found")
        
        # Get existing token addresses for the wallet
        existing_tokens = Token.query.filter_by(wallet_id=wallet_id).all()
        existing_addresses = [token.address.lower() for token in existing_tokens]
        
        # Process new tokens
        added_tokens = []
        for token_info in discovered_tokens:
            token_address = token_info.get('address').lower()
            
            # Skip if token already exists
            if token_address in existing_addresses:
                continue
            
            # Create new token
            new_token = Token(
                wallet_id=wallet_id,
                chain=wallet.chain,
                address=token_address,
                symbol=token_info.get('symbol', ''),
                name=token_info.get('name', ''),
                decimals=token_info.get('decimals', 18),
                balance=token_info.get('balance', 0),
                logo_url=token_info.get('logo_url'),
                token_list_source='discovery',
                last_updated=datetime.utcnow()
            )
            
            # Get token price and update USD value
            try:
                price = get_token_price(token_address, wallet.chain)
                new_token.current_price = price
                new_token.usd_value = new_token.balance * price
            except Exception as e:
                print(f"Error getting token price: {str(e)}")
            
            # Save token to database
            db.session.add(new_token)
            added_tokens.append(new_token)
        
        # Commit changes
        if added_tokens:
            db.session.commit()
        
        # Return added token IDs
        return [token.id for token in added_tokens]
    
    def refresh_token_balances(self, wallet_id):
        """Refresh token balances for wallet
        
        Args:
            wallet_id (int): Wallet ID
            
        Returns:
            dict: Updated token balances
        """
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet with ID {wallet_id} not found")
        
        # Get Web3 connection for the chain
        web3 = get_web3_for_chain(wallet.chain)
        
        # Get tokens for the wallet
        tokens = Token.query.filter_by(wallet_id=wallet_id).all()
        
        # Update token balances
        updated_tokens = {}
        for token in tokens:
            try:
                # Get current balance
                old_balance = token.balance
                new_balance = get_token_balance(web3, token.address, wallet.address)
                token.balance = new_balance
                
                # Get current token price and update USD value
                price = get_token_price(token.address, wallet.chain)
                token.current_price = price
                token.usd_value = new_balance * price
                
                # Calculate 24h change if we have price history
                yesterday = datetime.utcnow() - timedelta(days=1)
                price_history = TokenPriceHistory.query.filter(
                    TokenPriceHistory.token_id == token.id,
                    TokenPriceHistory.timestamp >= yesterday
                ).order_by(TokenPriceHistory.timestamp.asc()).first()
                
                if price_history:
                    old_price = price_history.price
                    if old_price > 0:
                        token.price_24h_change = ((price - old_price) / old_price) * 100
                
                # Update last updated timestamp
                token.last_updated = datetime.utcnow()
                
                # Add to updated tokens
                updated_tokens[token.id] = {
                    'old_balance': old_balance,
                    'new_balance': new_balance,
                    'difference': new_balance - old_balance,
                    'price': price,
                    'usd_value': new_balance * price
                }
            except Exception as e:
                print(f"Error updating token {token.symbol}: {str(e)}")
        
        # Save changes
        db.session.commit()
        
        return updated_tokens
    
    def add_custom_token(self, wallet_id, token_address, **kwargs):
        """Add custom token to wallet
        
        Args:
            wallet_id (int): Wallet ID
            token_address (str): Token address
            **kwargs: Additional token parameters
            
        Returns:
            Token: Added token
        """
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet with ID {wallet_id} not found")
        
        # Validate token address
        if not is_address(token_address):
            raise ValueError(f"Invalid token address: {token_address}")
        
        # Check if token already exists
        existing_token = Token.query.filter_by(wallet_id=wallet_id, address=token_address).first()
        if existing_token:
            return existing_token
        
        # Get Web3 connection for the chain
        web3 = get_web3_for_chain(wallet.chain)
        
        # Get token contract
        token_contract = web3.eth.contract(address=token_address, abi=ERC20_ABI)
        
        # Get token info
        try:
            name = kwargs.get('name') or token_contract.functions.name().call()
            symbol = kwargs.get('symbol') or token_contract.functions.symbol().call()
            decimals = kwargs.get('decimals') or token_contract.functions.decimals().call()
        except Exception as e:
            raise ValueError(f"Error getting token info: {str(e)}")
        
        # Get token balance
        try:
            balance_wei = token_contract.functions.balanceOf(wallet.address).call()
            balance = balance_wei / (10 ** decimals)
        except Exception as e:
            raise ValueError(f"Error getting token balance: {str(e)}")
        
        # Create new token
        new_token = Token(
            wallet_id=wallet_id,
            chain=wallet.chain,
            address=token_address,
            symbol=symbol,
            name=name,
            decimals=decimals,
            balance=balance,
            token_list_source='manual',
            last_updated=datetime.utcnow()
        )
        
        # Get token price and update USD value
        try:
            price = get_token_price(token_address, wallet.chain)
            new_token.current_price = price
            new_token.usd_value = balance * price
        except Exception as e:
            print(f"Error getting token price: {str(e)}")
        
        # Save token to database
        db.session.add(new_token)
        db.session.commit()
        
        return new_token
    
    def import_token_list(self, token_list_name, token_list_url, chain_name):
        """Import token list from URL
        
        Args:
            token_list_name (str): Token list name
            token_list_url (str): Token list URL
            chain_name (str): Chain name
            
        Returns:
            TokenList: Imported token list
        """
        # Get chain info
        chain_info = ChainInfo.query.filter_by(name=chain_name).first()
        if not chain_info:
            raise ValueError(f"Chain {chain_name} not found")
        
        # Fetch token list
        try:
            response = requests.get(token_list_url)
            if response.status_code != 200:
                raise ValueError(f"Failed to fetch token list: {response.status_code}")
            
            token_list_data = response.json()
        except Exception as e:
            raise ValueError(f"Error fetching token list: {str(e)}")
        
        # Extract tokens
        tokens = token_list_data.get('tokens', [])
        if not tokens:
            raise ValueError("No tokens found in the token list")
        
        # Filter tokens for the specified chain
        chain_tokens = []
        for token in tokens:
            token_chain_id = token.get('chainId')
            if token_chain_id == chain_info.chain_id:
                chain_tokens.append(token)
        
        if not chain_tokens:
            raise ValueError(f"No tokens found for chain ID {chain_info.chain_id}")
        
        # Create or update token list
        token_list = TokenList.query.filter_by(name=token_list_name, chain=chain_name).first()
        if not token_list:
            token_list = TokenList(
                name=token_list_name,
                source='url',
                chain=chain_name,
                tokens_count=len(chain_tokens),
                is_active=True,
                last_updated=datetime.utcnow(),
                metadata={
                    'url': token_list_url,
                    'token_addresses': [token.get('address') for token in chain_tokens]
                }
            )
            db.session.add(token_list)
        else:
            token_list.tokens_count = len(chain_tokens)
            token_list.last_updated = datetime.utcnow()
            token_list.metadata = {
                'url': token_list_url,
                'token_addresses': [token.get('address') for token in chain_tokens]
            }
        
        db.session.commit()
        
        return token_list
    
    def fetch_token_price_history(self, token_id, days=30):
        """Fetch price history for token
        
        Args:
            token_id (int): Token ID
            days (int): Number of days to fetch
            
        Returns:
            list: List of price points
        """
        token = Token.query.get(token_id)
        if not token:
            raise ValueError(f"Token with ID {token_id} not found")
        
        # Calculate start date
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Check if we have enough price history in the database
        existing_history = TokenPriceHistory.query.filter(
            TokenPriceHistory.token_id == token_id,
            TokenPriceHistory.timestamp >= start_date
        ).order_by(TokenPriceHistory.timestamp.asc()).all()
        
        # If we have enough data points, return them
        if len(existing_history) >= days / 2:
            # We have at least half the required data points, fill in the rest
            result = [history.to_dict() for history in existing_history]
            return result
        
        # If we don't have enough data, fetch from external API
        try:
            # In a real implementation, you'd use a price API like CoinGecko or similar
            # For this example, we'll simulate price history with random data
            price_history = self._fetch_price_history_from_api(token, days)
            
            # Save price history to database
            for price_point in price_history:
                # Check if we already have this timestamp
                existing = TokenPriceHistory.query.filter_by(
                    token_id=token_id,
                    timestamp=price_point['timestamp']
                ).first()
                
                if not existing:
                    new_price_history = TokenPriceHistory(
                        token_id=token_id,
                        timestamp=price_point['timestamp'],
                        price=price_point['price'],
                        volume_24h=price_point.get('volume_24h'),
                        market_cap=price_point.get('market_cap')
                    )
                    db.session.add(new_price_history)
            
            db.session.commit()
            
            # Fetch updated price history
            updated_history = TokenPriceHistory.query.filter(
                TokenPriceHistory.token_id == token_id,
                TokenPriceHistory.timestamp >= start_date
            ).order_by(TokenPriceHistory.timestamp.asc()).all()
            
            return [history.to_dict() for history in updated_history]
        except Exception as e:
            # If we can't fetch from API, return what we have
            return [history.to_dict() for history in existing_history]
    
    def _fetch_price_history_from_api(self, token, days):
        """Fetch token price history from API
        
        Args:
            token (Token): Token object
            days (int): Number of days to fetch
            
        Returns:
            list: List of price points
        """
        # In a real implementation, you'd use a price API like CoinGecko or similar
        # For this example, we'll simulate price history with random data
        import random
        
        price_history = []
        current_price = token.current_price or 1.0
        
        # Generate price history
        for i in range(days, -1, -1):
            date = datetime.utcnow() - timedelta(days=i)
            
            # Simulate price variation (up to ±5% per day)
            variation = (random.random() - 0.5) * 0.1
            if i < days:
                # Use previous day's price as reference
                price = price_history[-1]['price'] * (1 + variation)
            else:
                # First day, use current price as reference
                price = current_price * (1 + variation)
            
            # Ensure price is not negative
            price = max(0.000001, price)
            
            # Simulate volume and market cap
            volume_24h = price * random.uniform(1000, 100000)
            market_cap = price * random.uniform(10000, 10000000)
            
            price_point = {
                'timestamp': date,
                'price': price,
                'volume_24h': volume_24h,
                'market_cap': market_cap
            }
            
            price_history.append(price_point)
        
        return price_history
    
    def get_token_analytics(self, token_id):
        """Get detailed analytics for token
        
        Args:
            token_id (int): Token ID
            
        Returns:
            dict: Token analytics
        """
        token = Token.query.get(token_id)
        if not token:
            raise ValueError(f"Token with ID {token_id} not found")
        
        # Get price history for the last 30 days
        price_history = self.fetch_token_price_history(token_id, 30)
        
        # Calculate metrics
        metrics = self._calculate_token_metrics(token, price_history)
        
        # Get token transactions
        transactions = TokenTransaction.query.filter_by(token_id=token_id).order_by(
            TokenTransaction.timestamp.desc()
        ).limit(10).all()
        
        # Prepare result
        result = {
            'token': token.to_dict(),
            'metrics': metrics,
            'price_history': price_history,
            'recent_transactions': [tx.to_dict() for tx in transactions]
        }
        
        return result
    
    def _calculate_token_metrics(self, token, price_history):
        """Calculate token metrics
        
        Args:
            token (Token): Token object
            price_history (list): List of price points
            
        Returns:
            dict: Token metrics
        """
        if not price_history:
            return {}
        
        # Calculate price metrics
        current_price = token.current_price or 0
        
        # Calculate ATH (All-Time High)
        ath = token.all_time_high or 0
        for point in price_history:
            if point['price'] > ath:
                ath = point['price']
                ath_date = datetime.fromisoformat(point['timestamp'])
        
        if ath > token.all_time_high:
            token.all_time_high = ath
            token.all_time_high_date = ath_date
            db.session.commit()
        
        # Calculate 7d change
        price_7d_ago = None
        for point in price_history:
            date = datetime.fromisoformat(point['timestamp'])
            if datetime.utcnow() - date < timedelta(days=8):
                price_7d_ago = point['price']
                break
        
        price_7d_change = 0
        if price_7d_ago and price_7d_ago > 0:
            price_7d_change = ((current_price - price_7d_ago) / price_7d_ago) * 100
        
        # Calculate 30d change
        price_30d_ago = None
        if price_history:
            price_30d_ago = price_history[0]['price']
        
        price_30d_change = 0
        if price_30d_ago and price_30d_ago > 0:
            price_30d_change = ((current_price - price_30d_ago) / price_30d_ago) * 100
        
        # Calculate volatility (standard deviation of daily returns)
        returns = []
        for i in range(1, len(price_history)):
            prev_price = price_history[i-1]['price']
            curr_price = price_history[i]['price']
            if prev_price > 0:
                daily_return = (curr_price - prev_price) / prev_price
                returns.append(daily_return)
        
        volatility = 0
        if returns:
            import numpy as np
            volatility = np.std(returns) * 100  # Convert to percentage
        
        # Calculate trading volume (avg over the last 7 days)
        recent_volumes = [point.get('volume_24h', 0) for point in price_history[-7:]]
        avg_volume = sum(recent_volumes) / len(recent_volumes) if recent_volumes else 0
        
        # Prepare metrics
        metrics = {
            'current_price': current_price,
            'price_24h_change': token.price_24h_change,
            'price_7d_change': price_7d_change,
            'price_30d_change': price_30d_change,
            'all_time_high': ath,
            'all_time_high_date': token.all_time_high_date.isoformat() if token.all_time_high_date else None,
            'all_time_high_change': ((current_price - ath) / ath) * 100 if ath > 0 else 0,
            'volatility_30d': volatility,
            'avg_volume_7d': avg_volume
        }
        
        return metrics
    
    def fetch_token_transactions(self, wallet_id, token_address=None, page=1, per_page=20):
        """Fetch token transactions for wallet
        
        Args:
            wallet_id (int): Wallet ID
            token_address (str, optional): Token address
            page (int): Page number
            per_page (int): Number of items per page
            
        Returns:
            dict: Paged transactions
        """
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet with ID {wallet_id} not found")
        
        # Build query
        query = TokenTransaction.query.filter_by(wallet_id=wallet_id)
        
        # Filter by token address if provided
        if token_address:
            # Get token ID
            token = Token.query.filter_by(wallet_id=wallet_id, address=token_address).first()
            if token:
                query = query.filter_by(token_id=token.id)
        
        # Get total count
        total = query.count()
        
        # Get paginated transactions
        transactions = query.order_by(TokenTransaction.timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Prepare result
        result = {
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page,
            'transactions': [tx.to_dict() for tx in transactions.items]
        }
        
        return result
    
    def sync_token_transactions(self, wallet_id, token_id=None, start_block=None):
        """Sync token transactions for wallet
        
        Args:
            wallet_id (int): Wallet ID
            token_id (int, optional): Token ID
            start_block (int, optional): Starting block number
            
        Returns:
            dict: Sync results
        """
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet with ID {wallet_id} not found")
        
        # Get Web3 connection for the chain
        web3 = get_web3_for_chain(wallet.chain)
        
        # Get chain info
        chain_info = ChainInfo.query.filter_by(name=wallet.chain).first()
        if not chain_info:
            raise ValueError(f"Chain {wallet.chain} not found")
        
        # Determine tokens to sync
        tokens_to_sync = []
        if token_id:
            # Sync specific token
            token = Token.query.get(token_id)
            if not token or token.wallet_id != wallet_id:
                raise ValueError(f"Token with ID {token_id} not found for wallet")
            tokens_to_sync.append(token)
        else:
            # Sync all tokens for wallet
            tokens_to_sync = Token.query.filter_by(wallet_id=wallet_id).all()
        
        # Determine start block
        if not start_block:
            # Get the latest transaction block number or use current block - 10000
            latest_tx = TokenTransaction.query.filter_by(wallet_id=wallet_id).order_by(
                TokenTransaction.block_number.desc()
            ).first()
            
            if latest_tx:
                start_block = latest_tx.block_number
            else:
                # Use current block - 10000 (approximately 1-2 days of blocks)
                current_block = web3.eth.block_number
                start_block = max(0, current_block - 10000)
        
        # Current block
        end_block = web3.eth.block_number
        
        # Sync results
        results = {
            'tokens_synced': 0,
            'transactions_found': 0,
            'transactions_added': 0,
            'blocks_scanned': end_block - start_block,
            'errors': []
        }
        
        # Sync token transactions
        for token in tokens_to_sync:
            try:
                # Get token transactions using etherscan-like API
                explorer_base_url = chain_info.explorer_url
                api_url = f"{explorer_base_url}/api?module=account&action=tokentx&address={wallet.address}&contractaddress={token.address}&startblock={start_block}&endblock={end_block}&sort=asc"
                
                # Make API request
                response = requests.get(api_url)
                if response.status_code != 200:
                    results['errors'].append(f"Error fetching transactions for token {token.symbol}: API request failed")
                    continue
                
                # Parse response
                data = response.json()
                if data.get('status') != '1':
                    results['errors'].append(f"Error fetching transactions for token {token.symbol}: {data.get('message')}")
                    continue
                
                # Process transactions
                transactions = data.get('result', [])
                results['transactions_found'] += len(transactions)
                
                for tx_data in transactions:
                    try:
                        # Skip if transaction already exists
                        existing_tx = TokenTransaction.query.filter_by(tx_hash=tx_data.get('hash')).first()
                        if existing_tx:
                            continue
                        
                        # Process transaction
                        timestamp = datetime.fromtimestamp(int(tx_data.get('timeStamp')))
                        from_address = tx_data.get('from').lower()
                        to_address = tx_data.get('to').lower()
                        
                        # Determine transaction type
                        tx_type = 'unknown'
                        if from_address == wallet.address.lower():
                            tx_type = 'send'
                        elif to_address == wallet.address.lower():
                            tx_type = 'receive'
                        
                        # Calculate value
                        value_wei = int(tx_data.get('value', '0'))
                        value = value_wei / (10 ** int(tx_data.get('tokenDecimal', '18')))
                        
                        # Calculate gas cost
                        gas_used = int(tx_data.get('gasUsed', '0'))
                        gas_price = int(tx_data.get('gasPrice', '0'))
                        gas_cost_eth = (gas_used * gas_price) / 1e18
                        
                        # Create transaction
                        new_tx = TokenTransaction(
                            wallet_id=wallet_id,
                            token_id=token.id,
                            chain=wallet.chain,
                            tx_hash=tx_data.get('hash'),
                            block_number=int(tx_data.get('blockNumber')),
                            timestamp=timestamp,
                            from_address=from_address,
                            to_address=to_address,
                            amount=value,
                            gas_used=gas_used,
                            gas_price=gas_price,
                            gas_cost_eth=gas_cost_eth,
                            tx_type=tx_type,
                            status='confirmed',
                            metadata={
                                'block_hash': tx_data.get('blockHash'),
                                'token_name': tx_data.get('tokenName'),
                                'token_symbol': tx_data.get('tokenSymbol')
                            }
                        )
                        
                        # Add transaction to database
                        db.session.add(new_tx)
                        results['transactions_added'] += 1
                    except Exception as e:
                        results['errors'].append(f"Error processing transaction {tx_data.get('hash')}: {str(e)}")
                
                # Mark token as synced
                results['tokens_synced'] += 1
            except Exception as e:
                results['errors'].append(f"Error syncing token {token.symbol}: {str(e)}")
        
        # Commit changes
        db.session.commit()
        
        return results
    
    def export_transactions_csv(self, wallet_id, token_id=None, start_date=None, end_date=None):
        """Export token transactions to CSV
        
        Args:
            wallet_id (int): Wallet ID
            token_id (int, optional): Token ID
            start_date (datetime, optional): Start date
            end_date (datetime, optional): End date
            
        Returns:
            str: CSV data
        """
        import csv
        import io
        
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet with ID {wallet_id} not found")
        
        # Build query
        query = TokenTransaction.query.filter_by(wallet_id=wallet_id)
        
        # Filter by token
        if token_id:
            query = query.filter_by(token_id=token_id)
        
        # Filter by date range
        if start_date:
            query = query.filter(TokenTransaction.timestamp >= start_date)
        if end_date:
            query = query.filter(TokenTransaction.timestamp <= end_date)
        
        # Get transactions ordered by date
        transactions = query.order_by(TokenTransaction.timestamp.desc()).all()
        
        # Prepare CSV data
        output = io.StringIO()
        csv_writer = csv.writer(output)
        
        # Write header
        csv_writer.writerow([
            'Date', 'Type', 'Token', 'Amount', 'From', 'To', 'Hash', 
            'Gas Used', 'Gas Price (Gwei)', 'Gas Cost', 'Status'
        ])
        
        # Write transactions
        for tx in transactions:
            # Get token symbol
            token_symbol = 'Unknown'
            if tx.token:
                token_symbol = tx.token.symbol
            
            # Format row
            row = [
                tx.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                tx.tx_type.capitalize(),
                token_symbol,
                f"{tx.amount:.8f}",
                tx.from_address,
                tx.to_address,
                tx.tx_hash,
                tx.gas_used,
                f"{tx.gas_price / 1e9:.2f}",
                f"{tx.gas_cost_eth:.6f}",
                tx.status.capitalize()
            ]
            
            csv_writer.writerow(row)
        
        return output.getvalue()
    
    def get_token_performance(self, wallet_id, period='all'):
        """Get token performance for wallet
        
        Args:
            wallet_id (int): Wallet ID
            period (str): Time period ('24h', '7d', '30d', 'all')
            
        Returns:
            dict: Token performance data
        """
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet with ID {wallet_id} not found")
        
        # Get all tokens for wallet
        tokens = Token.query.filter_by(wallet_id=wallet_id).all()
        
        # Calculate start date based on period
        start_date = None
        if period == '24h':
            start_date = datetime.utcnow() - timedelta(days=1)
        elif period == '7d':
            start_date = datetime.utcnow() - timedelta(days=7)
        elif period == '30d':
            start_date = datetime.utcnow() - timedelta(days=30)
        
        # Prepare performance data
        performance = {
            'total_value': 0,
            'total_value_change': 0,
            'total_value_change_percent': 0,
            'tokens': []
        }
        
        # Process each token
        for token in tokens:
            # Skip tokens with no value
            if token.balance <= 0 or token.usd_value <= 0:
                continue
            
            # Get price history
            price_history = None
            if start_date:
                price_history = TokenPriceHistory.query.filter(
                    TokenPriceHistory.token_id == token.id,
                    TokenPriceHistory.timestamp >= start_date
                ).order_by(TokenPriceHistory.timestamp.asc()).first()
            
            # Calculate value change
            value_change = 0
            value_change_percent = 0
            
            if price_history:
                old_price = price_history.price
                old_value = token.balance * old_price
                
                value_change = token.usd_value - old_value
                if old_value > 0:
                    value_change_percent = (value_change / old_value) * 100
            
            # Add to total value
            performance['total_value'] += token.usd_value
            performance['total_value_change'] += value_change
            
            # Add token performance
            token_performance = {
                'id': token.id,
                'symbol': token.symbol,
                'name': token.name,
                'logo_url': token.logo_url,
                'balance': token.balance,
                'price': token.current_price,
                'price_change_percent': token.price_24h_change,
                'value': token.usd_value,
                'value_change': value_change,
                'value_change_percent': value_change_percent,
                'percentage_of_portfolio': 0  # Will be calculated after totals
            }
            
            performance['tokens'].append(token_performance)
        
        # Calculate percentage of portfolio for each token
        if performance['total_value'] > 0:
            for token_performance in performance['tokens']:
                token_performance['percentage_of_portfolio'] = (token_performance['value'] / performance['total_value']) * 100
            
            # Calculate total percentage change
            if performance['total_value'] - performance['total_value_change'] > 0:
                performance['total_value_change_percent'] = (
                    performance['total_value_change'] / 
                    (performance['total_value'] - performance['total_value_change'])
                ) * 100
        
        # Sort tokens by value (descending)
        performance['tokens'].sort(key=lambda x: x['value'], reverse=True)
        
        return performance