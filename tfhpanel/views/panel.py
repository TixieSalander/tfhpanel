from pyramid.response import Response
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPOk, HTTPSeeOther, HTTPNotFound, HTTPBadRequest, HTTPInternalServerError
from pyramid.renderers import render_to_response
from collections import namedtuple

from tfhnode.models import *
from tfhnode.forms import *

import logging
log = logging.getLogger(__name__)

class PanelView(object):
    models = None
    form = None
    parent = None
    subs = []

    @property
    @classmethod
    def short_name(cls):
        return cls.__name__.lower()

    def __init__(self, request):
        self.request = request
        self.filters = {}
        for k, v in self.request.matchdict.items():
            self.filters[k] = int(v, 16) if v else None
    
    def find_required_uid(self):
        view = self
        while view:
            if view.model == User:
                return view.model.id
            if hasattr(view.model, 'userid'):
                return view.model.userid
            view = view.parent

    def filter_query(self, q):
        if not self.request.has_permission('panel_admin'):
            column = self.find_required_uid()
            if not column:
                # Cannot determine column, assume no one owns it.
                raise HTTPForbidden()
            q = q.filter(column == self.request.user.id)

        for k, v in self.filters.items():
            if v is None or v == '':
                # Do not put a break here, because of the dict's random order.
                # debugging time lost here: timedelta(minutes=30)
                continue
            column = getattr(self.model, k)
            q = q.filter(column == v)
        return q

    def make_url(self, o=None):
        if o:
            url = '/%s/%d' % (o.short_name, o.id)
        else:
            url = '/%s/' % self.model.short_name
        parent = self.parent
        while parent:
            if o:
                parent_name = parent.model.short_name
                id = getattr(o, parent_name+'id')
                url = '/%s/%d'%(parent_name, id) + url
            else:
                parent_name = parent.model.short_name
                if not parent_name+'id' in self.filters:
                    raise HTTPInternalServerError()
                id = self.filters[parent_name+'id']
                url = '/%s/%d'%(parent_name, id) + url

            parent = parent.parent
        return url

    def render(self, template, **kwargs):
        v = kwargs
        v.update(dict(view=self))
        return render_to_response('panel/'+template,
            v, request=self.request)

    def get_index(self):
        objects = DBSession.query(self.model)
        objects = self.filter_query(objects).order_by(self.model.id).all()
        return self.render('list.mako', objects=objects)

    def get(self):
        object = DBSession.query(self.model)
        object = self.filter_query(object).first()
        if not object:
            raise HTTPNotFound(comment='object not found')
        return self.render('view.mako', object=object)
    
    # TODO: post/post_index

    def __call__(self):
        get = self.request.method == 'GET'
        post = self.request.method == 'POST'
        index = not self.request.matchdict['id']

        return \
            self.get_index() if get & index else \
            self.get() if get else \
            self.post_index() if post & index else \
            self.post() if post else \
            HTTPBadRequest()

@view_config(route_name='p_vhost', request_method=('GET', 'POST'), permission='vhost_panel')
class VHostPanel(PanelView):
    model = VHost
    form = (
        FormField('VHost.name'),
        ForeignField('Domain.userid', fk='user'),
        # serverid
        # update
        FormField('VHost.catchall'),
        FormField('VHost.autoindex'),
        FormField('VHost.apptype'),
        FormField('VHost.applocation'),
    )
    list_fields = ('name', 'user')

@view_config(route_name='p_domain', request_method=('GET', 'POST'), permission='domain_panel')
class DomainPanel(PanelView):
    model = Domain
    form = (
        ForeignField('Domain.userid', fk='user'),
        FormField('Domain.domain'),
        FormField('Domain.hostedns'),
        FormField('Domain.public'),
        ForeignField('Domain.vhostid', fk='vhost'),
    )
    list_fields = ('user', 'domain', 'hostedns', 'public')

@view_config(route_name='p_mailbox', request_method=('GET', 'POST'), permission='mail_panel')
class MailboxPanel(PanelView):
    model = Mailbox
    form = (
        ForeignField('Mailbox.userid', fk='user'),
        ForeignField('Mailbox.domainid', fk='domain'),
        FormField('Mailbox.local_part', RegexpValidator('^[a-zA-Z0-9._-]{1,64}$'),
            immutable=True),
        FormFieldGroup('or',
            FormField('Mailbox.redirect', RegexpValidator('^.+@.+$')),
            PasswordField('Mailbox.password', StringValidator(max_len=256)),
        ),
    )
    list_fields = ('user', 'address')

@view_config(route_name='p_vhostrewrite', request_method=('GET', 'POST'), permission='vhost_panel')
class VHostRewritePanel(PanelView):
    model = VHostRewrite
    form = (
        FormField('VHostRewrite.regexp', StringValidator(1, 256)),
        FormField('VHostRewrite.dest', StringValidator(1, 256)),
        FormField('VHostRewrite.redirect_temp'),
        FormField('VHostRewrite.redirect_perm'),
        FormField('VHostRewrite.last'),
    )
    parent = VHostPanel
    list_fields = ('regexp', 'dest')

@view_config(route_name='p_vhostacl', request_method=('GET', 'POST'), permission='vhost_panel')
class VHostACLPanel(PanelView):
    model = VHostACL
    form = (
        FormField('VHostACL.title', StringValidator(1, 256)),
        FormField('VHostACL.regexp', StringValidator(1, 256)),
        FormField('VHostACL.passwd', StringValidator(1, 256)),
    )
    parent = VHostPanel
    list_fields = ('title', 'regexp')
   
@view_config(route_name='p_vhostep', request_method=('GET', 'POST'), permission='vhost_panel')
class VHostErrorPagePanel(PanelView):
    model = VHostErrorPage
    form = (
        FormField('VHostErrorPage.code'),
        FormField('VHostErrorPage.path', StringValidator(1, 256)),
    )
    parent = VHostPanel
    list_fields = ('code', 'page')


root_panels = []

for pv in PanelView.__subclasses__():
    if pv.parent and not pv.parent.subs:
        pv.parent.subs = []
    if pv.parent and not pv in pv.parent.subs:
        pv.parent.subs.append(pv)
    else:
        root_panels.append(pv)
    del pv

