#!/usr/bin/env python

"""
A script for exporting a Coppermine Photo Gallery to a directory structure
"""

from __future__ import print_function

__author__ = "Markus Koskinen at futurice.com"
__license__ = "BSD"

import os
import shutil
import sys

import MySQLdb

_MYSQL_HOST = "localhost"
_MYSQL_USER = "coppermine"
_MYSQL_PASSWORD = "" # Insert your coppermine DB user password here
_MYSQL_DB = "coppermine"

_COPPERMINE_PATH = "/var/www/coppermine"
_TARGET_DIR = "/home/e/emkos/sshfs"

def syntax(execname):
    print("Syntax: %s [coppermine album path]" % execname)
    sys.exit(1)

def main():
    global _COPPERMINE_PATH

    db = MySQLdb.connect(host=_MYSQL_HOST,
                         user=_MYSQL_USER,
                         passwd=_MYSQL_PASSWORD,
                         db=_MYSQL_DB)

    cur = db.cursor()
    cur.execute("""SELECT COUNT(filename) as filecount FROM cpg15x_pictures;""")
    total_files = cur.fetchall()[0]
    cur.close()

    cur = db.cursor()
    cur.execute("""
    SELECT REPLACE(REPLACE(alb.title, " ", "_"), "/", "-") AS albumname, CONCAT(pic.filepath, pic.filename) AS serverpath 
        FROM cpg15x_albums as alb, 
             cpg15x_pictures as pic 
        WHERE pic.aid = alb.aid;
    """)

    if len(sys.argv) == 2:
        _COPPERMINE_PATH = sys.argv[1]

    if not os.path.exists(_TARGET_DIR):
        os.mkdir(_TARGET_DIR)

    print("Coppermine path: %s" % _COPPERMINE_PATH)

    files, dirs = (0, 0)

    print("Expecting %d files. Working..." % total_files)

    for row in cur.fetchall():
        album_name = row[0]

        # Create target dir if it does not exist
        target_dir = _TARGET_DIR + "/" + album_name

        if not os.path.exists(target_dir):
            os.mkdir(target_dir)
            dirs += 1

        source_path = _COPPERMINE_PATH + "/albums/" + row[1]

        shutil.copy2(source_path, target_dir)
        files += 1

        if files > 0:
            print("Copying file: %d" % files, end='\r')

    print("Done. Files: %d New dirs: %d" % (files, dirs))


if __name__ == "__main__":
    if len(sys.argv) not in (1, 2):
        syntax(sys.argv[0])

    main()
