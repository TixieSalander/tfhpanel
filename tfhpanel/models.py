from tfhnode.models import *
from pyramid.security import Allow, Deny, Authenticated, Everyone, ALL_PERMISSIONS, DENY_ALL

class AuthenticationPolicy(object):
    def authenticated_userid(self, request):
        return request.user.id

    def unauthenticated_userid(self, request):
        return None

    def effective_principals(self, request):
        return request.principals

class RootFactory(object):
    __acl__ = [
        (Allow, Authenticated, 'user'),
        (Allow, 'group:hosted', 'vhost_panel'),
        (Allow, 'group:hosted', 'domain_panel'),
        (Allow, 'group:hosted', 'mail_panel'),
        (Allow, 'group:hosted', 'support_user'),
        (Allow, 'group:support', 'support_admin'),
        (Allow, 'group:admin', ALL_PERMISSIONS),
        DENY_ALL
    ]

    def __init__(self, request):
        pass

