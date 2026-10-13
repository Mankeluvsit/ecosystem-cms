"""HTTP acceptance tests: verify the interface's real server boundaries."""
import base64
import copy
import http.client
import io
import json
import tempfile
import threading
import time
import unittest
from app import server, web, themes
from PIL import Image


class HTTPAcceptance(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.previous_db = server.DB
        server.DB = self.tmp.name + '/cms.sqlite3'
        server.init()
        self.uid = server.bootstrap('admin@example.test', 'TestPasswordOnly123!')
        self.http = web.make_server(port=0)
        self.worker = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.worker.start()
        self.cookie = ''; self.csrf = ''
        status, result, headers = self.call('/api/login', {'email': 'admin@example.test', 'password': 'TestPasswordOnly123!'}, anonymous=True)
        self.assertEqual(status, 200)
        self.cookie = headers['set-cookie'].split(';')[0]
        self.csrf = result['csrf']

    def tearDown(self):
        self.http.shutdown(); self.http.server_close(); self.worker.join(timeout=2)
        server.DB = self.previous_db
        self.tmp.cleanup()

    def call(self, path, data=None, anonymous=False, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.http.server_port, timeout=5)
        h = {'Content-Type': 'application/json'}
        if not anonymous: h.update({'Cookie': self.cookie, 'X-CSRF-Token': self.csrf})
        h.update(headers or {})
        conn.request('GET' if data is None else 'POST', path, None if data is None else json.dumps(data), h)
        r = conn.getresponse(); body = r.read(); response_headers = {k.lower(): v for k, v in r.getheaders()}
        result = json.loads(body) if 'application/json' in response_headers.get('content-type', '') else body.decode(errors='replace')
        conn.close(); return r.status, result, response_headers

    def post(self, path, data):
        status, result, _ = self.call(path, data)
        self.assertEqual(status, 200, result)
        return result

    def test_control_acceptance_and_retention_execution(self):
        disabled = self.post('/api/change', {'category':'flags','key':'forum.enabled','value':False,'reason':'acceptance','expected_version':0})
        self.assertEqual(self.call('/api/forum/categories')[:2], (403, {'error':'MODULE_DISABLED'}))
        self.post('/api/undo', {'audit_id':disabled['audit_id'],'expected_version':1})
        self.assertEqual(self.call('/api/forum/categories')[0], 200)
        self.post('/api/change', {'category':'labels','key':'role.editor','value':'Publisher','reason':'acceptance','expected_version':0})
        self.post('/api/change', {'category':'labels','key':'publish.button','value':'Release now','reason':'acceptance','expected_version':0})
        boot = self.call('/api/public/bootstrap', anonymous=True)[1]
        self.assertEqual(boot['labels']['role.editor'], 'Publisher')
        self.assertEqual(boot['labels']['publish.button'], 'Release now')
        person = self.post('/api/users/create', {'email':'writer@example.test','password':'WriterPasswordOnly123!','role':'editor'})
        self.assertEqual(next(u for u in self.call('/api/users')[1] if u['id']==person['id'])['role'], 'editor')
        self.post('/api/change', {'category':'settings','key':'chat.retention_days','value':30,'reason':'acceptance','expected_version':0})
        with server.connect() as c:
            for days in (31, 29):
                c.execute('INSERT INTO messages(room_id,author_id,body,created_at) VALUES(1,?,?,?)',(self.uid,str(days),int(time.time())-days*86400))
        result = self.post('/api/chat/prune', {})
        self.assertEqual(result['deleted'], 1)
        self.assertEqual([m['body'] for m in self.call('/api/chat/messages?room_id=1')[1]], ['29'])
        audit = self.call('/api/audit')[1]
        change = next(a for a in audit if a['key']=='publish.button')
        self.assertEqual(change['actor'], str(self.uid)); self.assertEqual(change['reason'], 'acceptance')
        self.assertEqual(json.loads(change['new_value']), 'Release now')

    def test_publishing_revisions_and_public_isolation(self):
        entry = self.post('/api/content/create', {'type_id':'page','slug':'first-entry','title':'A story','body':'<script>alert(1)</script>','fields':{},'media_ids':[]})
        self.assertEqual(self.call('/api/public/entries', anonymous=True)[1], [])
        self.assertEqual(self.call('/p/first-entry', anonymous=True)[0], 404)
        status, result, _ = self.call('/api/content/update', {'id':entry['id'],'expected_version':5,'type_id':'page','slug':'first-entry','title':'Lost','body':'x','fields':{},'media_ids':[]})
        self.assertEqual((status, result['error']), (409, 'VERSION_CONFLICT'))
        self.post('/api/content/transition', {'id':entry['id'],'expected_version':0,'status':'published'})
        public = self.call('/p/first-entry', anonymous=True)
        self.assertEqual(public[0], 200); self.assertIn('&lt;script&gt;', public[1]); self.assertNotIn('<script>alert', public[1])
        revision = self.call('/api/content/revisions?id='+str(entry['id']))[1][0]
        self.post('/api/content/restore', {'id':entry['id'],'expected_version':1,'revision_id':revision['id']})
        self.assertEqual(self.call('/p/first-entry', anonymous=True)[0], 404)

    def test_images_references_and_transforms(self):
        image = io.BytesIO(); Image.new('RGB',(8,6),'green').save(image,format='PNG')
        asset = self.post('/api/media/upload', {'name':'image.png','alt':'Green rectangle','data':base64.b64encode(image.getvalue()).decode()})
        self.assertEqual(self.call('/media?id='+str(asset['id']), anonymous=True)[0], 404)
        copy = self.post('/api/media/transform', {'id':asset['id'],'width':4})
        self.assertEqual(next(m for m in self.call('/api/media')[1] if m['id']==copy['id'])['width'],4)
        entry = self.post('/api/content/create', {'type_id':'page','slug':'image-entry','title':'Image','body':'Body','fields':{},'media_ids':[asset['id']]})
        self.assertEqual(self.call('/api/media/delete', {'id':asset['id']})[0],409)
        self.post('/api/content/transition', {'id':entry['id'],'expected_version':0,'status':'published'})
        self.assertEqual(self.call('/media?id='+str(asset['id']), anonymous=True)[0],200)

    def test_forum_chat_and_scoped_keys(self):
        thread = self.post('/api/forum/threads', {'category_id':1,'title':'Welcome','body':'Hello'})
        self.assertEqual(self.call('/api/forum/replies', {'thread_id':thread['id'],'body':'reply'})[0],409)
        self.post('/api/forum/moderate', {'kind':'threads','id':thread['id'],'state':'approved','expected_version':0})
        reply = self.post('/api/forum/replies', {'thread_id':thread['id'],'body':'Reply'})
        queue=self.call('/api/forum/moderation')[1]
        self.assertEqual([(item['kind'],item['thread_id']) for item in queue],[('replies',thread['id'])])
        self.post('/api/forum/moderate', {'kind':'replies','id':reply['id'],'state':'approved','expected_version':0})
        self.post('/api/forum/lock', {'id':thread['id'],'expected_version':1,'locked':True})
        self.assertEqual(self.call('/api/forum/replies', {'thread_id':thread['id'],'body':'Blocked'})[0],409)
        room = self.post('/api/chat/rooms', {'name':'Studio'})
        message = self.post('/api/chat/send', {'room_id':room['id'],'body':'Hello room'})
        self.assertEqual(self.call('/api/chat/messages?room_id='+str(room['id']))[1][0]['id'],message['id'])
        self.assertEqual(self.post('/api/chat/presence', {'room_id':room['id']})[0]['id'],self.uid)
        key = self.post('/api/keys/create', {'name':'Read only','days':1,'scopes':['content.read']})
        bearer = {'Authorization':'Bearer '+key['token']}
        self.assertEqual(self.call('/api/content/entries', anonymous=True, headers=bearer)[0],200)
        self.assertEqual(self.call('/api/users', anonymous=True, headers=bearer)[0],403)
        self.post('/api/keys/revoke', {'id':key['id']})
        self.assertEqual(self.call('/api/content/entries', anonymous=True, headers=bearer)[0],401)

    def test_authentication_csrf_registry_and_dashboard_visibility(self):
        self.assertEqual(self.call('/api/dashboard', anonymous=True, headers={'X-Actor':'admin','X-Role':'admin'})[0],401)
        self.assertEqual(self.call('/api/change', {'category':'labels','key':'publish.button','value':'Bad','reason':'test','expected_version':0}, headers={'X-CSRF-Token':''})[0],403)
        self.assertTrue(all(a in server.ACTIONS for a, op in web.ROUTES.values()))
        editor = self.post('/api/users/create', {'email':'editor@example.test','password':'EditorPassword123!','role':'editor'})
        status, login, headers = self.call('/api/login', {'email':'editor@example.test','password':'EditorPassword123!'}, anonymous=True)
        self.assertEqual(status,200); self.cookie=headers['set-cookie'].split(';')[0]; self.csrf=login['csrf']
        counts = self.call('/api/dashboard')[1]
        self.assertNotIn('users',counts); self.assertNotIn('pending',counts)
        self.assertEqual(self.call('/api/users')[0],403)
        self.assertEqual(self.call('/api/forum/moderation')[0],403)
        self.assertEqual(self.call('/api/change', {'category':'flags','key':'forum.enabled','value':False,'reason':'test','expected_version':0})[0],403)

    def test_theme_validation_preview_save_and_undo(self):
        manifest=self.call('/api/theme/contract')[1]
        self.assertEqual(manifest['current'],themes.DEFAULT)
        theme=copy.deepcopy(themes.DEFAULT);theme['preset']='ocean';theme['colors']=themes.PALETTES['ocean'];theme['public_font']='serif';theme['density']='compact';theme['radius']=4;theme['public_layout']='list';theme['design_notes']='Private styling instructions'
        preview=self.post('/api/theme/preview',{'theme':theme})
        self.assertFalse(preview['persisted']);self.assertEqual(preview['tokens']['--green'],'#175d86')
        self.assertEqual(self.call('/api/state')[1]['settings']['appearance.theme']['version'],0)
        saved=self.post('/api/change',{'category':'settings','key':'appearance.theme','value':theme,'reason':'theme acceptance','expected_version':0})
        css=self.call('/assets/theme.css',anonymous=True)[1]
        self.assertIn('--green:#175d86;',css);self.assertIn('--radius:4px;',css);self.assertIn('Georgia',css)
        boot=self.call('/api/public/bootstrap',anonymous=True)[1]
        self.assertNotIn('design_notes',boot['theme']);self.assertNotIn('Private styling instructions',css)
        invalid=copy.deepcopy(theme);invalid['colors']['accent']='#ffffff'
        status,result,_=self.call('/api/change',{'category':'settings','key':'appearance.theme','value':invalid,'reason':'invalid','expected_version':1})
        self.assertEqual((status,result['error']),(400,'THEME_CONTRAST_TOO_LOW'))
        injected=copy.deepcopy(theme);injected['colors']['accent']='red; background:url(https://evil.test)'
        self.assertEqual(self.call('/api/theme/preview',{'theme':injected})[0],400)
        self.assertEqual(self.call('/api/theme/preview',{'theme':theme},anonymous=True)[0],401)
        self.assertEqual(self.call('/api/theme/contract',anonymous=True)[0],401)
        self.post('/api/undo',{'audit_id':saved['audit_id'],'expected_version':1})
        self.assertEqual(self.call('/api/state')[1]['settings']['appearance.theme']['value'],themes.DEFAULT)
        for name,colors in themes.PALETTES.items():
            variant=copy.deepcopy(themes.DEFAULT);variant['preset']=name;variant['colors']=colors
            self.assertEqual(self.post('/api/theme/preview',{'theme':variant})['theme']['preset'],name)

    def test_public_news_visibility_limits_and_atomic_settings(self):
        category=self.post('/api/forum/categories',{'name':'News and updates'})['id']
        self.assertEqual(self.call('/api/public/news',anonymous=True)[1],[])
        pending=self.post('/api/forum/threads',{'category_id':category,'title':'Pending announcement','body':'Do not expose this'})
        rejected=self.post('/api/forum/threads',{'category_id':category,'title':'Rejected announcement','body':'Do not expose this either'})
        public=self.post('/api/forum/threads',{'category_id':category,'title':'A public update','body':'<script>unsafe()</script> A safe escaped announcement.'})
        other=self.post('/api/forum/threads',{'category_id':1,'title':'Other category','body':'This is not public news'})
        for thread,state in [(public,'approved'),(other,'approved'),(rejected,'rejected')]:
            self.post('/api/forum/moderate',{'kind':'threads','id':thread['id'],'state':state,'expected_version':0})
        self.post('/api/forum/replies',{'thread_id':public['id'],'body':'Reply should stay private'})
        self.post('/api/news/settings',{'category_id':category,'limit':1,'reason':'Publish news category','expected_category_version':0,'expected_limit_version':0})
        feed=self.call('/api/public/news',anonymous=True)[1]
        self.assertEqual([n['id'] for n in feed],[public['id']]);self.assertIn('published_at',feed[0]);self.assertNotIn('author_id',feed[0])
        home=self.call('/',anonymous=True)[1]
        self.assertIn('A public update',home);self.assertNotIn('Pending announcement',home);self.assertNotIn('Reply should stay private',home)
        self.assertEqual(self.call('/news/'+str(pending['id']),anonymous=True)[0],404)
        self.assertEqual(self.call('/api/public/news/item?id='+str(rejected['id']),anonymous=True)[0],404)
        self.assertEqual(self.call('/news/'+str(other['id']),anonymous=True)[0],404)
        page=self.call('/news/'+str(public['id']),anonymous=True)
        self.assertEqual(page[0],200);self.assertIn('&lt;script&gt;',page[1]);self.assertNotIn('<script>unsafe',page[1])
        self.assertIn('Published ',page[1])
        # Historical approvals have no known approval timestamp; show their real posting date.
        with server.connect() as c: c.execute('UPDATE threads SET published_at=NULL WHERE id=?',(public['id'],))
        self.assertIn('Posted ',self.call('/news/'+str(public['id']),anonymous=True)[1])
        # A bad second setting rolls back the first setting and both audit records.
        before=len(self.call('/api/audit')[1])
        status,_,_=self.call('/api/news/settings',{'category_id':0,'limit':99,'reason':'invalid limit','expected_category_version':1,'expected_limit_version':1})
        self.assertEqual(status,400);self.assertEqual(len(self.call('/api/audit')[1]),before)
        self.assertEqual(self.call('/api/state')[1]['settings']['public.news_category']['value'],category)
        self.assertEqual(self.call('/api/change',{'category':'settings','key':'public.news_category','value':9999,'reason':'invalid category','expected_version':1})[0],400)
        self.post('/api/change',{'category':'flags','key':'forum.enabled','value':False,'reason':'Disable forum','expected_version':0})
        self.assertEqual(self.call('/api/public/news',anonymous=True)[1],[])
        self.assertEqual(self.call('/news/'+str(public['id']),anonymous=True)[0],404)

    def test_untouched_copy_upgrade_preserves_user_labels(self):
        with server.connect() as c:
            c.execute("DELETE FROM schema_migrations WHERE version='003_readable_labels'")
            c.execute("UPDATE controls SET value=?,version=0 WHERE category='labels' AND key='studio.saved'",(json.dumps('Saved on the server'),))
            c.execute("UPDATE controls SET value=?,version=3 WHERE category='labels' AND key='content.title'",(json.dumps('My publishing desk'),))
        server.init()
        state=server.get_state()['labels']
        self.assertEqual(state['studio.saved']['value'],'All changes saved')
        self.assertEqual(state['studio.saved']['version'],1)
        self.assertEqual(state['content.title'],{'value':'My publishing desk','version':3})
        self.assertTrue(any(e['key']=='studio.saved' and e['actor']=='system' for e in self.call('/api/audit')[1]))

if __name__ == '__main__': unittest.main()
