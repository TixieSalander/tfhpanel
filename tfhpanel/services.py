from .models import DBSession, VHost, User
from mako.template import Template
import os
import logging
import subprocess

class Service(object):
    output_dir = None
    output_file = None
    pidfile = None
    reload_signal = 'SIGHUP'
    appmask = 0xffffffff

    def __init__(self, settings):
        self.settings = settings
        if self.output_dir and not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def clear(self):
        if self.output_dir:
            for f in os.listdir(self.output_dir):
                if f.endswith(self.output_ext):
                    os.remove(self.output_dir+'/'+f)
        elif self.output_file:
            if os.path.isfile(self.output_file):
                os.remove(self.output_file)
            
    def reload(self):
        if self.pidfile:
            process = self.__class__.__name__
            try:
                pid = int(open(self.pidfile).read())
                r = subprocess.call(['kill', '-'+self.reload_signal, str(pid)])
                if r != 0:
                    logging.error('Failed to sent %s to %s!', self.reload_signal, process)
            except FileNotFoundError:
                logging.warning('Pidfile not found for '+process)
    
    def generate_vhost(self, vhost):
        raise NotImplementedError()
        
class NginxService(Service):
    name = 'nginx'

    def __init__(self, output, settings):
        self.output_dir = os.path.join(output, 'nginx')
        self.output_ext = '.conf'
        self.pidfile = settings.get('services.nginx.pidfile', False)
        self.reload_signal = settings.get('services.nginx.signal', 'SIGHUP')
        self.uwsgi_socks = settings.get('services.uwsgi.socks', '/var/lib/uwsgi/')
        self.template = Template(filename=os.path.join(os.path.dirname(__file__), 'templates/config/nginx.conf'))
        self.require_verified_domains = settings.get('require_verified_domains', False)
        self.https_port = settings.get('services.nginx.https_port', 443)
        super().__init__(settings)


    def generate_vhost(self, vhost):
        filename = os.path.join(self.output_dir, '%s_%s.conf'%(
            vhost.user.username, vhost.name))
        fh = open(filename, 'w')
        if len(vhost.domains) < 1:
            logging.warning('vhost#%d/nginx: no domain associated.'%(vhost.id))
            return
        
        pubdir = '/home/%s/http_%s/' % (vhost.user.username, vhost.name)
        oldpubdir = '/home/%s/public_http/' % (vhost.user.username)
        if not os.path.isdir(pubdir):
            if os.path.isdir(oldpubdir):
                # Use ~/public_http
                pubdir = oldpubdir
            elif self.settings.get('services.nginx.make_http_dirs', False):
                os.makedirs(pubdir)
                os.system('chown %s:%s -R %s'%(
                    vhost.user.username, vhost.user.username, pubdir))
        
        appsocket = None
        if vhost.apptype & 0x20: # uwsgi apps
            appsocket = '%s/app_%s_%s.sock' %(self.uwsgi_socks, vhost.user.username, vhost.name)
        
        domains = []
        for d in vhost.domains:
            logging.debug('-> domain: %s'%d.domain)
            if not self.require_verified_domains or d.verified:
                domains.append(d)

        addresses = ['127.0.0.1', '::1']
        addresses_in = self.settings.get('services.nginx.listen', '').split(',')
        for a in addresses_in:
            a = a.strip()
            if not a:
                continue
            addresses.append(a)

        ssl_enable = False
        ssl_cert = None
        ssl_key = None
        r = self.get_ssl_certs(vhost)
        if r:
            ssl_cert, ssl_key = r
            ssl_enable = True

        fh.write(self.template.render(
            listen_addr = addresses,
            user = vhost.user.username,
            name = vhost.name,
            ssl_enable = ssl_enable,
            ssl_port = self.https_port, 
            ssl_cert = ssl_cert,
            ssl_key = ssl_key,
            pubdir = pubdir,
            hostnames = ' '.join([d.domain for d in domains]),
            autoindex = vhost.autoindex,
            catchall = vhost.catchall,
            rewrites = vhost.rewrites,
            error_pages = vhost.errorpages,
            acl = vhost.acls,
            apptype = vhost.apptype,
            appsocket = appsocket,
            applocation = vhost.applocation,
        ))
        
        if ssl_enable:
            # Add the same vhost without SSL
            fh.write(self.template.render(
                listen_addr = addresses,
                user = vhost.user.username,
                name = vhost.name,
                ssl_enable = False,
                ssl_port = self.https_port,
                ssl_cert = None,
                ssl_key = None,
                pubdir = pubdir,
                hostnames = ' '.join([d.domain for d in vhost.domains]),
                autoindex = vhost.autoindex,
                catchall = vhost.catchall,
                rewrites = vhost.rewrites,
                error_pages = vhost.errorpages,
                acl = vhost.acls,
                apptype = vhost.apptype,
                appsocket = appsocket,
                applocation = vhost.applocation,
            ))
        fh.close()
    
    def get_ssl_certs(self, vhost):
        # User-provided SSL cert
        base = '/home/%s/ssl/%s' % (vhost.user.username, vhost.name)
        user_cert, user_csr, user_key = base+'.crt', base+'.csr', base+'.key'
        if os.path.isfile(user_cert) and os.path.isfile(user_key):
            logging.debug('-> found user SSL cert.')
            return (user_cert, user_key)
        
        # System-wide wildcard
        for domain in vhost.domains:
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

        if not self.settings.get('services.nginx.gen_ssl', False):
            return None

        bits = 4096
        days = 3650
        cert_org = 'Tux-FreeHost'
        
        ssl_dir = '/home/%s/ssl/'%(vhost.user.username)
        if not os.path.isdir(ssl_dir):
            os.makedirs(ssl_dir)

        logging.debug('-> generating RSA key...')
        subprocess.call(['openssl', 'genrsa', '-out', user_key, str(bits)])
        os.chmod(user_key, 0o400)

        logging.debug('-> generating CSR...')
        subprocess.call(['openssl', 'req', '-new', '-days', str(days),
            '-key', user_key, '-out', user_csr, '-batch',
            '-subj', '/C=FR/O=%s/CN=%s'%(cert_org, vhost.domains[0].domain)])
        
        logging.debug('-> generating certificate...')
        subprocess.call(['openssl', 'x509', '-req', '-days', str(days),
            '-in', user_csr, '-signkey', user_key, '-out', user_cert])
        
        for f in (user_cert, user_csr, user_key):
            subprocess.call(['chown', vhost.user.username, f])
        
        return (user_cert, user_key)

    
