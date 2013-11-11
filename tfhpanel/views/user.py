from pyramid.response import Response
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPOk, HTTPSeeOther, HTTPNotFound, HTTPBadRequest, HTTPForbidden
from pyramid.renderers import render_to_response
from sqlalchemy import or_
from tfhnode.models import User
from tfhpanel.forms import *
from tfhpanel.models import make_pgp_token
import logging
log = logging.getLogger(__name__)

from pyramid.view import forbidden_view_config

from pyramid.i18n import TranslationStringFactory
_ = TranslationStringFactory('pyramid')

@forbidden_view_config()
def forbidden_view(request):
    if not request.user:
        return HTTPSeeOther(location=request.route_url('user_login'))
    return request.exception

@view_config(route_name='home')
def home(request):
    if request.user:
        return HTTPSeeOther(location=request.route_url('user_home'))
    return HTTPSeeOther(location=request.route_url('user_login'))

@view_config(route_name='user_login', renderer='user/login.mako')
def user_login(request):
    _ = request.translate
    pgp = 'pgp' in request.GET and request.GET['pgp']
    if request.method == 'POST':
        try:
            username = request.POST['username']
            user = DBSession.query(User) \
                .filter(or_(User.username==username, User.email==username)) \
                .first()
            assert user is not None
            if pgp:
                token = request.session['login_cleartoken']
                signedtoken = request.POST['signedtoken']
                assert user.verify_signature(cleartext=token, signature=signedtoken)
            else:
                password = request.POST['password']
                assert user.check_password(password)
            
            request.session['uid'] = user.id
            request.session.flash(('info', _('Logged in.')))
            return HTTPSeeOther(location=request.route_url('user_home'))
        except KeyError:
            return HTTPBadRequest()
        except AssertionError:
            request.session.flash(('error', _('Invalid username/password.')))
    if pgp:
        token = make_pgp_token(request)
        request.session['login_cleartoken'] = token
    else:
        token = ''
    return {'pgp':pgp, 'pgp_token':token}

@view_config(route_name='user_logout', permission='user')
def user_logout(request):
    _ = request.translate
    if 'uid' in request.session:
        del request.session['uid']
        request.session.flash(('info', _('Logged out.')))
    return HTTPSeeOther(location=request.route_url('user_login'))

@view_config(route_name='user_home', permission='user', renderer='user/home.mako')
def user_home(request):
    return {'user':request.user}

class UserSettingsForm(Form):
    username = TextField(_('Username'))
    password = PasswordField(_('Password'))
    email = TextField(_('E-Mail'))
    pgppk = PGPKeyField(_('OpenPGP public key'), require=PGPKeyField.PUBKEY)

@view_config(route_name='user_settings', permission='user', renderer='user/settings.mako')
def user_settings(request):
    form = UserSettingsForm(request, request.route_url('user_settings'))
    object = request.user
    if request.method == 'POST':
        errors = form.validate(request.POST)
        if errors:
            for error in errors:
                request.session.flash(('error', error))
        else:
            form.save(object)
            if form.password and not isinstance(form.password, IgnoreValue):
                object.set_password(form.password)
            DBSession.commit()
            request.session.flash(('info', _('Saved!')))
    return dict(form=form, object=object)

