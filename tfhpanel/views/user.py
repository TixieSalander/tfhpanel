from pyramid.response import Response
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPOk, HTTPSeeOther, HTTPNotFound, HTTPBadRequest, HTTPForbidden
from pyramid.renderers import render_to_response

from tfhnode.models import User
from tfhpanel.forms import *

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
    if request.method == 'POST':
        try:
            username = request.POST['username']
            password = request.POST['password']
            # TODO: match username or email
            user = DBSession.query(User).filter_by(username=username).first()
            assert user is not None
            assert user.check_password(password)
            request.session['uid'] = user.id
            request.session.flash(('info', _('Logged in.')))
            return HTTPSeeOther(location=request.route_url('user_home'))
        except KeyError:
            return HTTPBadRequest()
        except AssertionError:
            request.session.flash(('error', _('Invalid username/password.')))
    return {}

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
            DBSession.commit()
            request.session.flash(('info', _('Saved!')))
    return dict(form=form, object=object)


'''
@view_config(route_name='account_signup', renderer='ccvpn2_web:templates/signup.mako')
def a_signup(request):
    if request.method == 'POST':
        errors = []
        u = User()
        try:
            u.validate_username(request.POST['username']) or \
                errors.append('Invalid username.')
            u.validate_password(request.POST['password']) or \
                errors.append('Invalid password.')
            if request.POST['email']:
                u.validate_email(request.POST['email']) or \
                    errors.append('Invalid email address.')
            if request.POST['password'] != request.POST['password2']:
                errors.append('Both passwords do not match.')
            assert not errors
            
            nc = DBSession.query(func.count(User.id).label('nc')) \
                .filter_by(username=request.POST['username']) \
                .subquery()
            ec = DBSession.query(func.count(User.id).label('ec')) \
                .filter_by(email=request.POST['email']) \
                .subquery()
            c  = DBSession.query(nc, ec).first()
            if c.nc > 0:
                errors.append('Username already registered.')
            if c.ec > 0 and request.POST['email'] != '':
                errors.append('E-mail address already registered.')
            assert not errors
            u.username = request.POST['username']
            u.email = request.POST['email']
            u.set_password(request.POST['password'])
            DBSession.add(u)
            DBSession.commit()
            request.session['uid'] = u.id
            return HTTPSeeOther(location=request.route_url('account'))
        except KeyError:
            return HTTPBadRequest()
        except AssertionError as e:
            for error in errors:
                request.session.flash(('error', error))
            return {k:request.POST[k] for k in ('username','password','password2','email')}
    return {}

@view_config(route_name='account_forgot', renderer='ccvpn2_web:templates/forgot_password.mako')
def a_forgot(request):
    if request.method == 'POST':
        try:
            u = DBSession.query(User) \
                .filter_by(username=request.POST['username']) \
                .first()
            if not u:
                raise Exception('Unknown username.')
            if not u.email:
                raise Exception('No e-mail address associated. Contact the support.')
            # TODO: Here, send a mail with a reset link
            request.session.flash(('info', 'We sent a reset link. Check your emails.'))
        except KeyError:
            return HTTPBadRequest()
        except Exception as e:
            request.session.flash(('error', e.args[0]))
    return {}


@view_config(route_name='account', request_method='POST', permission='logged', renderer='ccvpn2_web:templates/account.mako')
def account_post(request):
    # TODO: Fix that. split in two functions or something.
    errors = []
    try:
        if 'profilename' in request.POST:
            p = Profile()
            p.validate_name(request.POST['profilename']) or \
                errors.append('Invalid name.')
            assert not errors
            if DBSession.query(Profile).filter_by(uid=request.user.id, name=request.POST['profilename']).first():
                errors.append('Name already used.')
            if DBSession.query(func.count(Profile.id)).filter_by(uid=request.user.id).scalar() > 10:
                errors.append('You have too many profiles.')
            assert not errors
            p.name = request.POST['profilename']
            p.askpw = 'askpw' in request.POST and request.POST['askpw'] == '1'
            p.uid = request.user.id
            if not p.askpw:
                p.password = random_profile_password()
            DBSession.add(p)
            DBSession.commit()
            return account(request)

        if 'profiledelete' in request.POST:
            p = DBSession.query(Profile) \
                .filter_by(id=int(request.POST['profiledelete'])) \
                .filter_by(uid=request.user.id) \
                .first()
            assert p or errors.append('Unknown profile.')
            DBSession.delete(p)
            DBSession.commit()
            return account(request)

        u = request.user
        if request.POST['password'] != '':
            u.validate_password(request.POST['password']) or \
                errors.append('Invalid password.')
            if request.POST['password'] != request.POST['password2']:
                errors.append('Both passwords do not match.')
        if request.POST['email'] != '':
            u.validate_email(request.POST['email']) or \
                errors.append('Invalid email address.')
        assert not errors

        if request.POST['email'] != '':
            c = DBSession.query(func.count(User.id).label('ec')).filter_by(email=request.POST['email']).first()
            if c.ec > 0:
                errors.append('E-mail address already registered.')
        assert not errors
        if request.POST['password'] != '':
            u.set_password(request.POST['password'])
        if request.POST['email'] != '':
            u.email = request.POST['email']
        DBSession.commit()
        request.session.flash(('info', 'Saved!'))

    except KeyError:
        return HTTPBadRequest()
    except AssertionError:
        for error in errors:
            request.session.flash(('error', error))
    return account(request)
    

@view_config(route_name='account_redirect')
def account_redirect(request):
    return HTTPMovedPermanently(location=request.route_url('account'))
'''
