"""
WebSocket URL routing for voting app
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/election/(?P<election_id>[0-9a-f-]+)/$', consumers.ElectionConsumer.as_asgi()),
    re_path(r'ws/dashboard/$', consumers.DashboardConsumer.as_asgi()),
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/broadcast/$', consumers.BroadcastConsumer.as_asgi()),
]
