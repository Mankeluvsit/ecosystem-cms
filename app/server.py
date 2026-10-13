"""SQLite services. HTTP authorization lives at the registered-route boundary."""
import os, json, sqlite3, threading, time, secrets, hashlib, hmac, re, base64, io
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
try:
 from .registry import SETTINGS, FLAGS, LABELS, ACTIONS, ROLES, LABEL_REFINEMENTS
except ImportError:
 from registry import SETTINGS, FLAGS, LABELS, ACTIONS, ROLES, LABEL_REFINEMENTS
try:
 from . import themes
except ImportError:
 import themes
DB = os.getenv('CMS_DB', 'cms.sqlite3')
LOCK = threading.RLock()
class Fault(ValueError):
 def __init__(self, code, status=400): self.code, self.status = code, status; super().__init__(code)
def fail(code, status=400): raise Fault(code, status)
def now(): return datetime.now(timezone.utc).isoformat()
def connect():
 c=sqlite3.connect(DB, timeout=15); c.row_factory=sqlite3.Row
 c.execute('PRAGMA foreign_keys=ON'); c.execute('PRAGMA busy_timeout=15000'); return c
@contextmanager
def transaction():
 with LOCK, connect() as c:
  c.execute('BEGIN IMMEDIATE'); yield c
  c.commit()
def init():
 with LOCK, connect() as c:
  c.execute('PRAGMA journal_mode=WAL')
  c.execute('CREATE TABLE IF NOT EXISTS schema_migrations(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)')
  for path in sorted((Path(__file__).parent/'migrations').glob('*.sql')):
   if not c.execute('SELECT 1 FROM schema_migrations WHERE version=?',(path.name,)).fetchone():
    c.executescript('BEGIN IMMEDIATE;\n'+path.read_text()+"\nINSERT INTO schema_migrations VALUES ('"+path.name+"','"+now()+"');\nCOMMIT;")
  for role in ROLES: c.execute('INSERT OR IGNORE INTO roles VALUES(?)',(role,))
  for key,meta in ACTIONS.items(): c.execute('INSERT OR IGNORE INTO actions VALUES(?,?,?)',(key,meta['module'],meta['description']))
  for category,registry in [('settings',SETTINGS),('flags',FLAGS),('labels',LABELS),('permissions',{r:sorted(v) for r,v in ROLES.items()})]:
   for key,meta in registry.items():
    value=meta if category in ('labels','permissions') else meta['default']
    c.execute('INSERT OR IGNORE INTO controls(category,key,value) VALUES(?,?,?)',(category,key,json.dumps(value)))
  c.execute('INSERT OR IGNORE INTO content_types VALUES(?,?,0)',('page','{}'))
  c.execute('INSERT OR IGNORE INTO categories(id,name) VALUES(1,?)',('General',))
  c.execute('INSERT OR IGNORE INTO rooms(id,name) VALUES(1,?)',('General',))
  if not c.execute("SELECT 1 FROM schema_migrations WHERE version='003_readable_labels'").fetchone():
   for key,(old,new) in LABEL_REFINEMENTS.items():
    row=c.execute("SELECT * FROM controls WHERE category='labels' AND key=?",(key,)).fetchone()
    if row and row['version']==0 and json.loads(row['value'])==old:
     _change(c,'system','labels',key,new,'updated interface wording',0)
   c.execute('INSERT INTO schema_migrations VALUES(?,?)',('003_readable_labels',now()))
def record(c, actor, category, key, old, new, reason, old_version=None, new_version=None):
 return c.execute('INSERT INTO audit(actor,category,key,old_value,new_value,old_version,new_version,reason) VALUES(?,?,?,?,?,?,?,?)', (str(actor),category,str(key),json.dumps(old),json.dumps(new),old_version,new_version,reason)).lastrowid
def get_state(c=None):
 if c is None:
  with connect() as conn: return get_state(conn)
 result={k:{} for k in ('settings','flags','labels','permissions')}
 for row in c.execute('SELECT * FROM controls'): result[row['category']][row['key']]={'value':json.loads(row['value']),'version':row['version']}
 return result
def value(c, category, key):
 return json.loads(c.execute('SELECT value FROM controls WHERE category=? AND key=?',(category,key)).fetchone()[0])
def text(v, minimum=1, maximum=10000):
 if not isinstance(v,str) or len(v.strip())<minimum or len(v)>maximum: fail('INVALID_VALUE')
 return v.strip()
def integer(v, minimum=1, maximum=2147483647):
 if type(v)!=int or not minimum<=v<=maximum: fail('INVALID_VALUE')
 return v
