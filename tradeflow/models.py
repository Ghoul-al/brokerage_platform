from django.db import models
from django.conf import settings
from decimal import Decimal

class Broker(models.Model):
    name = models.CharField(max_length=100)
    rating = models.DecimalField(max_digits=3, decimal_places=1)
    commission_rate = models.DecimalField(max_digits=4, decimal_places=2)
    minimum_deposit = models.DecimalField(max_digits=10, decimal_places=2)
    regulation = models.CharField(max_length=100)   
    account_types = models.CharField(max_length=200)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Account(models.Model):
    ACCOUNT_STATUS = (
        ('verified', 'Verified'),
        ('unverified', 'Unverified'),
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tradeflow_account')
    balance = models.DecimalField(max_digits=12, decimal_places=2)
    account_type = models.CharField(max_length=20, choices=[('cash', 'Cash'), ('margin', 'Margin')])
    account_status = models.CharField(max_length=10, choices=ACCOUNT_STATUS, default='unverified')
    total_withdrawals = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    withdrawal_limit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('10000.00'))
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Account"

class Order(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=10)
    order_type = models.CharField(max_length=10, choices=[('buy', 'Buy'), ('sell', 'Sell')])
    price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.IntegerField()
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('filled', 'Filled'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired')
    ], default='pending')
    security_key = models.CharField(max_length=6, blank=True)  # For 2FA confirmation
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order_type} {self.quantity} of {self.symbol} at {self.price}"

class Trade(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    broker = models.ForeignKey(Broker, on_delete=models.CASCADE, default=1)  # Set a default Broker id (replace 1 with an actual Broker ID)
    trade_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.IntegerField()
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Replace 0.00 with your default value
    trade_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Trade of {self.quantity} {self.order.symbol} at {self.trade_price}"

class MarketData(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    current_price = models.DecimalField(max_digits=12, decimal_places=2)
    high_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    low_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    volume = models.BigIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.symbol} - {self.current_price} (H: {self.high_price}, L: {self.low_price})"

class CryptoBalance(models.Model):
    """Store cryptocurrency balances for each user account"""
    CRYPTO_CHOICES = [
        ('USD', 'US Dollar'),
        ('BTC', 'Bitcoin'),
        ('ETH', 'Ethereum'),
        ('BNB', 'Binance Coin'),
        ('USDT', 'Tether'),
        ('SOL', 'Solana'),
        ('XRP', 'XRP'),
        ('USDC', 'USD Coin'),
    ]
    
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='crypto_balances')
    crypto_type = models.CharField(max_length=10, choices=CRYPTO_CHOICES)
    total_balance = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal('0.00'))
    available_balance = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal('0.00'))
    wallet_address = models.CharField(max_length=255, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('account', 'crypto_type')
        verbose_name_plural = 'Crypto Balances'

    def __str__(self):
        return f"{self.account.user.username} - {self.crypto_type}: {self.total_balance}"
