"""
Overriding django.middleware.locale.LocaleMiddleware because we want to make the
domain more important than anything else.
"""

from django.utils.cache import patch_vary_headers
from django.utils import translation
from django.middleware.locale import LocaleMiddleware
from django.contrib.sites.models import RequestSite
from django.conf import settings

class LocaleMiddleware(LocaleMiddleware):
    """
    This is a very simple middleware that parses a request
    and decides what translation object to install in the current
    thread context. This allows pages to be dynamically
    translated to the language the user desires (if the language
    is available, of course).
    """

    def process_request(self, request):
        # assume we can't figure out the language by domain
        language = None
        domain = RequestSite(request).domain
        if domain in settings.LANGUAGE_DOMAINS.values():
            language = [k for (k,v) in settings.LANGUAGE_DOMAINS.items() if v==domain][0]
        if not language:
            if settings.LANGUAGE_DOMAINS:
                # we don't want them to set the language willy nilly 
                # if domains are defined
                language = settings.DEFAULT_LANGUAGE
            else:
                # e.g. localhost:8000
                language = translation.get_language_from_request(request)
            
        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()

