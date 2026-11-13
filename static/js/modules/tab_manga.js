// ============================================================================
// GEMINITRANS MODULE: Tab Manga
// Error Boundary: Isolated execution - does not affect other tabs
// ============================================================================
(function(window, document) {
  'use strict';
  try {
    // ==========================================
    // TAB 4: MANGA & COMIC TRANSLATOR CONTROLLER
    // ==========================================
    const mangaState = {
      sessionId: null,
      pages: [],
      viewMode: 'translated', // 'translated' | 'original' | 'split'
      bilingualActive: false,
      zoomLevel: 100,
      isTranslatingAll: false,
      seriesTitle: '',
      chapters: [],
      currentChapterIndex: -1,
      currentChapterUrl: '',
      autoTranslateOnSwitch: true,
      lightboxPageIndex: 1,
      lightboxMode: 'translated',
      lightboxZoom: 100
    };

    function updateChapterNavUI() {
      const dropdown = document.getElementById('manga-chapter-dropdown');
      const bottomDropdown = document.getElementById('manga-bottom-chapter-dropdown');
      const prevBtn = document.getElementById('btn-manga-prev');
      const nextBtn = document.getElementById('btn-manga-next');
      const bottomPrevBtn = document.getElementById('btn-manga-bottom-prev');
      const bottomNextBtn = document.getElementById('btn-manga-bottom-next');
      const chapterInfo = document.getElementById('manga-chapter-info');

      if (!dropdown) return;

      if (!mangaState.chapters || mangaState.chapters.length === 0) {
        const defaultOpt = `<option value="">${t('manga_select_chapter')}</option>`;
        dropdown.innerHTML = defaultOpt;
        if (bottomDropdown) bottomDropdown.innerHTML = defaultOpt;
        if (prevBtn) prevBtn.disabled = true;
        if (nextBtn) nextBtn.disabled = true;
        if (bottomPrevBtn) bottomPrevBtn.disabled = true;
        if (bottomNextBtn) bottomNextBtn.disabled = true;
        return;
      }

      let options = '';
      mangaState.chapters.forEach((c, idx) => {
        const isSel = idx === mangaState.currentChapterIndex;
        options += `<option value="${c.url}" ${isSel ? 'selected' : ''}>${c.name}</option>`;
      });
      dropdown.innerHTML = options;
      if (bottomDropdown) bottomDropdown.innerHTML = options;

      const hasPrev = mangaState.currentChapterIndex > 0;
      const hasNext = mangaState.currentChapterIndex < mangaState.chapters.length - 1;
      if (prevBtn) prevBtn.disabled = !hasPrev;
      if (nextBtn) nextBtn.disabled = !hasNext;
      if (bottomPrevBtn) bottomPrevBtn.disabled = !hasPrev;
      if (bottomNextBtn) bottomNextBtn.disabled = !hasNext;

      if (chapterInfo && mangaState.currentChapterIndex >= 0 && mangaState.chapters[mangaState.currentChapterIndex]) {
        const titlePrefix = mangaState.seriesTitle ? `${mangaState.seriesTitle} - ` : '';
        chapterInfo.innerText = `${titlePrefix}${mangaState.chapters[mangaState.currentChapterIndex].name}`;
      }
    }

    async function scanMangaChapters() {
      const urlInput = document.getElementById('manga-url-input');
      const statusEl = document.getElementById('manga-url-status');
      const btn = document.getElementById('btn-manga-scan-series');
      const url = urlInput ? urlInput.value.trim() : '';

      if (!url) {
        alert("Vui lòng dán link Dịch Truyện để quét!");
        return;
      }

      if (btn) btn.disabled = true;
      if (statusEl) statusEl.innerText = "Gemini AI đang phân tích cấu trúc website truyện...";

      try {
        const res = await fetch('/api/manga/chapters', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: url })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Không thể quét chapter");

        mangaState.seriesTitle = data.comic_title || data.series_title || '';
        mangaState.chapters = data.chapters || [];
        mangaState.currentChapterIndex = data.current_chapter_index >= 0 ? data.current_chapter_index : 0;
        mangaState.currentChapterUrl = data.current_chapter_url || url;

        updateChapterNavUI();

        const titleText = mangaState.seriesTitle ? `[${mangaState.seriesTitle}] ` : '';
        if (statusEl) statusEl.innerText = `${titleText}Tìm thấy ${mangaState.chapters.length} chapter!`;
        const chapterBar = document.getElementById('manga-chapter-bar');
        if (chapterBar) {
          chapterBar.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      } catch (err) {
        if (statusEl) statusEl.innerText = "Lỗi: " + err.message;
        alert("Lỗi quét chapter: " + err.message);
      } finally {
        if (btn) btn.disabled = false;
      }
    }

    async function changeChapterOffset(delta) {
      if (!mangaState.chapters || mangaState.chapters.length === 0) return;
      const newIdx = mangaState.currentChapterIndex + delta;
      if (newIdx < 0 || newIdx >= mangaState.chapters.length) return;

      mangaState.currentChapterIndex = newIdx;
      const targetChap = mangaState.chapters[newIdx];
      updateChapterNavUI();
      await loadChapterByUrl(targetChap.url, targetChap.name);
    }

    async function onChapterDropdownChange(chapterUrl) {
      if (!chapterUrl) return;
      const idx = mangaState.chapters.findIndex(c => c.url === chapterUrl);
      if (idx !== -1) {
        mangaState.currentChapterIndex = idx;
      }
      updateChapterNavUI();
      const chapName = (idx !== -1) ? mangaState.chapters[idx].name : '';
      await loadChapterByUrl(chapterUrl, chapName);
    }

    async function loadChapterByUrl(chapterUrl, chapterName = '') {
      const statusEl = document.getElementById('manga-url-status');
      const progressContainer = document.getElementById('manga-progress-container');
      const progressText = document.getElementById('manga-progress-text');
      const progressPercent = document.getElementById('manga-progress-percent');
      const progressBar = document.getElementById('manga-progress-bar');
      const chapterInfo = document.getElementById('manga-chapter-info');

      if (chapterInfo && chapterName) chapterInfo.innerText = chapterName;
      if (progressContainer) {
        progressContainer.classList.remove('hidden');
        if (progressText) progressText.innerText = `Đang tải hình ảnh ${chapterName}...`;
        if (progressPercent) progressPercent.innerText = "15%";
        if (progressBar) progressBar.style.width = "15%";
      }

      try {
        const res = await fetch('/api/manga/process-url', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: chapterUrl })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Không thể tải chapter");

        mangaState.sessionId = data.session_id;
        mangaState.pages = data.pages || [];
        mangaState.currentChapterUrl = chapterUrl;

        // Render Webtoon continuous vertical scroll
        renderMangaWorkspace();

        // Smooth scroll to top of reader viewport
        const viewport = document.getElementById('manga-reader-viewport');
        if (viewport) viewport.scrollTop = 0;

        // Auto translate if checked
        const autoCheck = document.getElementById('manga-auto-trans-check');
        if (!autoCheck || autoCheck.checked) {
          await translateAllManga();
        } else {
          if (progressContainer) progressContainer.classList.add('hidden');
        }
      } catch (err) {
        alert("Lỗi tải chapter: " + err.message);
        if (progressContainer) progressContainer.classList.add('hidden');
      }
    }

    function pasteMangaUrl() {
      navigator.clipboard.readText().then(text => {
        if (text) {
          document.getElementById('manga-url-input').value = text.trim();
        }
      }).catch(err => {
        console.warn('Could not read clipboard:', err);
      });
    }

// ==========================================
    // CLIPBOARD & PASTE IMAGE TO TRANSLATE LOGIC
    // ==========================================

    function showPasteToast(message) {
      let toast = document.getElementById('paste-toast-notification');
      if (!toast) {
        toast = document.createElement('div');
        toast.id = 'paste-toast-notification';
        toast.className = "fixed top-6 right-6 z-50 px-4 py-3 rounded-[10px] bg-slate-900/95 border border-indigo-500/50 shadow-lg border border-slate-800 text-white text-xs sm:text-sm font-semibold flex items-center gap-2.5 transition-all duration-300 pointer-events-none transform -translate-y-5 opacity-0 backdrop-blur";
        document.body.appendChild(toast);
      }
      toast.innerHTML = `<i data-lucide="check-circle-2" class="w-4 h-4 text-emerald-400"></i><span>${message}</span>`;
      if (window.lucide && lucide.createIcons) lucide.createIcons();
      
      toast.classList.remove('-translate-y-5', 'opacity-0');
      toast.classList.add('translate-y-0', 'opacity-100');

      setTimeout(() => {
        toast.classList.remove('translate-y-0', 'opacity-100');
        toast.classList.add('-translate-y-5', 'opacity-0');
      }, 3500);
    }

    async function pasteAndTranslateImage(file) {
      if (!file) return;

      // Switch to manga tab automatically if not already active
      if (typeof switchTab === 'function') {
        switchTab('manga');
      }

      const statusEl = document.getElementById('manga-upload-status');
      if (statusEl) {
        statusEl.innerHTML = `<span class="inline-flex items-center gap-1.5 text-indigo-400 font-semibold"><i data-lucide="loader" class="w-3.5 h-3.5 animate-spin"></i> Đang nạp ảnh & AI inpainting dịch tiếng Việt...</span>`;
        if (window.lucide && lucide.createIcons) lucide.createIcons();
      }

      // Show progress container
      const progressContainer = document.getElementById('manga-progress-container');
      const progressBar = document.getElementById('manga-progress-bar');
      const progressText = document.getElementById('manga-progress-text');
      const progressPercent = document.getElementById('manga-progress-percent');
      if (progressContainer) progressContainer.classList.remove('hidden');
      if (progressBar) progressBar.style.width = '25%';
      if (progressPercent) progressPercent.innerText = '25%';
      if (progressText) progressText.innerText = 'Đang gửi ảnh sang bộ dịch AI Inpainting đa luồng...';

      let fakeProgress = 25;
      const fakeTimer = setInterval(() => {
        if (fakeProgress < 85) {
          fakeProgress += 15;
          if (progressBar) progressBar.style.width = fakeProgress + '%';
          if (progressPercent) progressPercent.innerText = fakeProgress + '%';
          if (progressText) progressText.innerText = `AI Gemini Vision đang nhận diện thoại & inpainting (${fakeProgress}%)...`;
        }
      }, 600);

      const targetLang = document.getElementById('manga-target-lang') ? document.getElementById('manga-target-lang').value : 'vi';

      const formData = new FormData();
      formData.append('file', file, file.name || `clipboard_${Date.now()}.png`);
      formData.append('target_lang', targetLang);

      try {
        const res = await fetch('/api/manga/paste-and-translate', {
          method: 'POST',
          body: formData
        });
        clearInterval(fakeTimer);

        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || "Lỗi dịch ảnh từ Clipboard");
        }

        if (progressBar) progressBar.style.width = '100%';
        if (progressPercent) progressPercent.innerText = '100%';
        if (progressText) progressText.innerText = 'Hoàn tất dịch ảnh từ Clipboard!';

        mangaState.sessionId = data.session_id;
        mangaState.pages = data.pages || [];
        mangaState.viewMode = 'translated';

        if (statusEl) {
          statusEl.innerHTML = `<span class="inline-flex items-center gap-1.5 text-emerald-400 font-semibold"><i data-lucide="check-circle" class="w-3.5 h-3.5"></i> Đã dịch thành công từ Clipboard!</span>`;
        }

        renderMangaWorkspace();

        const workspace = document.getElementById('manga-workspace');
        if (workspace) {
          workspace.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        setTimeout(() => {
          if (progressContainer) progressContainer.classList.add('hidden');
        }, 2500);

      } catch (err) {
        clearInterval(fakeTimer);
        if (progressContainer) progressContainer.classList.add('hidden');
        if (statusEl) {
          statusEl.innerHTML = `<span class="text-rose-400 font-medium">Lỗi: ${err.message}</span>`;
        }
        alert("Lỗi khi xử lý ảnh dán từ Clipboard: " + err.message);
      } finally {
        if (window.lucide && lucide.createIcons) lucide.createIcons();
        if (typeof fetchPoolStatus === 'function') fetchPoolStatus();
      }
    }

    function handleGlobalPaste(e) {
      const activeEl = document.activeElement;
      const isTextInput = activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA' || activeEl.isContentEditable);

      const clipboardData = e.clipboardData || window.clipboardData;
      if (!clipboardData || !clipboardData.items) return;

      let imageItem = null;
      for (let i = 0; i < clipboardData.items.length; i++) {
        const item = clipboardData.items[i];
        if (item.type && item.type.startsWith('image/')) {
          imageItem = item;
          break;
        }
      }

      // If user is pasting text into input field, allow standard behavior
      if (!imageItem) {
        return;
      }

      // If image is present, intercept paste!
      e.preventDefault();
      e.stopPropagation();

      const file = imageItem.getAsFile();
      if (!file) return;

      showPasteToast("Đã nhận diện ảnh từ Clipboard! Đang nạp & dịch...");
      pasteAndTranslateImage(file);
    }

    async function pasteImageFromClipboardButton(e) {
      if (e) {
        e.preventDefault();
        e.stopPropagation();
      }

      if (navigator.clipboard && navigator.clipboard.read) {
        try {
          const items = await navigator.clipboard.read();
          for (const item of items) {
            for (const type of item.types) {
              if (type.startsWith('image/')) {
                const blob = await item.getType(type);
                const file = new File([blob], `clipboard_${Date.now()}.${type.split('/')[1] || 'png'}`, { type });
                showPasteToast("Đang dịch ảnh từ Clipboard...");
                await pasteAndTranslateImage(file);
                return;
              }
            }
          }
          alert("Không tìm thấy dữ liệu ảnh trong Clipboard. Vui lòng Copy ảnh hoặc Chụp màn hình (Snipping Tool / Ctrl+PrtScn) rồi bấm Ctrl + V!");
        } catch (err) {
          console.warn("Clipboard read API:", err);
          alert("Trình duyệt yêu cầu phím tắt: Hãy bấm [Ctrl + V] trực tiếp trên màn hình để dán ảnh từ Clipboard!");
        }
      } else {
        alert("Hãy bấm phím tắt [Ctrl + V] trên bàn phím để dán ảnh từ bộ nhớ tạm!");
      }
    }

    function handleMangaDragOver(e) {
      e.preventDefault();
      e.stopPropagation();
      const dropzone = document.getElementById('manga-dropzone');
      if (dropzone) {
        dropzone.classList.add('border-indigo-500', 'bg-indigo-950/20');
      }
    }

    function handleMangaDragLeave(e) {
      e.preventDefault();
      e.stopPropagation();
      const dropzone = document.getElementById('manga-dropzone');
      if (dropzone) {
        dropzone.classList.remove('border-indigo-500', 'bg-indigo-950/20');
      }
    }

    function handleMangaDrop(e) {
      e.preventDefault();
      e.stopPropagation();
      const dropzone = document.getElementById('manga-dropzone');
      if (dropzone) {
        dropzone.classList.remove('border-indigo-500', 'bg-indigo-950/20');
      }
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        uploadMangaFiles(e.dataTransfer.files);
      }
    }

    function handleMangaFileInput(e) {
      if (e.target.files && e.target.files.length > 0) {
        uploadMangaFiles(e.target.files);
      }
    }

    async function uploadMangaFiles(files) {
      const statusEl = document.getElementById('manga-upload-status');
      if (statusEl) statusEl.innerText = "Đang tải lên " + files.length + " tệp...";

      const formData = new FormData();
      for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
      }

      try {
        const res = await fetch('/api/manga/upload', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || "Lỗi tải ảnh truyện");
        }

        mangaState.sessionId = data.session_id;
        mangaState.pages = data.pages || [];
        if (statusEl) statusEl.innerText = "Đã nạp: " + data.total_pages + " trang";

        renderMangaWorkspace();
      } catch (err) {
        if (statusEl) statusEl.innerText = "Lỗi: " + err.message;
        alert("Lỗi khi tải truyện: " + err.message);
      }
    }

    async function loadMangaFromUrl(autoTranslate = true) {
      const urlInput = document.getElementById('manga-url-input');
      const statusEl = document.getElementById('manga-url-status');
      const btn = document.getElementById('btn-manga-load-url');
      const url = urlInput ? urlInput.value.trim() : '';

      if (!url) {
        alert("Vui lòng dán link web truyện hoặc link ảnh!");
        return;
      }

      if (btn) btn.disabled = true;
      if (statusEl) statusEl.innerText = "Đang kết nối & quét chapter...";

      try {
        // Try to scan chapters in background to enrich navigation
        try {
          const chapRes = await fetch('/api/manga/chapters', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
          });
          if (chapRes.ok) {
            const chapData = await chapRes.json();
            mangaState.seriesTitle = chapData.comic_title || chapData.series_title || '';
            mangaState.chapters = chapData.chapters || [];
            mangaState.currentChapterIndex = chapData.current_chapter_index >= 0 ? chapData.current_chapter_index : 0;
            mangaState.currentChapterUrl = chapData.current_chapter_url || url;
            updateChapterNavUI();
          }
        } catch (e) {
          console.warn("Could not fetch chapters list:", e);
        }

        if (statusEl) statusEl.innerText = "Đang tải trang truyện...";
        const targetUrl = mangaState.currentChapterUrl || url;
        const res = await fetch('/api/manga/process-url', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: targetUrl })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Không thể nạp truyện từ liên kết");

        mangaState.sessionId = data.session_id;
        mangaState.pages = data.pages || [];
        if (statusEl) statusEl.innerText = `Đã nạp ${data.total_pages} trang!`;

        renderMangaWorkspace();

        const autoCheck = document.getElementById('manga-auto-trans-check');
        const shouldTrans = autoTranslate && (!autoCheck || autoCheck.checked);
        if (shouldTrans && mangaState.pages.length > 0) {
          await translateAllManga();
        }
      } catch (err) {
        if (statusEl) statusEl.innerText = "Lỗi: " + err.message;
        alert("Lỗi nạp từ URL: " + err.message);
      } finally {
        if (btn) btn.disabled = false;
      }
    }

    function renderMangaWorkspace() {
      const emptyState = document.getElementById('manga-empty-state');
      const pagesList = document.getElementById('manga-pages-list');
      const chapterInfo = document.getElementById('manga-chapter-info');
      const pageBadge = document.getElementById('manga-page-count-badge');

      if (!mangaState.pages || mangaState.pages.length === 0) {
        if (emptyState) emptyState.classList.remove('hidden');
        if (pagesList) pagesList.innerHTML = '';
        if (chapterInfo) chapterInfo.innerText = "Chapter: Chưa có dữ liệu";
        if (pageBadge) pageBadge.innerText = "0 trang";
        return;
      }

      if (emptyState) emptyState.classList.add('hidden');
      if (chapterInfo) chapterInfo.innerText = "Session #" + (mangaState.sessionId || '').substring(0, 8);
      if (pageBadge) pageBadge.innerText = mangaState.pages.length + " trang";

      let html = '';
      mangaState.pages.forEach((p, idx) => {
        const isTrans = p.status === 'translated' && p.translated_url;
        const currentSrc = (mangaState.viewMode === 'translated' && isTrans) ? p.translated_url : p.original_url;

        html += `
          <div class="w-full bg-slate-900 rounded-[10px] border border-slate-800/90 shadow-xl overflow-hidden transition-all duration-200" id="manga-page-card-${p.page_index}">
            <!-- Header bar of page -->
            <div class="px-4 py-2.5 bg-slate-900/95 border-b border-slate-800 flex flex-wrap items-center justify-between gap-2 text-xs">
              <div class="flex items-center gap-2">
                <span class="font-bold text-slate-200">Trang ${p.page_index}</span>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded-[8px] ${isTrans ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' : 'bg-slate-800 text-slate-400'}">
                  ${isTrans ? (p.bubbles ? `Đã dịch AI (${p.bubbles.length} thoại)` : 'Đã dịch AI') : 'Bản gốc'}
                </span>
              </div>
              <div class="flex items-center gap-2">
                <!-- Hold to view original button -->
                ${isTrans ? `
                <button type="button" 
                        onmousedown="holdCompareManga(${p.page_index}, true)" 
                        onmouseup="holdCompareManga(${p.page_index}, false)" 
                        onmouseleave="holdCompareManga(${p.page_index}, false)" 
                        ontouchstart="holdCompareManga(${p.page_index}, true)" 
                        ontouchend="holdCompareManga(${p.page_index}, false)"
                        class="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition flex items-center gap-1 cursor-pointer select-none border border-slate-700/60" 
                        title="Nhấn giữ chuột để xem bản gốc, thả ra để về bản dịch">
                  <i data-lucide="eye" class="w-3 h-3 text-indigo-400"></i>
                  <span class="text-[11px] font-medium" data-i18n="manga_hold_orig">Giữ xem Gốc</span>
                </button>
                ` : ''}

                <button onclick="translateSingleMangaPage(${p.page_index})" id="btn-trans-page-${p.page_index}" class="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition flex items-center gap-1.5 cursor-pointer border border-slate-700/60">
                  <i data-lucide="cpu" class="w-3 h-3 text-indigo-400"></i>
                  <span>${isTrans ? 'Dịch lại' : 'Dịch trang này'}</span>
                </button>

                <button onclick="openMangaLightbox(${p.page_index})" class="p-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition border border-slate-700/60" title="Phóng to & So sánh chi tiết">
                  <i data-lucide="maximize" class="w-3.5 h-3.5 text-cyan-400"></i>
                </button>
              </div>
            </div>

            <!-- Image Content Container -->
            ${mangaState.viewMode === 'split' ? `
              <div class="grid grid-cols-1 md:grid-cols-2 gap-3 bg-black/70 p-3 sm:p-4">
                <div class="flex flex-col items-center">
                  <div class="text-[11px] font-semibold text-slate-400 mb-1.5 flex items-center gap-1">Bản gốc</div>
                  <img src="${p.original_url}" alt="Original Page ${p.page_index}" class="w-full h-auto object-contain rounded-lg border border-slate-800" loading="lazy">
                </div>
                <div class="flex flex-col items-center">
                  <div class="text-[11px] font-semibold text-emerald-400 mb-1.5 flex items-center gap-1">Bản dịch AI Inpainting</div>
                  <img src="${isTrans ? p.translated_url : p.original_url}" alt="Translated Page ${p.page_index}" class="w-full h-auto object-contain rounded-lg border border-slate-800" loading="lazy">
                </div>
              </div>
            ` : `
              <div class="relative w-full flex justify-center bg-black/50 select-none overflow-hidden" id="manga-img-container-${p.page_index}">
                <img src="${currentSrc}" 
                     alt="Page ${p.page_index}" 
                     id="manga-img-${p.page_index}"
                     class="w-full h-auto object-contain block transition-opacity duration-300"
                     loading="lazy">

                <!-- Interactive Bilingual Tooltip Overlay -->
                <div id="manga-overlay-${p.page_index}" class="absolute inset-0 pointer-events-none ${mangaState.bilingualActive ? '' : 'hidden'}">
                  ${renderBubbleOverlays(p)}
                </div>
              </div>
            `}
          </div>
        `;
      });

      // Bottom Webtoon Chapter Navigation Bar
      if (mangaState.chapters && mangaState.chapters.length > 0) {
        html += `
          <div class="w-full py-6 mt-6 border-t border-slate-800 flex flex-wrap items-center justify-between gap-3 bg-slate-900/60 p-4 rounded-[10px]">
            <div class="flex items-center gap-2">
              <button id="btn-manga-bottom-prev" onclick="changeChapterOffset(-1)" ${mangaState.currentChapterIndex <= 0 ? 'disabled' : ''} class="px-3 py-1.5 rounded-[8px] bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-semibold text-slate-200 hover:text-white flex items-center gap-1.5 transition border border-slate-700/60 shadow cursor-pointer">
                <i data-lucide="chevron-left" class="w-4 h-4 text-indigo-400"></i>
                <span>Chương trước</span>
              </button>

              <select id="manga-bottom-chapter-dropdown" onchange="onChapterDropdownChange(this.value)" class="bg-slate-950 border border-indigo-500/50 hover:border-indigo-400 focus:border-indigo-400 text-indigo-300 font-semibold rounded-[8px] px-3 py-1.5 text-xs focus:outline-none transition shadow-inner max-w-[200px] sm:max-w-[280px] truncate cursor-pointer">
                ${mangaState.chapters.map((c, idx) => `<option value="${c.url}" ${idx === mangaState.currentChapterIndex ? 'selected' : ''}>${c.name}</option>`).join('')}
              </select>

              <button id="btn-manga-bottom-next" onclick="changeChapterOffset(1)" ${mangaState.currentChapterIndex >= mangaState.chapters.length - 1 ? 'disabled' : ''} class="px-3 py-1.5 rounded-[8px] bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-semibold text-slate-200 hover:text-white flex items-center gap-1.5 transition border border-slate-700/60 shadow cursor-pointer">
                <span>Chương tiếp</span>
                <i data-lucide="chevron-right" class="w-4 h-4 text-indigo-400"></i>
              </button>
            </div>

            <button onclick="document.getElementById('manga-reader-viewport').scrollTop = 0" class="px-3 py-1.5 rounded-[8px] bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-medium flex items-center gap-1.5 transition border border-slate-700/60 shadow cursor-pointer">
              <i data-lucide="arrow-up" class="w-3.5 h-3.5 text-cyan-400"></i>
              <span>Lên đầu trang</span>
            </button>
          </div>
        `;
      }

      if (pagesList) pagesList.innerHTML = html;
      if (window.lucide && lucide.createIcons) lucide.createIcons();
    }

    function renderBubbleOverlays(page) {
      if (!page.bubbles || page.bubbles.length === 0) return '';
      return page.bubbles.map(b => {
        const box = b.box_2d || [];
        if (box.length !== 4) return '';
        const ymin = (box[0] / 10).toFixed(1);
        const xmin = (box[1] / 10).toFixed(1);
        const ymax = (box[2] / 10).toFixed(1);
        const xmax = (box[3] / 10).toFixed(1);
        const top = ymin + '%';
        const left = xmin + '%';
        const width = (xmax - xmin) + '%';
        const height = (ymax - ymin) + '%';
        const orig = (b.original || '').replace(/"/g, '&quot;');
        const trans = (b.translated || '').replace(/"/g, '&quot;');

        return `
          <div class="absolute border border-indigo-400/40 bg-indigo-500/10 hover:bg-indigo-500/30 pointer-events-auto rounded transition cursor-help group"
               style="top: ${top}; left: ${left}; width: ${width}; height: ${height};"
               title="Nguyên tác: ${orig}">
            <div class="hidden group-hover:block absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 z-30 w-max max-w-xs p-2 rounded-lg bg-slate-900 border border-slate-700 shadow-lg border border-slate-800 text-[11px] text-white">
              <p class="text-indigo-300 font-semibold mb-0.5">Gốc:</p>
              <p class="italic text-slate-300">${orig || '(Không có chữ)'}</p>
              <p class="text-emerald-400 font-semibold mt-1 mb-0.5">Dịch:</p>
              <p class="text-slate-200">${trans}</p>
            </div>
          </div>
        `;
      }).join('');
    }

    function setMangaViewMode(mode) {
      mangaState.viewMode = mode;
      const btnTrans = document.getElementById('manga-view-btn-trans');
      const btnOrig = document.getElementById('manga-view-btn-orig');
      const btnSplit = document.getElementById('manga-view-btn-split');

      const activeCls = "px-2.5 py-1 rounded-md text-xs font-semibold transition bg-indigo-600 text-white shadow";
      const inactiveCls = "px-2.5 py-1 rounded-md text-xs font-semibold transition text-slate-400 hover:text-white";

      if (btnTrans) btnTrans.className = mode === 'translated' ? activeCls : inactiveCls;
      if (btnOrig) btnOrig.className = mode === 'original' ? activeCls : inactiveCls;
      if (btnSplit) btnSplit.className = mode === 'split' ? activeCls : inactiveCls;

      const list = document.getElementById('manga-pages-list');
      if (list) {
        if (mode === 'split') {
          list.classList.remove('max-w-2xl');
          const targetWidth = Math.round(1400 * (mangaState.zoomLevel / 100));
          list.style.maxWidth = targetWidth + 'px';
        } else {
          list.classList.add('max-w-2xl');
          const targetWidth = Math.round(672 * (mangaState.zoomLevel / 100));
          list.style.maxWidth = targetWidth + 'px';
        }
      }

      renderMangaWorkspace();
    }

    function holdCompareManga(pageIndex, isHolding) {
      const p = mangaState.pages.find(item => item.page_index === pageIndex);
      if (!p) return;
      const img = document.getElementById('manga-img-' + pageIndex);
      if (!img) return;

      if (isHolding) {
        img.src = p.original_url;
      } else {
        const isTrans = p.status === 'translated' && p.translated_url;
        img.src = (mangaState.viewMode === 'translated' && isTrans) ? p.translated_url : p.original_url;
      }
    }

    function zoomMangaReset() {
      mangaState.zoomLevel = 100;
      const zoomText = document.getElementById('manga-zoom-text');
      if (zoomText) zoomText.innerText = "100%";
      const list = document.getElementById('manga-pages-list');
      if (list) {
        const base = mangaState.viewMode === 'split' ? 1400 : 672;
        list.style.maxWidth = base + 'px';
      }
    }

    // ==========================================
    // LIGHTBOX / ZOOM / FULLSCREEN COMPARISON
    // ==========================================

    function openMangaLightbox(pageIndex) {
      mangaState.lightboxPageIndex = pageIndex;
      mangaState.lightboxMode = mangaState.viewMode === 'split' ? 'split' : 'translated';
      mangaState.lightboxZoom = 100;

      const modal = document.getElementById('manga-lightbox-modal');
      if (!modal) return;
      modal.classList.remove('hidden');

      setLightboxMode(mangaState.lightboxMode);
    }

    function closeMangaLightbox(e) {
      if (e && e.target && e.target.closest('#manga-lightbox-content')) return;
      const modal = document.getElementById('manga-lightbox-modal');
      if (modal) modal.classList.add('hidden');
    }

    function setLightboxMode(mode) {
      mangaState.lightboxMode = mode;
      const btnTrans = document.getElementById('lb-btn-trans');
      const btnOrig = document.getElementById('lb-btn-orig');
      const btnSplit = document.getElementById('lb-btn-split');

      const activeCls = "px-2.5 py-1 rounded font-semibold bg-indigo-600 text-white transition";
      const inactiveCls = "px-2.5 py-1 rounded font-semibold text-slate-400 hover:text-white transition";

      if (btnTrans) btnTrans.className = mode === 'translated' ? activeCls : inactiveCls;
      if (btnOrig) btnOrig.className = mode === 'original' ? activeCls : inactiveCls;
      if (btnSplit) btnSplit.className = mode === 'split' ? activeCls : inactiveCls;

      renderLightboxContent();
    }

    function zoomLightbox(delta) {
      mangaState.lightboxZoom = Math.max(40, Math.min(250, mangaState.lightboxZoom + delta));
      const zoomVal = document.getElementById('manga-lightbox-zoom-val');
      if (zoomVal) zoomVal.innerText = mangaState.lightboxZoom + '%';
      const content = document.getElementById('manga-lightbox-content');
      if (content) content.style.transform = `scale(${mangaState.lightboxZoom / 100})`;
    }

    function resetLightboxZoom() {
      mangaState.lightboxZoom = 100;
      const zoomVal = document.getElementById('manga-lightbox-zoom-val');
      if (zoomVal) zoomVal.innerText = '100%';
      const content = document.getElementById('manga-lightbox-content');
      if (content) content.style.transform = 'scale(1)';
    }

    function renderLightboxContent() {
      const p = mangaState.pages.find(item => item.page_index === mangaState.lightboxPageIndex) || mangaState.pages[0];
      if (!p) return;

      const titleEl = document.getElementById('manga-lightbox-title');
      if (titleEl) titleEl.innerHTML = `<i data-lucide="image" class="w-4 h-4 text-indigo-400"></i> Trang ${p.page_index} / ${mangaState.pages.length} - ${p.filename}`;

      const infoEl = document.getElementById('manga-lightbox-info');
      if (infoEl) infoEl.innerText = p.bubbles ? `${p.bubbles.length} bóng thoại được dịch` : '';

      const container = document.getElementById('manga-lightbox-content');
      if (!container) return;

      const isTrans = p.status === 'translated' && p.translated_url;
      const mode = mangaState.lightboxMode;

      if (mode === 'split') {
        container.innerHTML = `
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-[1700px] w-full">
            <div class="flex flex-col items-center bg-slate-900/90 p-3 rounded-[10px] border border-slate-800 shadow-lg border border-slate-800">
              <span class="text-xs font-semibold text-slate-300 mb-2 flex items-center gap-1.5">Bản gốc</span>
              <img src="${p.original_url}" class="max-h-[80vh] w-auto object-contain rounded-lg">
            </div>
            <div class="flex flex-col items-center bg-slate-900/90 p-3 rounded-[10px] border border-slate-800 shadow-lg border border-slate-800">
              <span class="text-xs font-semibold text-emerald-400 mb-2 flex items-center gap-1.5">Bản dịch AI Inpainting</span>
              <img src="${isTrans ? p.translated_url : p.original_url}" class="max-h-[80vh] w-auto object-contain rounded-lg">
            </div>
          </div>
        `;
      } else {
        const src = (mode === 'translated' && isTrans) ? p.translated_url : p.original_url;
        container.innerHTML = `
          <div class="relative max-w-5xl flex justify-center">
            <img src="${src}" class="max-h-[82vh] w-auto object-contain rounded-[8px] shadow-md border border-slate-800">
          </div>
        `;
      }
      if (window.lucide && lucide.createIcons) lucide.createIcons();
    }

    function toggleMangaBilingualTooltip() {
      mangaState.bilingualActive = !mangaState.bilingualActive;
      const btn = document.getElementById('manga-view-btn-bilingual');
      if (btn) {
        if (mangaState.bilingualActive) {
          btn.className = "px-2.5 py-1 rounded-md text-xs font-semibold transition bg-cyan-600 text-white shadow";
        } else {
          btn.className = "px-2.5 py-1 rounded-md text-xs font-semibold transition text-slate-400 hover:text-white";
        }
      }

      mangaState.pages.forEach(p => {
        const overlay = document.getElementById('manga-overlay-' + p.page_index);
        if (overlay) {
          if (mangaState.bilingualActive) {
            overlay.classList.remove('hidden');
          } else {
            overlay.classList.add('hidden');
          }
        }
      });
    }

    function zoomManga(delta) {
      mangaState.zoomLevel = Math.max(50, Math.min(160, mangaState.zoomLevel + delta));
      const zoomText = document.getElementById('manga-zoom-text');
      if (zoomText) zoomText.innerText = mangaState.zoomLevel + "%";

      const list = document.getElementById('manga-pages-list');
      if (list) {
        const base = mangaState.viewMode === 'split' ? 1400 : 672;
        const targetWidth = Math.round(base * (mangaState.zoomLevel / 100));
        list.style.maxWidth = targetWidth + 'px';
      }
    }

    async function translateSingleMangaPage(pageIndex) {
      if (!mangaState.sessionId) return;
      const btn = document.getElementById('btn-trans-page-' + pageIndex);
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i data-lucide="loader" class="w-3 h-3 animate-spin"></i><span>Đang dịch...</span>';
        if (window.lucide && lucide.createIcons) lucide.createIcons();
      }

      const targetLang = document.getElementById('manga-target-lang') ? document.getElementById('manga-target-lang').value : 'vi';

      try {
        const res = await fetch('/api/manga/translate-page', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: mangaState.sessionId,
            page_index: pageIndex,
            target_lang: targetLang
          })
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || "Không thể dịch trang");
        }

        // Update state
        const idx = mangaState.pages.findIndex(p => p.page_index === pageIndex);
        if (idx !== -1) {
          mangaState.pages[idx].status = 'translated';
          mangaState.pages[idx].translated_url = data.translated_url;
          mangaState.pages[idx].bubbles = data.bubbles || [];
        }

        // Update image
        const img = document.getElementById('manga-img-' + pageIndex);
        if (img && mangaState.viewMode === 'translated') {
          img.src = data.translated_url;
        }

        // Update overlay
        const overlay = document.getElementById('manga-overlay-' + pageIndex);
        if (overlay) {
          overlay.innerHTML = renderBubbleOverlays(mangaState.pages[idx]);
        }

        // Refresh card header
        renderMangaWorkspace();
      } catch (err) {
        alert("Lỗi khi dịch trang #" + pageIndex + ": " + err.message);
      } finally {
        if (btn) btn.disabled = false;
        fetchPoolStatus();
      }
    }

    async function translateAllManga() {
      if (!mangaState.sessionId || !mangaState.pages || mangaState.pages.length === 0) {
        alert("Vui lòng tải lên hoặc nạp chapter truyện trước!");
        return;
      }

      if (mangaState.isTranslatingAll) return;
      mangaState.isTranslatingAll = true;

      const btn = document.getElementById('btn-manga-translate-all');
      const progressContainer = document.getElementById('manga-progress-container');
      const progressBar = document.getElementById('manga-progress-bar');
      const progressText = document.getElementById('manga-progress-text');
      const progressPercent = document.getElementById('manga-progress-percent');
      const targetLang = document.getElementById('manga-target-lang') ? document.getElementById('manga-target-lang').value : 'vi';

      if (btn) btn.disabled = true;
      if (progressContainer) progressContainer.classList.remove('hidden');
      if (progressBar) progressBar.style.width = '10%';
      if (progressPercent) progressPercent.innerText = '10%';
      if (progressText) progressText.innerText = "Đang gửi yêu cầu dịch song song qua 7 Keys Smart Pool...";

      // Fake progress interval for smooth UX while waiting
      let fakeProgress = 10;
      const progressTimer = setInterval(() => {
        if (fakeProgress < 90) {
          fakeProgress += 5;
          if (progressBar) progressBar.style.width = fakeProgress + '%';
          if (progressPercent) progressPercent.innerText = fakeProgress + '%';
          if (progressText) {
            progressText.innerText = "Đang dịch AI song song qua Smart Key Pool (" + fakeProgress + "%)...";
          }
        }
      }, 1000);

      try {
        const res = await fetch('/api/manga/translate-all', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: mangaState.sessionId,
            target_lang: targetLang,
            concurrency: 7
          })
        });
        const data = await res.json();
        clearInterval(progressTimer);

        if (!res.ok) {
          throw new Error(data.detail || "Không thể dịch toàn bộ chapter");
        }

        if (progressBar) progressBar.style.width = '100%';
        if (progressPercent) progressPercent.innerText = '100%';
        if (progressText) progressText.innerText = "Hoàn tất dịch toàn bộ " + data.total_pages + " trang!";

        mangaState.pages = data.pages || [];
        setMangaViewMode('translated');
        renderMangaWorkspace();

        setTimeout(() => {
          if (progressContainer) progressContainer.classList.add('hidden');
        }, 3000);

      } catch (err) {
        clearInterval(progressTimer);
        alert("Lỗi khi dịch toàn bộ chapter: " + err.message);
        if (progressContainer) progressContainer.classList.add('hidden');
      } finally {
        mangaState.isTranslatingAll = false;
        if (btn) btn.disabled = false;
        fetchPoolStatus();
      }
    }

    async function exportMangaZip() {
      if (!mangaState.sessionId) {
        alert("Chưa có chapter nào được nạp!");
        return;
      }

      const btn = document.getElementById('btn-manga-export-zip');
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i data-lucide="loader" class="w-3.5 h-3.5 animate-spin"></i><span>Đang nén ZIP...</span>';
        if (window.lucide && lucide.createIcons) lucide.createIcons();
      }

      try {
        const res = await fetch('/api/manga/export-zip', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: mangaState.sessionId })
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || "Không thể tạo tệp ZIP");
        }

        // Trigger download
        const a = document.createElement('a');
        a.href = data.download_url;
        a.download = "manga_chapter_" + mangaState.sessionId + ".zip";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      } catch (err) {
        alert("Lỗi xuất ZIP: " + err.message);
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = '<i data-lucide="file-archive" class="w-3.5 h-3.5"></i><span data-i18n="manga_btn_export_zip">Tải Tệp ZIP Chapter</span>';
          if (window.lucide && lucide.createIcons) lucide.createIcons();
        }
      }
    }

    // Register Global Paste Listener (Ctrl+V from anywhere)
    window.addEventListener('paste', handleGlobalPaste);

    // Register Escape key to close Lightbox modal
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        const modal = document.getElementById('manga-lightbox-modal');
        if (modal && !modal.classList.contains('hidden')) {
          closeMangaLightbox();
        }
      }
    });


    // Expose functions to window for HTML inline event handlers
    window.updateChapterNavUI = typeof updateChapterNavUI !== 'undefined' ? updateChapterNavUI : undefined;
    window.scanMangaChapters = typeof scanMangaChapters !== 'undefined' ? scanMangaChapters : undefined;
    window.changeChapterOffset = typeof changeChapterOffset !== 'undefined' ? changeChapterOffset : undefined;
    window.onChapterDropdownChange = typeof onChapterDropdownChange !== 'undefined' ? onChapterDropdownChange : undefined;
    window.loadChapterByUrl = typeof loadChapterByUrl !== 'undefined' ? loadChapterByUrl : undefined;
    window.pasteMangaUrl = typeof pasteMangaUrl !== 'undefined' ? pasteMangaUrl : undefined;
    window.showPasteToast = typeof showPasteToast !== 'undefined' ? showPasteToast : undefined;
    window.pasteAndTranslateImage = typeof pasteAndTranslateImage !== 'undefined' ? pasteAndTranslateImage : undefined;
    window.handleGlobalPaste = typeof handleGlobalPaste !== 'undefined' ? handleGlobalPaste : undefined;
    window.pasteImageFromClipboardButton = typeof pasteImageFromClipboardButton !== 'undefined' ? pasteImageFromClipboardButton : undefined;
    window.handleMangaDragOver = typeof handleMangaDragOver !== 'undefined' ? handleMangaDragOver : undefined;
    window.handleMangaDragLeave = typeof handleMangaDragLeave !== 'undefined' ? handleMangaDragLeave : undefined;
    window.handleMangaDrop = typeof handleMangaDrop !== 'undefined' ? handleMangaDrop : undefined;
    window.handleMangaFileInput = typeof handleMangaFileInput !== 'undefined' ? handleMangaFileInput : undefined;
    window.uploadMangaFiles = typeof uploadMangaFiles !== 'undefined' ? uploadMangaFiles : undefined;
    window.loadMangaFromUrl = typeof loadMangaFromUrl !== 'undefined' ? loadMangaFromUrl : undefined;
    window.renderMangaWorkspace = typeof renderMangaWorkspace !== 'undefined' ? renderMangaWorkspace : undefined;
    window.renderBubbleOverlays = typeof renderBubbleOverlays !== 'undefined' ? renderBubbleOverlays : undefined;
    window.setMangaViewMode = typeof setMangaViewMode !== 'undefined' ? setMangaViewMode : undefined;
    window.holdCompareManga = typeof holdCompareManga !== 'undefined' ? holdCompareManga : undefined;
    window.zoomMangaReset = typeof zoomMangaReset !== 'undefined' ? zoomMangaReset : undefined;
    window.openMangaLightbox = typeof openMangaLightbox !== 'undefined' ? openMangaLightbox : undefined;
    window.closeMangaLightbox = typeof closeMangaLightbox !== 'undefined' ? closeMangaLightbox : undefined;
    window.setLightboxMode = typeof setLightboxMode !== 'undefined' ? setLightboxMode : undefined;
    window.zoomLightbox = typeof zoomLightbox !== 'undefined' ? zoomLightbox : undefined;
    window.resetLightboxZoom = typeof resetLightboxZoom !== 'undefined' ? resetLightboxZoom : undefined;
    window.renderLightboxContent = typeof renderLightboxContent !== 'undefined' ? renderLightboxContent : undefined;
    window.toggleMangaBilingualTooltip = typeof toggleMangaBilingualTooltip !== 'undefined' ? toggleMangaBilingualTooltip : undefined;
    window.zoomManga = typeof zoomManga !== 'undefined' ? zoomManga : undefined;
    window.translateSingleMangaPage = typeof translateSingleMangaPage !== 'undefined' ? translateSingleMangaPage : undefined;
    window.translateAllManga = typeof translateAllManga !== 'undefined' ? translateAllManga : undefined;
    window.exportMangaZip = typeof exportMangaZip !== 'undefined' ? exportMangaZip : undefined;
  } catch (err) {
    console.error('[GeminiTrans Error Boundary - Tab Manga]', err);
    if (window.showToast) {
      window.showToast('Lỗi khởi tạo module Tab Manga: ' + err.message, 'error');
    }
  }
})(window, document);
