"""
Serializers for voter registration and verification
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from accounts.voter_models import (
    VoterProfile, VoterDocument, EligibilityRule, VerificationLog
)
from datetime import date

User = get_user_model()


class VoterProfileSerializer(serializers.ModelSerializer):
    """
    Voter profile serializer with biographical data
    """
    user_email = serializers.CharField(source='user.email', read_only=True)
    age = serializers.SerializerMethodField()
    is_eligible = serializers.SerializerMethodField()
    eligibility_issues = serializers.SerializerMethodField()
    verification_status_display = serializers.CharField(
        source='get_verification_status_display',
        read_only=True
    )
    disability_status_display = serializers.CharField(
        source='get_disability_status_display',
        read_only=True
    )
    
    class Meta:
        model = VoterProfile
        fields = [
            'id', 'user_email', 'date_of_birth', 'gender', 'marital_status',
            'street_address', 'city', 'state_province', 'postal_code', 'country',
            'occupation', 'employer', 'disability_status', 'disability_status_display',
            'disability_description', 'age', 'verification_status', 
            'verification_status_display', 'is_eligible', 'eligibility_issues',
            'ineligibility_reason', 'created_at', 'updated_at', 'verified_at'
        ]
        read_only_fields = [
            'id', 'user_email', 'is_eligible', 'eligibility_issues',
            'verification_status', 'verified_by', 'ineligibility_reason',
            'created_at', 'updated_at', 'verified_at'
        ]
    
    def get_age(self, obj):
        """Calculate and return voter age"""
        return obj.calculate_age()
    
    def get_is_eligible(self, obj):
        """Check if voter is eligible"""
        is_eligible, _ = obj.validate_eligibility()
        return is_eligible
    
    def get_eligibility_issues(self, obj):
        """Get list of eligibility issues"""
        _, reasons = obj.validate_eligibility()
        return reasons
    
    def validate_date_of_birth(self, value):
        """Validate date of birth"""
        if value > date.today():
            raise serializers.ValidationError("Date of birth cannot be in the future")
        
        # Check minimum age (18)
        from dateutil.relativedelta import relativedelta
        min_age_date = date.today() - relativedelta(years=18)
        if value > min_age_date:
            raise serializers.ValidationError("Must be at least 18 years old")
        
        return value
    
    def validate_postal_code(self, value):
        """Validate postal code format"""
        if value and len(value) < 4:
            raise serializers.ValidationError("Postal code must be at least 4 characters")
        return value


class VoterDocumentSerializer(serializers.ModelSerializer):
    """
    Document upload serializer
    """
    document_type_display = serializers.CharField(
        source='get_document_type_display',
        read_only=True
    )
    verification_status_display = serializers.CharField(
        source='get_verification_status_display',
        read_only=True
    )
    is_expired = serializers.SerializerMethodField()
    verified_by_email = serializers.CharField(
        source='verified_by.email',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = VoterDocument
        fields = [
            'id', 'document_type', 'document_type_display', 'document_number',
            'issuing_country', 'issue_date', 'expiry_date', 'document_file',
            'file_size', 'verification_status', 'verification_status_display',
            'is_expired', 'verification_notes', 'verified_by_email',
            'uploaded_at', 'verified_at'
        ]
        read_only_fields = [
            'id', 'file_size', 'verification_status', 'verification_notes',
            'verified_by_email', 'uploaded_at', 'verified_at'
        ]
    
    def get_is_expired(self, obj):
        """Check if document is expired"""
        return obj.is_expired()
    
    def validate_document_file(self, value):
        """Validate document file"""
        if value.size > 5 * 1024 * 1024:  # 5MB max
            raise serializers.ValidationError("File size must not exceed 5MB")
        
        # Check file extension
        allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png']
        file_ext = value.name.split('.')[-1].lower()
        if file_ext not in allowed_extensions:
            raise serializers.ValidationError(
                f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
            )
        
        return value
    
    def validate_expiry_date(self, value):
        """Validate expiry date"""
        if value and value < date.today():
            raise serializers.ValidationError("Document has expired")
        return value


class DocumentUploadSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for document upload
    """
    class Meta:
        model = VoterDocument
        fields = [
            'document_type', 'document_number', 'issuing_country',
            'issue_date', 'expiry_date', 'document_file'
        ]


