from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CustomUserCreationForm, ProfileForm, ProfileUpdateForm, UserUpdateForm
from .models import Profile


User = get_user_model()
LOGIN_ATTEMPT_WINDOW_SECONDS = 300
LOGIN_MAX_ATTEMPTS = 5


def get_user_profile(user):
    profile, _ = Profile.objects.get_or_create(
        user=user,
        defaults={
            "username": user.username,
            "email": user.email,
        },
    )
    if profile.username != user.username or profile.email != user.email:
        profile.username = user.username
        profile.email = user.email
        profile.save(update_fields=["username", "email"])
    return profile


def is_login_blocked(ip):
    return cache.get(f"login_block_{ip}") is True


def register_failed_login(ip):
    key = f"login_attempts_{ip}"
    attempts = cache.get(key, 0) + 1
    cache.set(key, attempts, LOGIN_ATTEMPT_WINDOW_SECONDS)
    return attempts


def block_login(ip):
    cache.set(f"login_block_{ip}", True, LOGIN_ATTEMPT_WINDOW_SECONDS)


def clear_login_attempt_state(ip):
    cache.delete_many([f"login_attempts_{ip}", f"login_block_{ip}"])


def resolve_auth_username(identifier):
    normalized = identifier.strip()
    if not normalized:
        return ""

    username_match = User.objects.filter(username__iexact=normalized).first()
    if username_match:
        return username_match.username

    email_match = User.objects.filter(email__iexact=normalized).first()
    if email_match:
        return email_match.username

    return normalized


def signup(request):
    form = CustomUserCreationForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.is_active = True
        user.save()

        # Keep Profile data synchronized at registration time.
        get_user_profile(user)

        messages.success(request, "Account created successfully. You can now sign in.")
        return redirect("users:login")

    return render(request, "users/signup.html", {"form": form})


def loginUser(request):
    if request.user.is_authenticated:
        return redirect("users:profile")

    ip = request.META.get("REMOTE_ADDR", "unknown")

    if is_login_blocked(ip):
        messages.error(request, "Too many failed attempts. Try again in 5 minutes.")
        return render(request, "users/login_logout.html")

    if request.method == "POST":
        identifier = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        remember_me = request.POST.get("remember_me")

        if not identifier or not password:
            messages.error(request, "Enter your username or email and password.")
            return render(request, "users/login_logout.html")

        auth_username = resolve_auth_username(identifier)
        user = authenticate(request, username=auth_username, password=password)

        if user:
            login(request, user)
            clear_login_attempt_state(ip)

            if remember_me:
                request.session.set_expiry(60 * 60 * 24 * 14)
            else:
                request.session.set_expiry(0)

            return redirect("users:profile")

        attempts = register_failed_login(ip)
        if attempts >= LOGIN_MAX_ATTEMPTS:
            block_login(ip)
            messages.error(request, "Too many failed attempts. Try again in 5 minutes.")
        else:
            messages.error(request, "Invalid username/email or password.")

    return render(request, "users/login_logout.html")


def logoutUser(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect("users:login")


@login_required
def profile(request):
    profile_obj = get_user_profile(request.user)
    return render(request, "users/profile.html", {"profile": profile_obj})


@login_required
def profile_view(request, username):
    target_user = get_object_or_404(User, username=username)
    profile_obj = get_user_profile(target_user)

    return render(
        request,
        "users/profile_view.html",
        {
            "profile": profile_obj,
        },
    )


@login_required
def profile_update(request):
    try:
        account = request.user.tradeflow_account
    except Exception:
        account = None

    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(
            request.POST,
            request.FILES,
            instance=get_user_profile(request.user),
        )

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return redirect("users:profile_view", username=request.user.username)
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=get_user_profile(request.user))

    return render(
        request,
        "users/profile_update.html",
        {
            "user_form": user_form,
            "profile_form": profile_form,
            "account": account,
        },
    )


@login_required
def edit_profile(request):
    profile_obj = get_user_profile(request.user)

    form = ProfileForm(
        request.POST or None,
        request.FILES or None,
        instance=profile_obj,
    )

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("users:profile")

    return render(request, "users/edit_profile.html", {"form": form})
