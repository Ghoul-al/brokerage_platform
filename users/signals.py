from decimal import Decimal

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Profile

User = get_user_model()

@receiver(post_save, sender=User)
def create_profile_and_account(sender, instance, created, **kwargs):
    profile, _ = Profile.objects.get_or_create(
        user=instance,
        defaults={
            'username': instance.username,
            'email': instance.email,
        }
    )

    if profile.username != instance.username or profile.email != instance.email:
        profile.username = instance.username
        profile.email = instance.email
        profile.save(update_fields=['username', 'email'])

    if created:
        try:
            from tradeflow.models import Account

            Account.objects.get_or_create(
                user=instance,
                defaults={
                    'balance': Decimal('0.00'),
                    'account_type': 'cash',
                    'account_status': 'unverified',
                }
            )
        except Exception:
            # Tradeflow may not be ready during some management operations.
            pass

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()

# Signal to delete a user when their profile is deleted
def delete_user(sender, instance, **kwargs):
    instance.user.delete()
    print('User deleted!')

