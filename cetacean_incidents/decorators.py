from django.conf import settings

from django.contrib.auth.decorators import permission_required as old_permission_required

def permission_required(perm, login_url=None):
    '''\
    Like Django's permission_required, but the login_url defaults to the value
    of the BAD_PERMISSION_URL setting.
    '''
    if login_url is None:
        login_url = settings.BAD_PERMISSION_URL
    return old_permission_required(perm, login_url)

def global_etag(request, *args, **kwargs):
    if not (request.GET or request.POST or request.FILES):
        if hasattr(settings, 'GLOBAL_ETAG'):
            return settings.GLOBAL_ETAG

