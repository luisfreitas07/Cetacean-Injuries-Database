#from os import path
try:
    from cetacean_incidents.local_settings import *
except ImportError:
    from local_settings import *

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en_US'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = URL_PREFIX + 'site_media/'

# The jQuery library should be present in
#<MEDIA_URL>/<JQUERY_FILE>
JQUERY_FILE = 'jquery/jquery-1.5.2.min.js'

JQUERY_PLUGIN_COOKIE = 'jquery/plugins/jquery.cookie.js'

# The a jQuery-ui library with the overcast theme and the tabs component should 
# be present in:
#<MEDIA_URL>/<JQUERYUI_CSS_FILE>
#<MEDIA_URL>/<JQUERYUI_JS_FILE>
JQUERYUI_CSS_FILE = 'jqueryui/mmid/jquery-ui-1.8.11.custom.css'
JQUERYUI_JS_FILE = 'jqueryui/jquery-ui-1.8.11.custom/js/jquery-ui-1.8.11.custom.min.js'

# careful of circular imports here. if you import django.contrib.admin, it tries
# to read django settings from this file
#import django.contrib
#ADMIN_MEDIA_ROOT = path.join(path.dirname(django.contrib.__file__), 'admin', 'media')
ADMIN_MEDIA_PREFIX = MEDIA_URL + 'admin/'

LOGIN_URL = URL_PREFIX + 'login/' 
LOGIN_REDIRECT_URL = URL_PREFIX

# this is the URL users are redirected to when the permission_required decorator
# fails
BAD_PERMISSION_URL = URL_PREFIX + 'not_allowed/'

CACHE_MIDDLEWARE_SECONDS = 15 * 60
CACHE_MIDDLEWARE_KEY_PREFIX = ''

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    #'django.middleware.cache.UpdateCacheMiddleware' ,
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    #'django.middleware.cache.FetchFromCacheMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
    'reversion.middleware.RevisionMiddleware',
)

ROOT_URLCONF = 'cetacean_incidents.urls'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.databrowse',
    'django.contrib.humanize',
    'django_extensions',
    #'devserver',
    #'debug_toolbar',
    'reversion',
    'tinymce',
    'cetacean_incidents.apps.utils',
    'cetacean_incidents.apps.countries',
    'cetacean_incidents.apps.locations',
    'cetacean_incidents.apps.contacts',
    'cetacean_incidents.apps.uncertain_datetimes',
    'cetacean_incidents.apps.vessels',
    'cetacean_incidents.apps.taxons',
    'cetacean_incidents.apps.incidents',
    'cetacean_incidents.apps.tags',
    'cetacean_incidents.apps.entanglements',
    'cetacean_incidents.apps.shipstrikes',
    'cetacean_incidents.apps.generic_templates',
    'cetacean_incidents.apps.merge_form',
    'cetacean_incidents.apps.jquery_ui',
    'cetacean_incidents.apps.describe_fields',
    'cetacean_incidents.apps.documents',
    'cetacean_incidents.apps.csv_import',
    'cetacean_incidents.apps.clean_cache',
    'cetacean_incidents.apps.search_forms',
    'cetacean_incidents.apps.reports',
    'cetacean_incidents.apps.manual',
)

USING_ORACLE = False
import re
for db_settings in DATABASES.values():
    if re.search('\.oracle$', db_settings['ENGINE']):
        USING_ORACLE = True

# oracle checks the enviornment for lang settings.
if USING_ORACLE:
    import os
    os.environ['NLS_SORT'] = 'LATIN' # do a sensible english sort

# match the formatting of UncertainDatetime.__unicode__
DATE_FORMAT = '%Y-%m-%d'
SHORT_DATE_FORMAT = DATE_FORMAT
TIME_FORMAT = '%H:%M:%S'
SHORT_TIME_FORMAT = TIME_FORMAT
DATETIME_FORMAT = DATE_FORMAT + ' ' + TIME_FORMAT
SHORT_DATETIME_FORMAT = DATETIME_FORMAT

GLOABL_ETAG = None
# if the dulwich library is available, the ETAG is set based on git
try:
    from dulwich.repo import Repo
    # The ETAG is the sha1 of the current git HEAD commit
    REPO_PATH = path.dirname(PROJECT_PATH)
    repo = Repo(REPO_PATH)
    GLOBAL_ETAG = repo.head()
except ImportError:
    pass

TINYMCE_JS_URL = MEDIA_URL + 'tiny_mce/tiny_mce.js'
TINYMCE_JS_ROOT = path.join(MEDIA_ROOT, 'tiny_mce')

TINYMCE_DEFAULT_CONFIG = {
    'plugins': "table,fullpage,style,contextmenu,advlist,paste",
    'theme_advanced_buttons2_add': "styleprops",
    'theme_advanced_buttons3_add': "tablecontrols,fullpage",
    'theme': "advanced",
    'cleanup_on_startup': True,
    'custom_undo_redo_levels': 10,
}
TINYMCE_COMPRESSOR = False

