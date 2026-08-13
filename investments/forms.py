from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

from .models import Investment

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


class InvestmentProofForm(forms.ModelForm):
    class Meta:
        model = Investment
        fields = ["payment_screenshot"]
        widgets = {
            "payment_screenshot": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def clean_payment_screenshot(self):
        image = self.cleaned_data["payment_screenshot"]
        max_bytes = settings.MAX_SCREENSHOT_SIZE_MB * 1024 * 1024
        if image.size > max_bytes:
            raise ValidationError(f"Screenshot must be smaller than {settings.MAX_SCREENSHOT_SIZE_MB}MB.")

        content_type = getattr(image, "content_type", None)
        if content_type and content_type not in ALLOWED_CONTENT_TYPES:
            raise ValidationError("Only JPG, PNG, or WEBP screenshots are allowed.")

        try:
            image.seek(0)
            Image.open(image).verify()
        except UnidentifiedImageError:
            raise ValidationError("This file does not look like a valid image.")
        finally:
            image.seek(0)

        return image
