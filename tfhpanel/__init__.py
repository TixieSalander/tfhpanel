from pyramid.config import Configurator
from sqlalchemy import engine_from_config
from pyramid_beaker import session_factory_from_settings
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.httpexceptions import HTTPMovedPermanently
from pyramid.view import notfound_view_config, view_config
from tfhpanel.models import (
    RootFactory, traversal_view, PanelView, link_panels,
    Base, DBSession,
)
from tfhpanel.security import (
    AuthenticationPolicy, 
    get_user, get_principals, req_has_permission,
)

def add_auto_route(config, name, pattern, **kw):
    config.add_route(name, pattern, **kw)
    
    if not pattern.endswith('/'):
        config.add_route(name + '_', pattern + '/')
        def redirector(request):
            return HTTPMovedPermanently(request.route_url(name,_query=request.GET,**request.matchdict))
        config.add_view(redirector, route_name=name + '_')


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    session_factory = session_factory_from_settings(settings)
    config = Configurator(settings=settings)
    config.include('pyramid_mako')
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


    # URLs ending with slash
    config.add_route('home',        '/')
    config.add_route('user_home',   '/user/')

    # URLs ending without slash
    add_auto_route(config, 'user_settings',   '/user/settings')
    add_auto_route(config, 'user_logout',     '/user/logout')
    add_auto_route(config, 'user_signup',     '/user/signup')
    add_auto_route(config, 'user_pwreset',    '/user/pwreset')
    add_auto_route(config, 'user_login',      '/user/login')


    config.add_view(traversal_view, context=PanelView)


    config.scan()
    link_panels()
    return config.make_wsgi_app()

