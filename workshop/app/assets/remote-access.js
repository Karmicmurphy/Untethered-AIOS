(() => {
  'use strict';
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const escapeHtml = value => String(value ?? '').replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const request = async (path, options = {}) => {
    const response = await fetch(path, {headers:{'Content-Type':'application/json', ...(options.headers || {})}, ...options});
    const value = await response.json().catch(() => ({error:`HTTP ${response.status}`}));
    if (!response.ok) throw new Error(value.error || `HTTP ${response.status}`);
    return value;
  };
  const panel = (title, copy) => {
    const section = document.createElement('section');
    section.className = 'visitor-bench';
    section.innerHTML = `<p class="eyebrow">GOVERNED REMOTE SANDBOX</p><h2>${escapeHtml(title)}</h2><p>${escapeHtml(copy)}</p>`;
    return section;
  };
  const hidePanelContents = room => $$('.room[data-panel="'+room+'"]').forEach(node => [...node.children].forEach(child => child.classList.add('remote-hidden')));
  const guestEditor = (room, identity) => {
    hidePanelContents(room);
    $$('.room[data-panel="'+room+'"]').forEach((node, index) => {
      if (index) return;
      const bench = panel(`Visitor's Bench · ${room === 'write' ? 'Write' : 'Music'}`, 'Your work stays in your authenticated guest namespace. It is inactive and cannot modify owner projects or sources.');
      bench.innerHTML += `<p class="visitor-bench-meta">Authenticated creator: ${escapeHtml(identity)}</p><form><label>Title<input name="title" required maxlength="200"></label><label>${room === 'write' ? 'Writing draft' : 'Music concept / lyrics / production notes'}<textarea name="content" required></textarea></label><label>Operation<input name="operation" value="${room === 'write' ? 'guest-writing-draft' : 'guest-music-concept'}" maxlength="100"></label><div class="visitor-bench-actions"><button class="primary" type="submit">Save inactive sandbox draft</button><button class="quiet" type="reset">Clear without saving</button></div><p class="muted" role="status"></p></form>`;
      node.append(bench);
      const form = $('form', bench), status = $('[role="status"]', bench);
      form.addEventListener('submit', async event => {
        event.preventDefault(); status.textContent = 'Saving locally…';
        try {
          await request('/api/visitor-bench/submissions', {method:'POST', body:JSON.stringify({room,title:form.title.value,content:form.content.value,operation:form.operation.value})});
          status.textContent = 'Saved as an inactive Visitor’s Bench draft.'; form.reset();
        } catch (error) { status.textContent = error.message; }
      });
    });
  };
  const renderGuestWork = async identity => {
    hidePanelContents('work');
    const room = $('.room[data-panel="work"]');
    if (!room) return;
    const bench = panel("Visitor's Bench · My Work", `Only sandbox work owned by ${identity} is shown.`);
    bench.innerHTML += '<div class="visitor-bench-list"><p>Loading…</p></div>';
    room.append(bench);
    try {
      const data = await request('/api/visitor-bench/submissions');
      $('.visitor-bench-list', bench).innerHTML = data.submissions.length ? data.submissions.map(item => `<article class="visitor-bench-item"><h3>${escapeHtml(item.title)}</h3><p class="visitor-bench-meta">${escapeHtml(item.room)} · ${escapeHtml(item.operation)} · ${escapeHtml(item.created_at)} · ${escapeHtml(item.content_sha256.slice(0,12))}</p><pre>${escapeHtml(item.content)}</pre><strong>${item.promotion ? 'Copied into owner authority by explicit review' : 'GUEST SANDBOX DRAFT'}</strong></article>`).join('') : '<p>No saved sandbox work.</p>';
    } catch (error) { $('.visitor-bench-list', bench).textContent = error.message; }
  };
  const renderOwnerReview = async () => {
    const room = $('.room[data-panel="work"]');
    if (!room) return;
    const bench = panel("Visitor's Bench", 'Owner-only review. Promotion creates a separate inactive owner artifact and receipt; the guest original is unchanged.');
    bench.innerHTML += '<div class="visitor-bench-list"><p>Loading…</p></div>';
    room.prepend(bench);
    try {
      const [data, projects] = await Promise.all([request('/api/visitor-bench/submissions'), request('/api/projects')]);
      const projectRows = projects.projects || projects;
      $('.visitor-bench-list', bench).innerHTML = data.submissions.length ? data.submissions.map(item => `<article class="visitor-bench-item" data-id="${escapeHtml(item.id)}"><h3>${escapeHtml(item.title)}</h3><p class="visitor-bench-meta">${escapeHtml(item.guest_identity)} · ${escapeHtml(item.room)} · ${escapeHtml(item.created_at)} · ${escapeHtml(item.content_sha256.slice(0,12))}</p><pre>${escapeHtml(item.content)}</pre>${item.promotion ? `<strong>Promoted as ${escapeHtml(item.promotion.owner_artifact_id)}</strong>` : `<div class="visitor-bench-actions"><select aria-label="Owner project">${projectRows.map(project => `<option value="${escapeHtml(project.id)}">${escapeHtml(project.title)}</option>`).join('')}</select><button class="quiet" data-promote>Copy into owner My Work</button></div>`}</article>`).join('') : '<p>No guest submissions.</p>';
      $$('[data-promote]', bench).forEach(button => button.addEventListener('click', async () => {
        const article = button.closest('[data-id]'), select = $('select', article); button.disabled = true;
        try { await request(`/api/visitor-bench/submissions/${article.dataset.id}/promote`, {method:'POST',body:JSON.stringify({projectId:select.value})}); button.textContent = 'Promoted with receipt'; }
        catch (error) { button.textContent = error.message; button.disabled = false; }
      }));
    } catch (error) { $('.visitor-bench-list', bench).textContent = error.message; }
  };
  const applyRemoteRole = session => {
    document.body.dataset.twisRole = session.role;
    const banner = document.createElement('div');
    banner.className = 'remote-authority-banner';
    banner.innerHTML = `<strong>${escapeHtml(session.role)}</strong><span>${escapeHtml(session.identity)} · ${session.remote ? 'Cloudflare Access identity' : 'local loopback owner'}</span>`;
    const frame = $('.app') || document.body; frame.prepend(banner);
    if (session.role === 'OWNER') { renderOwnerReview(); return; }
    const allowed = session.role === 'GUEST_CREATOR' ? new Set(['sanctuary','crossroads','write','music','work']) : new Set(['sanctuary','crossroads']);
    $$('[data-room]').forEach(button => { if (!allowed.has(button.dataset.room)) button.classList.add('remote-hidden'); });
    if (session.role === 'GUEST_CREATOR') { guestEditor('write', session.identity); guestEditor('music', session.identity); renderGuestWork(session.identity); }
    else {
      $$('.sanctuary-actions [data-room]').forEach(button => { if (!allowed.has(button.dataset.room)) button.classList.add('remote-hidden'); });
    }
  };
  document.addEventListener('DOMContentLoaded', async () => {
    try { const session = await request('/api/session'); applyRemoteRole(session); }
    catch (error) { document.body.innerHTML = `<main class="visitor-bench"><h1>TWIS Remote Access denied</h1><p>${escapeHtml(error.message)}</p></main>`; }
  });
})();
