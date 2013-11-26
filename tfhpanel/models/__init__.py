from pyramid.security import Allow, Deny, Authenticated, Everyone, ALL_PERMISSIONS, DENY_ALL
from pyramid.response import Response
from pyramid.view import view_config
from pyramid.httpexceptions import *
from pyramid.renderers import render_to_response
from collections import namedtuple
import sqlalchemy
import datetime
import random
from .db import *
from .forms import *

from pyramid.i18n import TranslationStringFactory
_ = TranslationStringFactory('pyramid')

def make_url(path, change_ids=None, index=False):
    url = ''
    for item in path:
        url += '/%s/' % item.model.short_name

        id = item.id
        if change_ids:
            if isinstance(change_ids, item.model):
                attr = 'id'
            else:
                attr = item.model.short_name + 'id'
            if hasattr(change_ids, attr):
                id = getattr(change_ids, attr)
        if id:
            if item == path[-1] and index:
                break
            url += str(id)
    return url

def make_pgp_token(request):
    # Remote address, timestamp,
    token = 'Tux-FreeHost authentication\n'
    token += 'From %s\n' % request.remote_addr
    token += 'On %s\n' % datetime.datetime.now().timestamp()
    token += '---\n'
    
    charset = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for i in range(0, 128, 32):
        randomstuff = [charset[random.randint(0, len(charset)-1)] for n in range(32)]
        token += ''.join(randomstuff) + '\n'
    return token

def traversal_view(context, request):
    return context.handle_request(request)

class RootFactory(object):
    children = {}
    __acl__ = [
        (Allow, Authenticated, 'user'),
        (Allow, 'group:hosted', 'vhost_panel'),
        (Allow, 'group:hosted', 'domain_panel'),
        (Allow, 'group:hosted', 'mailbox_panel'),
        (Allow, 'group:hosted', 'support_user'),
        (Allow, 'group:support', 'support_admin'),
        (Allow, 'group:admin', ALL_PERMISSIONS),
        DENY_ALL
    ]

    def __getitem__(self, name):
        return self.children[name]([])

    def __init__(self, request):
        pass

