#!/usr/bin/env python3

from pyramid.paster import get_appsettings, setup_logging
from argparse import ArgumentParser, RawTextHelpFormatter
import sqlalchemy
from tfhpanel import services, models, DBSession
import os
import logging
log = logging.getLogger(__name__)

def get_subclasses(cls):
    subclasses = []
    for c in cls.__subclasses__():
        subclasses.append(c)
        subclasses.extend(get_subclasses(c))
    return subclasses

def initdb(args, settings):
    print('Creating DB structure...')
    models.Base.metadata.create_all(DBSession.bind)

    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("./alembic.ini")
    command.stamp(alembic_cfg, "head")
    
    print('Add default data...')
    try:
        hosted_group = models.Group(name='hosted', description='Hosted users')
        support_group = models.Group(name='support', description='Support')
        admin_group = models.Group(name='admin', description='Administrator')
        DBSession.add_all([hosted_group, support_group, admin_group])
        DBSession.commit()
        
        admin_user = models.User(username='admin', groups=[admin_group])
        admin_user.set_password('admin')
        DBSession.add(admin_user)
        DBSession.commit()
    except sqlalchemy.exc.IntegrityError:
        pass

def config(args, settings):
    configfiles = get_subclasses(services.ConfigFile)
    if args.filename:
        files = []
        for f in args.filename:
            files.extend(filter(lambda c: c.filename==f, configfiles))
    else:
        files = configfiles
    
    for file in files:
        if not file.filename:
            continue

        path = os.path.join(args.output, file.filename)
        dirname = os.path.dirname(path)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname)
        
        fh = open(path, 'w')
        fh.write(file.generate(settings))
        fh.close()
        
        if file.mode:
            os.chmod(path, file.mode)
        
        print('Generated %s' % file.filename)

if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__, formatter_class=RawTextHelpFormatter)
    parser.add_argument('-v', '--verbose', action='count',
        help='Increase verbosity')
    parser.add_argument('-c', '--config', default='development.ini')
    subparsers = parser.add_subparsers(title='subcommands')
    
    subparsers.add_parser('initdb').set_defaults(func=initdb)
    
    parser_add = subparsers.add_parser('config', help='Generate config files')
    parser_add.set_defaults(func=config)
    parser_add.add_argument('-f', '--filename', help='Only <filename>', action='append', default=[])
    parser_add.add_argument('-o', '--output',  default='./config/',
        help='where to put generated config')

    args = parser.parse_args()

    log_level = logging.WARNING
    if args.verbose != None:
        verbose = int(args.verbose)
        if verbose == 1:
            log_level = logging.INFO
        elif verbose >= 2:
            log_level = logging.DEBUG
    logging.basicConfig(level=log_level)
    
    config_uri = args.config
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)
    engine = sqlalchemy.engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)

    try:
        f = args.func
    except AttributeError:
        parser.print_help()
        exit()
    f(args, settings=settings)

