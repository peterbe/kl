from django import forms


class DSSOUploadForm(forms.Form):
    
    file = forms.FileField()
    