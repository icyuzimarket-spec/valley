from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render

from core.models import SiteSettings

from .forms import PhoneAuthenticationForm, ProfileForm, SignUpForm
from .models import User


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard_redirect")

    initial = {"referral_code": request.GET.get("ref", "")}
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                code = form.cleaned_data["referral_code"].strip()
                referrer = User.objects.filter(referral_code__iexact=code).first() if code else None
                is_fallback = referrer is None

                new_user = User(
                    phone_number=form.cleaned_data["phone_number"],
                    full_name=form.cleaned_data["full_name"],
                    referred_by=referrer if referrer else SiteSettings.load().fallback_referrer,
                    is_fallback_referral=is_fallback,
                )
                new_user.set_password(form.cleaned_data["password1"])
                new_user.save()

            auth_login(request, new_user)
            messages.success(request, "Welcome to Valley Investment! Choose a plan to get started.")
            return redirect("core:dashboard_redirect")
    else:
        form = SignUpForm(initial=initial)

    return render(request, "accounts/signup.html", {"form": form})


class PhoneLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = PhoneAuthenticationForm
    redirect_authenticated_user = True


class PhoneLogoutView(LogoutView):
    next_page = "core:home"


@login_required
def profile_view(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=request.user)

    referral_link = request.build_absolute_uri(request.user.get_referral_path())
    return render(
        request,
        "accounts/profile.html",
        {"form": form, "referral_link": referral_link},
    )
