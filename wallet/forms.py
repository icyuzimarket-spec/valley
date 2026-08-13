from decimal import Decimal

from django import forms


class WithdrawalRequestForm(forms.Form):
    amount = forms.DecimalField(
        label="Amount (RWF)", max_digits=12, decimal_places=2, min_value=Decimal("1")
    )
