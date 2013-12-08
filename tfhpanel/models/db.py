from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.sql.expression import true, false
import datetime
from sqlalchemy.ext.declarative import declarative_base
import inspect
import re
import crypt
import tempfile
import subprocess
import random
import os
import logging
from mako.template import Template

class MyBase(object):
    def get_natural_key(self):
        if hasattr(self, '__natural_key__'):
            return getattr(self, self.__natural_key__)
        return None

    def __str__(self):
        return self.get_natural_key() or ('#'+str(self.id))

    def __repr__(self):
        args = ['id='+repr(self.id)]
        if hasattr(self, '__natural_key__'):
            value = getattr(self, self.__natural_key__)
            args.append(self.__natural_key__+'='+repr(value))
        return '%s(%s)' % (self.__class__.__name__, args.join(', '))

class NullBoolean(TypeDecorator):
    impl = Boolean

    def process_bind_param(self, value, dialect):
        return True if value else None

    def process_result_value(self, value, dialect):
        return value or False

DBSession = scoped_session(sessionmaker())
Base = declarative_base(cls=MyBase)
metadata = MetaData()

class User(Base):
    __tablename__ = 'users'
    __display_name__ = 'Users'
    __short_name__ = 'user'
    __natural_key__ =  'username'
    id       = Column(Integer, primary_key=True)
    username = Column(String(32), unique=True, nullable=False)
    password = Column(String(128))
    pgppk    = deferred(Column(Binary()))
    email    = Column(String(512))
    signup_date = Column(DateTime, default=datetime.datetime.now, nullable=False)
    shell    = Column(String(128))

    vhosts   = relationship('VHost', backref='user')
    logins   = relationship('LoginHistory', backref='user')
    domains  = relationship('Domain', backref='user')
    mailboxes= relationship('Mailbox', backref='user')

    def check_password(self, cleartext):
        return self.password == crypt.crypt(cleartext, self.password)

    def set_password(self, cleartext):
        try:
            self.password = crypt.crypt(cleartext)
        except TypeError:
            # Python2
            charset = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
            salt = ''.join([random.choice(charset) for n in range(0, 16)])
            self.password = crypt.crypt(cleartext, '$6$'+salt)

    def verify_signature(self, cleartext, signature):
        import gnupg
        import shutil
        import os

        gpghome = tempfile.mkdtemp()
        text_file = tempfile.mkstemp()[1]
        sign_file = tempfile.mkstemp()[1]

        with open(text_file, 'wb') as f:
            f.write(bytes(cleartext, 'utf-8'))
        with open(sign_file, 'wb') as f:
            f.write(bytes(signature, 'utf-8'))

        gpg = gnupg.GPG(gnupghome=gpghome)
        i = gpg.import_keys(self.pgppk)
        v = gpg.verify_file(open(sign_file, 'rb'), text_file)

        os.remove(text_file)
        os.remove(sign_file)
        shutil.rmtree(gpghome)

        return i and v and v.pubkey_fingerprint in i.fingerprints

    def get_primary_group_name(self):
        return self.groups[0].name


usergroup_association = Table('usergroups', Base.metadata,
    Column('userid', Integer, ForeignKey('users.id')),
    Column('groupid', Integer, ForeignKey('groups.id')),
)

class Group(Base):
    __tablename__ = 'groups'
    __natural_key__ =  'name'
    id       = Column(Integer, primary_key=True)
    name     = Column(String(64), index=True, unique=True, nullable=False)
    description = Column(String(256))

    users    = relationship('User', secondary=usergroup_association, backref='groups')

class LoginHistory(Base):
    __tablename__ = 'login_history'
    id       = Column(Integer, primary_key=True)
    userid   = Column(ForeignKey('users.id'), nullable=False)
    time     = Column(DateTime, default=datetime.datetime.now, nullable=False)
    remote   = Column(String(64))
    useragent= Column(String(64))

