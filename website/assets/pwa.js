(() => {
  'use strict';
  if (!('serviceWorker' in navigator) || !window.isSecureContext) return;
  function start() {
    const host = document.querySelector('#main footer') || document.querySelector('#main');
    if (!host || document.getElementById('pwa-controls')) return;
    const section = document.createElement('div');
    section.id = 'pwa-controls';section.className = 'pwa-controls';section.setAttribute('aria-label', 'Offline and installation');
    section.innerHTML = '<p id="pwa-install-help">For installation, use your browser’s Install app command if available. On iPhone/iPad, use Safari Share → Add to Home Screen. Availability depends on your browser; this does not confirm installation.</p><button id="pwa-install" type="button" hidden>Install MDAAI</button><div id="pwa-update" hidden><p>A newer version is available. Refresh may discard unsaved input in this tab.</p><button id="pwa-refresh" type="button">Refresh</button> <button id="pwa-later" type="button">Later</button></div><p id="pwa-message" role="status" aria-live="polite"></p>';
    host.append(section);
    const notice = section.querySelector('#pwa-update');
    const refresh = section.querySelector('#pwa-refresh');
    const message = section.querySelector('#pwa-message');
    const install = section.querySelector('#pwa-install');
    let requested = false, reloaded = false, timer, prompt;
    const reveal = () => {notice.hidden = false;};
    const recover = text => {clearTimeout(timer);requested = false;refresh.disabled = false;message.textContent = text;};
    const reload = () => {if (!reloaded) {reloaded = true;clearTimeout(timer);location.reload();}};
    // Bind before registration: activation can occur in a different tab.
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (requested) reload();
      else if (navigator.serviceWorker.controller && section.dataset.controlled === 'yes') reveal();
      section.dataset.controlled = 'yes';
    });
    section.dataset.controlled = navigator.serviceWorker.controller ? 'yes' : 'no';
    section.querySelector('#pwa-later').addEventListener('click', () => {notice.hidden = true;});
    refresh.addEventListener('click', async () => {
      if (requested) return;
      if (!navigator.onLine) {message.textContent = 'Reconnect before refreshing. Your input has been kept.';return;}
      requested = true;refresh.disabled = true;message.textContent = 'Preparing refresh…';
      timer = setTimeout(() => recover('Refresh did not finish. Reconnect and try again; your input has been kept.'), 8000);
      try {
        // Verify connectivity before allowing explicit refresh to discard a draft.
        const abort = new AbortController();
        const timeout = setTimeout(() => abort.abort(), 4000);
        let response;
        try {response = await fetch('/service-worker.js', {cache:'no-store', signal:abort.signal});}
        finally {clearTimeout(timeout);}
        if (!response.ok) throw new Error('Worker unavailable');
        const registration = await navigator.serviceWorker.getRegistration();
        if (!requested) return;
        if (registration?.waiting) registration.waiting.postMessage({type:'ACTIVATE_UPDATE'});
        else reload(); // Another tab already activated: never use a stale waiting reference.
      } catch (_) {recover('Reconnect and try Refresh again. Your input has been kept.');}
    });
    window.addEventListener('beforeinstallprompt', event => {event.preventDefault();prompt = event;install.hidden = false;});
    window.addEventListener('appinstalled', () => {prompt = null;install.hidden = true;message.textContent = 'MDAAI installation reported by your browser.';});
    install.addEventListener('click', async () => {
      if (!prompt) return;
      const native = prompt;prompt = null;install.hidden = true;
      try {await native.prompt();await native.userChoice;message.textContent = 'Installation choice handled by your browser.';}
      catch (_) {message.textContent = 'Use the installation instructions above.';}
    });
    navigator.serviceWorker.register('/service-worker.js', {scope:'/', updateViaCache:'none'}).then(registration => {
      if (registration.waiting) reveal();
      registration.addEventListener('updatefound', () => {
        const worker = registration.installing;
        worker?.addEventListener('statechange', () => {if (worker.state === 'installed' && registration.waiting && navigator.serviceWorker.controller) reveal();});
      });
      const check = () => registration.update().catch(() => {});
      window.addEventListener('online', check);
      document.addEventListener('visibilitychange', () => {if (document.visibilityState === 'visible') check();});
    }).catch(() => {message.textContent = 'Offline reading is unavailable right now. You can still browse online.';});
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once:true});
  else start();
})();
