import os,json
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse
import server
class Handler(BaseHTTPRequestHandler):
 def reply(self,status,data):
  body=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 def dispatch(self):
  path=urlparse(self.path).path
  if path=='/':
   body=open(os.path.join(os.path.dirname(__file__),'admin.html'),encoding='utf-8').read().encode()
   self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(body);return
  route=self.command+' '+path
  if route not in server.ROUTES:return self.reply(404,{'error':'NOT_FOUND'})
  actor=self.headers.get('X-Actor','');role=self.headers.get('X-Role','')
  if not actor or role!='admin':return self.reply(403,{'error':'PERMISSION_DENIED'})
  if path=='/api/state':return self.reply(200,server.get_state())
  if path=='/api/registry':return self.reply(200,{'settings':server.SETTINGS,'flags':server.FLAGS,'labels':server.LABELS,'actions':sorted(server.ACTIONS)})
  if path=='/api/audit':
   with server.connect() as c:rows=[dict(x) for x in c.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 100')]
   return self.reply(200,rows)
  try:
   length=int(self.headers.get('Content-Length','0'))
   if length>10000:return self.reply(413,{'error':'PAYLOAD_TOO_LARGE'})
   data=json.loads(self.rfile.read(length))
   if path=='/api/change':result=server.change(actor,data['category'],data['key'],data['value'],data.get('reason','manual'),data['expected_version'])
   else:result=server.undo(actor,data['audit_id'],data['expected_version'])
   return self.reply(200,result)
  except (ValueError,KeyError,TypeError) as e:return self.reply(400,{'error':str(e)})
 def do_GET(self):self.dispatch()
 def do_POST(self):self.dispatch()
if __name__=='__main__':
 server.init();port=int(os.getenv('CMS_PORT','8765'))
 print('LOCAL TEST ONLY: http://127.0.0.1:'+str(port))
 ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
