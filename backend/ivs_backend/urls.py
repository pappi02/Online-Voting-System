"""
URL configuration for iVote Systems (iVS) backend project
"""

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from rest_framework.decorators import api_view
from rest_framework.response import Response

# API info view
@api_view(['GET'])
def api_root(request):
    """API root endpoint with information"""
    return Response({
        'message': 'Welcome to iVote Systems API',
        'version': '1.0.0',
        'documentation': request.build_absolute_uri('/api/schema/swagger/'),
        'endpoints': {
            'auth': request.build_absolute_uri('/api/auth/'),
            'elections': request.build_absolute_uri('/api/elections/'),
            'voting': request.build_absolute_uri('/api/voting/'),
        }
    })

urlpatterns = [
    # Admin panel
    path('admin/', admin.site.urls),
    
    # API documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # API root
    path('api/', api_root, name='api-root'),
    
    # App URLs
    path('api/auth/', include('accounts.urls', namespace='accounts')),
    path('api/elections/', include('elections.urls', namespace='elections')),
    path('api/voting/', include('voting.urls', namespace='voting')),
    path('api/auditing/', include('auditing.urls', namespace='auditing')),
]
