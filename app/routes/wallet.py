wallet.hardware_wallet = {
                'type': random.choice(['ledger', 'trezor']),
                'path': "m/44'/60'/0'/0/0",
                'status': 'active'
            }
            secured_wallets_count += 1
        
        # Random audit date (50% chance of having one)
        if random.random() > 0.5:
            days_ago = random.randint(1, 60)
            wallet.last_audit_date = datetime.utcnow() - timedelta(days=days_ago)
        else:
            wallet.last_audit_date = None
    
    # Calculate security metrics
    users_with_access = random.randint(1, 5)
    avg_security_score = sum(wallet.security_score for wallet in wallets) / len(wallets) if wallets else 0
    
    # Generate dummy security recommendations
    security_recommendations = []
    rec_types = [
        {'title': 'Enable Hardware Wallet', 'description': 'Hardware wallets provide the highest level of security by keeping private keys offline.', 'priority': 'high', 'priority_color': 'danger'},
        {'title': 'Secure Private Keys', 'description': 'Encrypt and securely store your private keys to prevent unauthorized access.', 'priority': 'high', 'priority_color': 'danger'},
        {'title': 'Limit Admin Access', 'description': 'Reduce the number of users with admin privileges to minimize security risks.', 'priority': 'medium', 'priority_color': 'warning'},
        {'title': 'Regular Security Audits', 'description': 'Perform regular security audits to identify and address potential vulnerabilities.', 'priority': 'medium', 'priority_color': 'warning'},
        {'title': 'Create Backup', 'description': 'Create encrypted backups of your wallets to prevent loss of funds.', 'priority': 'low', 'priority_color': 'info'}
    ]
    
    # Randomly select 3-5 recommendations
    num_recommendations = random.randint(3, 5)
    for i in range(min(num_recommendations, len(rec_types))):
        rec = rec_types[i].copy()
        # Add action URL to some recommendations
        if random.random() > 0.5:
            if rec['title'] == 'Enable Hardware Wallet':
                rec['action_url'] = '#hardwareWalletModal'
            elif rec['title'] == 'Secure Private Keys':
                rec['action_url'] = '#keyManagementModal'
            elif rec['title'] == 'Create Backup':
                rec['action_url'] = '#backupRecoveryModal'
        
        security_recommendations.append(rec)
    
    # Generate dummy audit activity
    audit_activity = []
    for i in range(10):
        days_ago = random.randint(0, 30)
        old_score = random.randint(20, 70)
        new_score = random.randint(old_score - 10, old_score + 30)
        
        if new_score > old_score:
            status = 'improved'
        elif new_score < old_score:
            status = 'degraded'
        else:
            status = 'unchanged'
        
        activity = {
            'timestamp': datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59)),
            'wallet_address': f'0x{random.randint(0, 9999999):07x}...{random.randint(0, 9999):04x}',
            'chain': random.choice(['ethereum', 'polygon', 'bsc', 'arbitrum-one']),
            'activity_type': random.choice(['Security Audit', 'Key Management', 'Permission Change', 'Hardware Wallet Setup']),
            'old_score': old_score,
            'new_score': new_score,
            'status': status
        }
        
        audit_activity.append(activity)
    
    # Sort by timestamp (most recent first)
    audit_activity.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return render_template('dashboard/security.html',
                           wallets=wallets,
                           users=users,
                           active_chains=active_chains,
                           secured_wallets_count=secured_wallets_count,
                           users_with_access=users_with_access,
                           avg_security_score=round(avg_security_score),
                           security_recommendations=security_recommendations,
                           audit_activity=audit_activity,
                           title='Wallet Security')

#
# API Endpoints for Token Management
#

