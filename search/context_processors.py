# project
from kl import settings

#from MobileUserAgent import parseUserAgent

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

    return data
