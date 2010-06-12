# Django settings for kl project.
import os
DEBUG = False
TEMPLATE_DEBUG = DEBUG

HOME = os.path.normpath(os.path.dirname(__file__))


#TEST_RUNNER = 'kl.testrunner.run_tests'

ADMINS = (
     ('Peter', 'peter@fry-it.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'postgresql_psycopg2'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'kl'             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/London'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-gb'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = HOME + '/media'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/admin/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = open(os.path.join(HOME, '.secret')).read()

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)



MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'djangodblog.DBLogMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    #'django.middleware.locale.LocaleMiddleware',
    'middleware.locale.LocaleMiddleware',
    'minidetector.Middleware',
    'middleware.MobileSecondMiddleware',
                      
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    HOME + '/templates',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'search',
    'djangodblog',
    'django.contrib.flatpages',
    'django.contrib.sitemaps',
    'rosetta',
    'django_static',
                  
)


TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'context_processors.context',
)

CACHE_BACKEND = 'memcached://127.0.0.1:11211/'

ugettext = lambda s: s

LANGUAGES = (
  ('sv', ugettext("Swedish")),
  ('fr', ugettext("French")),
  ('en-GB', ugettext("British English")),
  ('en-US', ugettext("American English")),

)

DEFAULT_LANGUAGE = 'en-us'

TEMPLATE_STRING_IF_INVALID = ''

DJANGO_SLIMMER = True

SESSION_ENGINE="django.contrib.sessions.backends.cache"

GOOGLE_ANALYTICS = True

CANONICAL_DOMAINS = {
    'en-gb.crosstips.org':'crosstips.org',
    'en-us.crosstips.org':'crosstips.org',
    }

GOOGLEMAPS_API_KEY = open(os.path.join(HOME, 'default_googlemaps_api.key')).read()

DO_THIS_MONTH_SPARKLINES = True

USE_CACHE_PAGE = True

MIGRATIONS_ROOT = os.path.join(HOME, 'migrations')




import logging
LOGGING_LOG_FILENAME = '/tmp/event-kl.log'
LOGGING_LEVEL = DEBUG and logging.DEBUG or logging.ERROR

import subprocess
_proc = subprocess.Popen('git log --no-color -n 1 --date=iso',
                         shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
_proc_out = _proc.communicate()[0]                         
try:
    GIT_REVISION_DATE = [x.split('Date:')[1].split('+')[0].strip() for x in
                         _proc_out.splitlines() if x.startswith('Date:')][0]
except IndexError:
    GIT_REVISION_DATE = 'unknown'
    logging.info("_proc_out=%r" % _proc_out)


try:
    # this should slowly die
    from settings_local import *
except ImportError:
    pass

try:
    from local_settings import *
except ImportError:
    pass

# must exist
HOME, SECRET_KEY, LANGUAGE_DOMAINS



logging.basicConfig(filename=LOGGING_LOG_FILENAME,
                    level=LOGGING_LEVEL,
                   )


