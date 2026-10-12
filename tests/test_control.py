import unittest,tempfile,os,sys
sys.path.insert(0,os.path.abspath('app'))
import server
class ControlTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();server.DB=os.path.join(self.tmp.name,'test.db');server.init()
 def tearDown(self):self.tmp.cleanup()
 def test_persist_and_undo(self):
  r=server.change('tester','labels','publish.button','Release','test',0)
  self.assertEqual(server.get_state()['labels']['publish.button']['value'],'Release')
  server.undo('tester',r['audit_id'],1)
  self.assertEqual(server.get_state()['labels']['publish.button']['value'],'Publish')
 def test_flag(self):
  server.change('tester','flags','forum.enabled',False,'test',0)
  self.assertFalse(server.get_state()['flags']['forum.enabled']['value'])
 def test_undeclared(self):
  with self.assertRaisesRegex(ValueError,'UNDECLARED_CONTROL'):server.change('tester','flags','unknown',True,'test',0)
 def test_version_conflict(self):
  server.change('tester','settings','site.title','New','test',0)
  with self.assertRaisesRegex(ValueError,'VERSION_CONFLICT'):server.change('tester','settings','site.title','Other','test',0)
 def test_audit(self):
  server.change('tester','settings','site.title','New','test',0)
  with server.connect() as c:
   row=c.execute('SELECT * FROM audit').fetchone()
   self.assertEqual(row['actor'],'tester');self.assertEqual(row['reason'],'test')
if __name__=='__main__':unittest.main()

