#!/usr/bin/python

import cmd
import string, sys
import boto
import boto.s3.connection
import ConfigParser
import re
import subprocess
import logging
import signal
import datetime

ROOT_LOG = 'deploy_cli'
LOG_filename = '/var/log/deploy_cli'

def signal_handler(signal, frame):
    pass

class s3(object):
    def __init__(self):
        self._LOG = logging.getLogger("%s.%s" % (ROOT_LOG, self.__class__.__name__))
        config = ConfigParser.ConfigParser()
        config.read('/root/.s3cfg')
        self._access_key = config.get('default', 'access_key')
        self._secret_key = config.get('default', 'secret_key')
        self._host = config.get('default', 'host_base')


    def _connect(self):
        self._LOG.debug('connecting to s3')
        connection = boto.connect_s3(aws_access_key_id = self._access_key,
                      aws_secret_access_key = self._secret_key,
                      host = self._host,
                      is_secure = False,
                      )
        return connection


    def get_bucket(self):
       conn = self._connect()

       for bucket in conn.get_all_buckets():
           print "{name}\t{created}".format(
                   name = bucket.name,
                   created = bucket.creation_date
           )
       return conn.get_all_buckets()


    def ls_bucket(self, bucket_name=None, display = True):
       if bucket_name is None:
           bucket_name = 'livrables'

       conn = self._connect()

       bucket = conn.get_bucket(bucket_name)

       keys = [k.name for k in bucket.list()]

       if display:
           for key in sorted(keys):
               print "{name}".format(name = key)

       return sorted(keys)


    def _ls_filtered(self, bucket_name=None, display=False, pattern=None):
        if bucket_name is None:
            bucket_name = 'livrables'

        global_ls = self.ls_bucket(bucket_name = bucket_name, display = False)
        ls_filtered = [k for k in global_ls if k.startswith(pattern)][-10:]

        ls_filtered_tag = self._get_tag(ls_filtered)

        return ls_filtered_tag

    def _get_tag(self, ls_filtered=None):
        ls_tag = []
        for k in ls_filtered:
            regexp = '^.+_([0-9-]+)(\.tar\.gz|\.sql)$'
            match = re.match(regexp, k)
            if match:
                ls_tag.append(match.group(1))
            else:
                self._LOG.error("There is a problem with a tag which doesn't match: %s, please contact eNovance." % (k))
        return ls_tag

    def ls_www(self, bucket_name=None):
        ls_filtered = self._ls_filtered(bucket_name = bucket_name, pattern='www')

        for ls in ls_filtered:
            print ls

    def ls_workers(self, bucket_name=None):
        ls_filtered = self._ls_filtered(bucket_name = bucket_name, pattern='workers')

        for ls in ls_filtered:
            print ls

    def ls_api(self, bucket_name=None):
        ls_filtered = self._ls_filtered(bucket_name = bucket_name, pattern='restapi')

        for ls in ls_filtered:
            print ls

    def ls_admin(self, bucket_name=None):
        ls_filtered = self._ls_filtered(bucket_name = bucket_name, pattern='admin')

        for ls in ls_filtered:
            print ls

    def ls_db(self, bucket_name=None):
        ls_filtered = self._ls_filtered(bucket_name = bucket_name, pattern='db')

        for ls in ls_filtered:
            print ls

class CLI(cmd.Cmd):
    def __init__(self):
        self._LOG = logging.getLogger("%s.%s" % (ROOT_LOG, self.__class__.__name__))
        self._LOG.info('Cli launched')
        cmd.Cmd.__init__(self)
        self.prompt = '> '

        config = ConfigParser.ConfigParser()
        config.read('/root/.deploycli.cfg')
        self._hosts = {}
        self._projects = {}

        for key, name in config.items("hosts"):
            self._hosts[key] = name

        for key, name in config.items("projects"):
            self._projects[key] = name

    def _exec_command(self, command=None):
        result = {}
        self._LOG.info('Exec command: %s' % (command))
        process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                   stderr=None, shell=True)
        result['output'] = process.communicate()
        result['returncode'] = process.wait()
        result['pid_child'] = process.pid

        return result

