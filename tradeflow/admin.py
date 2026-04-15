from decimal import Decimal, InvalidOperation

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import path

from .models import Account, Broker, CryptoBalance, MarketData, Order, Trade


MANAGED_CRYPTO_TYPES = ("BTC", "ETH", "BNB", "SOL")
DEFAULT_WALLET_ADDRESSES = {
    "BTC": "abc1qlgrdzr8spzqug9exavfg2z3dr49a8p5y7udwqt",
    "ETH": "0xA542835Dd8eA565697a45Da1648212Af19e94AdB",
    "BNB": "0xA542835Dd8eA565697a45Da1648212Af19e94AdB",
    "SOL": "4LzsD6VsdNGLL3nBqoqtzVoYUEhg88TSV35SmZpLjqgS",
}


class CryptoBalanceInline(admin.TabularInline):
    model = CryptoBalance
    extra = 0
    fields = ("crypto_type", "total_balance", "available_balance", "wallet_address")


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    inlines = [CryptoBalanceInline]
    list_display = ("user", "balance", "account_type", "account_status", "created")
    list_filter = ("account_status", "account_type", "created")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("created", "updated")
    change_list_template = "admin/tradeflow/account/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "wallet-balances/",
                self.admin_site.admin_view(self.wallet_balances_view),
                name="tradeflow_account_wallet_balances",
            ),
        ]
        return custom_urls + urls

    def _parse_decimal(self, value, label):
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError(f"{label} must be a valid number.")
        if amount < 0:
            raise ValueError(f"{label} cannot be negative.")
        return amount

    def _build_rows(self, accounts):
        coin_labels = dict(CryptoBalance.CRYPTO_CHOICES)
        coins = [
            {"code": coin_code, "label": coin_labels.get(coin_code, coin_code)}
            for coin_code in MANAGED_CRYPTO_TYPES
        ]

        balances = CryptoBalance.objects.filter(
            account__in=accounts,
            crypto_type__in=MANAGED_CRYPTO_TYPES,
        ).select_related("account")
        balance_map = {(balance.account_id, balance.crypto_type): balance for balance in balances}

        missing = []
        for account in accounts:
            for coin in MANAGED_CRYPTO_TYPES:
                if (account.id, coin) not in balance_map:
                    missing.append(
                        CryptoBalance(
                            account=account,
                            crypto_type=coin,
                            wallet_address=DEFAULT_WALLET_ADDRESSES.get(coin, ""),
                        )
                    )
        if missing:
            CryptoBalance.objects.bulk_create(missing)
            balances = CryptoBalance.objects.filter(
                account__in=accounts,
                crypto_type__in=MANAGED_CRYPTO_TYPES,
            ).select_related("account")
            balance_map = {(balance.account_id, balance.crypto_type): balance for balance in balances}

        rows = []
        for account in accounts:
            coin_balances = []
            for coin in coins:
                balance = balance_map[(account.id, coin["code"])]
                if (
                    not balance.wallet_address
                    and DEFAULT_WALLET_ADDRESSES.get(coin["code"])
                ):
                    balance.wallet_address = DEFAULT_WALLET_ADDRESSES[coin["code"]]
                    balance.save(update_fields=["wallet_address", "updated"])
                coin_balances.append(
                    {
                        "coin": coin,
                        "balance": balance,
                    }
                )
            rows.append({"account": account, "coin_balances": coin_balances})
        return rows, coins

    def wallet_balances_view(self, request):
        if not self.has_change_permission(request):
            raise PermissionDenied

        accounts = list(Account.objects.select_related("user").order_by("user__username"))

        if request.method == "POST":
            rows, coins = self._build_rows(accounts)
            updated_accounts = 0
            updated_crypto = 0

            try:
                with transaction.atomic():
                    for row in rows:
                        account = row["account"]
                        cash_key = f"account_{account.id}_cash_balance"
                        new_cash_balance = self._parse_decimal(
                            request.POST.get(cash_key, account.balance),
                            f"{account.user.username} cash balance",
                        )

                        if new_cash_balance != account.balance:
                            account.balance = new_cash_balance
                            account.save(update_fields=["balance", "updated"])
                            updated_accounts += 1

                        for coin_data in row["coin_balances"]:
                            coin_code = coin_data["coin"]["code"]
                            balance = coin_data["balance"]

                            total_key = (
                                f"account_{account.id}_{coin_code}_total_balance"
                            )
                            available_key = (
                                f"account_{account.id}_{coin_code}_available_balance"
                            )
                            address_key = (
                                f"account_{account.id}_{coin_code}_wallet_address"
                            )

                            new_total = self._parse_decimal(
                                request.POST.get(total_key, balance.total_balance),
                                f"{account.user.username} {coin_code} total balance",
                            )
                            new_available = self._parse_decimal(
                                request.POST.get(available_key, balance.available_balance),
                                f"{account.user.username} {coin_code} available balance",
                            )
                            new_address = (
                                request.POST.get(
                                    address_key,
                                    balance.wallet_address,
                                )
                                or ""
                            ).strip()

                            if (
                                new_total != balance.total_balance
                                or new_available != balance.available_balance
                                or new_address != balance.wallet_address
                            ):
                                balance.total_balance = new_total
                                balance.available_balance = new_available
                                balance.wallet_address = new_address
                                balance.save(
                                    update_fields=[
                                        "total_balance",
                                        "available_balance",
                                        "wallet_address",
                                        "updated",
                                    ]
                                )
                                updated_crypto += 1
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect("admin:tradeflow_account_wallet_balances")

            if updated_accounts or updated_crypto:
                messages.success(
                    request,
                    (
                        f"Updated {updated_accounts} cash balances and "
                        f"{updated_crypto} crypto wallet records."
                    ),
                )
            else:
                messages.info(request, "No balance changes were submitted.")

            return redirect("admin:tradeflow_account_wallet_balances")

        rows, coins = self._build_rows(accounts)
        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Wallet Balance Manager",
            "rows": rows,
            "coins": coins,
        }
        return render(request, "admin/tradeflow/wallet_balances.html", context)


@admin.register(CryptoBalance)
class CryptoBalanceAdmin(admin.ModelAdmin):
    list_display = (
        "account",
        "crypto_type",
        "total_balance",
        "available_balance",
        "updated",
    )
    list_filter = ("crypto_type", "updated")
    search_fields = ("account__user__username", "account__user__email")
    readonly_fields = ("created", "updated")
    list_select_related = ("account", "account__user")


admin.site.register(Broker)
admin.site.register(Order)
admin.site.register(Trade)
admin.site.register(MarketData)
