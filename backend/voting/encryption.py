"""
Vote Encryption Utilities
Provides AES-256 encryption for secure vote storage
"""

import os
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from django.conf import settings
import hashlib


class VoteEncryption:
    """
    AES-256 encryption for votes
    Ensures vote anonymity and confidentiality
    """
    
    def __init__(self):
        # Get encryption key from settings or generate one
        self.key = self._get_or_create_key()
    
    def _get_or_create_key(self):
        """Get encryption key from settings"""
        import hashlib
        
        key = getattr(settings, 'VOTE_ENCRYPTION_KEY', None)
        if not key:
            # Generate a new key (32 bytes for AES-256)
            key = base64.b64encode(os.urandom(32)).decode('utf-8')
        
        # Convert string key to 32-byte key using SHA-256
        if isinstance(key, str):
            # Use SHA-256 to derive a proper 32-byte key
            return hashlib.sha256(key.encode('utf-8')).digest()
        
        return key
    
    def encrypt_vote(self, vote_data: str) -> tuple:
        """
        Encrypt vote data using AES-256
        
        Args:
            vote_data: String representation of vote (e.g., candidate IDs)
        
        Returns:
            Tuple of (encrypted_data, initialization_vector)
        """
        # Generate random IV (16 bytes for AES)
        iv = os.urandom(16)
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(self.key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Pad the data to AES block size (128 bits = 16 bytes)
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(vote_data.encode('utf-8')) + padder.finalize()
        
        # Encrypt
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        
        # Return base64 encoded values
        return (
            base64.b64encode(encrypted).decode('utf-8'),
            base64.b64encode(iv).decode('utf-8')
        )
    
    def decrypt_vote(self, encrypted_data: str, iv: str) -> str:
        """
        Decrypt vote data
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            iv: Base64 encoded initialization vector
        
        Returns:
            Decrypted vote data string
        """
        # Decode base64
        encrypted = base64.b64decode(encrypted_data)
        iv_bytes = base64.b64decode(iv)
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(self.key),
            modes.CBC(iv_bytes),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # Decrypt
        padded_data = decryptor.update(encrypted) + decryptor.finalize()
        
        # Unpad
        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()
        
        return data.decode('utf-8')
    
    def hash_voter_id(self, voter_id: str, election_id: str) -> str:
        """
        Create a one-way hash of voter + election ID
        Used to prevent double voting without storing voter identity
        
        Args:
            voter_id: Voter's unique identifier
            election_id: Election's unique identifier
        
        Returns:
            SHA-256 hash string
        """
        combined = f"{voter_id}:{election_id}:{self.key.hex()}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()


class VerificationCodeGenerator:
    """
    Generate and validate vote verification codes
    Allows voters to confirm their vote was recorded
    """
    
    @staticmethod
    def generate_code(vote_id: str, timestamp: str) -> str:
        """
        Generate a unique verification code
        
        Args:
            vote_id: Vote's unique identifier
            timestamp: Vote submission timestamp
        
        Returns:
            12-character verification code
        """
        # Combine vote ID and timestamp
        combined = f"{vote_id}:{timestamp}"
        hash_obj = hashlib.sha256(combined.encode('utf-8'))
        
        # Take first 12 characters of hex digest
        code = hash_obj.hexdigest()[:12].upper()
        
        # Format as XXX-XXX-XXX-XXX for readability
        return f"{code[0:3]}-{code[3:6]}-{code[6:9]}-{code[9:12]}"
    
    @staticmethod
    def validate_code_format(code: str) -> bool:
        """
        Validate verification code format
        
        Args:
            code: Verification code to validate
        
        Returns:
            True if format is valid
        """
        # Remove dashes
        clean_code = code.replace('-', '')
        
        # Must be 12 hexadecimal characters
        if len(clean_code) != 12:
            return False
        
        try:
            int(clean_code, 16)
            return True
        except ValueError:
            return False


# Singleton instances
vote_encryptor = VoteEncryption()
verification_generator = VerificationCodeGenerator()


__all__ = [
    'VoteEncryption',
    'VerificationCodeGenerator',
    'vote_encryptor',
    'verification_generator',
]
