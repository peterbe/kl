DIRECTORIES = (
   ('search/unit_tests/test_views.py',
    './manage.py test --settings=test_settings search.ViewTestCase.test__find_alternatives'),
    
   ('search/unit_tests', 
    './manage.py test --settings=test_settings search'),
               
   ('search', 
    './manage.py test --settings=test_settings search.ViewTestCase.test__find_alternatives'),
)

