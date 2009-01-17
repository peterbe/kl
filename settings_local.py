DEBUG = True
TEMPLATE_DEBUG = DEBUG

HOME = '/home/peterbe/dev/DJANGO/kl_env/kl'

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'search',
    'debug_toolbar',
    'django_extensions',
)


DEBUG_TOOLBAR = False

CACHE_BACKEND = "locmem:///?timeout=30"
