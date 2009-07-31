# python
import os
from time import time
import datetime
from collections import defaultdict
from pygooglechart import SimpleLineChart
from pygooglechart import SparkLineChart
from pygooglechart import PieChart2D
#from pygooglechart import PieChart3D
from pygooglechart import GroupedVerticalBarChart
import pygooglechart

# django
from django.utils.translation import ugettext as _
from django.core.cache import cache
from django.conf import settings

# app
from models import Search
from utils import print_sql, ONE_HOUR

def get_sparklines_cached(width, height, background_color='efefef'):
    cache_key = 'sparklines_%s_%s_%s' % (width, height, background_color)
    result = cache.get(cache_key)
    if result is None:
        result = get_sparklines(width, height, background_color=background_color)
        cache.set(cache_key, result, ONE_HOUR)
    return result

def get_sparklines(width, height, background_color='efefef'):
    """wrap _get_sparklines() but first work out the data"""
    data = defaultdict(int)
                  
    print "GENERATE SPARKLINES!"
    
    today = datetime.datetime.today()
    today_date = datetime.datetime(today.year, today.month, today.day)
    first_date = datetime.datetime(today.year, today.month, 1)
    searches = Search.objects
    searches = searches.filter(add_date__gte=first_date,
                               add_date__lt=today_date)
    for search in searches:
        data[search.add_date.day] += 1
    
    data = [(k,v) for (k,v) in data.items()]
    data.sort()
    data = [x[1] for x in data]
    
    return _get_sparklines(width, height, data,
                           background_color=background_color)
    
def _get_sparklines_save_filepath(filename):
    """ filename should be something like 'sparklines.png'
    and then we return 
    /path/to/mediaroot/sparklines/sparklines.123456789.png
    """
    dir_ = os.path.join(settings.MEDIA_ROOT, 'sparklines')
    if not os.path.isdir(dir_):
        os.mkdir(dir_)
    
    filename = list(os.path.splitext(filename))
    filename.insert(-1, '.%s' % int(time()))
    filename = ''.join(filename)
    return os.path.join(dir_, filename)
    
def _get_sparklines(width, height, data, background_color=None):
    chart = SparkLineChart(width, height)
    chart.add_data(data)
    if background_color:
        chart.fill_solid(chart.BACKGROUND, background_color)
    chart.set_colours(['777777'])
    fileurl = _get_sparklines_save_filepath('sparklines.png')
    chart.download(fileurl)
    return fileurl.replace(settings.MEDIA_ROOT, '')
    #return chart.get_url()


def get_search_types_pie(queryset, search_types, width, height, background_color='ffffff'):
    """wrap _get_search_types_pie() but first work out the data"""
    
    data = defaultdict(int)
    for search_type in search_types:
        caption = search_type
        if not caption:
            caption = _(u"standard")
        data[caption] = queryset.filter(search_type=search_type).count()
        
    total_count = sum(data.values())
    ndata = {}
    for k, v in data.items():
        p = 100 * float(v)/total_count
        ndata['%s (%.1f%%)' % (k, p)] = v
        
    return _get_pie_chart(width, height, ndata, background_color=background_color)

    
    
def get_languages_pie(queryset, languages, width, height, background_color='ffffff'):
    """wrap _get_search_types_pie() but first work out the data"""
    
    from templatetags.language import show_language_verbose
    data = defaultdict(int)
    for language in languages:
        caption = show_language_verbose(language).encode('utf8')
        data[caption] = queryset.filter(language=language).count()
        
    total_count = sum(data.values())
    ndata = {}
    for k, v in data.items():
        p = 100 * float(v)/total_count
        ndata['%s (%.1f%%)' % (k, p)] = v
        
    return _get_pie_chart(width, height, ndata, background_color=background_color)

        
def _get_pie_chart(width, height, data, background_color=None, colour=None):
    chart = PieChart2D(width, height)
    data = [(v, k) for (k, v) in data.items()]
    data.sort()
    data.reverse()
    
    chart.add_data([x[0] for x in data])
    chart.set_pie_labels([x[1] for x in data])
    
    if background_color:
        chart.fill_solid(chart.BACKGROUND, background_color)
    if colour:
        chart.set_colours([colour])
    return chart.get_url()
    

def get_lengths_bar(queryset, lengths, width, height, background_color=None, colour=None):
    data = defaultdict(int)
    for length in lengths:
        caption = str(length)
        data[caption] = queryset.extra(where=['length(search_word)=%d' % length]).count()
        
    return _get_bar_chart(width, height, data, background_color=background_color,
                         colour=colour)
    
def _get_bar_chart(width, height, data, background_color=None, colour=None):
    data = sorted([(int(k), v) for (k,v) in data.items()])
    
    min_ = min([x[1] for x in data])
    max_ = max([x[1] for x in data])
    
    chart = GroupedVerticalBarChart(width, height, 
                                    y_range=(min_, max_+30)) # add 30px for some extra space
    chart.add_data([x[1] for x in data])
    #print dir(chart)
    chart.set_axis_labels(pygooglechart.Axis.BOTTOM, [x[0] for x in data])
    interval = (max_ - min_) / 10
    if interval > 100:
        interval = 500
    elif interval > 50:
        interval = 100
    else:
        interval = 50
    max_range = interval * (max_ / interval +1)
    chart.set_axis_labels(pygooglechart.Axis.LEFT, 
                          [str(x) for x in range(0, max_range, interval)])
    
    if background_color:
        chart.fill_solid(chart.BACKGROUND, background_color)
    if colour:
        chart.set_colours([colour])
    return chart.get_url()
    