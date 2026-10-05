'use strict';
// Mobile drawer uses the same breakpoint as the CSS shell.
(() => {
  const root = document.documentElement;
  let saved;
  try { saved = localStorage.getItem('onion-theme'); } catch (_) { /* Storage may be unavailable. */ }
  root.dataset.theme = saved === 'dark' || saved === 'light' ? saved : 'light';
  const theme = document.querySelector('.theme');
  const updateTheme = () => { theme.setAttribute('aria-label', `Switch to ${root.dataset.theme === 'dark' ? 'light' : 'dark'} theme`); theme.setAttribute('aria-pressed', String(root.dataset.theme === 'dark')); document.querySelectorAll('meta[name="theme-color"]').forEach(meta => { meta.removeAttribute('media'); meta.setAttribute('content', root.dataset.theme === 'dark' ? '#161b21' : '#f8f9fa'); }); };
  updateTheme();
  theme.addEventListener('click', () => { root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark'; try { localStorage.setItem('onion-theme', root.dataset.theme); } catch (_) {} updateTheme(); });
  const menu = document.querySelector('.menu');
  const pane = document.getElementById('main');
  const layout = document.querySelector('.docs-layout');
  if (layout?.prepend) {
    const backdrop = document.createElement('div');
    backdrop.className = 'nav-backdrop'; backdrop.setAttribute('aria-hidden', 'true');
    layout.prepend(backdrop);
  }
  const closeNav = () => {
    const wasOpen = document.body.classList.contains('nav-open');
    document.body.classList.remove('nav-open'); menu.setAttribute('aria-expanded', 'false');
    pane.inert = false;
    if (wasOpen) menu.focus({preventScroll:true});
  };
  menu.addEventListener('click', () => {
    if (document.body.classList.contains('nav-open')) { closeNav(); return; }
    document.body.classList.add('nav-open'); menu.setAttribute('aria-expanded', 'true'); pane.inert = true;
  });
  if (window.matchMedia) window.matchMedia('(min-width: 801px)').addEventListener('change', e => { if (e.matches) closeNav(); });
  document.addEventListener('click', e => { if (document.body.classList.contains('nav-open') && !e.target.closest('#docs-nav') && !e.target.closest('.menu')) closeNav(); });
  const dialog = document.getElementById('search-dialog');
  const input = document.getElementById('search-input');
  const results = document.getElementById('search-results');
  const status = document.getElementById('search-status');
  let index;
  let returnFocus;
  const openSearch = async () => {
    closeNav(); returnFocus = document.activeElement; dialog.showModal(); input.focus();
    if (!index) {
      try { const response = await fetch('/assets/search.json'); if (!response.ok) throw new Error('index unavailable'); index = await response.json(); render(); }
      catch (_) { status.textContent = 'Search could not load. Use the documentation navigation instead.'; }
    } else render();
  };
  const closeSearch = () => dialog.close();
  dialog.addEventListener('close', () => { if (returnFocus && returnFocus.isConnected) returnFocus.focus(); });
  document.querySelector('.search-open').addEventListener('click', openSearch);
  document.getElementById('search-close').addEventListener('click', closeSearch);
  dialog.addEventListener('click', e => { if (e.target === dialog) { const r = dialog.getBoundingClientRect(); if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) closeSearch(); } });
  document.addEventListener('keydown', e => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); if (!dialog.open) openSearch(); }
    if (e.key === 'Escape') closeNav();
  });
  function render() {
    if (!index) return;
    results.replaceChildren();
    const terms = input.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
    if (!terms.length) { status.textContent = 'Search runs locally. Try TASKS.json, scope or supersession.'; return; }
    const matches = index.map(item => ({item, score: terms.reduce((sum, term) => sum + (item.title.toLowerCase().includes(term) ? 5 : 0) + (item.heading.toLowerCase().includes(term) ? 3 : 0), 0)})).filter(({item}) => terms.every(term => `${item.title} ${item.heading} ${item.text}`.toLowerCase().includes(term))).sort((a,b) => b.score - a.score);
    status.textContent = matches.length ? `${matches.length} matching sections${matches.length > 12 ? ' · showing the first 12' : ''}` : 'No results. Try a broader word, or browse the documentation.';
    matches.slice(0, 12).forEach(({item}) => {
      const link = document.createElement('a'); link.className = 'search-result'; link.href = item.url;
      const title = document.createElement('strong'); title.textContent = item.heading;
      const page = document.createElement('span'); page.textContent = item.title;
      const excerpt = document.createElement('p'); excerpt.textContent = item.text.slice(0, 145) + (item.text.length > 145 ? '…' : '');
      link.append(title, page, excerpt); results.append(link);
      link.addEventListener('click', closeSearch);
    });
  }
  input.addEventListener('input', render);
  dialog.addEventListener('keydown', e => {
    const links = Array.from(results.querySelectorAll('a'));
    if ((e.key === 'ArrowDown' || e.key === 'ArrowUp') && links.length) {
      e.preventDefault(); const i = links.indexOf(document.activeElement); const next = e.key === 'ArrowDown' ? (i + 1) % links.length : i < 0 ? links.length - 1 : (i - 1 + links.length) % links.length; links[next].focus();
    } else if (e.key === 'Enter' && document.activeElement === input && links.length) { e.preventDefault(); links[0].click(); }
  });
  document.querySelectorAll('.copy').forEach(button => button.addEventListener('click', async () => {
    const block = button.closest('.code-block'); const text = block.querySelector('code').textContent; let ok = false;
    let timer;
    try {
      if (navigator.clipboard) {
        await Promise.race([
          navigator.clipboard.writeText(text),
          new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('Clipboard permission did not settle')), 1500); })
        ]);
        ok = true;
      }
    } catch (_) {} finally { clearTimeout(timer); }
    if (!ok) {
      const area = document.createElement('textarea'); area.value = text; area.style.position = 'fixed'; area.style.opacity = '0'; document.body.append(area); area.select();
      try { ok = document.execCommand('copy'); } catch (_) {} area.remove(); button.focus();
    }
    block.querySelector('.copy-status').textContent = ok ? 'Copied to clipboard.' : 'Copy unavailable. Select the code and copy manually.';
    button.textContent = ok ? 'Copied' : 'Copy';
  }));
  const templateSearch = document.getElementById('template-search');
  if (templateSearch) {
    const cards = Array.from(document.querySelectorAll('[data-template-search]'));
    const filterTemplates = () => {
      const query = templateSearch.value.toLowerCase().trim().replace(/\s+/g, ' ');
      const terms = query ? [query] : [];
      let count = 0;
      cards.forEach(card => {
        const match = terms.every(term => card.dataset.templateSearch.toLowerCase().includes(term));
        card.hidden = !match;
        if (match) count += 1;
      });
      document.getElementById('template-status').textContent = `${count} ${count === 1 ? 'template' : 'templates'}${terms.length ? ' match' : ''}`;
      document.getElementById('template-empty').hidden = count !== 0;
    };
    templateSearch.addEventListener('input', filterTemplates);
    filterTemplates();
  }
  const main = document.getElementById('main');
  const jump = document.getElementById('section-jump');
  const sections = Array.from(main.querySelectorAll('.article section[id]'));
  if (sections.length) jump.replaceChildren();
  sections.forEach(section => {
    const option = document.createElement('option'); option.value = section.id;
    option.textContent = section.querySelector('h2')?.textContent || section.id;
    jump.append(option);
  });
  function spy() {
    const top = main.getBoundingClientRect().top;
    let active = sections[0]?.id || '';
    sections.forEach(section => { if (section.getBoundingClientRect().top <= top + 100) active = section.id; });
    if (main.scrollTop > 0 && main.scrollTop + main.clientHeight >= main.scrollHeight - 2 && sections.length) active = sections[sections.length - 1].id;
    jump.value = active;
    jump.dataset.currentSection = active;
  }
  function navigate(hash, record = false) {
    const id = decodeURIComponent(hash.replace(/^#/, ''));
    const target = id ? document.getElementById(id) : main;
    if (!target || !main.contains(target) && target !== main) return;
    if (record) history.pushState(null, '', id ? '#' + encodeURIComponent(id) : location.pathname);
    main.scrollTo({top: target === main ? 0 : main.scrollTop + target.getBoundingClientRect().top - main.getBoundingClientRect().top - 16, behavior: 'auto'});
    spy();
  }
  jump.addEventListener('change', () => navigate('#' + jump.value, true));
  document.addEventListener('click', event => {
    const link = event.target.closest('a[href]');
    if (!link || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const url = new URL(link.href, location.href);
    if (url.origin === location.origin && url.pathname === location.pathname && url.hash) {
      event.preventDefault(); navigate(url.hash, true);
      if (url.hash === '#main') main.focus({preventScroll:true});
      closeNav();
    }
  });
  // Only the focused pane owns document-style scroll keys; leave inputs,
  // selects, links, and modified keyboard commands to their native behavior.
  main.addEventListener('keydown', event => {
    if (event.target !== main || event.altKey || event.ctrlKey || event.metaKey) return;
    const page = Math.max(1, main.clientHeight - 40);
    const positions = {Home:0, End:main.scrollHeight, PageDown:main.scrollTop + page, PageUp:main.scrollTop - page, ' ':main.scrollTop + (event.shiftKey ? -page : page)};
    if (!Object.prototype.hasOwnProperty.call(positions, event.key)) return;
    event.preventDefault(); main.scrollTo({top:positions[event.key], behavior:'instant'});
  });
  main.addEventListener('scroll', spy, {passive:true});
  window.addEventListener('hashchange', () => navigate(location.hash));
  window.addEventListener('popstate', () => navigate(location.hash));
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(spy, {root:main, threshold:[0,1]});
    sections.forEach(section => observer.observe(section));
  }
  document.fonts.ready.then(() => navigate(location.hash));
  window.addEventListener('load', () => navigate(location.hash));
  spy();
  // Enhance anchored headings without changing stable IDs, jump labels or history.
  main.querySelectorAll('h2,h3').forEach(heading => {
    const existing = heading.querySelector('.heading-anchor');
    const id = existing?.getAttribute('href')?.slice(1) || heading.id || (heading.parentElement.matches('section[id]') ? heading.parentElement.id : '');
    if (!id) return;
    const title = heading.textContent.trim();
    const label = document.createElement('span'); label.className = 'heading-title'; label.textContent = title;
    const anchor = document.createElement('a'); anchor.className = 'heading-anchor'; anchor.href = '#' + id;
    anchor.textContent = '#'; anchor.setAttribute('aria-label', `Permalink to ${title}`);
    const button = document.createElement('button'); button.type = 'button'; button.className = 'heading-copy';
    button.setAttribute('aria-label', `Copy link to ${title}`); button.title = `Copy link to ${title}`;
    const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    Object.entries({'aria-hidden':'true',viewBox:'0 0 24 24',width:'16',height:'16',fill:'none',stroke:'currentColor','stroke-width':'1.7'}).forEach(([key,value]) => icon.setAttribute(key,value));
    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    Object.entries({x:'8',y:'8',width:'12',height:'12',rx:'2'}).forEach(([key,value]) => rect.setAttribute(key,value));
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', 'M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3');
    icon.append(rect, path); button.append(icon);
    const notice = document.createElement('span'); notice.className = 'heading-copy-status'; notice.hidden = true; notice.setAttribute('aria-live', 'polite');
    heading.classList.add('anchorable-heading'); heading.replaceChildren(label, anchor, button, notice);
    button.addEventListener('click', async () => {
      // Canonical public host and path, never transient search parameters.
      const url = new URL(document.querySelector('link[rel="canonical"]')?.href || location.href);
      url.search = ''; url.hash = '#' + id;
      let timer; let ok = false;
      button.disabled = true;
      try {
        if (navigator.clipboard) {
          await Promise.race([navigator.clipboard.writeText(url.href), new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('Clipboard permission did not settle')), 1500); })]);
          ok = true;
        }
      } catch (_) {} finally { clearTimeout(timer); button.disabled = false; }
      notice.hidden = false;
      notice.textContent = ok ? 'Copied link.' : `Copy unavailable. Copy this link manually: ${url.href}`;
      button.focus({preventScroll:true});
    });
  });
})();
