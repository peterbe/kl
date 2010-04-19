import os
import glob
from django.conf import settings
from django.db import connection, transaction
from django.core.management.base import NoArgsCommand

class Command(NoArgsCommand):
    help = 'Gets the migration job done.'

    def handle_noargs(self, **options):
        cursor = connection.cursor()
        files = sorted(glob.glob(os.path.join(settings.MIGRATIONS_ROOT, '*.sql')))
        alter_db = False
        for fn in files:
            done = '%s.done' % fn
            if not os.path.exists(done):
                f = open(fn, 'r')
                sql = f.read()
                f.close()
                print "Executing: %s" % os.path.split(fn)[1]
                cursor.execute(sql)
                transaction.commit_unless_managed()
                open(done, 'w').close()
                alter_db = True
        if not alter_db:
            print "Up to date, nothing to do."
        else:
            print "Success!"
