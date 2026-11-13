// ============================================================================
// GEMINITRANS MODULE: Tab Text
// Error Boundary: Isolated execution - does not affect other tabs
// ============================================================================
(function(window, document) {
  'use strict';
  try {
    // ==========================================
    // TAB 2: TEXT TRANSLATE
    // ==========================================
    function updateCharCount() {
      const srcTextEl = document.getElementById('src-text');
      if (!srcTextEl) return;
      const charCountEl = document.getElementById('src-char-count');
      if (charCountEl) {
        charCountEl.innerText = t('char_count_format', { count: srcTextEl.value.length });
      }
    }
    function clearSourceText() {
      document.getElementById('src-text').value = '';
      document.getElementById('target-text').innerHTML = `<span class="text-slate-600 italic">${t('target_placeholder')}</span>`;
      updateCharCount();
    }
    function swapLanguages() {
      const src = document.getElementById('source-lang');
      const tgt = document.getElementById('target-lang');
      if (src.value === 'auto') return;
      const tmp = src.value;
      src.value = tgt.value;
      tgt.value = tmp;
    }
    function handleFileUpload(event) {
      const file = event.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (e) => {
        document.getElementById('src-text').value = e.target.result;
        updateCharCount();
      };
      reader.readAsText(file);
    }
    async function startTranslation() {
      const text = document.getElementById('src-text').value.trim();
      if (!text) return alert(t('alert_no_text'));
      const targetDiv = document.getElementById('target-text');
      const statusIndicator = document.getElementById('translate-status');
      targetDiv.innerText = '';
      statusIndicator.classList.remove('hidden');

      try {
        const response = await fetch('/api/translate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: text,
            source_lang: document.getElementById('source-lang').value,
            target_lang: document.getElementById('target-lang').value,
            tier: document.getElementById('tier-select').value,
            stream: true
          })
        });
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let done = false;
        while (!done) {
          const { value, done: rDone } = await reader.read();
          done = rDone;
          if (value) {
            const rawChunk = decoder.decode(value, { stream: true });
            const lines = rawChunk.split('\n');
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const dataStr = line.slice(6).trim();
                if (dataStr === '[DONE]') break;
                try {
                  const parsed = JSON.parse(dataStr);
                  if (parsed.chunk) targetDiv.innerText += parsed.chunk;
                } catch (e) {}
              }
            }
          }
        }
      } catch (err) {
        targetDiv.innerText = `Error: ${err.message}`;
      } finally {
        statusIndicator.classList.add('hidden');
        fetchPoolStatus();
      }
    }
    function copyTargetText() {
      navigator.clipboard.writeText(document.getElementById('target-text').innerText);
      alert(t('alert_copied'));
    }
    function downloadTargetText() {
      const blob = new Blob([document.getElementById('target-text').innerText], { type: 'text/plain;charset=utf-8' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `translated_${new Date().toISOString().slice(0,10)}.txt`;
      a.click();
    }


    function switchTextSubMode(mode) {
      webState.subMode = mode;
      const textBtn = document.getElementById('submode-btn-text');
      const webBtn = document.getElementById('submode-btn-web');
      const textContainer = document.getElementById('text-mode-container');
      const webContainer = document.getElementById('web-mode-container');
      const tagline = document.getElementById('submode-tagline');

      if (mode === 'web') {
        if (textBtn) {
          textBtn.className = "px-4 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition text-slate-400 hover:text-white cursor-pointer";
        }
        if (webBtn) {
          webBtn.className = "px-4 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition bg-cyan-600 text-white shadow cursor-pointer";
        }
        if (textContainer) textContainer.classList.add('hidden');
        if (webContainer) webContainer.classList.remove('hidden');
        if (tagline) tagline.innerText = currentLang === 'vi' ? 'Dịch toàn bộ trang web & giữ nguyên bố cục HTML/CSS' : 'Full webpage translator preserving layout/CSS';
      } else {
        if (textBtn) {
          textBtn.className = "px-4 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition bg-indigo-600 text-white shadow cursor-pointer";
        }
        if (webBtn) {
          webBtn.className = "px-4 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition text-slate-400 hover:text-white cursor-pointer";
        }
        if (textContainer) textContainer.classList.remove('hidden');
        if (webContainer) webContainer.classList.add('hidden');
        if (tagline) tagline.innerText = currentLang === 'vi' ? 'Dịch văn bản thuần, tài liệu hoặc phụ đề' : 'Plain text, documents or subtitles translator';
      }
      if (window.lucide && lucide.createIcons) lucide.createIcons();
    }


    // Expose functions to window for HTML inline event handlers
    window.updateCharCount = typeof updateCharCount !== 'undefined' ? updateCharCount : undefined;
    window.clearSourceText = typeof clearSourceText !== 'undefined' ? clearSourceText : undefined;
    window.swapLanguages = typeof swapLanguages !== 'undefined' ? swapLanguages : undefined;
    window.handleFileUpload = typeof handleFileUpload !== 'undefined' ? handleFileUpload : undefined;
    window.startTranslation = typeof startTranslation !== 'undefined' ? startTranslation : undefined;
    window.copyTargetText = typeof copyTargetText !== 'undefined' ? copyTargetText : undefined;
    window.downloadTargetText = typeof downloadTargetText !== 'undefined' ? downloadTargetText : undefined;
    window.switchTextSubMode = typeof switchTextSubMode !== 'undefined' ? switchTextSubMode : undefined;
  } catch (err) {
    console.error('[GeminiTrans Error Boundary - Tab Text]', err);
    if (window.showToast) {
      window.showToast('Lỗi khởi tạo module Tab Text: ' + err.message, 'error');
    }
  }
})(window, document);
