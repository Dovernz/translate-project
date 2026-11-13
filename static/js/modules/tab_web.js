// ============================================================================
// GEMINITRANS MODULE: Tab Web
// Error Boundary: Isolated execution - does not affect other tabs
// ============================================================================
(function(window, document) {
  'use strict';
  try {

    // Webpage Translation State
    const webState = window.webState || {
      url: '',
      title: '',
      translatedTitle: '',
      viewMode: 'split',
      syncScroll: true,
      originalHtml: '',
      translatedHtml: '',
      isLoading: false
    };
    window.webState = webState;

    async function pasteWebUrl() {
      try {
        const text = await navigator.clipboard.readText();
        if (text && text.trim()) {
          const input = document.getElementById('web-url-input');
          if (input) {
            input.value = text.trim();
            showToast(currentLang === 'vi' ? 'Đã dán link từ clipboard!' : 'Pasted link from clipboard!');
          }
        }
      } catch (err) {
        showToast(currentLang === 'vi' ? 'Không thể truy cập clipboard' : 'Cannot access clipboard', 'error');
      }
    }

    function toggleSyncScroll(enabled) {
      webState.syncScroll = !!enabled;
      const check = document.getElementById('web-sync-scroll-check');
      if (check) check.checked = webState.syncScroll;
      if (!webState.syncScroll) {
        if (syncScrollRafId) {
          cancelAnimationFrame(syncScrollRafId);
          syncScrollRafId = null;
        }
        syncScrollPending = null;
        isSyncScrollDispatching = false;
        syncScrollActiveDriver = null;
      }
    }

    function toggleWebQuickSwitch() {
      if (webState.viewMode === 'translated') {
        setWebViewMode('original');
      } else if (webState.viewMode === 'original') {
        setWebViewMode('translated');
      } else {
        // From split, switch to single translated
        setWebViewMode('translated');
      }
    }

    function setWebViewMode(mode) {
      webState.viewMode = mode;
      const btnTrans = document.getElementById('web-view-btn-trans');
      const btnOrig = document.getElementById('web-view-btn-orig');
      const btnSplit = document.getElementById('web-view-btn-split');
      const grid = document.getElementById('web-viewports-grid');
      const colOrig = document.getElementById('web-col-orig');
      const colTrans = document.getElementById('web-col-trans');

      // Reset button styles
      [btnTrans, btnOrig, btnSplit].forEach(btn => {
        if (btn) btn.className = "px-3 py-1 rounded-md text-xs font-semibold transition text-slate-400 hover:text-white cursor-pointer";
      });

      if (mode === 'translated') {
        if (btnTrans) btnTrans.className = "px-3 py-1 rounded-md text-xs font-semibold transition bg-indigo-600 text-white shadow cursor-pointer";
        if (grid) grid.className = "grid grid-cols-1 gap-3 transition-all duration-200";
        if (colOrig) colOrig.classList.add('hidden');
        if (colTrans) colTrans.classList.remove('hidden');
      } else if (mode === 'original') {
        if (btnOrig) btnOrig.className = "px-3 py-1 rounded-md text-xs font-semibold transition bg-cyan-600 text-white shadow cursor-pointer";
        if (grid) grid.className = "grid grid-cols-1 gap-3 transition-all duration-200";
        if (colOrig) colOrig.classList.remove('hidden');
        if (colTrans) colTrans.classList.add('hidden');
      } else { // split
        if (btnSplit) btnSplit.className = "px-3 py-1 rounded-md text-xs font-semibold transition bg-indigo-600 text-white shadow cursor-pointer";
        if (grid) grid.className = "grid grid-cols-1 lg:grid-cols-2 gap-3 transition-all duration-200";
        if (colOrig) colOrig.classList.remove('hidden');
        if (colTrans) colTrans.classList.remove('hidden');
      }
    }

    // ==========================================
    // SYNCHRONIZED SCROLLING CONTROLLER (ACTIVE DRIVER + RAF 60FPS)
    // ==========================================
    let syncScrollActiveDriver = null; // 'orig' | 'trans' | null
    let syncScrollDriverTimer = null;
    let isSyncScrollDispatching = false;
    let syncScrollRafId = null;
    let syncScrollPending = null; // { targetIframe: HTMLIFrameElement, ratio: number }

    function setSyncScrollActiveDriver(driverRole) {
      if (syncScrollActiveDriver !== driverRole) {
        syncScrollActiveDriver = driverRole;
      }
      if (syncScrollDriverTimer) {
        clearTimeout(syncScrollDriverTimer);
      }
      // Keep driver role active during interaction, auto-release after 350ms idle
      syncScrollDriverTimer = setTimeout(() => {
        syncScrollActiveDriver = null;
      }, 350);
    }

    function handleSyncScroll(driverRole) {
      if (!webState.syncScroll || isSyncScrollDispatching) return;
      // If the other column is currently driving, ignore scroll events from this column (prevent ping-pong cycle)
      if (syncScrollActiveDriver && syncScrollActiveDriver !== driverRole) return;

      setSyncScrollActiveDriver(driverRole);

      const origIframe = document.getElementById('web-orig-iframe');
      const transIframe = document.getElementById('web-trans-iframe');
      if (!origIframe || !transIframe) return;

      const sourceIframe = driverRole === 'orig' ? origIframe : transIframe;
      const targetIframe = driverRole === 'orig' ? transIframe : origIframe;

      try {
        const sWin = sourceIframe.contentWindow;
        if (!sWin || !sWin.document) return;
        const sDoc = sWin.document.scrollingElement || sWin.document.documentElement || sWin.document.body;
        if (!sDoc) return;

        const sScrollTop = sWin.scrollY || sDoc.scrollTop || 0;
        const sMax = Math.max(0, (sDoc.scrollHeight || 0) - (sWin.innerHeight || sDoc.clientHeight || 0));
        if (sMax <= 0) return;

        const ratio = Math.max(0, Math.min(1, sScrollTop / sMax));
        syncScrollPending = { targetIframe, ratio };

        if (!syncScrollRafId) {
          syncScrollRafId = requestAnimationFrame(() => {
            syncScrollRafId = null;
            if (!syncScrollPending || !webState.syncScroll) return;
            const { targetIframe: tgt, ratio: r } = syncScrollPending;
            syncScrollPending = null;

            try {
              const tWin = tgt.contentWindow;
              if (!tWin || !tWin.document) return;
              const tDoc = tWin.document.scrollingElement || tWin.document.documentElement || tWin.document.body;
              if (!tDoc) return;

              const tMax = Math.max(0, (tDoc.scrollHeight || 0) - (tWin.innerHeight || tDoc.clientHeight || 0));
              if (tMax <= 0) return;

              const targetY = Math.round(r * tMax);
              const currentY = tWin.scrollY || tDoc.scrollTop || 0;
              if (Math.abs(currentY - targetY) < 1) return;

              isSyncScrollDispatching = true;
              tWin.scrollTo({ top: targetY, behavior: 'auto' });
              if (tDoc.scrollTop !== targetY) {
                tDoc.scrollTop = targetY;
              }

              requestAnimationFrame(() => {
                isSyncScrollDispatching = false;
              });
            } catch (err) {
              isSyncScrollDispatching = false;
            }
          });
        }
      } catch (e) {
        // Safe cross-origin / access error guard
      }
    }

    function attachIframeScrollSync() {
      const origIframe = document.getElementById('web-orig-iframe');
      const transIframe = document.getElementById('web-trans-iframe');
      const origCol = document.getElementById('web-col-orig');
      const transCol = document.getElementById('web-col-trans');
      if (!origIframe || !transIframe) return;

      const bindPointerEvents = (container, role) => {
        if (!container || container._syncDriverBound) return;
        container._syncDriverBound = true;
        const setDriver = () => setSyncScrollActiveDriver(role);
        ['pointerenter', 'pointermove', 'wheel', 'touchstart'].forEach(evt => {
          container.addEventListener(evt, setDriver, { passive: true });
        });
      };

      bindPointerEvents(origCol, 'orig');
      bindPointerEvents(transCol, 'trans');

      function bindIframe(iframe, role) {
        try {
          const win = iframe.contentWindow;
          const doc = iframe.contentDocument;
          const setDriver = () => setSyncScrollActiveDriver(role);
          const onScroll = () => handleSyncScroll(role);

          if (win) {
            win.onscroll = onScroll;
            win.addEventListener('scroll', onScroll, { passive: true });
            win.addEventListener('wheel', setDriver, { passive: true });
          }

          if (doc) {
            doc.onscroll = onScroll;
            doc.addEventListener('scroll', onScroll, { passive: true });
            ['pointermove', 'wheel', 'touchstart'].forEach(evt => {
              doc.addEventListener(evt, setDriver, { passive: true });
            });
          }
        } catch (e) {
          // ignore any cross-origin restrictions
        }
      }

      bindIframe(origIframe, 'orig');
      bindIframe(transIframe, 'trans');
    }

    // ==========================================
    // CLIENT-SIDE CACHE & BROWSER NAVIGATION STACK
    // ==========================================
    const webClientCache = new Map(); // key: `${targetLang}:::${url}`
    const webHistory = []; // Array<{ url: string, targetLang: string, title?: string }>
    let webHistoryIndex = -1;

    function setWebCacheBadge(show, label = '0ms Cache Hit') {
      const b1 = document.getElementById('web-cache-badge');
      const b2 = document.getElementById('web-tb-cache-badge');
      [b1, b2].forEach(b => {
        if (b) {
          if (show) {
            b.innerText = label;
            b.classList.remove('hidden');
          } else {
            b.classList.add('hidden');
          }
        }
      });
    }

    function updateWebNavButtons() {
      const canBack = webHistoryIndex > 0;
      const canForward = webHistoryIndex >= 0 && webHistoryIndex < webHistory.length - 1;

      const navBack = document.getElementById('btn-web-nav-back');
      const navFwd = document.getElementById('btn-web-nav-forward');
      const tbBack = document.getElementById('btn-web-tb-back');
      const tbFwd = document.getElementById('btn-web-tb-forward');

      [navBack, tbBack].forEach(btn => {
        if (btn) {
          btn.disabled = !canBack;
          if (canBack) {
            btn.classList.remove('opacity-40', 'cursor-not-allowed', 'text-slate-500');
            btn.classList.add('text-slate-200', 'hover:text-cyan-400');
          } else {
            btn.classList.remove('text-slate-200', 'hover:text-cyan-400');
            btn.classList.add('opacity-40', 'cursor-not-allowed', 'text-slate-500');
          }
        }
      });

      [navFwd, tbFwd].forEach(btn => {
        if (btn) {
          btn.disabled = !canForward;
          if (canForward) {
            btn.classList.remove('opacity-40', 'cursor-not-allowed', 'text-slate-500');
            btn.classList.add('text-slate-200', 'hover:text-cyan-400');
          } else {
            btn.classList.remove('text-slate-200', 'hover:text-cyan-400');
            btn.classList.add('opacity-40', 'cursor-not-allowed', 'text-slate-500');
          }
        }
      });
      if (window.lucide && lucide.createIcons) lucide.createIcons();
    }

    function pushWebHistory(url, targetLang, title) {
      if (!url) return;
      if (webHistoryIndex >= 0 && webHistory[webHistoryIndex]) {
        const cur = webHistory[webHistoryIndex];
        if (cur.url === url && cur.targetLang === targetLang) {
          return;
        }
      }
      // If navigating to a new URL after moving back in history, discard forward stack
      if (webHistoryIndex < webHistory.length - 1) {
        webHistory.splice(webHistoryIndex + 1);
      }
      webHistory.push({ url, targetLang, title: title || url });
      webHistoryIndex = webHistory.length - 1;
      updateWebNavButtons();
    }

    function webNavBack() {
      if (webHistoryIndex > 0) {
        webHistoryIndex--;
        const entry = webHistory[webHistoryIndex];
        const input = document.getElementById('web-url-input');
        if (input) input.value = entry.url;
        const targetLangSelect = document.getElementById('web-target-lang');
        if (targetLangSelect && entry.targetLang) targetLangSelect.value = entry.targetLang;
        updateWebNavButtons();
        translateWebPage(entry.url, { pushHistory: false, bypassCache: false });
      }
    }

    function webNavForward() {
      if (webHistoryIndex >= 0 && webHistoryIndex < webHistory.length - 1) {
        webHistoryIndex++;
        const entry = webHistory[webHistoryIndex];
        const input = document.getElementById('web-url-input');
        if (input) input.value = entry.url;
        const targetLangSelect = document.getElementById('web-target-lang');
        if (targetLangSelect && entry.targetLang) targetLangSelect.value = entry.targetLang;
        updateWebNavButtons();
        translateWebPage(entry.url, { pushHistory: false, bypassCache: false });
      }
    }

    function webNavRefresh() {
      const input = document.getElementById('web-url-input');
      const currentUrl = (input ? input.value : '').trim() || (webHistory[webHistoryIndex]?.url);
      if (!currentUrl) return;
      showToast(currentLang === 'vi' ? 'Đang làm mới trang web...' : 'Refreshing webpage...');
      translateWebPage(currentUrl, { pushHistory: false, bypassCache: true });
    }

    function navigateToWebUrl(targetUrl) {
      if (!targetUrl) return;
      const input = document.getElementById('web-url-input');
      if (input) input.value = targetUrl;
      translateWebPage(targetUrl, { pushHistory: true, bypassCache: false });
    }

    function attachIframeLinkInterception(iframe) {
      if (!iframe) return;
      try {
        const doc = iframe.contentDocument;
        if (!doc) return;
        doc.addEventListener('click', function(e) {
          const anchor = e.target.closest('a');
          if (!anchor) return;
          const rawHref = anchor.getAttribute('href');
          if (!rawHref || rawHref.startsWith('#') || rawHref.startsWith('javascript:')) return;
          e.preventDefault();
          e.stopPropagation();
          let absUrl = anchor.href;
          if (!absUrl || absUrl.startsWith('about:')) {
            try {
              absUrl = new URL(rawHref, doc.baseURI || window.location.href).href;
            } catch (err) {
              absUrl = rawHref;
            }
          }
          navigateToWebUrl(absUrl);
        }, true);
      } catch (err) {
        // Cross-origin access guard
      }
    }

    // Window message listener for injected interceptor script in iframes
    window.addEventListener('message', function(event) {
      if (event.data && event.data.type === 'GEMINI_TRANS_NAVIGATE' && event.data.url) {
        navigateToWebUrl(event.data.url);
      }
    });

    function renderWebpageData(data, cacheLabel = null) {
      const emptyState = document.getElementById('web-empty-state');
      const workspace = document.getElementById('web-result-workspace');

      webState.url = data.url;
      webState.title = data.title || data.url;
      webState.translatedTitle = data.translated_title || data.title || data.url;
      webState.originalHtml = data.original_html || '';
      webState.translatedHtml = data.translated_html || '';

      if (emptyState) emptyState.classList.add('hidden');
      if (workspace) workspace.classList.remove('hidden');

      const titleEl = document.getElementById('web-result-title');
      if (titleEl) {
        titleEl.innerText = webState.translatedTitle || webState.title;
        titleEl.title = webState.url;
      }

      const countBadge = document.getElementById('web-node-count-badge');
      if (countBadge) {
        countBadge.innerText = `${data.total_nodes || 0} ${currentLang === 'vi' ? 'đoạn đã dịch' : 'nodes translated'}`;
      }

      const extLink = document.getElementById('web-external-link');
      if (extLink) extLink.href = webState.url;

      if (cacheLabel) {
        setWebCacheBadge(true, cacheLabel);
      } else {
        setWebCacheBadge(false);
      }

      const origIframe = document.getElementById('web-orig-iframe');
      const transIframe = document.getElementById('web-trans-iframe');

      if (origIframe) {
        origIframe.srcdoc = webState.originalHtml;
        origIframe.onload = () => {
          // Defensive shield: dismiss any unmounted React splash/preloader overlays (e.g. Oracle #highline-mount)
          try {
            const doc = origIframe.contentDocument;
            if (doc) {
              const mounts = doc.querySelectorAll('#highline-mount, [id$="-mount"]:empty, .preloader, #preloader, .loading-screen');
              mounts.forEach(m => m.remove());
            }
          } catch(e) {}

          attachIframeScrollSync();
          attachIframeLinkInterception(origIframe);
        };
      }
      if (transIframe) {
        transIframe.srcdoc = webState.translatedHtml;
        transIframe.onload = () => {
          // Defensive shield: dismiss any unmounted React splash/preloader overlays (e.g. Oracle #highline-mount)
          try {
            const doc = transIframe.contentDocument;
            if (doc) {
              const mounts = doc.querySelectorAll('#highline-mount, [id$="-mount"]:empty, .preloader, #preloader, .loading-screen');
              mounts.forEach(m => m.remove());
            }
          } catch(e) {}

          attachIframeScrollSync();
          attachIframeLinkInterception(transIframe);
        };
      }

      setWebViewMode(webState.viewMode || 'split');
      if (window.lucide && lucide.createIcons) lucide.createIcons();
    }

    async function translateWebPage(customUrl = null, options = {}) {
      const input = document.getElementById('web-url-input');
      const targetLangSelect = document.getElementById('web-target-lang');
      const btn = document.getElementById('btn-web-translate');
      const btnText = document.getElementById('btn-web-translate-text');
      const progressContainer = document.getElementById('web-progress-container');
      const progressText = document.getElementById('web-progress-text');
      const progressBar = document.getElementById('web-progress-bar');

      const url = (customUrl || (input ? input.value : '')).trim();
      if (!url) {
        showToast(currentLang === 'vi' ? 'Vui lòng nhập đường dẫn trang web!' : 'Please enter a webpage URL!', 'error');
        if (input) input.focus();
        return;
      }

      if (!url.startsWith('http://') && !url.startsWith('https://')) {
        showToast(currentLang === 'vi' ? 'URL phải bắt đầu bằng http:// hoặc https://' : 'URL must start with http:// or https://', 'error');
        return;
      }

      const targetLang = targetLangSelect ? targetLangSelect.value : 'vi';
      const cacheKey = `${targetLang}:::${url}`;
      const bypassCache = !!options.bypassCache;
      const shouldPushHistory = options.pushHistory !== false;

      // 1. Check Client-side Memory Cache (Instant, 0ms, 100% token saved)
      if (!bypassCache && webClientCache.has(cacheKey)) {
        const cachedData = webClientCache.get(cacheKey);
        renderWebpageData(cachedData, '0ms Client Cache');
        if (shouldPushHistory) {
          pushWebHistory(url, targetLang, cachedData.translated_title || cachedData.title);
        } else {
          updateWebNavButtons();
        }
        showToast(currentLang === 'vi' ? 'Đã tải từ bộ nhớ đệm (0ms)' : 'Loaded from cache (0ms)');
        return;
      }

      // UI state: loading
      webState.isLoading = true;
      if (btn) btn.disabled = true;
      if (btnText) btnText.innerText = currentLang === 'vi' ? 'Đang dịch...' : 'Translating...';
      if (progressContainer) progressContainer.classList.remove('hidden');
      if (progressBar) progressBar.style.width = '35%';
      if (progressText) progressText.innerText = currentLang === 'vi' ? 'Đang tải mã nguồn và phân tích cấu trúc HTML/CSS...' : 'Fetching HTML and parsing layout/CSS...';

      try {
        const res = await fetch('/api/webpage/translate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            url: url,
            target_lang: targetLang,
            tier: 'bulk',
            bypass_cache: bypassCache
          })
        });

        if (progressBar) progressBar.style.width = '85%';
        if (progressText) progressText.innerText = currentLang === 'vi' ? 'Đang hoàn tất render song song...' : 'Finishing parallel rendering...';

        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || 'Không thể dịch trang web');
        }

        // Store into client memory cache
        webClientCache.set(cacheKey, data);

        const cacheLabel = data.from_cache ? (data.cache_source === 'server_memory_lru' ? '0ms Server Memory Cache' : '0ms Server Disk Cache') : null;
        renderWebpageData(data, cacheLabel);

        if (shouldPushHistory) {
          pushWebHistory(url, targetLang, data.translated_title || data.title);
        } else {
          updateWebNavButtons();
        }

        if (data.from_cache) {
          showToast(currentLang === 'vi' ? 'Đã tải từ bộ nhớ đệm máy chủ (0ms)' : 'Loaded from server cache (0ms)');
        } else {
          showToast(currentLang === 'vi' ? `Dịch thành công ${data.total_nodes} đoạn văn!` : `Successfully translated ${data.total_nodes} elements!`);
        }
      } catch (err) {
        console.error('translateWebPage error:', err);
        showToast(err.message || 'Lỗi khi dịch trang web', 'error');
      } finally {
        webState.isLoading = false;
        if (btn) btn.disabled = false;
        if (btnText) btnText.innerText = currentLang === 'vi' ? 'Dịch Trang Web' : 'Translate Webpage';
        if (progressBar) progressBar.style.width = '100%';
        setTimeout(() => {
          if (progressContainer) progressContainer.classList.add('hidden');
          if (progressBar) progressBar.style.width = '0%';
        }, 600);
      }
    }

    // Attach Enter key listener to web-url-input
    document.addEventListener('DOMContentLoaded', () => {
      const urlInput = document.getElementById('web-url-input');
      if (urlInput) {
        urlInput.addEventListener('keydown', (e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            translateWebPage();
          }
        });
      }
    });



    // Expose functions to window for HTML inline event handlers
    window.webState = typeof webState !== 'undefined' ? webState : undefined;
    window.pasteWebUrl = typeof pasteWebUrl !== 'undefined' ? pasteWebUrl : undefined;
    window.toggleSyncScroll = typeof toggleSyncScroll !== 'undefined' ? toggleSyncScroll : undefined;
    window.toggleWebQuickSwitch = typeof toggleWebQuickSwitch !== 'undefined' ? toggleWebQuickSwitch : undefined;
    window.setWebViewMode = typeof setWebViewMode !== 'undefined' ? setWebViewMode : undefined;
    window.setSyncScrollActiveDriver = typeof setSyncScrollActiveDriver !== 'undefined' ? setSyncScrollActiveDriver : undefined;
    window.handleSyncScroll = typeof handleSyncScroll !== 'undefined' ? handleSyncScroll : undefined;
    window.attachIframeScrollSync = typeof attachIframeScrollSync !== 'undefined' ? attachIframeScrollSync : undefined;
    window.setWebCacheBadge = typeof setWebCacheBadge !== 'undefined' ? setWebCacheBadge : undefined;
    window.updateWebNavButtons = typeof updateWebNavButtons !== 'undefined' ? updateWebNavButtons : undefined;
    window.pushWebHistory = typeof pushWebHistory !== 'undefined' ? pushWebHistory : undefined;
    window.webNavBack = typeof webNavBack !== 'undefined' ? webNavBack : undefined;
    window.webNavForward = typeof webNavForward !== 'undefined' ? webNavForward : undefined;
    window.webNavRefresh = typeof webNavRefresh !== 'undefined' ? webNavRefresh : undefined;
    window.navigateToWebUrl = typeof navigateToWebUrl !== 'undefined' ? navigateToWebUrl : undefined;
    window.attachIframeLinkInterception = typeof attachIframeLinkInterception !== 'undefined' ? attachIframeLinkInterception : undefined;
    window.renderWebpageData = typeof renderWebpageData !== 'undefined' ? renderWebpageData : undefined;
    window.translateWebPage = typeof translateWebPage !== 'undefined' ? translateWebPage : undefined;
  } catch (err) {
    console.error('[GeminiTrans Error Boundary - Tab Web]', err);
    if (window.showToast) {
      window.showToast('Lỗi khởi tạo module Tab Web: ' + err.message, 'error');
    }
  }
})(window, document);
