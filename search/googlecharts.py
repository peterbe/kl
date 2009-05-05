# python
import datetime
from collections import defaultdict
from pygooglechart import SimpleLineChart
from pygooglechart import SparkLineChart

# app
from models import Search
from utils import print_sql

def get_sparklines(width, height, background_color='efefef'):
    """wrap _get_sparklines() but first work out the data"""
    data = defaultdict(int)
    
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
    
    
def _get_sparklines(width, height, data, background_color=None):
    chart = SparkLineChart(width, height)
    chart.add_data(data)
    if background_color:
        chart.fill_solid(chart.BACKGROUND, background_color)
    chart.set_colours(['777777'])
    return chart.get_url()