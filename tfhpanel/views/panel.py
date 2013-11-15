from pyramid.response import Response
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPOk, HTTPSeeOther, HTTPNotFound, HTTPBadRequest, HTTPInternalServerError
from pyramid.renderers import render_to_response
from collections import namedtuple
from sqlalchemy.orm import joinedload

from tfhnode.models import *
from tfhpanel.forms import *
from tfhpanel.models import PanelView

import logging
log = logging.getLogger(__name__)

from pyramid.i18n import TranslationStringFactory
_ = TranslationStringFactory('pyramid')

def filter_owned(field, query, request):
    return query.filter_by(userid = request.user.id)


class VHostForm(Form):
    name = TextField(_('Name'))
    catchall = TextField(_('Fallback URI'))
    autoindex = CheckboxField(_('Autoindex'))
    domains = OneToManyField(_('Domains'), fm=Domain,
        qf=[filter_owned])

class VHostPanel(PanelView):
    model = VHost
    formclass = VHostForm
    list_fields = ('name', 'domains')


class DomainForm(Form):
    domain = TextField(_('Name'))
    hostedns = CheckboxField(_('Hosted NS'))
    vhost = ForeignField(_('VHost'), fm=VHost, qf=[filter_owned])
    public = CheckboxField(_('Public'))
    verified = CheckboxField(_('Verified'), readonly=True)

class DomainPanel(PanelView):
    model = Domain
    formclass = DomainForm
    list_fields = ('user', 'domain', 'vhost', 'hostedns', 'public', 'verified')
    
    def read(self):
        d = super().read()
        d['left_template'] = 'domain/view_status.mako'
        return d


class MailboxForm(Form):
    domain = ForeignField(_('Domain'), fm=Domain, qf=[filter_owned])
    local_part = TextField(_('Local part'))
    redirect = TextField(_('Redirect (if any)'))
    password = PasswordField(_('Password (required to accept mails)'))

class MailboxPanel(PanelView):
    model = Mailbox
    formclass = MailboxForm
    list_fields = ('user', 'address')
    
    def read(self):
        d = super().read()
        d['aliases'] = DBSession.query(Mailbox).filter_by(redirect=d['object'].address).all()
        d['left_template'] = 'mailbox/view_aliases.mako'
        return d


class VHostRewriteForm(Form):
    regexp = TextField(_('RegExp'))
    dest = TextField(_('Rewrite to'))
    redirect_temp = CheckboxField(_('Temporary redirect (302)'))
    redirect_perm = CheckboxField(_('Permanent redirect (301)'))
    last = CheckboxField(_('Last'))

class VHostRewritePanel(PanelView):
    model = VHostRewrite
    formclass = VHostRewriteForm
    parent = VHostPanel
    list_fields = ('regexp', 'dest')


class VHostACLForm(Form):
    title = TextField(_('Title'))
    regexp = TextField(_('RegExp'))
    passwd = TextField(_('passwd file'))

class VHostACLPanel(PanelView):
    model = VHostACL
    formclass = VHostACLForm
    parent = VHostPanel
    list_fields = ('title', 'regexp')


class VHostErrorPageForm(Form):
    code = IntegerField(_('Error code'))
    path = TextField(_('Page URI'))

class VHostErrorPagePanel(PanelView):
    model = VHostErrorPage
    formclass = VHostErrorPageForm
    parent = VHostPanel
    list_fields = ('code', 'page')