class Domain(Base):
    __tablename__ = 'domains'
    __table_args__ = (
        UniqueConstraint('domain', 'userid'),
        UniqueConstraint('domain', 'verified'),
    )
    __natural_key__ =  'domain'
    __short_name__ = 'domain'
    __display_name__ = 'Domains'
    id       = Column(Integer, primary_key=True)
    userid   = Column(ForeignKey('users.id'), nullable=False)
    domain   = Column(String(256), nullable=False)
    hostedns = Column(Boolean, nullable=False)
    vhostid  = Column(ForeignKey('vhosts.id'))
    public   = Column(Boolean, default=False, nullable=False)
    verified = Column(NullBoolean, default=False, nullable=True)
    verif_token = Column(String(64))

    entries  = relationship('DomainEntry', backref='domain')
    mailboxes= relationship('Mailbox', backref='domain')


class DomainEntry(Base):
    __tablename__ = 'domainentries'
    __short_name__ = 'domainentry'
    __display_name__ = 'Domain Entries'
    id       = Column(Integer, primary_key=True)
    domainid = Column(ForeignKey('domains.id'), nullable=False)
    sub      = Column(String(256))
    rdatatype= Column(Integer, nullable=False)
    rdata    = Column(Text, nullable=False)

    panel_parent = Domain

class Mailbox(Base):
    __tablename__ = 'mailboxes'
    __table_args__ = (
        UniqueConstraint('domainid', 'local_part'),
    )
    __short_name__ = 'mailbox'
    __display_name__ = 'Mailboxes'
    __natural_key__ =  'address'
    id       = Column(Integer, primary_key=True)
    userid   = Column(ForeignKey('users.id'), nullable=False)
    domainid = Column(ForeignKey('domains.id'), nullable=False)
    local_part = Column(String(64), nullable=True)
    password = Column(String(128))
    redirect = Column(String(512))

    @property
    def address(self):
        return (self.local_part or '*')+'@'+self.domain.domain

    @address.setter
    def address(self, value):
        l, h = value.rsplit('@', 1)
        self.local_part = l
        # TODO: search for domain h

