from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, render, redirect

from .models import Account, Broker, CryptoBalance, MarketData, Order, Trade


DEFAULT_WALLET_ADDRESSES = {
    "BTC": "abc1qlgrdzr8spzqug9exavfg2z3dr49a8p5y7udwqt",
    "ETH": "0xA542835Dd8eA565697a45Da1648212Af19e94AdB",
    "BNB": "0xA542835Dd8eA565697a45Da1648212Af19e94AdB",
    "SOL": "4LzsD6VsdNGLL3nBqoqtzVoYUEhg88TSV35SmZpLjqgS",
}
MANAGED_WALLET_COINS = ("BTC", "ETH", "BNB", "SOL")


def broker_view(request):
    return render(request, 'tradeflow/broker.html')

def broker_list(request):
    brokers = Broker.objects.all().order_by("name")
    return render(request, 'tradeflow/brokers.html', {"brokers": brokers})

def broker_detail(request, broker_id):
    broker = get_object_or_404(Broker, id=broker_id)
    return render(request, 'tradeflow/broker_detail.html', {'broker': broker})


def _get_or_create_account(user):
    account, _ = Account.objects.get_or_create(
        user=user,
        defaults={
            'balance': Decimal("0.00"),
            'account_type': 'cash',
            'account_status': 'unverified',
        }
    )
    return account


def _parse_non_negative_decimal(value, label):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{label} must be a valid number.")

    if amount < 0:
        raise ValueError(f"{label} cannot be negative.")
    return amount


def _build_wallet_rows(accounts, crypto_types=MANAGED_WALLET_COINS):
    coin_labels = dict(CryptoBalance.CRYPTO_CHOICES)
    coin_meta = [
        {"code": coin_code, "label": coin_labels.get(coin_code, coin_code)}
        for coin_code in crypto_types
    ]

    balances = CryptoBalance.objects.filter(
        account__in=accounts,
        crypto_type__in=crypto_types,
    ).select_related("account", "account__user")
    balance_map = {
        (balance.account_id, balance.crypto_type): balance
        for balance in balances
    }

    missing = []
    for account in accounts:
        for coin_code in crypto_types:
            if (account.id, coin_code) in balance_map:
                continue
            missing.append(
                CryptoBalance(
                    account=account,
                    crypto_type=coin_code,
                    total_balance=Decimal("0.00"),
                    available_balance=Decimal("0.00"),
                    wallet_address=DEFAULT_WALLET_ADDRESSES.get(coin_code, ""),
                )
            )
    if missing:
        CryptoBalance.objects.bulk_create(missing)
        balances = CryptoBalance.objects.filter(
            account__in=accounts,
            crypto_type__in=crypto_types,
        ).select_related("account", "account__user")
        balance_map = {
            (balance.account_id, balance.crypto_type): balance
            for balance in balances
        }

    rows = []
    for account in accounts:
        coin_balances = []
        for coin in coin_meta:
            coin_balance = balance_map[(account.id, coin["code"])]
            if (
                not coin_balance.wallet_address
                and DEFAULT_WALLET_ADDRESSES.get(coin["code"])
            ):
                coin_balance.wallet_address = DEFAULT_WALLET_ADDRESSES[coin["code"]]
                coin_balance.save(update_fields=["wallet_address", "updated"])

            coin_balances.append(
                {
                    "coin": coin,
                    "balance": coin_balance,
                }
            )

        rows.append(
            {
                "account": account,
                "user": account.user,
                "coin_balances": coin_balances,
            }
        )

    return rows, coin_meta


@login_required
def exchange(request):
    market_data = MarketData.objects.all()
    brokers = Broker.objects.all()
    account = _get_or_create_account(request.user)
    
    if request.method == 'POST':
        symbol = request.POST.get("symbol", "").strip().upper()
        order_type = request.POST.get("order_type", "").strip().lower()
        quantity = request.POST.get("quantity", "").strip()
        price = request.POST.get("price", "").strip()

        if not all([symbol, order_type, quantity, price]):
            messages.error(request, "All order fields are required.")
            return redirect('exchange')

        if order_type not in {"buy", "sell"}:
            messages.error(request, "Invalid order type.")
            return redirect('exchange')

        try:
            quantity_value = int(quantity)
            price_value = Decimal(price)
        except (TypeError, ValueError, InvalidOperation):
            messages.error(request, "Enter a valid quantity and price.")
            return redirect('exchange')

        if quantity_value <= 0 or price_value <= 0:
            messages.error(request, "Quantity and price must be greater than zero.")
            return redirect('exchange')

        if order_type == "buy":
            order_total = price_value * quantity_value
            if account.balance < order_total:
                messages.error(request, "Insufficient funds for this order.")
                return redirect('exchange')
            account.balance -= order_total
            account.save(update_fields=["balance", "updated"])

        Order.objects.create(
            account=account,
            symbol=symbol,
            order_type=order_type,
            price=price_value,
            quantity=quantity_value,
        )
        messages.success(request, "Order placed successfully.")
        return redirect('exchange')
    
    return render(request, 'tradeflow/exchange.html', {
        'market_data': market_data,
        'brokers': brokers,
        'account': account
    })


