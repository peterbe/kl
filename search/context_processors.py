# project
from kl import settings

#from MobileUserAgent import parseUserAgent
from views import get_search_stats, get_saved_cookies

def context(request):
            
    data = {'TEMPLATE_DEBUG': settings.TEMPLATE_DEBUG,
            'DEBUG': settings.DEBUG,
            #'OFFLINE': settings.OFFLINE,
            'base_template': "base.html",
            'mobile_version': False,
            'mobile_user_agent': False,
            }
    
    #if settings.DEBUG:
    #    data['ADMIN_MEDIA_PREFIX'] = '/'
    #else:
    #    data['ADMIN_MEDIA_PREFIX'] = settings.ADMIN_MEDIA_PREFIX
            
    #if request.GET.get('MOBILE_TEMPLATE') or \
    #  request.META.get('HTTP_USER_AGENT', None) and \
    #  parseUserAgent(request.META.get('HTTP_USER_AGENT')):
    #    data['mobile_user_agent'] = True
    #    data['base_template'] = "mobile_base.html"
    #    data['mobile_version'] = True

    data.update(get_search_stats())
    
    data.update(get_saved_cookies(request))

    return data
