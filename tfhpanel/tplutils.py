from tfhnode.models import DBSession
from tfhpanel.views.panel import root_panels

def get_items(model):
    return DBSession.query(model).order_by(model.id).all()

def get_root_panels():
    return root_panels