class VoterRegistrationSerializer(serializers.Serializer):
    """
    Complete voter registration serializer
    Combines user creation and voter profile
    """
    # User fields
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=12)
    password_confirm = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    phone_number = serializers.CharField(max_length=17, allow_blank=True)
    
    # Voter profile fields
    date_of_birth = serializers.DateField()
    gender = serializers.ChoiceField(choices=VoterProfile.GENDER_CHOICES)
    marital_status = serializers.ChoiceField(choices=VoterProfile.MARITAL_STATUS_CHOICES)
    street_address = serializers.CharField(max_length=255, allow_blank=True)
    city = serializers.CharField(max_length=100, allow_blank=True)
    state_province = serializers.CharField(max_length=100, allow_blank=True)
    postal_code = serializers.CharField(max_length=20, allow_blank=True)
    country = serializers.CharField(max_length=100, default='Kenya')
    occupation = serializers.CharField(max_length=255, allow_blank=True)
    employer = serializers.CharField(max_length=255, allow_blank=True)
    disability_status = serializers.ChoiceField(choices=VoterProfile.DISABILITY_STATUS_CHOICES)
    disability_description = serializers.CharField(allow_blank=True)
    
    def validate(self, data):
        """Validate combined user and voter data"""
        # Check passwords match
        if data['password'] != data.pop('password_confirm'):
            raise serializers.ValidationError({'password': 'Passwords do not match'})
        
        # Check email unique
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({'email': 'Email already registered'})
        
        # Check age
        from dateutil.relativedelta import relativedelta
        age = relativedelta(date.today(), data['date_of_birth']).years
        if age < 18:
            raise serializers.ValidationError(
                {'date_of_birth': 'Must be at least 18 years old'}
            )
        
        return data
    
    def create(self, validated_data):
        """Create user and voter profile"""
        # Create user
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            phone_number=validated_data.get('phone_number', ''),
            role='voter',
            status='pending'
        )
        
        # Create voter profile
        voter_profile = VoterProfile.objects.create(
            user=user,
            date_of_birth=validated_data['date_of_birth'],
            gender=validated_data.get('gender', ''),
            marital_status=validated_data.get('marital_status', ''),
            street_address=validated_data.get('street_address', ''),
            city=validated_data.get('city', ''),
            state_province=validated_data.get('state_province', ''),
            postal_code=validated_data.get('postal_code', ''),
            country=validated_data.get('country', 'Kenya'),
            occupation=validated_data.get('occupation', ''),
            employer=validated_data.get('employer', ''),
            disability_status=validated_data.get('disability_status', 'N'),
            disability_description=validated_data.get('disability_description', '')
        )
        
        return {
            'user': user,
            'voter_profile': voter_profile
        }


class EligibilityRuleSerializer(serializers.ModelSerializer):
    """
    Eligibility rule serializer
    """
    rule_type_display = serializers.CharField(
        source='get_rule_type_display',
        read_only=True
    )
    created_by_email = serializers.CharField(
        source='created_by.email',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = EligibilityRule
        fields = [
            'id', 'rule_name', 'rule_type', 'rule_type_display',
            'description', 'is_active', 'minimum_age', 'maximum_age',
            'created_at', 'updated_at', 'created_by_email'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'created_by_email'
        ]


class VerificationLogSerializer(serializers.ModelSerializer):
    """
    Verification log serializer
    """
    action_display = serializers.CharField(
        source='get_action_display',
        read_only=True
    )
    performed_by_email = serializers.CharField(
        source='performed_by.email',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = VerificationLog
        fields = [
            'id', 'action', 'action_display', 'performed_by_email',
            'description', 'timestamp', 'details'
        ]
        read_only_fields = [
            'id', 'action_display', 'performed_by_email',
            'timestamp', 'details'
        ]
