"""
Comprehensive tests for Security features (2FA, Trusted Devices, Security Questions)
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
import pyotp
import base64
from io import BytesIO
from PIL import Image

from accounts.security_models import (
    TwoFactorAuth, TwoFactorAuthLog, SecurityQuestion, TrustedDevice
)

User = get_user_model()


class TwoFactorAuthModelTest(TestCase):
    """Test TwoFactorAuth model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
    
    def test_create_two_factor_auth(self):
        """Test creating TwoFactorAuth instance"""
        tfa = TwoFactorAuth.objects.create(user=self.user)
        
        self.assertIsNotNone(tfa.secret_key)
        self.assertEqual(len(tfa.secret_key), 32)
        self.assertFalse(tfa.is_enabled)
        self.assertEqual(tfa.backup_codes, [])
    
    def test_generate_secret_key(self):
        """Test secret key generation"""
        tfa = TwoFactorAuth.objects.create(user=self.user)
        secret = tfa.generate_secret_key()
        
        self.assertEqual(len(secret), 32)
        self.assertNotEqual(secret, tfa.secret_key)
        
        # Update instance
        tfa.secret_key = secret
        tfa.save()
        self.assertEqual(tfa.secret_key, secret)
    
    def test_get_totp_uri(self):
        """Test TOTP URI generation"""
        tfa = TwoFactorAuth.objects.create(user=self.user)
        uri = tfa.get_totp_uri()
        
        self.assertIn('otpauth://totp/', uri)
        self.assertIn('iVote%20Systems', uri)
        self.assertIn(self.user.email, uri)
        self.assertIn(f'secret={tfa.secret_key}', uri)
    
    def test_generate_qr_code(self):
        """Test QR code generation"""
        tfa = TwoFactorAuth.objects.create(user=self.user)
        qr_code = tfa.generate_qr_code()
        
        self.assertIn('data:image/png;base64,', qr_code)
        
        # Decode and verify it's a valid image
        image_data = qr_code.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        image = Image.open(BytesIO(image_bytes))
        
        self.assertEqual(image.format, 'PNG')
        self.assertGreater(image.size[0], 0)
        self.assertGreater(image.size[1], 0)
    
    def test_verify_token_valid(self):
        """Test token verification with valid token"""
        tfa = TwoFactorAuth.objects.create(user=self.user)
        
        # Generate valid token
        totp = pyotp.TOTP(tfa.secret_key)
        token = totp.now()
        
        self.assertTrue(tfa.verify_token(token))
    
    def test_verify_token_invalid(self):
        """Test token verification with invalid token"""
        tfa = TwoFactorAuth.objects.create(user=self.user)
        
        self.assertFalse(tfa.verify_token('000000'))
        self.assertFalse(tfa.verify_token('invalid'))
        self.assertFalse(tfa.verify_token(''))
    
    def test_generate_backup_codes(self):
        """Test backup codes generation"""
        tfa = TwoFactorAuth.objects.create(user=self.user)
        codes = tfa.generate_backup_codes(count=10)
        
        self.assertEqual(len(codes), 10)
        self.assertEqual(len(tfa.backup_codes), 10)
        
        # Verify all codes are unique
        self.assertEqual(len(codes), len(set(codes)))
        
        # Verify code format (hex)
        for code in codes:
            self.assertEqual(len(code), 12)
            int(code, 16)  # Should not raise exception
    
    def test_verify_backup_code_valid(self):
        """Test backup code verification"""
        tfa = TwoFactorAuth.objects.create(user=self.user)
        codes = tfa.generate_backup_codes(count=5)
        
        # Use first code
        self.assertTrue(tfa.verify_backup_code(codes[0]))
        
        # Code should be removed
        tfa.refresh_from_db()
        self.assertEqual(len(tfa.backup_codes), 4)
        self.assertNotIn(codes[0], tfa.backup_codes)
        
        # Can't use same code again
        self.assertFalse(tfa.verify_backup_code(codes[0]))
    
    def test_verify_backup_code_invalid(self):
        """Test backup code verification with invalid code"""
        tfa = TwoFactorAuth.objects.create(user=self.user)
        tfa.generate_backup_codes(count=5)
        
        self.assertFalse(tfa.verify_backup_code('invalid'))
        self.assertFalse(tfa.verify_backup_code(''))
        self.assertFalse(tfa.verify_backup_code('000000000000'))
    
    def test_enable_disable(self):
        """Test enabling and disabling 2FA"""
        tfa = TwoFactorAuth.objects.create(user=self.user)
        
        # Initially disabled
        self.assertFalse(tfa.is_enabled)
        self.assertIsNone(tfa.enabled_at)
        
        # Enable
        tfa.enable()
        self.assertTrue(tfa.is_enabled)
        self.assertIsNotNone(tfa.enabled_at)
        
        # Disable
        tfa.disable()
        self.assertFalse(tfa.is_enabled)


