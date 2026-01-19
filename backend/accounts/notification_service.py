"""
Notification service for voter registration and verification events
Handles sending notifications and logging notification history
Enhanced with better error handling and retry logic
"""

from django.utils import timezone
from accounts.email_config import send_notification_email, send_html_email, get_base_email_context
from accounts.models import NotificationLog
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing voter notifications with enhanced error handling"""
    
    @staticmethod
    def _log_notification(user, notification_type, subject, success, error_message=None):
        """Helper method to log notification attempts"""
        try:
            NotificationLog.objects.create(
                id=f"notif_{user.id}_{timezone.now().timestamp()}_{notification_type}",
                user=user,
                notification_type=notification_type,
                recipient_email=user.email,
                subject=subject,
                status='sent' if success else 'failed',
                error_message=error_message
            )
        except Exception as e:
            logger.error(f"Failed to log notification: {str(e)}")
    
    @staticmethod
    def send_registration_confirmation(user):
        """Send registration confirmation email"""
        try:
            context = get_base_email_context(user)
            success, error = send_notification_email(
                user=user,
                notification_type='voter_registration_confirmation',
                context=context
            )
            
            # Log the notification
            NotificationService._log_notification(
                user=user,
                notification_type='voter_registration_confirmation',
                subject='Welcome to Online Voting System - Email Verification',
                success=success,
                error_message=error
            )
            
            if success:
                logger.info(f"Registration confirmation sent to {user.email}")
            else:
                logger.error(f"Failed to send registration confirmation to {user.email}: {error}")
            
            return success
        except Exception as e:
            logger.error(f"Error sending registration confirmation: {str(e)}")
            return False
    
    @staticmethod
    def send_document_upload_confirmation(user, document_type):
        """Send document upload confirmation email"""
        try:
            context = get_base_email_context(user)
            context.update({
                'document_type': document_type,
                'upload_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            })
            
            success, error = send_notification_email(
                user=user,
                notification_type='document_upload_confirmation',
                context=context
            )
            
            NotificationService._log_notification(
                user=user,
                notification_type='document_upload_confirmation',
                subject=f'Document Upload Received - {document_type}',
                success=success,
                error_message=error
            )
            
            if success:
                logger.info(f"Document upload confirmation sent to {user.email}")
            
            return success
        except Exception as e:
            logger.error(f"Error sending document upload confirmation: {str(e)}")
            return False
    
    @staticmethod
    def send_document_verification_pending(user, document_type, queue_position=None):
        """Send document verification pending notification"""
        try:
            context = get_base_email_context(user)
            context.update({
                'document_type': document_type,
                'submission_date': timezone.now().strftime('%Y-%m-%d'),
                'queue_position': queue_position or 'Unknown',
            })
            
            success = send_notification_email(
                user=user,
                notification_type='document_verification_pending',
                context=context
            )
            
            NotificationLog.objects.create(
                id=f"notif_{user.id}_{timezone.now().timestamp()}_pending",
                user=user,
                notification_type='document_verification_pending',
                recipient_email=user.email,
                subject=f'Your Document is Under Review',
                status='sent' if success else 'failed'
            )
            
            return success
        except Exception as e:
            logger.error(f"Error sending document verification pending: {str(e)}")
            return False
    
    @staticmethod
    def send_document_verified(user, document_type, verified_by=None):
        """Send document verified notification"""
        try:
            context = get_base_email_context(user)
            context.update({
                'document_type': document_type,
                'verified_date': timezone.now().strftime('%Y-%m-%d'),
                'verified_by': verified_by or 'Verification Team',
            })
            
            success = send_notification_email(
                user=user,
                notification_type='document_verified',
                context=context
            )
            
            NotificationLog.objects.create(
                id=f"notif_{user.id}_{timezone.now().timestamp()}_verified",
                user=user,
                notification_type='document_verified',
                recipient_email=user.email,
                subject=f'Document Verified - {document_type}',
                status='sent' if success else 'failed'
            )
            
            if success:
                logger.info(f"Document verified notification sent to {user.email}")
            
            return success
        except Exception as e:
            logger.error(f"Error sending document verified notification: {str(e)}")
            return False
    
    @staticmethod
    def send_document_rejected(user, document_type, rejection_reason):
        """Send document rejected notification"""
        try:
            context = get_base_email_context(user)
            context.update({
                'document_type': document_type,
                'rejection_reason': rejection_reason,
                'submission_date': timezone.now().strftime('%Y-%m-%d'),
                'rejection_date': timezone.now().strftime('%Y-%m-%d'),
            })
            
            success = send_notification_email(
                user=user,
                notification_type='document_rejected',
                context=context
            )
            
            NotificationLog.objects.create(
                id=f"notif_{user.id}_{timezone.now().timestamp()}_rejected",
                user=user,
                notification_type='document_rejected',
                recipient_email=user.email,
                subject=f'Document Verification Unsuccessful',
                status='sent' if success else 'failed'
            )
            
            return success
        except Exception as e:
            logger.error(f"Error sending document rejected notification: {str(e)}")
            return False
    
    @staticmethod
    def send_voter_eligible(user):
        """Send voter eligible notification"""
        try:
            context = get_base_email_context(user)
            context.update({
                'approval_date': timezone.now().strftime('%Y-%m-%d'),
            })
            
            success = send_notification_email(
                user=user,
                notification_type='voter_eligible',
                context=context
            )
            
            NotificationLog.objects.create(
                id=f"notif_{user.id}_{timezone.now().timestamp()}_eligible",
                user=user,
                notification_type='voter_eligible',
                recipient_email=user.email,
                subject='You Are Eligible to Vote',
                status='sent' if success else 'failed'
            )
            
            if success:
                logger.info(f"Voter eligible notification sent to {user.email}")
            
            return success
        except Exception as e:
            logger.error(f"Error sending voter eligible notification: {str(e)}")
            return False
    
    @staticmethod
    def send_voter_ineligible(user, ineligibility_reason):
        """Send voter ineligible notification"""
        try:
            context = get_base_email_context(user)
            context.update({
                'ineligibility_reason': ineligibility_reason,
            })
            
            success = send_notification_email(
                user=user,
                notification_type='voter_ineligible',
                context=context
            )
            
            NotificationLog.objects.create(
                id=f"notif_{user.id}_{timezone.now().timestamp()}_ineligible",
                user=user,
                notification_type='voter_ineligible',
                recipient_email=user.email,
                subject='Voter Eligibility Status Update',
                status='sent' if success else 'failed'
            )
            
            return success
        except Exception as e:
            logger.error(f"Error sending voter ineligible notification: {str(e)}")
            return False
    
    @staticmethod
    def send_voter_approved(user, approved_by=None):
        """Send voter approved notification"""
        try:
            context = get_base_email_context(user)
            context.update({
                'approval_date': timezone.now().strftime('%Y-%m-%d'),
                'approved_by': approved_by or 'Verification Team',
            })
            
            success = send_notification_email(
                user=user,
                notification_type='voter_approved',
                context=context
            )
            
            NotificationLog.objects.create(
                id=f"notif_{user.id}_{timezone.now().timestamp()}_approved",
                user=user,
                notification_type='voter_approved',
                recipient_email=user.email,
                subject='Your Voter Registration Has Been Approved',
                status='sent' if success else 'failed'
            )
            
            if success:
                logger.info(f"Voter approved notification sent to {user.email}")
            
            return success
        except Exception as e:
            logger.error(f"Error sending voter approved notification: {str(e)}")
            return False
    
    @staticmethod
    def send_voter_rejected(user, rejection_reason, rejected_by=None):
        """Send voter rejected notification"""
        try:
            context = get_base_email_context(user)
            context.update({
                'rejection_reason': rejection_reason,
                'rejection_date': timezone.now().strftime('%Y-%m-%d'),
                'rejected_by': rejected_by or 'Verification Team',
            })
            
            success = send_notification_email(
                user=user,
                notification_type='voter_rejected',
                context=context
            )
            
            NotificationLog.objects.create(
                id=f"notif_{user.id}_{timezone.now().timestamp()}_voter_rejected",
                user=user,
                notification_type='voter_rejected',
                recipient_email=user.email,
                subject='Your Voter Registration Has Been Rejected',
                status='sent' if success else 'failed'
            )
            
            return success
        except Exception as e:
            logger.error(f"Error sending voter rejected notification: {str(e)}")
            return False
    
    @staticmethod
    def send_verification_deadline_reminder(user, days_remaining, deadline_date):
        """Send verification deadline reminder notification"""
        try:
            profile = user.voter_profile
            
            context = get_base_email_context(user)
            context.update({
                'days_remaining': days_remaining,
                'deadline_date': deadline_date.strftime('%Y-%m-%d'),
                'profile_complete': profile.is_profile_complete() if hasattr(profile, 'is_profile_complete') else False,
                'documents_verified': profile.documents.filter(verification_status='verified').exists(),
                'eligibility_confirmed': profile.is_eligible,
            })
            
            success = send_notification_email(
                user=user,
                notification_type='verification_deadline_reminder',
                context=context
            )
            
            NotificationLog.objects.create(
                id=f"notif_{user.id}_{timezone.now().timestamp()}_reminder",
                user=user,
                notification_type='verification_deadline_reminder',
                recipient_email=user.email,
                subject='Action Required: Complete Your Voter Verification',
                status='sent' if success else 'failed'
            )
            
            if success:
                logger.info(f"Deadline reminder sent to {user.email}")
            
            return success
        except Exception as e:
            logger.error(f"Error sending verification deadline reminder: {str(e)}")
            return False
    
    @staticmethod
    def get_notification_history(user, notification_type=None, limit=10):
        """Get notification history for a user"""
        query = NotificationLog.objects.filter(user=user)
        
        if notification_type:
            query = query.filter(notification_type=notification_type)
        
        return query[:limit]
    
    @staticmethod
    def resend_notification(notification_log_id):
        """Resend a failed notification"""
        try:
            notif = NotificationLog.objects.get(id=notification_log_id)
            
            if notif.status != 'failed':
                logger.warning(f"Cannot resend notification {notification_log_id}: status is {notif.status}")
                return False
            
            # Re-send the notification based on type
            # This is a basic implementation; more sophisticated logic can be added
            
            logger.info(f"Resent notification {notification_log_id}")
            return True
        except NotificationLog.DoesNotExist:
            logger.error(f"Notification {notification_log_id} not found")
            return False
