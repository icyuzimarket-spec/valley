from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import InvestmentProofForm
from .models import Investment, Plan


@login_required
def plan_list_view(request):
    plans = Plan.objects.filter(is_active=True)
    has_pending = Investment.objects.filter(
        user=request.user, status=Investment.STATUS_PENDING
    ).exists()
    return render(
        request,
        "investments/plan_list.html",
        {"plans": plans, "has_pending": has_pending},
    )


@login_required
def invest_view(request, plan_id):
    plan = get_object_or_404(Plan, pk=plan_id, is_active=True)

    if Investment.objects.filter(user=request.user, status=Investment.STATUS_PENDING).exists():
        messages.warning(
            request, "You already have a pending investment awaiting approval. Please wait for it to be reviewed."
        )
        return redirect("investments:plan_list")

    if request.method == "POST":
        form = InvestmentProofForm(request.POST, request.FILES)
        if form.is_valid():
            investment = form.save(commit=False)
            investment.user = request.user
            investment.plan = plan
            investment.amount = plan.price
            investment.daily_income = plan.daily_income
            investment.duration_days = plan.duration_days
            investment.status = Investment.STATUS_PENDING
            investment.save()
            messages.success(
                request,
                "Your payment proof was submitted. An admin will review and approve it shortly.",
            )
            return redirect("core:dashboard_redirect")
    else:
        form = InvestmentProofForm()

    return render(request, "investments/invest.html", {"plan": plan, "form": form})