class VHost(Base):
    __tablename__ = 'vhosts'
    __table_args__ = (
        UniqueConstraint('name', 'userid'),
    )
    __natural_key__ =  'name'
    __short_name__ = 'vhost'
    __display_name__ = 'VHosts'

    appTypes = {
        0x00 : 'None',
        0x01 : 'Custom HTTP',
        0x02 : 'Custom FCGI',
        0x04 : 'Custom WSGI',
        0x10 : 'PHP',
        0x20 : 'Python',
        0x40 : 'Node.js',
        0x80 : 'Perl',
    }

    class APP:
        NONE = 0x00
        CUSTOM_HTTP = 0x01
        CUSTOM_FCGI = 0x02
        CUSTOM_WSGI = 0x04
        PHP = 0x10
        UWSGI = 0x20

    id       = Column(Integer, primary_key=True)
    name     = Column(String(32), nullable=False)
    userid   = Column(ForeignKey('users.id'), nullable=False)
    update   = Column(DateTime, onupdate=datetime.datetime.now)
    catchall = Column(String(256))
    autoindex= Column(Boolean, nullable=False, default=False)
    apptype  = Column(BigInteger, nullable=False, default=0)
    applocation = Column(String(512))

    domains  = relationship('Domain', backref='vhost')
    rewrites = relationship('VHostRewrite', backref='vhost')
    acls     = relationship('VHostACL', backref='vhost')
    errorpages=relationship('VHostErrorPage', backref='vhost')

    def get_public_dir(self):
        pubdir = '/home/%s/http_%s/' % (self.user.username, self.name)
        if not os.path.isdir(pubdir):
            return pubdir
        oldpubdir = '/home/%s/public_http/' % (self.user.username)
        if os.path.isdir(oldpubdir):
            return oldpubdir
        # TODO: Make and chown pubdir
        return None

    def get_ssl_certs(self, generate=False):
        # User-provided SSL cert
        base = '/home/%s/ssl/%s' % (self.user.username, self.name)
        user_cert, user_csr, user_key = base+'.crt', base+'.csr', base+'.key'
        if os.path.isfile(user_cert) and os.path.isfile(user_key):
            logging.debug('-> found user SSL cert.')
            return (user_cert, user_key)

        # System-wide wildcard
        for domain in self.domains:
            parts = domain.domain.split('.')
            for i in range(1, len(parts)-1):
                hmm = '.'.join(parts[i:])
                cert = '/etc/ssl/tfhcerts/wildcard.%s.crt' % (hmm)
                key  = '/etc/ssl/tfhkeys/wildcard.%s.key' % (hmm)
                if os.path.isfile(cert) and os.path.isfile(key):
                    logging.debug('-> found wildcard SSL cert.')
                    return (cert, key)

        # None found, generate a self-signed cert
        # TODO: CACert ?

        # TODO: generate a cert (need root, should be queued)
        return None

        '''
        if not generate:
            return None

        bits = 4096
        days = 3650
        cert_org = 'Tux-FreeHost'

        ssl_dir = '/home/%s/ssl/'%(self.user.username)
        if not os.path.isdir(ssl_dir):
            os.makedirs(ssl_dir)

        logging.debug('-> generating RSA key...')
        subprocess.call(['openssl', 'genrsa', '-out', user_key, str(bits)])
        os.chmod(user_key, 0o400)

        logging.debug('-> generating CSR...')
        subprocess.call(['openssl', 'req', '-new', '-days', str(days),
            '-key', user_key, '-out', user_csr, '-batch',
            '-subj', '/C=FR/O=%s/CN=%s'%(cert_org, self.domains[0].domain)])

        logging.debug('-> generating certificate...')
        subprocess.call(['openssl', 'x509', '-req', '-days', str(days),
            '-in', user_csr, '-signkey', user_key, '-out', user_cert])

        for f in (user_cert, user_csr, user_key):
            subprocess.call(['chown', self.user.username, f])

        return (user_cert, user_key)
        '''


    def on_create(self, settings):
        template = Template(filename=os.path.join(os.path.dirname(__file__),
            '../templates/config/nginx.conf'))
        output_dir = settings.get('nginx.output_dir', './config/nginx/')
        output_filename = os.path.join(output_dir, '%s_%s.conf'%(
            self.user.username, self.name))

        logging.info('VHost #%d: generating nginx config'%(self.id))

        domains = []
        req_verif = settings.get('nginx.require-verified-domains', True)
        for d in self.domains:
            if not req_verif or d.verified:
                domains.append(d)
        if not self.domains:
            logging.warning('VHost #%d: no domain associated. ignoring.'%(self.id))
            return

        pubdir = self.get_public_dir()
        if not pubdir:
            logging.warning('VHost #%d: cannot find public directory. ignoring.'%(self.id))
            return

        apptype = VHost.APP.NONE
        appsocket = None
        appregexp = '/'
        if self.apptype & VHost.APP.PHP:
            sockdir = settings.get('php.sockets_directory', '/var/run/php5-fpm/')
            apptype = VHost.APP.CUSTOM_FCGI
            appsocket = 'unix://%s/%s.sock' % (sockdir, self.user.username)
            appregexp = '\.php$'

            # PHP is used, this user needs a PHP-fpm instance
            php_output_dir = settings.get('php.output_dir', './config/php-fpm/')
            php_output_filename = os.path.join(php_output_dir, '%s.conf'%(
                self.user.username))
            if not os.path.isdir(php_output_dir):
                os.mkdir(php_output_dir)
            if not os.path.isfile(php_output_filename):
                with open(php_output_filename, 'w') as fh:
                    php_template = Template(
                        filename=os.path.join(os.path.dirname(__file__),
                            '../templates/config/phpfpm.conf'))
                    fh.write(php_template.render(
                        user=self.user,
                        socket=appsocket,
                    ))
                # TODO: restart php-fpm
        elif self.apptype & VHost.APP.UWSGI:
            sockdir = settings.get('uwsgi.sockets_directory', '/var/run/uwsgi/')
            apptype = VHost.APP.CUSTOM_WSGI
            appregexp = None
            appsocket = 'unix://%s/app_%s_%s.sock' % (sockdir, self.user.username, self.name)

            if not self.applocation:
                logging.warning('VHost #%d/uwsgi: invalid applocation'%(self.id))
                return
            real_location = '/home/'+self.user.username+'/'+self.applocation
            real_location = os.path.realpath(real_location)
            if not real_location.startswith('/home/'+self.user.username+'/'):
                logging.warning('VHost #%d/uwsgi: applocation is out of user\'s /home'%(self.id))
                return

            # Now with UWSGI we need to make ini files
            uwsgi_output_dir = settings.get('uwsgi.output_dir', './config/uwsgi/')
            uwsgi_output_filename = os.path.join(uwsgi_output_dir, '%s_%s.ini'%(
                self.user.username, self.name))
            if not os.path.isdir(uwsgi_output_dir):
                os.mkdir(uwsgi_output_dir)
            if not os.path.isfile(uwsgi_output_filename):
                with open(uwsgi_output_filename, 'w') as fh:
                    uwsgi_template = Template(
                        filename=os.path.join(os.path.dirname(__file__),
                            '../templates/config/uwsgi.ini'))
                    fh.write(uwsgi_template.render(
                        socket=appsocket,
                        vhost=self,
                        user=self.user,
                        real_location=real_location,
                    ))
                # We do not need to restart anything here, bacause uwsgi will
                # monitor filesystem changes in our config directory.

        # TODO: implement other app types

        addresses = ['127.0.0.1:80', '[::1]:80']
        addresses_in = settings.get('nginx.listen', '').split(',')
        for a in addresses_in:
            a = a.strip()
            if not a:
                continue
            addresses.append(a)

        ssl_cert, ssl_key = None, None
        r = self.get_ssl_certs(settings.get('nginx.gen_ssl', False))
        if r:
            ssl_cert, ssl_key = r

        def write_vhost(fh, **kwargs):
            fh.write(template.render(
                vhost = self,
                pubdir = pubdir,
                domains = domains,
                apptype = apptype,
                appsocket = appsocket,
                appregexp = appregexp,
                listen_addresses = addresses,
                hostnames = ' '.join([d.domain for d in domains]),
                ssl_cert = ssl_cert,
                ssl_key = ssl_key,
                **kwargs
            ))

        if not os.path.isdir(output_dir):
            os.mkdir(output_dir)

        with open(output_filename, 'w') as fh:
            write_vhost(fh)
            if ssl_cert and ssl_key:
                write_vhost(fh, ssl_enable=True)

    def on_update(self, settings):
        self.on_create(settings)

    def on_remove(self, settings):
        files = []

        output_dir = settings.get('nginx.output_dir', './config/nginx/')
        files.append(os.path.join(output_dir, '%s_%s.conf'%(
            self.user.username, self.name)))
        if self.apptype & VHost.APP.PHP:
            d = settings.get('php.output_dir', './config/php-fpm/')
            files.append(os.path.join(d, '%s.conf'%(self.user.username)))
        elif self.apptype & VHost.APP.UWSGI:
            d = settings.get('uwsgi.output_dir', './config/uwsgi/')
            files.append(os.path.join(d, '%s_%s.ini'%(self.user.username, self.name)))

        logging.info('VHost #%d: removing config'%(self.id))
        for f in files:
            if os.path.exists(f):
                os.remove(f)

