"""
Balance Analytics Service
Service for wallet balance analytics and portfolio management
"""
import json
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd
import numpy as np
from app import db
from app.models.wallet import Wallet, ChainInfo
from app.models.enhanced_token import Token, TokenPriceHistory, TokenTransaction
from app.utils.web3_helper import get_web3_for_chain, get_token_price

class BalanceAnalyticsService:
    """Service for wallet balance analytics"""
    
    def __init__(self, user_id=None):
        """Initialize balance analytics service
        
        Args:
            user_id (int, optional): User ID
        """
        self.user_id = user_id
    
    def track_balance_history(self, wallet_id):
        """Track balance history for a wallet
        
        Args:
            wallet_id (int): Wallet ID
            
        Returns:
            dict: Updated balance history entry
        """
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet with ID {wallet_id} not found")
        
        # Get current balances
        native_balance = wallet.native_balance
        usd_balance = wallet.usd_balance
        
        # Get token balances
        tokens = Token.query.filter_by(wallet_id=wallet_id).all()
        token_balances = {token.id: token.balance for token in tokens}
        token_usd_values = {token.id: token.usd_value for token in tokens}
        
        # Create balance history entry
        from app.models.balance_history import WalletBalanceHistory
        
        # Check if we already have an entry for today
        today = datetime.utcnow().date()
        existing_entry = WalletBalanceHistory.query.filter(
            WalletBalanceHistory.wallet_id == wallet_id,
            WalletBalanceHistory.date == today
        ).first()
        
        if existing_entry:
            # Update existing entry
            existing_entry.native_balance = native_balance
            existing_entry.usd_balance = usd_balance
            existing_entry.token_balances = token_balances
            existing_entry.token_usd_values = token_usd_values
            existing_entry.last_updated = datetime.utcnow()
            
            db.session.commit()
            return existing_entry.to_dict()
        else:
            # Create new entry
            new_entry = WalletBalanceHistory(
                wallet_id=wallet_id,
                date=today,
                native_balance=native_balance,
                usd_balance=usd_balance,
                token_balances=token_balances,
                token_usd_values=token_usd_values,
                last_updated=datetime.utcnow()
            )
            
            db.session.add(new_entry)
            db.session.commit()
            return new_entry.to_dict()
    
    def get_balance_history(self, wallet_id, days=30):
        """Get balance history for a wallet
        
        Args:
            wallet_id (int): Wallet ID
            days (int): Number of days of history
            
        Returns:
            list: Balance history entries
        """
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet with ID {wallet_id} not found")
        
        # Calculate start date
        start_date = datetime.utcnow().date() - timedelta(days=days)
        
        # Get balance history entries
        from app.models.balance_history import WalletBalanceHistory
        history_entries = WalletBalanceHistory.query.filter(
            WalletBalanceHistory.wallet_id == wallet_id,
            WalletBalanceHistory.date >= start_date
        ).order_by(WalletBalanceHistory.date.asc()).all()
        
        # Convert to dictionaries
        history = [entry.to_dict() for entry in history_entries]
        
        # Fill in missing dates with estimated values
        filled_history = self._fill_missing_dates(history, days)
        
        return filled_history
    
    def _fill_missing_dates(self, history, days):
        """Fill in missing dates in balance history
        
        Args:
            history (list): Original balance history
            days (int): Total days to cover
            
        Returns:
            list: Filled balance history
        """
        if not history:
            return []
        
        # Create a date range
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        date_range = [start_date + timedelta(days=i) for i in range(days + 1)]
        
        # Create a map of existing entries
        history_map = {entry['date']: entry for entry in history}
        
        # Fill in missing dates
        filled_history = []
        prev_entry = None
        
        for date in date_range:
            date_str = date.isoformat()
            
            if date_str in history_map:
                # Use existing entry
                entry = history_map[date_str]
                prev_entry = entry
            elif prev_entry:
                # Estimate based on previous entry
                entry = prev_entry.copy()
                entry['date'] = date_str
                entry['estimated'] = True
            else:
                # Skip if we don't have a previous entry to base estimation on
                continue
            
            filled_history.append(entry)
        
        return filled_history
    
    def get_portfolio_composition(self, wallet_ids, include_zero_balances=False):
        """Get portfolio composition across multiple wallets
        
        Args:
            wallet_ids (list): List of wallet IDs
            include_zero_balances (bool): Include tokens with zero balance
            
        Returns:
            dict: Portfolio composition data
        """
        if not wallet_ids:
            raise ValueError("At least one wallet ID is required")
        
        # Get wallets
        wallets = Wallet.query.filter(Wallet.id.in_(wallet_ids)).all()
        if not wallets:
            raise ValueError("No valid wallets found")
        
        # Initialize portfolio data
        portfolio = {
            'total_value_usd': 0,
            'assets': [],
            'by_chain': {},
            'by_wallet': {},
            'composition': []
        }
        
        # Process each wallet
        for wallet in wallets:
            wallet_data = {
                'id': wallet.id,
                'address': wallet.address,
                'chain': wallet.chain,
                'native_balance': wallet.native_balance,
                'usd_balance': wallet.usd_balance,
                'tokens': []
            }
            
            # Add native currency as an asset
            native_asset = {
                'type': 'native',
                'chain': wallet.chain,
                'symbol': 'ETH',  # Default, should be replaced with actual symbol
                'balance': wallet.native_balance,
                'usd_value': wallet.usd_balance
            }
            
            # Try to get the actual symbol
            chain_info = ChainInfo.query.filter_by(name=wallet.chain).first()
            if chain_info:
                native_asset['symbol'] = chain_info.currency_symbol
            
            # Add to wallet data if balance > 0 or include_zero_balances is True
            if native_asset['balance'] > 0 or include_zero_balances:
                wallet_data['tokens'].append(native_asset)
            
            # Update portfolio total
            portfolio['total_value_usd'] += wallet.usd_balance
            
            # Update chain data
            if wallet.chain not in portfolio['by_chain']:
                portfolio['by_chain'][wallet.chain] = {
                    'name': wallet.chain,
                    'usd_value': 0,
                    'percentage': 0,
                    'assets': []
                }
            
            portfolio['by_chain'][wallet.chain]['usd_value'] += wallet.usd_balance
            
            # Add native asset to chain data
            if native_asset['balance'] > 0 or include_zero_balances:
                portfolio['by_chain'][wallet.chain]['assets'].append(native_asset)
            
            # Process tokens
            tokens = Token.query.filter_by(wallet_id=wallet.id).all()
            for token in tokens:
                # Skip tokens with zero balance if not including zero balances
                if token.balance <= 0 and not include_zero_balances:
                    continue
                
                token_data = {
                    'type': 'token',
                    'id': token.id,
                    'chain': token.chain,
                    'address': token.address,
                    'symbol': token.symbol,
                    'name': token.name,
                    'balance': token.balance,
                    'usd_value': token.usd_value
                }
                
                # Add to wallet data
                wallet_data['tokens'].append(token_data)
                
                # Update portfolio total
                portfolio['total_value_usd'] += token.usd_value
                
                # Update chain data
                portfolio['by_chain'][token.chain]['usd_value'] += token.usd_value
                portfolio['by_chain'][token.chain]['assets'].append(token_data)
                
                # Track asset in total portfolio
                portfolio['assets'].append(token_data)
            
            # Add wallet data to portfolio
            portfolio['by_wallet'][wallet.id] = wallet_data
        
        # Calculate percentages for chains
        for chain_name, chain_data in portfolio['by_chain'].items():
            if portfolio['total_value_usd'] > 0:
                chain_data['percentage'] = (chain_data['usd_value'] / portfolio['total_value_usd']) * 100
        
        # Calculate overall composition
        # Group assets by symbol
        composition = defaultdict(lambda: {'symbol': '', 'name': '', 'usd_value': 0, 'percentage': 0})
        
        # Add native assets
        for chain_name, chain_data in portfolio['by_chain'].items():
            for asset in chain_data['assets']:
                if asset['type'] == 'native':
                    key = f"native_{chain_name}"
                    composition[key]['symbol'] = asset['symbol']
                    composition[key]['name'] = f"{asset['symbol']} ({chain_name})"
                    composition[key]['usd_value'] += asset['usd_value']
        
        # Add token assets
        for asset in portfolio['assets']:
            key = f"{asset['symbol']}_{asset['chain']}"
            composition[key]['symbol'] = asset['symbol']
            composition[key]['name'] = f"{asset['name']} ({asset['chain']})"
            composition[key]['usd_value'] += asset['usd_value']
        
        # Calculate percentages and convert to list
        composition_list = []
        for key, data in composition.items():
            if portfolio['total_value_usd'] > 0:
                data['percentage'] = (data['usd_value'] / portfolio['total_value_usd']) * 100
            composition_list.append(data)
        
        # Sort by USD value (descending)
        composition_list.sort(key=lambda x: x['usd_value'], reverse=True)
        
        portfolio['composition'] = composition_list
        
        return portfolio
    
    def calculate_profit_loss(self, wallet_id, period='all'):
        """Calculate profit/loss for a wallet
        
        Args:
            wallet_id (int): Wallet ID
            period (str): Time period ('24h', '7d', '30d', 'all')
            
        Returns:
            dict: Profit/loss data
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
        
        # Get balance history
        from app.models.balance_history import WalletBalanceHistory
        
        # Get current balances
        current_native = wallet.native_balance
        current_usd = wallet.usd_balance
        
        # Get token balances
        tokens = Token.query.filter_by(wallet_id=wallet_id).all()
        current_tokens = {
            token.id: {
                'id': token.id,
                'symbol': token.symbol,
                'name': token.name,
                'balance': token.balance,
                'usd_value': token.usd_value
            }
            for token in tokens
        }
        
        # Get historical balance
        historical_entry = None
        if start_date:
            historical_entry = WalletBalanceHistory.query.filter(
                WalletBalanceHistory.wallet_id == wallet_id,
                WalletBalanceHistory.date >= start_date.date()
            ).order_by(WalletBalanceHistory.date.asc()).first()
        else:
            # Get the earliest entry
            historical_entry = WalletBalanceHistory.query.filter_by(
                wallet_id=wallet_id
            ).order_by(WalletBalanceHistory.date.asc()).first()
        
        # If no historical data, use current values as baseline (no profit/loss)
        if not historical_entry:
            historical_native = current_native
            historical_usd = current_usd
            historical_tokens = current_tokens
        else:
            historical_native = historical_entry.native_balance
            historical_usd = historical_entry.usd_balance
            
            # Map historical token balances
            historical_tokens = {}
            for token_id, balance in historical_entry.token_balances.items():
                token_id = int(token_id)  # Convert from string to int (JSON serialization issue)
                usd_value = historical_entry.token_usd_values.get(str(token_id), 0)
                
                token = Token.query.get(token_id)
                if token:
                    historical_tokens[token_id] = {
                        'id': token_id,
                        'symbol': token.symbol,
                        'name': token.name,
                        'balance': balance,
                        'usd_value': usd_value
                    }
        
        # Calculate profit/loss
        native_change = current_native - historical_native
        usd_change = current_usd - historical_usd
        
        # Calculate percentage changes
        native_change_pct = 0
        if historical_native > 0:
            native_change_pct = (native_change / historical_native) * 100
        
        usd_change_pct = 0
        if historical_usd > 0:
            usd_change_pct = (usd_change / historical_usd) * 100
        
        # Calculate token changes
        token_changes = []
        for token_id, current in current_tokens.items():
            historical = historical_tokens.get(token_id, {
                'balance': 0,
                'usd_value': 0
            })
            
            balance_change = current['balance'] - historical.get('balance', 0)
            usd_change = current['usd_value'] - historical.get('usd_value', 0)
            
            # Calculate percentage changes
            balance_change_pct = 0
            if historical.get('balance', 0) > 0:
                balance_change_pct = (balance_change / historical['balance']) * 100
            
            usd_change_pct = 0
            if historical.get('usd_value', 0) > 0:
                usd_change_pct = (usd_change / historical['usd_value']) * 100
            
            token_changes.append({
                'id': token_id,
                'symbol': current['symbol'],
                'name': current['name'],
                'current_balance': current['balance'],
                'historical_balance': historical.get('balance', 0),
                'balance_change': balance_change,
                'balance_change_pct': balance_change_pct,
                'current_usd': current['usd_value'],
                'historical_usd': historical.get('usd_value', 0),
                'usd_change': usd_change,
                'usd_change_pct': usd_change_pct
            })
        
        # Sort token changes by USD change (descending)
        token_changes.sort(key=lambda x: abs(x['usd_change']), reverse=True)
        
        # Prepare result
        result = {
            'wallet_id': wallet_id,
            'address': wallet.address,
            'chain': wallet.chain,
            'period': period,
            'current_date': datetime.utcnow().isoformat(),
            'historical_date': historical_entry.date.isoformat() if historical_entry else None,
            'native': {
                'current': current_native,
                'historical': historical_native,
                'change': native_change,
                'change_pct': native_change_pct
            },
            'usd': {
                'current': current_usd,
                'historical': historical_usd,
                'change': usd_change,
                'change_pct': usd_change_pct
            },
            'tokens': token_changes
        }
        
        return result
    
    def compare_wallets(self, wallet_ids, period='30d'):
        """Compare performance of multiple wallets
        
        Args:
            wallet_ids (list): List of wallet IDs
            period (str): Time period ('24h', '7d', '30d', 'all')
            
        Returns:
            dict: Wallet comparison data
        """
        if not wallet_ids:
            raise ValueError("At least one wallet ID is required")
        
        # Get wallets
        wallets = Wallet.query.filter(Wallet.id.in_(wallet_ids)).all()
        if not wallets:
            raise ValueError("No valid wallets found")
        
        # Initialize comparison data
        comparison = {
            'period': period,
            'wallets': [],
            'best_performer': None,
            'worst_performer': None,
            'combined_profit_loss': 0
        }
        
        # Calculate profit/loss for each wallet
        best_usd_change_pct = float('-inf')
        worst_usd_change_pct = float('inf')
        best_performer = None
        worst_performer = None
        
        for wallet in wallets:
            try:
                pnl = self.calculate_profit_loss(wallet.id, period)
                wallet_data = {
                    'id': wallet.id,
                    'address': wallet.address,
                    'chain': wallet.chain,
                    'current_usd': pnl['usd']['current'],
                    'historical_usd': pnl['usd']['historical'],
                    'usd_change': pnl['usd']['change'],
                    'usd_change_pct': pnl['usd']['change_pct'],
                    'top_tokens': pnl['tokens'][:3] if pnl['tokens'] else []
                }
                
                comparison['wallets'].append(wallet_data)
                comparison['combined_profit_loss'] += pnl['usd']['change']
                
                # Track best and worst performers
                if pnl['usd']['change_pct'] > best_usd_change_pct:
                    best_usd_change_pct = pnl['usd']['change_pct']
                    best_performer = wallet_data
                
                if pnl['usd']['change_pct'] < worst_usd_change_pct:
                    worst_usd_change_pct = pnl['usd']['change_pct']
                    worst_performer = wallet_data
            except Exception as e:
                # Skip wallets with errors
                print(f"Error calculating PnL for wallet {wallet.id}: {str(e)}")
        
        # Sort wallets by USD change percentage (descending)
        comparison['wallets'].sort(key=lambda x: x['usd_change_pct'], reverse=True)
        
        # Set best and worst performers
        comparison['best_performer'] = best_performer
        comparison['worst_performer'] = worst_performer
        
        return comparison
    
    def calculate_cross_chain_value(self, user_id=None):
        """Calculate total value across all chains
        
        Args:
            user_id (int, optional): User ID to filter wallets
            
        Returns:
            dict: Cross-chain value data
        """
        # Build wallet query
        query = Wallet.query
        
        # Filter by user if provided
        if user_id:
            # In a real implementation, you would join with user permissions
            # For this example, we'll assume direct ownership
            query = query.filter_by(user_id=user_id)
        
        # Get all active wallets
        wallets = query.filter_by(is_active=True).all()
        
        # Initialize cross-chain data
        cross_chain = {
            'total_usd_value': 0,
            'chains': {},
            'tokens': {},
            'wallets': []
        }
        
        # Process each wallet
        for wallet in wallets:
            wallet_data = {
                'id': wallet.id,
                'address': wallet.address,
                'chain': wallet.chain,
                'native_balance': wallet.native_balance,
                'usd_balance': wallet.usd_balance
            }
            
            cross_chain['wallets'].append(wallet_data)
            cross_chain['total_usd_value'] += wallet.usd_balance
            
            # Update chain data
            if wallet.chain not in cross_chain['chains']:
                cross_chain['chains'][wallet.chain] = {
                    'name': wallet.chain,
                    'native_balance': 0,
                    'usd_value': 0,
                    'percentage': 0
                }
            
            cross_chain['chains'][wallet.chain]['native_balance'] += wallet.native_balance
            cross_chain['chains'][wallet.chain]['usd_value'] += wallet.usd_balance
            
            # Get chain info for native token symbol
            chain_info = ChainInfo.query.filter_by(name=wallet.chain).first()
            symbol = chain_info.currency_symbol if chain_info else 'ETH'  # Default to ETH
            
            # Update token data for native token
            token_key = f"native_{wallet.chain}"
            if token_key not in cross_chain['tokens']:
                cross_chain['tokens'][token_key] = {
                    'symbol': symbol,
                    'name': f"{symbol} ({wallet.chain})",
                    'type': 'native',
                    'chain': wallet.chain,
                    'balance': 0,
                    'usd_value': 0,
                    'percentage': 0
                }
            
            cross_chain['tokens'][token_key]['balance'] += wallet.native_balance
            cross_chain['tokens'][token_key]['usd_value'] += wallet.usd_balance
            
            # Process ERC20 tokens
            tokens = Token.query.filter_by(wallet_id=wallet.id).all()
            for token in tokens:
                token_key = f"{token.symbol}_{token.chain}_{token.address}"
                if token_key not in cross_chain['tokens']:
                    cross_chain['tokens'][token_key] = {
                        'symbol': token.symbol,
                        'name': token.name,
                        'type': 'erc20',
                        'chain': token.chain,
                        'address': token.address,
                        'balance': 0,
                        'usd_value': 0,
                        'percentage': 0
                    }
                
                cross_chain['tokens'][token_key]['balance'] += token.balance
                cross_chain['tokens'][token_key]['usd_value'] += token.usd_value
                cross_chain['total_usd_value'] += token.usd_value
        
        # Calculate percentages
        if cross_chain['total_usd_value'] > 0:
            for chain_name, chain_data in cross_chain['chains'].items():
                chain_data['percentage'] = (chain_data['usd_value'] / cross_chain['total_usd_value']) * 100
            
            for token_key, token_data in cross_chain['tokens'].items():
                token_data['percentage'] = (token_data['usd_value'] / cross_chain['total_usd_value']) * 100
        
        # Convert dictionaries to lists for easier processing
        cross_chain['chains'] = list(cross_chain['chains'].values())
        cross_chain['tokens'] = list(cross_chain['tokens'].values())
        
        # Sort chains by USD value (descending)
        cross_chain['chains'].sort(key=lambda x: x['usd_value'], reverse=True)
        
        # Sort tokens by USD value (descending)
        cross_chain['tokens'].sort(key=lambda x: x['usd_value'], reverse=True)
        
        return cross_chain
    
    def get_risk_assessment(self, wallet_id):
        """Get risk assessment for a wallet
        
        Args:
            wallet_id (int): Wallet ID
            
        Returns:
            dict: Risk assessment data
        """
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet with ID {wallet_id} not found")
        
        # Get tokens for the wallet
        tokens = Token.query.filter_by(wallet_id=wallet_id).all()
        
        # Get transactions for the wallet
        transactions = TokenTransaction.query.filter_by(wallet_id=wallet_id).all()
        
        # Initialize risk assessment
        risk = {
            'wallet_id': wallet_id,
            'address': wallet.address,
            'chain': wallet.chain,
            'overall_risk_score': 0,
            'risk_level': 'unknown',
            'risk_factors': [],
            'diversification_score': 0,
            'activity_score': 0,
            'volatility_score': 0,
            'gas_efficiency_score': 0,
            'recommendations': []
        }
        
        # Calculate diversification score
        risk['diversification_score'] = self._calculate_diversification_score(wallet, tokens)
        
        # Calculate activity score
        risk['activity_score'] = self._calculate_activity_score(wallet, transactions)
        
        # Calculate volatility score
        risk['volatility_score'] = self._calculate_volatility_score(wallet, tokens)
        
        # Calculate gas efficiency score
        risk['gas_efficiency_score'] = self._calculate_gas_efficiency_score(wallet, transactions)
        
        # Calculate overall risk score
        risk['overall_risk_score'] = (
            risk['diversification_score'] * 0.4 +
            risk['activity_score'] * 0.2 +
            risk['volatility_score'] * 0.3 +
            risk['gas_efficiency_score'] * 0.1
        )
        
        # Determine risk level
        if risk['overall_risk_score'] >= 80:
            risk['risk_level'] = 'low'
        elif risk['overall_risk_score'] >= 60:
            risk['risk_level'] = 'medium'
        elif risk['overall_risk_score'] >= 40:
            risk['risk_level'] = 'high'
        else:
            risk['risk_level'] = 'very_high'
        
        # Generate risk factors and recommendations
        self._generate_risk_factors_and_recommendations(risk, wallet, tokens, transactions)
        
        return risk
    
    def _calculate_diversification_score(self, wallet, tokens):
        """Calculate diversification score
        
        Args:
            wallet (Wallet): Wallet object
            tokens (list): List of tokens
            
        Returns:
            float: Diversification score (0-100)
        """
        # If no tokens, diversification is poor
        if not tokens:
            return 20
        
        # Calculate Herfindahl-Hirschman Index (HHI)
        # Lower HHI means better diversification
        total_value = wallet.usd_balance
        for token in tokens:
            total_value += token.usd_value
        
        if total_value <= 0:
            return 0
        
        # Calculate market shares and HHI
        hhi = (wallet.usd_balance / total_value) ** 2 * 10000  # Native token
        
        for token in tokens:
            market_share = token.usd_value / total_value
            hhi += market_share ** 2 * 10000
        
        # Normalize HHI to 0-100 score (inverted)
        # HHI: 10000 = monopoly (one token), 0 = perfect diversification
        # Score: 0 = poor diversification, 100 = excellent diversification
        num_assets = len(tokens) + 1  # +1 for native token
        
        if num_assets <= 1:
            return 0
        
        # Minimum possible HHI for num_assets
        min_hhi = 10000 / num_assets
        
        # Scale score based on how close HHI is to minimal HHI
        if hhi >= 10000:
            return 0
        elif hhi <= min_hhi:
            return 100
        else:
            # Linear scaling
            return max(0, min(100, 100 * (10000 - hhi) / (10000 - min_hhi)))
    
    def _calculate_activity_score(self, wallet, transactions):
        """Calculate activity score
        
        Args:
            wallet (Wallet): Wallet object
            transactions (list): List of transactions
            
        Returns:
            float: Activity score (0-100)
        """
        # If no transactions, activity is poor
        if not transactions:
            return 0
        
        # Get transactions from the last 30 days
        recent_date = datetime.utcnow() - timedelta(days=30)
        recent_transactions = [tx for tx in transactions if tx.timestamp >= recent_date]
        
        # Count unique days with transactions
        unique_days = set()
        for tx in recent_transactions:
            unique_days.add(tx.timestamp.date())
        
        # Calculate average transactions per day
        avg_tx_per_day = len(recent_transactions) / 30
        
        # Calculate scores
        num_days_score = min(100, (len(unique_days) / 30) * 100)
        tx_frequency_score = min(100, avg_tx_per_day * 20)  # 5 tx/day = 100 score
        
        # Combine scores
        activity_score = (num_days_score * 0.6) + (tx_frequency_score * 0.4)
        
        return activity_score
    
    def _calculate_volatility_score(self, wallet, tokens):
        """Calculate volatility score
        
        Args:
            wallet (Wallet): Wallet object
            tokens (list): List of tokens
            
        Returns:
            float: Volatility score (0-100, higher = less volatile = better)
        """
        if not tokens:
            # Only native token, generally low volatility
            return 80
        
        # Get price history for tokens
        volatilities = []
        total_value = 0
        
        for token in tokens:
            # Skip tokens with no value
            if token.usd_value <= 0:
                continue
            
            total_value += token.usd_value
            
            # Get price history for the last 30 days
            price_history = TokenPriceHistory.query.filter(
                TokenPriceHistory.token_id == token.id,
                TokenPriceHistory.timestamp >= datetime.utcnow() - timedelta(days=30)
            ).order_by(TokenPriceHistory.timestamp.asc()).all()
            
            # Calculate volatility if we have enough data points
            if len(price_history) >= 7:
                prices = [ph.price for ph in price_history]
                # Calculate daily returns
                returns = []
                for i in range(1, len(prices)):
                    if prices[i-1] > 0:
                        daily_return = (prices[i] - prices[i-1]) / prices[i-1]
                        returns.append(daily_return)
                
                if returns:
                    # Calculate volatility (standard deviation of returns)
                    volatility = np.std(returns) * 100  # Convert to percentage
                    volatilities.append((volatility, token.usd_value))
            else:
                # Not enough data, use a default volatility based on token type
                # Stablecoins have low volatility, others have medium-high
                if 'usd' in token.symbol.lower() or 'dai' in token.symbol.lower():
                    volatilities.append((1.0, token.usd_value))  # Low volatility
                else:
                    volatilities.append((15.0, token.usd_value))  # Medium-high volatility
        
        # Add native token
        if wallet.usd_balance > 0:
            # Most native tokens have medium volatility
            volatilities.append((10.0, wallet.usd_balance))
            total_value += wallet.usd_balance
        
        # Calculate weighted average volatility
        if total_value <= 0:
            return 50  # Default score
        
        weighted_volatility = sum(vol * value for vol, value in volatilities) / total_value
        
        # Convert volatility to score (lower volatility = higher score)
        # Typical volatility ranges: 0-5% = excellent, 5-15% = good, 15-30% = medium, 30%+ = high
        if weighted_volatility <= 5:
            volatility_score = 100
        elif weighted_volatility <= 15:
            volatility_score = 80 - ((weighted_volatility - 5) * 2)
        elif weighted_volatility <= 30:
            volatility_score = 60 - ((weighted_volatility - 15) * 2)
        else:
            volatility_score = max(0, 30 - ((weighted_volatility - 30) * 0.5))
        
        return volatility_score
    
    def _calculate_gas_efficiency_score(self, wallet, transactions):
        """Calculate gas efficiency score
        
        Args:
            wallet (Wallet): Wallet object
            transactions (list): List of transactions
            
        Returns:
            float: Gas efficiency score (0-100)
        """
        # If no transactions, can't calculate gas efficiency
        if not transactions:
            return 50  # Default score
        
        # Filter to sent transactions (only these use gas)
        sent_transactions = [tx for tx in transactions if tx.tx_type == 'send']
        
        if not sent_transactions:
            return 50  # Default score
        
        # Get transactions from the last 30 days
        recent_date = datetime.utcnow() - timedelta(days=30)
        recent_transactions = [tx for tx in sent_transactions if tx.timestamp >= recent_date]
        
        if not recent_transactions:
            return 50  # Default score
        
        # Calculate average gas price and gas used
        total_gas_price_gwei = 0
        total_gas_used = 0
        total_gas_cost_eth = 0
        total_transaction_value = 0
        
        for tx in recent_transactions:
            if tx.gas_price:
                gas_price_gwei = tx.gas_price / 1e9
                total_gas_price_gwei += gas_price_gwei
            
            if tx.gas_used:
                total_gas_used += tx.gas_used
            
            if tx.gas_cost_eth:
                total_gas_cost_eth += tx.gas_cost_eth
            
            if tx.usd_value:
                total_transaction_value += tx.usd_value
        
        avg_gas_price_gwei = total_gas_price_gwei / len(recent_transactions)
        avg_gas_used = total_gas_used / len(recent_transactions)
        
        # Calculate gas cost as percentage of transaction value
        gas_cost_percentage = 0
        if total_transaction_value > 0:
            # Approximate ETH to USD conversion
            gas_cost_usd = total_gas_cost_eth * 1500  # Placeholder value
            gas_cost_percentage = (gas_cost_usd / total_transaction_value) * 100
        
        # Calculate scores
        gas_price_score = 0
        if wallet.chain.lower() == 'ethereum':
            # For Ethereum, score based on typical gas prices
            if avg_gas_price_gwei <= 30:
                gas_price_score = 100
            elif avg_gas_price_gwei <= 60:
                gas_price_score = 80
            elif avg_gas_price_gwei <= 100:
                gas_price_score = 60
            elif avg_gas_price_gwei <= 150:
                gas_price_score = 40
            else:
                gas_price_score = 20
        else:
            # For other chains, gas is typically cheaper
            if avg_gas_price_gwei <= 10:
                gas_price_score = 100
            elif avg_gas_price_gwei <= 30:
                gas_price_score = 80
            elif avg_gas_price_gwei <= 50:
                gas_price_score = 60
            elif avg_gas_price_gwei <= 100:
                gas_price_score = 40
            else:
                gas_price_score = 20
        
        # Score based on gas cost percentage
        cost_percentage_score = 0
        if gas_cost_percentage <= 0.5:
            cost_percentage_score = 100
        elif gas_cost_percentage <= 1:
            cost_percentage_score = 80
        elif gas_cost_percentage <= 3:
            cost_percentage_score = 60
        elif gas_cost_percentage <= 10:
            cost_percentage_score = 40
        else:
            cost_percentage_score = 20
        
        # Combine scores
        gas_efficiency_score = (gas_price_score * 0.5) + (cost_percentage_score * 0.5)
        
        return gas_efficiency_score
    
    def _generate_risk_factors_and_recommendations(self, risk, wallet, tokens, transactions):
        """Generate risk factors and recommendations
        
        Args:
            risk (dict): Risk assessment data
            wallet (Wallet): Wallet object
            tokens (list): List of tokens
            transactions (list): List of transactions
        """
        risk_factors = []
        recommendations = []
        
        # Check diversification
        if risk['diversification_score'] < 40:
            risk_factors.append({
                'type': 'diversification',
                'severity': 'high',
                'description': 'Portfolio lacks diversification'
            })
            recommendations.append({
                'type': 'diversification',
                'description': 'Consider diversifying your portfolio across more assets to reduce risk',
                'priority': 'high'
            })
        elif risk['diversification_score'] < 60:
            risk_factors.append({
                'type': 'diversification',
                'severity': 'medium',
                'description': 'Portfolio moderately concentrated'
            })
            recommendations.append({
                'type': 'diversification',
                'description': 'Consider adding more diverse assets to your portfolio',
                'priority': 'medium'
            })
        
        # Check for large concentrations in single tokens
        total_value = wallet.usd_balance
        for token in tokens:
            total_value += token.usd_value
        
        if total_value > 0:
            for token in tokens:
                concentration = (token.usd_value / total_value) * 100
                if concentration > 50:
                    risk_factors.append({
                        'type': 'concentration',
                        'severity': 'high',
                        'description': f'High concentration ({concentration:.1f}%) in {token.symbol}'
                    })
                    recommendations.append({
                        'type': 'rebalance',
                        'description': f'Consider reducing exposure to {token.symbol} to decrease portfolio risk',
                        'priority': 'high'
                    })
                elif concentration > 30:
                    risk_factors.append({
                        'type': 'concentration',
                        'severity': 'medium',
                        'description': f'Significant concentration ({concentration:.1f}%) in {token.symbol}'
                    })
        
        # Check activity level
        if risk['activity_score'] < 20:
            risk_factors.append({
                'type': 'activity',
                'severity': 'low',
                'description': 'Wallet shows low activity'
            })
            recommendations.append({
                'type': 'activity',
                'description': 'Consider implementing more regular trading or rebalancing',
                'priority': 'low'
            })
        
        # Check volatility
        if risk['volatility_score'] < 40:
            risk_factors.append({
                'type': 'volatility',
                'severity': 'high',
                'description': 'Portfolio has high volatility'
            })
            recommendations.append({
                'type': 'volatility',
                'description': 'Consider adding more stable assets to reduce portfolio volatility',
                'priority': 'high'
            })
        elif risk['volatility_score'] < 60:
            risk_factors.append({
                'type': 'volatility',
                'severity': 'medium',
                'description': 'Portfolio has moderate volatility'
            })
        
        # Check gas efficiency
        if risk['gas_efficiency_score'] < 40:
            risk_factors.append({
                'type': 'gas',
                'severity': 'medium',
                'description': 'High gas costs relative to transaction values'
            })
            recommendations.append({
                'type': 'gas',
                'description': 'Consider optimizing transaction timing or batching transactions to reduce gas costs',
                'priority': 'medium'
            })
        
        # Check for stablecoin allocation
        has_stablecoins = False
        stablecoin_value = 0
        for token in tokens:
            if ('usd' in token.symbol.lower() or 'dai' in token.symbol.lower() or 
                'usdc' in token.symbol.lower() or 'usdt' in token.symbol.lower()):
                has_stablecoins = True
                stablecoin_value += token.usd_value
        
        stablecoin_percentage = (stablecoin_value / total_value) * 100 if total_value > 0 else 0
        
        if not has_stablecoins and len(tokens) > 0:
            recommendations.append({
                'type': 'allocation',
                'description': 'Consider adding stablecoins to your portfolio for reduced volatility',
                'priority': 'medium'
            })
        elif stablecoin_percentage < 10 and total_value > 1000:
            recommendations.append({
                'type': 'allocation',
                'description': 'Consider increasing stablecoin allocation for better risk management',
                'priority': 'low'
            })
        
        # Set risk factors and recommendations
        risk['risk_factors'] = risk_factors
        risk['recommendations'] = recommendations