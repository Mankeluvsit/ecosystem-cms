'use strict';
// Buildless UI: registered labels, same-origin requests, no credentials in storage.
let L = {}, S = {}, me = null, csrf = '', busy = false, dirty = false;
let renderId = 0, fieldId = 0, category = 'settings', selectedRoom = 1, acceptedHash = location.hash;
let appliedTokens = [];
const $ = id => document.getElementById(id);
const t = key => L[key] ?? key;
const can = action => me?.permissions.includes(action) ?? false;
const views = {
  overview: ['nav.overview', 'admin.read', 'overview'],
  content: ['nav.content', 'content.read', 'content'],
  media: ['nav.media', 'media.read', 'media'],
  forum: ['nav.forum', 'forum.read', 'forum'],
  chat: ['nav.chat', 'chat.read', 'chat'],
  config: ['studio.settings', 'config.read', 'settings'],
  users: ['nav.users', 'auth.users.read', 'users'],
  api: ['nav.api', 'api.keys.read', 'key'],
  audit: ['nav.audit', 'audit.read', 'audit'],
};
const paths = {
  leaf: ['M5 19C3 9 10 3 20 4c1 10-5 17-15 15Z', 'M5 19 15 9', 'M10 14v-4', 'M10 14h4'],
  overview: ['M3 3h7v7H3z', 'M14 3h7v7h-7z', 'M3 14h7v7H3z', 'M14 14h7v7h-7z'],
  content: ['M6 3h9l4 4v14H6z', 'M14 3v5h5', 'M9 12h7', 'M9 16h7'],
  media: ['M3 4h18v16H3z', 'M3 16l6-6 4 4 3-3 5 5', 'M16 7h.01'],
  forum: ['M3 4h18v12H9l-5 5v-5H3z', 'M7 8h10', 'M7 12h6'],
  chat: ['M3 4h14v11H8l-4 4v-4H3z', 'M17 8h4v11h-3l-3 3v-3h-4'],
  settings: ['M12 3v4', 'M12 17v4', 'M3 12h4', 'M17 12h4', 'M5.6 5.6l3 3', 'M15.4 15.4l3 3', 'M5.6 18.4l3-3', 'M15.4 8.6l3-3', 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8'],
  users: ['M8 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8', 'M1 21v-3a7 7 0 0 1 14 0v3', 'M16 4a4 4 0 0 1 0 8', 'M17 15a6 6 0 0 1 5 6'],
  key: ['M8 3a5 5 0 1 0 0 10A5 5 0 0 0 8 3Z', 'M12 12l9 9', 'M17 17l3-3', 'M19 19l3-3'],
  audit: ['M4 5h16v16H4z', 'M8 2v6', 'M16 2v6', 'M8 12h8', 'M8 16h5'],
  plus: ['M12 5v14', 'M5 12h14'], close: ['M6 6l12 12', 'M18 6 6 18'],
  arrow: ['M5 12h14', 'M14 7l5 5-5 5'], back: ['M19 12H5', 'M10 7l-5 5 5 5'],
  external: ['M14 3h7v7', 'M21 3l-11 11', 'M10 3H3v18h18v-7'],
  chevron: ['M9 5l7 7-7 7'], menu: ['M3 6h18', 'M3 12h18', 'M3 18h18'],
  check: ['M5 12l4 4L19 6'], clock: ['M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18', 'M12 7v5l3 2'],
  warning: ['M12 3 2 21h20Z', 'M12 9v5', 'M12 17h.01'], upload: ['M12 16V3', 'M7 8l5-5 5 5', 'M4 16v5h16v-5'],
  edit: ['M16 3l5 5-12 12H4v-5Z', 'M13 6l5 5'], logout: ['M9 3H3v18h6', 'M8 12h13', 'M16 7l5 5-5 5'],
  refresh: ['M20 10a8 8 0 1 0-1 7', 'M20 3v7h-7'], send: ['M3 3l19 9-19 9 4-9Z', 'M7 12h15'],
};
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === 'class') node.className = value;
    else if (key === 'text') node.textContent = value;
    else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
    else if (value !== false && value != null) node.setAttribute(key, value === true ? '' : value);
  }
  for (const child of children.flat(Infinity)) {
    if (child != null) node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}
