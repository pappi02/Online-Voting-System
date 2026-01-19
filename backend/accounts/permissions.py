"""
Custom permissions for role-based access control
"""

from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """
    Allow access only to admin users
    """
    message = 'Only administrators can access this resource'
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin())


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allow read access to anyone, write access only to admins
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_admin())


class IsVoter(permissions.BasePermission):
    """
    Allow access only to approved voters
    """
    message = 'Only registered voters can access this resource'
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_voter())


class IsElectionOfficer(permissions.BasePermission):
    """
    Allow access only to election officers
    """
    message = 'Only election officers can access this resource'
    
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and 
            request.user.is_election_officer()
        )


class IsAdminOrElectionOfficer(permissions.BasePermission):
    """
    Allow access to admins and election officers
    """
    message = 'Only admins and election officers can access this resource'
    
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and (
                request.user.is_admin() or request.user.is_election_officer()
            )
        )


class CanVote(permissions.BasePermission):
    """
    Allow voting only if user is eligible
    """
    message = 'You are not eligible to vote'
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.can_vote())


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Allow access if user is the object owner or admin
    """
    message = 'You do not have permission to access this resource'
    
    def has_object_permission(self, request, view, obj):
        # Admin can access any object
        if request.user.is_admin():
            return True
        # User can access their own profile
        return obj.user == request.user


# Additional permissions for voting system
class IsVerifiedVoter(permissions.BasePermission):
    """
    Allow access only to verified voters
    """
    message = 'Only verified voters can access this resource'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user is a voter
        if not request.user.is_voter():
            return False
        
        # Check if voter profile exists and is verified
        try:
            voter_profile = request.user.voter_profile
            return voter_profile.verification_status == 'verified'
        except Exception:
            return False


class IsElectionOfficial(permissions.BasePermission):
    """
    Allow access to election officials (election officers and admins)
    """
    message = 'Only election officials can access this resource'
    
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and (
                request.user.is_admin() or request.user.is_election_officer()
            )
        )


class IsSystemAdmin(permissions.BasePermission):
    """
    Allow access only to system administrators
    """
    message = 'Only system administrators can access this resource'
    
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and 
            (request.user.is_staff or request.user.is_admin())
        )
