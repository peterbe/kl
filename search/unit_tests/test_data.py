# python
import datetime

# django
from django.test import TestCase

# project
from search import data

class DataTestCase(TestCase):
    
    def test_ip_to_coordinates(self):
        """ test ip_to_coordinates() """
        ip = '24.76.224.175'
        info = data.ip_to_coordinates(ip)
        self.assertTrue('country_name' in info)
        self.assertTrue('place_name' in info)
        self.assertTrue('country_code' in info)
        self.assertTrue('coordinates' in info)
        
        # to test the caching function, the second look up should be
        # very fast
        from time import time
        ip = '24.76.224.176'
        t0=time()
        data.ip_to_coordinates(ip)
        t1=time()
        data.ip_to_coordinates(ip)
        t2=time()
        time1 = t1-t0
        time2 = t2-t1
        self.assertTrue(time2 * 100 < time1)
        