#        return [line for line in output[0].split("\n") if line != '']

    def _exec_command_puppi(self, project=None, instance=None, tag=None):
        command = r'ssh %s "puppi deploy %s -t -o version=%s"' % (self._hosts[instance], project, tag)
        result = self._exec_command(command=command)

        return result

    def _exec_command_dump(self, instance=None, dbname=None, dump_path='/var/lib/postgresql'):
        if instance in self._hosts:
            date = datetime.datetime.now().strftime("%d-%m-%Y_%I%M")
            filename = 'deploy_cli_backup_%s.bin' % (date)
            self._LOG.info('Dumping database %s for backup, this may take a while...' % (dbname))
            command = '''ssh -t %s \"su - postgres -c 'pg_dump -Fc %s > %s/%s'\"''' % (self._hosts[instance], dbname, dump_path, filename)
            try:
                result = self._exec_command(command=command)
                output = ('%s' % ('\n'.join([result['output'][0]])))
                returncode = result['returncode']
            except IOError as e:
                print e
        else:
            self._LOG.error("Instance name doesn't exist")

        result['filename'] = filename
        return result

    def _exec_command_upload_s3(self, instance=None, dump_path='/var/lib/postgresql', filename=None):
        if filename == None or filename == None:
            self._LOG.error('Error, filename is missing')
        else:
           pass 

    def _deploy(self, arg, project=None, instance=None):
        if arg == '':
            self._LOG.error('Error, you must specify a tag number')
        else:
            self._LOG.info('Deploying %s package on %s instance' % (arg, instance))
            result = self._exec_command_puppi(project=project, instance=instance, tag=arg)
            output = result['output'][0]
            returncode = result['returncode']
            print '\n'.join([output])
            print 'return code: %s' % (result['returncode'])

    def do_get_bucket(self, arg):
        get_bucket = s3()
        get_bucket.get_bucket()

    def do_ls_bucket(self, arg, display = True):
        if arg == '':
            bucket_name = None
        ls_bucket = s3()
        ls_bucket.ls_bucket(bucket_name = bucket_name)

    def do_ls_www(self, arg):
        if arg == '':
            bucket_name = None
        ls_www = s3()
        ls_www.ls_www(bucket_name = bucket_name)

    def do_ls_workers(self, arg):
        if arg == '':
            bucket_name = None
        ls_workers = s3()
        ls_workers.ls_workers(bucket_name = bucket_name)

    def do_ls_api(self, arg):
        if arg == '':
            bucket_name = None
        ls_api = s3()
        ls_api.ls_api(bucket_name = bucket_name)

    def do_ls_admin(self, arg):
        if arg == '':
            bucket_name = None
        ls_admin = s3()
        ls_admin.ls_admin(bucket_name = bucket_name)

    def do_ls_db(self, arg):
        if arg == '':
            bucket_name = None
        ls_db = s3()
        ls_db.ls_db(bucket_name = bucket_name)

    def do_deploy_www(self, arg):
        instance = 'www'
        self._deploy(arg=arg, project=self._projects[instance], instance=instance)

    def do_deploy_workers(self, arg):
        instance = 'workers'
        self._deploy(arg=arg, project=self._projects[instance], instance=instance)

    def do_deploy_api(self, arg):
        instance = 'api'
        self._deploy(arg=arg, project=self._projects[instance], instance=instance)

    def do_deploy_admin(self, arg):
        instance = 'admin'
        self._deploy(arg=arg, project=self._projects[instance], instance=instance)

    def do_deploy_db(self, arg):
        args = arg.split()
        if len(args) != 2:
            self._LOG.error('Missing argument')
            self.help_deploy_db()
        else:
            dbname = args[0]
            tag = args[1]
            result_dump = self._exec_command_dump(dbname=dbname, instance='db_slave')

            if result_dump['returncode'] == 0:
                self._LOG.info('database %s dumped successfully' % (dbname))
                result_upload = self._exec_command_upload_s3(instance='db_slave', filename=result_dump['filename'])
            elif result_dump['returncode'] == 130:
                self._LOG.info('database %s dump aborted' % (dbname))
            else:
                self._LOG.error('database %s dump error:\n%s' % (dbname, result_dump['output']))

#TODO: retrieve upload dump on s3, rm dump, retrieve patch, apply patch...

    def do_quit(self, arg):
        self._LOG.info('Cli exited')
        sys.exit(1)

    def do_exit(self, arg):
        self.do_quit(arg)

    def help_get_bucket(self):
        print "syntax: get_bucket"
        print "List all buckets"

    def help_ls_bucket(self):
        print "syntax: ls_bucket <bucket_name>"
        print "List content of a bucket. (<bucket_name> is optional, default is 'livrables')"

    def help_ls_www(self):
        print "syntax: ls_www"
        print "List the last 10 www package"

    def help_ls_workers(self):
        print "syntax: ls_workers"
        print "List the last 10 workers package"

    def help_ls_api(self):
        print "syntax: ls_api"
        print "List the last 10 api package"

    def help_ls_admin(self):
        print "syntax: ls_admin"
        print "List the last 10 admin package"

    def help_deploy_www(self):
        print "syntax: deploy_www <tag>"
        print "Deploy the www composant with <tag>"

    def help_deploy_admin(self):
        print "syntax: deploy_admin <tag>"
        print "Deploy the admin composant with <tag>"

    def help_deploy_api(self):
        print "syntax: deploy_api <tag>"
        print "Deploy the api composant with <tag>"

    def help_deploy_db(self):
        print "syntax: deploy_db <dbname> <tag>"
        print "Deploy the <tag> patch on <dbname>"

    def help_deploy_workers(self):
        print "syntax: deploy_workers <tag>"
        print "Deploy the workers composant with <tag>"

    def help_help(self):
        print "print this message"

    def help_quit(self):
        print "syntax: quit"
        print "Quit this awesome CLI"


def init_log():
    LOG = logging.getLogger(ROOT_LOG)
    LOG.setLevel(logging.DEBUG)

    handler_file = logging.FileHandler(filename=LOG_filename)
    handler_file.setLevel(logging.DEBUG)

    handler_stream = logging.StreamHandler()
    handler_stream.setLevel(logging.DEBUG)

    formatter_file = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler_file.setFormatter(formatter_file)

    formatter_stream = logging.Formatter('%(message)s')
    handler_stream.setFormatter(formatter_stream)

    LOG.addHandler(handler_file)
    LOG.addHandler(handler_stream)



if __name__ == '__main__':
#TODO: l'argument signal_handler il sort d'ou ? pourquoi c'est pas signal_handler (ma fonction tt en haut)
    signal.signal(signal.SIGINT, signal_handler)

    init_log()

    cli = CLI()
    cli.cmdloop()
