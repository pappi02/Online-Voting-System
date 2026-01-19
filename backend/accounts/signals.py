"""
Django signals for automatically triggering notifications on model events
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from accounts.models import User
from accounts.voter_models import VoterProfile, VoterDocument
from accounts.notification_service import NotificationService
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def send_user_notification(sender, instance, created, **kwargs):
    """Send notifications when user is created"""
    if created and hasattr(instance, 'voter_profile'):
        try:
            # Send registration confirmation email
            NotificationService.send_registration_confirmation(instance)
            logger.info(f"Registration notification sent for user {instance.email}")
        except Exception as e:
            logger.error(f"Error sending registration notification: {str(e)}")


@receiver(post_save, sender=VoterDocument)
def send_document_notification(sender, instance, created, update_fields=None, **kwargs):
    """Send notifications when document status changes"""
    if created:
        # Send document upload confirmation
        try:
            NotificationService.send_document_upload_confirmation(
                user=instance.voter.user,
                document_type=instance.get_document_type_display()
            )
            logger.info(f"Document upload notification sent for {instance.voter.user.email}")
        except Exception as e:
            logger.error(f"Error sending document upload notification: {str(e)}")
    
    elif update_fields and 'verification_status' in update_fields:
        # Send verification status update
        try:
            user = instance.voter.user
            
            if instance.verification_status == 'pending':
                NotificationService.send_document_verification_pending(
                    user=user,
                    document_type=instance.get_document_type_display()
                )
            
            elif instance.verification_status == 'verified':
                NotificationService.send_document_verified(
                    user=user,
                    document_type=instance.get_document_type_display(),
                    verified_by=instance.verified_by.get_full_name() if instance.verified_by else None
                )
            
            elif instance.verification_status == 'rejected':
                NotificationService.send_document_rejected(
                    user=user,
                    document_type=instance.get_document_type_display(),
                    rejection_reason=instance.verification_notes or 'Document does not meet requirements'
                )
            
            logger.info(f"Document status notification sent for {user.email}")
        
        except Exception as e:
            logger.error(f"Error sending document status notification: {str(e)}")


@receiver(post_save, sender=VoterProfile)
def send_voter_profile_notification(sender, instance, update_fields=None, **kwargs):
    """Send notifications when voter profile status changes"""
    if update_fields and ('is_eligible' in update_fields or 'verification_status' in update_fields):
        try:
            user = instance.user
            
            # Check eligibility status
            if instance.is_eligible:
                NotificationService.send_voter_eligible(user=user)
                logger.info(f"Voter eligible notification sent for {user.email}")
            
            elif instance.ineligibility_reason:
                NotificationService.send_voter_ineligible(
                    user=user,
                    ineligibility_reason=instance.ineligibility_reason
                )
                logger.info(f"Voter ineligible notification sent for {user.email}")
        
        except Exception as e:
            logger.error(f"Error sending voter profile notification: {str(e)}")


def send_voter_approval_notification(voter_profile, approved=True, reason=None, approved_by=None):
    """
    Manually trigger voter approval/rejection notification
    Used by admin actions in views
    """
    try:
        user = voter_profile.user
        
        if approved:
            NotificationService.send_voter_approved(
                user=user,
                approved_by=approved_by.get_full_name() if approved_by else None
            )
            logger.info(f"Voter approved notification sent for {user.email}")
        else:
            NotificationService.send_voter_rejected(
                user=user,
                rejection_reason=reason or 'Your registration does not meet our requirements',
                rejected_by=approved_by.get_full_name() if approved_by else None
            )
            logger.info(f"Voter rejected notification sent for {user.email}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error sending voter approval notification: {str(e)}")
        return False


def send_deadline_reminder_notifications():
    """
    Send reminder notifications to users with incomplete verification
    Should be called by a scheduled task (Celery beat)
    """
    from datetime import timedelta
    
    try:
        # Find profiles with pending verification created more than 7 days ago
        seven_days_ago = timezone.now() - timedelta(days=7)
        pending_profiles = VoterProfile.objects.filter(
            verification_status='pending',
            created_at__lt=seven_days_ago
        )
        
        count = 0
        for profile in pending_profiles:
            # Calculate days until deadline (assuming 14-day verification window)
            deadline = profile.created_at + timedelta(days=14)
            days_remaining = (deadline - timezone.now()).days
            
            if 0 < days_remaining <= 7:  # Only send if within last week
                NotificationService.send_verification_deadline_reminder(
                    user=profile.user,
                    days_remaining=days_remaining,
                    deadline_date=deadline
                )
                count += 1
        
        logger.info(f"Sent {count} deadline reminder notifications")
        return count
    
    except Exception as e:
        logger.error(f"Error sending deadline reminders: {str(e)}")
        return 0
