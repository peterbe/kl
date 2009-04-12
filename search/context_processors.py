import time
# project
from kl import settings

from MobileUserAgent import parseUserAgent
from views import get_search_stats, get_saved_cookies, get_language_options
from data import get_amazon_advert

def context(request):
            
    data = {'TEMPLATE_DEBUG': settings.TEMPLATE_DEBUG,
            'DEBUG': settings.DEBUG,
            'HOME': settings.HOME,
            #'OFFLINE': settings.OFFLINE,
            'base_template': "base.html",
            'mobile_version': False,
            'mobile_user_agent': False,
            'GOOGLE_ANALYTICS': settings.GOOGLE_ANALYTICS,
            }
    
    #if settings.DEBUG:
    #    data['ADMIN_MEDIA_PREFIX'] = '/'
    #else:
    #    data['ADMIN_MEDIA_PREFIX'] = settings.ADMIN_MEDIA_PREFIX
            
    if request.GET.get('MOBILE_TEMPLATE') or \
      request.META.get('HTTP_USER_AGENT', None) and \
      parseUserAgent(request.META.get('HTTP_USER_AGENT')):
        data['mobile_user_agent'] = True
        data['base_template'] = "mobile_base.html"
        data['mobile_version'] = True

    language = request.LANGUAGE_CODE
    data.update(get_search_stats(language))
    
    data.update(get_saved_cookies(request))
    
    data.update(dict(language_options=get_language_options(request)))
    
    data['render_form_ts'] = int(time.time())
    
    
    if request.META.get('GEO'):
        data['geo'] = request.META.get('GEO')
        
        if 1 or not settings.DEBUG:
            if request.session.get('has_searched'):
                data['amazon_advert'] = get_amazon_advert(data['geo'])
    
        
    data['use_google_analytics'] = True

    return data
