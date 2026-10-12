import argparse, getpass, os, sqlite3
from . import server
parser=argparse.ArgumentParser(description='Ecosystem database operations')
sub=parser.add_subparsers(dest='command',required=True)
sub.add_parser('migrate'); sub.add_parser('maintenance')
bootstrap=sub.add_parser('bootstrap'); bootstrap.add_argument('--email',required=True)
backup=sub.add_parser('backup'); backup.add_argument('destination')
args=parser.parse_args(); server.init()
if args.command=='bootstrap':
 password=getpass.getpass('Administrator password (minimum 12 characters): ')
 if password!=getpass.getpass('Repeat password: '): raise SystemExit('Passwords differ')
 print('Created administrator',server.bootstrap(args.email,password))
elif args.command=='backup':
 with server.connect() as source, sqlite3.connect(args.destination) as destination: source.backup(destination)
 os.chmod(args.destination,0o600); print('Backup written')
elif args.command=='maintenance': print(server.maintenance())
else: print('Migrations applied')