@wallet_bp.route('/api/token/scan', methods=['POST'])
@login_required
def scan_tokens():
    """API endpoint for scanning wallet for tokens"""
    try:
        # Get request data
        data = request.get_json()
        
        # Validate wallet ID
        wallet_id = data.get('wallet_id')
        if not wallet_id:
            return jsonify({'success': False, 'error': 'Wallet ID is required'})
        
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({'success': False, 'error': 'Wallet not found'})
        
        # Check if we should include tokens from token lists
        include_token_lists = data.get('include_token_lists', True)
        
        # Initialize token discovery service
        discovery_service = TokenDiscoveryService(wallet.chain)
        
        # Scan wallet for tokens
        discovered_tokens = discovery_service.scan_wallet_for_tokens(wallet.address)
        
        # Add tokens to wallet
        added_token_ids = discovery_service.add_discovered_tokens_to_wallet(wallet_id, discovered_tokens)
        
        # Get added tokens
        added_tokens = []
        for token_id in added_token_ids:
            token = Token.query.get(token_id)
            if token:
                added_tokens.append(token.to_dict())
        
        return jsonify({
            'success': True,
            'message': f'Found {len(discovered_tokens)} tokens, added {len(added_token_ids)} to wallet',
            'discovered_tokens': discovered_tokens,
            'added_tokens': added_tokens
        })
    except Exception as e:
        current_app.logger.error(f"Error creating wallet permission: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/wallet/<int:wallet_id>/revoke_permission', methods=['POST'])
@login_required
def revoke_wallet_permission(wallet_id):
    """API endpoint for revoking wallet permission"""
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({'success': False, 'error': 'Wallet not found'})
        
        # Get request data
        data = request.get_json()
        
        # Validate required fields
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID is required'})
        
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
        current_app.logger.error(f"Error revoking wallet permission: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/wallet/<int:wallet_id>/create_session', methods=['POST'])
@login_required
def create_wallet_session(wallet_id):
    """API endpoint for creating wallet session"""
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({'success': False, 'error': 'Wallet not found'})
        
        # Get request data
        data = request.get_json() or {}
        
        # Get expiry parameter
        expiry_minutes = data.get('expiry_minutes', 30)
        
        # Initialize security service
        security_service = WalletSecurityService(current_user.id)
        
        # Create session key
        session_key = security_service.create_session_key(wallet_id, expiry_minutes)
        
        return jsonify({
            'success': True,
            'message': f'Created session key with {expiry_minutes} minute expiry',
            'session_key': session_key
        })
    except Exception as e:
        current_app.logger.error(f"Error creating session key: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/wallet/<int:wallet_id>/security_audit', methods=['POST'])
@login_required
def wallet_security_audit(wallet_id):
    """API endpoint for wallet security audit"""
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({'success': False, 'error': 'Wallet not found'})
        
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
        current_app.logger.error(f"Error performing security audit: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/wallet/<int:wallet_id>/hardware_wallet', methods=['POST'])
@login_required
def integrate_hardware_wallet(wallet_id):
    """API endpoint for integrating hardware wallet"""
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({'success': False, 'error': 'Wallet not found'})
        
        # Get request data
        data = request.get_json() or {}
        
        # Get parameters
        hardware_type = data.get('hardware_type')
        hardware_path = data.get('hardware_path')
        
        if not hardware_type or not hardware_path:
            return jsonify({'success': False, 'error': 'Hardware wallet type and path are required'})
        
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
        current_app.logger.error(f"Error integrating hardware wallet: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/wallet/<int:wallet_id>/secure_key', methods=['POST'])
@login_required
def secure_private_key(wallet_id):
    """API endpoint for securing private key"""
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({'success': False, 'error': 'Wallet not found'})
        
        # Get request data
        data = request.get_json()
        
        # Validate required fields
        private_key = data.get('private_key')
        password = data.get('password')
        
        if not private_key or not password:
            return jsonify({'success': False, 'error': 'Private key and password are required'})
        
        # Initialize security service
        security_service = WalletSecurityService(current_user.id)
        
        # Encrypt private key
        encrypted_data = security_service.encrypt_private_key(private_key, password, current_user.id)
        
        # Save encrypted data to wallet
        wallet.private_key_encrypted = json.dumps(encrypted_data)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Private key secured successfully'
        })
    except Exception as e:
        current_app.logger.error(f"Error securing private key: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/wallet/<int:wallet_id>/export_key', methods=['POST'])
@login_required
def export_private_key(wallet_id):
    """API endpoint for exporting private key"""
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({'success': False, 'error': 'Wallet not found'})
        
        # Check if wallet has encrypted private key
        if not wallet.private_key_encrypted:
            return jsonify({'success': False, 'error': 'Wallet does not have an encrypted private key'})
        
        # Get request data
        data = request.get_json()
        
        # Validate required fields
        password = data.get('password')
        create_session = data.get('create_session', False)
        
        if not password:
            return jsonify({'success': False, 'error': 'Password is required'})
        
        # Initialize security service
        security_service = WalletSecurityService(current_user.id)
        
        # Decrypt private key
        encrypted_data = json.loads(wallet.private_key_encrypted)
        private_key = security_service.decrypt_private_key(encrypted_data, password, current_user.id)
        
        # Create session key if requested
        session_key = None
        if create_session:
            session_key = security_service.create_session_key(wallet_id, 30)
        
        return jsonify({
            'success': True,
            'private_key': private_key,
            'session_key': session_key
        })
    except Exception as e:
        current_app.logger.error(f"Error exporting private key: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/wallet/key_fragments', methods=['POST'])
@login_required
def generate_key_fragments():
    """API endpoint for generating key fragments"""
    try:
        # Get request data
        data = request.get_json()
        
        # Validate required fields
        private_key = data.get('private_key')
        wallet_id = data.get('wallet_id')
        password = data.get('password')
        num_shares = data.get('num_shares', 3)
        threshold = data.get('threshold', 2)
        
        # Check if using wallet ID and password
        if wallet_id and password:
            wallet = Wallet.query.get(wallet_id)
            if not wallet:
                return jsonify({'success': False, 'error': 'Wallet not found'})
            
            # Check if wallet has encrypted private key
            if not wallet.private_key_encrypted:
                return jsonify({'success': False, 'error': 'Wallet does not have an encrypted private key'})
            
            # Initialize security service
            security_service = WalletSecurityService(current_user.id)
            
            # Decrypt private key
            encrypted_data = json.loads(wallet.private_key_encrypted)
            private_key = security_service.decrypt_private_key(encrypted_data, password, current_user.id)
        
        # Check if we have a private key
        if not private_key:
            return jsonify({'success': False, 'error': 'Private key is required'})
        
        # Initialize security service
        security_service = WalletSecurityService(current_user.id)
        
        # Generate key fragments
        fragments = security_service.generate_key_fragments(private_key, num_shares, threshold)
        
        return jsonify({
            'success': True,
            'fragments': fragments,
            'threshold': threshold,
            'total_shares': num_shares
        })
    except Exception as e:
        current_app.logger.error(f"Error generating key fragments: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/backup_wallets', methods=['POST'])
@login_required
def backup_wallets():
    """API endpoint for backing up wallets"""
    try:
        # Get request data
        data = request.get_json()
        
        # Validate required fields
        wallet_ids = data.get('wallet_ids', [])
        backup_password = data.get('backup_password')
        include_private_keys = data.get('include_private_keys', True)
        
        if not wallet_ids:
            return jsonify({'success': False, 'error': 'At least one wallet ID is required'})
        
        if not backup_password:
            return jsonify({'success': False, 'error': 'Backup password is required'})
        
        # Get wallets
        wallets = Wallet.query.filter(Wallet.id.in_(wallet_ids)).all()
        if not wallets:
            return jsonify({'success': False, 'error': 'No valid wallets found'})
        
        # Initialize security service
        security_service = WalletSecurityService(current_user.id)
        
        # Create backup data
        backup_data = []
        for wallet in wallets:
            wallet_data = {
                'id': wallet.id,
                'address': wallet.address,
                'chain': wallet.chain,
                'native_balance': wallet.native_balance,
                'usd_balance': wallet.usd_balance,
                'is_active': wallet.is_active,
                'is_contract': wallet.is_contract,
                'last_updated': wallet.last_updated.isoformat() if wallet.last_updated else None,
                'metadata': wallet.metadata
            }
            
            # Include private key if requested
            if include_private_keys and wallet.private_key_encrypted:
                wallet_data['private_key_encrypted'] = wallet.private_key_encrypted
            
            backup_data.append(wallet_data)
        
        # Encrypt backup data
        encrypted_backup = security_service.encrypt_private_key(json.dumps(backup_data), backup_password)
        
        # Create backup file content
        backup_file = {
            'version': '1.0',
            'created_at': datetime.utcnow().isoformat(),
            'user_id': current_user.id,
            'wallet_count': len(wallets),
            'encrypted_data': encrypted_backup
        }
        
        return jsonify({
            'success': True,
            'message': f'Created backup of {len(wallets)} wallets',
            'backup_file': backup_file
        })
    except Exception as e:
        current_app.logger.error(f"Error backing up wallets: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/restore_wallets', methods=['POST'])
@login_required
def restore_wallets():
    """API endpoint for restoring wallets from backup"""
    try:
        # Get request data (backup file is in JSON format)
        data = request.get_json()
        
        # Validate required fields
        backup_file = data.get('backup_file')
        backup_password = data.get('backup_password')
        restore_private_keys = data.get('restore_private_keys', True)
        
        if not backup_file or not backup_password:
            return jsonify({'success': False, 'error': 'Backup file and password are required'})
        
        # Validate backup file format
        if not isinstance(backup_file, dict) or 'encrypted_data' not in backup_file:
            return jsonify({'success': False, 'error': 'Invalid backup file format'})
        
        # Initialize security service
        security_service = WalletSecurityService(current_user.id)
        
        # Decrypt backup data
        try:
            encrypted_data = backup_file.get('encrypted_data')
            decrypted_data = security_service.decrypt_private_key(encrypted_data, backup_password)
            wallet_data_list = json.loads(decrypted_data)
        except Exception as e:
            return jsonify({'success': False, 'error': f'Failed to decrypt backup: {str(e)}'})
        
        # Restore wallets
        restored_wallets = []
        skipped_wallets = []
        
        for wallet_data in wallet_data_list:
            # Check if wallet already exists
            existing_wallet = Wallet.query.filter_by(
                address=wallet_data.get('address'),
                chain=wallet_data.get('chain')
            ).first()
            
            if existing_wallet:
                skipped_wallets.append({
                    'address': wallet_data.get('address'),
                    'chain': wallet_data.get('chain'),
                    'reason': 'Already exists'
                })
                continue
            
            # Create new wallet
            new_wallet = Wallet(
                address=wallet_data.get('address'),
                chain=wallet_data.get('chain'),
                native_balance=wallet_data.get('native_balance', 0),
                usd_balance=wallet_data.get('usd_balance', 0),
                is_active=wallet_data.get('is_active', True),
                is_contract=wallet_data.get('is_contract', False),
                metadata=wallet_data.get('metadata'),
                last_updated=datetime.utcnow()
            )
            
            # Restore private key if requested
            if restore_private_keys and 'private_key_encrypted' in wallet_data:
                new_wallet.private_key_encrypted = wallet_data.get('private_key_encrypted')
            
            # Save to database
            db.session.add(new_wallet)
            
            restored_wallets.append({
                'address': new_wallet.address,
                'chain': new_wallet.chain,
                'has_private_key': bool(new_wallet.private_key_encrypted)
            })
        
        # Commit changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Restored {len(restored_wallets)} wallets, skipped {len(skipped_wallets)}',
            'restored_wallets': restored_wallets,
            'skipped_wallets': skipped_wallets
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error restoring wallets: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/generate_recovery_phrase', methods=['POST'])
@login_required
def generate_recovery_phrase():
    """API endpoint for generating recovery phrase"""
    try:
        # Get request data
        data = request.get_json() or {}
        
        # Get parameters
        phrase_length = data.get('phrase_length', 24)
        
        # Only 12 or 24 words are supported
        if phrase_length not in [12, 24]:
            phrase_length = 24
        
        # Initialize security service
        security_service = WalletSecurityService(current_user.id)
        
        # Generate mnemonic (not implemented in this example)
        # In a real implementation, this would use a library like bip39
        import random
        word_list = ["abandon", "ability", "able", "about", "above", "absent", "absorb", "abstract", 
                     "absurd", "abuse", "access", "accident", "account", "accuse", "achieve", "acid", 
                     "acoustic", "acquire", "across", "act", "action", "actor", "actress", "actual", 
                     "adapt", "add", "addict", "address", "adjust", "admit", "adult", "advance", 
                     "advice", "aerobic", "affair", "afford", "afraid", "again", "age", "agent", 
                     "agree", "ahead", "aim", "air", "airport", "aisle", "alarm", "album", 
                     "alcohol", "alert", "alien", "all", "alley", "allow", "almost", "alone", 
                     "alpha", "already", "also", "alter", "always", "amateur", "amazing", "among"]
        
        # Generate random words
        mnemonic = " ".join(random.sample(word_list, phrase_length))
        
        return jsonify({
            'success': True,
            'phrase_length': phrase_length,
            'mnemonic': mnemonic,
            'words': mnemonic.split()
        })
    except Exception as e:
        current_app.logger.error(f"Error generating recovery phrase: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/recover_wallet', methods=['POST'])
@login_required
def recover_wallet():
    """API endpoint for recovering wallet from mnemonic"""
    try:
        # Get request data
        data = request.get_json()
        
        # Validate required fields
        recovery_phrase = data.get('recovery_phrase')
        derivation_path = data.get('derivation_path', "m/44'/60'/0'/0/0")
        chain = data.get('chain')
        
        if not recovery_phrase or not chain:
            return jsonify({'success': False, 'error': 'Recovery phrase and chain are required'})
        
        # Check if chain exists
        chain_info = ChainInfo.query.filter_by(name=chain).first()
        if not chain_info:
            return jsonify({'success': False, 'error': f'Chain {chain} not found'})
        
        # Initialize security service
        security_service = WalletSecurityService(current_user.id)
        
        # Simulate wallet recovery (not implemented in this example)
        # In a real implementation, this would derive the private key from the mnemonic
        import random
        address = f"0x{random.randint(0, 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF):040x}"
        private_key = f"0x{random.randint(0, 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF):064x}"
        
        # Create new wallet
        new_wallet = Wallet(
            address=address,
            chain=chain,
            native_balance=0,
            usd_balance=0,
            is_active=True,
            is_contract=False,
            last_updated=datetime.utcnow()
        )
        
        # Save to database
        db.session.add(new_wallet)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Wallet recovered successfully',
            'wallet': {
                'id': new_wallet.id,
                'address': address,
                'chain': chain,
                'private_key': private_key  # Only for demonstration, never return this in production
            }
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error recovering wallet: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})logger.error(f"Error scanning tokens: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/token/add', methods=['POST'])
@login_required
def add_custom_token():
    """API endpoint for adding custom token"""
    try:
        # Get request data
        data = request.get_json()
        
        # Validate required fields
        wallet_id = data.get('wallet_id')
        token_address = data.get('token_address')
        
        if not wallet_id or not token_address:
            return jsonify({'success': False, 'error': 'Wallet ID and token address are required'})
        
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({'success': False, 'error': 'Wallet not found'})
        
        # Optional fields
        symbol = data.get('symbol')
        name = data.get('name')
        decimals = data.get('decimals')
        
        # Initialize token discovery service
        discovery_service = TokenDiscoveryService(wallet.chain)
        
        # Add custom token
        token = discovery_service.add_custom_token(
            wallet_id=wallet_id,
            token_address=token_address,
            symbol=symbol,
            name=name,
            decimals=decimals
        )
        
        return jsonify({
            'success': True,
            'message': f'Added token {token.symbol}',
            'token': token.to_dict()
        })
    except Exception as e:
        current_app.logger.error(f"Error adding custom token: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/token/refresh', methods=['POST'])
@login_required
def refresh_tokens():
    """API endpoint for refreshing token balances"""
    try:
        # Get request data
        data = request.get_json()
        
        # Validate wallet ID
        wallet_id = data.get('wallet_id')
        if not wallet_id:
            return jsonify({'success': False, 'error': 'Wallet ID is required'})
        
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({'success': False, 'error': 'Wallet not found'})
        
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
        current_app.logger.error(f"Error refreshing tokens: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/token/<int:token_id>/details')
@login_required
def token_details(token_id):
    """API endpoint for token details"""
    try:
        token = Token.query.get(token_id)
        if not token:
            return jsonify({'success': False, 'error': 'Token not found'})
        
        wallet = Wallet.query.get(token.wallet_id)
        if not wallet:
            return jsonify({'success': False, 'error': 'Wallet not found'})
        
        # Initialize token discovery service
        discovery_service = TokenDiscoveryService(wallet.chain)
        
        # Get token analytics
        analytics = discovery_service.get_token_analytics(token_id)
        
        return jsonify({
            'success': True,
            'token': analytics
        })
    except Exception as e:
        current_app.logger.error(f"Error getting token details: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/token/<int:token_id>/price_history')
@login_required
def token_price_history(token_id):
    """API endpoint for token price history"""
    try:
        token = Token.query.get(token_id)
        if not token:
            return jsonify({'success': False, 'error': 'Token not found'})
        
        wallet = Wallet.query.get(token.wallet_id)
        if not wallet:
            return jsonify({'success': False, 'error': 'Wallet not found'})
        
        # Get days parameter
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
        current_app.logger.error(f"Error getting token price history: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/token_lists')
@login_required
def get_token_lists():
    """API endpoint for token lists"""
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
        current_app.logger.error(f"Error getting token lists: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/token_list/import', methods=['POST'])
@login_required
def import_token_list():
    """API endpoint for importing token list"""
    try:
        # Get request data
        data = request.get_json()
        
        # Validate required fields
        name = data.get('name')
        url = data.get('url')
        chain = data.get('chain')
        
        if not name or not url or not chain:
            return jsonify({'success': False, 'error': 'Name, URL, and chain are required'})
        
        # Initialize token discovery service
        discovery_service = TokenDiscoveryService(chain)
        
        # Import token list
        token_list = discovery_service.import_token_list(name, url, chain)
        
        return jsonify({
            'success': True,
            'message': f'Imported {token_list.tokens_count} tokens',
            'token_list': token_list.to_dict()
        })
    except Exception as e:
        current_app.logger.error(f"Error importing token list: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

#
# API Endpoints for Transaction History
#

@wallet_bp.route('/api/wallet/<int:wallet_id>/transactions')
@login_required
def wallet_transactions(wallet_id):
    """API endpoint for wallet transactions"""
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({'success': False, 'error': 'Wallet not found'})
        
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
                return jsonify({'success': False, 'error': f'Invalid start_date format: {start_date}'})
        
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date)
            except ValueError:
                return jsonify({'success': False, 'error': f'Invalid end_date format: {end_date}'})
        
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
        current_app.logger.error(f"Error getting wallet transactions: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/wallet/<int:wallet_id>/sync_transactions', methods=['POST'])
@login_required
def sync_wallet_transactions(wallet_id):
    """API endpoint for syncing wallet transactions"""
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({'success': False, 'error': 'Wallet not found'})
        
        # Get request data
        data = request.get_json() or {}
        
        # Get parameters
        token_id = data.get('token_id')
        start_block = data.get('start_block')
        
        # Initialize history service
        history_service = TransactionHistoryService(wallet.chain)
        
        # Sync native transactions
        native_result = history_service.sync_native_transactions(wallet_id, start_block)
        
        # Sync token transactions if specified
        token_result = None
        if token_id:
            # Initialize token discovery service
            discovery_service = TokenDiscoveryService(wallet.chain)
            
            # Sync token transactions
            token_result = discovery_service.sync_token_transactions(wallet_id, token_id, start_block)
        
        return jsonify({
            'success': True,
            'native_sync': native_result,
            'token_sync': token_result
        })
    except Exception as e:
        current_app.logger.error(f"Error syncing wallet transactions: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/wallet/<int:wallet_id>/transaction_summary')
@login_required
def transaction_summary(wallet_id):
    """API endpoint for transaction summary"""
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({'success': False, 'error': 'Wallet not found'})
        
        # Get period parameter
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
        current_app.logger.error(f"Error getting transaction summary: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/wallet/<int:wallet_id>/gas_analytics')
@login_required
def gas_analytics(wallet_id):
    """API endpoint for gas analytics"""
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({'success': False, 'error': 'Wallet not found'})
        
        # Get period parameter
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
        current_app.logger.error(f"Error getting gas analytics: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/wallet/<int:wallet_id>/export_transactions', methods=['POST'])
@login_required
def export_transactions(wallet_id):
    """API endpoint for exporting transactions"""
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({'success': False, 'error': 'Wallet not found'})
        
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
                return jsonify({'success': False, 'error': f'Invalid start_date format: {start_date}'})
        
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date)
            except ValueError:
                return jsonify({'success': False, 'error': f'Invalid end_date format: {end_date}'})
        
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
        current_app.logger.error(f"Error exporting transactions: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/wallet/<int:wallet_id>/transaction_patterns')
@login_required
def transaction_patterns(wallet_id):
    """API endpoint for transaction pattern analysis"""
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({'success': False, 'error': 'Wallet not found'})
        
        # Get period parameter
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
        current_app.logger.error(f"Error analyzing transaction patterns: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

#
# API Endpoints for Balance Analytics
#

@wallet_bp.route('/api/wallet/<int:wallet_id>/balance_history')
@login_required
def wallet_balance_history(wallet_id):
    """API endpoint for wallet balance history"""
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({'success': False, 'error': 'Wallet not found'})
        
        # Get days parameter
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
    except Exception as e:
        current_app.logger.error(f"Error getting balance history: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/portfolio_composition')
@login_required
def portfolio_composition():
    """API endpoint for portfolio composition"""
    try:
        # Get wallet IDs parameter (comma-separated list)
        wallet_ids_param = request.args.get('wallet_ids', '')
        include_zero_balances = request.args.get('include_zero_balances', 'false').lower() == 'true'
        
        # Parse wallet IDs
        if wallet_ids_param:
            wallet_ids = [int(id.strip()) for id in wallet_ids_param.split(',') if id.strip().isdigit()]
        else:
            # Use all wallets if not specified
            wallets = Wallet.query.all()
            wallet_ids = [wallet.id for wallet in wallets]
        
        # Initialize balance analytics service
        analytics_service = BalanceAnalyticsService(current_user.id)
        
        # Get portfolio composition
        composition = analytics_service.get_portfolio_composition(wallet_ids, include_zero_balances)
        
        return jsonify({
            'success': True,
            'composition': composition
        })
    except Exception as e:
        current_app.logger.error(f"Error getting portfolio composition: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/wallet/<int:wallet_id>/profit_loss')
@login_required
def wallet_profit_loss(wallet_id):
    """API endpoint for wallet profit/loss calculation"""
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({'success': False, 'error': 'Wallet not found'})
        
        # Get period parameter
        period = request.args.get('period', '30d')
        
        # Initialize balance analytics service
        analytics_service = BalanceAnalyticsService(current_user.id)
        
        # Calculate profit/loss
        profit_loss = analytics_service.calculate_profit_loss(wallet_id, period)
        
        return jsonify({
            'success': True,
            'wallet_id': wallet_id,
            'period': period,
            'profit_loss': profit_loss
        })
    except Exception as e:
        current_app.logger.error(f"Error calculating profit/loss: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/compare_wallets', methods=['POST'])
@login_required
def compare_wallets():
    """API endpoint for comparing wallet performance"""
    try:
        # Get request data
        data = request.get_json()
        
        # Validate wallet IDs
        wallet_ids = data.get('wallet_ids', [])
        if not wallet_ids:
            return jsonify({'success': False, 'error': 'Wallet IDs are required'})
        
        # Get period parameter
        period = data.get('period', '30d')
        
        # Initialize balance analytics service
        analytics_service = BalanceAnalyticsService(current_user.id)
        
        # Compare wallets
        comparison = analytics_service.compare_wallets(wallet_ids, period)
        
        return jsonify({
            'success': True,
            'period': period,
            'comparison': comparison
        })
    except Exception as e:
        current_app.logger.error(f"Error comparing wallets: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/cross_chain_value')
@login_required
def cross_chain_value():
    """API endpoint for cross-chain value aggregation"""
    try:
        # Initialize balance analytics service
        analytics_service = BalanceAnalyticsService(current_user.id)
        
        # Get cross-chain value
        cross_chain = analytics_service.calculate_cross_chain_value(current_user.id)
        
        return jsonify({
            'success': True,
            'cross_chain_value': cross_chain
        })
    except Exception as e:
        current_app.logger.error(f"Error calculating cross-chain value: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/wallet/<int:wallet_id>/risk_assessment')
@login_required
def wallet_risk_assessment(wallet_id):
    """API endpoint for wallet risk assessment"""
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({'success': False, 'error': 'Wallet not found'})
        
        # Initialize balance analytics service
        analytics_service = BalanceAnalyticsService(current_user.id)
        
        # Get risk assessment
        risk = analytics_service.get_risk_assessment(wallet_id)
        
        return jsonify({
            'success': True,
            'wallet_id': wallet_id,
            'risk_assessment': risk
        })
    except Exception as e:
        current_app.logger.error(f"Error getting risk assessment: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

#
# API Endpoints for Wallet Security
#

@wallet_bp.route('/api/wallet/<int:wallet_id>/permissions')
@login_required
def wallet_permissions(wallet_id):
    """API endpoint for wallet permissions"""
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({'success': False, 'error': 'Wallet not found'})
        
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
        current_app.logger.error(f"Error getting wallet permissions: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@wallet_bp.route('/api/wallet/<int:wallet_id>/create_permission', methods=['POST'])
@login_required
def create_wallet_permission(wallet_id):
    """API endpoint for creating wallet permission"""
    try:
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return jsonify({'success': False, 'error': 'Wallet not found'})
        
        # Get request data
        data = request.get_json()
        
        # Validate required fields
        user_id = data.get('user_id')
        permission_level = data.get('permission_level', 'read')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID is required'})
        
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
        current_app."""
Wallet Routes
Flask Blueprint for wallet-related routes
"""
from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for, session
from flask_login import login_required, current_user
from app import db
from app.models.wallet import Wallet, ChainInfo, Token
from app.models.enhanced_token import TokenList, TokenTransaction
from app.models.balance_history import WalletBalanceHistory
from app.models.user import User, UserPermission
from app.services.token_discovery_service import TokenDiscoveryService
from app.services.transaction_history_service import TransactionHistoryService
from app.services.wallet_security_service import WalletSecurityService
from app.services.balance_analytics_service import BalanceAnalyticsService
from app.utils.web3_helper import get_web3_for_chain, get_token_balance, get_token_price
from datetime import datetime, timedelta
import json

# Create blueprint
wallet_bp = Blueprint('wallet', __name__)

@wallet_bp.route('/wallets')
@login_required
def wallets():
    """Wallet management page"""
    # Get all wallets
    wallets = Wallet.query.all()
    
    # Get all chains
    chains = ChainInfo.query.all()
    
    # Prepare chain info mapping
    chain_info = {}
    for chain in chains:
        chain_info[chain.name] = {
            'currency_symbol': chain.currency_symbol,
            'explorer_url': chain.explorer_url
        }
    
    return render_template('dashboard/wallets.html', 
                           wallets=wallets,
                           chains=chains,
                           chain_info=chain_info,
                           title='Wallet Management')

@wallet_bp.route('/tokens')
@login_required
def tokens():
    """Token discovery and management page"""
    # Get all wallets
    wallets = Wallet.query.all()
    
    # Get all chains
    chains = ChainInfo.query.all()
    
    # Get all tokens
    tokens = Token.query.all()
    
    # Enhance token data with wallet address
    for token in tokens:
        wallet = Wallet.query.get(token.wallet_id)
        if wallet:
            token.wallet_address = wallet.address
        else:
            token.wallet_address = "Unknown"
    
    # Get all token lists
    token_lists = TokenList.query.all()
    
    # Prepare chain info mapping
    chain_info = {}
    for chain in chains:
        chain_info[chain.name] = {
            'currency_symbol': chain.currency_symbol,
            'explorer_url': chain.explorer_url
        }
    
    return render_template('dashboard/tokens.html', 
                           wallets=wallets,
                           chains=chains,
                           tokens=tokens,
                           token_lists=token_lists,
                           chain_info=chain_info,
                           title='Token Management')

@wallet_bp.route('/transactions')
@login_required
def transactions():
    """Transaction history page"""
    # Get all wallets
    wallets = Wallet.query.all()
    
    # Get all chains
    chains = ChainInfo.query.all()
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Get transactions with pagination
    query = TokenTransaction.query.order_by(TokenTransaction.timestamp.desc())
    pagination = {
        'page': page,
        'per_page': per_page,
        'total': query.count(),
        'pages': (query.count() + per_page - 1) // per_page
    }
    transactions = query.paginate(page=page, per_page=per_page, error_out=False).items
    
    # Enhance transaction data
    for tx in transactions:
        # Get token symbol
        if tx.token_id:
            token = Token.query.get(tx.token_id)
            if token:
                tx.token_symbol = token.symbol
                tx.token_logo_url = token.logo_url
            else:
                tx.token_symbol = None
                tx.token_logo_url = None
        else:
            tx.token_symbol = None
            tx.token_logo_url = None
    
    # Calculate transaction summary
    total_transactions = TokenTransaction.query.count()
    
    # Calculate total received/sent (only consider transactions with USD value)
    total_received = sum(tx.usd_value or 0 for tx in TokenTransaction.query.filter_by(tx_type='receive').all())
    total_sent = sum(tx.usd_value or 0 for tx in TokenTransaction.query.filter_by(tx_type='send').all())
    
    # Calculate gas spent
    total_gas_spent = sum(tx.gas_cost_usd or 0 for tx in TokenTransaction.query.all())
    
    # Get most active tokens
    most_active_tokens = []
    try:
        # Initialize transaction history service
        history_service = TransactionHistoryService()
        summary = history_service.generate_transaction_summary(None, '30d')
        most_active_tokens = summary.get('most_active_tokens', [])
    except Exception as e:
        current_app.logger.error(f"Error generating transaction summary: {str(e)}")
    
    # Prepare chain info mapping
    chain_info = {}
    for chain in chains:
        chain_info[chain.name] = {
            'currency_symbol': chain.currency_symbol,
            'explorer_url': chain.explorer_url
        }
    
    return render_template('dashboard/transactions.html',
                           wallets=wallets,
                           chains=chains,
                           transactions=transactions,
                           pagination=pagination,
                           total_transactions=total_transactions,
                           total_received=total_received,
                           total_sent=total_sent,
                           total_gas_spent=total_gas_spent,
                           most_active_tokens=most_active_tokens,
                           chain_info=chain_info,
                           title='Transaction History')

@wallet_bp.route('/analytics')
@login_required
def analytics():
    """Balance analytics page"""
    # Get all wallets
    wallets = Wallet.query.all()
    
    # Get all tokens
    tokens = Token.query.all()
    
    # Calculate total portfolio value
    total_portfolio_value = sum(wallet.usd_balance for wallet in wallets)
    total_portfolio_value += sum(token.usd_value for token in tokens)
    
    # Calculate profit/loss for the last 30 days
    profit_loss_30d = 0
    profit_loss_pct_30d = 0
    
    try:
        # Initialize balance analytics service
        analytics_service = BalanceAnalyticsService(current_user.id)
        
        # Add some dummy wallet analytics data for the UI
        for wallet in wallets:
            # Random 30d change percentage between -20% and +40%
            import random
            wallet.change_30d = random.uniform(-20, 40)
        
        # Get cross-chain value distribution
        cross_chain_value = analytics_service.calculate_cross_chain_value(current_user.id)
        
        # Get top performing tokens (sort by value)
        top_tokens = sorted(tokens, key=lambda x: x.usd_value, reverse=True)[:10]
        
        # Add 7d price change
        for token in top_tokens:
            # Random 7d change percentage between -15% and +25%
            token.price_7d_change = random.uniform(-15, 25)
    
    except Exception as e:
        current_app.logger.error(f"Error calculating analytics: {str(e)}")
        cross_chain_value = {'chains': [], 'tokens': [], 'total_usd_value': 0}
        top_tokens = []
    
    return render_template('dashboard/analytics.html',
                           wallets=wallets,
                           tokens=tokens,
                           total_portfolio_value=total_portfolio_value,
                           profit_loss_30d=profit_loss_30d,
                           profit_loss_pct_30d=profit_loss_pct_30d,
                           cross_chain_value=cross_chain_value,
                           top_tokens=top_tokens,
                           title='Balance Analytics')

@wallet_bp.route('/security')
@login_required
def security():
    """Wallet security page"""
    # Get all wallets
    wallets = Wallet.query.all()
    
    # Get all users
    users = User.query.all()
    
    # Get active chains
    active_chains = ChainInfo.query.filter_by(status='active').all()
    
    # Add dummy security data for UI
    secured_wallets_count = 0
    for wallet in wallets:
        # Random security score between 20 and 95
        wallet.security_score = random.randint(20, 95)
        
        # Random permissions list
        wallet.permissions = []
        for i in range(random.randint(1, 3)):
            wallet.permissions.append({
                'user_id': i + 1,
                'username': f'User {i + 1}',
                'permission_level': random.choice(['read', 'write', 'admin'])
            })
        
        # Random hardware wallet info
        if random.random() > 0.7:  # 30% chance
            wallet.hardware_wallet = {
                'type': 'Ledger Nano S',   # Example type
                'firmware_version': '1.6.0',
                'last_sync': datetime.utcnow().isoformat()
            }
        else:
            wallet.hardware_wallet = None
            