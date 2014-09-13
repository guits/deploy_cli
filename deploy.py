#!/usr/bin/python

import cmd
import string, sys
import boto
import boto.s3.connection
import ConfigParser
import re
import subprocess

class s3(object):
    def __init__(self):
        config = ConfigParser.ConfigParser()
        config.read('/root/.s3cfg')
        self._access_key = config.get('default', 'access_key')
        self._secret_key = config.get('default', 'secret_key')
        self._host = config.get('default', 'host_base')


    def _connect(self):
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


    def ls_filtered(self, bucket_name=None, display=False, pattern=None):
        if bucket_name is None:
            bucket_name = 'livrables'

        global_ls = self.ls_bucket(bucket_name = bucket_name, display = False)
        ls_filtered = [k for k in global_ls if k.startswith(pattern)][-10:]

        ls_filtered_tag = self.get_tag(ls_filtered)

        return ls_filtered_tag

    def get_tag(self, ls_filtered=None):
        ls_tag = []
        for k in ls_filtered:
            regexp = '^.*_([0-9-]*)\.tar\.gz$'
            match = re.match(regexp, k)
            if match:
                ls_tag.append(match.group(1))
            else:
                "There is a problem with a tag which doesn't match, please contact eNovance."
        return ls_tag

    def ls_www(self, bucket_name=None):
        ls_filtered = self.ls_filtered(bucket_name = bucket_name, pattern='www')

        for ls in ls_filtered:
            print ls

    def ls_workers(self, bucket_name=None):
        ls_filtered = self.ls_filtered(bucket_name = bucket_name, pattern='workers')

        for ls in ls_filtered:
            print ls

    def ls_api(self, bucket_name=None):
        ls_filtered = self.ls_filtered(bucket_name = bucket_name, pattern='restapi')

        for ls in ls_filtered:
            print ls

class CLI(cmd.Cmd):
    def __init__(self):
        cmd.Cmd.__init__(self)
        self.prompt = '> '

        config = ConfigParser.ConfigParser()
        config.read('/root/.deploycli.cfg')
        self._hosts = {}
        for key, name in config.items("hosts"):
            self._hosts[key] = name

    def _exec_command(self, project=None, instance=None, tag=None):
        process = subprocess.Popen(r'ssh %s "puppi deploy %s -t -o version=%s"' % (self._hosts[instance], project, tag),
                                   stdout=subprocess.PIPE,
                                   stderr=None, shell=True)
        output = process.communicate()

        return [line for line in output[0].split("\n") if line != '']

    def _print_exec_output(self, output=None):
        for k in output:
            print k

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

    def do_deploy_www(self, arg):
        if arg == '':
            print 'Error, you must specify a tag number'
        else:
            print 'Deploying %s package' % (arg)
            output = self._exec_command(project='cinemur', instance='www', tag=arg)
            self._print_exec_output(output=output)

    def do_deploy_workers(self, arg):
        if arg == '':
            print 'Error, you must specify a tag number'
        else:
            print 'Deploying %s package' % (arg)
            output = self._exec_command(project='cinemur', instance='workers', tag=arg)
            self._print_exec_output(output=output)

    def do_deploy_api(self, arg):
        if arg == '':
            print 'Error, you must specify a tag number'
        else:
            print 'Deploying %s package' % (arg)
            output = self._exec_command(project='cinemur', instance='api', tag=arg)
            self._print_exec_output(output=output)

    def do_deploy_admin(self, arg):
        if arg == '':
            print 'Error, you must specify a tag number'
        else:
            print 'Deploying %s package' % (arg)
            output = self._exec_command(project='cinemur-admin', instance='www', tag=arg)
            self._print_exec_output(output=output)

    def do_quit(self, arg):
        sys.exit(1)

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

    def help_deploy_www(self):
        print "syntax: deploy_www <tag>"
        print "Deploy the www composant with <tag>"

    def help_quit(self):
        print "syntax: quit"
        print "Quit this awesome CLI"


if __name__ == '__main__':
    cli = CLI()
    cli.cmdloop()