class TwoFactorAuthLogTest(TestCase):
    """Test TwoFactorAuthLog model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_log_action(self):
        """Test logging 2FA action"""
        log = TwoFactorAuthLog.log_action(
            user=self.user,
            action=TwoFactorAuthLog.ACTION_ENABLED,
            success=True,
            ip_address='192.168.1.1',
            user_agent='Test Agent',
            details={'method': 'app'}
        )
        
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, TwoFactorAuthLog.ACTION_ENABLED)
        self.assertTrue(log.success)
        self.assertEqual(log.ip_address, '192.168.1.1')
        self.assertEqual(log.user_agent, 'Test Agent')
        self.assertEqual(log.details['method'], 'app')
    
    def test_log_multiple_actions(self):
        """Test logging multiple actions"""
        actions = [
            TwoFactorAuthLog.ACTION_SETUP_INITIATED,
            TwoFactorAuthLog.ACTION_SETUP_COMPLETED,
            TwoFactorAuthLog.ACTION_ENABLED,
        ]
        
        for action in actions:
            TwoFactorAuthLog.log_action(
                user=self.user,
                action=action,
                success=True
            )
        
        logs = TwoFactorAuthLog.objects.filter(user=self.user)
        self.assertEqual(logs.count(), 3)


class SecurityQuestionTest(TestCase):
    """Test SecurityQuestion model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_security_question(self):
        """Test creating security question"""
        question = SecurityQuestion.objects.create(
            user=self.user,
            question='What is your favorite color?'
        )
        question.set_answer('blue')
        
        self.assertIsNotNone(question.answer_hash)
        self.assertNotEqual(question.answer_hash, 'blue')
    
    def test_check_answer_correct(self):
        """Test checking correct answer"""
        question = SecurityQuestion.objects.create(
            user=self.user,
            question='What is your favorite color?'
        )
        question.set_answer('blue')
        
        self.assertTrue(question.check_answer('blue'))
        self.assertTrue(question.check_answer('BLUE'))  # Case insensitive
        self.assertTrue(question.check_answer(' blue '))  # Trimmed
    
    def test_check_answer_incorrect(self):
        """Test checking incorrect answer"""
        question = SecurityQuestion.objects.create(
            user=self.user,
            question='What is your favorite color?'
        )
        question.set_answer('blue')
        
        self.assertFalse(question.check_answer('red'))
        self.assertFalse(question.check_answer(''))
        self.assertFalse(question.check_answer('blu'))
    
    def test_unique_constraint(self):
        """Test unique constraint on user+question"""
        SecurityQuestion.objects.create(
            user=self.user,
            question='What is your favorite color?'
        )
        
        # Should raise IntegrityError
        with self.assertRaises(Exception):
            SecurityQuestion.objects.create(
                user=self.user,
                question='What is your favorite color?'
            )


