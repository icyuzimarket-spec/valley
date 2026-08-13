from django.core.management.base import BaseCommand

from investments import services
from investments.models import Investment


class Command(BaseCommand):
    help = (
        "Credits any daily income owed to all approved, in-progress investments. "
        "Idempotent - safe to run any number of times per day. Dashboard access "
        "already self-heals this, so this command is only needed for exact daily "
        "timing (e.g. wired to Windows Task Scheduler)."
    )

    def handle(self, *args, **options):
        investments = Investment.objects.filter(
            status=Investment.STATUS_APPROVED, is_completed=False
        )
        credited, failed = 0, 0
        for inv in investments:
            try:
                services.credit_due_earnings(inv)
                credited += 1
            except Exception as exc:
                failed += 1
                self.stderr.write(self.style.ERROR(f"Investment #{inv.pk} failed: {exc}"))

        self.stdout.write(
            self.style.SUCCESS(f"Processed {credited} investment(s), {failed} failure(s).")
        )
