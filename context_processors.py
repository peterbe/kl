import os
import random
import datetime
from urllib import quote
import time

# django
from django.conf import settings

# project

from search.MobileUserAgent import parseUserAgent
from search.views import get_search_stats, get_saved_cookies, get_language_options
from search.views import get_canonical_url
from search.data import get_amazon_advert
from search.googlecharts import get_sparklines_cached
from search.forms import QUIZZES

def context(request):

    data = {'TEMPLATE_DEBUG': settings.TEMPLATE_DEBUG,
            'DEBUG': settings.DEBUG,
            'HOME': settings.HOME,
            #'OFFLINE': settings.OFFLINE,
            'base_template': "base.html",
            'mobile_version': False,
            'mobile_user_agent': False,
            'GOOGLE_ANALYTICS': settings.GOOGLE_ANALYTICS,
            'GIT_REVISION_DATE': settings.GIT_REVISION_DATE,
            }

    data['quiz_question'] = random.choice(QUIZZES.keys())

    #if settings.DEBUG:
    #    data['ADMIN_MEDIA_PREFIX'] = '/'
    #else:
    #    data['ADMIN_MEDIA_PREFIX'] = settings.ADMIN_MEDIA_PREFIX

    #http_user_agent = request.META.get('HTTP_USER_AGENT', None)

    #request.mobile_version = False
    #request.iphone_version = False


    if request.iphone:
        data['iphone_version'] = True
    if request.mobile:
        data['mobile_user_agent'] = True
        data['base_template'] = "mobile_base.html"
        data['mobile_version'] = True

    language = request.LANGUAGE_CODE
    data.update(get_search_stats(language))

    data.update(get_saved_cookies(request))

    data.update(dict(language_options=get_language_options(request)))

    data['render_form_ts'] = int(time.time())

    # for the link the Searches summary of the latest month
    data['searches_summary_link'] = datetime.datetime.today().strftime('/searches/%Y/%B/')

    if settings.DO_THIS_MONTH_SPARKLINES and not settings.DEBUG:
        sparklines_url = get_sparklines_cached(150, 100, only_if_cached=True)
        if sparklines_url:
            data['sparklines_url'] = sparklines_url

            today = datetime.datetime.today()
            first_date = datetime.datetime(today.year, today.month, 1)
            data['sparklines_href'] = '/statistics/graph/?daterange='+\
                                    quote(first_date.strftime('%Y/%m/%d')) +\
                                    quote(' - ') +\
                                    quote(today.strftime('%Y/%m/%d'))

        else:
            data['sparklines_script'] = '<script type="text/javascript">'\
             'var SPARKLINES=true;</script>'

    current_url = request.build_absolute_uri()

    canonical_url = get_canonical_url(current_url)
    if canonical_url:
        data['canonical_url'] = canonical_url

    if request.META.get('GEO'):
        data['geo'] = request.META.get('GEO')

        if not settings.DEBUG:
            if request.session.get('has_searched'):
                data['amazon_advert'] = get_amazon_advert(data['geo'])


    data['use_google_analytics'] = data.get('use_google_analytics',
                                            not settings.DEBUG)

    data['show_crossing_the_world_link'] = '/crossing-the-world' not in current_url

    data['this_django_instance'] = os.path.basename(os.path.dirname(__file__))

    data['show_publishermedia_ad'] = request.get_host() == 'crosstips.org'
    logging.info(request.get_host())

    return data
