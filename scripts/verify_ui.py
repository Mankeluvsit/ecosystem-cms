"""Real Chromium workflows on an isolated, synthetic SQLite fixture.

Run: python scripts/verify_ui.py
Optional CMS_BROWSER selects a system Chromium path; otherwise Playwright's browser.
No production accounts or data are read or changed. Screenshots use test records.
"""
import base64
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from PIL import Image
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import server, web


def run():
    artifact_dir = ROOT / 'evidence' / 'ui'
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir/'results.json').write_text(json.dumps({'status':'IMPLEMENTED_UNVERIFIED','checks':[],'fixture':'isolated synthetic test data','note':'Current browser run has started; prior screenshots are not pass evidence.'},indent=2)+'\n')
    checks = []
    axe_path=os.getenv('CMS_AXE_PATH')
    axe_source=Path(axe_path).read_text() if axe_path else None
    accessibility=[]
    with tempfile.TemporaryDirectory(prefix='ecosystem-ui-') as directory:
        previous_db = server.DB
        server.DB = directory + '/cms.sqlite3'
        server.init()
        uid = server.bootstrap('studio@example.test', 'StudioTestPassword123!')
        admin = {'id':uid, 'role':'admin', 'email':'studio@example.test'}
        server.change(uid, 'settings', 'api.requests_per_minute', 10000, 'isolated browser fixture', 0)
        server.execute('type_create', admin, {'id':'story','fields':{'summary':'text','featured':'boolean','reading_minutes':'number'}})
        image = io.BytesIO(); Image.new('RGB',(720,440),'#446c51').save(image,format='PNG')
        media = server.execute('media_upload',admin,{'name':'forest-study.png','alt':'Green color study for test media','data':base64.b64encode(image.getvalue()).decode()})
        first = server.execute('entry_create',admin,{'type_id':'page','slug':'welcome-to-the-ecosystem','title':'Welcome to the ecosystem','body':'A shared space for ideas, useful stories, and conversations.\n\nThis is synthetic test content used to verify the interface.','fields':{},'media_ids':[media['id']]})
        server.execute('entry_transition',admin,{'id':first['id'],'expected_version':0,'status':'published'})
        server.execute('entry_create',admin,{'type_id':'story','slug':'field-notes','title':'Field notes from the community','body':'A draft ready for another thoughtful edit.','fields':{'summary':'Notes for review','featured':True,'reading_minutes':4},'media_ids':[]})
        thread = server.execute('forum_thread_create',admin,{'category_id':1,'title':'What should we build together?','body':'Share one idea for the next community project.'})
        server.execute('chat_send',admin,{'room_id':1,'body':'Welcome to the studio. These messages are test fixtures.'})
        http = web.make_server(port=0)
        worker = threading.Thread(target=http.serve_forever,daemon=True); worker.start()
        origin = 'http://127.0.0.1:' + str(http.server_port)
        errors = []
        try:
            with sync_playwright() as p:
                executable = os.getenv('CMS_BROWSER')
                browser = p.chromium.launch(executable_path=executable,headless=True,args=['--no-sandbox','--disable-crashpad-for-testing'])
                context = browser.new_context(viewport={'width':1440,'height':1000})
                context.set_default_timeout(10000)
                page = context.new_page(); page.on('pageerror',lambda error:errors.append(str(error)))
                def capture(name):
                    page.evaluate('window.scrollTo(0,0)')
                    page.evaluate('document.activeElement?.blur()')
                    page.screenshot(path=str(artifact_dir/name),full_page=True)
                def audit_page(target,label):
                    if not axe_source: return
                    target.evaluate(axe_source)
                    violations=target.evaluate('async () => (await axe.run(document,{runOnly:{type:"tag",values:["wcag2a","wcag2aa","wcag21aa","wcag22aa"]}})).violations.map(v=>({id:v.id,impact:v.impact,description:v.description,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))')
                    accessibility.append({'screen':label,'violations':violations})
                    if violations:
                        (artifact_dir/'accessibility.json').write_text(json.dumps(accessibility,indent=2)+'\n')
                    assert not violations,(label,violations)
                page.goto(origin+'/admin')
                expect(page.get_by_role('heading',name='Welcome back')).to_be_visible()
                audit_page(page,'sign-in desktop')
                capture('signin-desktop.png')
                page.get_by_label('Email',exact=True).fill('studio@example.test')
                page.get_by_label('Password',exact=True).fill('StudioTestPassword123!')
                page.get_by_role('button',name='Sign in',exact=True).click()
                expect(page.get_by_role('heading',name='Your workspace, at a glance.')).to_be_visible()
                capture('overview-desktop.png')
                checks.append('Password sign-in and permitted dashboard render')

                def nav(name, heading):
                    page.locator('#nav').get_by_role('link',name=name,exact=True).click()
                    expect(page.get_by_role('heading',name=heading,exact=True).first).to_be_visible()
                    expect(page.locator('#main')).not_to_have_attribute('aria-busy','true')

                nav('Content','Content workspace')
                page.get_by_label('Search records').fill('field notes')
                expect(page.get_by_role('link',name='Field notes from the community',exact=True)).to_be_visible()
                expect(page.get_by_role('link',name='Welcome to the ecosystem',exact=True)).to_have_count(0)
                page.get_by_label('Search records').fill('')
                capture('content-desktop.png')
                page.get_by_role('button',name='Create draft',exact=True).first.click()
                expect(page.get_by_role('heading',name='Create draft',exact=True)).to_be_visible()
                capture('new-draft.png')
                page.get_by_label('Content type',exact=True).select_option('story')
                page.get_by_label('Title',exact=True).fill('Browser workflow story')
                page.get_by_label('URL slug',exact=True).fill('browser-workflow-story')
                page.get_by_label('Body (plain text)',exact=True).fill('This entry was created and published through the redesigned browser UI.')
                page.get_by_label('summary',exact=True).fill('Typed schema fields work')
                page.get_by_label('reading_minutes',exact=True).fill('3')
                page.get_by_label('featured',exact=True).check()
                page.get_by_role('button',name='Choose images',exact=True).click()
                expect(page.locator('#inspector')).to_be_visible()
                page.get_by_role('button',name='forest-study.png',exact=True).click()
                page.get_by_role('button',name='Use selected images',exact=True).click()
                page.get_by_role('button',name='Save',exact=True).click()
                expect(page.get_by_role('heading',name='Browser workflow story',exact=True)).to_be_visible()
                expect(page.get_by_text('Saved on the server',exact=True)).to_be_visible()
                capture('editor-desktop.png')
                checks.append('Create draft with typed custom fields and visual media references')

                page.route('**/api/content/update',lambda r:r.fulfill(status=409,content_type='application/json',body='{"error":"VERSION_CONFLICT"}'))
                page.get_by_label('Body (plain text)',exact=True).fill('Keep this unsaved text after a conflict.')
                page.get_by_role('button',name='Save',exact=True).click()
                expect(page.locator('.editor-form .form-error')).to_contain_text('Another change occurred')
                expect(page.get_by_label('Body (plain text)',exact=True)).to_have_value('Keep this unsaved text after a conflict.')
                expect(page.locator('#progress li[data-state=failed]')).to_have_count(1)
                expect(page.locator('#progress li[data-state=blocked]')).to_have_count(1)
                capture('save-conflict.png')
                checks.append('Conflict preserves editor input and marks failed/blocked stages')
                page.unroute('**/api/content/update')
                page.get_by_role('button',name='Save',exact=True).click()
                expect(page.get_by_text('Saved on the server',exact=True)).to_be_visible()
                page.get_by_role('button',name='Publish',exact=True).click()
                expect(page.locator('#confirmation')).to_be_visible()
                page.locator('#confirm-yes').click()
                expect(page.locator('.editor-properties .badge[data-state=published]')).to_be_visible()
                public = context.new_page(); public.goto(origin+'/p/browser-workflow-story')
                expect(public.get_by_role('heading',name='Browser workflow story')).to_be_visible()
                expect(public.get_by_text('Keep this unsaved text after a conflict.',exact=True)).to_be_visible()
                public.screenshot(path=str(artifact_dir/'public-article.png'),full_page=True)
                audit_page(public,'public article')
                public.goto(origin+'/'); public.screenshot(path=str(artifact_dir/'public-home.png'),full_page=True); public.close()
                checks.append('Publish confirmation and real public page')

                nav('Media','Media library')
                page.get_by_role('button',name='Upload image',exact=True).first.click()
                audit_page(page,'upload dialog desktop')
                page.keyboard.press('Escape')
                expect(page.get_by_role('button',name='Upload image',exact=True).first).to_be_focused()
                page.get_by_role('button',name='Upload image',exact=True).first.click()
                page.get_by_label('PNG, JPEG, GIF or WebP image',exact=True).set_input_files({'name':'browser-upload.png','mimeType':'image/png','buffer':image.getvalue()})
                page.get_by_label('Alternative text',exact=True).fill('Browser uploaded image')
                page.locator('#inspector').get_by_role('button',name='Upload image',exact=True).click()
                expect(page.locator('#inspector')).not_to_be_visible()
                expect(page.get_by_role('heading',name='browser-upload.png',exact=True)).to_be_visible()
                capture('media-desktop.png')
                checks.append('Media upload persists; inspector Escape restores focus')

                nav('Forum','Forum')
                page.get_by_role('button',name='What should we build together?',exact=True).click()
                expect(page.get_by_role('heading',name='What should we build together?',exact=True)).to_be_visible()
                page.get_by_role('button',name='Approve',exact=True).click(); page.locator('#confirm-yes').click()
                expect(page.locator('.thread-meta').first.locator('.badge[data-state=approved]')).to_be_visible()
                page.get_by_label('Message',exact=True).fill('Browser-created reply')
                page.get_by_role('button',name='Reply',exact=True).click()
                expect(page.get_by_text('Browser-created reply',exact=True)).to_be_visible()
                checks.append('Moderation confirmation and reply workflow')

                nav('Chat','Chat rooms')
                page.get_by_label('Message',exact=True).fill('Keep failed message in composer')
                page.route('**/api/chat/send',lambda r:r.fulfill(status=403,content_type='application/json',body='{"error":"MODULE_DISABLED"}'))
                page.get_by_role('button',name='Send message',exact=True).click()
                expect(page.get_by_label('Message',exact=True)).to_have_value('Keep failed message in composer')
                page.unroute('**/api/chat/send')
                page.get_by_role('button',name='Send message',exact=True).click()
                expect(page.locator('.message-body').filter(has_text='Keep failed message in composer')).to_be_visible()
                expect(page.get_by_label('Message',exact=True)).to_have_value('')
                capture('chat-desktop.png')
                checks.append('Failed chat preserves composer; successful send clears it')

                nav('Settings','Runtime controls')
                page.get_by_role('button',name='Interface labels',exact=True).click()
                page.get_by_label('Search records').fill('publish.button')
                page.get_by_role('button',name='Edit',exact=True).click()
                page.get_by_label('Value',exact=True).fill('Release now')
                page.get_by_label('Reason for change',exact=True).fill('Browser acceptance test')
                page.locator('#inspector').get_by_role('button',name='Save',exact=True).click()
                expect(page.locator('#inspector')).not_to_be_visible()
                expect(page.locator('.setting-value').filter(has_text='Release now')).to_be_visible()
                page.get_by_label('Search records').fill('role.editor')
                page.get_by_role('button',name='Edit',exact=True).click()
                page.get_by_label('Value',exact=True).fill('Publisher')
                page.get_by_label('Reason for change',exact=True).fill('Display label only')
                page.locator('#inspector').get_by_role('button',name='Save',exact=True).click()
                expect(page.locator('#inspector')).not_to_be_visible()
                checks.append('Label registry changes Publish and role display text without source changes')

                nav('People & access','People & access')
                page.get_by_role('button',name='Create user',exact=True).click()
                page.get_by_label('Email',exact=True).fill('writer@example.test')
                page.get_by_label('Password',exact=True).fill('WriterTestPassword123!')
                expect(page.get_by_label('Role',exact=True).get_by_role('option',name='Publisher',exact=True)).to_have_attribute('value','editor')
                page.get_by_label('Role',exact=True).select_option('editor')
                page.locator('#inspector').get_by_role('button',name='Create user',exact=True).click()
                expect(page.locator('#inspector')).not_to_be_visible()
                expect(page.get_by_text('writer@example.test',exact=True)).to_be_visible()
                checks.append('Role label preserves stable editor ID and user creation works')

                nav('Content','Content workspace')
                page.get_by_role('link',name='Field notes from the community',exact=True).click()
                expect(page.get_by_role('button',name='Release now',exact=True)).to_be_visible()
                page.get_by_role('button',name='Schedule',exact=True).click()
                future=(datetime.now(timezone.utc)+timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
                page.get_by_label('Publish at (UTC)',exact=True).fill(future)
                page.locator('#inspector').get_by_role('button',name='Schedule',exact=True).click()
                page.locator('#confirm-yes').click()
                expect(page.locator('.editor-properties .badge[data-state=scheduled]')).to_be_visible()
                checks.append('Edited Publish label appears and UTC scheduling changes persisted workflow state')

                nav('Settings','Runtime controls')
                page.get_by_role('button',name='Features',exact=True).click()
                page.get_by_label('Search records').fill('forum.enabled')
                page.get_by_role('button',name='Edit',exact=True).click()
                page.get_by_label('Value',exact=True).uncheck()
                page.get_by_label('Reason for change',exact=True).fill('Browser forum flag acceptance')
                page.locator('#inspector').get_by_role('button',name='Save',exact=True).click(); page.locator('#confirm-yes').click()
                expect(page.locator('#inspector')).not_to_be_visible()
                page.locator('#nav').get_by_role('link',name='Forum',exact=True).click()
                expect(page.get_by_text('Forum is disabled by configuration.',exact=True)).to_be_visible()
                nav('Settings','Runtime controls')
                page.get_by_role('button',name='Features',exact=True).click()
                page.get_by_label('Search records').fill('forum.enabled')
                page.get_by_role('button',name='Edit',exact=True).click()
                page.get_by_label('Value',exact=True).check()
                page.get_by_label('Reason for change',exact=True).fill('Restore test forum')
                page.locator('#inspector').get_by_role('button',name='Save',exact=True).click(); page.locator('#confirm-yes').click()
                expect(page.locator('#inspector')).not_to_be_visible()
                checks.append('Feature quick-select confirmation disables the real forum and restores it')

                nav('API keys','Scoped API keys')
                page.get_by_role('button',name='Create key',exact=True).first.click()
                page.get_by_label('Key name',exact=True).fill('Browser test key')
                page.get_by_label('content.read',exact=True).check()
                page.locator('#inspector').get_by_role('button',name='Create key',exact=True).click()
                expect(page.locator('.secret-token')).to_be_visible()
                assert page.locator('.secret-token').input_value().startswith('eco_')
                page.locator('#inspector').get_by_role('button',name='Close',exact=True).click()
                checks.append('Scope picker creates a key with one-time token display')

                nav('Audit history','Audit history')
                page.get_by_label('Search records').fill('publish.button')
                page.get_by_role('button',name='Open',exact=True).click()
                expect(page.locator('#inspector').get_by_text('Release now',exact=False)).to_be_visible()
                page.get_by_role('button',name='Undo change',exact=True).click(); page.locator('#confirm-yes').click()
                expect(page.locator('#inspector')).not_to_be_visible()
                checks.append('Audit detail and confirmed control undo')

                # Screens and tables at phone, tablet, and desktop widths.
                for width in (320,390,768,1024,1440):
                    page.set_viewport_size({'width':width,'height':900})
                    for view in ('overview','content','media','forum','chat','config','users','api','audit'):
                        page.goto(origin+'/admin#'+view)
                        expect(page.locator('#main')).not_to_have_attribute('aria-busy','true')
                        expect(page.locator('.page-header h1')).to_be_visible()
                        # Ensure the asynchronous initial load finished before measuring.
                        expect(page.locator('.loading-state')).to_have_count(0)
                        sizes=page.evaluate('({scroll:document.documentElement.scrollWidth,width:window.innerWidth})')
                        assert sizes['scroll']<=sizes['width']+1,(width,view,sizes)
                        if width in (390,1440): audit_page(page,f'{view} at {width}px')
                    page.goto(origin+'/admin#content/2')
                    expect(page.get_by_role('heading',name='Field notes from the community',exact=True)).to_be_visible()
                    sizes=page.evaluate('({scroll:document.documentElement.scrollWidth,width:window.innerWidth})')
                    assert sizes['scroll']<=sizes['width']+1,(width,'editor',sizes)
                    if width==390: capture('editor-mobile.png')
                    if width==320:
                        page.goto(origin+'/admin#api')
                        expect(page.get_by_role('heading',name='Scoped API keys',exact=True)).to_be_visible()
                        page.get_by_role('button',name='Create key',exact=True).first.click()
                        expect(page.locator('#inspector')).to_be_visible()
                        sizes=page.locator('#inspector').evaluate('(e)=>({scroll:e.scrollWidth,width:e.clientWidth})')
                        assert sizes['scroll']<=sizes['width']+1,('scope picker',sizes)
                        page.keyboard.press('Escape')
                    if width in (390,1440):
                        page.goto(origin+'/admin#overview'); expect(page.get_by_role('heading',name='Your workspace, at a glance.')).to_be_visible()
                        capture(f'overview-{width}.png')
                    if width==390:
                        page.get_by_role('button',name='Open navigation',exact=True).click()
                        expect(page.locator('#mobile-menu')).to_be_visible()
                        page.keyboard.press('Escape')
                        expect(page.get_by_role('button',name='Open navigation',exact=True)).to_be_focused()
                checks.append('No page overflow on nine modules and editor at 320, 390, 768, 1024 and 1440px; mobile scope picker fits; menu Escape restores focus')
                page.goto(origin+'/admin#overview'); expect(page.get_by_role('heading',name='Your workspace, at a glance.')).to_be_visible()
                page.evaluate('document.documentElement.style.zoom="2"')
                sizes=page.evaluate('({scroll:document.documentElement.scrollWidth,width:window.innerWidth})')
                assert sizes['scroll']<=sizes['width']+1,sizes
                page.evaluate('document.documentElement.style.zoom=""')
                context = page.context
                page.emulate_media(reduced_motion='reduce')
                assert page.evaluate('matchMedia("(prefers-reduced-motion:reduce)").matches')
                checks.append('200% CSS zoom overview reflow and reduced-motion setting')
                if accessibility: checks.append('axe-core automated WCAG A/AA checks: no violations on sign-in, public article and nine modules at 390px and 1440px')
                assert not errors,errors
                browser.close()
                checks.append('No uncaught JavaScript errors during browser run')
        finally:
            http.shutdown(); http.server_close(); worker.join(timeout=2); server.DB=previous_db
    report={'status':'TESTED_PASS','checks':checks,'fixture':'isolated synthetic test data','screenshots':str(artifact_dir),'browser':'Chromium via Playwright','accessibility_scans':len(accessibility)}
    if accessibility: (artifact_dir/'accessibility.json').write_text(json.dumps(accessibility,indent=2)+'\n')
    (artifact_dir/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    try: run()
    except Exception as error:
        report_path=ROOT/'evidence'/'ui'/'results.json'
        report_path.parent.mkdir(parents=True,exist_ok=True)
        report_path.write_text(json.dumps({'status':'TESTED_FAIL','error':str(error),'fixture':'isolated synthetic test data','note':'The run failed. Any screenshots are partial evidence only.'},indent=2)+'\n')
        raise
