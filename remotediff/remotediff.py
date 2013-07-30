#!/usr/bin/env python
'''
Check filesystem/ownership/permission/size differences in remote/local paths.
'''

import argparse
import os
import sqlite3
import subprocess
import sys

from pprint import pprint as pp

__author__ = "Sury Prakash Soni"
__copyright__ = "Copyright 2013"
__license__ = "MIT"
__version__ = "0.1.dev"
__maintainer__ = "Sury Prakash Soni"
__email__ = "suryasoni@gmail.com"
__status__ = "Development"

class ListPrinter:


    def __init__(self, args):
        self.args = args

    def pp(self, name, obj):
        print(name)
        pp(obj[:3])

    def export(self, name, obj, prefix=''):
        if self.args.debug:
            self.pp(name, obj)
        else:
            if self.args.quiet:
                print('\n'.join(obj))
            else:
                print(prefix + ('\n' + prefix).join(obj))

class DB:


    def __init__(self, create, insert, debug=False):
        name = 'db.sdb' if debug else ':memory:'
        #name = ':memory:'
        self.conn = sqlite3.connect(name)
        self.conn.text_factory = str
        self.create = create
        self.insert = insert

    def dump(self, name, rows):
        c = self.conn.cursor()
        c.execute(self.create.format(name))
        c.executemany(self.insert.format(name), rows)
        self.conn.commit()

    def _only(self, A, B):
        sql = '''
            select 
                path 
            from 
                {0} 
            where 
                path not in (select path from {1})'''.format(A, B)
        c = self.conn.cursor()
        c.execute(sql)
        return [d[0] for d in c.fetchall()]
    
    def only_a(self):
        return self._only('A', 'B')

    def only_b(self):
        return self._only('B', 'A')

    def _common(self, filter='1'):
        sql = '''
            select 
                A.path 
            from 
                A,B 
            where 
                A.path = B.path and ({0})'''.format(filter)
        c = self.conn.cursor()
        c.execute(sql)
        return [d[0] for d in c.fetchall()]

    def common(self):
        return self._common()

    def diff_any(self):
        filter = '''
            A.perm != B.perm or A.sz != B.sz or A.ft != B.ft or A.usr != B.usr
        '''
        return self._common(filter)

    def diff_owner(self):
        return self._common('A.usr != B.usr or A.grp != B.grp')

    def diff_perms(self):
        return self._common('A.perm != B.perm')

    def diff_size(self):
        return self._common('A.perm != B.perm')

def get_data(src):
    if '@' in src and ':' in src:
        cmd = r'ssh {0} '.format(src.split(':')[0])
        src = src.split(':')[1]
        cmd += r'find {0} -xdev -printf \'%P\\t%y\\t%u\\t%g\\t%m\\t%s\\n\' 2>/dev/null'.format(src)
    else:
        cmd = r'find {0} -xdev -printf "%P\t%y\t%u\t%g\t%m\t%s\n" 2>/dev/null'.format(src)

    def conv(line):
        p = line.split('\t')
        try:
            return {
                'path':p[0], 'ft':p[1], 'usr':p[2], 'grp':p[3], 'perm':p[4], 
                'sz':p[5]
            }
        except:
            pp(line)
            raise
    
    try:
        data = subprocess.check_output(cmd, shell=True)
    except subprocess.CalledProcessError as e:
        data = e.output
        raise e

    # Skip first line of data because %P would not produce path in first line.
    return map(conv, data.strip().decode().split('\n')[1:])

def diff(args):
    lp = ListPrinter(args)

    create = '''
        create table {0} 
        (
            path varchar(255), 
            ft varchar(2), 
            usr varchar(50), 
            grp varchar(50), 
            perm varchar(5), 
            sz varchar(50)
        );'''
    insert = 'insert into {0} values (:path,:ft,:usr,:grp,:perm,:sz);'
    
    db = DB(create, insert, args.debug)
    db.dump('A', get_data(args.path1))
    db.dump('B', get_data(args.path2))

    # Get path level diff, only a, only b and common
    if 1 not in args.supps:
        lp.export('only a', db.only_a(), '< ')
        lp.export('only b', db.only_b(), '> ')
        lp.export('common', db.common(), '= ')
    
    # Get ownership diff (user, group)
    if 2 not in args.supps:
        lp.export('diff owner', db.diff_owner(), '<o> ')
    
    # Get access diff (rwx for users, groups and others)
    if 3 not in args.supps:
        lp.export('diff perm', db.diff_perms(), '<p> ')
    
    # Get file size diff
    if 4 not in args.supps:
        lp.export('diff size', db.diff_size(), '<s> ')

def check_params(args):
    def check_remote_path(path):
        # Basic check for remote path to keep the code simple
        return '@' in path and not path.startswith('@') and len(path) > 3

    def check_local_path(path):
        return os.path.exists(path)

    # Check src1 and src2 for path validity
    for path in (args.path1, args.path2):
        if not any([check_remote_path(path), check_local_path(path)]):
            print('Incorrect path: {0}'.format(path))
            return False

    return True

def do_parser_stuff():
    parser = argparse.ArgumentParser()

    # Setup optional parameters
    parser.add_argument('-d', '--debug', help='debug only', dest='debug', 
        action='store_true', default=False)
    parser.add_argument('-q', '--quiet', help='quiet output', dest='quiet', 
        action='store_true', default=False)
    parser.add_argument('-1', help='supress path diffs', default=list(), 
        dest='supps', action='append_const', const=1)
    parser.add_argument('-2', help='supress ownership diffs (user, group)', 
        dest='supps', action='append_const', const=2)
    parser.add_argument('-3', help=
        'supress access diffs (rwx for users, groups and others)', 
        dest='supps', action='append_const', const=3)
    parser.add_argument('-4', help='supress file size diffs', dest='supps', 
        action='append_const', const=4)

    # Setup required parameters
    parser.add_argument('path1', help='local or remote path')
    parser.add_argument('path2', help='local or remote path')

    args = parser.parse_args()

    # Parameters path1 and path2 are mandatory
    if not (args.path1 and args.path2):
        print('Arguments path1 and path2 are mandatory.\n')
        parser.print_help()
        exit(-1)

    if not check_params(args):
        parser.print_help()
        exit(-1)
    
    return args

if __name__ == '__main__':
    args = do_parser_stuff()
    diff(args)
