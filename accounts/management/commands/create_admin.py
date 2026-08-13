from django.core.management.base import BaseCommand, CommandError

from accounts.models import User, normalize_phone_number
from core.models import SiteSettings


class Command(BaseCommand):
    help = "Create a staff+superuser admin account and set it as the default referral fallback."

    def add_arguments(self, parser):
        parser.add_argument("phone_number", type=str)
        parser.add_argument("password", type=str)
        parser.add_argument("--full-name", type=str, default="Admin")

    def handle(self, *args, **options):
        try:
            phone_number = normalize_phone_number(options["phone_number"])
        except Exception as exc:
            raise CommandError(str(exc))

        if User.objects.filter(phone_number=phone_number).exists():
            raise CommandError(f"A user with phone number {phone_number} already exists.")

        admin = User.objects.create_superuser(
            phone_number=phone_number,
            password=options["password"],
            full_name=options["full_name"],
        )

        site_settings = SiteSettings.load()
        if not site_settings.fallback_referrer:
            site_settings.fallback_referrer = admin
            site_settings.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Created admin {admin.phone_number} and set as default referral fallback."
            )
        )
