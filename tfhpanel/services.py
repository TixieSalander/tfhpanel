from mako.template import Template
import os
import logging
import subprocess

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