class PanelView(RootFactory):
    parent = None
    children = {}
    model = None
    form = None
    id = None
    required_perm = None

    @property
    @classmethod
    def short_name(cls):
        return cls.model.short_name

    def __init__(self, path=[]):
        self.id = None
        self.path = path
        self.path.append(self)

    def __getitem__(self, name):
        if self.id:
            # TODO: get object #id => self.object
            return self.children[name](self.path)
        else:
            try:
                self.id = int(name)
            except ValueError:
                # Bad URL -> KeyError -> 404
                raise KeyError()
            return self

    def is_admin(self):
        return self.request.session.get('panel_admin', False)
    
    def find_required_uid(self):
        view = self
        while view:
            if view.model == User:
                return view.model.id
            if hasattr(view.model, 'userid'):
                return view.model.userid
            view = view.parent
    
    def filter_query(self, q, level=None):
        if not self.is_admin():
            column = self.find_required_uid()
            if not column:
                # Cannot determine column, assume no one owns it.
                raise HTTPForbidden()
            q = q.filter(column == self.request.user.id)
        
        for item in self.path:
            if not item.id:
                continue
            if level is not None:
                if not level:
                    break
                level -= 1
            if item.model == self.model:
                column = getattr(self.model, 'id')
            else:
                column = getattr(self.model, item.model.short_name + 'id')
            q = q.filter(column == item.id)
        return q

    def make_title(self):
        title = ''
        sep = ' &#xbb; '
        for i in range(1, len(self.path)+1):
            path = self.path[0:i]
            url = make_url(path)
            name = path[-1].model.display_name
            if i > 1:
                title += sep
            title += '<a href="%s">%s</a>' % (make_url(path, index=True), name)
            if hasattr(path[-1], 'object'):
                title += sep+'<a href="%s">%s</a>' % (make_url(path), path[-1].object.get_natural_key())
            elif path[-1].id:
                title += sep+'<a href="%s">#%s</a>' % (make_url(path), path[-1].id)
        return title
            

    def render(self, template, data):
        data['panelview'] = self
        return render_to_response('panel/'+template,
            data, request=self.request)
    
    def redirect(self, object):
        url = make_url(self.path, change_ids=object)
        return HTTPSeeOther(location=url)

    def list(self):
        objects = DBSession.query(self.model)
        objects = self.filter_query(objects).order_by(self.model.id).all()
        self.objects = list(objects)
        if hasattr(self.model, 'user') and self.is_admin():
            list_fields = self.list_fields[:]
            list_fields.append((_('User'), 'user'))
        else:
            list_fields = self.list_fields
        
        self.form._defaults['user'] = '#'+str(self.request.user.id)
        for item in self.path:
            if not item.id:
                continue
            self.form._defaults[item.model.short_name] = '#'+str(item.id)

        return dict(objects=self.objects, list_fields=list_fields)

    def create(self):
        object = self.model()
        # apply filter_query stuff
        if hasattr(object, 'userid'):
            object.userid = self.request.user.id
        for item in self.path:
            if not item.id or isinstance(item, self.__class__):
                continue
            setattr(object, item.model.short_name+'id', item.id)

        errors = self.form.save(self.request.POST, object)
        if errors:
            for error in errors:
                self.request.session.flash(('error', error))
        else:
            DBSession.add(object)
            try:
                DBSession.commit()
                self.request.session.flash(('info', _('Saved!')))
            except sqlalchemy.exc.IntegrityError as err:
                # TODO: Find what column make the error with err
                DBSession.rollback()
                self.request.session.flash(('error', _('Error: duplicate key.')))
        return dict(object=object)

    def read(self):
        object = DBSession.query(self.model)
        object = self.filter_query(object).first()
        if not object:
            raise HTTPNotFound(comment='object not found')
        self.object = object
        return dict(object=object)

    def update(self):
        object = DBSession.query(self.model)
        object = self.filter_query(object).first()
        if not object:
            raise HTTPNotFound(comment='object not found')
        
        errors = self.form.save(self.request.POST, object)
        if errors:
            # del object to ignore any changes
            del object
            object = None
            for error in errors:
                self.request.session.flash(('error', error))
        else:
            try:
                DBSession.commit()
                self.request.session.flash(('info', _('Saved!')))
            except sqlalchemy.exc.IntegrityError as err:
                # TODO: Find what column make the error with err
                DBSession.rollback()
                self.request.session.flash(('error', _('Error: duplicate key.')))
        return dict(object=object)
    
    def delete(self):
        # TODO
        pass

    def handle_request(self, req):
        self.request = req
        get = req.method == 'GET'
        post = req.method == 'POST'
        index = not self.id
        
        if self.required_perm and not self.request.has_permission(self.required_perm):
            raise HTTPForbidden()
        
        if 'admin' in req.GET and self.request.has_permission('panel_admin'):
            req.session['panel_admin'] = '1' == req.GET['admin']

        act = make_url(self.path)
        self.form = self.formclass(self.request, action=act, admin=self.is_admin())
        
        return \
            self.render('list.mako', self.list()) if get & index else \
            self.render('view.mako', self.read()) if get else \
            self.redirect(self.create()) if post & index else \
            self.redirect(self.update()) if post else \
            HTTPBadRequest()
            




# Setup links between panel views
def link_panels():

    root_panels = []
    root_panels_dict = {}

    for pv in PanelView.__subclasses__():
        if pv.parent and not pv.parent.children:
            pv.parent.children = {}
        if pv.parent and not pv in pv.parent.children:
            pv.parent.children[pv.model.short_name] = pv
        else:
            RootFactory.children[pv.model.short_name] = pv
        
        pv.reverse_path = []
        o = pv
        while o:
            pv.reverse_path.append(o)
            o = o.parent
        pv.path = reversed(pv.reverse_path)

        del pv
    

