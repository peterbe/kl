import random
import datetime
from urllib import quote
import time

# django

# project
from kl import settings

from MobileUserAgent import parseUserAgent
from views import get_search_stats, get_saved_cookies, get_language_options
from views import get_canonical_url
from data import get_amazon_advert
from googlecharts import get_sparklines
from forms import QUIZZES

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
    
    data['quiz_question'] = random.choice(QUIZZES.keys())
    
    #if settings.DEBUG:
    #    data['ADMIN_MEDIA_PREFIX'] = '/'
    #else:
    #    data['ADMIN_MEDIA_PREFIX'] = settings.ADMIN_MEDIA_PREFIX
         
    http_user_agent = request.META.get('HTTP_USER_AGENT', None)
    
    if request.GET.get('MOBILE_TEMPLATE') or \
      http_user_agent and \
      parseUserAgent(request.META.get('HTTP_USER_AGENT')):
        data['mobile_user_agent'] = True
        data['base_template'] = "mobile_base.html"
        data['mobile_version'] = True
    elif http_user_agent and http_user_agent.count('iPhone') and \
      http_user_agent.count('AppleWebKit'): # XXX needs work (e.g. iPhoney fails)
        data['iphone_version'] = True

    language = request.LANGUAGE_CODE
    data.update(get_search_stats(language))
    
    data.update(get_saved_cookies(request))
    
    data.update(dict(language_options=get_language_options(request)))
    
    data['render_form_ts'] = int(time.time())
    
    # for the link the Searches summary of the latest month
    data['searches_summary_link'] = datetime.datetime.today().strftime('/searches/%Y/%B/')
    
    if settings.DO_THIS_MONTH_SPARKLINES:
        data['sparklines_url'] = get_sparklines(150, 100)
        today = datetime.datetime.today()
        first_date = datetime.datetime(today.year, today.month, 1)
        data['sparklines_href'] = '/statistics/graph/?daterange='+\
                                quote(first_date.strftime('%Y/%m/%d')) +\
                                quote(' - ') +\
                                quote(today.strftime('%Y/%m/%d'))
        
    
    current_url = request.build_absolute_uri()
    
    canonical_url = get_canonical_url(current_url)
    if canonical_url:
        data['canonical_url'] = canonical_url
    
    if request.META.get('GEO'):
        data['geo'] = request.META.get('GEO')
        
        if 1 or not settings.DEBUG:
            if request.session.get('has_searched'):
                data['amazon_advert'] = get_amazon_advert(data['geo'])
    
        
    data['use_google_analytics'] = data.get('use_google_analytics', 
                                            not settings.DEBUG)

    data['show_crossing_the_world_link'] = '/crossing-the-world' not in current_url
    
    return data