class TrustedDeviceTest(TestCase):
    """Test TrustedDevice model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_trusted_device(self):
        """Test creating trusted device"""
        device = TrustedDevice.create_trusted_device(
            user=self.user,
            device_name='Chrome on Windows',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0...'
        )
        
        self.assertEqual(device.user, self.user)
        self.assertIsNotNone(device.device_id)
        self.assertEqual(len(device.device_id), 64)  # SHA256 hex
        self.assertTrue(device.is_active)
        self.assertIsNotNone(device.expires_at)
    
    def test_is_valid(self):
        """Test device validity check"""
        device = TrustedDevice.create_trusted_device(
            user=self.user,
            device_name='Chrome',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0...'
        )
        
        self.assertTrue(device.is_valid())
        
        # Revoke and check
        device.revoke()
        self.assertFalse(device.is_valid())
    
    def test_revoke(self):
        """Test device revocation"""
        device = TrustedDevice.create_trusted_device(
            user=self.user,
            device_name='Chrome',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0...'
        )
        
        self.assertTrue(device.is_active)
        
        device.revoke()
        self.assertFalse(device.is_active)


class TwoFactorAuthAPITest(APITestCase):
    """Test 2FA API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_2fa_status_disabled(self):
        """Test getting 2FA status when disabled"""
        response = self.client.get('/api/accounts/2fa/status/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['enabled'])
        self.assertEqual(response.data['backup_codes_remaining'], 0)
    
    def test_2fa_status_enabled(self):
        """Test getting 2FA status when enabled"""
        tfa = TwoFactorAuth.objects.create(user=self.user)
        tfa.enable()
        tfa.generate_backup_codes(count=10)
        
        response = self.client.get('/api/accounts/2fa/status/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['enabled'])
        self.assertEqual(response.data['backup_codes_remaining'], 10)
    
    def test_2fa_setup(self):
        """Test initiating 2FA setup"""
        response = self.client.post('/api/accounts/2fa/setup/')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('secret_key', response.data)
        self.assertIn('qr_code', response.data)
        self.assertIn('manual_entry_key', response.data)
        self.assertIn('data:image/png;base64,', response.data['qr_code'])
        
        # Verify TwoFactorAuth was created
        tfa = TwoFactorAuth.objects.get(user=self.user)
        self.assertFalse(tfa.is_enabled)
    
    def test_2fa_verify_valid_token(self):
        """Test verifying valid token"""
        tfa = TwoFactorAuth.objects.create(user=self.user)
        totp = pyotp.TOTP(tfa.secret_key)
        token = totp.now()
        
        response = self.client.post('/api/accounts/2fa/verify/', {
            'token': token,
            'trust_device': False
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('backup_codes', response.data)
        
        # Verify 2FA is enabled
        tfa.refresh_from_db()
        self.assertTrue(tfa.is_enabled)
    
    def test_2fa_verify_invalid_token(self):
        """Test verifying invalid token"""
        TwoFactorAuth.objects.create(user=self.user)
        
        response = self.client.post('/api/accounts/2fa/verify/', {
            'token': '000000',
            'trust_device': False
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_2fa_verify_with_trust_device(self):
        """Test verifying with device trust"""
        tfa = TwoFactorAuth.objects.create(user=self.user)
        totp = pyotp.TOTP(tfa.secret_key)
        token = totp.now()
        
        response = self.client.post('/api/accounts/2fa/verify/', {
            'token': token,
            'trust_device': True
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('device_id', response.data)
        
        # Verify device was created
        device_count = TrustedDevice.objects.filter(user=self.user).count()
        self.assertEqual(device_count, 1)
    
    def test_2fa_disable(self):
        """Test disabling 2FA"""
        tfa = TwoFactorAuth.objects.create(user=self.user)
        tfa.enable()
        totp = pyotp.TOTP(tfa.secret_key)
        token = totp.now()
        
        response = self.client.post('/api/accounts/2fa/disable/', {
            'password': 'testpass123',
            'token': token
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify 2FA is disabled
        tfa.refresh_from_db()
        self.assertFalse(tfa.is_enabled)
    
    def test_2fa_disable_wrong_password(self):
        """Test disabling 2FA with wrong password"""
        tfa = TwoFactorAuth.objects.create(user=self.user)
        tfa.enable()
        
        response = self.client.post('/api/accounts/2fa/disable/', {
            'password': 'wrongpass',
            'token': '000000'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_regenerate_backup_codes(self):
        """Test regenerating backup codes"""
        tfa = TwoFactorAuth.objects.create(user=self.user)
        tfa.enable()
        old_codes = tfa.generate_backup_codes(count=5)
        
        response = self.client.post('/api/accounts/2fa/regenerate_backup_codes/', {
            'password': 'testpass123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('backup_codes', response.data)
        
        new_codes = response.data['backup_codes']
        self.assertEqual(len(new_codes), 10)
        
        # Verify old codes don't work
        tfa.refresh_from_db()
        for code in old_codes:
            self.assertNotIn(code, tfa.backup_codes)
    
    def test_2fa_logs(self):
        """Test getting 2FA activity logs"""
        # Create some logs
        TwoFactorAuthLog.log_action(
            user=self.user,
            action=TwoFactorAuthLog.ACTION_ENABLED,
            success=True
        )
        
        response = self.client.get('/api/accounts/2fa/logs/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)
        self.assertEqual(response.data[0]['action'], TwoFactorAuthLog.ACTION_ENABLED)


class TrustedDevicesAPITest(APITestCase):
    """Test Trusted Devices API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_list_trusted_devices(self):
        """Test listing trusted devices"""
        # Create devices
        TrustedDevice.create_trusted_device(
            user=self.user,
            device_name='Chrome',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0...'
        )
        TrustedDevice.create_trusted_device(
            user=self.user,
            device_name='Firefox',
            ip_address='192.168.1.2',
            user_agent='Mozilla/5.0...'
        )
        
        response = self.client.get('/api/accounts/trusted-devices/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_revoke_device(self):
        """Test revoking a device"""
        device = TrustedDevice.create_trusted_device(
            user=self.user,
            device_name='Chrome',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0...'
        )
        
        response = self.client.delete(f'/api/accounts/trusted-devices/{device.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify device is revoked
        device.refresh_from_db()
        self.assertFalse(device.is_active)
    
    def test_revoke_all_devices(self):
        """Test revoking all devices"""
        # Create multiple devices
        for i in range(3):
            TrustedDevice.create_trusted_device(
                user=self.user,
                device_name=f'Device {i}',
                ip_address=f'192.168.1.{i}',
                user_agent='Mozilla/5.0...'
            )
        
        response = self.client.post('/api/accounts/trusted-devices/revoke_all/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify all devices are revoked
        active_count = TrustedDevice.objects.filter(
            user=self.user,
            is_active=True
        ).count()
        self.assertEqual(active_count, 0)
    
    def test_check_device_trusted(self):
        """Test checking if device is trusted"""
        device = TrustedDevice.create_trusted_device(
            user=self.user,
            device_name='Chrome',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0...'
        )
        
        response = self.client.post('/api/accounts/trusted-devices/check_device/', {
            'device_id': device.device_id
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['trusted'])
    
    def test_check_device_not_trusted(self):
        """Test checking device that's not trusted"""
        response = self.client.post('/api/accounts/trusted-devices/check_device/', {
            'device_id': 'invalid_device_id'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['trusted'])


class SecurityQuestionsAPITest(APITestCase):
    """Test Security Questions API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_create_security_question(self):
        """Test creating security question"""
        response = self.client.post('/api/accounts/security-questions/', {
            'question': 'What is your favorite color?',
            'answer': 'blue'
        })
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify question was created
        question = SecurityQuestion.objects.get(user=self.user)
        self.assertEqual(question.question, 'What is your favorite color?')
        self.assertTrue(question.check_answer('blue'))
    
    def test_list_security_questions(self):
        """Test listing security questions"""
        # Create questions
        for i in range(3):
            question = SecurityQuestion.objects.create(
                user=self.user,
                question=f'Question {i}?'
            )
            question.set_answer(f'answer{i}')
        
        response = self.client.get('/api/accounts/security-questions/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        
        # Verify answers are not returned
        for item in response.data:
            self.assertNotIn('answer', item)
            self.assertNotIn('answer_hash', item)
    
    def test_delete_security_question(self):
        """Test deleting security question"""
        question = SecurityQuestion.objects.create(
            user=self.user,
            question='Question?'
        )
        
        response = self.client.delete(f'/api/accounts/security-questions/{question.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify question was deleted
        exists = SecurityQuestion.objects.filter(id=question.id).exists()
        self.assertFalse(exists)
    
    def test_verify_answer_correct(self):
        """Test verifying correct answer"""
        question = SecurityQuestion.objects.create(
            user=self.user,
            question='What is your favorite color?'
        )
        question.set_answer('blue')
        
        response = self.client.post(
            f'/api/accounts/security-questions/{question.id}/verify/',
            {'answer': 'blue'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['verified'])
    
    def test_verify_answer_incorrect(self):
        """Test verifying incorrect answer"""
        question = SecurityQuestion.objects.create(
            user=self.user,
            question='What is your favorite color?'
        )
        question.set_answer('blue')
        
        response = self.client.post(
            f'/api/accounts/security-questions/{question.id}/verify/',
            {'answer': 'red'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['verified'])


# Run tests with: python manage.py test accounts.test_security