class UwsgiService(Service):
    name = 'uwsgi'
    appmask = 0x20

    def __init__(self, output, settings):
        self.output_dir = os.path.join(output, 'uwsgi')
        self.output_ext = '.ini'
        self.uwsgi_socks = settings.get('services.uwsgi-socks', '/var/lib/uwsgi/')
        self.template = Template(filename=os.path.join(os.path.dirname(__file__), 'templates/config/uwsgi.ini'))
        super().__init__(settings)

    def generate_vhost(self, vhost):
        filename = os.path.join(self.output_dir, '%s_%s.ini'%(
            vhost.user.username, vhost.name))

        if not vhost.applocation:
            logging.debug('vhost#%d/uwsgi: not applocation' % vhost.id)
            return

        real_location = '/home/'+vhost.user.username+'/'+vhost.applocation
        real_location = os.path.realpath(real_location)
        if not real_location.startswith('/home/'+vhost.user.username+'/'):
            logging.warning('vhost#%d/uwsgi: uwsgi app trying to get out its of /home' % vhost.id)
            return

        logging.info('-> uwsgi app')
        fh = open(filename, 'w')
        fh.write(self.template.render(
            vhost=vhost,
            user=vhost.user,
            real_location=real_location,
            sockdir=self.uwsgi_socks,
        ))
        fh.close()
        
    def remove_vhost(self, vhost):
        filename = self.output_dir + '/%s_%s.ini'%(
            vhost.user.username, vhost.name)
        if os.path.isfile(filename):
            os.remove(filename)
        
class PhpfpmService(Service):
    name = 'php'
    appmask = 0x10

    def __init__(self, output, settings):
        self.output_dir = os.path.join(output, 'php-fpm')
        self.output_ext = '.conf'
        self.pidfile = settings.get('services.php.pidfile', None)
        self.reload_signal = settings.get('services.php.signal', 'SIGUSR2')
        self.template = Template(filename=os.path.join(os.path.dirname(__file__), 'templates/config/phpfpm.conf'))
        super().__init__(settings)

    def generate_vhost(self, vhost):
        filename = os.path.join(self.output_dir, '%s.conf'%(vhost.user.username))
        # Never need to be changed, only created/deleted
        if os.path.isfile(filename):
            return
        logging.info('-> php for '+vhost.user.username)
        fh = open(filename, 'w')
        fh.write(self.template.render(user=vhost.user.username))
        fh.close()

    def remove_vhost(self, vhost):
        filename = self.output_dir + '%s.conf'%(vhost.user.username)
        if os.path.isfile(filename):
            os.remove(filename)



