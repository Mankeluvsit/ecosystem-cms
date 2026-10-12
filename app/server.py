import os,json,sqlite3,threading
DB=os.getenv('CMS_DB','cms.sqlite3');LOCK=threading.RLock()
SETTINGS={'site.title':{'kind':'text','default':'Ecosystem CMS'},'chat.retention_days':{'kind':'number','default':30}}
FLAGS={'forum.enabled':{'default':True,'module':'forum'},'chat.enabled':{'default':True,'module':'chat'}}
LABELS={'publish.button':'Publish','site.heading':'Ecosystem CMS'}
ACTIONS={'config.read','config.write','audit.read','forum.read','chat.read'}
ROUTES={'GET /api/registry':'config.read','GET /api/state':'config.read','GET /api/audit':'audit.read','POST /api/change':'config.write','POST /api/undo':'config.write'}
assert all(action in ACTIONS for action in ROUTES.values())
def connect():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;return c
def init():
 with LOCK,connect() as c:
  c.execute('CREATE TABLE IF NOT EXISTS controls(category TEXT,key TEXT,value TEXT,version INTEGER DEFAULT 0,PRIMARY KEY(category,key))')
  c.execute('CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,actor TEXT,category TEXT,key TEXT,old_value TEXT,new_value TEXT,old_version INTEGER,new_version INTEGER,reason TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
  for category,registry in [('settings',SETTINGS),('flags',FLAGS),('labels',LABELS)]:
   for key,meta in registry.items():
    value=meta if category=='labels' else meta['default']
    c.execute('INSERT OR IGNORE INTO controls(category,key,value) VALUES(?,?,?)',(category,key,json.dumps(value)))
def get_state():
 with connect() as c:
  result={'settings':{},'flags':{},'labels':{}}
  for row in c.execute('SELECT * FROM controls'):
   result[row['category']][row['key']]={'value':json.loads(row['value']),'version':row['version']}
  return result
def change(actor,category,key,value,reason,expected_version):
 registries={'settings':SETTINGS,'flags':FLAGS,'labels':LABELS}
 if category not in registries:raise ValueError('UNKNOWN_CATEGORY')
 if key not in registries[category]:raise ValueError('UNDECLARED_CONTROL')
 if category=='flags' and type(value)!=bool:raise ValueError('INVALID_VALUE')
 if category=='labels' and (not isinstance(value,str) or not value.strip()):raise ValueError('INVALID_VALUE')
 if category=='settings':
  kind=SETTINGS[key]['kind']
  if kind=='text' and not isinstance(value,str):raise ValueError('INVALID_VALUE')
  if kind=='number' and (type(value) not in (int,float) or value<0):raise ValueError('INVALID_VALUE')
 if type(expected_version)!=int:raise ValueError('EXPECTED_VERSION_REQUIRED')
 with LOCK,connect() as c:
  row=c.execute('SELECT value,version FROM controls WHERE category=? AND key=?',(category,key)).fetchone()
  if row['version']!=expected_version:raise ValueError('VERSION_CONFLICT')
  version=expected_version+1
  c.execute('UPDATE controls SET value=?,version=? WHERE category=? AND key=?',(json.dumps(value),version,category,key))
  cur=c.execute('INSERT INTO audit(actor,category,key,old_value,new_value,old_version,new_version,reason) VALUES(?,?,?,?,?,?,?,?)',(actor,category,key,row['value'],json.dumps(value),expected_version,version,reason))
  return {'audit_id':cur.lastrowid,'version':version,'value':value}
def undo(actor,audit_id,expected_version):
 with connect() as c:
  row=c.execute('SELECT * FROM audit WHERE id=?',(audit_id,)).fetchone()
  if not row:raise ValueError('UNKNOWN_AUDIT_ID')
  return change(actor,row['category'],row['key'],json.loads(row['old_value']),'undo:'+str(audit_id),expected_version)