def identifier(v):
 if not isinstance(v,str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}',v): fail('INVALID_IDENTIFIER')
 return v
def version(row, expected):
 if type(expected)!=int: fail('EXPECTED_VERSION_REQUIRED')
 if row['version']!=expected: fail('VERSION_CONFLICT',409)
def validate_control(category,key,v):
 registries={'settings':SETTINGS,'flags':FLAGS,'labels':LABELS,'permissions':ROLES}
 if category not in registries: fail('UNKNOWN_CATEGORY')
 if key not in registries[category]: fail('UNDECLARED_CONTROL')
 if category=='settings':
  meta=SETTINGS[key]; limits=meta['validate']
  if key=='appearance.theme':
   try: themes.validate(v)
   except (ValueError,TypeError) as error:
    code=str(error)
    fail(code if code in ('INVALID_THEME','THEME_LIGHT_SURFACES_REQUIRED','THEME_CONTRAST_TOO_LOW') else 'INVALID_THEME')
  elif meta['kind']=='number': integer(v,limits['min'],limits['max'])
  else: text(v,limits['min'],limits['max'])
 elif category=='flags':
  if type(v)!=bool: fail('INVALID_VALUE')
 elif category=='labels': text(v,1,1000)
 else:
  if not isinstance(v,list) or len(v)!=len(set(v)) or any(x not in ACTIONS or ACTIONS[x]['public'] for x in v): fail('INVALID_SCOPES')
  if key=='admin' and not {'auth.permissions.write','auth.users.write','auth.session','config.read','config.write','admin.read'}.issubset(v): fail('ADMIN_RECOVERY_PERMISSIONS_REQUIRED')
def _change(c,actor,category,key,v,reason,expected_version):
 validate_control(category,key,v); text(reason,1,500)
 if category=='settings' and key=='public.news_category' and v and not c.execute('SELECT 1 FROM categories WHERE id=?',(v,)).fetchone(): fail('NEWS_CATEGORY_NOT_FOUND')
 row=c.execute('SELECT * FROM controls WHERE category=? AND key=?',(category,key)).fetchone(); version(row,expected_version)
 new_version=expected_version+1
 c.execute('UPDATE controls SET value=?,version=? WHERE category=? AND key=?',(json.dumps(v),new_version,category,key))
 audit_id=record(c,actor,category,key,json.loads(row['value']),v,reason,expected_version,new_version)
 return {'audit_id':audit_id,'version':new_version,'value':v}
def change(actor,category,key,value,reason,expected_version):
 with transaction() as c: return _change(c,actor,category,key,value,reason,expected_version)
def undo(actor,audit_id,expected_version):
 with transaction() as c:
  row=c.execute('SELECT * FROM audit WHERE id=?',(integer(audit_id),)).fetchone()
  if not row: fail('UNKNOWN_AUDIT_ID',404)
  if row['category'] not in ('settings','flags','labels','permissions'): fail('UNDO_NOT_SUPPORTED')
  current=c.execute('SELECT version FROM controls WHERE category=? AND key=?',(row['category'],row['key'])).fetchone()
  if current['version']!=row['new_version']: fail('UNDO_STALE',409)
  return _change(c,actor,row['category'],row['key'],json.loads(row['old_value']),'undo:'+str(audit_id),expected_version)
def digest(token): return hashlib.sha256(token.encode()).hexdigest()
def password_hash(password):
 text(password,12,256); salt=secrets.token_bytes(16)
 return salt.hex()+':'+hashlib.scrypt(password.encode(),salt=salt,n=16384,r=8,p=1).hex()
def check_password(password,stored):
 if not isinstance(password,str) or len(password)>256: return False
 salt,hashed=stored.split(':'); result=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
 return hmac.compare_digest(result,hashed)
def email_address(email):
 email=text(email,3,254).lower()
 if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email): fail('INVALID_EMAIL')
 return email
def bootstrap(email,password):
 with transaction() as c:
  if c.execute('SELECT 1 FROM users').fetchone(): fail('ALREADY_INITIALIZED',409)
  uid=c.execute('INSERT INTO users(email,password_hash,role,created_at) VALUES(?,?,?,?)',(email_address(email),password_hash(password),'admin',now())).lastrowid
  record(c,'bootstrap','auth','users',None,{'id':uid,'role':'admin'},'initial administrator')
  return uid
