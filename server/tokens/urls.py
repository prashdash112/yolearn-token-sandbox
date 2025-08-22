from django.urls import path
from .views import create_quote, authorize, push_usage, settle, wallet_view

urlpatterns = [
    path("wallet", wallet_view, name="wallet"),
    path("quotes", create_quote, name="create_quote"),
    path("quotes/<str:quote_id>/authorize", authorize, name="authorize"),
    path("usage", push_usage, name="push_usage"),
    path("quotes/<str:quote_id>/settle", settle, name="settle"),
]