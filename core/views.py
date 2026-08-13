from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from investments import services as investment_services
from investments.models import Investment, Plan
from wallet import services as wallet_services
from wallet.models import Transaction, Withdrawal


def home_view(request):
    plans = Plan.objects.filter(is_active=True)
    return render(request, "core/home.html", {"plans": plans})


@login_required
def dashboard_redirect_view(request):
    if request.user.is_staff:
        return redirect("core:admin_dashboard")
    return redirect("core:user_dashboard")


@login_required
def user_dashboard_view(request):
    investment_services.sync_active_investments(request.user)

    investments = Investment.objects.filter(user=request.user)
    transactions = Transaction.objects.filter(user=request.user)[:20]
    withdrawals = Withdrawal.objects.filter(user=request.user)[:10]
    next_withdrawal = wallet_services.next_withdrawal_window(request.user)

    return render(
        request,
        "core/dashboard_user.html",
        {
            "investments": investments,
            "transactions": transactions,
            "withdrawals": withdrawals,
            "next_withdrawal": next_withdrawal,
        },
    )


@staff_member_required
def admin_dashboard_view(request):
    stats = {
        "total_users": User.objects.filter(is_staff=False).count(),
        "pending_investments": Investment.objects.filter(status=Investment.STATUS_PENDING).count(),
        "pending_withdrawals": Withdrawal.objects.filter(status=Withdrawal.STATUS_PENDING).count(),
        "total_invested": sum(
            (inv.amount for inv in Investment.objects.filter(status=Investment.STATUS_APPROVED)),
            start=0,
        ),
        "total_balance_outstanding": sum(
            (u.balance for u in User.objects.filter(is_staff=False)), start=0
        ),
    }
    return render(request, "core/dashboard_admin.html", {"stats": stats})


@staff_member_required
def user_management_users_view(request):
    query = request.GET.get("q", "").strip()
    users = User.objects.filter(is_staff=False)
    if query:
        users = users.filter(Q(phone_number__icontains=query) | Q(full_name__icontains=query))
    return render(request, "core/management_users.html", {"users": users[:200], "query": query})


@staff_member_required
def user_management_investments_view(request):
    if request.method == "POST":
        investment = get_object_or_404(Investment, pk=request.POST.get("investment_id"))
        action = request.POST.get("action")
        if action == "approve":
            investment_services.approve_investment(investment, request.user)
            messages.success(request, f"Approved investment #{investment.pk}.")
        elif action == "reject":
            investment_services.reject_investment(
                investment, request.user, reason=request.POST.get("reason", "")
            )
            messages.success(request, f"Rejected investment #{investment.pk}.")
        return redirect("core:management_investments")

    pending = Investment.objects.filter(status=Investment.STATUS_PENDING).select_related("user", "plan")
    return render(request, "core/management_investments.html", {"pending": pending})


@staff_member_required
def user_management_withdrawals_view(request):
    if request.method == "POST":
        withdrawal = get_object_or_404(Withdrawal, pk=request.POST.get("withdrawal_id"))
        action = request.POST.get("action")
        if action == "approve":
            wallet_services.approve_withdrawal(withdrawal, request.user)
            messages.success(request, f"Approved withdrawal #{withdrawal.pk}.")
        elif action == "reject":
            wallet_services.reject_withdrawal(
                withdrawal, request.user, reason=request.POST.get("reason", "")
            )
            messages.success(request, f"Rejected withdrawal #{withdrawal.pk}.")
        return redirect("core:management_withdrawals")

    pending = Withdrawal.objects.filter(status=Withdrawal.STATUS_PENDING).select_related("user")
    return render(request, "core/management_withdrawals.html", {"pending": pending})
