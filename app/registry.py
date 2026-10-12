"""Authoritative declarations; persisted values live in controls/actions."""
SETTINGS = {
 'site.title': dict(key='site.title', label='setting.site.title', kind='text', default='Ecosystem CMS', scope='global', validate={'min':1,'max':120}, editable_by='config.write', restart=False),
 'chat.retention_days': dict(key='chat.retention_days', label='setting.chat.retention_days', kind='number', default=30, scope='global', validate={'min':1,'max':3650}, editable_by='config.write', restart=False),
 'media.max_bytes': dict(key='media.max_bytes', label='setting.media.max_bytes', kind='number', default=2097152, scope='global', validate={'min':1024,'max':8388608}, editable_by='config.write', restart=False),
 'api.requests_per_minute': dict(key='api.requests_per_minute', label='setting.api.requests_per_minute', kind='number', default=120, scope='global', validate={'min':10,'max':10000}, editable_by='config.write', restart=False),
}
FLAGS = {f'{m}.enabled': {'key':f'{m}.enabled','default':True,'module':m} for m in ('forum','chat')}
ACTIONS = {}
def action(key, public=False):
 ACTIONS[key]={'key':key,'module':key.split('.')[0],'description':key,'public':public}
for key in ('config.read','config.write','audit.read','auth.users.read','auth.users.write','auth.permissions.write','auth.session','content.read','content.write','content.publish','media.read','media.write','forum.read','forum.write','forum.moderate','chat.read','chat.write','chat.manage','admin.read','api.keys.read','api.keys.write'):
 action(key)
for key in ('auth.login','public.read','api.health'):
 action(key, True)
ROLES = {
 'admin': set(ACTIONS)-{'auth.login','public.read','api.health'},
 'editor': {'auth.session','content.read','content.write','content.publish','media.read','media.write','forum.read','forum.write','chat.read','chat.write','admin.read'},
 'moderator': {'auth.session','forum.read','forum.write','forum.moderate','chat.read','chat.write','chat.manage','admin.read'},
 'member': {'auth.session','forum.read','forum.write','chat.read','chat.write'},
}
# All application-owned interface strings are label keys. User content is not a label.
LABELS = {
 'site.heading':'Ecosystem CMS','publish.button':'Publish','role.admin':'Administrator','role.editor':'Editor','role.moderator':'Moderator','role.member':'Member',
 'setting.site.title':'Site title','setting.chat.retention_days':'Chat retention (days)','setting.media.max_bytes':'Maximum upload bytes','setting.api.requests_per_minute':'API requests per minute',
 'forum.enabled':'Forum enabled','chat.enabled':'Chat enabled',
 'nav.overview':'Overview','nav.content':'Content','nav.media':'Media','nav.forum':'Forum','nav.chat':'Chat','nav.config':'Control plane','nav.users':'People & access','nav.api':'API keys','nav.audit':'Audit history',
 'login.title':'Sign in','email':'Email','password':'Password','login.button':'Sign in','logout':'Sign out','public.link':'View public site','refresh':'Refresh','save':'Save','cancel':'Cancel','confirm':'Confirm','confirm.title':'Confirm consequential action','confirm.body':'This changes stored data. Continue?',
 'loading':'Loading…','success':'Server completed the operation.','error':'Operation failed.','retry':'Retry','empty':'No records to display.','no.access':'Your role does not grant access to this operation.','enabled':'Enabled','disabled':'Disabled','not.found':'Page not found','health.ok':'Healthy',
 'overview.title':'Operations','overview.description':'Live counts from persisted records. Select a module to manage it.','count.entries':'Content entries','count.media':'Media assets','count.pending':'Pending moderation','count.messages':'Retained messages','count.users':'Active users','workflow.title':'Operation stages','step.validate':'Validate input','step.submit':'Submit to server','step.complete':'Confirm persisted result','pending':'Pending','active':'Active','complete':'Completed','failed':'Failed','blocked':'Blocked',
 'content.title':'Content workspace','content.create':'Create draft','content.type':'Content type','content.slug':'URL slug','content.name':'Title','content.body':'Body (plain text)','content.fields':'Custom fields (JSON object)','content.references':'Media IDs (comma separated)','content.types':'Content types','content.type.id':'Type identifier','content.type.schema':'Fields (JSON: name → text, number, boolean)','content.type.create':'Create type','content.review':'Submit for review','content.schedule':'Schedule','content.when':'Publish at (UTC)','content.archive':'Archive','content.revisions':'Revisions','content.restore':'Restore draft','content.preview':'Preview draft','content.status':'Status','content.version':'Version','content.edit':'Edit draft','draft':'Draft','review':'In review','scheduled':'Scheduled','published':'Published','archived':'Archived',
 'media.title':'Media library','media.upload':'Upload image','media.file':'PNG, JPEG, GIF or WebP image','media.alt':'Alternative text','media.transform':'Create resized copy','media.width':'Width in pixels','media.delete':'Delete asset','media.references':'Referenced by entries','media.name':'File name','media.limit':'Upload limit in bytes',
 'forum.title':'Forum','forum.category':'Category','forum.category.create':'Create category','forum.thread.create':'Create thread','forum.reply':'Reply','forum.approve':'Approve','forum.reject':'Reject','forum.lock':'Lock thread','forum.unlock':'Unlock thread','forum.disabled':'Forum is disabled by configuration.','forum.body':'Message','forum.state':'Moderation state','approved':'Approved','rejected':'Rejected',
 'chat.title':'Chat rooms','chat.room.create':'Create room','chat.room':'Room','chat.send':'Send message','chat.message':'Message','chat.presence':'Members present','chat.prune':'Apply retention now','chat.disabled':'Chat is disabled by configuration.','chat.polling':'Refresh messages manually. Presence expires after 90 seconds.','chat.retention':'Retention days','chat.delete':'Delete message',
 'config.title':'Runtime controls','config.settings':'Settings','config.flags':'Feature flags','config.labels':'Editable labels','config.permissions':'Role permissions','config.reason':'Reason for change','config.undo':'Undo change','config.key':'Stable key','config.value':'Value','config.version':'Version','config.filter':'Find a control',
 'users.title':'People & access','users.create':'Create user','users.role':'Role','users.active':'Account active','users.update':'Update access','users.password':'New password (leave blank to keep)','users.id':'User ID',
 'api.title':'Scoped API keys','api.create':'Create key','api.name':'Key name','api.scopes':'Scopes (registered actions)','api.expiry':'Validity in days','api.revoke':'Revoke key','api.token':'Copy this token now; it will not be shown again.','api.revoked':'Revoked','api.expires':'Expires','api.warning':'Keys inherit the owner’s current permissions. Revocation is immediate.',
 'audit.title':'Audit history','audit.actor':'Actor','audit.operation':'Operation','audit.time':'Time','audit.reason':'Reason','audit.before':'Before','audit.after':'After','public.empty':'No published content.','public.home':'Home','public.description':'Published content from this ecosystem.',
 'label.error.UNAUTHENTICATED':'Sign in to continue.','label.error.PERMISSION_DENIED':'Your account lacks permission.','label.error.VERSION_CONFLICT':'Another change occurred. Refresh and retry.','label.error.MODULE_DISABLED':'This module is disabled.','label.error.INVALID_VALUE':'Check the value and retry.','label.error.RATE_LIMITED':'Too many requests. Wait a minute and retry.','label.error.CSRF_REQUIRED':'Session validation failed. Sign in again.','label.error.INTERNAL_ERROR':'Server error. Retry or inspect the server log.',
}