def rate(c,key,limit,seconds=60):
 window=int(time.time())//seconds
 c.execute('DELETE FROM rate_buckets WHERE window<?',(int(time.time())//seconds-2,)) if seconds==60 else None
 c.execute('INSERT INTO rate_buckets VALUES(?,?,1) ON CONFLICT(key,window) DO UPDATE SET count=count+1',(key,window))
 return c.execute('SELECT count FROM rate_buckets WHERE key=? AND window=?',(key,window)).fetchone()[0]<=limit
def login(email,password,ip):
 email=email_address(email)
 with transaction() as c:
  allowed=rate(c,'login-ip:'+ip,10,60) and rate(c,'login-email:'+digest(email),30,60)
 if not allowed: fail('RATE_LIMITED',429)
 with transaction() as c:
  row=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
  # Equal work for missing accounts, without logging submitted credentials.
  stored=row['password_hash'] if row else ('00'*16+':'+'00'*64)
  valid=check_password(password,stored)
  if not row or not row['active'] or not valid:
   record(c,'anonymous','auth','login',None,{'success':False},'login rejected')
   result=None
  else:
   token=secrets.token_urlsafe(32); csrf=secrets.token_urlsafe(32); expiry=int(time.time())+43200
   c.execute('DELETE FROM sessions WHERE expires_at<?',(int(time.time()),))
   c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(digest(token),row['id'],csrf,expiry))
   record(c,row['id'],'auth','login',None,{'success':True},'session created')
   result={'token':token,'csrf':csrf,'user':{'id':row['id'],'email':row['email'],'role':row['role']}}
 if result is None: fail('INVALID_CREDENTIALS',401)
 return result
def identity(token,is_key=False):
 if not token: return None
 with connect() as c:
  if is_key:
   row=c.execute('SELECT u.id,u.email,u.role,k.id AS key_id,k.scopes FROM api_keys k JOIN users u ON u.id=k.user_id WHERE k.token_hash=? AND k.revoked=0 AND k.expires_at>? AND u.active=1',(digest(token),int(time.time()))).fetchone()
  else:
   row=c.execute('SELECT u.id,u.email,u.role,s.csrf FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>? AND u.active=1',(digest(token),int(time.time()))).fetchone()
  return dict(row) if row else None
def permissions(user,c=None):
 if c is None:
  with connect() as conn: return permissions(user,conn)
 allowed=set(value(c,'permissions',user['role']))
 if 'scopes' in user: allowed &= set(json.loads(user['scopes']))
 return allowed
def require(user,action):
 if ACTIONS[action]['public']: return
 if not user: fail('UNAUTHENTICATED',401)
 if action not in permissions(user): fail('PERMISSION_DENIED',403)
def module(c,name):
 if not value(c,'flags',name+'.enabled'): fail('MODULE_DISABLED',403)
def row_for(c,table,id):
 row=c.execute('SELECT * FROM '+table+' WHERE id=?',(integer(id),)).fetchone()
 if not row: fail('NOT_FOUND',404)
 return row
def clean_fields(c,type_id,fields):
 row=c.execute('SELECT fields FROM content_types WHERE id=?',(type_id,)).fetchone()
 if not row: fail('UNKNOWN_CONTENT_TYPE')
 schema=json.loads(row['fields'])
 if not isinstance(fields,dict) or set(fields)!=set(schema): fail('INVALID_FIELDS')
 for k,kind in schema.items():
  if kind=='text': text(fields[k],0,10000)
  elif kind=='number':
   if type(fields[k]) not in (int,float) or not (-1e12<=fields[k]<=1e12): fail('INVALID_FIELDS')
  elif type(fields[k])!=bool: fail('INVALID_FIELDS')
 return json.dumps(fields)
def snapshot(c,id,actor):
 row=dict(row_for(c,'entries',id)); row['media_ids']=[r[0] for r in c.execute('SELECT media_id FROM media_references WHERE entry_id=?',(id,))]
 c.execute('INSERT INTO revisions(entry_id,snapshot,actor,created_at) VALUES(?,?,?,?)',(id,json.dumps(row),str(actor),now()))
def references(c,id,ids):
 if not isinstance(ids,list) or len(ids)>100: fail('INVALID_REFERENCES')
 for mid in ids: row_for(c,'media',mid)
 c.execute('DELETE FROM media_references WHERE entry_id=?',(id,))
 for mid in set(ids): c.execute('INSERT INTO media_references VALUES(?,?)',(id,mid))
def maintenance():
 with transaction() as c:
  timestamp=int(time.time()); days=value(c,'settings','chat.retention_days')
  count=c.execute('DELETE FROM messages WHERE created_at<?',(timestamp-days*86400,)).rowcount
  c.execute('DELETE FROM presence WHERE seen_at<?',(timestamp-90,))
  c.execute('DELETE FROM sessions WHERE expires_at<?',(timestamp,))
  if count: record(c,'system','chat','retention',None,{'deleted':count,'days':days},'retention applied')
  scheduled=c.execute("SELECT * FROM entries WHERE status='scheduled' AND publish_at<=?",(timestamp,)).fetchall()
  for row in scheduled:
   snapshot(c,row['id'],'system')
   c.execute("UPDATE entries SET status='published',version=version+1,updated_at=? WHERE id=?",(now(),row['id']))
   record(c,'system','content',row['id'],{'status':'scheduled'},{'status':'published'},'scheduled publication',row['version'],row['version']+1)
 return {'deleted':count,'published':len(scheduled)}
def media_image(raw):
 from PIL import Image, UnidentifiedImageError
 try:
  with Image.open(io.BytesIO(raw)) as im:
   if im.format not in ('PNG','JPEG','GIF','WEBP') or im.width*im.height>25000000: fail('UNSUPPORTED_IMAGE')
   im.verify()
  with Image.open(io.BytesIO(raw)) as im:
   im.seek(0); im=im.convert('RGBA'); out=io.BytesIO(); im.save(out,format='PNG')
   return out.getvalue(),im.width,im.height
 except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError) as e:
  if isinstance(e,Fault): raise
  fail('INVALID_IMAGE')
