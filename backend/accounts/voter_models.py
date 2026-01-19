"""
Voter registration and verification models
Handles voter profiles, document uploads, and eligibility validation
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid

User = get_user_model()


class VoterProfile(models.Model):
    """
    Extended voter profile with additional biographical data
    and eligibility information
    """
    
    GENDER_CHOICES = (
        ('M', _('Male')),
        ('F', _('Female')),
        ('O', _('Other')),
        ('P', _('Prefer not to say')),
    )
    
    MARITAL_STATUS_CHOICES = (
        ('S', _('Single')),
        ('M', _('Married')),
        ('D', _('Divorced')),
        ('W', _('Widowed')),
    )
    
    DISABILITY_STATUS_CHOICES = (
        ('N', _('None')),
        ('P', _('Physical')),
        ('V', _('Visual')),
        ('H', _('Hearing')),
        ('C', _('Cognitive')),
        ('M', _('Multiple')),
        ('O', _('Other')),
    )
    
    VERIFICATION_STATUS_CHOICES = (
        ('pending', _('Pending Verification')),
        ('under_review', _('Under Review')),
        ('verified', _('Verified')),
        ('rejected', _('Rejected')),
        ('suspended', _('Suspended')),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='voter_profile'
    )
    
    # Biographical Information
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        blank=True,
        help_text='Biological sex'
    )
    marital_status = models.CharField(
        max_length=1,
        choices=MARITAL_STATUS_CHOICES,
        blank=True
    )
    
    # Address Information
    street_address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state_province = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True, default='Kenya')
    
    # Professional Information
    occupation = models.CharField(max_length=255, blank=True)
    employer = models.CharField(max_length=255, blank=True)
    
    # Additional Information
    disability_status = models.CharField(
        max_length=1,
        choices=DISABILITY_STATUS_CHOICES,
        default='N',
        help_text='Accessibility needs for voting'
    )
    disability_description = models.TextField(
        blank=True,
        help_text='Description of disability if "Other" selected'
    )
    
    # Eligibility & Verification
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default='pending',
        help_text='Current verification status'
    )
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_voters',
        help_text='Admin who verified this voter'
    )
    
    # Eligibility Information
    is_eligible = models.BooleanField(
        default=False,
        help_text='Whether voter meets all eligibility criteria'
    )
    ineligibility_reason = models.TextField(
        blank=True,
        help_text='Reason for ineligibility if applicable'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'voter_profile'
        verbose_name = _('Voter Profile')
        verbose_name_plural = _('Voter Profiles')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Voter Profile: {self.user.email}"
    
    def calculate_age(self):
        """Calculate voter age from date of birth"""
        if self.date_of_birth:
            from dateutil.relativedelta import relativedelta
            return relativedelta(timezone.now().date(), self.date_of_birth).years
        return None
    
    def meets_age_requirement(self, min_age=18):
        """Check if voter meets minimum age requirement"""
        age = self.calculate_age()
        return age is not None and age >= min_age
    
    def validate_eligibility(self):
        """
        Validate all eligibility criteria
        Returns tuple: (is_eligible: bool, reasons: list)
        """
        reasons = []
        
        # Age requirement
        if not self.meets_age_requirement():
            reasons.append("Must be at least 18 years old")
        
        # ID verification
        if not self.user.id_verified:
            reasons.append("National ID not verified")
        
        # Account status
        if self.user.status not in ['approved', 'pending']:
            reasons.append(f"Account status is {self.user.get_status_display()}")
        
        # Verification status
        if self.verification_status == 'rejected':
            reasons.append("Voter profile has been rejected")
        
        # Check for active blocks
        if self.user.is_locked_out():
            reasons.append("Account is locked")
        
        is_eligible = len(reasons) == 0
        return is_eligible, reasons


class VoterDocument(models.Model):
    """
    Document upload for voter verification
    Supports national ID, passport, student ID, etc.
    """
    
    DOCUMENT_TYPE_CHOICES = (
        ('national_id', _('National ID')),
        ('passport', _('Passport')),
        ('student_id', _('Student ID')),
        ('driver_license', _('Driver\'s License')),
        ('residence_permit', _('Residence Permit')),
        ('other', _('Other')),
    )
    
    VERIFICATION_STATUS_CHOICES = (
        ('pending', _('Pending Review')),
        ('verified', _('Verified')),
        ('rejected', _('Rejected')),
        ('expired', _('Expired')),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    voter = models.ForeignKey(
        VoterProfile,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    
    document_type = models.CharField(
        max_length=20,
        choices=DOCUMENT_TYPE_CHOICES,
        help_text='Type of identification document'
    )
    
    # Document Details
    document_number = models.CharField(
        max_length=100,
        blank=True,
        help_text='ID number or document reference'
    )
    issuing_country = models.CharField(
        max_length=100,
        default='Kenya',
        help_text='Country that issued the document'
    )
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    
    # Document File
    document_file = models.FileField(
        upload_to='voter_documents/%Y/%m/%d/',
        validators=[FileExtensionValidator(
            allowed_extensions=['pdf', 'jpg', 'jpeg', 'png']
        )],
        help_text='Document file (PDF, JPG, PNG, max 5MB)'
    )
    
    file_size = models.IntegerField(
        default=0,
        help_text='File size in bytes'
    )
    
    # Verification
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default='pending',
        help_text='Verification status of document'
    )
    
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_documents',
        help_text='Admin who verified this document'
    )
    
    verification_notes = models.TextField(
        blank=True,
        help_text='Comments from verifier (rejection reason, etc.)'
    )
    
    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'voter_document'
        verbose_name = _('Voter Document')
        verbose_name_plural = _('Voter Documents')
        indexes = [
            models.Index(fields=['voter', '-uploaded_at']),
            models.Index(fields=['verification_status']),
        ]
        ordering = ['-uploaded_at']
        unique_together = ['voter', 'document_type']  # One of each type per voter
    
    def __str__(self):
        return f"{self.get_document_type_display()} - {self.voter.user.email}"
    
    def is_expired(self):
        """Check if document is expired"""
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False
    
    def save(self, *args, **kwargs):
        """Save document and update file size"""
        if self.document_file:
            self.file_size = self.document_file.size
        super().save(*args, **kwargs)


class EligibilityRule(models.Model):
    """
    System-wide eligibility rules for voting
    Allows for flexible, configurable eligibility criteria
    """
    
    RULE_TYPE_CHOICES = (
        ('age', _('Age Requirement')),
        ('citizenship', _('Citizenship')),
        ('residency', _('Residency')),
        ('id_type', _('ID Type')),
        ('custom', _('Custom Rule')),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    rule_name = models.CharField(
        max_length=255,
        unique=True,
        help_text='Unique identifier for this rule'
    )
    
    rule_type = models.CharField(
        max_length=20,
        choices=RULE_TYPE_CHOICES,
        help_text='Type of eligibility rule'
    )
    
    description = models.TextField(
        help_text='Description of the eligibility requirement'
    )
    
    # Rule Configuration
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this rule is currently enforced'
    )
    
    # Age-specific fields
    minimum_age = models.IntegerField(
        default=18,
        null=True,
        blank=True,
        help_text='Minimum age requirement (if applicable)'
    )
    maximum_age = models.IntegerField(
        null=True,
        blank=True,
        help_text='Maximum age requirement (if applicable)'
    )
    
    # Custom rule
    rule_code = models.TextField(
        blank=True,
        help_text='Python code for custom eligibility logic'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_eligibility_rules'
    )
    
    class Meta:
        db_table = 'eligibility_rule'
        verbose_name = _('Eligibility Rule')
        verbose_name_plural = _('Eligibility Rules')
        ordering = ['rule_type', 'rule_name']
    
    def __str__(self):
        return f"{self.get_rule_type_display()} - {self.rule_name}"


class VerificationLog(models.Model):
    """
    Audit log for voter verification activities
    Tracks who verified what and when
    """
    
    ACTION_CHOICES = (
        ('document_verified', _('Document Verified')),
        ('document_rejected', _('Document Rejected')),
        ('voter_approved', _('Voter Approved')),
        ('voter_rejected', _('Voter Rejected')),
        ('eligibility_checked', _('Eligibility Checked')),
        ('profile_updated', _('Profile Updated')),
        ('verification_suspended', _('Verification Suspended')),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    voter = models.ForeignKey(
        VoterProfile,
        on_delete=models.CASCADE,
        related_name='verification_logs'
    )
    
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        help_text='Type of verification action'
    )
    
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verification_actions',
        help_text='Admin who performed this action'
    )
    
    description = models.TextField(
        blank=True,
        help_text='Detailed description of the action'
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='IP address of the verifier'
    )
    
    user_agent = models.TextField(
        blank=True,
        help_text='User agent of the verifier'
    )
    
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional metadata about the action'
    )
    
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )
    
    class Meta:
        db_table = 'verification_log'
        verbose_name = _('Verification Log')
        verbose_name_plural = _('Verification Logs')
        indexes = [
            models.Index(fields=['voter', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.voter.user.email} - {self.get_action_display()}"
