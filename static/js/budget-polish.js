// Site enhancement loader.
(function () {
  function loadScript(src) {
    if (document.querySelector('script[src="' + src + '"]')) return;
    const s = document.createElement('script');
    s.src = src;
    s.defer = true;
    document.head.appendChild(s);
  }
  function loadDynamicRoutines() {
    if (!location.pathname.startsWith('/cards')) return;
    loadScript('/static/js/dynamic-routine-list.js?v=' + Date.now());
  }
  document.addEventListener('DOMContentLoaded', loadDynamicRoutines);
  window.addEventListener('load', loadDynamicRoutines);
})();