def public_news(c,id=None):
 """Only approved top-level posts from the explicitly selected public category."""
 category=value(c,'settings','public.news_category')
 if not category or not value(c,'flags','forum.enabled'):
  if id is not None: fail('NOT_FOUND',404)
  return []
 columns='t.id,t.title,t.body,t.published_at,t.created_at AS posted_at,c.name AS category'
 sql="SELECT "+columns+" FROM threads t JOIN categories c ON c.id=t.category_id WHERE t.category_id=? AND t.state='approved'"
 args=[category]
 if id is not None: sql+=' AND t.id=?'; args.append(integer(id))
 sql+=' ORDER BY COALESCE(t.published_at,t.created_at) DESC,t.id DESC'
 if id is None: sql+=' LIMIT ?'; args.append(value(c,'settings','public.news_limit'))
 rows=[dict(r) for r in c.execute(sql,args)]
 if id is not None:
  if not rows: fail('NOT_FOUND',404)
  return rows[0]
 return rows
def execute(op,user,data,query=None):
 query=query or {}; actor=user['id'] if user else 'anonymous'
 if op=='registry': return {'settings':SETTINGS,'flags':FLAGS,'labels':LABELS,'actions':ACTIONS,'roles':list(ROLES)}
 if op=='state': return get_state()
 if op=='news_settings':
  with transaction() as c:
   category_result=_change(c,actor,'settings','public.news_category',data['category_id'],data['reason'],data['expected_category_version'])
   limit_result=_change(c,actor,'settings','public.news_limit',data['limit'],data['reason'],data['expected_limit_version'])
   return {'category':category_result,'limit':limit_result}
 if op=='publication_options':
  require(user,'forum.read')
  with connect() as c:
   return {'categories':[dict(r) for r in c.execute("SELECT c.id,c.name,(SELECT count(*) FROM threads t WHERE t.category_id=c.id AND t.state='approved') AS approved_count FROM categories c ORDER BY c.name")],
           'forum_enabled':value(c,'flags','forum.enabled')}
 if op=='theme_contract':
  with connect() as c:
   item=get_state(c)['settings']['appearance.theme']
   return themes.contract(item['value'],item['version'])
 if op=='theme_preview':
  theme=data.get('theme'); validate_control('settings','appearance.theme',theme)
  return {'tokens':themes.tokens(theme),'theme':themes.public_theme(theme),'persisted':False}
 if op=='change':
  if data.get('category')=='permissions': require(user,'auth.permissions.write')
  return change(actor,data['category'],data['key'],data['value'],data['reason'],data['expected_version'])
 if op=='undo':
  with connect() as c:
   audit=row_for(c,'audit',data['audit_id'])
   if audit['category']=='permissions': require(user,'auth.permissions.write')
  return undo(actor,data['audit_id'],data['expected_version'])
 if op=='me': return {'user':{k:user[k] for k in ('id','email','role')},'permissions':sorted(permissions(user)),'csrf':user.get('csrf')}
 if op=='public_boot':
  with connect() as c:
   theme=value(c,'settings','appearance.theme')
   return {'labels':{k:v['value'] for k,v in get_state(c)['labels'].items()},'title':value(c,'settings','site.title'),'theme':themes.public_theme(theme),'theme_tokens':themes.tokens(theme)}
 if op in ('public_news','public_news_item'):
  with connect() as c:
   return public_news(c,int(query.get('id','0'))) if op=='public_news_item' else public_news(c)
 if op=='health':
  with connect() as c: c.execute('SELECT 1').fetchone()
  return {'status':'ok'}
 if op=='chat_prune':
  with connect() as c: module(c,'chat')
  return maintenance()
 if op in ('public_entries','public_entry'): maintenance()
 # One transaction per operation; mutations and audit either both commit or both roll back.
 with transaction() as c:
  if op.startswith('forum_'): module(c,'forum')
  if op.startswith('chat_'): module(c,'chat')
  if op=='logout':
   c.execute('DELETE FROM sessions WHERE token_hash=?',(data['_token_hash'],)); record(c,actor,'auth','logout',None,{'success':True},'session revoked'); return {'ok':True}
  if op=='audit': return [dict(x) for x in c.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 200')]
  if op=='dashboard':
   allowed=permissions(user,c); counts={}
   if 'content.read' in allowed: counts['entries']=c.execute('SELECT count(*) FROM entries').fetchone()[0]
   if 'media.read' in allowed: counts['media']=c.execute('SELECT count(*) FROM media').fetchone()[0]
   if 'forum.moderate' in allowed and value(c,'flags','forum.enabled'):
    counts['pending']=c.execute("SELECT (SELECT count(*) FROM threads WHERE state='pending')+(SELECT count(*) FROM replies WHERE state='pending')").fetchone()[0]
   if 'chat.read' in allowed and value(c,'flags','chat.enabled'):
    cutoff=int(time.time())-value(c,'settings','chat.retention_days')*86400
    counts['messages']=c.execute('SELECT count(*) FROM messages WHERE created_at>=?',(cutoff,)).fetchone()[0]
   if 'auth.users.read' in allowed: counts['users']=c.execute('SELECT count(*) FROM users WHERE active=1').fetchone()[0]
   return counts
  if op=='users': return [dict(r) for r in c.execute('SELECT id,email,role,active,created_at FROM users')]
  if op=='user_create':
   role=data['role']
   if role not in ROLES: fail('UNKNOWN_ROLE')
   uid=c.execute('INSERT INTO users(email,password_hash,role,created_at) VALUES(?,?,?,?)',(email_address(data['email']),password_hash(data['password']),role,now())).lastrowid
   record(c,actor,'auth','user:'+str(uid),None,{'email':data['email'],'role':role},'user created'); return {'id':uid}
  if op=='user_update':
   row=row_for(c,'users',data['id']); role=data['role']; active=data['active']
   if role not in ROLES or type(active)!=bool: fail('INVALID_VALUE')
   if row['role']=='admin' and row['active'] and (role!='admin' or not active) and c.execute("SELECT count(*) FROM users WHERE role='admin' AND active=1").fetchone()[0]<=1: fail('LAST_ADMIN_REQUIRED')
   hashed=password_hash(data['password']) if data.get('password') else row['password_hash']
   c.execute('UPDATE users SET role=?,active=?,password_hash=? WHERE id=?',(role,int(active),hashed,row['id']))
   c.execute('DELETE FROM sessions WHERE user_id=?',(row['id'],))
   record(c,actor,'auth','user:'+str(row['id']),{'role':row['role'],'active':bool(row['active'])},{'role':role,'active':active,'password_changed':bool(data.get('password'))},'access updated'); return {'ok':True}
  if op=='types': return [dict(r) for r in c.execute('SELECT * FROM content_types')]
  if op=='type_create':
   tid=identifier(data['id']); fields=data['fields']
   if not isinstance(fields,dict) or len(fields)>30 or any(not isinstance(k,str) or not re.fullmatch('[a-z][a-z0-9_]{0,63}',k) or v not in ('text','number','boolean') for k,v in fields.items()): fail('INVALID_SCHEMA')
   c.execute('INSERT INTO content_types VALUES(?,?,0)',(tid,json.dumps(fields))); record(c,actor,'content','type:'+tid,None,fields,'type created'); return {'id':tid}
  if op in ('entries','public_entries','public_entry'):
   if op=='entries': rows=c.execute('SELECT * FROM entries ORDER BY id DESC').fetchall()
   elif op=='public_entries': rows=c.execute("SELECT * FROM entries WHERE status='published' ORDER BY id DESC").fetchall()
   else:
    rows=c.execute("SELECT * FROM entries WHERE slug=? AND status='published'",(query.get('slug',''),)).fetchall()
    if not rows: fail('NOT_FOUND',404)
   result=[]
   for r in rows:
    item=dict(r); item['fields']=json.loads(item['fields']); item['media_ids']=[x[0] for x in c.execute('SELECT media_id FROM media_references WHERE entry_id=?',(r['id'],))]; result.append(item)
   return result[0] if op=='public_entry' else result
  if op in ('entry_create','entry_update'):
   tid=data['type_id']; slug=identifier(data['slug']); title=text(data['title'],1,200); body=text(data['body'],0,200000); fields=clean_fields(c,tid,data.get('fields',{}))
   if op=='entry_create':
    id=c.execute("INSERT INTO entries(type_id,slug,title,body,fields,status,author_id,updated_at) VALUES(?,?,?,?,?,'draft',?,?)",(tid,slug,title,body,fields,actor,now())).lastrowid
    previous=None; new_version=0
   else:
    row=row_for(c,'entries',data['id']); version(row,data['expected_version'])
    if row['status'] not in ('draft','review'): fail('RESTORE_TO_DRAFT_REQUIRED',409)
    id=row['id']; previous=dict(row); new_version=row['version']+1; snapshot(c,id,actor)
    c.execute("UPDATE entries SET type_id=?,slug=?,title=?,body=?,fields=?,status='draft',version=?,updated_at=? WHERE id=?",(tid,slug,title,body,fields,new_version,now(),id))
   references(c,id,data.get('media_ids',[])); record(c,actor,'content',id,previous,{'title':title,'status':'draft'},op,None,new_version); return {'id':id,'version':new_version}
  if op=='entry_transition':
   row=row_for(c,'entries',data['id']); version(row,data['expected_version']); target=data['status']
   allowed={'draft':{'review','published','scheduled','archived'},'review':{'draft','published','scheduled','archived'},'published':{'archived'},'scheduled':{'draft','archived'},'archived':{'draft'}}
   if target not in allowed[row['status']]: fail('INVALID_TRANSITION',409)
   if target in ('published','scheduled') or row['status']=='published': require(user,'content.publish')
   when=integer(data.get('publish_at'),int(time.time())+1) if target=='scheduled' else None
   snapshot(c,row['id'],actor); c.execute('UPDATE entries SET status=?,publish_at=?,version=version+1,updated_at=? WHERE id=?',(target,when,now(),row['id']))
   record(c,actor,'content',row['id'],{'status':row['status']},{'status':target,'publish_at':when},'workflow transition',row['version'],row['version']+1); return {'status':target,'version':row['version']+1}
  if op=='revisions':
   row_for(c,'entries',int(query['id'])); return [dict(x) for x in c.execute('SELECT * FROM revisions WHERE entry_id=? ORDER BY id DESC',(int(query['id']),))]
  if op=='entry_restore':
   row=row_for(c,'entries',data['id']); version(row,data['expected_version']); rev=row_for(c,'revisions',data['revision_id'])
   if rev['entry_id']!=row['id']: fail('INVALID_REVISION')
   old=json.loads(rev['snapshot']); snapshot(c,row['id'],actor)
   c.execute("UPDATE entries SET type_id=?,slug=?,title=?,body=?,fields=?,status='draft',publish_at=NULL,version=version+1,updated_at=? WHERE id=?",(old['type_id'],old['slug'],old['title'],old['body'],old['fields'],now(),row['id']))
   references(c,row['id'],old['media_ids']); record(c,actor,'content',row['id'],{'version':row['version']},{'revision_id':rev['id'],'status':'draft'},'revision restored'); return {'ok':True}
  if op=='media':
   return [dict(r) for r in c.execute('SELECT id,name,mime,alt,width,height,created_at,(SELECT count(*) FROM media_references WHERE media_id=media.id) AS references_count FROM media ORDER BY id DESC')]
  if op=='media_upload':
   name=text(data['name'],1,200); alt=text(data['alt'],1,1000); encoded=data['data']
   if not isinstance(encoded,str): fail('INVALID_IMAGE')
   try: raw=base64.b64decode(encoded,validate=True)
   except Exception: fail('INVALID_IMAGE')
   limit=value(c,'settings','media.max_bytes')
   if len(raw)>limit: fail('PAYLOAD_TOO_LARGE',413)
   raw,w,h=media_image(raw)
   if len(raw)>limit: fail('PAYLOAD_TOO_LARGE',413)
   id=c.execute('INSERT INTO media(name,mime,alt,data,width,height,owner_id,created_at) VALUES(?,?,?,?,?,?,?,?)',(name,'image/png',alt,raw,w,h,actor,now())).lastrowid
   record(c,actor,'media',id,None,{'name':name,'bytes':len(raw)},'image uploaded'); return {'id':id,'width':w,'height':h}
  if op=='media_transform':
   from PIL import Image
   row=row_for(c,'media',data['id']); width=integer(data['width'],1,4096)
   with Image.open(io.BytesIO(row['data'])) as im:
    height=max(1,round(im.height*width/im.width))
    if height>4096: fail('INVALID_DIMENSIONS')
    im=im.resize((width,height)); output=io.BytesIO(); im.save(output,format='PNG'); raw=output.getvalue()
   if len(raw)>value(c,'settings','media.max_bytes'): fail('PAYLOAD_TOO_LARGE',413)
   id=c.execute('INSERT INTO media(name,mime,alt,data,width,height,owner_id,created_at) VALUES(?,?,?,?,?,?,?,?)',(row['name'],'image/png',row['alt'],raw,width,height,actor,now())).lastrowid
   record(c,actor,'media',id,None,{'source':row['id'],'width':width},'transformed copy created'); return {'id':id}
  if op=='media_delete':
   row=row_for(c,'media',data['id'])
   if c.execute('SELECT 1 FROM media_references WHERE media_id=?',(row['id'],)).fetchone(): fail('MEDIA_IN_USE',409)
   c.execute('DELETE FROM media WHERE id=?',(row['id'],)); record(c,actor,'media',row['id'],{'name':row['name']},None,'asset deleted'); return {'ok':True}
  if op=='forum_categories': return [dict(r) for r in c.execute('SELECT * FROM categories')]
  if op=='forum_queue':
   threads=[dict(r) for r in c.execute("SELECT 'threads' AS kind,id,id AS thread_id,title,body,author_id,state,version,created_at FROM threads WHERE state='pending'")]
   replies=[dict(r) for r in c.execute("SELECT 'replies' AS kind,r.id,r.thread_id,t.title,r.body,r.author_id,r.state,r.version,r.created_at FROM replies r JOIN threads t ON t.id=r.thread_id WHERE r.state='pending'")]
   return sorted(threads+replies,key=lambda r:r['created_at'],reverse=True)
  if op=='forum_category_create':
   name=text(data['name'],1,120); id=c.execute('INSERT INTO categories(name) VALUES(?)',(name,)).lastrowid; record(c,actor,'forum','category:'+str(id),None,{'name':name},'category created'); return {'id':id}
  if op=='forum_threads':
   moderate='forum.moderate' in permissions(user,c)
   return [dict(r) for r in c.execute('SELECT * FROM threads WHERE state=\'approved\' OR author_id=? OR ? ORDER BY id DESC',(actor,int(moderate)))]
  if op=='forum_thread_create':
   row_for(c,'categories',data['category_id']); title=text(data['title'],1,200); body=text(data['body'],1,20000)
   id=c.execute('INSERT INTO threads(category_id,title,body,author_id,created_at) VALUES(?,?,?,?,?)',(data['category_id'],title,body,actor,now())).lastrowid
   record(c,actor,'forum','thread:'+str(id),None,{'state':'pending'},'thread created'); return {'id':id}
  if op=='forum_replies':
   thread=row_for(c,'threads',int(query['id'])); moderate='forum.moderate' in permissions(user,c)
   if thread['state']!='approved' and thread['author_id']!=actor and not moderate: fail('NOT_FOUND',404)
   return [dict(r) for r in c.execute("SELECT * FROM replies WHERE thread_id=? AND (state='approved' OR author_id=? OR ?) ORDER BY id",(thread['id'],actor,int(moderate)))]
  if op=='forum_reply_create':
   thread=row_for(c,'threads',data['thread_id'])
   if thread['state']!='approved' or thread['locked']: fail('THREAD_NOT_OPEN',409)
   id=c.execute('INSERT INTO replies(thread_id,body,author_id,created_at) VALUES(?,?,?,?)',(thread['id'],text(data['body'],1,20000),actor,now())).lastrowid
   record(c,actor,'forum','reply:'+str(id),None,{'state':'pending'},'reply created'); return {'id':id}
  if op=='forum_moderate':
   table=data['kind']
   if table not in ('threads','replies'): fail('INVALID_VALUE')
   row=row_for(c,table,data['id']); version(row,data['expected_version']); state=data['state']
   if state not in ('approved','rejected'): fail('INVALID_VALUE')
   if table=='threads':
    published_at=(row['published_at'] or now()) if state=='approved' else None
    c.execute('UPDATE threads SET state=?,published_at=?,version=version+1 WHERE id=?',(state,published_at,row['id']))
   else: c.execute('UPDATE replies SET state=?,version=version+1 WHERE id=?',(state,row['id']))
   record(c,actor,'forum',table+':'+str(row['id']),{'state':row['state']},{'state':state},text(data.get('reason','moderation'),1,500)); return {'ok':True}
  if op=='forum_lock':
   row=row_for(c,'threads',data['id']); version(row,data['expected_version']); locked=data['locked']
   if type(locked)!=bool: fail('INVALID_VALUE')
   c.execute('UPDATE threads SET locked=?,version=version+1 WHERE id=?',(int(locked),row['id'])); record(c,actor,'forum','thread:'+str(row['id']),{'locked':bool(row['locked'])},{'locked':locked},'thread lock changed'); return {'ok':True}
  if op=='chat_rooms': return [dict(r) for r in c.execute('SELECT * FROM rooms')]
  if op=='chat_room_create':
   name=text(data['name'],1,120); id=c.execute('INSERT INTO rooms(name) VALUES(?)',(name,)).lastrowid; record(c,actor,'chat','room:'+str(id),None,{'name':name},'room created'); return {'id':id}
  if op=='chat_messages':
   room=row_for(c,'rooms',int(query['room_id'])); cutoff=int(time.time())-value(c,'settings','chat.retention_days')*86400
   return [dict(r) for r in c.execute('SELECT m.*,u.email FROM messages m JOIN users u ON u.id=m.author_id WHERE room_id=? AND m.created_at>=? ORDER BY m.id DESC LIMIT 100',(room['id'],cutoff))][::-1]
  if op=='chat_presence':
   room=row_for(c,'rooms',data['room_id']); timestamp=int(time.time()); c.execute('INSERT INTO presence VALUES(?,?,?) ON CONFLICT(room_id,user_id) DO UPDATE SET seen_at=excluded.seen_at',(room['id'],actor,timestamp))
   return [dict(r) for r in c.execute('SELECT u.id,u.email FROM presence p JOIN users u ON u.id=p.user_id WHERE p.room_id=? AND seen_at>=? AND u.active=1',(room['id'],timestamp-90))]
  if op=='chat_send':
   room=row_for(c,'rooms',data['room_id']); body=text(data['body'],1,4000)
   timestamp=int(time.time())
   id=c.execute('INSERT INTO messages(room_id,author_id,body,created_at) VALUES(?,?,?,?)',(room['id'],actor,body,timestamp)).lastrowid
   record(c,actor,'chat','message:'+str(id),None,{'room_id':room['id']},'message sent'); return {'id':id,'created_at':timestamp}
  if op=='chat_delete':
   row=row_for(c,'messages',data['id']); c.execute('DELETE FROM messages WHERE id=?',(row['id'],)); record(c,actor,'chat','message:'+str(row['id']),{'room_id':row['room_id']},None,'message moderated'); return {'ok':True}
  if op=='keys': return [dict(r) for r in c.execute('SELECT id,name,scopes,expires_at,revoked,created_at FROM api_keys WHERE user_id=?',(actor,))]
  if op=='key_create':
   scopes=data['scopes']; allowed=permissions(user,c)
   if not isinstance(scopes,list) or not scopes or any(x not in allowed for x in scopes) or len(scopes)!=len(set(scopes)): fail('INVALID_SCOPES')
   token='eco_'+secrets.token_urlsafe(32); name=text(data['name'],1,120); expiry=int(time.time())+integer(data['days'],1,365)*86400
   id=c.execute('INSERT INTO api_keys(user_id,name,token_hash,scopes,expires_at,created_at) VALUES(?,?,?,?,?,?)',(actor,name,digest(token),json.dumps(scopes),expiry,now())).lastrowid
   record(c,actor,'api','key:'+str(id),None,{'name':name,'scopes':scopes},'key created'); return {'id':id,'token':token}
  if op=='key_revoke':
   row=row_for(c,'api_keys',data['id'])
   if row['user_id']!=actor: fail('PERMISSION_DENIED',403)
   c.execute('UPDATE api_keys SET revoked=1 WHERE id=?',(row['id'],)); record(c,actor,'api','key:'+str(row['id']),{'revoked':False},{'revoked':True},'key revoked'); return {'ok':True}
 fail('NOT_FOUND',404)