function icon(name) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 24 24'); svg.setAttribute('class', 'icon'); svg.setAttribute('aria-hidden', 'true');
  for (const d of paths[name] ?? paths.content) {
    const path = document.createElementNS(svg.namespaceURI, 'path'); path.setAttribute('d', d); svg.append(path);
  }
  return svg;
}
function btn(key, callback, options = {}) {
  const b = el('button', { type: 'button', class: 'btn ' + (options.primary ? 'btn-primary' : options.danger ? 'btn-danger' : options.quiet ? 'btn-quiet' : ''),
    'aria-label': options.iconOnly ? t(key) : null }, options.icon ? icon(options.icon) : null, options.iconOnly ? null : el('span', { text: t(key) }));
  b.addEventListener('click', async () => {
    if (busy) return;
    try { await callback(); } catch (error) { report(error); }
  });
  if (options.iconOnly) b.classList.add('icon-button');
  if (options.action && !can(options.action) || options.disabled) {
    b.disabled = true;
    const reason = options.reason ?? 'no.access';
    const id = 'reason-' + (++fieldId); b.setAttribute('aria-describedby', id);
    return el('span', { class: 'action-with-reason' }, b, el('small', { id, class: 'disabled-reason', text: t(reason) }));
  }
  return b;
}
function anchor(key, href, name = 'arrow', cls = '') {
  return el('a', { href, class: cls, 'aria-label': t(key) }, el('span', { text: t(key) }), icon(name));
}
function route() { return location.hash.slice(1).split('/').filter(Boolean); }
async function go(target) {
  if (busy) return;
  if (dirty && !await confirm('studio.discard.title', 'studio.discard.body')) return;
  dirty = false; if ($('inspector').open) $('inspector').close();
  if ($('mobile-menu').open) $('mobile-menu').close();
  if (location.hash === '#' + target) await load(); else location.hash = target;
}
async function reloadView() {
  if (dirty && !await confirm('studio.discard.title', 'studio.discard.body')) return;
  dirty = false; await load();
}
function date(value) {
  if (!value) return '—';
  const d = new Date(typeof value === 'number' ? value * 1000 : /Z$|[+]\d\d:\d\d$/.test(value) ? value : value.replace(' ', 'T') + 'Z');
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString(undefined, { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}
function badge(state) { return el('span', { class: 'badge', 'data-state': state }, icon(['published', 'approved', 'enabled', 'complete'].includes(state) ? 'check' : 'clock'), t(state === 'revoked' ? 'studio.key.revoked' : state)); }
function avatar(name) { return el('span', { class: 'avatar', 'aria-hidden': true, text: name.slice(0, 2).toUpperCase() }); }
function errorText(error) { return L['label.error.' + error.code] ?? (error.code ? t('studio.operation.failed') + ' (' + error.code + ')' : t('studio.connection.error')); }
async function req(path, data) {
  let response;
  try { response = await fetch(path, { method: data === undefined ? 'GET' : 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf }, body: data === undefined ? undefined : JSON.stringify(data) }); }
  catch { throw Object.assign(new Error('NETWORK'), { code: 'NETWORK' }); }
  const result = await response.json();
  if (!response.ok) throw Object.assign(new Error(result.error), { code: result.error, status: response.status });
  return result;
}
function applyTheme(tokens) {
  for (const key of appliedTokens) document.documentElement.style.removeProperty(key);
  appliedTokens = Object.keys(tokens ?? {});
  for (const [key, value] of Object.entries(tokens ?? {})) document.documentElement.style.setProperty(key, value);
}
function feedback(text, failed = false) {
  $('operation-status').hidden = false; $('operation-status').classList.toggle('error', failed);
  $('feedback').replaceChildren(el('div', { class: 'feedback-row' }, icon(failed ? 'warning' : busy ? 'clock' : 'check'), el('span', { text }), btn('studio.close', () => { $('operation-status').hidden = true; }, { icon: 'close', iconOnly: true, quiet: true })));
}
function report(error, form = null) {
  feedback(errorText(error), true);
  if (form) { const box = form.querySelector('.form-error'); if (box) { box.textContent = errorText(error); box.focus(); } }
}
function progress(states) {
  $('progress').replaceChildren(...states.map((state, i) => el('li', { 'data-state': state }, icon(state === 'complete' ? 'check' : state === 'failed' ? 'warning' : 'clock'), t(['studio.step.request', 'studio.step.confirm'][i]) + ': ' + t(state))));
}
async function mutate(path, data, success = 'studio.success.save') {
  if (busy) throw new Error('DUPLICATE_SUBMISSION');
  busy = true; progress(['active', 'pending']); feedback(t('studio.operation.pending'));
  const forms = [...document.querySelectorAll('form')];
  const buttons = forms.flatMap(f => [...f.querySelectorAll('button[type=submit]')]).map(b => [b, b.disabled]);
  buttons.forEach(([b]) => { b.disabled = true; });
  try {
    const result = await req(path, data); progress(['complete', 'complete']); busy = false; feedback(t(success));
    return result;
  } catch (error) { progress(['failed', 'blocked']); busy = false; report(error); throw error; }
  finally { busy = false; buttons.forEach(([b, disabled]) => { if (b.isConnected) b.disabled = disabled; }); }
}
async function confirm(title = 'confirm.title', description = 'confirm.body', target = '') {
  const dialog = $('confirmation');
  $('confirm-title').textContent = t(title);
  $('confirm-body').textContent = t(description) + (target ? '\n\n' + t('studio.confirm.target') + ': ' + target : '');
  $('confirm-cancel').textContent = t('cancel'); $('confirm-yes').textContent = t('confirm');
  $('confirm-yes').className = 'btn btn-primary'; $('confirm-cancel').className = 'btn';
  const previous = document.activeElement; dialog.returnValue = '';
  return new Promise(resolve => { dialog.addEventListener('close', () => { if (previous?.isConnected) previous.focus(); resolve(dialog.returnValue === 'confirm'); }, { once: true }); dialog.showModal(); $('confirm-cancel').focus(); });
}
function openDialog(titleKey, body, wide = false, titleData = null) {
  const dialog = $('inspector'); if (dialog.open) dialog.close();
  dialog.className = wide ? 'dialog-wide' : '';
  const previous = document.activeElement;
  dialog.replaceChildren(el('div', { class: 'dialog-header' }, el('h2', { id: 'inspector-title', text: titleData ?? t(titleKey) }), btn('studio.close', () => dialog.close(), { icon: 'close', iconOnly: true, quiet: true })), el('div', { class: 'dialog-body' }, body));
  dialog.addEventListener('close', () => { if (previous?.isConnected) previous.focus(); }, { once: true }); dialog.showModal();
}
function field(key, name, type = 'text', value = '', options = {}) {
  const id = 'field-' + (++fieldId); let input;
  if (type === 'textarea') input = el('textarea', { id, name, class: options.class ?? '' }, value);
  else if (type === 'select') input = el('select', { id, name }, (options.choices ?? []).map(choice => el('option', { value: choice.value, selected: String(choice.value) === String(value), text: choice.label })));
  else input = el('input', { id, name, type, value: type === 'checkbox' ? null : value, checked: type === 'checkbox' && Boolean(value), class: options.class ?? '' });
  if (options.required) input.required = true;
  if (options.disabled) input.disabled = true;
  for (const property of ['min', 'max', 'maxlength', 'minlength', 'step', 'autocomplete', 'accept']) if (options[property] != null) input.setAttribute(property, options[property]);
  const hintId = id + '-hint';
  input.setAttribute('aria-labelledby', id + '-label');
  if (options.hint) input.setAttribute('aria-describedby', hintId);
  return el('label', { for: id, class: type === 'checkbox' ? 'checkbox-field' : 'field' }, type === 'checkbox' ? input : null,
    el('span', { class: 'field-label', id: id + '-label', text: options.literal ?? t(key) }), type === 'checkbox' ? null : input,
    options.hint ? el('small', { class: 'field-hint', id: hintId, text: t(options.hint) }) : null);
}
function values(form) {
  const result = {};
  for (const input of form.querySelectorAll('[name]')) {
    if (input.type === 'checkbox') result[input.name] = input.checked;
    else if (input.type === 'number') result[input.name] = input.value === '' ? null : Number(input.value);
    else result[input.name] = input.value;
  }
  return result;
}
function form(fields, key, callback, action = null, options = {}) {
  const f = el('form', { class: options.class ?? '' }, fields, el('div', { class: 'form-error', role: 'alert', tabindex: '-1' }));
  const submit = el('button', { type: 'submit', class: 'btn btn-primary' }, options.icon ? icon(options.icon) : null, t(key));
  if (action && !can(action)) submit.disabled = true;
  f.append(el('div', { class: 'form-actions' }, options.cancel === false ? null : btn('cancel', () => $('inspector').close()), submit));
  if(action&&!can(action))f.append(el('p',{class:'disabled-reason',text:t('no.access')}));
  let submitting = false;
  f.addEventListener('submit', async event => {
    event.preventDefault(); if (busy || submitting) return;
    submitting = true; const wasDisabled = submit.disabled; submit.disabled = true;
    f.querySelector('.form-error').textContent = '';
    try { await callback(values(f), f); } catch (error) { report(error, f); }
    finally { submitting = false; if (submit.isConnected) submit.disabled = wasDisabled; }
  });
  return f;
}
function header(key, description, ...actions) {
  return el('div', { class: 'page-header' }, el('div', { class: 'page-heading' }, el('p', { class: 'eyebrow', text: t('studio.workspace') }), el('h1', { text: t(key) }), description ? el('p', { class: 'description', text: t(description) }) : null), el('div', { class: 'actions' }, actions));
}
function panel(key, children, action = null) { return el('section', { class: 'panel' }, el('div', { class: 'panel-title' }, el('h2', { text: t(key) }), action), children); }
function empty(description = 'empty', action = null, name = 'content', title = 'studio.no.records') { return el('div', { class: 'empty' }, el('div', { class: 'empty-icon' }, icon(name)), el('h2', { text: t(title) }), el('p', { text: t(description) }), action); }
function loading() { return el('div', { class: 'loading-state', role: 'status' }, el('span', { class: 'spinner', 'aria-hidden': true }), t('loading')); }
function table(columns, rows, captionKey = 'studio.records') {
  if (!rows.length) return empty('studio.no.results.description', null, 'content', 'studio.no.results');
  const head = el('thead', {}, el('tr', {}, columns.map(c => el('th', { scope: 'col', text: t(c) }))));
  const body = el('tbody', {}, rows.map(row => el('tr', {}, row.map((cell, i) => el('td', { 'data-label': t(columns[i]) }, cell)))));
  const dataTable = el('table', { class: 'responsive-table' }, el('caption', { class: 'sr-only', text: t(captionKey) }), head, body);
  return el('div', { class: 'collection' }, el('div', { class: 'table-scroll' }, dataTable), el('div', { class: 'table-footer', text: t('studio.records') + ': ' + rows.length }));
}
function searchBar(onChange, filters = []) {
  const search = field('studio.search', 'search');
  search.querySelector('input').addEventListener('input', onChange);
  for (const filter of filters) filter.querySelector('select').addEventListener('change', onChange);
  return el('div', { class: 'toolbar' }, search, filters);
}
function navItems() {
  const groups = [['studio.workspace', ['overview', 'content', 'media']], ['studio.community', ['forum', 'chat']], ['studio.administration', ['users', 'config', 'api', 'audit']]];
  const current = route()[0] ?? 'overview';
  return groups.map(([label, modules]) => {
    const allowed = modules.filter(v => can(views[v][1])); if (!allowed.length) return null;
    return el('div', { class: 'nav-group' }, el('p', { class: 'nav-group-label', text: t(label) }), allowed.map(view => {
      const a = el('a', { href: '#' + view, class: 'nav-item', 'aria-current': current === view ? 'page' : null }, icon(views[view][2]), t(views[view][0]));
      a.addEventListener('click', event => { event.preventDefault(); go(view); }); return a;
    }));
  });
}
function chrome() {
  document.body.classList.toggle('signed-out', !me); document.title = t('studio.name'); $('skip').textContent = t('studio.skip');
  $('brand').replaceChildren(el('a', { class: 'brand', href: '#overview' }, el('span', { class: 'brand-mark' }, icon('leaf')), el('span', {}, el('span', { class: 'brand-name', text: t('site.heading') }), el('small', { class: 'brand-subtitle', text: t('studio.subtitle') }))));
  $('brand').querySelector('a').addEventListener('click', event => { event.preventDefault(); go('overview'); });
  $('nav').setAttribute('aria-label', t('studio.menu')); $('nav').replaceChildren(...navItems().filter(Boolean));
  $('sidebar-footer').className = 'sidebar-bottom';
  $('sidebar-footer').replaceChildren(...(me?[el('div', { class: 'account' }, avatar(me.user.email), el('div', { class: 'account-copy' }, el('strong', { text: me.user.email }), el('small', { text: t('role.' + me.user.role) }))), el('a', { href: '#logout', class: 'nav-item', onclick: event => { event.preventDefault(); signOut(); } }, icon('logout'), t('logout'))]:[]));
  const view = route()[0] ?? 'overview';
  $('header').replaceChildren(el('div', { class: 'breadcrumb' }, me ? btn('studio.menu', mobileMenu, { icon: 'menu', iconOnly: true, quiet: true }) : icon('leaf'), el('span', { text: t('studio.workspace') }), me ? icon('chevron') : null, el('strong', { text: me ? t(views[view]?.[0] ?? 'studio.name') : t('studio.name') })), el('div', { class: 'topbar-actions' }, anchor('public.link', '/', 'external'), me ? avatar(me.user.email) : null));
  const menu = $('header').querySelector('.icon-button'); if (menu) menu.classList.add('menu-toggle');
}
function mobileMenu() {
  const dialog = $('mobile-menu');
  dialog.replaceChildren(el('div', { class: 'dialog-header' }, el('h2', { id: 'mobile-menu-title', text: t('site.heading') }), btn('studio.close', () => dialog.close(), { iconOnly: true, icon: 'close' })), el('div', { class: 'dialog-body' }, navItems(), btn('logout', signOut, { icon: 'logout' })));
  dialog.showModal();
}
async function signOut() {
  try {
    if (dirty && !await confirm('studio.discard.title', 'studio.discard.body')) return;
    await mutate('/api/logout', {}); me = null; csrf = ''; dirty = false;
    if ($('mobile-menu').open) $('mobile-menu').close(); chrome(); loginView();
  } catch (error) { report(error); }
}
function loginView() {
  const f = form([el('h2', { text: t('studio.login.welcome') }), el('p', { class: 'muted', text: t('studio.login.note') }), field('email', 'email', 'email', '', { required: true, autocomplete: 'username' }), field('password', 'password', 'password', '', { required: true, autocomplete: 'current-password' })], 'login.button', async data => {
    const result = await mutate('/api/login', data, 'studio.success.login'); csrf = result.csrf; me = await req('/api/me');
    const first = Object.keys(views).find(v => can(views[v][1])) ?? 'overview';
    chrome(); await go(first);
  }, null, { class: 'panel login-form', cancel: false });
  $('main').replaceChildren(el('div', { class: 'login-layout' }, el('section', { class: 'login-intro' }, el('div', { class: 'brand-mark' }, icon('leaf')), el('p', { class: 'eyebrow', text: t('studio.name') }), el('h1', { text: t('studio.login.heading') }), el('p', { text: t('studio.login.description') })), f));
}
async function load() {
  if (!me) return;
  const id = ++renderId; const main = $('main'); main.setAttribute('aria-busy', 'true');
  let indicator = loading(); main.append(indicator);
  try {
    const boot = await req('/api/public/bootstrap'); L = boot.labels; applyTheme(boot.theme_tokens);
    me = await req('/api/me'); csrf = me.csrf;
    if (can('config.read')) S = await req('/api/state'); else S = {};
    let parts = route(), view = parts[0] ?? 'overview';
    if (!views[view] || !can(views[view][1])) view = Object.keys(views).find(v => can(views[v][1])) ?? 'overview';
    const page = await ({ overview, content, media, forum, chat, config, users, api, audit }[view])(parts[1]);
    if (id !== renderId) return;
    chrome(); main.replaceChildren(page); main.focus({ preventScroll: true });
  } catch (error) {
    if (id !== renderId) return;
    if (error.status === 401) { me = null; csrf = ''; dirty = false; chrome(); loginView(); }
    else {
      main.replaceChildren(header(views[route()[0]]?.[0] ?? 'error', null), empty(error.code === 'MODULE_DISABLED' ? route()[0] + '.disabled' : 'error', btn('retry', load, { icon: 'refresh' }), 'warning'));
      if (error.code === 'MODULE_DISABLED' && can('config.read')) main.append(btn('studio.settings', () => go('config')));
      report(error);
    }
  } finally { indicator.remove(); if (id === renderId) main.removeAttribute('aria-busy'); }
}
function done() { dirty = false; if ($('inspector').open) $('inspector').close(); return load(); }
window.addEventListener('hashchange', async () => {
  if (dirty && !await confirm('studio.discard.title', 'studio.discard.body')) {
    history.replaceState(null, '', location.pathname + location.search + acceptedHash); return;
  }
  dirty = false; acceptedHash = location.hash; $('operation-status').hidden = true; load();
});
window.addEventListener('beforeunload', event => { if (dirty) { event.preventDefault(); event.returnValue = ''; } });

async function overview() {
  const page = el('div', {}, header('studio.overview', 'studio.overview.description', can('content.write') ? btn('content.create', () => go('content/new'), { primary: true, icon: 'plus' }) : null));
  const jobs = [req('/api/dashboard'), can('content.read') ? req('/api/content/entries') : [], can('audit.read') ? req('/api/audit') : [], can('forum.moderate') ? req('/api/forum/moderation').catch(e => e.code === 'MODULE_DISABLED' ? [] : Promise.reject(e)) : []];
  const [counts, entries, events, threads] = await Promise.all(jobs);
  const summaries = el('div', { class: 'summary-strip' });
  for (const [key, target] of [['entries', 'content'], ['media', 'media'], ['pending', 'forum'], ['messages', 'chat'], ['users', 'users']]) {
    if (counts[key] == null || !can(views[target][1])) continue;
    const action = anchor('studio.manage', '#' + target); action.addEventListener('click', e => { e.preventDefault(); go(target); });
    summaries.append(el('div', { class: 'summary-item' }, el('div', { class: 'summary-label' }, icon(views[target][2]), t('count.' + key)), el('strong', { class: 'metric', text: counts[key] }), action));
  }
  page.append(summaries);
  const left = el('div', { class: 'stack' });
  if (can('content.read')) {
    const recent = entries.slice(0, 6).map(entry => [entryLink(entry), badge(entry.status), date(entry.updated_at), btn('studio.open', () => go('content/' + entry.id), { icon: 'arrow', quiet: true })]);
    left.append(panel('studio.recent', recent.length ? table(['content.name', 'content.status', 'studio.updated', 'studio.action'], recent) : empty('studio.no.content', can('content.write') ? btn('content.create', () => go('content/new'), { primary: true, icon: 'plus' }) : null), btn('studio.view.all', () => go('content'), { quiet: true, icon: 'arrow' })));
  }
  if (can('forum.moderate')) {
    const pending = threads.filter(th => th.state === 'pending').slice(0, 5);
    left.append(panel('studio.review', pending.length ? pending.map(th => el('div', { class: 'thread' }, avatar(String(th.author_id)), el('div', { class: 'thread-copy' }, el('strong', { text: th.title }), el('small', { class: 'record-meta', text: t(th.kind === 'replies' ? 'forum.reply' : 'forum.title') + ' · ' + date(th.created_at) })), btn('studio.open', () => go('forum/' + th.thread_id), { icon: 'arrow', quiet: true }))) : empty('studio.no.review', null, 'check')));
  }
  if (!left.childElementCount) left.append(panel('studio.welcome', el('p', { class: 'muted', text: t('studio.overview.description') })));
  const right = el('div', { class: 'stack' });
  if (can('content.write')) right.append(el('div', { class: 'welcome-note' }, icon('leaf'), el('div', {}, el('h3', { text: t('studio.welcome') }), el('p', { text: t('studio.welcome.description') }))));
  if (can('audit.read')) right.append(panel('studio.activity', events.length ? events.slice(0, 6).map(event => el('div', { class: 'activity-item' }, el('span', { class: 'activity-dot' }, icon('audit')), el('div', { class: 'activity-copy' }, el('p', { text: eventSummary(event) }), el('small', { text: actorName(event.actor) + ' · ' + date(event.created_at) })))) : empty('studio.no.activity', null, 'audit'), btn('studio.view.all', () => go('audit'), { quiet: true, icon: 'arrow' })));
  page.append(el('div', { class: 'dashboard-grid' }, left, right)); return page;
}
function entryLink(entry) {
  const a = el('a', { href: '#content/' + entry.id, class: 'table-title', text: entry.title });
  a.addEventListener('click', event => { event.preventDefault(); go('content/' + entry.id); });
  return el('div', {}, a, el('small', { class: 'record-meta', text: '/' + entry.slug }));
}
async function content(id) {
  const [entries, types] = await Promise.all([req('/api/content/entries'), req('/api/content/types')]);
  if (id) {
    const entry = id === 'new' ? null : entries.find(e => e.id === Number(id));
    if (id !== 'new' && !entry) return empty('not.found', btn('studio.back', () => go('content')));
    return editor(entry, types);
  }
  const page = el('div', {}, header('content.title', 'studio.content.description', can('content.write') ? btn('content.create', () => go('content/new'), { primary: true, icon: 'plus' }) : null, can('content.write') ? btn('content.types', () => typeDialog(types), { icon: 'settings' }) : null));
  const status = field('content.status', 'status', 'select', '', { choices: [{ value: '', label: t('studio.all') }, ...['draft', 'review', 'scheduled', 'published', 'archived'].map(s => ({ value: s, label: t(s) }))] });
  const type = field('content.type', 'type', 'select', '', { choices: [{ value: '', label: t('studio.all') }, ...types.map(x => ({ value: x.id, label: x.id }))] });
  const results = el('div'); let toolbar;
  function filter() {
    const v = values(toolbar), query = v.search.toLowerCase();
    const rows = entries.filter(e => (!v.status || e.status === v.status) && (!v.type || e.type_id === v.type) && (e.title + ' ' + e.slug).toLowerCase().includes(query));
    results.replaceChildren(entries.length ? table(['content.name', 'content.type', 'content.status', 'studio.updated', 'studio.action'], rows.map(e => [entryLink(e), e.type_id, badge(e.status), date(e.updated_at), btn('studio.open', () => go('content/' + e.id), { icon: 'arrow', quiet: true })])) : empty('studio.no.content', can('content.write') ? btn('content.create', () => go('content/new'), { primary: true }) : null));
  }
  toolbar = searchBar(filter, [status, type]); page.append(toolbar, results); filter(); return page;
}
function typeDialog(types) {
  const list = el('div', { class: 'notice' }, el('span', { text: types.map(x => x.id).join(' · ') }));
  const f = form([list, field('content.type.id', 'id', 'text', '', { required: true, maxlength: 64 }), field('content.type.schema', 'fields', 'textarea', '{}', { required: true, hint: 'studio.types.schema.hint' })], 'content.type.create', async v => {
    let fields; try { fields = JSON.parse(v.fields); } catch { throw { code: 'INVALID_VALUE' }; }
    await mutate('/api/content/types', { id: v.id, fields }, 'studio.success.create'); await done();
  }, 'content.write'); openDialog('studio.types.advanced', f);
}
async function editor(entry, types) {
  const isNew = !entry; const editable = can('content.write') && (isNew || ['draft', 'review'].includes(entry.status));
  const media = can('media.read') ? await req('/api/media') : [];
  let mediaIds = [...(entry?.media_ids ?? [])];
  const page = el('div', {}, header(isNew ? 'content.create' : 'content.edit', null, btn('studio.back', () => go('content'), { icon: 'back' })));
  if (entry) page.querySelector('h1').textContent = entry.title;
  const f = el('form', { class: 'editor-form' });
  const left = el('section', { class: 'panel' }); const write = el('div');
  const title = field('content.name', 'title', 'text', entry?.title ?? '', { required: true, maxlength: 200, class: 'editor-title-input', disabled: !editable });
  const body = field('content.body', 'body', 'textarea', entry?.body ?? '', { class: 'body-input', maxlength: 200000, disabled: !editable });
  const custom = el('div');
  function fieldsFor(tid) {
    custom.replaceChildren(); const schema = JSON.parse(types.find(x => x.id === tid)?.fields ?? '{}');
    if (Object.keys(schema).length) custom.append(el('h3', { text: t('studio.fields') }));
    for (const [key, kind] of Object.entries(schema)) {
      custom.append(field(key, 'custom:' + key, kind === 'text' ? 'text' : kind === 'boolean' ? 'checkbox' : 'number', entry?.type_id === tid ? entry.fields[key] : kind === 'boolean' ? false : kind === 'number' ? 0 : '', { literal: key, disabled: !editable, step: kind === 'number' ? 'any' : null }));
    }
  }
  fieldsFor(entry?.type_id ?? types[0]?.id); write.append(title, body, custom);
  const preview = el('div', { hidden: true });
  const tabs = el('div', { class: 'editor-tabs' });
  for (const [key, target] of [['studio.write', write], ['studio.preview', preview]]) {
    const b = el('button', { type: 'button', class: 'tab', 'aria-pressed': target === write ? 'true' : 'false' }, t(key));
    b.addEventListener('click', () => {
      for (const child of tabs.children) child.setAttribute('aria-pressed', String(child === b));
      write.hidden = target !== write; preview.hidden = target !== preview;
      preview.replaceChildren(el('p', { class: 'field-hint', text: t('studio.preview.description') }), el('h2', { text: title.querySelector('input').value }), el('div', { class: 'preview', text: body.querySelector('textarea').value }));
    }); tabs.append(b);
  }
  left.append(tabs, write, preview);
  const properties = el('aside', { class: 'editor-properties' });
  const details = el('section', { class: 'panel' }, el('h2', { text: t('studio.properties') }));
  if (entry) details.append(badge(entry.status), el('p', { class: 'record-meta', text: t('content.version') + ' ' + entry.version + ' · ' + date(entry.updated_at) }));
  const type = field('content.type', 'type_id', 'select', entry?.type_id ?? types[0]?.id, { choices: types.map(x => ({ value: x.id, label: x.id })), disabled: !editable });
  type.querySelector('select').addEventListener('change', e => fieldsFor(e.target.value));
  details.append(type, field('content.slug', 'slug', 'text', entry?.slug ?? '', { required: true, maxlength: 64, disabled: !editable }));
  const selected = el('div', { class: 'media-selection' });
  function selectedImages() {
    selected.replaceChildren(...mediaIds.map(mid => {
      const asset = media.find(a => a.id === mid);
      return el('div', { class: 'selected-media' }, el('img', { src: '/api/media/file?id=' + mid, alt: asset?.alt ?? '' }), editable ? btn('studio.media.remove', () => { mediaIds = mediaIds.filter(id => id !== mid); dirty = true; mark.textContent = t('studio.unsaved'); selectedImages(); }, { iconOnly: true, icon: 'close' }) : null);
    }));
  }
  const mediaPanel = el('section', { class: 'panel' }, el('h2', { text: t('studio.media.selected') }), selected);
  if (editable && can('media.read')) mediaPanel.append(btn('studio.media.attach', () => mediaPicker(media, mediaIds, ids => { mediaIds = ids; dirty = true; mark.textContent = t('studio.unsaved'); selectedImages(); }), { icon: 'media' }));
  if (entry && !editable) details.append(el('p', { class: 'field-hint', text: t('studio.editor.readonly') }));
  properties.append(details, mediaPanel); selectedImages();
  f.append(el('div', { class: 'editor-layout' }, left, properties), el('div', { class: 'form-error', role: 'alert', tabindex: '-1' }));
  const mark = el('span', { class: 'unsaved', text: isNew ? '' : t('studio.saved') });
  const save = el('button', { type: 'submit', class: 'btn btn-primary' }, icon('check'), t('save')); save.disabled = !editable;
  const workflow = el('div', { class: 'actions' }, editable ? save : null);
  if (entry) {
    if (['draft', 'review'].includes(entry.status)) {
      if (entry.status === 'draft' && can('content.write')) workflow.append(btn('content.review', () => transition(entry, 'review'), { icon: 'arrow' }));
      if (can('content.publish') && can('content.write')) workflow.append(btn('publish.button', () => transition(entry, 'published'), { primary: true, icon: 'external' }), btn('content.schedule', () => scheduleDialog(entry), { icon: 'clock' }));
    }
    if (['archived', 'scheduled', 'review'].includes(entry.status) && can('content.write')) workflow.append(btn('content.restore', () => transition(entry, 'draft'), { icon: 'back' }));
    if (entry.status !== 'archived' && can('content.write') && (entry.status !== 'published' || can('content.publish'))) workflow.append(btn('content.archive', () => transition(entry, 'archived'), { danger: true }));
    workflow.append(btn('content.revisions', () => revisionsDialog(entry), { icon: 'audit' }));
    if (entry.status === 'published') workflow.append(anchor('public.link', '/p/' + entry.slug, 'external', 'btn'));
  }
  f.append(el('div', { class: 'editor-savebar' }, mark, workflow));
  f.addEventListener('input', () => { dirty = true; mark.textContent = t('studio.unsaved'); });
  f.addEventListener('submit', async event => {
    event.preventDefault(); if (busy || !editable) return;
    try {
      const v = values(f), fields = {}; for (const [key, val] of Object.entries(v)) if (key.startsWith('custom:')) fields[key.slice(7)] = val;
      const payload = { type_id: v.type_id, title: v.title, body: v.body, slug: v.slug, fields, media_ids: mediaIds };
      if (entry) Object.assign(payload, { id: entry.id, expected_version: entry.version });
      const result = await mutate(entry ? '/api/content/update' : '/api/content/create', payload, isNew ? 'studio.success.create' : 'studio.success.save');
      dirty = false; if (isNew) await go('content/' + result.id); else await load();
    } catch (error) { report(error, f); }
  });
  page.append(f); return page;
}
async function transition(entry, state) {
  if (dirty) { feedback(t('studio.unsaved'), true); return; }
  const warning = state === 'published' ? 'studio.confirm.publish' : state === 'archived' ? 'studio.confirm.archive' : state === 'draft' ? 'studio.confirm.restore' : 'confirm.body';
  if (!await confirm('confirm.title', warning, entry.title)) return;
  await mutate('/api/content/transition', { id: entry.id, expected_version: entry.version, status: state }, state === 'published' ? 'studio.success.publish' : 'studio.success.save'); await load();
}
function scheduleDialog(entry) {
  if (dirty) { feedback(t('studio.unsaved'), true); return; }
  const f = form([field('content.when', 'when', 'datetime-local', '', { required: true, hint: 'studio.schedule.hint' })], 'content.schedule', async v => {
    const stamp = Math.floor(new Date(v.when + 'Z').getTime() / 1000);
    if (!Number.isFinite(stamp) || stamp <= Date.now() / 1000) throw { code: 'INVALID_VALUE' };
    if (!await confirm('content.schedule', 'studio.schedule.hint', entry.title + ' · ' + v.when + ' UTC')) return;
    await mutate('/api/content/transition', { id: entry.id, status: 'scheduled', expected_version: entry.version, publish_at: stamp }); await done();
  }, 'content.publish'); openDialog('content.schedule', f);
}
async function revisionsDialog(entry) {
  const revisions = await req('/api/content/revisions?id=' + entry.id);
  const body = el('div');
  if (!revisions.length) body.append(empty('studio.revisions.empty', null, 'audit'));
  for (const revision of revisions) {
    const snap = JSON.parse(revision.snapshot);
    body.append(el('div', { class: 'setting-row' }, el('div', {}, el('strong', { text: snap.title }), el('p', { class: 'record-meta', text: date(revision.created_at) + ' · ' + t('audit.actor') + ' ' + revision.actor })), btn('content.restore', async () => {
      if (dirty) { feedback(t('studio.unsaved'), true); return; }
      if (!await confirm('content.restore', 'studio.confirm.restore', snap.title)) return;
      await mutate('/api/content/restore', { id: entry.id, revision_id: revision.id, expected_version: entry.version }); await done();
    }, { action: 'content.write', icon: 'back' })));
  }
  openDialog('content.revisions', body, true);
}
function mediaPicker(assets, ids, callback) {
  const picked = new Set(ids); const grid = el('div', { class: 'grid' });
  for (const asset of assets) {
    const b = el('button', { type: 'button', class: 'asset-picker', 'aria-pressed': String(picked.has(asset.id)), 'aria-label': asset.name }, el('img', { class: 'asset-image', src: '/api/media/file?id=' + asset.id, alt: asset.alt }), el('span', { text: asset.name }));
    b.addEventListener('click', () => { if (picked.has(asset.id)) picked.delete(asset.id); else picked.add(asset.id); b.setAttribute('aria-pressed', String(picked.has(asset.id))); }); grid.append(b);
  }
  openDialog('studio.media.attach', el('div', {}, assets.length ? grid : empty('studio.no.media', null, 'media'), el('div', { class: 'form-actions' }, btn('studio.media.use', () => { callback([...picked]); $('inspector').close(); }, { primary: true, icon: 'check' }))), true);
}

async function media() {
  const assets = await req('/api/media');
  const page = el('div', {}, header('media.title', 'studio.media.description', can('media.write') ? btn('media.upload', uploadDialog, { primary: true, icon: 'upload' }) : null));
  const result = el('div'); let toolbar;
  function filter() {
    const query = values(toolbar).search.toLowerCase(), matches = assets.filter(a => (a.name + ' ' + a.alt).toLowerCase().includes(query));
    result.replaceChildren(!assets.length ? empty('studio.no.media', can('media.write') ? btn('media.upload', uploadDialog, { primary: true, icon: 'upload' }) : null, 'media') : !matches.length ? empty('studio.no.results.description', null, 'media', 'studio.no.results') : el('div', { class: 'grid' }, matches.map(asset => el('article', { class: 'asset-card' }, el('img', { class: 'asset-image', src: '/api/media/file?id=' + asset.id, alt: asset.alt, loading: 'lazy' }), el('div', { class: 'asset-info' }, el('h2', { text: asset.name }), el('p', { text: asset.width + ' × ' + asset.height + ' · ' + t('media.references') + ': ' + asset.references_count }), btn('studio.media.inspect', () => assetDialog(asset), { icon: 'arrow' }))))));
  }
  toolbar = searchBar(filter); page.append(toolbar, result); filter(); return page;
}
function uploadDialog() {
  const f = form([el('div', { class: 'upload-zone' }, icon('upload'), el('p', { text: t('studio.upload.hint') }), field('media.file', 'file', 'file', '', { required: true, accept: 'image/png,image/jpeg,image/gif,image/webp' })), field('media.alt', 'alt', 'text', '', { required: true, maxlength: 1000 }), S.settings ? el('p', { class: 'field-hint', text: t('media.limit') + ': ' + S.settings['media.max_bytes'].value }) : null], 'media.upload', async (v, f) => {
    const file = f.querySelector('[type=file]').files[0];
    if (!file || S.settings && file.size > S.settings['media.max_bytes'].value) throw { code: file ? 'PAYLOAD_TOO_LARGE' : 'INVALID_IMAGE' };
    const data = await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result.split(',')[1]); reader.onerror = () => reject({ code: 'INVALID_IMAGE' }); reader.readAsDataURL(file); });
    await mutate('/api/media/upload', { name: file.name, alt: v.alt, data }, 'studio.success.upload'); await done();
  }, 'media.write'); openDialog('media.upload', f);
}
function assetDialog(asset) {
  const body = el('div', {}, el('img', { src: '/api/media/file?id=' + asset.id, alt: asset.alt, class: 'media-inspector-image' }), el('p', { class: 'muted', text: asset.alt }), el('p', { class: 'field-hint', text: t('media.references') + ': ' + asset.references_count }));
  body.append(form([field('media.width', 'width', 'number', Math.min(asset.width, 640), { min: 1, max: 4096, required: true })], 'media.transform', async v => { await mutate('/api/media/transform', { id: asset.id, width: v.width }, 'studio.success.create'); await done(); }, 'media.write', { cancel: false }));
  body.append(el('div', { class: 'form-actions' }, btn('media.delete', async () => { if (!await confirm('media.delete', 'studio.confirm.delete', asset.name)) return; await mutate('/api/media/delete', { id: asset.id }); await done(); }, { action: 'media.write', danger: true, disabled: asset.references_count > 0, reason: 'studio.media.inuse' })));
  openDialog('studio.media.inspect', body, false, asset.name);
}

