"""
Enhanced Wallet API
API endpoints for enhanced wallet functionality
"""
from flask import Blueprint, jsonify, request, current_app, session
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from app.models.wallet import Wallet, ChainInfo
from app.models.enhanced_token import Token, TokenTransaction, TokenList
from app.models.balance_history import WalletBalanceHistory

# Import services
from app.services.token_discovery_service import TokenDiscoveryService
from app.services.transaction_history_service import TransactionHistoryService
from app.services.wallet_security_service import WalletSecurityService
from app.services.balance_analytics_service import BalanceAnalyticsService

# Create blueprint
wallet_api_bp = Blueprint('wallet_api', __name__)

#
# Token Management Endpoints
#

@wallet_api_bp.route('/wallet/<int:wallet_id>/scan_tokens', methods=['POST'])
@login_required
def scan_wallet_tokens(wallet_id):
    """API endpoint for scanning wallet for tokens
    
    Scans a wallet for ERC-20/ERC-721 tokens
    """
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with ID {wallet_id} not found'
            })
        
        # Security check
        security_service = WalletSecurityService(current_user.id)
        if not security_service.check_wallet_permission(wallet_id, 'read'):
            return jsonify({
                'success': False,
                'error': 'You do not have permission to access this wallet'
            })
        
        # Initialize token discovery service
        discovery_service = TokenDiscoveryService(wallet.chain)
        
        # Refresh token balances
        updated_tokens = discovery_service.refresh_token_balances(wallet_id)
        
        return jsonify({
            'success': True,
            'message': f'Refreshed {len(updated_tokens)} tokens',
            'updated_tokens': updated_tokens
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@wallet_api_bp.route('/wallet/<int:wallet_id>/add_token', methods=['POST'])
@login_required
def add_custom_token(wallet_id):
    """API endpoint for adding a custom token
    
    Adds a custom token to a wallet
    """
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with ID {wallet_id} not found'
            })
        
        # Security check
        security_service = WalletSecurityService(current_user.id)
        if not security_service.check_wallet_permission(wallet_id, 'write'):
            return jsonify({
                'success': False,
                'error': 'You do not have permission to modify this wallet'
            })
        
        # Get request data
        data = request.get_json()
        
        # Validate required fields
        token_address = data.get('token_address')
        if not token_address:
            return jsonify({
                'success': False,
                'error': 'Token address is required'
            })
        
        # Optional fields
        name = data.get('name')
        symbol = data.get('symbol')
        decimals = data.get('decimals')
        
        # Initialize token discovery service
        discovery_service = TokenDiscoveryService(wallet.chain)
        
        # Add custom token
        token = discovery_service.add_custom_token(
            wallet_id, 
            token_address, 
            name=name, 
            symbol=symbol, 
            decimals=decimals
        )
        
        return jsonify({
            'success': True,
            'message': f'Added token {token.symbol}',
            'token': token.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@wallet_api_bp.route('/wallet/<int:wallet_id>/token/<int:token_id>/details')
@login_required
def token_details(wallet_id, token_id):
    """API endpoint for token details
    
    Returns detailed information about a token
    """
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with ID {wallet_id} not found'
            })
        
        # Security check
        security_service = WalletSecurityService(current_user.id)
        if not security_service.check_wallet_permission(wallet_id, 'read'):
            return jsonify({
                'success': False,
                'error': 'You do not have permission to access this wallet'
            })
        
        # Get token
        token = Token.query.get(token_id)
        if not token or token.wallet_id != wallet_id:
            return jsonify({
                'success': False,
                'error': f'Token with ID {token_id} not found in wallet'
            })
        
        # Initialize token discovery service
        discovery_service = TokenDiscoveryService(wallet.chain)
        
        # Get token analytics
        analytics = discovery_service.get_token_analytics(token_id)
        
        return jsonify({
            'success': True,
            'token': analytics
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@wallet_api_bp.route('/wallet/<int:wallet_id>/token/<int:token_id>/price_history')
@login_required
def token_price_history(wallet_id, token_id):
    """API endpoint for token price history
    
    Returns price history for a token
    """
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with ID {wallet_id} not found'
            })
        
        # Security check
        security_service = WalletSecurityService(current_user.id)
        if not security_service.check_wallet_permission(wallet_id, 'read'):
            return jsonify({
                'success': False,
                'error': 'You do not have permission to access this wallet'
            })
        
        # Get token
        token = Token.query.get(token_id)
        if not token or token.wallet_id != wallet_id:
            return jsonify({
                'success': False,
                'error': f'Token with ID {token_id} not found in wallet'
            })
        
        # Get query parameters
        days = request.args.get('days', 30, type=int)
        
        # Initialize token discovery service
        discovery_service = TokenDiscoveryService(wallet.chain)
        
        # Get price history
        price_history = discovery_service.fetch_token_price_history(token_id, days)
        
        return jsonify({
            'success': True,
            'token_id': token_id,
            'days': days,
            'price_history': price_history
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@wallet_api_bp.route('/token_lists')
@login_required
def get_token_lists():
    """API endpoint for token lists
    
    Returns all token lists
    """
    try:
        # Get chain parameter
        chain = request.args.get('chain')
        
        # Query token lists
        query = TokenList.query
        if chain:
            query = query.filter_by(chain=chain)
        
        token_lists = query.all()
        
        return jsonify({
            'success': True,
            'token_lists': [token_list.to_dict() for token_list in token_lists]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@wallet_api_bp.route('/import_token_list', methods=['POST'])
@login_required
def import_token_list():
    """API endpoint for importing a token list
    
    Imports a token list from a URL
    """
    try:
        # Get request data
        data = request.get_json()
        
        # Validate required fields
        token_list_name = data.get('name')
        token_list_url = data.get('url')
        chain_name = data.get('chain')
        
        if not token_list_name or not token_list_url or not chain_name:
            return jsonify({
                'success': False,
                'error': 'Name, URL, and chain are required'
            })
        
        # Initialize token discovery service
        discovery_service = TokenDiscoveryService(chain_name)
        
        # Import token list
        token_list = discovery_service.import_token_list(token_list_name, token_list_url, chain_name)
        
        return jsonify({
            'success': True,
            'message': f'Imported {token_list.tokens_count} tokens from {token_list_name}',
            'token_list': token_list.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

#
# Transaction History Endpoints
#

@wallet_api_bp.route('/wallet/<int:wallet_id>/transactions')
@login_required
def wallet_transactions(wallet_id):
    """API endpoint for wallet transactions
    
    Returns transaction history for a wallet
    """
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with ID {wallet_id} not found'
            })
        
        # Security check
        security_service = WalletSecurityService(current_user.id)
        if not security_service.check_wallet_permission(wallet_id, 'read'):
            return jsonify({
                'success': False,
                'error': 'You do not have permission to access this wallet'
            })
        
        # Get query parameters
        token_id = request.args.get('token_id', type=int)
        tx_type = request.args.get('tx_type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        status = request.args.get('status')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Convert date strings to datetime objects
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date)
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': f'Invalid start_date format: {start_date}'
                })
        
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date)
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': f'Invalid end_date format: {end_date}'
                })
        
        # Prepare filter options
        filter_options = {
            'page': page,
            'per_page': per_page
        }
        
        if token_id:
            filter_options['token_id'] = token_id
        
        if tx_type:
            filter_options['tx_type'] = tx_type
        
        if start_date:
            filter_options['start_date'] = start_date
        
        if end_date:
            filter_options['end_date'] = end_date
        
        if status:
            filter_options['status'] = status
        
        # Initialize transaction history service
        history_service = TransactionHistoryService(wallet.chain)
        
        # Get transactions
        transactions_data = history_service.get_wallet_transactions(wallet_id, filter_options)
        
        return jsonify({
            'success': True,
            'wallet_id': wallet_id,
            'transactions': transactions_data['transactions'],
            'pagination': transactions_data['pagination']
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@wallet_api_bp.route('/wallet/<int:wallet_id>/sync_transactions', methods=['POST'])
@login_required
def sync_wallet_transactions(wallet_id):
    """API endpoint for syncing wallet transactions
    
    Syncs transaction history for a wallet
    """
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with ID {wallet_id} not found'
            })
        
        # Security check
        security_service = WalletSecurityService(current_user.id)
        if not security_service.check_wallet_permission(wallet_id, 'write'):
            return jsonify({
                'success': False,
                'error': 'You do not have permission to modify this wallet'
            })
        
        # Get request data
        data = request.get_json() or {}
        
        # Get parameters
        token_id = data.get('token_id')
        start_block = data.get('start_block')
        
        # Initialize services
        history_service = TransactionHistoryService(wallet.chain)
        discovery_service = TokenDiscoveryService(wallet.chain)
        
        # Sync native transactions
        native_result = history_service.sync_native_transactions(wallet_id, start_block)
        
        # Sync token transactions if token_id is specified
        token_result = None
        if token_id:
            token_result = discovery_service.sync_token_transactions(wallet_id, token_id, start_block)
        else:
            # Sync all tokens
            token_result = discovery_service.sync_token_transactions(wallet_id, None, start_block)
        
        return jsonify({
            'success': True,
            'native_sync': native_result,
            'token_sync': token_result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@wallet_api_bp.route('/wallet/<int:wallet_id>/transaction_summary')
@login_required
def transaction_summary(wallet_id):
    """API endpoint for transaction summary
    
    Returns transaction summary for a wallet
    """
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with ID {wallet_id} not found'
            })
        
        # Security check
        security_service = WalletSecurityService(current_user.id)
        if not security_service.check_wallet_permission(wallet_id, 'read'):
            return jsonify({
                'success': False,
                'error': 'You do not have permission to access this wallet'
            })
        
        # Get query parameters
        period = request.args.get('period', '30d')
        
        # Initialize transaction history service
        history_service = TransactionHistoryService(wallet.chain)
        
        # Get transaction summary
        summary = history_service.generate_transaction_summary(wallet_id, period)
        
        return jsonify({
            'success': True,
            'wallet_id': wallet_id,
            'summary': summary
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@wallet_api_bp.route('/wallet/<int:wallet_id>/gas_analytics')
@login_required
def gas_analytics(wallet_id):
    """API endpoint for gas analytics
    
    Returns gas usage analytics for a wallet
    """
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with ID {wallet_id} not found'
            })
        
        # Security check
        security_service = WalletSecurityService(current_user.id)
        if not security_service.check_wallet_permission(wallet_id, 'read'):
            return jsonify({
                'success': False,
                'error': 'You do not have permission to access this wallet'
            })
        
        # Get query parameters
        period = request.args.get('period', '30d')
        
        # Initialize transaction history service
        history_service = TransactionHistoryService(wallet.chain)
        
        # Get gas analytics
        analytics = history_service.get_gas_usage_analytics(wallet_id, period)
        
        return jsonify({
            'success': True,
            'wallet_id': wallet_id,
            'analytics': analytics
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@wallet_api_bp.route('/wallet/<int:wallet_id>/export_transactions', methods=['POST'])
@login_required
def export_transactions(wallet_id):
    """API endpoint for exporting transactions
    
    Exports transaction history as CSV or PDF
    """
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with ID {wallet_id} not found'
            })
        
        # Security check
        security_service = WalletSecurityService(current_user.id)
        if not security_service.check_wallet_permission(wallet_id, 'read'):
            return jsonify({
                'success': False,
                'error': 'You do not have permission to access this wallet'
            })
        
        # Get request data
        data = request.get_json() or {}
        
        # Get parameters
        token_id = data.get('token_id')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        format_type = data.get('format', 'csv')
        
        # Convert date strings to datetime objects
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date)
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': f'Invalid start_date format: {start_date}'
                })
        
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date)
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': f'Invalid end_date format: {end_date}'
                })
        
        # Initialize transaction history service
        history_service = TransactionHistoryService(wallet.chain)
        
        # Export transactions
        if format_type.lower() == 'csv':
            csv_data = history_service.export_transactions_csv(wallet_id, token_id, start_date, end_date)
            
            return jsonify({
                'success': True,
                'format': 'csv',
                'data': csv_data
            })
        elif format_type.lower() == 'pdf':
            pdf_data = history_service.export_transactions_pdf(wallet_id, token_id, start_date, end_date)
            
            return jsonify({
                'success': True,
                'format': 'pdf',
                'data': pdf_data.decode('utf-8')
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Unsupported export format: {format_type}'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@wallet_api_bp.route('/wallet/<int:wallet_id>/transaction_patterns')
@login_required
def transaction_patterns(wallet_id):
    """API endpoint for transaction pattern analysis
    
    Returns transaction pattern analysis for a wallet
    """
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with ID {wallet_id} not found'
            })
        
        # Security check
        security_service = WalletSecurityService(current_user.id)
        if not security_service.check_wallet_permission(wallet_id, 'read'):
            return jsonify({
                'success': False,
                'error': 'You do not have permission to access this wallet'
            })
        
        # Get query parameters
        period = request.args.get('period', 'all')
        
        # Initialize transaction history service
        history_service = TransactionHistoryService(wallet.chain)
        
        # Get transaction patterns
        patterns = history_service.analyze_transaction_patterns(wallet_id, period)
        
        return jsonify({
            'success': True,
            'wallet_id': wallet_id,
            'patterns': patterns
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

#
# Security Endpoints
#

@wallet_api_bp.route('/wallet/<int:wallet_id>/permissions')
@login_required
def wallet_permissions(wallet_id):
    """API endpoint for wallet permissions
    
    Returns all permissions for a wallet
    """
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with ID {wallet_id} not found'
            })
        
        # Initialize security service
        security_service = WalletSecurityService(current_user.id)
        
        # Get wallet permissions
        permissions = security_service.get_wallet_permissions(wallet_id)
        
        return jsonify({
            'success': True,
            'wallet_id': wallet_id,
            'permissions': permissions
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@wallet_api_bp.route('/wallet/<int:wallet_id>/create_permission', methods=['POST'])
@login_required
def create_wallet_permission(wallet_id):
    """API endpoint for creating wallet permission
    
    Creates or updates a wallet permission
    """
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with ID {wallet_id} not found'
            })
        
        # Get request data
        data = request.get_json()
        
        # Validate required fields
        user_id = data.get('user_id')
        permission_level = data.get('permission_level', 'read')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'User ID is required'
            })
        
        # Validate permission level
        if permission_level not in ['read', 'write', 'admin']:
            return jsonify({
                'success': False,
                'error': f'Invalid permission level: {permission_level}'
            })
        
        # Initialize security service
        security_service = WalletSecurityService(current_user.id)
        
        # Create wallet permission
        permission = security_service.create_wallet_permission(wallet_id, user_id, permission_level)
        
        return jsonify({
            'success': True,
            'message': f'Created {permission_level} permission for user {user_id}',
            'permission': {
                'id': permission.id,
                'user_id': permission.user_id,
                'resource_type': permission.resource_type,
                'resource_id': permission.resource_id,
                'permission_level': permission.permission_level
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@wallet_api_bp.route('/wallet/<int:wallet_id>/revoke_permission', methods=['POST'])
@login_required
def revoke_wallet_permission(wallet_id):
    """API endpoint for revoking wallet permission
    
    Revokes a wallet permission
    """
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with ID {wallet_id} not found'
            })
        
        # Get request data
        data = request.get_json()
        
        # Validate required fields
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'User ID is required'
            })
        
        # Initialize security service
        security_service = WalletSecurityService(current_user.id)
        
        # Revoke wallet permission
        result = security_service.revoke_wallet_permission(wallet_id, user_id)
        
        if result:
            return jsonify({
                'success': True,
                'message': f'Revoked permission for user {user_id}'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'No permission found for user {user_id}'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@wallet_api_bp.route('/wallet/<int:wallet_id>/create_session', methods=['POST'])
@login_required
def create_wallet_session(wallet_id):
    """API endpoint for creating wallet session
    
    Creates a session key for sensitive operations
    """
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with ID {wallet_id} not found'
            })
        
        # Security check
        security_service = WalletSecurityService(current_user.id)
        if not security_service.check_wallet_permission(wallet_id, 'write'):
            return jsonify({
                'success': False,
                'error': 'You do not have permission to modify this wallet'
            })
        
        # Get request data
        data = request.get_json() or {}
        
        # Get parameters
        expiry_minutes = data.get('expiry_minutes', 30)
        
        # Create session key
        session_key = security_service.create_session_key(wallet_id, expiry_minutes)
        
        return jsonify({
            'success': True,
            'message': f'Created session key with {expiry_minutes} minute expiry',
            'session_key': session_key
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@wallet_api_bp.route('/wallet/<int:wallet_id>/security_audit')
@login_required
def wallet_security_audit(wallet_id):
    """API endpoint for wallet security audit
    
    Performs a security audit for a wallet
    """
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with ID {wallet_id} not found'
            })
        
        # Initialize security service
        security_service = WalletSecurityService(current_user.id)
        
        # Perform security audit
        audit = security_service.perform_security_audit(wallet_id)
        
        return jsonify({
            'success': True,
            'wallet_id': wallet_id,
            'audit': audit
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@wallet_api_bp.route('/wallet/<int:wallet_id>/hardware_wallet', methods=['POST'])
@login_required
def integrate_hardware_wallet(wallet_id):
    """API endpoint for integrating hardware wallet
    
    Integrates a hardware wallet for signing transactions
    """
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with ID {wallet_id} not found'
            })
        
        # Get request data
        data = request.get_json() or {}
        
        # Get parameters
        hardware_type = data.get('type')
        hardware_path = data.get('path')
        
        if not hardware_type or not hardware_path:
            return jsonify({
                'success': False,
                'error': 'Hardware wallet type and path are required'
            })
        
        # Initialize security service
        security_service = WalletSecurityService(current_user.id)
        
        # Integrate hardware wallet
        result = security_service.integrate_hardware_wallet(wallet_id, hardware_type, hardware_path)
        
        return jsonify({
            'success': True,
            'message': f'Integrated {hardware_type} hardware wallet',
            'result': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@wallet_api_bp.route('/wallet/<int:wallet_id>/key_fragments', methods=['POST'])
@login_required
def generate_key_fragments(wallet_id):
    """API endpoint for generating key fragments
    
    Generates key fragments using Shamir's Secret Sharing
    """
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with ID {wallet_id} not found'
            })
        
        # Security check
        security_service = WalletSecurityService(current_user.id)
        if not security_service.check_wallet_permission(wallet_id, 'admin'):
            return jsonify({
                'success': False,
                'error': 'You do not have permission to perform this operation'
            })
        
        # Get request data
        data = request.get_json() or {}
        
        # Get parameters
        num_shares = data.get('num_shares', 3)
        threshold = data.get('threshold', 2)
        private_key = data.get('private_key')
        session_key = data.get('session_key')
        
        if not private_key or not session_key:
            return jsonify({
                'success': False,
                'error': 'Private key and session key are required'
            })
        
        # Validate session key
        if not security_service.validate_session_key(wallet_id, session_key):
            return jsonify({
                'success': False,
                'error': 'Invalid or expired session key'
            })
        
        # Generate key fragments
        fragments = security_service.generate_key_fragments(private_key, num_shares, threshold)
        
        return jsonify({
            'success': True,
            'message': f'Generated {num_shares} key fragments with threshold {threshold}',
            'fragments': fragments,
            'threshold': threshold
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

#
# Balance Analytics Endpoints
#

@wallet_api_bp.route('/wallet/<int:wallet_id>/balance_history')
@login_required
def wallet_balance_history(wallet_id):
    """API endpoint for wallet balance history
    
    Returns balance history for a wallet
    """
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with ID {wallet_id} not found'
            })
        
        # Security check
        security_service = WalletSecurityService(current_user.id)
        if not security_service.check_wallet_permission(wallet_id, 'read'):
            return jsonify({
                'success': False,
                'error': 'You do not have permission to access this wallet'
            })
        
        # Get query parameters
        days = request.args.get('days', 30, type=int)
        
        # Initialize balance analytics service
        analytics_service = BalanceAnalyticsService(current_user.id)
        
        # Update current balance history
        analytics_service.track_balance_history(wallet_id)
        
        # Get balance history
        history = analytics_service.get_balance_history(wallet_id, days)
        
        return jsonify({
            'success': True,
            'wallet_id': wallet_id,
            'days': days,
            'history': history
        })
    """
Enhanced Wallet API
API endpoints for enhanced wallet functionality
"""
from flask import Blueprint, jsonify, request, current_app, session
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from app.models.wallet import Wallet, ChainInfo
from app.models.enhanced_token import Token, TokenTransaction, TokenList
from app.models.balance_history import WalletBalanceHistory

