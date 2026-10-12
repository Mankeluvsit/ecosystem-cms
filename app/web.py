"""Registered HTTP boundary. No actor/role headers are trusted."""
import os, json, sqlite3, threading, time, logging, html
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from . import server
# Every API route is registered, including intentional public operations.
ROUTES = {}
def route(method,path,action,operation):
 assert action in server.ACTIONS
 ROUTES[method+' '+path]=(action,operation)
for method,path,action,operation in [
 ('GET','/api/health','api.health','health'),('GET','/api/public/bootstrap','public.read','public_boot'),('GET','/api/public/entries','public.read','public_entries'),('GET','/api/public/entry','public.read','public_entry'),
 ('POST','/api/login','auth.login','login'),('POST','/api/logout','auth.session','logout'),('GET','/api/me','auth.session','me'),
 ('GET','/api/registry','config.read','registry'),('GET','/api/state','config.read','state'),('GET','/api/audit','audit.read','audit'),('POST','/api/change','config.write','change'),('POST','/api/undo','config.write','undo'),
 ('GET','/api/dashboard','admin.read','dashboard'),('GET','/api/users','auth.users.read','users'),('POST','/api/users/create','auth.users.write','user_create'),('POST','/api/users/update','auth.users.write','user_update'),
 ('GET','/api/content/types','content.read','types'),('POST','/api/content/types','content.write','type_create'),('GET','/api/content/entries','content.read','entries'),('POST','/api/content/create','content.write','entry_create'),('POST','/api/content/update','content.write','entry_update'),('POST','/api/content/transition','content.write','entry_transition'),('GET','/api/content/revisions','content.read','revisions'),('POST','/api/content/restore','content.write','entry_restore'),
 ('GET','/api/media','media.read','media'),('GET','/api/media/file','media.read','media_file'),('POST','/api/media/upload','media.write','media_upload'),('POST','/api/media/transform','media.write','media_transform'),('POST','/api/media/delete','media.write','media_delete'),
 ('GET','/api/forum/categories','forum.read','forum_categories'),('POST','/api/forum/categories','forum.moderate','forum_category_create'),('GET','/api/forum/threads','forum.read','forum_threads'),('POST','/api/forum/threads','forum.write','forum_thread_create'),('GET','/api/forum/replies','forum.read','forum_replies'),('POST','/api/forum/replies','forum.write','forum_reply_create'),('POST','/api/forum/moderate','forum.moderate','forum_moderate'),('POST','/api/forum/lock','forum.moderate','forum_lock'),
 ('GET','/api/chat/rooms','chat.read','chat_rooms'),('POST','/api/chat/rooms','chat.manage','chat_room_create'),('GET','/api/chat/messages','chat.read','chat_messages'),('POST','/api/chat/presence','chat.read','chat_presence'),('POST','/api/chat/send','chat.write','chat_send'),('POST','/api/chat/delete','chat.manage','chat_delete'),('POST','/api/chat/prune','chat.manage','chat_prune'),
 ('GET','/api/keys','api.keys.read','keys'),('POST','/api/keys/create','api.keys.write','key_create'),('POST','/api/keys/revoke','api.keys.write','key_revoke'),
]: route(method,path,action,operation)
ROOT=Path(__file__).parent
class Handler(BaseHTTPRequestHandler):
 protocol_version='HTTP/1.1'
 def log_message(self,fmt,*args): pass # Avoid logging secrets or untrusted request targets.
 def send(self,status,body,mime='application/json',headers=None):
  if not isinstance(body,bytes): body=json.dumps(body,allow_nan=False).encode() if mime=='application/json' else body.encode()
  self.send_response(status)
  for key,val in {'Content-Type':mime,'Content-Length':str(len(body)),'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'same-origin','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",'Connection':'close',**(headers or {})}.items(): self.send_header(key,val)
  if os.getenv('CMS_ENV')=='production': self.send_header('Strict-Transport-Security','max-age=31536000')
  self.end_headers(); self.wfile.write(body); self.close_connection=True
 def json_body(self):
  try: length=int(self.headers.get('Content-Length','0'))
  except ValueError: server.fail('INVALID_BODY')
  if not 0<length<=12000000: server.fail('PAYLOAD_TOO_LARGE',413)
  self.connection.settimeout(15)
  try: data=json.loads(self.rfile.read(length),parse_constant=lambda x:server.fail('INVALID_BODY'))
  except (json.JSONDecodeError,UnicodeError): server.fail('INVALID_BODY')
  if not isinstance(data,dict): server.fail('INVALID_BODY')
  return data
 def current_identity(self):
  auth=self.headers.get('Authorization','')
  if auth.startswith('Bearer '): return server.identity(auth[7:],True),auth[7:],True
  cookie=SimpleCookie()
  try: cookie.load(self.headers.get('Cookie',''))
  except Exception: return None,'',False
  token=cookie['eco_session'].value if 'eco_session' in cookie else ''
  return server.identity(token),token,False
 def cookie(self,token,clear=False):
  return 'eco_session='+token+'; Path=/; HttpOnly; SameSite=Strict; Max-Age='+('0' if clear else '43200')+('; Secure' if os.getenv('CMS_ENV')=='production' else '')
 def dispatch(self):
  try:
   url=urlparse(self.path); path=url.path; query={k:v[0] for k,v in parse_qs(url.query).items()}
   user,token,is_key=self.current_identity()
   if self.command=='GET' and path in ('/admin','/admin/','/assets/admin.js','/assets/app.css'):
    file={'/admin':'admin.html','/admin/':'admin.html','/assets/admin.js':'admin.js','/assets/app.css':'app.css'}[path]
    mime={'html':'text/html; charset=utf-8','js':'text/javascript; charset=utf-8','css':'text/css; charset=utf-8'}[file.split('.')[-1]]
    return self.send(200,(ROOT/file).read_bytes(),mime)
   if self.command=='GET' and (path=='/' or path.startswith('/p/')): return self.public_page(path)
   if self.command=='GET' and path=='/media': return self.media_file(query,user,public=True)
   registered=ROUTES.get(self.command+' '+path)
   if not registered: server.fail('NOT_FOUND',404)
   action,op=registered; server.require(user,action)
   if self.command=='POST':
    origin=self.headers.get('Origin')
    expected=os.getenv('CMS_ORIGIN','http://'+self.headers.get('Host',''))
    if origin and origin!=expected: server.fail('ORIGIN_REJECTED',403)
    if op!='login' and not is_key and not server.hmac.compare_digest(self.headers.get('X-CSRF-Token',''),user.get('csrf','')): server.fail('CSRF_REQUIRED',403)
    if op in ('login','logout') and is_key: server.fail('SESSION_REQUIRED',403)
   with server.transaction() as c:
    key='api:'+('key:'+str(user['key_id']) if is_key and user else 'user:'+str(user['id']) if user else 'ip:'+self.client_address[0])
    allowed=server.rate(c,key,server.value(c,'settings','api.requests_per_minute'))
   if not allowed: server.fail('RATE_LIMITED',429)
   data=self.json_body() if self.command=='POST' else {}
   if op=='login':
    result=server.login(data['email'],data['password'],self.client_address[0]); result.pop('token',None) if False else None
    session_token=result.pop('token'); return self.send(200,result,headers={'Set-Cookie':self.cookie(session_token)})
   if op=='logout': data['_token_hash']=server.digest(token)
   if op=='media_file': return self.media_file(query,user)
   result=server.execute(op,user,data,query)
   return self.send(200,result,headers={'Set-Cookie':self.cookie('',True)} if op=='logout' else None)
  except server.Fault as exc: self.send(exc.status,{'error':exc.code})
  except sqlite3.IntegrityError: self.send(409,{'error':'CONSTRAINT_CONFLICT'})
  except (KeyError,TypeError,ValueError,OverflowError): self.send(400,{'error':'INVALID_REQUEST'})
  except Exception:
   logging.exception('Request failed'); self.send(500,{'error':'INTERNAL_ERROR'})
 def media_file(self,query,user,public=False):
  with server.connect() as c:
   row=server.row_for(c,'media',int(query['id']))
   if public:
    visible=c.execute("SELECT 1 FROM media_references r JOIN entries e ON e.id=r.entry_id WHERE r.media_id=? AND e.status='published'",(row['id'],)).fetchone()
    if not visible: server.fail('NOT_FOUND',404)
   else: server.require(user,'media.read')
   self.send(200,row['data'],row['mime'])
 def public_page(self,path):
  server.maintenance()
  esc=html.escape
  with server.connect() as c:
   labels={k:v['value'] for k,v in server.get_state(c)['labels'].items()}; title=server.value(c,'settings','site.title'); status=200
   if path=='/':
    rows=c.execute("SELECT * FROM entries WHERE status='published' ORDER BY id DESC").fetchall()
    body='<h1>'+esc(labels['site.heading'])+'</h1><p>'+esc(labels['public.description'])+'</p>'
    body+=''.join('<article class="card"><h2><a href="/p/'+esc(r['slug'])+'">'+esc(r['title'])+'</a></h2><p>'+esc(r['body'][:220])+'</p></article>' for r in rows) or '<p>'+esc(labels['public.empty'])+'</p>'
    description=labels['public.description']; canonical='/'
   else:
    row=c.execute("SELECT * FROM entries WHERE slug=? AND status='published'",(path[3:],)).fetchone()
    if not row: body='<h1>'+esc(labels['not.found'])+'</h1>'; status=404; description=labels['not.found']; canonical=path
    else:
     title=row['title']+' · '+title; description=row['body'][:155]; canonical='/p/'+row['slug']; body='<article><h1>'+esc(row['title'])+'</h1><div class="prose">'+esc(row['body'])+'</div>'
     for media in c.execute('SELECT m.* FROM media m JOIN media_references r ON r.media_id=m.id WHERE r.entry_id=?',(row['id'],)): body+='<img class="public-image" src="/media?id='+str(media['id'])+'" alt="'+esc(media['alt'])+'">'
     body+='</article>'
   origin=os.getenv('CMS_ORIGIN','')
   document='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(title)+'</title><meta name="description" content="'+esc(description)+'"><link rel="canonical" href="'+esc(origin+canonical)+'"><link rel="stylesheet" href="/assets/app.css"></head><body><header><a href="/">'+esc(labels['public.home'])+'</a><a href="/admin">'+esc(labels['login.title'])+'</a></header><main class="public-main">'+body+'</main></body></html>'
   self.send(status,document,'text/html; charset=utf-8')
 def do_GET(self): self.dispatch()
 def do_POST(self): self.dispatch()
def make_server(host='127.0.0.1',port=8765): return ThreadingHTTPServer((host,port),Handler)
def main():
 if os.getenv('CMS_ENV')=='production':
  origin=os.getenv('CMS_ORIGIN','')
  if not origin.startswith('https://') or origin.endswith('/'): raise SystemExit('Production requires CMS_ORIGIN=https://hostname without trailing slash')
  if not os.path.isabs(server.DB): raise SystemExit('Production requires absolute CMS_DB on persistent storage')
 server.init()
 with server.connect() as c:
  if not c.execute('SELECT 1 FROM users WHERE active=1 AND role=\'admin\'').fetchone(): raise SystemExit('Run python -m app.manage bootstrap before startup')
 stop=threading.Event()
 def worker():
  while not stop.is_set():
   try: server.maintenance()
   except Exception: logging.exception('Maintenance failed')
   stop.wait(30)
 thread=threading.Thread(target=worker,daemon=True); thread.start()
 http=make_server(os.getenv('CMS_HOST','127.0.0.1'),int(os.getenv('CMS_PORT','8765')))
 print('Listening on '+str(http.server_address),flush=True)
 try: http.serve_forever()
 finally: stop.set(); http.server_close(); thread.join(timeout=2)
if __name__=='__main__': main()
