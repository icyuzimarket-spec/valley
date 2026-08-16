import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .forms import InvestmentProofForm
from .models import Investment, Plan

logger = logging.getLogger(__name__)


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
            try:
                # The screenshot is uploaded by FileField.pre_save while the
                # INSERT is being built, so a storage failure aborts mid
                # statement and leaves the transaction unusable. The savepoint
                # rolls that back so this request can still render a page.
                with transaction.atomic():
                    investment.save()
            except Exception:
                # Object storage can fail independently of the database. An
                # investment row with no reviewable proof is worse than no row
                # at all, so keep the user on the form to retry.
                logger.exception(
                    "Failed to store payment screenshot for user %s on plan %s",
                    request.user.pk,
                    plan.pk,
                )
                messages.error(
                    request,
                    "We could not save your payment screenshot just now. "
                    "Please try again in a moment.",
                )
            else:
                messages.success(
                    request,
                    "Your payment proof was submitted. An admin will review and approve it shortly.",
                )
                return redirect("core:dashboard_redirect")
    else:
        form = InvestmentProofForm()

    return render(request, "investments/invest.html", {"plan": plan, "form": form})
