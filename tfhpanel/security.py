from pyramid.security import has_permission, Authenticated
from sqlalchemy.orm import joinedload
from .models import DBSession, User

class AuthenticationPolicy(object):
    def authenticated_userid(self, request):
        return request.user.id

    def unauthenticated_userid(self, request):
        return None

    def effective_principals(self, request):
        return request.principals

def get_user(request):
    if 'uid' not in request.session:
        return None

    uid = request.session['uid']
    user = DBSession.query(User) \
        .options(joinedload('groups')) \
        .filter_by(id=uid).first()
    if not user:
        # Delete bad session
        del request.session['uid']
        return None
    return user

# Used by AuthenticationPolicy and views through request.principals
# queried once per request
def get_principals(request):
    if not request.user:
        return []
    ep = []
    ep.append(Authenticated)
    #ep.append('user') # = every logged in user
    ep.append('user:'+str(request.user.id))
    for group in request.user.groups:
        ep.append('group:'+group.name)
    return ep

# same as pyramid.security.has_permission
# to not import has_permission in views
def req_has_permission(request, permission, context=None):
    if not context:
        context = request.context
    return has_permission(permission, context, request)

