import pymysql
import sys

# Spoof version to satisfy Django 6.0+'s requirements (requires mysqlclient >= 2.2.1)
pymysql.version_info = (2, 3, 0, 'final', 0)
pymysql.install_as_MySQLdb()

# Also set the attributes on the registered MySQLdb module to be absolutely safe
if 'MySQLdb' in sys.modules:
    db = sys.modules['MySQLdb']
    db.version_info = (2, 3, 0, 'final', 0)
    db.__version__ = '2.3.0'