async function forum(id) {
  const [categories, threads] = await Promise.all([req('/api/forum/categories'), req('/api/forum/threads')]);
  if (id) {
    const thread = threads.find(th => th.id === Number(id));
    if (!thread) return empty('not.found', btn('studio.back', () => go('forum')));
    return threadPage(thread, categories);
  }
  const page = el('div', {}, header('forum.title', 'studio.forum.description', can('forum.write') ? btn('forum.thread.create', () => threadDialog(categories), { primary: true, icon: 'plus' }) : null, can('forum.moderate') ? btn('studio.review', async () => {
    const queue = await req('/api/forum/moderation');
    openDialog('studio.review', queue.length ? el('div', {}, queue.map(item => el('div', { class: 'setting-row' }, el('div', {}, el('strong', { text: item.title }), el('p', { class: 'record-meta', text: t(item.kind === 'replies' ? 'forum.reply' : 'forum.title') + ' · ' + item.body.slice(0, 80) })), btn('studio.open', () => go('forum/' + item.thread_id), { icon: 'arrow' })))) : empty('studio.no.review', null, 'check'), true);
  }, { icon: 'check' }) : null));
  const categoryList = el('div', { class: 'category-list' }); const results = el('div'); let selected = 0, toolbar;
  const status = field('forum.state', 'status', 'select', '', { choices: [{ value: '', label: t('studio.all') }, ...['pending', 'approved', 'rejected'].map(s => ({ value: s, label: t(s) }))] });
  function filter() {
    const v = values(toolbar); const matches = threads.filter(th => (!selected || th.category_id === selected) && (!v.status || th.state === v.status) && (th.title + ' ' + th.body).toLowerCase().includes(v.search.toLowerCase()));
    results.replaceChildren(matches.length ? el('div', { class: 'collection' }, matches.map(th => el('article', { class: 'thread' }, el('span', { class: 'activity-dot' }, icon('forum')), el('div', { class: 'thread-copy' }, el('button', { type: 'button', class: 'table-row-action', onclick: () => go('forum/' + th.id), text: th.title }), el('div', { class: 'thread-meta' }, el('small', { class: 'muted', text: categories.find(c => c.id === th.category_id)?.name ?? '' }), el('small', { class: 'muted', text: date(th.created_at) }), th.locked ? el('small', { text: t('studio.locked') }) : null)), badge(th.state)))) : empty(threads.length ? 'studio.no.results.description' : 'studio.no.threads', can('forum.write') ? btn('forum.thread.create', () => threadDialog(categories), { primary: true }) : null, 'forum'));
  }
  for (const c of [{ id: 0, name: t('studio.all') }, ...categories]) {
    const b = el('button', { type: 'button', class: 'category-button', 'aria-pressed': String(c.id === selected) }, icon('forum'), c.name);
    b.addEventListener('click', () => { selected = c.id; for (const sibling of categoryList.children) sibling.setAttribute('aria-pressed', String(sibling === b)); filter(); }); categoryList.append(b);
  }
  const sidebar = panel('studio.categories', categoryList, can('forum.moderate') ? btn('forum.category.create', () => nameDialog('forum.category.create', 'forum.category', '/api/forum/categories', 'forum.moderate'), { icon: 'plus', iconOnly: true }) : null);
  toolbar = searchBar(filter, [status]); page.append(el('div', { class: 'community-layout' }, sidebar, el('div', {}, toolbar, results))); filter(); return page;
}
function nameDialog(titleKey, fieldKey, path, action) {
  openDialog(titleKey, form([field(fieldKey, 'name', 'text', '', { required: true, maxlength: 120 })], titleKey, async v => { await mutate(path, v, 'studio.success.create'); await done(); }, action));
}
function threadDialog(categories) {
  openDialog('forum.thread.create', form([field('forum.category', 'category_id', 'select', categories[0]?.id, { choices: categories.map(c => ({ value: c.id, label: c.name })) }), field('content.name', 'title', 'text', '', { required: true, maxlength: 200 }), field('forum.body', 'body', 'textarea', '', { required: true, maxlength: 20000 })], 'forum.thread.create', async v => { const result = await mutate('/api/forum/threads', { ...v, category_id: Number(v.category_id) }, 'studio.success.create'); $('inspector').close(); await go('forum/' + result.id); }, 'forum.write'));
}
async function moderate(item, kind, state) {
  if (!await confirm(state === 'approved' ? 'forum.approve' : 'forum.reject', state === 'rejected' ? 'studio.confirm.reject' : 'studio.moderation.hint', item.title ?? item.body.slice(0, 140))) return;
  await mutate('/api/forum/moderate', { id: item.id, kind, state, expected_version: item.version }); await load();
}
async function threadPage(thread, categories) {
  const replies = await req('/api/forum/replies?id=' + thread.id);
  const page = el('div', {}, header('studio.thread.details', null, btn('studio.back', () => go('forum'), { icon: 'back' })));
  page.querySelector('h1').textContent = thread.title;
  const body = el('section', { class: 'panel' }, el('div', { class: 'thread-meta' }, badge(thread.state), el('span', { class: 'muted', text: categories.find(c => c.id === thread.category_id)?.name ?? '' }), thread.locked ? badge('studio.locked') : null), el('div', { class: 'thread-body', text: thread.body }));
  if (can('forum.moderate')) body.append(el('div', { class: 'moderation-actions' }, el('h3', { text: t('studio.moderation') }), el('p', { text: t('studio.moderation.hint') }), el('div', { class: 'actions' }, btn('forum.approve', () => moderate(thread, 'threads', 'approved'), { primary: true, icon: 'check' }), btn('forum.reject', () => moderate(thread, 'threads', 'rejected'), { danger: true }), btn(thread.locked ? 'forum.unlock' : 'forum.lock', async () => {
    if (!await confirm('confirm.title', 'confirm.body', thread.title)) return;
    await mutate('/api/forum/lock', { id: thread.id, locked: !thread.locked, expected_version: thread.version }); await load();
  }))));
  for (const reply of replies) body.append(el('article', { class: 'reply' }, el('div', { class: 'thread-meta' }, badge(reply.state), el('small', { class: 'muted', text: t('audit.actor') + ' ' + reply.author_id + ' · ' + date(reply.created_at) })), el('p', { text: reply.body }), can('forum.moderate') ? el('div', { class: 'actions' }, btn('forum.approve', () => moderate(reply, 'replies', 'approved'), { icon: 'check' }), btn('forum.reject', () => moderate(reply, 'replies', 'rejected'), { danger: true })) : null));
  if (can('forum.write') && thread.state === 'approved' && !thread.locked) body.append(form([field('forum.body', 'body', 'textarea', '', { required: true, maxlength: 20000 })], 'forum.reply', async v => { await mutate('/api/forum/replies', { body: v.body, thread_id: thread.id }, 'studio.success.create'); await load(); }, 'forum.write', { cancel: false }));
  else body.append(el('div', { class: 'notice' }, icon('warning'), t(thread.locked ? 'studio.locked' : thread.state !== 'approved' ? 'label.error.THREAD_NOT_OPEN' : 'no.access')));
  page.append(body); return page;
}
async function chat(roomId) {
  const rooms = await req('/api/chat/rooms');
  selectedRoom = Number(roomId) || selectedRoom; if (!rooms.some(r => r.id === selectedRoom)) selectedRoom = rooms[0]?.id;
  const room = rooms.find(r => r.id === selectedRoom);
  const page = el('div', {}, header('chat.title', 'studio.chat.description', can('chat.manage') ? btn('chat.room.create', () => nameDialog('chat.room.create', 'chat.room', '/api/chat/rooms', 'chat.manage'), { icon: 'plus' }) : null));
  if (!room) { page.append(empty('empty')); return page; }
  const [messages, presence] = await Promise.all([req('/api/chat/messages?room_id=' + room.id), req('/api/chat/presence', { room_id: room.id })]);
  const roomList = el('div', { class: 'room-list' }, rooms.map(r => el('button', { class: 'category-button', type: 'button', 'aria-pressed': String(r.id === selectedRoom), onclick: () => go('chat/' + r.id) }, icon('chat'), r.name)));
  const timeline = el('div', { class: 'message-list', tabindex: '0', 'aria-label': t('chat.title') });
  function appendMessage(m) {
    const row=el('article', { class: 'message-row' }, avatar(m.email), el('div', { class: 'message-copy' }, el('span', { class: 'message-author', text: m.email }), el('time', { class: 'message-time', text: date(m.created_at) }), el('div', { class: 'message-body', text: m.body })));
    if(can('chat.manage'))row.append(btn('chat.delete', async () => {
      if (!await confirm('chat.delete', 'studio.confirm.delete', m.body.slice(0, 120))) return;
      await mutate('/api/chat/delete', { id: m.id }); await load();
    }, { danger: true, icon: 'close', iconOnly: true }));
    timeline.append(row);
  }
  if (messages.length) messages.forEach(appendMessage); else timeline.append(empty('studio.no.messages', null, 'chat'));
  const chatHeader = el('div', { class: 'chat-heading' }, el('div', {}, el('h2', { text: room.name }), el('p', { class: 'presence', text: t('studio.presence') + ': ' + presence.map(p => p.email).join(', ') })), btn('refresh', reloadView, { icon: 'refresh', quiet: true }));
  const chatPanel = el('section', { class: 'panel chat-panel' }, chatHeader, timeline);
  if (can('chat.write')) chatPanel.append(form([field('chat.message', 'body', 'textarea', '', { required: true, maxlength: 4000 })], 'chat.send', async (v, f) => {
    const result = await mutate('/api/chat/send', { room_id: room.id, body: v.body }, 'studio.success.send');
    if (!timeline.querySelector('.message-row')) timeline.replaceChildren();
    appendMessage({ id: result.id, email: me.user.email, body: v.body, created_at: result.created_at });
    f.reset(); dirty = false; timeline.scrollTop = timeline.scrollHeight;
  }, 'chat.write', { class: 'composer', cancel: false, icon: 'send' }));
  const composer = chatPanel.querySelector('form'); if (composer) composer.addEventListener('input', () => { dirty = true; });
  page.append(el('div', { class: 'community-layout' }, panel('studio.rooms', roomList), el('div', {}, chatPanel, el('p', { class: 'field-hint', text: t('chat.polling') }), el('p', { class: 'field-hint', text: t('studio.chat.window') }), can('chat.manage') ? el('div', { class: 'chat-settings' }, btn('studio.chat.settings', () => {
    openDialog('studio.chat.settings', el('div', {}, S.settings ? el('p', { text: t('chat.retention') + ': ' + S.settings['chat.retention_days'].value }) : null, el('p', { class: 'field-hint', text: t('studio.confirm.retention') }), btn('chat.prune', async () => { if (!await confirm('chat.prune', 'studio.confirm.retention')) return; await mutate('/api/chat/prune', {}); await done(); }, { danger: true })));
  }, { icon: 'settings' })) : null)));
  return page;
}