# Import services
from app.services.token_discovery_service import TokenDiscoveryService
from app.services.transaction_history_service import TransactionHistoryService
from app.services.wallet_security_service import WalletSecurityService
from app.services.balance_analytics_service import BalanceAnalyticsService

# Create blueprint
wallet_api_bp = Blueprint('wallet_api', __name__)

#
# Token Management Endpoints
#

@wallet_api_bp.route('/wallet/<int:wallet_id>/scan_tokens', methods=['POST'])
@login_required
def scan_wallet_tokens(wallet_id):
    """API endpoint for scanning wallet for tokens
    
    Scans a wallet for ERC-20/ERC-721 tokens
    """
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with ID {wallet_id} not found'
            })
        
        # Security check
        security_service = WalletSecurityService(current_user.id)
        if not security_service.check_wallet_permission(wallet_id, 'read'):
            return jsonify({
                'success': False,
                'error': 'You do not have permission to access this wallet'
            })
        
        # Initialize token discovery service
        discovery_service = TokenDiscoveryService(wallet.chain)
        
        # Scan wallet for tokens
        discovered_tokens = discovery_service.scan_wallet_for_tokens(wallet.address)
        
        # Add discovered tokens to wallet
        added_token_ids = discovery_service.add_discovered_tokens_to_wallet(wallet_id, discovered_tokens)
        
        return jsonify({
            'success': True,
            'message': f'Found {len(discovered_tokens)} tokens, added {len(added_token_ids)} to wallet',
            'discovered_tokens': discovered_tokens,
            'added_token_ids': added_token_ids
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@wallet_api_bp.route('/wallet/<int:wallet_id>/tokens')
@login_required
def wallet_tokens(wallet_id):
    """API endpoint for wallet tokens
    
    Returns information about all tokens in a wallet
    """
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with ID {wallet_id} not found'
            })
        
        # Security check
        security_service = WalletSecurityService(current_user.id)
        if not security_service.check_wallet_permission(wallet_id, 'read'):
            return jsonify({
                'success': False,
                'error': 'You do not have permission to access this wallet'
            })
        
        # Get tokens
        tokens = Token.query.filter_by(wallet_id=wallet_id).all()
        
        # Format response
        token_data = []
        total_usd_value = wallet.usd_balance  # Start with native balance
        
        # Add native token
        chain_info = ChainInfo.query.filter_by(name=wallet.chain).first()
        native_token = {
            'id': 'native',
            'type': 'native',
            'chain': wallet.chain,
            'symbol': chain_info.currency_symbol if chain_info else 'ETH',
            'name': f'{chain_info.currency_symbol if chain_info else "ETH"} ({wallet.chain})',
            'balance': wallet.native_balance,
            'usd_value': wallet.usd_balance,
            'last_updated': wallet.last_updated.isoformat()
        }
        token_data.append(native_token)
        
        # Add ERC tokens
        for token in tokens:
            token_info = token.to_dict()
            total_usd_value += token.usd_value
            token_data.append(token_info)
        
        # Calculate percentages
        for token in token_data:
            if total_usd_value > 0:
                token['percentage'] = (token['usd_value'] / total_usd_value) * 100
            else:
                token['percentage'] = 0
        
        # Sort by USD value (descending)
        token_data.sort(key=lambda x: x['usd_value'], reverse=True)
        
        return jsonify({
            'success': True,
            'wallet_id': wallet_id,
            'total_usd_value': total_usd_value,
            'tokens': token_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@wallet_api_bp.route('/wallet/<int:wallet_id>/refresh_tokens', methods=['POST'])
@login_required
def refresh_wallet_tokens(wallet_id):
    """API endpoint for refreshing token balances
    
    Refreshes token balances for a wallet
    """
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({
                'success': False,
                'error': f'Wallet with ID {wallet_id} not found'
            })
        
        # Security check
        security_service = WalletSecurityService(current_user.id)
        if not security_service.check_wallet_permission(wallet_id, 'read'):
            return jsonify({
                'success': False,
                'error': 'You do not have permission to access this wallet'
            })
        
        # Initialize token discovery service
        discovery_service = TokenDiscoveryService(wallet.chain)
        
        # Refresh token balances
        updated_tokens = discovery_service.refresh_token_balances(wallet_id)
        
        return jsonify({
            'success': True,
            'message': f'Refreshed {len(updated_tokens)} tokens',
            'updated_tokens': updated_tokens
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })
        