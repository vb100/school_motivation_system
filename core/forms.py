from django import forms


class AwardForm(forms.Form):
    points = forms.IntegerField(
        min_value=1,
        label="Taškai",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    message = forms.CharField(
        label="Sveikinimo žinutė",
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
    )
