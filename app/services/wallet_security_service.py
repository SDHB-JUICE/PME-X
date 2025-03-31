"""
Wallet Security Service
Enhanced security features for wallet management
"""
import os
import json
import base64
import hashlib
import secrets
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
import shamir_mnemonic
from flask import session, current_app
from app import db
from app.models.wallet import Wallet
from app.models.user import User, Permission, Role, UserPermission

class WalletSecurityService:
    """Service for wallet security management"""
    
    def __init__(self, user_id=None):
        """Initialize wallet security service
        
        Args:
            user_id (int, optional): User ID
        """
        self.user_id = user_id
        self.user = None
        
        if user_id:
            self.user = User.query.get(user_id)
    
    def encrypt_private_key(self, private_key, password, user_id=None):
        """Encrypt private key with AES-256 using user specific encryption key
        
        Args:
            private_key (str): Private key to encrypt
            password (str): Password for encryption
            user_id (int, optional): User ID for user-specific encryption
            
        Returns:
            dict: Encrypted data with metadata
        """
        if not private_key or not password:
            raise ValueError("Private key and password are required")
        
        # Create a key derived from the password
        password_bytes = password.encode('utf-8')
        salt = os.urandom(16)
        
        # User specific salt addition for enhanced security
        if user_id:
            user_salt = hashlib.sha256(f"user_{user_id}_salt".encode('utf-8')).digest()[:8]
            combined_salt = salt + user_salt
        else:
            combined_salt = salt
        
        # Create key using PBKDF2
        key = hashlib.pbkdf2_hmac('sha256', password_bytes, combined_salt, 100000)
        
        # Generate initialization vector
        iv = os.urandom(16)
        
        # Create cipher
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        # Pad the private key
        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        private_key_bytes = private_key.encode('utf-8')
        padded_data = padder.update(private_key_bytes) + padder.finalize()
        
        # Encrypt the padded data
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
        
        # Encode the encrypted data and parameters for storage
        result = {
            'salt': base64.b64encode(salt).decode('utf-8'),
            'iv': base64.b64encode(iv).decode('utf-8'),
            'encrypted_data': base64.b64encode(encrypted_data).decode('utf-8'),
            'user_id': user_id,
            'version': '1.0',
            'algorithm': 'AES-256-CBC'
        }
        
        return result
    
    def decrypt_private_key(self, encrypted_data, password, user_id=None):
        """Decrypt private key
        
        Args:
            encrypted_data (dict): Encrypted data dictionary
            password (str): Password for decryption
            user_id (int, optional): User ID for user-specific decryption
            
        Returns:
            str: Decrypted private key
        """
        if not encrypted_data or not password:
            raise ValueError("Encrypted data and password are required")
        
        # Extract parameters
        salt = base64.b64decode(encrypted_data['salt'])
        iv = base64.b64decode(encrypted_data['iv'])
        encrypted_bytes = base64.b64decode(encrypted_data['encrypted_data'])
        
        # User specific salt addition for enhanced security
        if user_id:
            user_salt = hashlib.sha256(f"user_{user_id}_salt".encode('utf-8')).digest()[:8]
            combined_salt = salt + user_salt
        else:
            combined_salt = salt
        
        # Derive key from password
        password_bytes = password.encode('utf-8')
        key = hashlib.pbkdf2_hmac('sha256', password_bytes, combined_salt, 100000)
        
        # Create cipher
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        
        # Decrypt the data
        padded_data = decryptor.update(encrypted_bytes) + decryptor.finalize()
        
        # Remove padding
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        private_key_bytes = unpadder.update(padded_data) + unpadder.finalize()
        
        return private_key_bytes.decode('utf-8')
    
    def generate_key_fragments(self, private_key, num_shares=3, threshold=2):
        """Generate key fragments using Shamir's Secret Sharing
        
        Args:
            private_key (str): Private key to split
            num_shares (int): Number of shares to generate
            threshold (int): Minimum number of shares needed to reconstruct
            
        Returns:
            list: List of mnemonic phrases representing shares
        """
        if not private_key:
            raise ValueError("Private key is required")
        
        if num_shares < threshold:
            raise ValueError("Number of shares must be greater than or equal to threshold")
        
        # Convert private key to bytes (must be 16, 20, 24, 28, or 32 bytes)
        # We'll normalize to 32 bytes by hashing if necessary
        if len(private_key) != 64:  # Not a 32-byte hex string
            private_key_bytes = hashlib.sha256(private_key.encode('utf-8')).digest()
        else:
            # Assuming it's a hex string representation of bytes
            private_key_bytes = bytes.fromhex(private_key)
        
        # Generate random identifier (1 to 31)
        identifier = secrets.randbelow(31) + 1
        
        # Split secret into shares
        shares = shamir_mnemonic.generate_mnemonics(
            threshold=threshold,
            shares_count=num_shares,
            secret=private_key_bytes,
            identifier=identifier
        )
        
        return shares
    
    def recover_private_key_from_fragments(self, mnemonics):
        """Recover private key from mnemonic fragments
        
        Args:
            mnemonics (list): List of mnemonic phrases
            
        Returns:
            str: Recovered private key
        """
        if not mnemonics:
            raise ValueError("Mnemonic phrases are required")
        
        # Validate and combine shares
        try:
            # Combine shares to recover secret
            secret_bytes = shamir_mnemonic.combine_mnemonics(mnemonics)
            
            # Convert bytes to hex string representation
            private_key = secret_bytes.hex()
            
            return private_key
        except Exception as e:
            raise ValueError(f"Failed to recover private key: {str(e)}")
    
    def create_session_key(self, wallet_id, expiry_minutes=30):
        """Create a session-based encryption key for sensitive operations
        
        Args:
            wallet_id (int): Wallet ID
            expiry_minutes (int): Session key expiry in minutes
            
        Returns:
            str: Session key for sensitive operations
        """
        if not self.user_id:
            raise ValueError("User ID is required for session key creation")
        
        # Generate a random session key
        session_key = Fernet.generate_key().decode('utf-8')
        
        # Store in session with expiry time
        from datetime import datetime, timedelta
        expiry_time = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        
        session['wallet_session_keys'] = session.get('wallet_session_keys', {})
        session['wallet_session_keys'][str(wallet_id)] = {
            'key': session_key,
            'expiry': expiry_time.isoformat(),
            'user_id': self.user_id
        }
        
        return session_key
    
    def validate_session_key(self, wallet_id, session_key):
        """Validate session key for sensitive operations
        
        Args:
            wallet_id (int): Wallet ID
            session_key (str): Session key to validate
            
        Returns:
            bool: True if session key is valid
        """
        wallet_session_keys = session.get('wallet_session_keys', {})
        wallet_key_data = wallet_session_keys.get(str(wallet_id))
        
        if not wallet_key_data:
            return False
        
        # Check if key matches
        if wallet_key_data['key'] != session_key:
            return False
        
        # Check if key belongs to current user
        if wallet_key_data['user_id'] != self.user_id:
            return False
        
        # Check expiry
        from datetime import datetime
        expiry_time = datetime.fromisoformat(wallet_key_data['expiry'])
        if datetime.utcnow() > expiry_time:
            # Remove expired key
            del wallet_session_keys[str(wallet_id)]
            session['wallet_session_keys'] = wallet_session_keys
            return False
        
        return True
    
    def create_wallet_permission(self, wallet_id, user_id, permission_level='read'):
        """Create or update wallet permission for a user
        
        Args:
            wallet_id (int): Wallet ID
            user_id (int): User ID to grant permission
            permission_level (str): Permission level (read, write, admin)
            
        Returns:
            UserPermission: Created or updated permission
        """
        if not self.user_id:
            raise ValueError("User ID is required to create permissions")
        
        # Check if wallet exists
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet with ID {wallet_id} not found")
        
        # Check if user exists
        user = User.query.get(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")
        
        # Check if current user has admin permission
        admin_permission = UserPermission.query.filter_by(
            user_id=self.user_id,
            resource_type='wallet',
            resource_id=wallet_id,
            permission_level='admin'
        ).first()
        
        if not admin_permission and self.user_id != current_app.config.get('ADMIN_USER_ID'):
            raise ValueError("You don't have permission to modify permissions for this wallet")
        
        # Check if permission already exists
        existing_permission = UserPermission.query.filter_by(
            user_id=user_id,
            resource_type='wallet',
            resource_id=wallet_id
        ).first()
        
        if existing_permission:
            # Update existing permission
            existing_permission.permission_level = permission_level
            db.session.commit()
            return existing_permission
        else:
            # Create new permission
            new_permission = UserPermission(
                user_id=user_id,
                resource_type='wallet',
                resource_id=wallet_id,
                permission_level=permission_level
            )
            db.session.add(new_permission)
            db.session.commit()
            return new_permission
    
    def revoke_wallet_permission(self, wallet_id, user_id):
        """Revoke wallet permission for a user
        
        Args:
            wallet_id (int): Wallet ID
            user_id (int): User ID to revoke permission
            
        Returns:
            bool: True if permission was revoked
        """
        if not self.user_id:
            raise ValueError("User ID is required to revoke permissions")
        
        # Check if wallet exists
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet with ID {wallet_id} not found")
        
        # Check if current user has admin permission
        admin_permission = UserPermission.query.filter_by(
            user_id=self.user_id,
            resource_type='wallet',
            resource_id=wallet_id,
            permission_level='admin'
        ).first()
        
        if not admin_permission and self.user_id != current_app.config.get('ADMIN_USER_ID'):
            raise ValueError("You don't have permission to modify permissions for this wallet")
        
        # Find and delete the permission
        permission = UserPermission.query.filter_by(
            user_id=user_id,
            resource_type='wallet',
            resource_id=wallet_id
        ).first()
        
        if permission:
            db.session.delete(permission)
            db.session.commit()
            return True
        
        return False
    
    def check_wallet_permission(self, wallet_id, permission_level='read'):
        """Check if current user has permission for a wallet
        
        Args:
            wallet_id (int): Wallet ID
            permission_level (str): Required permission level (read, write, admin)
            
        Returns:
            bool: True if user has permission
        """
        if not self.user_id:
            return False
        
        # Admin user has all permissions
        if self.user_id == current_app.config.get('ADMIN_USER_ID'):
            return True
        
        # Get user's permission for this wallet
        permission = UserPermission.query.filter_by(
            user_id=self.user_id,
            resource_type='wallet',
            resource_id=wallet_id
        ).first()
        
        if not permission:
            return False
        
        # Check permission level
        if permission_level == 'read':
            # Any level of permission grants read access
            return True
        elif permission_level == 'write':
            # Write or admin permission grants write access
            return permission.permission_level in ['write', 'admin']
        elif permission_level == 'admin':
            # Only admin permission grants admin access
            return permission.permission_level == 'admin'
        
        return False
    
    def get_wallet_permissions(self, wallet_id):
        """Get all permissions for a wallet
        
        Args:
            wallet_id (int): Wallet ID
            
        Returns:
            list: List of permissions
        """
        if not self.user_id:
            raise ValueError("User ID is required to view permissions")
        
        # Check if wallet exists
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet with ID {wallet_id} not found")
        
        # Check if current user has permission to view permissions
        if not self.check_wallet_permission(wallet_id, 'admin') and self.user_id != current_app.config.get('ADMIN_USER_ID'):
            raise ValueError("You don't have permission to view permissions for this wallet")
        
        # Get all permissions for this wallet
        permissions = UserPermission.query.filter_by(
            resource_type='wallet',
            resource_id=wallet_id
        ).all()
        
        # Format permissions
        result = []
        for permission in permissions:
            user = User.query.get(permission.user_id)
            result.append({
                'id': permission.id,
                'user_id': permission.user_id,
                'username': user.username if user else 'Unknown',
                'email': user.email if user else 'Unknown',
                'permission_level': permission.permission_level
            })
        
        return result
    
    def integrate_hardware_wallet(self, wallet_id, hardware_type, hardware_path):
        """Integrate hardware wallet for signing
        
        Args:
            wallet_id (int): Wallet ID
            hardware_type (str): Hardware wallet type (ledger, trezor)
            hardware_path (str): Derivation path
            
        Returns:
            dict: Integration status
        """
        # In a real implementation, you would interface with hardware wallet libraries
        # For this example, we'll just store the metadata
        
        if not self.user_id:
            raise ValueError("User ID is required for hardware wallet integration")
        
        # Check if wallet exists
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet with ID {wallet_id} not found")
        
        # Check if user has permission
        if not self.check_wallet_permission(wallet_id, 'write'):
            raise ValueError("You don't have permission to modify this wallet")
        
        # Store hardware wallet metadata
        hardware_config = {
            'type': hardware_type,
            'path': hardware_path,
            'integrated_by': self.user_id,
            'integrated_at': datetime.utcnow().isoformat(),
            'status': 'active'
        }
        
        # In a real implementation, you would have a dedicated model
        # For this example, we'll store it in wallet metadata
        if not wallet.metadata:
            wallet.metadata = {}
        
        wallet.metadata['hardware_wallet'] = hardware_config
        wallet.private_key_encrypted = None  # Remove private key when using hardware wallet
        db.session.commit()
        
        return {
            'success': True,
            'wallet_id': wallet_id,
            'hardware_type': hardware_type,
            'status': 'integrated'
        }
    
    def perform_security_audit(self, wallet_id):
        """Perform security audit for a wallet
        
        Args:
            wallet_id (int): Wallet ID
            
        Returns:
            dict: Security audit results
        """
        if not self.user_id:
            raise ValueError("User ID is required for security audit")
        
        # Check if wallet exists
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet with ID {wallet_id} not found")
        
        # Check if user has permission
        if not self.check_wallet_permission(wallet_id, 'read'):
            raise ValueError("You don't have permission to view this wallet")
        
        # Initialize audit results
        audit = {
            'wallet_id': wallet_id,
            'timestamp': datetime.utcnow().isoformat(),
            'overall_score': 0,
            'risk_level': 'unknown',
            'security_checks': []
        }
        
        # Perform security checks
        security_checks = []
        
        # Check 1: Private key storage
        if wallet.private_key_encrypted:
            # Check encryption version
            encryption_data = json.loads(wallet.private_key_encrypted)
            if encryption_data.get('version') == '1.0' and encryption_data.get('algorithm') == 'AES-256-CBC':
                security_checks.append({
                    'name': 'private_key_storage',
                    'description': 'Private key is securely encrypted with AES-256-CBC',
                    'status': 'secure',
                    'score': 80
                })
            else:
                security_checks.append({
                    'name': 'private_key_storage',
                    'description': 'Private key encryption uses older or unknown method',
                    'status': 'warning',
                    'score': 50
                })
        elif wallet.metadata and wallet.metadata.get('hardware_wallet'):
            security_checks.append({
                'name': 'private_key_storage',
                'description': 'Private key is secured by hardware wallet',
                'status': 'secure',
                'score': 100
            })
        else:
            security_checks.append({
                'name': 'private_key_storage',
                'description': 'Private key is not stored or encryption status unknown',
                'status': 'unknown',
                'score': 0
            })
        
        # Check 2: Permissions
        permissions = UserPermission.query.filter_by(
            resource_type='wallet',
            resource_id=wallet_id
        ).all()
        
        admin_count = sum(1 for p in permissions if p.permission_level == 'admin')
        
        if admin_count == 0:
            security_checks.append({
                'name': 'permissions',
                'description': 'No admin permissions set - low control',
                'status': 'danger',
                'score': 0
            })
        elif admin_count == 1:
            security_checks.append({
                'name': 'permissions',
                'description': 'Single admin permission - good security practice',
                'status': 'secure',
                'score': 100
            })
        elif admin_count <= 3:
            security_checks.append({
                'name': 'permissions',
                'description': f'{admin_count} admin permissions - consider reducing',
                'status': 'warning',
                'score': 60
            })
        else:
            security_checks.append({
                'name': 'permissions',
                'description': f'{admin_count} admin permissions - too many',
                'status': 'danger',
                'score': 20
            })
        
        # Check 3: Access history
        # In a real implementation, you would check access logs
        # For this example, we'll use a placeholder
        security_checks.append({
            'name': 'access_history',
            'description': 'Access history monitoring not implemented',
            'status': 'warning',
            'score': 50
        })
        
        # Check 4: Transaction signing security
        if wallet.metadata and wallet.metadata.get('hardware_wallet'):
            security_checks.append({
                'name': 'transaction_signing',
                'description': 'Transactions signed with hardware wallet - maximum security',
                'status': 'secure',
                'score': 100
            })
        elif wallet.private_key_encrypted:
            security_checks.append({
                'name': 'transaction_signing',
                'description': 'Transactions signed with software wallet - good security',
                'status': 'good',
                'score': 70
            })
        else:
            security_checks.append({
                'name': 'transaction_signing',
                'description': 'Transaction signing mechanism unknown',
                'status': 'warning',
                'score': 30
            })
        
        # Calculate overall score
        total_score = sum(check['score'] for check in security_checks)
        average_score = total_score / len(security_checks) if security_checks else 0
        audit['overall_score'] = int(average_score)
        
        # Determine risk level
        if average_score >= 80:
            audit['risk_level'] = 'low'
        elif average_score >= 60:
            audit['risk_level'] = 'medium'
        elif average_score >= 40:
            audit['risk_level'] = 'high'
        else:
            audit['risk_level'] = 'critical'
        
        # Add security checks to audit
        audit['security_checks'] = security_checks
        
        return audit