class VHostRewrite(Base):
    __tablename__ = 'vhostrewrites'
    __display_name__ = 'URL Rewriting Rules'
    __short_name__ = 'rewrite'
    id       = Column(Integer, primary_key=True)
    vhostid  = Column(ForeignKey('vhosts.id'), nullable=False)
    regexp   = Column(String(256), nullable=False)
    dest     = Column(String(256), nullable=False)
    redirect_temp = Column(Boolean, nullable=False, default=False)
    redirect_perm = Column(Boolean, nullable=False, default=False)
    last     = Column(Boolean, nullable=False, default=False)

class VHostACL(Base):
    __tablename__ = 'vhostacls'
    __display_name__ = 'Access Control Lists'
    __short_name__ = 'acl'
    id       = Column(Integer, primary_key=True)
    title    = Column(String(256), nullable=False)
    vhostid  = Column(ForeignKey('vhosts.id'), nullable=False)
    regexp   = Column(String(256), nullable=False)
    passwd   = Column(String(256), nullable=False)

class VHostErrorPage(Base):
    __tablename__ = 'vhosterrorpages'
    __table_args__ = (
        UniqueConstraint('code', 'vhostid'),
    )
    __display_name__ = 'Custom Error Pages'
    __short_name__ = 'ep'
    id       = Column(Integer, primary_key=True)
    vhostid  = Column(ForeignKey('vhosts.id'), nullable=False)
    code     = Column(Integer, nullable=False)
    path     = Column(String(256), nullable=False)


