from django.conf import settings
from view_cache_utils import cache_page_with_prefix, expire_page

def expire_page_all(path):
    # Because it's not good enough to call expire_page(path, request) as it 
    # might only expire the cache for one particular key_prefix before going
    # in to kill the cache. Here we call expire_page() for all possible
    # key prefixes
    for key_prefix in ('', 'mobile'):
        expire_page(path, key_prefix)


    
def loggedin_aware_key_prefix(request):
    if not settings.USE_CACHE_PAGE:
        return None
    
    if request.user and request.user.is_authenticated():
        return None # we might want to be more aggressive later
    
    if request.POST:
        return None
    
    return ""
    
    


def mobile_aware_key_prefix(request):
    if not settings.USE_CACHE_PAGE:
        
        return None
    
    if request.user and request.user.is_authenticated():
        return None # we might want to be more aggressive later
    
    if request.POST:
        return None
    
    prefix = ""
    
    if request.GET:
        for key in ('languages','month','year','page','daterange'):
            if key in request.GET:
                prefix += '%s-%s' % (key, request.GET[key])
     
    if request.mobile or 'SIMULATE_MOBILE' in request.GET:
        prefix += "mobile"
        
    if request.iphone or 'SIMULATE_IPHONE' in request.GET:
        prefix += "iphone"
        
    return prefix