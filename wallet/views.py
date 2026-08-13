from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from . import services
from .forms import WithdrawalRequestForm
from .models import Withdrawal


@login_required
def countdown_clock_view(request):
    next_eligible = services.next_withdrawal_window(request.user)
    is_open_now = timezone.now() >= next_eligible
    return render(
        request,
        "wallet/countdown.html",
        {"next_eligible": next_eligible, "is_open_now": is_open_now},
    )


@login_required
def withdraw_view(request):
    next_eligible = services.next_withdrawal_window(request.user)
    is_open_now = timezone.now() >= next_eligible

    if request.method == "POST":
        form = WithdrawalRequestForm(request.POST)
        if form.is_valid():
            try:
                services.request_withdrawal(request.user, form.cleaned_data["amount"])
                messages.success(request, "Withdrawal request submitted. An admin will process it shortly.")
                return redirect("wallet:withdraw")
            except services.WithdrawalNotAllowed as exc:
                messages.error(
                    request,
                    f"Withdrawals aren't open right now. Next window opens {timezone.localtime(exc.next_eligible):%Y-%m-%d %H:%M}.",
                )
            except services.InsufficientBalance:
                messages.error(request, "Enter a valid amount within your available balance.")
    else:
        form = WithdrawalRequestForm()

    history = Withdrawal.objects.filter(user=request.user)[:20]
    return render(
        request,
        "wallet/withdraw.html",
        {
            "form": form,
            "next_eligible": next_eligible,
            "is_open_now": is_open_now,
            "history": history,
        },
    )
