import os
import time
import re
from glob import glob
from unittest import TestCase

from search.templatetags.django_slimmer import _slimfile
import settings 
TEST_JS_FILENAME = '/test__djang_slimmer.js'
TEST_CSS_FILENAME = '/test__djang_slimmer.css'

TEST_MEDIA_ROOT = '/tmp/fake_media_root'
_original_MEDIA_ROOT = settings.MEDIA_ROOT
_original_DEBUG = settings.DEBUG

class Test__django_slimmer(TestCase):
    
    def setUp(self):
        if not os.path.isdir(TEST_MEDIA_ROOT):
            os.mkdir(TEST_MEDIA_ROOT)
        open(TEST_MEDIA_ROOT + TEST_JS_FILENAME, 'w')\
          .write('var a  =  test\n')
        open(TEST_MEDIA_ROOT + TEST_CSS_FILENAME, 'w')\
          .write('body { color: #CCCCCC; }\n')
        super(Test__django_slimmer, self).setUp()
        
    def tearDown(self):
        os.remove(TEST_MEDIA_ROOT + TEST_JS_FILENAME)
        os.remove(TEST_MEDIA_ROOT + TEST_CSS_FILENAME)
        
        # also remove any of the correctly generated ones
        for filepath in glob(TEST_MEDIA_ROOT + '/*'):
            os.remove(filepath)
        os.rmdir(TEST_MEDIA_ROOT)

        # restore things for other potential tests
        settings.MEDIA_ROOT = _original_MEDIA_ROOT
        settings.DEBUG = _original_DEBUG
        
        super(Test__django_slimmer, self).tearDown()
    
    def test__slimfile__debug_on_save_prefixed(self):
        """ test the private method _slimfile().
        We're going to assume that the file exists
        """
        TEST_SAVE_PREFIX = '/tmp/infinity'
        
        settings.DJANGO_SLIMMER = True
        settings.DJANGO_SLIMMER_SAVE_PREFIX = TEST_SAVE_PREFIX
        settings.DJANGO_SLIMMER_NAME_PREFIX = ''
        settings.MEDIA_ROOT = TEST_MEDIA_ROOT
        
        result_filename = _slimfile(TEST_JS_FILENAME)
        assert result_filename != TEST_JS_FILENAME, "It hasn't changed"
        
        # the file should be called /test__django_slimmer.12345678.js
        timestamp = int(re.findall('\.(\d+)\.', result_filename)[0])
        now = int(time.time())
        # before we do the comparison, trim the last digit to prevent
        # bad luck on the millisecond and the rounding that int() does
        assert int(timestamp*.1) == int(now*.1)
        
        # if you remove that timestamp you should get the original 
        # file again
        print "RESULT_FILENAME", result_filename
        assert TEST_JS_FILENAME == \
          result_filename.replace(str(timestamp)+'.', '')\
          .replace('/cache-forever', '')
        
        # The file will be stored in a different place than the 
        # TEST_MEDIA_ROOT
        # and the content should be slimmed
        content = open(TEST_SAVE_PREFIX + result_filename).read()
        assert content == 'var a=test', content
        
        # run it again to test that the _slimfile() function can use
        # it's internal global variable map to get the file out
        assert result_filename == _slimfile(TEST_JS_FILENAME)
        
        # if in debug mode, if the file changes and you call
        # _slimfile() it should return a new file and delete the
        # old one
        time.sleep(1) # slow but necessary
        # now change the original file
        open(TEST_MEDIA_ROOT + TEST_JS_FILENAME, 'w').write('var b  =  foo\n')
        
        first_result_filename = result_filename
        result_filename = _slimfile(TEST_JS_FILENAME)
        assert first_result_filename != result_filename, result_filename
        content = open(TEST_SAVE_PREFIX + result_filename).read()
        assert content == 'var b=foo', content
        
        # the previous file should have been deleted
        assert not os.path.isfile(TEST_SAVE_PREFIX + first_result_filename)
        
    def test__slimfile__debug_on_save_prefixed_name_prefixed(self):
        """ 
        If you use a name prefix it might have nothing to do with what the file
        is called or where it's found or where it's saved. By setting a name
        prefix you get something nice in your rendered HTML that you can use to
        split your rewrite rules in apache/nginx so that you can set different
        cache headers. 
        """
        TEST_SAVE_PREFIX = '/tmp/infinity'
        TEST_NAME_PREFIX = '/cache-forever'
        print "**"
        print settings.MEDIA_URL
        
        settings.DJANGO_SLIMMER = True
        settings.DJANGO_SLIMMER_SAVE_PREFIX = TEST_SAVE_PREFIX
        settings.DJANGO_SLIMMER_NAME_PREFIX = TEST_NAME_PREFIX
        settings.MEDIA_ROOT = TEST_MEDIA_ROOT
        
        result_filename = _slimfile(TEST_JS_FILENAME)
        assert result_filename != TEST_JS_FILENAME, "It hasn't changed"
        
        # the file should be called /test__django_slimmer.12345678.js
        timestamp = int(re.findall('\.(\d+)\.', result_filename)[0])
        now = int(time.time())
        # before we do the comparison, trim the last digit to prevent
        # bad luck on the millisecond and the rounding that int() does
        assert int(timestamp*.1) == int(now*.1)
        
        # if you remove that timestamp you should get the original 
        # file again
        assert TEST_JS_FILENAME == \
          result_filename.replace(str(timestamp)+'.', '')\
          .replace(TEST_NAME_PREFIX, '')
        
        # The file will be stored in a different place than the 
        # TEST_MEDIA_ROOT
        # and the content should be slimmed
        actual_saved_filepath = TEST_SAVE_PREFIX + \
          result_filename.replace(TEST_NAME_PREFIX, '')
        content = open(actual_saved_filepath).read()
        assert content == 'var a=test', content
        
        # run it again to test that the _slimfile() function can use
        # it's internal global variable map to get the file out
        assert result_filename == _slimfile(TEST_JS_FILENAME)
        
        # if in debug mode, if the file changes and you call
        # _slimfile() it should return a new file and delete the
        # old one
        time.sleep(1) # slow but necessary
        # now change the original file
        open(TEST_MEDIA_ROOT + TEST_JS_FILENAME, 'w').write('var b  =  foo\n')
        
        first_result_filename = result_filename
        result_filename = _slimfile(TEST_JS_FILENAME)
        assert first_result_filename != result_filename, result_filename
        content = open(TEST_SAVE_PREFIX + \
                       result_filename.replace(TEST_NAME_PREFIX, '')).read()
        assert content == 'var b=foo', content
        
        # the previous file should have been deleted
        assert not os.path.isfile(TEST_MEDIA_ROOT + \
          first_result_filename.replace(TEST_NAME_PREFIX, ''))
        

    def test__slimfile__debug_off(self):
        """ same test as test__slimfile__debug_on() but this time not
        in DEBUG mode. Then slimit will not notice that the file changes
        because it's more optimized. 
        """
        settings.DJANGO_SLIMMER = True
        settings.DJANGO_SLIMMER_SAVE_PREFIX = '/tmp/infinity'
        settings.DJANGO_SLIMMER_NAME_PREFIX = '/cache-forever'
        settings.MEDIA_ROOT = TEST_MEDIA_ROOT
        settings.DEBUG = False
        
        result_filename = _slimfile(TEST_CSS_FILENAME)
        # the file should be called /test__django_slimmer.12345678.css
        timestamp = int(re.findall('\.(\d+)\.', result_filename)[0])
        now = int(time.time())
        # before we do the comparison, trim the last digit to prevent
        # bad luck on the millisecond and the rounding that int() does
        assert int(timestamp*.1) == int(now*.1)
        
        # if you remove that timestamp you should get the original 
        # file again
        assert TEST_CSS_FILENAME == \
          result_filename.replace(str(timestamp)+'.', '')
        
        # and the content should be slimmed
        content = open(TEST_MEDIA_ROOT + result_filename).read()
        assert content == 'body{color:#CCC}', content
            
        time.sleep(1) # slow but necessary
        # now change the original file
        open(TEST_MEDIA_ROOT + TEST_CSS_FILENAME, 'w')\
          .write('body { color:#FFFFFF}\n')
        
        result_filename = _slimfile(TEST_CSS_FILENAME)
        new_content = open(TEST_MEDIA_ROOT + result_filename).read()
        assert new_content == content, new_content
            
        
        