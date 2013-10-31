from pyramid.config import Configurator
from sqlalchemy import engine_from_config
from sqlalchemy.orm import joinedload
from pyramid_beaker import session_factory_from_settings
from pyramid.authorization import ACLAuthorizationPolicy
from tfhnode.models import Base, DBSession, User, Group
from pyramid.security import has_permission, Authenticated
from tfhpanel.models import AuthenticationPolicy, RootFactory, traversal_view, PanelView, link_panels

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


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    session_factory = session_factory_from_settings(settings)
    config = Configurator(settings=settings)
    config.set_authentication_policy(AuthenticationPolicy())
    config.set_authorization_policy(ACLAuthorizationPolicy())
    config.set_root_factory(RootFactory)
    config.set_session_factory(session_factory)
    config.set_request_property(get_user, 'user', reify=True)
    config.set_request_property(get_principals, 'principals', reify=True)
    config.add_request_method(req_has_permission, 'has_permission')
    config.add_translation_dirs('tfhpanel:locale')
    config.add_subscriber('tfhpanel.subscribers.add_renderer_globals',
                          'pyramid.events.BeforeRender')
    config.add_subscriber('tfhpanel.subscribers.add_localizer',
                          'pyramid.events.NewRequest')
    
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('home',            '/')
    
    config.add_route('user_home',       '/user/')
    config.add_route('user_settings',   '/user/settings')
    config.add_route('user_login',      '/user/login')
    config.add_route('user_logout',     '/user/logout')
    config.add_route('user_signup',     '/user/signup')
    config.add_route('user_pwreset',    '/user/pwreset')
    
    config.add_view(traversal_view, context=PanelView)

    config.scan()
    link_panels()
    return config.make_wsgi_app()

