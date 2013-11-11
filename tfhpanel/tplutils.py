from tfhnode.models import DBSession
from tfhpanel.models import RootFactory, make_url
#from tfhpanel.views.panel import root_panels, root_panels_dict

def get_items(model, filter=None):
    q = DBSession.query(model).order_by(model.id)
    if filter:
        q = filter(q)
    return q.all()

def get_root_panels():
    return RootFactory.children

def get_root_panels_dict():
    #TODO: remove.
    return RootFactory.children

def format_panel_value(value):
    if isinstance(value, bool):
        # &#x2714; HEAVY CHECK MARK / &#x2718; HEAVY BALLOT X
        # &#x25cf; BLACK CIRCLE / &#x25cb; WHITE CIRCLE
        boolvalue = '&#x2714;' if value else '&#x2718;'
        return '<span class="panel-value-bool">'+boolvalue+'</span>'
    return '<span class="panel-value">'+str(value)+'</span>'

def find_view(dbo, root=RootFactory.children):
    for v in root.values():
        if isinstance(dbo, v.model):
            return v
        elif v.children:
            r = find_view(dbo, root.children)
            if r:
                return r

