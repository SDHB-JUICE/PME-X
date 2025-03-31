"""
Transaction History Service
Service for wallet transaction history management
"""
import json
import requests
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from app import db
from app.models.wallet import Wallet, ChainInfo
from app.models.enhanced_token import Token, TokenTransaction
from app.utils.web3_helper import get_web3_for_chain, get_chain_explorer_url

class TransactionHistoryService:
    """Service for transaction history management"""
    
    def __init__(self, chain_name=None):
        """Initialize transaction history service
        
        Args:
            chain_name (str, optional): Chain name to use for operations
        """
        self.chain_name = chain_name
        self.web3 = None
        
        if chain_name:
            self.web3 = get_web3_for_chain(chain_name)
    
    def get_wallet_transactions(self, wallet_id, filter_options=None):
        """Get wallet transactions with filtering
        
        Args:
            wallet_id (int): Wallet ID
            filter_options (dict, optional): Filter options
                - token_id (int): Filter by token
                - tx_type (str): Filter by transaction type (send, receive, etc.)
                - start_date (datetime): Filter by start date
                - end_date (datetime): Filter by end date
                - status (str): Filter by status (confirmed, pending, failed)
                - page (int): Page number (default: 1)
                - per_page (int): Items per page (default: 20)
            
        Returns:
            dict: Paged transactions data
        """
        if not filter_options:
            filter_options = {}
        
        # Default pagination values
        page = filter_options.get('page', 1)
        per_page = filter_options.get('per_page', 20)
        
        # Build query
        query = TokenTransaction.query.filter_by(wallet_id=wallet_id)
        
        # Apply filters
        if 'token_id' in filter_options:
            query = query.filter_by(token_id=filter_options['token_id'])
        
        if 'tx_type' in filter_options:
            query = query.filter_by(tx_type=filter_options['tx_type'])
        
        if 'start_date' in filter_options:
            query = query.filter(TokenTransaction.timestamp >= filter_options['start_date'])
        
        if 'end_date' in filter_options:
            query = query.filter(TokenTransaction.timestamp <= filter_options['end_date'])
        
        if 'status' in filter_options:
            query = query.filter_by(status=filter_options['status'])
        
        # Get total count
        total = query.count()
        
        # Apply sorting (default: most recent first)
        query = query.order_by(TokenTransaction.timestamp.desc())
        
        # Apply pagination
        transactions = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Enhance transaction data
        tx_data = []
        for tx in transactions.items:
            # Get token information
            token = None
            if tx.token_id:
                token = Token.query.get(tx.token_id)
            
            # Format transaction data
            tx_dict = tx.to_dict()
            tx_dict['token'] = token.to_dict() if token else None
            tx_dict['explorer_url'] = get_chain_explorer_url(tx.chain, tx.tx_hash)
            tx_data.append(tx_dict)
        
        # Prepare result
        result = {
            'transactions': tx_data,
            'pagination': {
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page
            }
        }
        
        return result
    
    def sync_native_transactions(self, wallet_id, start_block=None):
        """Sync native currency transactions for wallet
        
        Args:
            wallet_id (int): Wallet ID
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
        
        # Determine start block
        if not start_block:
            # Get the latest transaction block number or use current block - 10000
            latest_tx = TokenTransaction.query.filter_by(
                wallet_id=wallet_id,
                token_id=None  # Native transactions don't have a token ID
            ).order_by(TokenTransaction.block_number.desc()).first()
            
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
            'transactions_found': 0,
            'transactions_added': 0,
            'blocks_scanned': end_block - start_block,
            'errors': []
        }
        
        # Get native transactions using etherscan-like API
        explorer_base_url = chain_info.explorer_url
        api_url = f"{explorer_base_url}/api?module=account&action=txlist&address={wallet.address}&startblock={start_block}&endblock={end_block}&sort=asc"
        
        try:
            # Make API request
            response = requests.get(api_url)
            if response.status_code != 200:
                results['errors'].append(f"Error fetching transactions: API request failed")
                return results
            
            # Parse response
            data = response.json()
            if data.get('status') != '1':
                results['errors'].append(f"Error fetching transactions: {data.get('message')}")
                return results
            
            # Process transactions
            transactions = data.get('result', [])
            results['transactions_found'] = len(transactions)
            
            for tx_data in transactions:
                try:
                    # Skip if transaction already exists
                    existing_tx = TokenTransaction.query.filter_by(tx_hash=tx_data.get('hash')).first()
                    if existing_tx:
                        continue
                    
                    # Process transaction
                    timestamp = datetime.fromtimestamp(int(tx_data.get('timeStamp')))
                    from_address = tx_data.get('from').lower()
                    to_address = tx_data.get('to', '').lower()  # 'to' can be None for contract creation
                    
                    # Determine transaction type
                    tx_type = 'unknown'
                    if from_address == wallet.address.lower():
                        if not to_address:
                            tx_type = 'contract_creation'
                        else:
                            tx_type = 'send'
                    elif to_address == wallet.address.lower():
                        tx_type = 'receive'
                    
                    # Calculate value
                    value_wei = int(tx_data.get('value', '0'))
                    value = web3.from_wei(value_wei, 'ether')
                    
                    # Calculate gas cost
                    gas_used = int(tx_data.get('gasUsed', '0'))
                    gas_price = int(tx_data.get('gasPrice', '0'))
                    gas_cost_eth = (gas_used * gas_price) / 1e18
                    
                    # Determine status
                    status = 'confirmed'
                    if tx_data.get('isError') == '1':
                        status = 'failed'
                        
                    # Calculate USD value (if available)
                    usd_value = None
                    if value > 0:
                        # In a real application, you would get the historical price
                        # For this example, we'll use a placeholder
                        usd_value = value * 1500  # Assuming a price of $1500 per ETH
                    
                    # Create transaction
                    new_tx = TokenTransaction(
                        wallet_id=wallet_id,
                        token_id=None,  # Native currency doesn't have a token ID
                        chain=wallet.chain,
                        tx_hash=tx_data.get('hash'),
                        block_number=int(tx_data.get('blockNumber')),
                        timestamp=timestamp,
                        from_address=from_address,
                        to_address=to_address or '',
                        amount=float(value),
                        usd_value=usd_value,
                        gas_used=gas_used,
                        gas_price=gas_price,
                        gas_cost_eth=gas_cost_eth,
                        gas_cost_usd=gas_cost_eth * 1500 if gas_cost_eth > 0 else None,  # Placeholder
                        tx_type=tx_type,
                        status=status,
                        error_message=tx_data.get('errCode'),
                        metadata={
                            'block_hash': tx_data.get('blockHash'),
                            'nonce': tx_data.get('nonce'),
                            'transaction_index': tx_data.get('transactionIndex'),
                            'input': tx_data.get('input'),
                            'confirmations': tx_data.get('confirmations')
                        }
                    )
                    
                    # Add transaction to database
                    db.session.add(new_tx)
                    results['transactions_added'] += 1
                except Exception as e:
                    results['errors'].append(f"Error processing transaction {tx_data.get('hash')}: {str(e)}")
            
            # Commit changes
            db.session.commit()
            
        except Exception as e:
            results['errors'].append(f"Error syncing native transactions: {str(e)}")
        
        return results
    
    def generate_transaction_summary(self, wallet_id, period='30d'):
        """Generate transaction summary for wallet
        
        Args:
            wallet_id (int): Wallet ID
            period (str): Time period ('24h', '7d', '30d', 'all')
            
        Returns:
            dict: Transaction summary
        """
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet with ID {wallet_id} not found")
        
        # Calculate start date based on period
        start_date = None
        if period == '24h':
            start_date = datetime.utcnow() - timedelta(days=1)
        elif period == '7d':
            start_date = datetime.utcnow() - timedelta(days=7)
        elif period == '30d':
            start_date = datetime.utcnow() - timedelta(days=30)
        
        # Base query for transactions
        query = TokenTransaction.query.filter_by(wallet_id=wallet_id)
        
        # Filter by start date if provided
        if start_date:
            query = query.filter(TokenTransaction.timestamp >= start_date)
        
        # Get all transactions for the period
        transactions = query.all()
        
        # Initialize summary
        summary = {
            'period': period,
            'total_transactions': len(transactions),
            'incoming_transactions': 0,
            'outgoing_transactions': 0,
            'total_received': 0,
            'total_sent': 0,
            'total_gas_spent': 0,
            'total_gas_spent_usd': 0,
            'most_active_tokens': [],
            'daily_activity': {},
            'hourly_gas_prices': {}
        }
        
        # Token activity tracking
        token_activity = {}
        
        # Process transactions
        for tx in transactions:
            # Update counts based on transaction type
            if tx.tx_type == 'receive':
                summary['incoming_transactions'] += 1
                summary['total_received'] += tx.usd_value or 0
            elif tx.tx_type == 'send':
                summary['outgoing_transactions'] += 1
                summary['total_sent'] += tx.usd_value or 0
            
            # Update gas spent (only for outgoing transactions)
            if tx.from_address.lower() == wallet.address.lower():
                summary['total_gas_spent'] += tx.gas_cost_eth or 0
                summary['total_gas_spent_usd'] += tx.gas_cost_usd or 0
            
            # Track token activity
            token_id = tx.token_id or 'native'
            if token_id not in token_activity:
                # Get token info
                token_name = 'Native Currency'
                token_symbol = wallet.chain_info.currency_symbol if hasattr(wallet, 'chain_info') else ''
                
                if tx.token_id:
                    token = Token.query.get(tx.token_id)
                    if token:
                        token_name = token.name
                        token_symbol = token.symbol
                
                token_activity[token_id] = {
                    'id': token_id,
                    'name': token_name,
                    'symbol': token_symbol,
                    'transaction_count': 0,
                    'total_volume': 0
                }
            
            token_activity[token_id]['transaction_count'] += 1
            token_activity[token_id]['total_volume'] += tx.usd_value or 0
            
            # Track daily activity
            day_str = tx.timestamp.strftime('%Y-%m-%d')
            if day_str not in summary['daily_activity']:
                summary['daily_activity'][day_str] = {
                    'date': day_str,
                    'transaction_count': 0,
                    'volume': 0,
                    'gas_spent': 0
                }
            
            summary['daily_activity'][day_str]['transaction_count'] += 1
            summary['daily_activity'][day_str]['volume'] += tx.usd_value or 0
            summary['daily_activity'][day_str]['gas_spent'] += tx.gas_cost_eth or 0
            
            # Track hourly gas prices
            hour_str = tx.timestamp.strftime('%H')
            if hour_str not in summary['hourly_gas_prices']:
                summary['hourly_gas_prices'][hour_str] = {
                    'hour': int(hour_str),
                    'avg_gas_price': 0,
                    'transaction_count': 0
                }
            
            if tx.gas_price:
                gas_price_gwei = tx.gas_price / 1e9
                current = summary['hourly_gas_prices'][hour_str]
                # Update average gas price
                current['avg_gas_price'] = (
                    (current['avg_gas_price'] * current['transaction_count'] + gas_price_gwei) / 
                    (current['transaction_count'] + 1)
                )
                current['transaction_count'] += 1
        
        # Sort token activity by transaction count
        top_tokens = sorted(
            token_activity.values(), 
            key=lambda x: x['transaction_count'], 
            reverse=True
        )[:10]  # Get top 10
        
        summary['most_active_tokens'] = top_tokens
        
        # Convert daily activity to list and sort by date
        summary['daily_activity'] = sorted(
            summary['daily_activity'].values(),
            key=lambda x: x['date']
        )
        
        # Convert hourly gas prices to list and sort by hour
        summary['hourly_gas_prices'] = sorted(
            summary['hourly_gas_prices'].values(),
            key=lambda x: x['hour']
        )
        
        return summary
    
    def get_gas_usage_analytics(self, wallet_id, period='30d'):
        """Get gas usage analytics for wallet
        
        Args:
            wallet_id (int): Wallet ID
            period (str): Time period ('24h', '7d', '30d', 'all')
            
        Returns:
            dict: Gas usage analytics
        """
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet with ID {wallet_id} not found")
        
        # Calculate start date based on period
        start_date = None
        if period == '24h':
            start_date = datetime.utcnow() - timedelta(days=1)
        elif period == '7d':
            start_date = datetime.utcnow() - timedelta(days=7)
        elif period == '30d':
            start_date = datetime.utcnow() - timedelta(days=30)
        
        # Base query for transactions (only outgoing transactions use gas)
        query = TokenTransaction.query.filter_by(
            wallet_id=wallet_id
        ).filter(
            TokenTransaction.from_address == wallet.address
        )
        
        # Filter by start date if provided
        if start_date:
            query = query.filter(TokenTransaction.timestamp >= start_date)
        
        # Get all transactions for the period
        transactions = query.all()
        
        # Initialize analytics
        analytics = {
            'period': period,
            'total_transactions': len(transactions),
            'total_gas_used': 0,
            'total_gas_cost_eth': 0,
            'total_gas_cost_usd': 0,
            'avg_gas_price_gwei': 0,
            'avg_gas_per_tx': 0,
            'highest_gas_tx': None,
            'lowest_gas_tx': None,
            'gas_by_token': {},
            'gas_price_over_time': [],
            'optimization_suggestions': []
        }
        
        if not transactions:
            return analytics
        
        # Process transactions
        highest_gas_cost = 0
        lowest_gas_cost = float('inf')
        highest_gas_tx = None
        lowest_gas_tx = None
        total_gas_price = 0
        gas_by_token = {}
        gas_price_over_time = []
        
        for tx in transactions:
            # Skip transactions with no gas data
            if not tx.gas_used or not tx.gas_price:
                continue
            
            # Update totals
            gas_cost_eth = tx.gas_cost_eth or 0
            gas_cost_usd = tx.gas_cost_usd or 0
            
            analytics['total_gas_used'] += tx.gas_used
            analytics['total_gas_cost_eth'] += gas_cost_eth
            analytics['total_gas_cost_usd'] += gas_cost_usd
            
            # Track gas price for average calculation
            total_gas_price += tx.gas_price
            
            # Track highest and lowest gas transactions
            if gas_cost_eth > highest_gas_cost:
                highest_gas_cost = gas_cost_eth
                highest_gas_tx = tx
            
            if gas_cost_eth < lowest_gas_cost and gas_cost_eth > 0:
                lowest_gas_cost = gas_cost_eth
                lowest_gas_tx = tx
            
            # Track gas by token
            token_id = tx.token_id or 'native'
            token_name = 'Native Currency'
            token_symbol = wallet.chain_info.currency_symbol if hasattr(wallet, 'chain_info') else ''
            
            if tx.token_id:
                token = Token.query.get(tx.token_id)
                if token:
                    token_name = token.name
                    token_symbol = token.symbol
            
            if token_id not in gas_by_token:
                gas_by_token[token_id] = {
                    'id': token_id,
                    'name': token_name,
                    'symbol': token_symbol,
                    'transaction_count': 0,
                    'total_gas_used': 0,
                    'total_gas_cost_eth': 0,
                    'avg_gas_per_tx': 0
                }
            
            gas_by_token[token_id]['transaction_count'] += 1
            gas_by_token[token_id]['total_gas_used'] += tx.gas_used
            gas_by_token[token_id]['total_gas_cost_eth'] += gas_cost_eth
            
            # Track gas price over time
            day_str = tx.timestamp.strftime('%Y-%m-%d')
            gas_price_over_time.append({
                'date': day_str,
                'gas_price_gwei': tx.gas_price / 1e9,
                'gas_used': tx.gas_used,
                'gas_cost_eth': gas_cost_eth
            })
        
        # Calculate averages
        if transactions:
            analytics['avg_gas_price_gwei'] = (total_gas_price / len(transactions)) / 1e9
            analytics['avg_gas_per_tx'] = analytics['total_gas_used'] / len(transactions)
        
        # Update token gas averages
        for token_id, token_data in gas_by_token.items():
            if token_data['transaction_count'] > 0:
                token_data['avg_gas_per_tx'] = token_data['total_gas_used'] / token_data['transaction_count']
        
        # Sort gas by token by total cost
        analytics['gas_by_token'] = sorted(
            gas_by_token.values(),
            key=lambda x: x['total_gas_cost_eth'],
            reverse=True
        )
        
        # Format highest and lowest gas transactions
        if highest_gas_tx:
            analytics['highest_gas_tx'] = {
                'tx_hash': highest_gas_tx.tx_hash,
                'timestamp': highest_gas_tx.timestamp.isoformat(),
                'gas_used': highest_gas_tx.gas_used,
                'gas_price_gwei': highest_gas_tx.gas_price / 1e9,
                'gas_cost_eth': highest_gas_tx.gas_cost_eth,
                'gas_cost_usd': highest_gas_tx.gas_cost_usd,
                'token': highest_gas_tx.token.symbol if highest_gas_tx.token else 'Native',
                'explorer_url': get_chain_explorer_url(highest_gas_tx.chain, highest_gas_tx.tx_hash)
            }
        
        if lowest_gas_tx:
            analytics['lowest_gas_tx'] = {
                'tx_hash': lowest_gas_tx.tx_hash,
                'timestamp': lowest_gas_tx.timestamp.isoformat(),
                'gas_used': lowest_gas_tx.gas_used,
                'gas_price_gwei': lowest_gas_tx.gas_price / 1e9,
                'gas_cost_eth': lowest_gas_tx.gas_cost_eth,
                'gas_cost_usd': lowest_gas_tx.gas_cost_usd,
                'token': lowest_gas_tx.token.symbol if lowest_gas_tx.token else 'Native',
                'explorer_url': get_chain_explorer_url(lowest_gas_tx.chain, lowest_gas_tx.tx_hash)
            }
        
        # Group gas price over time by day and calculate averages
        day_gas_prices = {}
        for entry in gas_price_over_time:
            day = entry['date']
            if day not in day_gas_prices:
                day_gas_prices[day] = {
                    'date': day,
                    'avg_gas_price_gwei': 0,
                    'total_gas_used': 0,
                    'total_gas_cost_eth': 0,
                    'transaction_count': 0
                }
            
            day_data = day_gas_prices[day]
            day_data['total_gas_used'] += entry['gas_used']
            day_data['total_gas_cost_eth'] += entry['gas_cost_eth']
            day_data['transaction_count'] += 1
            # Update average gas price
            day_data['avg_gas_price_gwei'] = (
                (day_data['avg_gas_price_gwei'] * (day_data['transaction_count'] - 1) + entry['gas_price_gwei']) /
                day_data['transaction_count']
            )
        
        # Convert to list and sort by date
        analytics['gas_price_over_time'] = sorted(
            day_gas_prices.values(),
            key=lambda x: x['date']
        )
        
        # Generate optimization suggestions
        self._generate_gas_optimization_suggestions(analytics)
        
        return analytics
    
    def _generate_gas_optimization_suggestions(self, analytics):
        """Generate gas optimization suggestions based on analytics
        
        Args:
            analytics (dict): Gas usage analytics
        """
        suggestions = []
        
        # Check if user is overpaying for gas
        if analytics['avg_gas_price_gwei'] > 40:
            suggestions.append({
                'title': 'Consider using lower gas price',
                'description': 'Your average gas price of {:.2f} Gwei is relatively high. Consider using a gas price estimator to avoid overpaying for transactions.'.format(
                    analytics['avg_gas_price_gwei']
                ),
                'potential_savings': 'Up to 30% on gas costs',
                'priority': 'high'
            })
        
        # Check if user has many small transactions
        if analytics['total_transactions'] > 20 and analytics['avg_gas_per_tx'] < 60000:
            suggestions.append({
                'title': 'Batch transactions',
                'description': 'You have many small transactions. Consider batching multiple operations into a single transaction to save on gas costs.',
                'potential_savings': 'Up to 40% on gas costs for multiple operations',
                'priority': 'medium'
            })
        
        # Check if user is transacting during high gas price times
        high_gas_times = []
        for entry in analytics['gas_price_over_time']:
            if entry['avg_gas_price_gwei'] > analytics['avg_gas_price_gwei'] * 1.2:
                high_gas_times.append(entry['date'])
        
        if high_gas_times:
            suggestions.append({
                'title': 'Avoid high gas price periods',
                'description': 'You tend to transact during periods of high gas prices (e.g., {}). Consider scheduling transactions during off-peak hours.'.format(
                    ', '.join(high_gas_times[:3])
                ),
                'potential_savings': 'Up to 50% on gas costs',
                'priority': 'medium'
            })
        
        # Check if user is using highly gas-intensive tokens/contracts
        gas_intensive_tokens = []
        for token_data in analytics['gas_by_token'][:3]:
            if token_data['avg_gas_per_tx'] > analytics['avg_gas_per_tx'] * 1.5:
                gas_intensive_tokens.append(token_data['symbol'] or token_data['name'])
        
        if gas_intensive_tokens:
            suggestions.append({
                'title': 'High gas usage for certain tokens',
                'description': 'Transactions involving {} use significantly more gas than average. Consider alternatives or timing these transactions during low gas periods.'.format(
                    ', '.join(gas_intensive_tokens)
                ),
                'potential_savings': 'Varies by token/contract',
                'priority': 'low'
            })
        
        # Check if gas costs represent a high percentage of transaction value
        # This would require analyzing transaction values, which we don't have in this function
        
        # Add general tips if no specific suggestions
        if not suggestions:
            suggestions.append({
                'title': 'Monitor gas prices',
                'description': 'Use gas price trackers to find optimal times for transactions. Gas prices are typically lower during weekends and off-peak hours.',
                'potential_savings': '10-30% on gas costs',
                'priority': 'low'
            })
        
        analytics['optimization_suggestions'] = suggestions
    
    def export_transactions_pdf(self, wallet_id, token_id=None, start_date=None, end_date=None):
        """Export token transactions to PDF
        
        Args:
            wallet_id (int): Wallet ID
            token_id (int, optional): Token ID
            start_date (datetime, optional): Start date
            end_date (datetime, optional): End date
            
        Returns:
            bytes: PDF data
        """
        # This is a simplified implementation
        # In a real application, you would use a PDF generation library like ReportLab or WeasyPrint
        # For this example, we'll return a placeholder
        
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
        
        # Get transaction count
        tx_count = query.count()
        
        # In a real implementation, you would generate a PDF file here
        # For this example, we'll just return a placeholder message
        pdf_data = f"Transaction report for wallet {wallet.address} with {tx_count} transactions."
        return pdf_data.encode('utf-8')
    
    def analyze_transaction_patterns(self, wallet_id, period='all'):
        """Analyze transaction patterns for wallet
        
        Args:
            wallet_id (int): Wallet ID
            period (str): Time period ('24h', '7d', '30d', 'all')
            
        Returns:
            dict: Transaction pattern analysis
        """
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet with ID {wallet_id} not found")
        
        # Calculate start date based on period
        start_date = None
        if period == '24h':
            start_date = datetime.utcnow() - timedelta(days=1)
        elif period == '7d':
            start_date = datetime.utcnow() - timedelta(days=7)
        elif period == '30d':
            start_date = datetime.utcnow() - timedelta(days=30)
        
        # Base query for transactions
        query = TokenTransaction.query.filter_by(wallet_id=wallet_id)
        
        # Filter by start date if provided
        if start_date:
            query = query.filter(TokenTransaction.timestamp >= start_date)
        
        # Get all transactions for the period
        transactions = query.all()
        
        # Initialize analysis
        analysis = {
            'period': period,
            'total_transactions': len(transactions),
            'transaction_types': {},
            'active_hours': {},
            'active_days': {},
            'recurring_patterns': [],
            'frequent_interactions': [],
            'patterns_by_token': {}
        }
        
        if not transactions:
            return analysis
        
        # Track transaction counts
        tx_types = {}
        active_hours = {str(i): 0 for i in range(24)}
        active_days = {'Mon': 0, 'Tue': 0, 'Wed': 0, 'Thu': 0, 'Fri': 0, 'Sat': 0, 'Sun': 0}
        interactions = {}
        token_patterns = {}
        
        # Process transactions
        for tx in transactions:
            # Track transaction types
            tx_type = tx.tx_type or 'unknown'
            if tx_type not in tx_types:
                tx_types[tx_type] = 0
            tx_types[tx_type] += 1
            
            # Track active hours
            hour = tx.timestamp.strftime('%H')
            active_hours[hour] += 1
            
            # Track active days
            day = tx.timestamp.strftime('%a')
            active_days[day] += 1
            
            # Track frequent interactions
            counterparty = None
            if tx.tx_type == 'send':
                counterparty = tx.to_address
            elif tx.tx_type == 'receive':
                counterparty = tx.from_address
            
            if counterparty:
                if counterparty not in interactions:
                    interactions[counterparty] = {
                        'address': counterparty,
                        'sent_count': 0,
                        'received_count': 0,
                        'total_sent': 0,
                        'total_received': 0
                    }
                
                if tx.tx_type == 'send':
                    interactions[counterparty]['sent_count'] += 1
                    interactions[counterparty]['total_sent'] += tx.amount or 0
                elif tx.tx_type == 'receive':
                    interactions[counterparty]['received_count'] += 1
                    interactions[counterparty]['total_received'] += tx.amount or 0
            
            # Track patterns by token
            token_id = tx.token_id or 'native'
            token_name = 'Native Currency'
            token_symbol = wallet.chain_info.currency_symbol if hasattr(wallet, 'chain_info') else ''
            
            if tx.token_id:
                token = Token.query.get(tx.token_id)
                if token:
                    token_name = token.name
                    token_symbol = token.symbol
            
            if token_id not in token_patterns:
                token_patterns[token_id] = {
                    'id': token_id,
                    'name': token_name,
                    'symbol': token_symbol,
                    'transaction_count': 0,
                    'sent_count': 0,
                    'received_count': 0,
                    'total_volume': 0,
                    'avg_transaction_size': 0
                }
            
            token_patterns[token_id]['transaction_count'] += 1
            token_patterns[token_id]['total_volume'] += tx.amount or 0
            
            if tx.tx_type == 'send':
                token_patterns[token_id]['sent_count'] += 1
            elif tx.tx_type == 'receive':
                token_patterns[token_id]['received_count'] += 1
        
        # Update token patterns with averages
        for token_id, pattern in token_patterns.items():
            if pattern['transaction_count'] > 0:
                pattern['avg_transaction_size'] = pattern['total_volume'] / pattern['transaction_count']
        
        # Format transaction types
        analysis['transaction_types'] = [
            {'type': tx_type, 'count': count}
            for tx_type, count in tx_types.items()
        ]
        
        # Format active hours
        analysis['active_hours'] = [
            {'hour': int(hour), 'count': count}
            for hour, count in active_hours.items()
        ]
        
        # Format active days
        analysis['active_days'] = [
            {'day': day, 'count': count}
            for day, count in active_days.items()
        ]
        
        # Get most frequent interactions
        frequent = sorted(
            interactions.values(),
            key=lambda x: x['sent_count'] + x['received_count'],
            reverse=True
        )[:10]  # Top 10
        
        analysis['frequent_interactions'] = frequent
        
        # Get patterns by token
        analysis['patterns_by_token'] = sorted(
            token_patterns.values(),
            key=lambda x: x['transaction_count'],
            reverse=True
        )
        
        # Detect recurring patterns
        recurring = []
        
        # Check for daily transactions
        if period == '30d' and len(transactions) >= 25:
            daily_counts = {}
            for tx in transactions:
                day_str = tx.timestamp.strftime('%Y-%m-%d')
                if day_str not in daily_counts:
                    daily_counts[day_str] = 0
                daily_counts[day_str] += 1
            
            # If transactions on 25+ days out of 30, likely daily activity
            if len(daily_counts) >= 25:
                recurring.append({
                    'pattern': 'daily',
                    'confidence': min(100, len(daily_counts) * 100 / 30),
                    'description': 'You appear to have daily transaction activity'
                })
        
        # Check for weekly patterns
        if period == '30d' and len(transactions) >= 4:
            weekly_count = 0
            for day, count in active_days.items():
                if count >= 4:  # Active on this day of week for 4+ weeks
                    weekly_count += 1
            
            if weekly_count > 0:
                recurring.append({
                    'pattern': 'weekly',
                    'confidence': min(100, weekly_count * 100 / 7),
                    'description': f'You appear to have regular weekly activity on {weekly_count} days of the week'
                })
        
        # Check for specific hour patterns
        if len(transactions) >= 10:
            hour_threshold = len(transactions) * 0.3  # 30% of transactions
            peak_hours = [int(h) for h, c in active_hours.items() if c >= hour_threshold]
            
            if peak_hours:
                recurring.append({
                    'pattern': 'time_of_day',
                    'confidence': 80,
                    'description': f'You tend to be most active during hours: {", ".join([str(h) for h in peak_hours])}'
                })
        
        analysis['recurring_patterns'] = recurring
        
        return analysis