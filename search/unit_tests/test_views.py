# python
import datetime

# django
from django.test.client import Client
from django.test import TestCase

# project
import search.views

class ViewTestCase(TestCase):
    """
    Testing views
    """
    
    def test_solve_errors(self):
        """ test sending rubbish to solve() """
        client = Client()
        response = client.get('/los/?l=x')
        # redirects means it's unhappy
        assert response.status_code == 302, response.status_code
        
        response = client.get('/los/?l=3&s=a')
        assert response.status_code == 302, response.status_code
        
        response = client.get('/los/?l=2&s=a&s=b&s=c')
        assert response.status_code == 302, response.status_code
        
        

        
        




        