class ConfigFile(object):
    ''' Base config file class '''

    filename = None
    mode = 0o600
    @classmethod
    def generate(cls, settings):
        raise NotImplementedError()

class DovecotSQLConf(ConfigFile):
    filename = 'dovecot-sql.conf'
    mode = 0o600

    @classmethod
    def generate(cls, settings):
        tpl = Template(filename=os.path.dirname(__file__)+'/templates/config/dovecot-sql.conf')
        return tpl.render(
            host=DBSession.bind.url.host, db=DBSession.bind.url.database,
            user=DBSession.bind.url.username, password=DBSession.bind.url.password,
            passwdscheme=settings.get('password-scheme', 'SHA512-CRYPT'),
        )

class PostfixConfigFile(ConfigFile):
    ''' Postfix .cf base class '''

    filename = None
    mode = 0o600

    @classmethod
    def generate(cls, settings):
        output = 'hosts = %s\n' % DBSession.bind.url.host
        output+= 'user = %s\n' % DBSession.bind.url.username
        output+= 'password = %s\n' % DBSession.bind.url.password or ''
        output+= 'dbname = %s\n' % DBSession.bind.url.database
        output+= 'query = %s\n' % (cls.query.replace('\n', ' '))
        return output

class PostfixDomainsConf(PostfixConfigFile):
    filename = 'postfix/domains.cf'
    query = '''
        SELECT '%s' AS output FROM mailboxes
        LEFT JOIN domains ON domains.id = mailboxes.domainid
        WHERE domain='%s' LIMIT 1;
    '''

class PostfixBoxesConf(PostfixConfigFile):
    filename = 'postfix/boxes.cf'
    query = '''
        SELECT '%d/%u' FROM mailboxes
        LEFT JOIN domains ON domains.id = mailboxes.domainid
        WHERE local_part='%u' AND domain='%d' AND redirect IS NULL
    '''

class PostfixAliasesConf(PostfixConfigFile):
    filename = 'postfix/aliases.cf'
    query = '''
        SELECT redirect FROM mailboxes
        LEFT JOIN domains ON domains.id = mailboxes.domainid
        WHERE (
            local_part='%u' AND domain='%d' AND redirect IS NOT NULL
        ) OR (
            local_part IS NULL AND domain='%d' AND redirect IS NOT NULL AND (
                SELECT COUNT(*) FROM mailboxes
                LEFT JOIN domains ON domains.id = mailboxes.domainid
                WHERE local_part='%u' AND domain='%d'
            ) = 0
        )
    '''

class PAMPgSQLConf(ConfigFile):
    filename = 'pam_pgsql.conf'
    mode = 0o600

    @classmethod
    def generate(cls, settings):
        tpl = Template(filename=os.path.dirname(__file__)+'/templates/config/pam_pgsql.conf')
        return tpl.render(
            host=DBSession.bind.url.host, db=DBSession.bind.url.database,
            user=DBSession.bind.url.username, password=DBSession.bind.url.password,
        )
    
class NSSPgSQLConf(ConfigFile):
    filename = 'nss-pgsql.conf'
    
    # passwd db need to be readable by every user.
    # tfh_node_passwd should only be able to read needed columns on that table
    mode = 0o644

    @classmethod
    def generate(cls, settings):
        tpl = Template(filename=os.path.dirname(__file__)+'/templates/config/nss-pgsql.conf')
        return tpl.render(
            host=DBSession.bind.url.host, db=DBSession.bind.url.database,
            user='tfh_node_passwd', password='passwdfile',
        )
        os.chmod(output, 0o644)

class NSSPgSQLRootConf(ConfigFile):
    filename = 'nss-pgsql-root.conf'
    mode = 0o600

    @classmethod
    def generate(cls, settings):
        tpl = Template(filename=os.path.dirname(__file__)+'/templates/config/nss-pgsql-root.conf')
        return tpl.render(
            host=DBSession.bind.url.host, db=DBSession.bind.url.database,
            user=DBSession.bind.url.username, password=DBSession.bind.url.password,
        )


