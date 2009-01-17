from django import forms


class DSSOUploadForm(forms.Form):
    
    file = forms.FileField()
    
    
class FeedbackForm(forms.Form):
    text = forms.CharField()
    name = forms.CharField(max_length=100, required=False)
    email = forms.CharField(max_length=100, required=False)
    url = forms.CharField(max_length=1, required=False)
    
    def clean(self):
        cleaned_data = self.cleaned_data
        if cleaned_data.get('url'):
            raise forms.ValidationError("Not empty :(")
        return cleaned_data
    
    
    def clean_body(self):
        if 'text' in self.cleaned_data and getattr(settings, 'AKISMET_API_KEY', ''):
            from akismet import Akismet
            from django.utils.encoding import smart_str
            akismet_api = Akismet(key=settings.AKISMET_API_KEY,
                                  blog_url='http://%s/' % Site.objects.get_current().domain)
            if akismet_api.verify_key():
                akismet_data = { 'comment_type': 'comment',
                                 'referer': self.request.META.get('HTTP_REFERER', ''),
                                 'user_ip': self.request.META.get('REMOTE_ADDR', ''),
                                 'user_agent': self.request.META.get('HTTP_USER_AGENT', '') }
                if akismet_api.comment_check(smart_str(self.cleaned_data['body']), data=akismet_data, build_data=True):
                    raise forms.ValidationError(u"Akismet thinks this message is spam")
        return self.cleaned_data['body']
    
