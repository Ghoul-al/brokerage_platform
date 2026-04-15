from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Account, Broker, CryptoBalance, MarketData, Order


User = get_user_model()


class TradeflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="trader",
            email="trader@example.com",
            password="StrongPass123!",
        )
        self.client.force_login(self.user)
        self.broker = Broker.objects.create(
            name="Alpha Broker",
            rating=Decimal("4.5"),
            commission_rate=Decimal("1.25"),
            minimum_deposit=Decimal("100.00"),
            regulation="SEC",
            account_types="cash,margin",
        )
        MarketData.objects.create(
            symbol="AAPL",
            current_price=Decimal("150.00"),
            high_price=Decimal("155.00"),
            low_price=Decimal("149.00"),
            volume=1000,
        )

    def test_broker_list_and_detail_render(self):
        list_response = self.client.get(reverse("brokers"))
        detail_response = self.client.get(reverse("broker_detail", args=[self.broker.id]))

        self.assertEqual(list_response.status_code, 200)
        self.assertTemplateUsed(list_response, "tradeflow/brokers.html")
        self.assertContains(list_response, "Alpha Broker")
        self.assertEqual(detail_response.status_code, 200)
        self.assertTemplateUsed(detail_response, "tradeflow/broker_detail.html")

    def test_exchange_renders_correct_template_and_creates_account(self):
        response = self.client.get(reverse("exchange"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tradeflow/exchange.html")
        self.assertTrue(Account.objects.filter(user=self.user).exists())

    def test_exchange_places_buy_order_without_verification(self):
        account = Account.objects.get(user=self.user)
        account.balance = Decimal("1000.00")
        account.account_type = "cash"
        account.account_status = "verified"
        account.save(update_fields=["balance", "account_type", "account_status"])

        response = self.client.post(
            reverse("exchange"),
            {
                "symbol": "AAPL",
                "order_type": "buy",
                "quantity": "2",
                "price": "100.00",
            },
        )

        self.assertRedirects(response, reverse("exchange"))
        self.assertEqual(Order.objects.count(), 1)

        order = Order.objects.get()
        self.assertEqual(order.symbol, "AAPL")
        self.assertEqual(order.order_type, "buy")
        self.assertEqual(order.quantity, 2)
        self.assertEqual(order.price, Decimal("100.00"))
        self.assertEqual(order.security_key, "")

        account.refresh_from_db()
        self.assertEqual(account.balance, Decimal("800.00"))

    def test_exchange_rejects_invalid_order_type(self):
        account = Account.objects.get(user=self.user)
        account.balance = Decimal("1000.00")
        account.save(update_fields=["balance"])

        response = self.client.post(
            reverse("exchange"),
            {
                "symbol": "AAPL",
                "order_type": "hold",
                "quantity": "2",
                "price": "100.00",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid order type.")
        self.assertEqual(Order.objects.count(), 0)

    def test_exchange_rejects_invalid_numeric_values(self):
        response = self.client.post(
            reverse("exchange"),
            {
                "symbol": "AAPL",
                "order_type": "buy",
                "quantity": "abc",
                "price": "100.00",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a valid quantity and price.")
        self.assertEqual(Order.objects.count(), 0)

    def test_buy_order_fails_when_funds_are_insufficient(self):
        account = Account.objects.get(user=self.user)
        account.balance = Decimal("50.00")
        account.account_type = "cash"
        account.account_status = "verified"
        account.save(update_fields=["balance", "account_type", "account_status"])

        response = self.client.post(
            reverse("exchange"),
            {
                "symbol": "AAPL",
                "order_type": "buy",
                "quantity": "2",
                "price": "100.00",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Insufficient funds for this order.")
        self.assertEqual(Order.objects.count(), 0)

        account.refresh_from_db()
        self.assertEqual(account.balance, Decimal("50.00"))

    def test_verify_route_redirects_when_verification_is_disabled(self):
        response = self.client.get(reverse("verify-trade"), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Trade verification is disabled.")


class TradeflowAdminWalletBalanceTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="adminuser",
            email="admin@example.com",
            password="AdminPass123!",
        )
        self.user = User.objects.create_user(
            username="walletuser",
            email="walletuser@example.com",
            password="StrongPass123!",
        )
        self.client.force_login(self.admin_user)
        self.account = Account.objects.get(user=self.user)

    def test_wallet_balance_admin_page_renders(self):
        response = self.client.get(reverse("admin:tradeflow_account_wallet_balances"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Wallet Balance Manager")
        self.assertContains(response, self.user.username)

    def test_wallet_balance_admin_page_updates_user_balances(self):
        btc_address = "bc1qexampleupdatedbtc123456789"
        eth_address = "0xExampleUpdatedEth123456789"
        response = self.client.post(
            reverse("admin:tradeflow_account_wallet_balances"),
            {
                f"account_{self.account.id}_cash_balance": "1250.50",
                f"account_{self.account.id}_BTC_total_balance": "1.50000000",
                f"account_{self.account.id}_BTC_available_balance": "1.25000000",
                f"account_{self.account.id}_BTC_wallet_address": btc_address,
                f"account_{self.account.id}_ETH_total_balance": "10.50000000",
                f"account_{self.account.id}_ETH_available_balance": "8.50000000",
                f"account_{self.account.id}_ETH_wallet_address": eth_address,
                f"account_{self.account.id}_BNB_total_balance": "6.00000000",
                f"account_{self.account.id}_BNB_available_balance": "5.00000000",
                f"account_{self.account.id}_BNB_wallet_address": "bnbexamplewalletaddress",
                f"account_{self.account.id}_SOL_total_balance": "20.00000000",
                f"account_{self.account.id}_SOL_available_balance": "18.00000000",
                f"account_{self.account.id}_SOL_wallet_address": "solexamplewalletaddress",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal("1250.50"))

        btc_balance = CryptoBalance.objects.get(account=self.account, crypto_type="BTC")
        self.assertEqual(btc_balance.total_balance, Decimal("1.50000000"))
        self.assertEqual(btc_balance.available_balance, Decimal("1.25000000"))
        self.assertEqual(btc_balance.wallet_address, btc_address)

        self.client.force_login(self.user)
        wallet_response = self.client.get(reverse("wallet"))
        account_response = self.client.get(reverse("account-summary"))

        self.assertEqual(wallet_response.status_code, 200)
        self.assertEqual(account_response.status_code, 200)
        self.assertContains(wallet_response, "1.50000000 BTC")
        self.assertContains(wallet_response, btc_address)
        self.assertContains(account_response, "$1250.50")


class TradeflowStaffWalletDashboardTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="staffmember",
            email="staff@example.com",
            password="StaffPass123!",
            is_staff=True,
        )
        self.user = User.objects.create_user(
            username="clientone",
            email="clientone@example.com",
            password="StrongPass123!",
        )
        self.account = Account.objects.get(user=self.user)

    def test_staff_wallet_dashboard_requires_staff(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("admin-wallet-dashboard"))

        self.assertEqual(response.status_code, 403)

    def test_staff_wallet_dashboard_renders_for_staff(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("admin-wallet-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tradeflow/admin_wallet_dashboard.html")
        self.assertContains(response, "Wallet Balance Control")
        self.assertContains(response, self.user.username)

    def test_staff_wallet_dashboard_updates_balances(self):
        btc_address = "bc1qstaffupdatedbtc123456789"
        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse("admin-wallet-dashboard"),
            {
                f"account_{self.account.id}_cash_balance": "350.75",
                f"account_{self.account.id}_BTC_total_balance": "2.00000000",
                f"account_{self.account.id}_BTC_available_balance": "1.75000000",
                f"account_{self.account.id}_BTC_wallet_address": btc_address,
                f"account_{self.account.id}_ETH_total_balance": "5.25000000",
                f"account_{self.account.id}_ETH_available_balance": "4.00000000",
                f"account_{self.account.id}_ETH_wallet_address": "0xstaffexampleethwallet",
                f"account_{self.account.id}_BNB_total_balance": "7.00000000",
                f"account_{self.account.id}_BNB_available_balance": "6.50000000",
                f"account_{self.account.id}_BNB_wallet_address": "staffexamplebnbwallet",
                f"account_{self.account.id}_SOL_total_balance": "12.00000000",
                f"account_{self.account.id}_SOL_available_balance": "11.00000000",
                f"account_{self.account.id}_SOL_wallet_address": "staffexamplesolwallet",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal("350.75"))

        btc_balance = CryptoBalance.objects.get(account=self.account, crypto_type="BTC")
        self.assertEqual(btc_balance.total_balance, Decimal("2.00000000"))
        self.assertEqual(btc_balance.available_balance, Decimal("1.75000000"))
        self.assertEqual(btc_balance.wallet_address, btc_address)

        self.client.force_login(self.user)
        wallet_response = self.client.get(reverse("wallet"))
        account_response = self.client.get(reverse("account-summary"))

        self.assertEqual(wallet_response.status_code, 200)
        self.assertEqual(account_response.status_code, 200)
        self.assertContains(wallet_response, "2.00000000 BTC")
        self.assertContains(wallet_response, btc_address)
        self.assertContains(account_response, "$350.75")