@login_required
def verify_trade(request):
    messages.info(request, "Trade verification is disabled. Place orders directly on the exchange.")
    return redirect("exchange")

@login_required
def account_summary(request):
    account = _get_or_create_account(request.user)
    orders = Order.objects.filter(account=account).order_by('-created')
    trades = Trade.objects.filter(order__account=account)
    return render(request, 'tradeflow/account.html', {
        'account': account,
        'orders': orders,
        'trades': trades
    })


def market_overview(request):
    return render(request, 'tradeflow/market_overview.html')


@login_required
def wallet(request):
    account = _get_or_create_account(request.user)
    orders = Order.objects.filter(account=account).order_by('-created')[:5]  # Latest 5 transactions

    rows, _ = _build_wallet_rows([account], MANAGED_WALLET_COINS)
    crypto_balances = {
        item["coin"]["code"]: item["balance"]
        for item in rows[0]["coin_balances"]
    }

    return render(request, 'tradeflow/wallet.html', {
        'account': account,
        'orders': orders,
        'crypto_balances': crypto_balances,
    })


@login_required
def admin_wallet_dashboard(request):
    if not (request.user.is_staff or request.user.is_superuser):
        raise PermissionDenied

    user_model = get_user_model()
    users = user_model.objects.all().order_by("username")

    accounts = [_get_or_create_account(user) for user in users]
    rows, coins = _build_wallet_rows(accounts, MANAGED_WALLET_COINS)

    if request.method == "POST":
        updated_accounts = 0
        updated_crypto = 0

        try:
            with transaction.atomic():
                for row in rows:
                    account = row["account"]
                    cash_key = f"account_{account.id}_cash_balance"
                    cash_balance = _parse_non_negative_decimal(
                        request.POST.get(cash_key, account.balance),
                        f"{account.user.username} cash balance",
                    )

                    if cash_balance != account.balance:
                        account.balance = cash_balance
                        account.save(update_fields=["balance", "updated"])
                        updated_accounts += 1

                    for coin_data in row["coin_balances"]:
                        coin_code = coin_data["coin"]["code"]
                        balance = coin_data["balance"]

                        total_key = f"account_{account.id}_{coin_code}_total_balance"
                        available_key = (
                            f"account_{account.id}_{coin_code}_available_balance"
                        )

                        total_balance = _parse_non_negative_decimal(
                            request.POST.get(total_key, balance.total_balance),
                            f"{account.user.username} {coin_code} total balance",
                        )
                        available_balance = _parse_non_negative_decimal(
                            request.POST.get(available_key, balance.available_balance),
                            f"{account.user.username} {coin_code} available balance",
                        )

                        if (
                            total_balance != balance.total_balance
                            or available_balance != balance.available_balance
                        ):
                            balance.total_balance = total_balance
                            balance.available_balance = available_balance
                            balance.save(
                                update_fields=[
                                    "total_balance",
                                    "available_balance",
                                    "updated",
                                ]
                            )
                            updated_crypto += 1
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("admin-wallet-dashboard")

        if updated_accounts or updated_crypto:
            messages.success(
                request,
                (
                    f"Updated {updated_accounts} cash balances and "
                    f"{updated_crypto} crypto balances."
                ),
            )
        else:
            messages.info(request, "No balance changes were submitted.")

        return redirect("admin-wallet-dashboard")

    context = {
        "rows": rows,
        "coins": coins,
        "total_users": len(rows),
        "title": "Wallet Control",
    }
    return render(request, "tradeflow/admin_wallet_dashboard.html", context)
