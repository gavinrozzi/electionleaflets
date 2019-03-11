from django import forms
from django.utils.translation import ugettext as _

from core.helpers import geocode

from localflavor.us.forms import USZipCodeField


class ConstituencyLookupForm(forms.Form):
    postcode = USZipCodeField(label="Search by ZIP Code",
                               error_messages={'invalid': 'Please enter a full US ZIP code'})
    location = None

    def clean(self):
        cleaned_data = super(ConstituencyLookupForm, self).clean()
        pcode = cleaned_data.get("postcode")
        self.location = geocode(pcode)
        if not self.location:
            raise forms.ValidationError(_("That ZIP Code was not found. Please try another"))
