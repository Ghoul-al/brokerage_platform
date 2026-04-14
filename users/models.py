from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator

class PaymentMethod(models.Model):
    PAYMENT_TYPES = (
        ('bank', 'Bank Account'),
        ('card', 'Credit/Debit Card'),
        ('crypto', 'Cryptocurrency'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPES)
    details = models.JSONField()  # Stores payment method specifics
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_payment_type_display()} - {self.user.username}"

class Profile(models.Model):
    GENDER = (
        ('M', 'Male'),
        ('F', 'Female'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100, null=True, blank=True)
    username = models.CharField(max_length=200, blank=True, null=True)
    email = models.EmailField(null=True, blank=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER, null=True, blank=True)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True, default='assets/img/avatar.svg')
    two_factor_enabled = models.BooleanField(default=False)
    withdrawal_limit = models.DecimalField(max_digits=12, decimal_places=2, default=5000.00, validators=[MinValueValidator(0)])
    
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"
    
 