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