async function config() {
  const registry = await req('/api/registry');
  const page = el('div', {}, header('config.title', 'studio.settings.description'));
  const nav = el('nav', { class: 'settings-nav', 'aria-label': t('studio.settings') });
  const results = el('div'); let toolbar;
  const catLabels = { settings: 'studio.general', theme: 'theme.title', news: 'news.settings', flags: 'studio.features', labels: 'studio.labels', permissions: 'studio.permissions' };
  async function draw() {
    const drawCategory=category;
    if (['theme','news'].includes(category)) {
      toolbar.hidden = true;
      results.replaceChildren(loading());
      try { const page = drawCategory === 'theme' ? await appearance() : await newsSettings(); if (category === drawCategory) results.replaceChildren(page); }
      catch (error) { results.replaceChildren(empty('error', btn('retry', draw))); report(error); }
    } else {
    toolbar.hidden = false;
    const query = values(toolbar).search.toLowerCase(); const controls = Object.entries(S[category]).filter(([key, item]) => !['appearance.theme','public.news_category','public.news_limit'].includes(key) && (key + ' ' + (category === 'labels' ? item.value : t(registry.settings[key]?.label ?? key))).toLowerCase().includes(query));
    results.replaceChildren(controls.length ? el('div', { class: 'collection' }, controls.map(([key, item]) => {
      const name = category === 'settings' ? t(registry.settings[key].label) : category === 'permissions' ? t('role.' + key) : category === 'flags' ? t(key) : key;
      return el('div', { class: 'setting-row' }, el('div', { class: 'setting-copy' }, el('strong', { text: name }), el('code', { text: key }), el('p', { class: 'setting-value', text: category === 'permissions' ? t('studio.permissions.count') + ': ' + item.value.length : category === 'flags' ? t(item.value ? 'enabled' : 'disabled') : String(item.value) }), el('small', { class: 'record-meta', text: t('config.version') + ' ' + item.version + (category === 'settings' ? ' · ' + t(registry.settings[key].restart ? 'studio.restart' : 'studio.runtime') : '') })), btn('studio.edit', () => controlDialog(category, key, item, registry), { icon: 'edit', action: category === 'permissions' ? 'auth.permissions.write' : 'config.write' }));
    })) : empty('studio.no.results.description', null, 'settings', 'studio.no.results'));
    }
    for (const b of nav.children) b.setAttribute('aria-pressed', String(b.dataset.category === category));
  }
  for (const [cat, label] of Object.entries(catLabels)) nav.append(el('button', { type: 'button', class: 'category-button', 'data-category': cat, onclick: async () => {
    if(busy)return;
    if(dirty){if(!await confirm('studio.discard.title','studio.discard.body'))return;dirty=false;const boot=await req('/api/public/bootstrap');applyTheme(boot.theme_tokens);}
    category = cat; draw();
  } }, t(label)));
  toolbar = searchBar(draw); page.append(el('div', { class: 'settings-layout' }, nav, el('div', {}, toolbar, results))); draw(); return page;
}
async function appearance() {
  const contract = await req('/api/theme/contract'), item = S.settings['appearance.theme'];
  const initial = structuredClone(item.value); let choice = initial.preset;
  const colors = Object.keys(initial.colors).map(key => field('theme.' + key, 'color:' + key, 'color', initial.colors[key]));
  const fonts = contract.fonts.map(key => ({ value:key, label:t('theme.font.' + key) }));
  const presets = field('theme.preset','preset','select',choice,{choices:[...Object.keys(contract.presets), 'custom'].map(key=>({value:key,label:t('theme.'+key)}))});
  const preview = el('div',{class:'theme-preview'},el('p',{class:'eyebrow',text:t('theme.preview.title')}),el('h2',{text:t('theme.preview.draft')}),el('p',{text:t('theme.preview.body')}),el('div',{class:'actions'},el('span',{class:'theme-button-example',text:t('theme.preview.button')}),el('span',{class:'theme-link-example',text:t('theme.preview.link')})));
  const info=el('div',{class:'notice',hidden:true,text:t('theme.preview.notice')});
  function payload(f) {
    const v=values(f), palette={}; for(const [key,value] of Object.entries(v)) if(key.startsWith('color:')) palette[key.slice(6)]=value;
    return {schema_version:1,preset:choice,colors:palette,admin_font:v.admin_font,public_font:v.public_font,density:v.density,radius:v.radius,public_layout:v.public_layout,design_notes:v.design_notes};
  }
  async function previewValue(f) {
    const result=await req('/api/theme/preview',{theme:payload(f)}); applyTheme(result.tokens); info.hidden=false;
  }
  const f=form([el('h2',{text:t('theme.title')}),el('p',{class:'description',text:t('theme.description')}),el('p',{class:'field-hint',text:t('theme.validation')}),presets,el('div',{class:'theme-colors'},colors),el('div',{class:'form-grid'},field('theme.admin_font','admin_font','select',initial.admin_font,{choices:fonts}),field('theme.public_font','public_font','select',initial.public_font,{choices:fonts}),field('theme.density','density','select',initial.density,{choices:['comfortable','compact'].map(x=>({value:x,label:t('theme.'+x)}))}),field('theme.radius','radius','number',initial.radius,{min:0,max:20,required:true}),field('theme.layout','public_layout','select',initial.public_layout,{choices:['cards','list'].map(x=>({value:x,label:t('theme.'+x)}))})),field('theme.notes','design_notes','textarea',initial.design_notes,{maxlength:2000,hint:'theme.notes.hint'}),info,preview,field('config.reason','reason','text',t('theme.change.reason'),{required:true,maxlength:500})], 'theme.save',async v=>{
    await mutate('/api/change',{category:'settings',key:'appearance.theme',value:payload(f),reason:v.reason,expected_version:item.version},'theme.success');
    dirty=false; await load();
  },'config.write',{class:'panel appearance-form',cancel:false});
  const setInputs=(theme)=>{
    choice=theme.preset;
    for(const input of f.querySelectorAll('[name]')) {
      const name=input.name; if(name==='reason') continue;
      input.value=name.startsWith('color:') ? theme.colors[name.slice(6)] : theme[name];
    }
    dirty=true;
  };
  presets.querySelector('select').addEventListener('change',()=>{
    choice=presets.querySelector('select').value;
    if(contract.presets[choice]) for(const input of f.querySelectorAll('[name^="color:"]')) input.value=contract.presets[choice][input.name.slice(6)];
    dirty=true;
  });
  for(const input of f.querySelectorAll('[type=color]')) input.addEventListener('input',()=>{choice='custom';presets.querySelector('select').value='custom';});
  f.addEventListener('input',()=>{dirty=true;});
  const tools=el('div',{class:'actions theme-tools'},btn('theme.preview',()=>previewValue(f),{action:'config.write',icon:'media'}),btn('theme.discard',async()=>{setInputs(initial);dirty=false;const boot=await req('/api/public/bootstrap');applyTheme(boot.theme_tokens);info.hidden=true;},{icon:'back'}),btn('theme.reset',async()=>{setInputs(structuredClone(contract.default));await previewValue(f);},{action:'config.write'}),btn('theme.export',()=>{
    const blob=new Blob([JSON.stringify(payload(f),null,2)],{type:'application/json'}),url=URL.createObjectURL(blob);
    const a=el('a',{href:url,download:'ecosystem-theme.json'});a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  },{icon:'external'}),btn('theme.import',()=>{
    openDialog('theme.import',form([el('p',{class:'field-hint',text:t('theme.import.hint')}),field('theme.import.file','file','file','',{required:true,accept:'.json,application/json'})],'theme.preview',async(v,importForm)=>{
      const file=importForm.querySelector('[type=file]').files[0]; if(!file||file.size>16000) throw {code:'INVALID_THEME'};
      let theme;try{theme=JSON.parse(await file.text());}catch{throw {code:'INVALID_THEME'};}
      const checked=await req('/api/theme/preview',{theme});setInputs(theme);applyTheme(checked.tokens);info.hidden=false;$('inspector').close();
    },'config.write'));
  },{action:'config.write',icon:'upload'}),btn('theme.contract',()=>openDialog('theme.contract',el('div',{},el('p',{text:t('theme.contract.description')}),el('pre',{class:'contract-data',text:JSON.stringify(contract,null,2)})),true),{icon:'content'}));
  f.insertBefore(tools,f.querySelector('.form-actions')); return f;
}
async function newsSettings() {
  if(!can('forum.read')) return empty('no.access',null,'forum');
  const options=await req('/api/publication/options'), categoryItem=S.settings['public.news_category'],limitItem=S.settings['public.news_limit'];
  const choose=field('news.category','news_category','select',categoryItem.value,{choices:[{value:0,label:t('news.disabled')},...options.categories.map(c=>({value:c.id,label:c.name}))]});
  const count=el('p',{class:'field-hint'});
  function updateCount(){const selected=Number(choose.querySelector('select').value);count.textContent=t('news.approved.count')+': '+(options.categories.find(c=>c.id===selected)?.approved_count??0);}
  choose.querySelector('select').addEventListener('change',updateCount);updateCount();
  const f=form([el('h2',{text:t('news.settings')}),el('p',{class:'description',text:t('news.settings.description')}),el('div',{class:'notice warning'},icon('warning'),t('news.warning')),options.forum_enabled?null:el('p',{class:'notice warning',text:t('news.forum.off')}),choose,count,can('forum.moderate')&&options.forum_enabled?btn('news.create',()=>nameDialog('news.create','forum.category','/api/forum/categories','forum.moderate'),{icon:'plus'}):null,field('news.limit','news_limit','number',limitItem.value,{min:1,max:30,required:true}),field('config.reason','reason','text','',{required:true,maxlength:500})],'news.save',async v=>{
    const chosen=Number(v.news_category);
    if(chosen!==categoryItem.value&&!await confirm('news.confirm','news.warning',options.categories.find(c=>c.id===chosen)?.name??t('news.disabled')))return;
    await mutate('/api/news/settings',{category_id:chosen,limit:v.news_limit,reason:v.reason,expected_category_version:categoryItem.version,expected_limit_version:limitItem.version},'news.success');
    dirty=false;await load();
  },'config.write',{class:'panel',cancel:false});
  f.addEventListener('input',()=>{dirty=true;});
  f.append(el('div',{class:'form-actions'},anchor('news.view','/news','external','btn')));return f;
}
function scopePicker(actions, checked) {
  const groups = {};
  for (const action of actions) (groups[action.split('.')[0]] ??= []).push(action);
  return el('div', {}, Object.entries(groups).map(([group, items]) => el('fieldset', { class: 'permission-group' }, el('legend', { text: t('module.'+group) }), el('div', { class: 'scope-grid' }, items.map(action => field('action.'+action, 'scope:' + action, 'checkbox', checked.includes(action)))))));
}
function controlDialog(cat, key, item, registry) {
  const meta = registry.settings[key]; const action = cat === 'permissions' ? 'auth.permissions.write' : 'config.write';
  const inputs = [];
  if (cat === 'permissions') inputs.push(el('p', { class: 'notice', text: t('studio.permissions.recovery') }), scopePicker(Object.keys(registry.actions).filter(a => !registry.actions[a].public), item.value));
  else inputs.push(field('config.value', 'value', cat === 'flags' ? 'checkbox' : cat === 'settings' && meta.kind === 'number' ? 'number' : cat === 'labels' ? 'textarea' : 'text', item.value, { required: cat !== 'flags', min: meta?.validate.min, max: meta?.validate.max, maxlength: cat === 'labels' ? 1000 : meta?.validate.max }));
  if (meta) inputs.push(el('p', { class: 'field-hint', text: t('studio.scope') + ': ' + meta.scope + ' · ' + t(meta.restart ? 'studio.restart' : 'studio.runtime') }));
  inputs.push(field('config.reason', 'reason', 'text', '', { required: true, maxlength: 500 }));
  const f = form(inputs, 'save', async v => {
    const value = cat === 'permissions' ? Object.entries(v).filter(([k, val]) => k.startsWith('scope:') && val).map(([k]) => k.slice(6)) : v.value;
    if (['permissions', 'flags'].includes(cat) && !await confirm('confirm.title', cat === 'flags' ? 'studio.confirm.feature' : 'studio.confirm.permissions', key)) return;
    await mutate('/api/change', { category: cat, key, value, reason: v.reason, expected_version: item.version }, 'studio.success.change'); await done();
  }, action);
  openDialog('studio.edit', el('div', {}, el('p', { class: 'field-hint', text: key + ' · ' + t('config.version') + ' ' + item.version }), f), cat === 'permissions', cat === 'settings' ? t(meta.label) : cat === 'permissions' ? t('role.' + key) : key);
}
async function users() {
  const rows = await req('/api/users'); const results = el('div'); let toolbar;
  function filter() {
    const query = values(toolbar).search.toLowerCase();
    results.replaceChildren(table(['email', 'users.role', 'users.active', 'studio.action'], rows.filter(u => (u.email + ' ' + t('role.' + u.role)).toLowerCase().includes(query)).map(u => [el('div', { class: 'actions' }, avatar(u.email), el('strong', { text: u.email })), el('div', {}, t('role.' + u.role), el('small', { class: 'record-meta', text: u.role })), badge(u.active ? 'enabled' : 'disabled'), btn('studio.edit', () => userDialog(u), { icon: 'edit', action: 'auth.users.write' })])));
  }
  toolbar = searchBar(filter); const page = el('div', {}, header('users.title', 'studio.users.description', can('auth.users.write') ? btn('users.create', () => userDialog(), { primary: true, icon: 'plus' }) : null), toolbar, results); filter(); return page;
}
function userDialog(user = null) {
  const fields = [user ? null : field('email', 'email', 'email', '', { required: true, autocomplete: 'username' }), field(user ? 'users.password' : 'password', 'password', 'password', '', { required: !user, minlength: 12, maxlength: 256, autocomplete: 'new-password' }), field('users.role', 'role', 'select', user?.role ?? 'member', { choices: ['admin', 'editor', 'moderator', 'member'].map(r => ({ value: r, label: t('role.' + r) })) })];
  if (user) fields.push(field('users.active', 'active', 'checkbox', Boolean(user.active)));
  openDialog(user ? 'users.update' : 'users.create', form(fields, user ? 'users.update' : 'users.create', async v => {
    if (user && !await confirm('users.update', 'studio.confirm.access', user.email)) return;
    await mutate(user ? '/api/users/update' : '/api/users/create', { ...v, ...(user ? { id: user.id } : {}) }, user ? 'studio.success.save' : 'studio.success.create'); await done();
  }, 'auth.users.write'), false, user?.email);
}
async function api() {
  const keys = await req('/api/keys');
  return el('div', {}, header('api.title', 'studio.api.description', can('api.keys.write') ? btn('api.create', keyDialog, { primary: true, icon: 'plus' }) : null), el('div', { class: 'notice' }, icon('key'), t('api.warning')), keys.length ? table(['api.name', 'api.scopes', 'api.expires', 'content.status', 'studio.action'], keys.map(k => [k.name, el('span', { class: 'key-scopes', text: JSON.parse(k.scopes).join(', ') }), date(k.expires_at), badge(k.revoked ? 'revoked' : 'active'), k.revoked ? el('span', { class: 'muted', text: t('studio.key.revoked') }) : btn('api.revoke', async () => { if (!await confirm('api.revoke', 'studio.confirm.revoke', k.name)) return; await mutate('/api/keys/revoke', { id: k.id }); await load(); }, { danger: true, action: 'api.keys.write' })])) : empty('studio.no.keys', can('api.keys.write') ? btn('api.create', keyDialog, { primary: true }) : null, 'key'));
}
function keyDialog() {
  openDialog('api.create', form([field('api.name', 'name', 'text', '', { required: true, maxlength: 120 }), field('api.expiry', 'days', 'number', 30, { required: true, min: 1, max: 365 }), el('p', { class: 'field-hint', text: t('studio.api.scope.hint') }), scopePicker(me.permissions, [])], 'api.create', async v => {
    const scopes = Object.entries(v).filter(([key, val]) => key.startsWith('scope:') && val).map(([key]) => key.slice(6));
    if (!scopes.length) throw { code: 'INVALID_SCOPES' };
    const result = await mutate('/api/keys/create', { name: v.name, days: v.days, scopes }, 'studio.success.create');
    const token = el('textarea', { class: 'secret-token', readonly: true, 'aria-label': t('api.token') }, result.token);
    openDialog('api.token', el('div', {}, token, el('div', { class: 'form-actions' }, btn('studio.api.copy', async () => {
      try { await navigator.clipboard.writeText(result.token); feedback(t('studio.api.copied')); }
      catch { token.focus(); token.select(); feedback(t('studio.api.copy.failed'), true); }
    }, { primary: true }))));
    await load();
  }, 'api.keys.write'), true);
}
async function audit() {
  const events = await req('/api/audit'); const results = el('div'); let toolbar;
  function draw() {
    const query = values(toolbar).search.toLowerCase(); const matches = events.filter(e => (e.actor + ' ' + actorName(e.actor) + ' ' + e.category + ' ' + e.key + ' ' + e.reason + ' ' + eventSummary(e)).toLowerCase().includes(query));
    results.replaceChildren(events.length ? table(['audit.operation', 'audit.actor', 'audit.time', 'studio.action'], matches.map(e => [el('div', {}, el('strong', { text: eventSummary(e) }), el('small', { class: 'record-meta', text: e.category + ' · ' + e.key })), actorName(e.actor), date(e.created_at), btn('studio.open', () => auditDialog(e), { icon: 'arrow', quiet: true })])) : empty('studio.no.activity', null, 'audit'));
  }
  toolbar = searchBar(draw); const page = el('div', {}, header('audit.title', 'studio.audit.description'), el('p', { class: 'field-hint', text: t('studio.audit.window') }), toolbar, results); draw(); return page;
}
function actorName(actor){return actor==='system'?t('audit.system'):actor==='bootstrap'?t('audit.bootstrap'):String(actor)===String(me?.user.id)?me.user.email:t('audit.member')+' #'+actor;}
function eventSummary(event){
  const phrases={entry_create:'audit.entry_create',entry_update:'audit.entry_update','workflow transition':'audit.workflow',
    'type created':'audit.type_create','session created':'audit.session.created','session revoked':'audit.session.revoked','user created':'audit.user.created',
    'access updated':'audit.access.updated','image uploaded':'audit.image.uploaded','transformed copy created':'audit.image.transformed','asset deleted':'audit.asset.deleted',
    'category created':'audit.category.created','thread created':'audit.thread.created','reply created':'audit.reply.created','message sent':'audit.message.sent',
    'key created':'audit.key.created','key revoked':'audit.key.revoked','moderation':'audit.moderation','retention applied':'audit.retention'};
  return phrases[event.reason]?t(phrases[event.reason]):event.reason.startsWith('undo:')?t('config.undo'):event.reason;
}
function readableValue(value,level=0){
  if(value==null)return t('audit.notset');
  if(typeof value==='boolean')return t(value?'audit.yes':'audit.no');
  if(Array.isArray(value))return value.length?value.map(v=>readableValue(v,level+1)).join(', '):t('audit.none.selected');
  if(typeof value==='object')return Object.entries(value).map(([key,val])=>'  '.repeat(level)+(L['audit.field.'+key]??L['theme.'+key]??L['content.'+key]??key.replaceAll('_',' '))+': '+readableValue(val,level+1)).join('\n')||t('audit.no.details');
  return String(value);
}
function auditValue(raw,label){
  if(raw==null)return t(label==='audit.before'?'audit.empty.before':'audit.empty.after');
  try{const value=JSON.parse(raw);return value===null?t(label==='audit.before'?'audit.empty.before':'audit.empty.after'):readableValue(value);}catch{return t('audit.unknown');}
}
function auditDialog(event) {
  const current = S[event.category]?.[event.key];
  const supported = ['settings', 'flags', 'labels', 'permissions'].includes(event.category);
  const allowed = can('config.write') && (event.category !== 'permissions' || can('auth.permissions.write'));
  const body = el('div', {}, el('p', { class: 'muted', text: t('audit.actor') + ': ' + actorName(event.actor) + ' · ' + date(event.created_at) }), el('p', { text: eventSummary(event) }), el('p', { class: 'field-hint', text: t('studio.audit.target') + ': ' + event.category + '.' + event.key }), el('div', { class: 'diff-grid' }, ...[['audit.before', event.old_value], ['audit.after', event.new_value]].map(([label, raw]) => el('div', {}, el('h3', { text: t(label) }), el('pre', { text: auditValue(raw,label) })))));
  body.append(el('div', { class: 'form-actions' }, btn('config.undo', async () => {
    if (!await confirm('config.undo', 'studio.confirm.undo', event.category + '.' + event.key)) return;
    await mutate('/api/undo', { audit_id: event.id, expected_version: event.new_version }, 'studio.success.undo'); await done();
  }, { icon: 'back', disabled: !supported || current?.version !== event.new_version || !allowed, reason: !allowed ? 'no.access' : 'studio.undo.unavailable' })));
  openDialog('studio.audit.details', body, true);
}

(async () => {
  $('main').replaceChildren(loading());
  try {
    const boot = await req('/api/public/bootstrap'); L = boot.labels; applyTheme(boot.theme_tokens);
    try { me = await req('/api/me'); csrf = me.csrf; } catch (error) { if (error.status !== 401) throw error; }
    chrome(); if (me) await load(); else loginView();
  } catch (error) { report(error); $('main').replaceChildren(empty('error', btn('retry', () => location.reload(), { icon: 'refresh' }), 'warning')); }
})();
