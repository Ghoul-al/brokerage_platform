from django.urls import path
from . import views

urlpatterns = [
    path('admin-dashboard/wallets/', views.admin_wallet_dashboard, name='admin-wallet-dashboard'),
    path('exchange/', views.exchange, name='exchange'),
    path('verify/', views.verify_trade, name='verify-trade'),
    path('account/', views.account_summary, name='account-summary'),
    path('wallet/', views.wallet, name='wallet'),
    path('brokers/', views.broker_list, name='brokers'),
    path('market-overview/', views.market_overview, name='market-overview'),

    path('broker/', views.broker_view, name='broker'),
    path('brokers/<int:broker_id>/', views.broker_detail, name='broker_detail'),
]
