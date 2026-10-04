'use strict';
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
  const closeNav = () => { document.body.classList.remove('nav-open'); menu.setAttribute('aria-expanded', 'false'); };
  menu.addEventListener('click', () => { const open = document.body.classList.toggle('nav-open'); menu.setAttribute('aria-expanded', String(open)); });
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
})();
