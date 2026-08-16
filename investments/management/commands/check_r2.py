"""Verify that payment screenshots can actually reach Cloudflare R2.

Upload failures surface to users as "We could not save your payment
screenshot", which says nothing about the cause. This command performs the
same round trip an investment does — write, read back, delete — and prints
whatever the storage backend raises, so a misconfigured bucket can be
diagnosed on the host that is failing.
"""

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Check that the configured media storage can store and serve payment screenshots."

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep",
            action="store_true",
            help="Leave the probe object in the bucket instead of deleting it.",
        )

    def handle(self, *args, **options):
        backend = settings.STORAGES["default"]["BACKEND"]
        self.stdout.write(f"Default file storage: {backend}")

        if not settings.USE_R2:
            raise CommandError(
                "R2 is not configured, so uploads go to the local disk at "
                f"{settings.MEDIA_ROOT}. On a host with an ephemeral disk they "
                "are lost on every redeploy. Set R2_BUCKET_NAME, "
                "R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY and R2_ACCOUNT_ID "
                "(or R2_ENDPOINT)."
            )

        self.stdout.write(f"Bucket: {settings.R2_BUCKET_NAME}")
        self.stdout.write(f"Endpoint: {settings.R2_ENDPOINT}")
        self.stdout.write(f"Region: {settings.R2_REGION}")

        # The same prefix real proofs use, so a bucket-scoped token that only
        # grants payment_proofs/ is exercised the way the app exercises it.
        payload = b"valley-r2-connectivity-probe"
        name = None
        try:
            name = default_storage.save(
                "payment_proofs/.r2-check", ContentFile(payload)
            )
            self.stdout.write(self.style.SUCCESS(f"Upload OK -> {name}"))

            with default_storage.open(name) as handle:
                read_back = handle.read()
            if read_back != payload:
                raise CommandError(
                    "Upload succeeded but the object read back with different "
                    f"content ({len(read_back)} bytes, expected {len(payload)}). "
                    "That points at the chunked-checksum upload path R2 does "
                    "not support."
                )
            self.stdout.write(self.style.SUCCESS("Download OK, content matches"))

            self.stdout.write(f"Signed URL: {default_storage.url(name)}")
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError(
                f"R2 round trip failed: {type(exc).__name__}: {exc}"
            ) from exc
        finally:
            if name and not options["keep"]:
                try:
                    default_storage.delete(name)
                except Exception as exc:  # pragma: no cover - cleanup only
                    self.stderr.write(f"Could not delete probe object {name}: {exc}")

        self.stdout.write(self.style.SUCCESS("R2 is working."))
