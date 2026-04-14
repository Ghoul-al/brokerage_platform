from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class UserFlowTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_signup_creates_active_user_and_redirects_to_login(self):
        response = self.client.post(
            reverse("users:signup"),
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertRedirects(response, reverse("users:login"))
        user = User.objects.get(username="newuser")
        self.assertTrue(user.is_active)

    def test_login_with_username(self):
        user = User.objects.create_user(
            username="simplelogin",
            email="simplelogin@example.com",
            password="StrongPass123!",
        )

        response = self.client.post(
            reverse("users:login"),
            {"username": "simplelogin", "password": "StrongPass123!"},
        )

        self.assertRedirects(response, reverse("users:profile"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_login_with_email(self):
        user = User.objects.create_user(
            username="emaillogin",
            email="emaillogin@example.com",
            password="StrongPass123!",
        )

        response = self.client.post(
            reverse("users:login"),
            {"username": "emaillogin@example.com", "password": "StrongPass123!"},
        )

        self.assertRedirects(response, reverse("users:profile"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_login_rejects_invalid_credentials(self):
        User.objects.create_user(
            username="badlogin",
            email="badlogin@example.com",
            password="StrongPass123!",
        )

        response = self.client.post(
            reverse("users:login"),
            {"username": "badlogin", "password": "wrong-pass"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username/email or password.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_rate_limit_blocks_after_repeated_failures(self):
        User.objects.create_user(
            username="ratelimit",
            email="ratelimit@example.com",
            password="StrongPass123!",
        )

        for _ in range(5):
            self.client.post(
                reverse("users:login"),
                {"username": "ratelimit", "password": "wrong-pass"},
            )

        self.assertTrue(cache.get("login_block_127.0.0.1"))

        response = self.client.post(
            reverse("users:login"),
            {"username": "ratelimit", "password": "StrongPass123!"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Too many failed attempts. Try again in 5 minutes.")

    def test_logout_redirects_to_login(self):
        user = User.objects.create_user(
            username="logoutuser",
            email="logout@example.com",
            password="StrongPass123!",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("users:logout"))

        self.assertRedirects(response, reverse("users:login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_new_user_has_profile_and_tradeflow_account(self):
        user = User.objects.create_user(
            username="linkeduser",
            email="linked@example.com",
            password="StrongPass123!",
        )

        self.assertTrue(hasattr(user, 'profile'))
        self.assertEqual(user.profile.username, user.username)
        self.assertEqual(user.profile.email, user.email)

        self.assertTrue(hasattr(user, 'tradeflow_account'))
        self.assertEqual(user.tradeflow_account.balance, Decimal('0.00'))
        self.assertEqual(user.tradeflow_account.account_type, 'cash')
        self.assertEqual(user.tradeflow_account.account_status, 'unverified')

    def test_profile_pages_render_for_authenticated_user(self):
        user = User.objects.create_user(
            username="profileuser",
            email="profile@example.com",
            password="StrongPass123!",
        )
        self.client.force_login(user)

        profile_response = self.client.get(reverse("users:profile"))
        public_response = self.client.get(reverse("users:profile_view", args=[user.username]))
        update_response = self.client.get(reverse("users:profile-update"))

        self.assertEqual(profile_response.status_code, 200)
        self.assertTemplateUsed(profile_response, "users/profile.html")
        self.assertEqual(public_response.status_code, 200)
        self.assertTemplateUsed(public_response, "users/profile_view.html")
        self.assertEqual(update_response.status_code, 200)
        self.assertTemplateUsed(update_response, "users/profile_update.html")
