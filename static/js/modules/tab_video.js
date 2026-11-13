// ============================================================================
// GEMINITRANS MODULE: Tab Video
// Error Boundary: Isolated execution - does not affect other tabs
// ============================================================================
(function(window, document) {
  'use strict';
  try {
    // ==========================================
    // GLOBAL STATE & SETUP
    // ==========================================
    let currentTab = 'video';
    let currentVideoId = null;
    let currentVideoSubtitles = [];
    let currentFileSignature = null;
    let currentLoadedUrl = null;
    let currentTrackBlobUrl = null;
    let isLoadingVideo = false;
    let autoSubtitleJob = null;
    let autoSubtitleJobVideoId = null;
    let poolData = null;
    let audioBlob = null;
    let mediaRecorder = null;
    let recordInterval = null;
    let recordSeconds = 0;
    let youtubePlayer = null;
    let youtubeSyncTimer = null;
    let youtubePlayerApiPromise = null;
    let currentYoutubeVideoId = null;
    let currentYoutubeUrl = null;
    let youtubeCaptionRequestId = 0;
    let tabAudioStream = null;
    let tabAudioRecorder = null;
    let tabAudioCaptureActive = false;
    let tabAudioCaptureGeneration = 0;
    let pendingTabAudioRequests = 0;
    let tabAudioCaptureStartedAt = 0;
    let tabAudioChunkQueue = [];
    let activeTabAudioWorkers = 0;

    // Client burner state
    let isClientBurning = false;
    let burnMediaRecorder = null;
    let burnChunks = [];

    const uploadedVideo = document.getElementById('uploaded-video-player');
    const subtitleOverlay = document.getElementById('video-subtitle');

    function setVideoActionsEnabled(enabled) {
      ['btn-auto-sub', 'btn-burn-video'].forEach(id => {
        const button = document.getElementById(id);
        if (!button) return;
        button.disabled = !enabled;
        button.classList.toggle('opacity-50', !enabled);
        button.classList.toggle('cursor-not-allowed', !enabled);
        button.title = enabled ? '' : t('youtube_download_limited');
      });
    }

    function setSubtitleOnlyMode(enabled) {
      ['btn-client-burn', 'btn-server-burn', 'btn-clean-server'].forEach(id => {
        document.getElementById(id)?.classList.toggle('hidden', enabled);
      });
      const label = document.getElementById('export-ready-label');
      if (label) {
        label.textContent = t(enabled ? 'export_subtitles_only' : 'export_ready_title');
      }
    }

    function stopYouTubePlayer() {
      if (youtubeSyncTimer) {
        clearInterval(youtubeSyncTimer);
        youtubeSyncTimer = null;
      }
      if (youtubePlayer && typeof youtubePlayer.destroy === 'function') {
        youtubePlayer.destroy();
      }
      youtubePlayer = null;
      currentYoutubeVideoId = null;
      currentYoutubeUrl = null;
      youtubeCaptionRequestId++;
    }

    function loadYouTubeIframeApi() {
      if (window.YT && window.YT.Player) return Promise.resolve(window.YT);
      if (youtubePlayerApiPromise) return youtubePlayerApiPromise;

      youtubePlayerApiPromise = new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          youtubePlayerApiPromise = null;
          reject(new Error('YouTube IFrame API timed out'));
        }, 15000);
        const previousReady = window.onYouTubeIframeAPIReady;
        window.onYouTubeIframeAPIReady = () => {
          if (typeof previousReady === 'function') previousReady();
          clearTimeout(timeout);
          if (window.YT && window.YT.Player) {
            resolve(window.YT);
          } else {
            youtubePlayerApiPromise = null;
            reject(new Error('YouTube IFrame API did not initialize'));
          }
        };

        let script = document.querySelector('script[src="https://www.youtube.com/iframe_api"]');
        if (!script) {
          script = document.createElement('script');
          script.src = 'https://www.youtube.com/iframe_api';
          script.async = true;
          script.onerror = () => {
            clearTimeout(timeout);
            youtubePlayerApiPromise = null;
            reject(new Error('Could not load YouTube IFrame API'));
          };
          document.head.appendChild(script);
        }
      });
      return youtubePlayerApiPromise;
    }

    
    function highlightAndScrollSubtitle(active) {
      if (!active) {
        document.querySelectorAll('.sub-item-card.active-cue').forEach(el => el.classList.remove('active-cue', 'border-amber-400', 'bg-slate-800'));
        return;
      }
      const activeCard = document.getElementById(`sub-card-${active.id}`);
      if (!activeCard) return;

      if (!activeCard.classList.contains('active-cue')) {
        document.querySelectorAll('.sub-item-card.active-cue').forEach(el => el.classList.remove('active-cue', 'border-amber-400', 'bg-slate-800'));
        activeCard.classList.add('active-cue', 'border-amber-400', 'bg-slate-800');

        const timeline = document.getElementById('sub-timeline-list');
        if (timeline) {
          const timelineRect = timeline.getBoundingClientRect();
          const cardRect = activeCard.getBoundingClientRect();
          if (cardRect.top < timelineRect.top || cardRect.bottom > timelineRect.bottom) {
            activeCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          }
        }
      }
    }

    function syncYouTubeSubtitle() {
      if (!youtubePlayer || typeof youtubePlayer.getCurrentTime !== 'function') return;
      const current = youtubePlayer.getCurrentTime();
      if (!Number.isFinite(current)) return;
      const duration = typeof youtubePlayer.getDuration === 'function'
        ? youtubePlayer.getDuration() || 0
        : 0;
      const formatClock = seconds => {
        const safeSeconds = Math.max(0, Math.floor(seconds || 0));
        return `${String(Math.floor(safeSeconds / 60)).padStart(2, '0')}:${String(safeSeconds % 60).padStart(2, '0')}`;
      };
      document.getElementById('video-time-display').innerText =
        `${formatClock(current)} / ${formatClock(duration)}`;

      const active = currentVideoSubtitles.find(cue =>
        current >= cue.start && current <= cue.end && (cue.translated || cue.original)
      );
      if (active) {
        renderOverlaySubtitle(active);
        subtitleOverlay.classList.remove('hidden');
        highlightAndScrollSubtitle(active);
      } else {
        subtitleOverlay.classList.add('hidden');
        highlightAndScrollSubtitle(null);
      }
    }

    async function initializeYouTubePlayer(videoId) {
      try {
        const YT = await loadYouTubeIframeApi();
        if (currentYoutubeVideoId !== videoId) return;
        const target = document.createElement('div');
        target.id = 'youtube-player-api-target';
        document.getElementById('yt-player-box').replaceChildren(target);
        youtubePlayer = new YT.Player(target, {
          width: '100%',
          height: '100%',
          videoId,
          playerVars: { playsinline: 1, rel: 0 },
          events: {
            onReady: () => {
              if (currentYoutubeVideoId === videoId) {
                youtubeSyncTimer = setInterval(syncYouTubeSubtitle, 200);
              }
            },
            onError: event => {
              console.warn('YouTube embedded player returned an error:', event.data);
            }
          }
        });
      } catch (error) {
        if (currentYoutubeVideoId !== videoId) return;
        const frame = document.createElement('iframe');
        frame.src = `https://www.youtube.com/embed/${encodeURIComponent(videoId)}`;
        frame.title = t('youtube_embed_title');
        frame.className = 'w-full h-full border-0';
        frame.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
        frame.referrerPolicy = 'strict-origin-when-cross-origin';
        frame.allowFullscreen = true;
        document.getElementById('yt-player-box').replaceChildren(frame);
        console.warn('YouTube IFrame API unavailable; using the standard embed:', error);
      }
    }

    async function fetchAndTranslateYouTubeCaptions(videoId, url) {
      const requestId = ++youtubeCaptionRequestId;
      const list = document.getElementById('sub-timeline-list');
      list.textContent = t('youtube_captions_loading');
      try {
        const response = await fetch('/api/video/youtube-captions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            url,
            target_lang: document.getElementById('video-target-lang')?.value || 'vi'
          })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || `Server HTTP ${response.status}`);
        if (requestId !== youtubeCaptionRequestId || currentYoutubeVideoId !== videoId) return;

        currentVideoSubtitles = data.subtitles || [];
        renderSubtitleTimeline(currentVideoSubtitles);
        document.getElementById('export-download-box')?.classList.remove('hidden');
        setSubtitleOnlyMode(true);
        updateYouTubeSubtitle();
        list.insertAdjacentHTML(
          'afterbegin',
          `<p class="p-3 text-xs text-emerald-300">${escapeHtml(t('youtube_captions_ready', { count: currentVideoSubtitles.length }))}</p>`
        );
      } catch (error) {
        if (requestId !== youtubeCaptionRequestId || currentYoutubeVideoId !== videoId) return;
        list.textContent = t('youtube_captions_unavailable');
        console.info('Public YouTube captions unavailable:', error.message);
      }
    }

    function updateYouTubeSubtitle() {
      if (youtubePlayer && typeof youtubePlayer.getCurrentTime === 'function') {
        syncYouTubeSubtitle();
      }
    }

    function getCurrentCaptureTime() {
      if (youtubePlayer && typeof youtubePlayer.getCurrentTime === 'function') {
        const current = youtubePlayer.getCurrentTime();
        if (Number.isFinite(current)) return current;
      }
      if (uploadedVideo && !uploadedVideo.paused && Number.isFinite(uploadedVideo.currentTime)) {
        return uploadedVideo.currentTime;
      }
      return Math.max(0, (performance.now() - tabAudioCaptureStartedAt) / 1000);
    }

    function recordTabAudioSegment(stream, generation) {
      return new Promise((resolve, reject) => {
        const preferredTypes = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/mp4'];
        const mimeType = preferredTypes.find(type => MediaRecorder.isTypeSupported(type));
        let recorder;
        try {
          recorder = mimeType
            ? new MediaRecorder(stream, { mimeType })
            : new MediaRecorder(stream);
        } catch (error) {
          reject(error);
          return;
        }
        tabAudioRecorder = recorder;
        const chunks = [];
        recorder.ondataavailable = event => {
          if (event.data && event.data.size) chunks.push(event.data);
        };
        recorder.onerror = event => reject(event.error || new Error('Audio recorder failed'));
        recorder.onstop = () => {
          if (tabAudioRecorder === recorder) tabAudioRecorder = null;
          resolve(new Blob(chunks, { type: recorder.mimeType || mimeType || 'audio/webm' }));
        };
        recorder.start();
        setTimeout(() => {
          if (
            tabAudioCaptureActive &&
            generation === tabAudioCaptureGeneration &&
            recorder.state === 'recording'
          ) {
            recorder.stop();
          }
        }, 6000);
      });
    }

    async function sendTabAudioChunk(blob, startTime, endTime, generation) {
      if (blob.size < 1000) return;
      pendingTabAudioRequests++;
      try {
        const form = new FormData();
        const extension = blob.type.includes('ogg') ? 'ogg' : blob.type.includes('mp4') ? 'm4a' : 'webm';
        form.append('file', blob, `tab-audio.${extension}`);
        form.append('target_lang', document.getElementById('video-target-lang')?.value || 'vi');
        const response = await fetch('/api/video/transcribe-capture-chunk', {
          method: 'POST',
          body: form
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || `Server HTTP ${response.status}`);
        if (generation !== tabAudioCaptureGeneration || !data.original && !data.translated) return;

        const cueStart = Math.max(0, startTime);
        const cueEnd = Math.max(cueStart + 0.3, endTime);
        currentVideoSubtitles.push({
          id: currentVideoSubtitles.length + 1,
          start: cueStart,
          end: cueEnd,
          start_str: formatVttTime(cueStart),
          end_str: formatVttTime(cueEnd),
          original: data.original,
          translated: data.translated,
          translations: {
            [document.getElementById('video-target-lang')?.value || 'vi']: data.translated
          }
        });
        currentVideoSubtitles.sort((left, right) => left.start - right.start);
        currentVideoSubtitles.forEach((cue, index) => { cue.id = index + 1; });
        renderSubtitleTimeline(currentVideoSubtitles);
        document.getElementById('export-download-box')?.classList.remove('hidden');
        setSubtitleOnlyMode(true);
        updateYouTubeSubtitle();
      } catch (error) {
        if (generation === tabAudioCaptureGeneration) {
          document.getElementById('tab-audio-capture-status').textContent =
            t('tab_audio_capture_error', { error: error.message });
        }
      } finally {
        pendingTabAudioRequests = Math.max(0, pendingTabAudioRequests - 1);
      }
    }

    async function enqueueTabAudioChunk(blob, startTime, endTime, generation) {
      if (blob.size < 1000) return;
      if (tabAudioChunkQueue.length >= 5) {
        const status = document.getElementById('tab-audio-capture-status');
        stopTabAudioCapture({ silent: true });
        status.textContent = t('tab_audio_capture_queue_full');
        return;
      }

      tabAudioChunkQueue.push({ blob, startTime, endTime, generation });
      while (activeTabAudioWorkers < 2 && tabAudioChunkQueue.length) {
        activeTabAudioWorkers++;
        void runTabAudioQueueWorker();
      }
    }

    async function runTabAudioQueueWorker() {
      try {
        while (tabAudioChunkQueue.length) {
          const chunk = tabAudioChunkQueue.shift();
          if (chunk.generation !== tabAudioCaptureGeneration) continue;
          await sendTabAudioChunk(
            chunk.blob,
            chunk.startTime,
            chunk.endTime,
            chunk.generation
          );
        }
      } finally {
        activeTabAudioWorkers--;
        if (tabAudioChunkQueue.length && activeTabAudioWorkers < 2) {
          activeTabAudioWorkers++;
          void runTabAudioQueueWorker();
        }
      }
    }

    async function runTabAudioCapture(stream, generation) {
      while (tabAudioCaptureActive && generation === tabAudioCaptureGeneration) {
        const startTime = getCurrentCaptureTime();
        let blob;
        try {
          blob = await recordTabAudioSegment(stream, generation);
        } catch (error) {
          if (generation === tabAudioCaptureGeneration) {
            document.getElementById('tab-audio-capture-status').textContent =
              t('tab_audio_capture_error', { error: error.message });
            stopTabAudioCapture();
          }
          return;
        }
        const endTime = getCurrentCaptureTime();
        if (generation !== tabAudioCaptureGeneration) return;
        if (blob.size) {
          void enqueueTabAudioChunk(blob, startTime, endTime, generation);
        }
      }
    }

    async function startTabAudioCapture() {
      if (tabAudioCaptureActive) return;
      const status = document.getElementById('tab-audio-capture-status');
      if (!navigator.mediaDevices?.getDisplayMedia || typeof MediaRecorder === 'undefined') {
        status.textContent = t('tab_audio_capture_unsupported');
        return;
      }

      status.textContent = t('tab_audio_capture_select');
      try {
        const sharedStream = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: true
        });
        const audioTracks = sharedStream.getAudioTracks();
        sharedStream.getVideoTracks().forEach(track => track.stop());
        if (!audioTracks.length) {
          sharedStream.getTracks().forEach(track => track.stop());
          status.textContent = t('tab_audio_capture_no_audio');
          return;
        }

        tabAudioStream = new MediaStream(audioTracks);
        tabAudioCaptureActive = true;
        const generation = ++tabAudioCaptureGeneration;
        tabAudioCaptureStartedAt = performance.now();
        currentVideoSubtitles = [];
        tabAudioChunkQueue = [];
        renderSubtitleTimeline(currentVideoSubtitles);
        document.getElementById('export-download-box')?.classList.add('hidden');
        setSubtitleOnlyMode(true);
        document.getElementById('btn-capture-tab-audio').disabled = true;
        document.getElementById('btn-stop-tab-audio').disabled = false;
        document.getElementById('btn-stop-tab-audio').classList.remove('opacity-50', 'cursor-not-allowed');
        status.textContent = t('tab_audio_capture_active');
        audioTracks.forEach(track => {
          track.addEventListener('ended', () => stopTabAudioCapture(), { once: true });
        });
        void runTabAudioCapture(tabAudioStream, generation);
      } catch (error) {
        status.textContent = t('tab_audio_capture_error', { error: error.message });
      }
    }

    function stopTabAudioCapture(options = {}) {
      tabAudioCaptureActive = false;
      tabAudioCaptureGeneration++;
      tabAudioChunkQueue = [];
      if (tabAudioRecorder && tabAudioRecorder.state !== 'inactive') {
        tabAudioRecorder.stop();
      }
      if (tabAudioStream) {
        tabAudioStream.getTracks().forEach(track => track.stop());
        tabAudioStream = null;
      }
      const startButton = document.getElementById('btn-capture-tab-audio');
      const stopButton = document.getElementById('btn-stop-tab-audio');
      if (startButton) startButton.disabled = false;
      if (stopButton) {
        stopButton.disabled = true;
        stopButton.classList.add('opacity-50', 'cursor-not-allowed');
      }
      if (!options.silent) {
        document.getElementById('tab-audio-capture-status').textContent =
          t('tab_audio_capture_stopped');
      }
    }

    // Restore the user's subtitle choices before any automatically-started job reads them.
    const savedVideoTargetLang = localStorage.getItem('geminitrans_video_target_lang');
    const videoTargetLangSelect = document.getElementById('video-target-lang');
    if (videoTargetLangSelect && savedVideoTargetLang &&
        Array.from(videoTargetLangSelect.options).some(option => option.value === savedVideoTargetLang)) {
      videoTargetLangSelect.value = savedVideoTargetLang;
    }
    const multiLangSubtitleToggle = document.getElementById('multi-lang-sub-toggle');
    if (multiLangSubtitleToggle) {
      multiLangSubtitleToggle.checked = localStorage.getItem('geminitrans_multi_lang_subtitles') === '1';
      multiLangSubtitleToggle.addEventListener('change', () => {
        localStorage.setItem('geminitrans_multi_lang_subtitles', multiLangSubtitleToggle.checked ? '1' : '0');
      });
    }

    // Dừng và dọn dẹp sạch sẽ toàn bộ player (YouTube iframe, HTML5 video, overlays)
    function stopAndCleanAllPlayers() {
      stopYouTubePlayer();
      stopTabAudioCapture({ silent: true });
      setVideoActionsEnabled(true);
      setSubtitleOnlyMode(false);
      // Dừng và xóa triệt để nội dung của yt-player-box
      const box = document.getElementById('yt-player-box');
      if (box) {
        box.innerHTML = '';
        box.classList.add('hidden');
      }
      // Dừng video player HTML5
      if (uploadedVideo) {
        uploadedVideo.pause();
        uploadedVideo.removeAttribute('src');
        uploadedVideo.load();
        uploadedVideo.classList.add('hidden');
      }
      // Đưa placeholder hiển thị trở lại
      const placeholder = document.getElementById('player-placeholder');
      if (placeholder) {
        placeholder.classList.remove('hidden');
        placeholder.innerHTML = `
          <i data-lucide="film" class="w-16 h-16 mx-auto mb-3 opacity-30"></i>
          <p class="text-sm" data-i18n="player_placeholder">${t('player_placeholder')}</p>
        `;
        if (window.lucide && lucide.createIcons) {
          lucide.createIcons();
        }
      }
      // Ẩn subtitle overlay
      if (subtitleOverlay) {
        subtitleOverlay.innerText = '';
        subtitleOverlay.classList.add('hidden');
      }
    }

    // ==========================================
    function renderOverlaySubtitle(sub) {
      const isDual = document.getElementById('dual-sub-toggle')?.checked;
      const original = (sub.original || '').trim();
      const translated = (sub.translated || '').trim();

      if (isDual && original && translated && original !== translated) {
        subtitleOverlay.innerHTML = `
          <div class="sub-original">${escapeHtml(original)}</div>
          <div class="sub-translated">${escapeHtml(translated)}</div>
        `;
      } else {
        subtitleOverlay.innerHTML = `<div class="sub-translated">${escapeHtml(translated || original)}</div>`;
      }
    }

    function toggleDualSubtitles(checked) {
      try {
        localStorage.setItem('geminitrans_dual_sub', checked ? '1' : '0');
      } catch (e) {}

      updateVideoTextTrack(currentVideoSubtitles);

      // Refresh live subtitle preview if playing
      if (uploadedVideo && !uploadedVideo.paused && currentVideoSubtitles.length) {
        const cur = uploadedVideo.currentTime;
        const active = currentVideoSubtitles.find(s => cur >= s.start && cur <= s.end);
        if (active) {
          renderOverlaySubtitle(active);
          subtitleOverlay.classList.remove('hidden');
        }
      } else {
        updateSubtitleStyle(true);
      }
    }

    // ==========================================
    // 3. WEBVTT TEXT TRACK (IOS SAFARI FULLSCREEN)
    // ==========================================
    function setNativeTrackMode(mode) {
      try {
        if (uploadedVideo && uploadedVideo.textTracks && uploadedVideo.textTracks.length > 0) {
          for (let i = 0; i < uploadedVideo.textTracks.length; i++) {
            uploadedVideo.textTracks[i].mode = mode;
          }
        }
      } catch (e) {
        console.warn("Could not set textTrack mode:", e);
      }
    }

    function updateVideoTextTrack(subs) {
      if (!uploadedVideo) return;
      const isDual = document.getElementById('dual-sub-toggle')?.checked;

      // Revoke previous blob url to avoid memory leaks
      if (currentTrackBlobUrl) {
        try { URL.revokeObjectURL(currentTrackBlobUrl); } catch (e) {}
        currentTrackBlobUrl = null;
      }

      let track = document.getElementById('uploaded-video-track');
      if (!track) {
        track = document.createElement('track');
        track.id = 'uploaded-video-track';
        track.kind = 'subtitles';
        track.label = isDual ? 'Bilingual Subtitles' : 'Tiếng Việt';
        track.srclang = 'vi';
        uploadedVideo.appendChild(track);
      } else {
        track.label = isDual ? 'Bilingual Subtitles' : 'Tiếng Việt';
      }

      if (!subs || !subs.length) {
        track.removeAttribute('src');
        return;
      }

      let vtt = "WEBVTT\n\n";
      subs.forEach((s, idx) => {
        const sTime = formatVttTime(s.start);
        const eTime = formatVttTime(s.end);
        let text = '';
        const orig = (s.original || '').trim();
        const trans = (s.translated || '').trim();

        if (isDual && orig && trans && orig !== trans) {
          text = `${orig}\n${trans}`;
        } else {
          text = trans || orig || '';
        }

        if (text) {
          vtt += `${idx + 1}\n${sTime} --> ${eTime}\n${text}\n\n`;
        }
      });

      const blob = new Blob([vtt], { type: 'text/vtt;charset=utf-8' });
      currentTrackBlobUrl = URL.createObjectURL(blob);
      track.src = currentTrackBlobUrl;

      // Giữ mode = 'hidden' trên chế độ xem thông thường để trình duyệt không tự vẽ phụ đề native đè lên phụ đề tùy chỉnh
      setNativeTrackMode('hidden');
    }

    // ==========================================
    // 2. LOCAL SUBTITLE CACHE (ZERO TOKEN)
    // ==========================================
    function getCacheKeys() {
      const keys = [];
      const curLang = document.getElementById('video-target-lang')?.value || 'vi';
      if (currentLoadedUrl) {
        keys.push(`geminitrans_cache_${curLang}_${currentLoadedUrl.trim()}`);
        keys.push(`geminitrans_cache_${currentLoadedUrl.trim()}`);
        keys.push(`geminitrans_cache_url_${encodeURIComponent(currentLoadedUrl.trim().toLowerCase())}`);
      }
      if (currentFileSignature) {
        keys.push(`geminitrans_cache_${curLang}_${currentFileSignature}`);
        keys.push(`geminitrans_cache_${currentFileSignature}`);
      }
      if (currentVideoId) {
        keys.push(`geminitrans_cache_${curLang}_${currentVideoId}`);
        keys.push(`geminitrans_cache_${currentVideoId}`);
      }
      return keys;
    }

    function checkAndLoadSubtitleCache() {
      const keys = getCacheKeys();
      for (const k of keys) {
        try {
          const raw = localStorage.getItem(k);
          if (raw) {
            const parsed = JSON.parse(raw);
            if (Array.isArray(parsed) && parsed.length > 0) {
              currentVideoSubtitles = parsed;
              renderSubtitleTimeline(currentVideoSubtitles);
              updateVideoTextTrack(currentVideoSubtitles);
              document.getElementById('export-download-box')?.classList.remove('hidden');
              showCacheNoticeBadge();
              return true;
            }
          }
        } catch (e) {
          console.warn("Error reading cache for", k, e);
        }
      }
      hideCacheNoticeBadge();
      return false;
    }

    function saveSubtitleCache(subs) {
      if (!Array.isArray(subs) || !subs.length) return;
      const raw = JSON.stringify(subs);
      const keys = getCacheKeys();
      for (const k of keys) {
        try {
          localStorage.setItem(k, raw);
        } catch (e) {
          console.warn("localStorage quota or error", e);
        }
      }
    }

    function clearSubtitleCacheForCurrentVideo() {
      const keys = getCacheKeys();
      for (const k of keys) {
        try {
          localStorage.removeItem(k);
        } catch (e) {}
      }
    }

    function showCacheNoticeBadge() {
      const badge = document.getElementById('cache-notice-badge');
      if (badge) {
        badge.classList.remove('hidden');
        badge.classList.add('flex');
        if (window.lucide && lucide.createIcons) lucide.createIcons();
      }
    }

    function hideCacheNoticeBadge() {
      const badge = document.getElementById('cache-notice-badge');
      if (badge) {
        badge.classList.add('hidden');
        badge.classList.remove('flex');
      }
    }

    function resetSubtitleStateForVideoLoad() {
      currentVideoSubtitles = [];
      renderSubtitleTimeline([]);
      updateVideoTextTrack([]);
      hideCacheNoticeBadge();
      document.getElementById('export-download-box')?.classList.add('hidden');
    }

    function rescanBypassCache() {
      clearSubtitleCacheForCurrentVideo();
      hideCacheNoticeBadge();
      currentVideoSubtitles = [];
      renderSubtitleTimeline([]);
      updateVideoTextTrack([]);
      startAutoSubtitling(true);
    }

    // ==========================================
    // 4. MOBILE / TABLET 1-TOUCH FULLSCREEN
    // ==========================================
    function togglePlayerFullscreen() {
      const container = document.getElementById('player-container');
      const video = document.getElementById('uploaded-video-player');

      // iOS Safari specific fullscreen for <video>
      if (video && video.webkitSupportsFullscreen && !document.fullscreenElement && !document.webkitFullscreenElement) {
        if (typeof video.webkitEnterFullscreen === 'function') {
          setNativeTrackMode('showing');
          video.webkitEnterFullscreen();
          return;
        }
      }

      if (!document.fullscreenElement && !document.webkitFullscreenElement && !document.mozFullScreenElement && !document.msFullscreenElement) {
        if (container.requestFullscreen) {
          container.requestFullscreen();
        } else if (container.webkitRequestFullscreen) {
          container.webkitRequestFullscreen();
        } else if (container.mozRequestFullScreen) {
          container.mozRequestFullScreen();
        } else if (container.msRequestFullscreen) {
          container.msRequestFullscreen();
        } else if (video && video.webkitEnterFullscreen) {
          setNativeTrackMode('showing');
          video.webkitEnterFullscreen();
        }
      } else {
        if (document.exitFullscreen) {
          document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
          document.webkitExitFullscreen();
        } else if (document.mozCancelFullScreen) {
          document.mozCancelFullScreen();
        } else if (document.msExitFullscreen) {
          document.msExitFullscreen();
        }
      }
    }

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);

    function handleFullscreenChange() {
      const isFs = !!(document.fullscreenElement || document.webkitFullscreenElement);
      const icon = document.getElementById('fs-icon');
      if (icon) {
        icon.setAttribute('data-lucide', isFs ? 'minimize' : 'maximize');
        if (window.lucide && lucide.createIcons) lucide.createIcons();
      }
      if (!isFs) {
        setNativeTrackMode('hidden');
      }
    }

    if (uploadedVideo) {
      uploadedVideo.addEventListener('webkitbeginfullscreen', () => setNativeTrackMode('showing'));
      uploadedVideo.addEventListener('webkitendfullscreen', () => setNativeTrackMode('hidden'));
    }

    // ==========================================
    // SUBTITLE CUSTOMIZER & REALTIME PREVIEW
    // ==========================================
    function hexToRgba(hex, alpha) {
      hex = hex.replace('#', '');
      if (hex.length === 3) hex = hex.split('').map(c => c + c).join('');
      const r = parseInt(hex.substring(0, 2), 16) || 0;
      const g = parseInt(hex.substring(2, 4), 16) || 0;
      const b = parseInt(hex.substring(4, 6), 16) || 0;
      return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }

    function updateSubtitleStyle(triggerPreview = false) {
      const textColor = document.getElementById('sub-color').value;
      const bgColor = document.getElementById('sub-bg-color').value;
      const opacity = parseInt(document.getElementById('sub-opacity').value) / 100.0;
      const fontSize = parseInt(document.getElementById('sub-font-size').value);
      const marginV = parseInt(document.getElementById('sub-margin-v').value);
      const maskOld = document.getElementById('mask-old-sub').checked;

      // Update text indicators
      document.getElementById('opacity-val').innerText = `${Math.round(opacity * 100)}%`;
      document.getElementById('font-size-val').innerText = `${fontSize}px`;
      document.getElementById('margin-val').innerText = `${marginV}px`;
      document.getElementById('color-hex-text').innerText = textColor.toUpperCase();

      // Apply directly to overlay
      subtitleOverlay.style.color = textColor;
      subtitleOverlay.style.fontSize = `${fontSize}px`;
      subtitleOverlay.style.bottom = `${marginV}px`;

      if (maskOld) {
        subtitleOverlay.style.backgroundColor = hexToRgba(bgColor, opacity);
        subtitleOverlay.style.padding = '6px 24px';
        subtitleOverlay.style.borderRadius = '6px';
        subtitleOverlay.style.boxShadow = '0 4px 14px rgba(0,0,0,0.5)';
      } else {
        subtitleOverlay.style.backgroundColor = 'transparent';
        subtitleOverlay.style.padding = '0';
        subtitleOverlay.style.boxShadow = 'none';
        subtitleOverlay.style.textShadow = '0 2px 4px #000, 0 0 2px #000, 0 0 4px #000';
      }

      // Sample preview if no subtitles loaded yet
      if (triggerPreview && !currentVideoSubtitles.length) {
        const isDual = document.getElementById('dual-sub-toggle')?.checked;
        if (isDual) {
          subtitleOverlay.innerHTML = `
            <div class="sub-original">Original spoken line (75% silver)</div>
            <div class="sub-translated">${currentLang === 'vi' ? 'Bản dịch tiếng Việt (Mẫu)' : 'Translated subtitle preview'}</div>
          `;
        } else {
          subtitleOverlay.innerHTML = `<div class="sub-translated">${currentLang === 'vi' ? 'Phụ đề mẫu (Preview Style)' : 'Sample Subtitle (Preview Style)'}</div>`;
        }
        subtitleOverlay.classList.remove('hidden');
        clearTimeout(window._previewTimer);
        window._previewTimer = setTimeout(() => {
          if (!currentVideoSubtitles.length) {
            subtitleOverlay.classList.add('hidden');
            subtitleOverlay.innerHTML = "";
          }
        }, 2500);
      }
    }

    // Synchronize subtitle overlay with video playback time
    uploadedVideo.addEventListener('timeupdate', () => {
      const current = uploadedVideo.currentTime;
      const duration = uploadedVideo.duration || 0;

      // Update timer display
      const curM = String(Math.floor(current / 60)).padStart(2, '0');
      const curS = String(Math.floor(current % 60)).padStart(2, '0');
      const durM = String(Math.floor(duration / 60)).padStart(2, '0');
      const durS = String(Math.floor(duration % 60)).padStart(2, '0');
      document.getElementById('video-time-display').innerText = `${curM}:${curS} / ${durM}:${durS}`;

      if (!currentVideoSubtitles.length) {
        subtitleOverlay.classList.add('hidden');
        subtitleOverlay.innerHTML = '';
        return;
      }

      // Find active subtitle
      const active = currentVideoSubtitles.find(s => current >= s.start && current <= s.end);
      if (active && (active.translated || active.original)) {
        renderOverlaySubtitle(active);
        subtitleOverlay.classList.remove('hidden');
        highlightAndScrollSubtitle(active);
      } else {
        subtitleOverlay.classList.add('hidden');
        highlightAndScrollSubtitle(null);
      }
    });

    // Handle Local Video Upload
    async function handleVideoUpload(event) {
      const file = event.target.files[0];
      if (!file) return;

      // Dọn dẹp và dừng sạch sẽ toàn bộ player trước khi nạp video mới
      stopAndCleanAllPlayers();
      currentVideoId = null;
      resetSubtitleStateForVideoLoad();

      document.getElementById('upload-btn-label').innerText = t('video_opt1_uploading');
      const statusText = document.getElementById('upload-status-text');
      statusText.classList.remove('hidden');
      statusText.innerText = "...";

      const formData = new FormData();
      formData.append('file', file);

      try {
        const res = await fetch('/api/video/upload', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        
        currentVideoId = data.video_id;
        currentFileSignature = `${file.name}_${file.size}`;
        currentLoadedUrl = null;

        document.getElementById('current-video-badge').innerText = `${t('badge_video_prefix')}${data.filename}`;
        document.getElementById('upload-btn-label').innerText = t('video_opt1_btn_change');
        statusText.innerText = t('video_opt1_success');

        // Load into HTML5 Video Player
        const placeholder = document.getElementById('player-placeholder');
        if (placeholder) placeholder.classList.add('hidden');
        const box = document.getElementById('yt-player-box');
        if (box) {
          box.innerHTML = '';
          box.classList.add('hidden');
        }
        uploadedVideo.classList.remove('hidden');
        uploadedVideo.src = data.video_url;
        uploadedVideo.load();

        // Enable Action Buttons
        setVideoActionsEnabled(true);
        
        subtitleOverlay.innerHTML = '';
        subtitleOverlay.classList.add('hidden');
        updateSubtitleStyle();

        // Check and restore local cache in 0.05s without calling AI Studio
        await startAutoSubtitling();
      } catch (err) {
        alert("Upload error: " + err.message);
        document.getElementById('upload-btn-label').innerText = t('video_opt1_btn');
      }
    }

    // AI AUTO SUBTITLING
    // Chuyển đổi ngôn ngữ hiển thị hoặc dịch phụ đề sang ngôn ngữ mới
    async function onVideoTargetLangChange(newLang) {
      localStorage.setItem('geminitrans_video_target_lang', newLang);
      if (currentYoutubeVideoId && currentYoutubeUrl) {
        await fetchAndTranslateYouTubeCaptions(currentYoutubeVideoId, currentYoutubeUrl);
        return;
      }
      if (!currentVideoSubtitles || !currentVideoSubtitles.length) {
        return;
      }
      
      // Kiểm tra nếu các cue đã có bản dịch sang ngôn ngữ này
      const hasLangInSubs = currentVideoSubtitles.some(s => s.translations && s.translations[newLang]);
      if (hasLangInSubs) {
        currentVideoSubtitles.forEach(s => {
          if (s.translations && s.translations[newLang]) {
            s.translated = s.translations[newLang];
          }
        });
        renderSubtitleTimeline(currentVideoSubtitles);
        updateVideoTextTrack(currentVideoSubtitles);
        saveSubtitleCache(currentVideoSubtitles);
        return;
      }

      // Hỏi người dùng để dịch tức thì bằng AI mà không cần quét lại video
      const langSelect = document.getElementById('video-target-lang');
      const langName = langSelect ? langSelect.options[langSelect.selectedIndex].text : newLang;
      const confirmMsg = currentLang === 'vi' 
        ? `Dịch toàn bộ phụ đề hiện tại sang ${langName}?\n(Quá trình diễn ra siêu tốc bằng AI, không cần quét lại video)`
        : `Translate existing subtitles to ${langName}?\n(Instant AI translation without re-scanning video)`;
        
      if (!confirm(confirmMsg)) return;

      const btn = document.getElementById('btn-auto-sub');
      btn.disabled = true;
      btn.innerHTML = `<span class="w-3.5 h-3.5 rounded-[8px] bg-white animate-ping mr-1"></span> ${t('btn_translating_sub') || 'Đang dịch...'}`;

      try {
        const res = await fetch('/api/video/translate-subtitles', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            video_id: currentVideoId,
            subtitles: currentVideoSubtitles,
            target_lang: newLang
          })
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `Server HTTP ${res.status}`);
        }

        const data = await res.json();
        currentVideoSubtitles = data.subtitles || currentVideoSubtitles;
        renderSubtitleTimeline(currentVideoSubtitles);
        updateVideoTextTrack(currentVideoSubtitles);
        saveSubtitleCache(currentVideoSubtitles);
      } catch (err) {
        alert("Lỗi dịch phụ đề: " + err.message);
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<i data-lucide="subtitles" class="w-4 h-4"></i> ${t('btn_auto_sub')}`;
        lucide.createIcons();
      }
    }

    async function startAutoSubtitling(bypassCache = false) {
      if (!currentVideoId) {
        const urlInput = document.getElementById('video-url-input').value.trim();
        if (urlInput) {
          return loadYouTubeVideo();
        } else {
          alert(t('alert_no_video'));
          return;
        }
      }

      const videoId = currentVideoId;
      if (autoSubtitleJob && autoSubtitleJobVideoId === videoId) {
        return autoSubtitleJob;
      }

      // Check cache first if not explicitly bypassing
      if (!bypassCache) {
        const hasCache = checkAndLoadSubtitleCache();
        if (hasCache) return;
      }

      autoSubtitleJobVideoId = videoId;
      autoSubtitleJob = runAutoSubtitleJob(videoId);
      try {
        return await autoSubtitleJob;
      } finally {
        if (autoSubtitleJobVideoId === videoId) {
          autoSubtitleJob = null;
          autoSubtitleJobVideoId = null;
        }
      }
    }

    async function runAutoSubtitleJob(videoId) {
      const btn = document.getElementById('btn-auto-sub');
      btn.disabled = true;
      btn.innerHTML = `<span class="w-3.5 h-3.5 rounded-[8px] bg-white animate-ping mr-1"></span> ${t('btn_auto_sub_scanning')}`;

      const listContainer = document.getElementById('sub-timeline-list');
      listContainer.innerHTML = `
        <div class="p-6 text-center space-y-3">
          <div class="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-[8px] animate-spin mx-auto"></div>
          <p class="text-xs text-indigo-300 font-medium">${t('timeline_scanning_msg')}</p>
          <p class="text-[11px] text-slate-500">${t('timeline_scanning_sub')}</p>
        </div>
      `;

      try {
        const targetLang = document.getElementById('video-target-lang')?.value || 'vi';
        const isMulti = document.getElementById('multi-lang-sub-toggle')?.checked || false;
        const targetLangs = isMulti ? ['vi', 'en', 'ja', 'zh', 'ko'] : [targetLang];

        const res = await fetch('/api/video/auto-subtitle', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            video_id: videoId,
            target_lang: targetLang,
            target_langs: isMulti ? targetLangs : undefined,
            url: document.getElementById('video-url-input').value.trim()
          })
        });
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `Server HTTP ${res.status}`);
        }
        const data = await res.json();
        if (currentVideoId !== videoId) return;
        currentVideoSubtitles = data.subtitles || [];

        subtitleOverlay.innerHTML = '';
        subtitleOverlay.classList.add('hidden');

        renderSubtitleTimeline(currentVideoSubtitles);
        updateVideoTextTrack(currentVideoSubtitles);
        saveSubtitleCache(currentVideoSubtitles);
        hideCacheNoticeBadge();

        // Show export box
        document.getElementById('export-download-box').classList.remove('hidden');

        // Auto play preview from beginning
        if (!uploadedVideo.classList.contains('hidden')) {
          uploadedVideo.currentTime = 0;
          uploadedVideo.play().catch(() => {});
        }
        fetchPoolStatus();
      } catch (err) {
        if (currentVideoId === videoId) {
          listContainer.innerHTML = `<div class="p-4 text-xs text-red-400">Subtitle error: ${err.message}</div>`;
        }
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<i data-lucide="subtitles" class="w-4 h-4"></i> ${t('btn_auto_sub')}`;
        lucide.createIcons();
      }
    }

    // Render Subtitle Timeline
    function renderSubtitleTimeline(subs) {
      const listContainer = document.getElementById('sub-timeline-list');
      listContainer.innerHTML = '';
      document.getElementById('sub-count-badge').innerText = t('timeline_count_cues', { count: subs.length });

      if (!subs.length) {
        listContainer.innerHTML = `<div class="p-4 text-xs text-slate-500 italic text-center">${t('timeline_no_subs')}</div>`;
        return;
      }

      subs.forEach((s, idx) => {
        const card = document.createElement('div');
        card.id = `sub-card-${s.id}`;
        card.className = "sub-item-card p-3 rounded-[8px] bg-slate-800/40 border border-slate-700/70 hover:border-indigo-500 active:border-indigo-400 transition cursor-pointer space-y-2 touch-manipulation";
        
        card.innerHTML = `
          <div class="flex items-center justify-between text-xs sm:text-[11px]">
            <span class="font-mono text-indigo-400 font-semibold flex items-center gap-1.5 py-0.5 px-1.5 -ml-1 rounded hover:bg-indigo-500/10 active:bg-indigo-500/20 transition cursor-pointer" onclick="jumpToTime(${s.start})" title="Tua tới mốc thời gian">
              <i data-lucide="play-circle" class="w-4 h-4 text-indigo-400"></i> ${s.start_str} ➔ ${s.end_str}
            </span>
            <span class="text-slate-500 font-mono text-xs">#${idx + 1}</span>
          </div>
          ${s.original ? `<div class="text-xs text-slate-300/80 italic bg-slate-900/50 p-1.5 rounded-lg border border-slate-800/80">${escapeHtml(s.original)}</div>` : ''}
          <textarea class="w-full bg-slate-900 border border-slate-700/80 rounded-lg p-2 text-xs sm:text-xs text-amber-300 font-medium focus:outline-none focus:border-indigo-500 resize-none leading-relaxed touch-manipulation" rows="2" onchange="editSubtitleText(${s.id}, this.value)">${escapeHtml(s.translated)}</textarea>
        `;
        listContainer.appendChild(card);
      });
      lucide.createIcons();
    }

    function jumpToTime(sec) {
      if (youtubePlayer && typeof youtubePlayer.seekTo === 'function') {
        youtubePlayer.seekTo(sec, true);
        youtubePlayer.playVideo();
        return;
      }
      uploadedVideo.currentTime = sec;
      uploadedVideo.play();
    }

    function editSubtitleText(id, newText) {
      const sub = currentVideoSubtitles.find(s => s.id === id);
      if (sub) {
        sub.translated = newText;
        if (uploadedVideo.currentTime >= sub.start && uploadedVideo.currentTime <= sub.end) {
          renderOverlaySubtitle(sub);
        }
        updateVideoTextTrack(currentVideoSubtitles);
        saveSubtitleCache(currentVideoSubtitles);
      }
    }

    // ==========================================
    // EXPORT HARDSUB MODAL
    // ==========================================
    function openExportModal() {
      if (!currentVideoId) {
        alert(t('alert_no_video'));
        return;
      }
      if (!currentVideoSubtitles.length) {
        alert(t('alert_no_subs'));
        return;
      }
      document.getElementById('export-choice-modal').classList.remove('hidden');
    }

    function closeExportModal() {
      document.getElementById('export-choice-modal').classList.add('hidden');
    }

    function chooseExportMode(mode) {
      closeExportModal();
      if (mode === 'client') {
        startClientSideHardsubBurn();
      } else if (mode === 'server') {
        burnAndExportVideoServer();
      } else if (mode === 'subtitles') {
        downloadCurrentSrt();
      }
    }

    // ==========================================
    // 1. CLIENT-SIDE ZERO-STORAGE HARDSUB BURNER
    // (HTML5 Canvas & MediaRecorder API)
    // ==========================================
    function drawCanvasSubtitle(ctx, subOrText, width, height, opts) {
      if (!subOrText) return;
      ctx.save();
      const isDual = document.getElementById('dual-sub-toggle')?.checked;

      let origText = '';
      let transText = '';
      if (typeof subOrText === 'object') {
        origText = (subOrText.original || '').trim();
        transText = (subOrText.translated || '').trim() || origText;
      } else {
        transText = String(subOrText).trim();
      }

      const showDual = isDual && origText && transText && origText !== transText;
      const maxWidth = width * 0.88;

      const wrapLines = (text, fSize, fWeight = 'bold') => {
        ctx.font = `${fWeight} ${fSize}px 'Inter', sans-serif, Arial`;
        const words = text.split(' ');
        const lines = [];
        let curLine = '';
        for (let n = 0; n < words.length; n++) {
          const testLine = curLine ? curLine + ' ' + words[n] : words[n];
          const metrics = ctx.measureText(testLine);
          if (metrics.width > maxWidth && n > 0) {
            lines.push(curLine);
            curLine = words[n];
          } else {
            curLine = testLine;
          }
        }
        if (curLine) lines.push(curLine);
        return lines;
      };

      const transLines = wrapLines(transText, opts.fontSize, 'bold');
      const origLines = showDual ? wrapLines(origText, Math.round(opts.fontSize * 0.75), 'normal') : [];

      const transLineHeight = opts.fontSize * 1.35;
      const origLineHeight = Math.round(opts.fontSize * 0.75) * 1.25;

      const totalTextHeight = (transLines.length * transLineHeight) + (origLines.length * origLineHeight);
      const padX = Math.round(opts.fontSize * 1.2);
      const padY = Math.round(opts.fontSize * 0.45);
      const boxHeight = totalTextHeight + (padY * 2);

      let maxW = 0;
      ctx.font = `bold ${opts.fontSize}px 'Inter', sans-serif, Arial`;
      for (const l of transLines) {
        const w = ctx.measureText(l).width;
        if (w > maxW) maxW = w;
      }
      if (showDual) {
        ctx.font = `normal ${Math.round(opts.fontSize * 0.75)}px 'Inter', sans-serif, Arial`;
        for (const l of origLines) {
          const w = ctx.measureText(l).width;
          if (w > maxW) maxW = w;
        }
      }

      const boxWidth = Math.min(width * 0.94, maxW + (padX * 2));
      const boxX = (width - boxWidth) / 2;
      const boxY = height - opts.marginV - boxHeight;

      if (opts.maskOld) {
        ctx.fillStyle = opts.bgColorRgba;
        if (typeof ctx.roundRect === 'function') {
          ctx.beginPath();
          ctx.roundRect(boxX, boxY, boxWidth, boxHeight, 8);
          ctx.fill();
        } else {
          ctx.fillRect(boxX, boxY, boxWidth, boxHeight);
        }
      }

      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';

      let curY = boxY + padY;

      // Draw original lines if dual
      if (showDual) {
        const origFontSize = Math.round(opts.fontSize * 0.75);
        ctx.font = `500 ${origFontSize}px 'Inter', sans-serif, Arial`;
        ctx.fillStyle = '#e2e8f0';
        for (let i = 0; i < origLines.length; i++) {
          const y = curY + (origLineHeight / 2);
          if (!opts.maskOld) {
            ctx.strokeStyle = '#000000';
            ctx.lineWidth = Math.max(2, Math.round(origFontSize * 0.15));
            ctx.strokeText(origLines[i], width / 2, y);
          }
          ctx.fillText(origLines[i], width / 2, y);
          curY += origLineHeight;
        }
      }

      // Draw translated lines
      ctx.font = `bold ${opts.fontSize}px 'Inter', sans-serif, Arial`;
      ctx.fillStyle = opts.textColor;
      for (let i = 0; i < transLines.length; i++) {
        const y = curY + (transLineHeight / 2);
        if (!opts.maskOld) {
          ctx.strokeStyle = '#000000';
          ctx.lineWidth = Math.max(3, Math.round(opts.fontSize * 0.15));
          ctx.strokeText(transLines[i], width / 2, y);
        }
        ctx.fillText(transLines[i], width / 2, y);
        curY += transLineHeight;
      }

      ctx.restore();
    }

    async function startClientSideHardsubBurn() {
      if (!uploadedVideo.src || uploadedVideo.classList.contains('hidden')) {
        alert(t('alert_no_video'));
        return;
      }
      if (!currentVideoSubtitles.length) {
        alert(t('alert_no_subs'));
        return;
      }

      // Open progress modal
      document.getElementById('client-burn-modal').classList.remove('hidden');
      document.getElementById('burn-progress-bar').style.width = '0%';
      document.getElementById('burn-progress-percent').innerText = '0%';
      document.getElementById('burn-progress-status').innerText = t('burn_init');

      isClientBurning = true;
      burnChunks = [];

      const video = uploadedVideo;
      video.pause();
      video.currentTime = 0;
      await new Promise(r => {
        if (video.readyState >= 2) return r();
        video.onloadeddata = () => r();
      });

      const vWidth = video.videoWidth || 1280;
      const vHeight = video.videoHeight || 720;
      const canvas = document.createElement('canvas');
      canvas.width = vWidth;
      canvas.height = vHeight;
      const ctx = canvas.getContext('2d');

      const fontScale = vHeight / 540;
      const textColor = document.getElementById('sub-color').value;
      const bgColor = document.getElementById('sub-bg-color').value;
      const opacity = parseInt(document.getElementById('sub-opacity').value) / 100.0;
      const rawFontSize = parseInt(document.getElementById('sub-font-size').value);
      const rawMarginV = parseInt(document.getElementById('sub-margin-v').value);
      const maskOld = document.getElementById('mask-old-sub').checked;

      const fontSize = Math.round(rawFontSize * fontScale);
      const marginV = Math.round(rawMarginV * fontScale);
      const bgColorRgba = hexToRgba(bgColor, opacity);

      // Audio capture
      let audioTracks = [];
      try {
        const vStream = video.captureStream ? video.captureStream() : (video.mozCaptureStream ? video.mozCaptureStream() : null);
        if (vStream) {
          audioTracks = vStream.getAudioTracks();
        }
      } catch (e) {
        console.warn("Audio track capture error:", e);
      }

      const canvasStream = canvas.captureStream(30);
      const combinedTracks = [canvasStream.getVideoTracks()[0], ...audioTracks];
      const combinedStream = new MediaStream(combinedTracks);

      let chosenMime = 'video/webm';
      const mimeTypes = [
        'video/mp4;codecs=avc1,mp4a.40.2',
        'video/mp4',
        'video/webm;codecs=vp9,opus',
        'video/webm;codecs=vp8,opus',
        'video/webm'
      ];
      for (const m of mimeTypes) {
        if (MediaRecorder.isTypeSupported(m)) {
          chosenMime = m;
          break;
        }
      }

      burnMediaRecorder = new MediaRecorder(combinedStream, { mimeType: chosenMime });
      burnMediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) burnChunks.push(e.data);
      };

      burnMediaRecorder.onstop = () => {
        if (!isClientBurning) return;
        const blob = new Blob(burnChunks, { type: chosenMime });
        const ext = chosenMime.includes('mp4') ? 'mp4' : 'webm';
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `GeminiTrans_Hardsub_${currentVideoId || 'export'}.${ext}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        document.getElementById('burn-progress-status').innerText = t('burn_done');
        document.getElementById('burn-progress-bar').style.width = '100%';
        document.getElementById('burn-progress-percent').innerText = '100%';
        setTimeout(() => {
          document.getElementById('client-burn-modal').classList.add('hidden');
          alert(t('burn_success_alert'));
        }, 600);
      };

      burnMediaRecorder.start(250);
      video.currentTime = 0;
      await video.play();

      const renderLoop = () => {
        if (!isClientBurning) return;

        if (video.ended || video.currentTime >= video.duration - 0.1) {
          isClientBurning = false;
          video.pause();
          burnMediaRecorder.stop();
          return;
        }

        ctx.drawImage(video, 0, 0, vWidth, vHeight);

        const curTime = video.currentTime;
        const activeSub = currentVideoSubtitles.find(s => curTime >= s.start && curTime <= s.end);
        if (activeSub && (activeSub.translated || activeSub.original)) {
          drawCanvasSubtitle(ctx, activeSub, vWidth, vHeight, {
            fontSize,
            marginV,
            textColor,
            bgColorRgba,
            maskOld
          });
        }

        const progress = Math.min(100, Math.round((curTime / (video.duration || 1)) * 100));
        document.getElementById('burn-progress-bar').style.width = `${progress}%`;
        document.getElementById('burn-progress-percent').innerText = `${progress}%`;
        const m = String(Math.floor(curTime / 60)).padStart(2, '0');
        const s = String(Math.floor(curTime % 60)).padStart(2, '0');
        const dm = String(Math.floor(video.duration / 60)).padStart(2, '0');
        const ds = String(Math.floor(video.duration % 60)).padStart(2, '0');
        document.getElementById('burn-progress-status').innerText = `${t('burn_encoding')} (${m}:${s} / ${dm}:${ds})`;

        requestAnimationFrame(renderLoop);
      };

      requestAnimationFrame(renderLoop);
    }

    function cancelClientSideBurn() {
      isClientBurning = false;
      if (burnMediaRecorder && burnMediaRecorder.state !== 'inactive') {
        burnMediaRecorder.stop();
      }
      uploadedVideo.pause();
      document.getElementById('client-burn-modal').classList.add('hidden');
    }

    // ==========================================
    // 2. SERVER HARDSUB BURN (FFMPEG & AUTO-CLEANUP)
    // ==========================================
    async function burnAndExportVideoServer() {
      if (!currentVideoId) return alert(t('alert_no_video'));
      if (!currentVideoSubtitles.length) return alert(t('alert_no_subs'));

      const btn = document.getElementById('btn-burn-video');
      btn.disabled = true;
      btn.innerHTML = `<span class="w-3.5 h-3.5 rounded-[8px] bg-white animate-ping mr-1"></span> FFmpeg Burning...`;

      const textColor = document.getElementById('sub-color').value;
      const bgColor = document.getElementById('sub-bg-color').value;
      const opacity = parseInt(document.getElementById('sub-opacity').value) / 100.0;
      const fontSize = parseInt(document.getElementById('sub-font-size').value);
      const marginV = parseInt(document.getElementById('sub-margin-v').value);
      const maskOld = document.getElementById('mask-old-sub').checked;
      const isDual = document.getElementById('dual-sub-toggle')?.checked;

      const subsPayload = isDual
        ? currentVideoSubtitles.map(s => {
            const o = (s.original || '').trim();
            const tr = (s.translated || '').trim();
            if (o && tr && o !== tr) {
              return { ...s, translated: `${o}\n${tr}` };
            }
            return s;
          })
        : currentVideoSubtitles;

      try {
        const res = await fetch('/api/video/burn-subtitles', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            video_id: currentVideoId,
            subtitles: subsPayload,
            font_size: fontSize,
            text_color: textColor,
            bg_color: bgColor,
            bg_opacity: opacity,
            mask_old_sub: maskOld,
            vertical_margin: marginV
          })
        });

        const data = await res.json();
        if (data.download_url) {
          const dlBtn = document.getElementById('btn-download-video');
          // Use clean download URL with auto-cleanup parameter
          dlBtn.href = data.clean_download_url || data.download_url;
          document.getElementById('server-mp4-link-container').classList.remove('hidden');
          document.getElementById('export-download-box').classList.remove('hidden');

          // Switch preview
          subtitleOverlay.classList.add('hidden');
          uploadedVideo.src = data.download_url + `?t=${Date.now()}`;
          uploadedVideo.load();
          uploadedVideo.play();

          alert(currentLang === 'vi' 
            ? "Xuất video Server thành công! Bạn có thể xem trực tiếp hoặc bấm nút 'Tải MP4 Hardsub'."
            : "Server video burn completed! You can watch it directly or click 'Download Hardsub MP4'.");
        }
      } catch (err) {
        alert("Server burn error: " + err.message);
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<i data-lucide="download" class="w-4 h-4"></i> ${t('btn_export_video')}`;
        lucide.createIcons();
      }
    }

    // Server Temp Storage Instant Cleanup
    async function cleanServerStorage() {
      if (!currentVideoId) {
        alert(t('alert_no_video'));
        return;
      }
      try {
        const res = await fetch('/api/video/cleanup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ video_id: currentVideoId })
        });
        const data = await res.json();
        if (data.status === 'success') {
          alert(t('alert_clean_success'));
        }
      } catch (e) {
        alert("Cleanup error: " + e.message);
      }
    }

    // ==========================================
    // 3. SUBTITLE DOWNLOADS (.SRT & .VTT)
    // ==========================================
    function formatSrtTime(sec) {
      const h = Math.floor(sec / 3600);
      const m = Math.floor((sec % 3600) / 60);
      const s = Math.floor(sec % 60);
      const ms = Math.floor((sec - Math.floor(sec)) * 1000);
      return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')},${String(ms).padStart(3, '0')}`;
    }

    function formatVttTime(sec) {
      const h = Math.floor(sec / 3600);
      const m = Math.floor((sec % 3600) / 60);
      const s = Math.floor(sec % 60);
      const ms = Math.floor((sec - Math.floor(sec)) * 1000);
      return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${String(ms).padStart(3, '0')}`;
    }

    function downloadCurrentSrt() {
      if (!currentVideoSubtitles.length) return alert(t('alert_no_subs'));
      let srt = '';
      const isDual = document.getElementById('dual-sub-toggle')?.checked;
      const curLang = document.getElementById('video-target-lang')?.value || 'vi';
      currentVideoSubtitles.forEach((s, idx) => {
        const sTime = formatSrtTime(s.start);
        const eTime = formatSrtTime(s.end);
        let text = '';
        const orig = (s.original || '').trim();
        const trans = (s.translations && s.translations[curLang] ? s.translations[curLang] : (s.translated || '')).trim();
        if (isDual && orig && trans && orig !== trans) {
          text = `${orig}\n${trans}`;
        } else {
          text = trans || orig || '';
        }
        srt += `${idx + 1}\n${sTime} --> ${eTime}\n${text}\n\n`;
      });
      const blob = new Blob([srt], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `GeminiTrans_${currentVideoId || 'subs'}_${curLang}.srt`;
      a.click();
    }

    function downloadCurrentVtt() {
      if (!currentVideoSubtitles.length) return alert(t('alert_no_subs'));
      let vtt = 'WEBVTT\n\n';
      const isDual = document.getElementById('dual-sub-toggle')?.checked;
      const curLang = document.getElementById('video-target-lang')?.value || 'vi';
      currentVideoSubtitles.forEach((s, idx) => {
        const sTime = formatVttTime(s.start);
        const eTime = formatVttTime(s.end);
        let text = '';
        const orig = (s.original || '').trim();
        const trans = (s.translations && s.translations[curLang] ? s.translations[curLang] : (s.translated || '')).trim();
        if (isDual && orig && trans && orig !== trans) {
          text = `${orig}\n${trans}`;
        } else {
          text = trans || orig || '';
        }
        vtt += `${idx + 1}\n${sTime} --> ${eTime}\n${text}\n\n`;
      });
      const blob = new Blob([vtt], { type: 'text/vtt;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `GeminiTrans_${currentVideoId || 'subs'}_${curLang}.vtt`;
      a.click();
    }

    function getYouTubeVideoId(url) {
      try {
        const parsed = new URL(url);
        if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') return null;
        const hostname = parsed.hostname.toLowerCase().replace(/\.$/, '');
        const isShortHost = hostname === 'youtu.be';
        const isYouTubeHost = isShortHost ||
          hostname === 'youtube.com' || hostname.endsWith('.youtube.com') ||
          hostname === 'youtube-nocookie.com' || hostname.endsWith('.youtube-nocookie.com');
        if (!isYouTubeHost) return null;

        let videoId = parsed.searchParams.get('v');
        if (isShortHost) {
          videoId = parsed.pathname.split('/').filter(Boolean)[0];
        } else if (!videoId) {
          const pathParts = parsed.pathname.split('/').filter(Boolean);
          if (['embed', 'shorts', 'live', 'v'].includes(pathParts[0])) {
            videoId = pathParts[1];
          }
        }
        return videoId && /^[A-Za-z0-9_-]{11}$/.test(videoId) ? videoId : null;
      } catch (_) {
        return null;
      }
    }

    function showYouTubeEmbedFallback(videoId, errorMessage, captionsAlreadyAttempted = false) {
      const box = document.getElementById('yt-player-box');
      const placeholder = document.getElementById('player-placeholder');
      const videoBadge = document.getElementById('current-video-badge');
      currentYoutubeVideoId = videoId;
      currentYoutubeUrl = document.getElementById('video-url-input').value.trim();
      currentVideoSubtitles = [];
      const target = document.createElement('div');
      target.id = 'youtube-player-api-target';
      box.replaceChildren(target);
      box.classList.remove('hidden');
      placeholder.classList.add('hidden');
      videoBadge.innerText = t('badge_youtube_embed');
      videoBadge.className = 'text-xs px-2.5 py-1 rounded-md bg-amber-500/20 text-amber-300 font-medium';
      setVideoActionsEnabled(false);
      setSubtitleOnlyMode(true);

      const message = document.createElement('div');
      message.className = 'p-4 text-xs text-amber-300 leading-relaxed';
      message.textContent = t('youtube_download_limited');
      document.getElementById('sub-timeline-list').replaceChildren(message);
      document.getElementById('sub-count-badge').innerText = '—';
      void initializeYouTubePlayer(videoId);
      if (captionsAlreadyAttempted) {
        document.getElementById('sub-timeline-list').textContent =
          t('youtube_captions_unavailable');
      } else {
        void fetchAndTranslateYouTubeCaptions(videoId, currentYoutubeUrl);
      }
      console.warn('YouTube server import failed; falling back to the official embedded player:', errorMessage);
    }

    // YouTube / Web Stream Video Loader
    async function loadYouTubeVideo() {
      if (isLoadingVideo) return;
      const url = document.getElementById('video-url-input').value.trim();
      if (!url) {
        alert(t('alert_no_video'));
        return;
      }
      isLoadingVideo = true;
      currentVideoId = null;
      currentLoadedUrl = null;
      currentFileSignature = null;

      // Dừng và dọn dẹp sạch sẽ toàn bộ player trước đó
      stopAndCleanAllPlayers();
      resetSubtitleStateForVideoLoad();

      // Hiển thị loading spinner trên player-placeholder (TUYỆT ĐỐI KHÔNG TẠO IFRAME YOUTUBE AUTOPLAY)
      const placeholder = document.getElementById('player-placeholder');
      if (placeholder) {
        placeholder.classList.remove('hidden');
        placeholder.innerHTML = `
          <div class="flex flex-col items-center justify-center p-6 space-y-3">
            <div class="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-[8px] animate-spin"></div>
            <p class="text-xs text-indigo-300 font-medium">${t('badge_url_loading')}</p>
          </div>
        `;
      }

      const videoBadge = document.getElementById('current-video-badge');
      const btnAuto = document.getElementById('btn-auto-sub');
      let youtubeCaptionsAttempted = false;

      videoBadge.innerText = t('badge_url_loading');
      videoBadge.className = "text-xs px-2.5 py-1 rounded-md bg-amber-500/20 text-amber-300 font-medium animate-pulse";
      btnAuto.innerHTML = `<span class="w-3.5 h-3.5 rounded-[8px] bg-white animate-ping mr-1"></span> ...`;

      try {
        const res = await fetch('/api/video/process-url', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            url,
            target_lang: document.getElementById('video-target-lang')?.value || 'vi'
          })
        });
        const data = await res.json();
        youtubeCaptionsAttempted = Boolean(data.youtube_captions_attempted);
        if (data.mode === 'youtube_captions' && Array.isArray(data.subtitles)) {
          currentVideoId = null;
          currentLoadedUrl = url;
          currentYoutubeVideoId = data.youtube_id;
          currentYoutubeUrl = url;
          currentVideoSubtitles = data.subtitles;
          const box = document.getElementById('yt-player-box');
          box.classList.remove('hidden');
          placeholder?.classList.add('hidden');
          videoBadge.innerText = t('badge_youtube_embed');
          videoBadge.className = 'text-xs px-2.5 py-1 rounded-md bg-emerald-500/20 text-emerald-300 font-medium';
          setVideoActionsEnabled(false);
          setSubtitleOnlyMode(true);
          document.getElementById('export-download-box')?.classList.remove('hidden');
          renderSubtitleTimeline(currentVideoSubtitles);
          void initializeYouTubePlayer(data.youtube_id);
          updateYouTubeSubtitle();
          return;
        }
        if (data.video_id) {
          setSubtitleOnlyMode(false);
          currentVideoId = data.video_id;
          videoBadge.innerText = `${t('badge_url_loaded')}${data.filename || 'Stream'}`;
          videoBadge.className = "text-xs px-2.5 py-1 rounded-md bg-emerald-500/20 text-emerald-300 font-medium";

          if (data.video_url) {
            // Đảm bảo box yt-player-box hoàn toàn rỗng và ẩn
            const box = document.getElementById('yt-player-box');
            if (box) {
              box.innerHTML = '';
              box.classList.add('hidden');
            }
            if (placeholder) {
              placeholder.classList.add('hidden');
            }
            uploadedVideo.classList.remove('hidden');
            uploadedVideo.src = data.video_url;
            uploadedVideo.load();
            uploadedVideo.play().catch(() => {});
          }

          // Enable Action Buttons
          setVideoActionsEnabled(true);

          currentLoadedUrl = url;
          currentFileSignature = null;

          subtitleOverlay.innerHTML = '';
          subtitleOverlay.classList.add('hidden');
          updateSubtitleStyle();

          // Reuse cached subtitles when available; otherwise start the normal extraction flow.
          await startAutoSubtitling();
        } else {
          throw new Error(data.error || data.detail || "Cannot load video");
        }
      } catch (err) {
        const youtubeId = getYouTubeVideoId(url);
        if (youtubeId && /\bHTTP\s+(?:403|429)\b/i.test(err.message)) {
          showYouTubeEmbedFallback(youtubeId, err.message, youtubeCaptionsAttempted);
          return;
        }
        stopAndCleanAllPlayers();
        videoBadge.innerText = "Error: " + err.message;
        videoBadge.className = "text-xs px-2.5 py-1 rounded-md bg-red-500/20 text-red-400 font-medium";
        alert("Error loading video: " + err.message);
      } finally {
        isLoadingVideo = false;
        btnAuto.innerHTML = `<i data-lucide="subtitles" class="w-4 h-4"></i> ${t('btn_auto_sub')}`;
        lucide.createIcons();
      }
    }

    // ==========================================
    // POOL STATUS & DRAWER RENDERING (100% SECURE - NO RAW KEYS)


    // Expose functions to window for HTML inline event handlers
    window.uploadedVideo = typeof uploadedVideo !== 'undefined' ? uploadedVideo : undefined;
    window.subtitleOverlay = typeof subtitleOverlay !== 'undefined' ? subtitleOverlay : undefined;
    window.setVideoActionsEnabled = typeof setVideoActionsEnabled !== 'undefined' ? setVideoActionsEnabled : undefined;
    window.setSubtitleOnlyMode = typeof setSubtitleOnlyMode !== 'undefined' ? setSubtitleOnlyMode : undefined;
    window.stopYouTubePlayer = typeof stopYouTubePlayer !== 'undefined' ? stopYouTubePlayer : undefined;
    window.loadYouTubeIframeApi = typeof loadYouTubeIframeApi !== 'undefined' ? loadYouTubeIframeApi : undefined;
    window.highlightAndScrollSubtitle = typeof highlightAndScrollSubtitle !== 'undefined' ? highlightAndScrollSubtitle : undefined;
    window.syncYouTubeSubtitle = typeof syncYouTubeSubtitle !== 'undefined' ? syncYouTubeSubtitle : undefined;
    window.initializeYouTubePlayer = typeof initializeYouTubePlayer !== 'undefined' ? initializeYouTubePlayer : undefined;
    window.fetchAndTranslateYouTubeCaptions = typeof fetchAndTranslateYouTubeCaptions !== 'undefined' ? fetchAndTranslateYouTubeCaptions : undefined;
    window.updateYouTubeSubtitle = typeof updateYouTubeSubtitle !== 'undefined' ? updateYouTubeSubtitle : undefined;
    window.getCurrentCaptureTime = typeof getCurrentCaptureTime !== 'undefined' ? getCurrentCaptureTime : undefined;
    window.recordTabAudioSegment = typeof recordTabAudioSegment !== 'undefined' ? recordTabAudioSegment : undefined;
    window.sendTabAudioChunk = typeof sendTabAudioChunk !== 'undefined' ? sendTabAudioChunk : undefined;
    window.enqueueTabAudioChunk = typeof enqueueTabAudioChunk !== 'undefined' ? enqueueTabAudioChunk : undefined;
    window.runTabAudioQueueWorker = typeof runTabAudioQueueWorker !== 'undefined' ? runTabAudioQueueWorker : undefined;
    window.runTabAudioCapture = typeof runTabAudioCapture !== 'undefined' ? runTabAudioCapture : undefined;
    window.startTabAudioCapture = typeof startTabAudioCapture !== 'undefined' ? startTabAudioCapture : undefined;
    window.stopTabAudioCapture = typeof stopTabAudioCapture !== 'undefined' ? stopTabAudioCapture : undefined;
    window.stopAndCleanAllPlayers = typeof stopAndCleanAllPlayers !== 'undefined' ? stopAndCleanAllPlayers : undefined;
    window.renderOverlaySubtitle = typeof renderOverlaySubtitle !== 'undefined' ? renderOverlaySubtitle : undefined;
    window.toggleDualSubtitles = typeof toggleDualSubtitles !== 'undefined' ? toggleDualSubtitles : undefined;
    window.setNativeTrackMode = typeof setNativeTrackMode !== 'undefined' ? setNativeTrackMode : undefined;
    window.updateVideoTextTrack = typeof updateVideoTextTrack !== 'undefined' ? updateVideoTextTrack : undefined;
    window.getCacheKeys = typeof getCacheKeys !== 'undefined' ? getCacheKeys : undefined;
    window.checkAndLoadSubtitleCache = typeof checkAndLoadSubtitleCache !== 'undefined' ? checkAndLoadSubtitleCache : undefined;
    window.saveSubtitleCache = typeof saveSubtitleCache !== 'undefined' ? saveSubtitleCache : undefined;
    window.clearSubtitleCacheForCurrentVideo = typeof clearSubtitleCacheForCurrentVideo !== 'undefined' ? clearSubtitleCacheForCurrentVideo : undefined;
    window.showCacheNoticeBadge = typeof showCacheNoticeBadge !== 'undefined' ? showCacheNoticeBadge : undefined;
    window.hideCacheNoticeBadge = typeof hideCacheNoticeBadge !== 'undefined' ? hideCacheNoticeBadge : undefined;
    window.resetSubtitleStateForVideoLoad = typeof resetSubtitleStateForVideoLoad !== 'undefined' ? resetSubtitleStateForVideoLoad : undefined;
    window.rescanBypassCache = typeof rescanBypassCache !== 'undefined' ? rescanBypassCache : undefined;
    window.togglePlayerFullscreen = typeof togglePlayerFullscreen !== 'undefined' ? togglePlayerFullscreen : undefined;
    window.handleFullscreenChange = typeof handleFullscreenChange !== 'undefined' ? handleFullscreenChange : undefined;
    window.hexToRgba = typeof hexToRgba !== 'undefined' ? hexToRgba : undefined;
    window.updateSubtitleStyle = typeof updateSubtitleStyle !== 'undefined' ? updateSubtitleStyle : undefined;
    window.handleVideoUpload = typeof handleVideoUpload !== 'undefined' ? handleVideoUpload : undefined;
    window.onVideoTargetLangChange = typeof onVideoTargetLangChange !== 'undefined' ? onVideoTargetLangChange : undefined;
    window.startAutoSubtitling = typeof startAutoSubtitling !== 'undefined' ? startAutoSubtitling : undefined;
    window.runAutoSubtitleJob = typeof runAutoSubtitleJob !== 'undefined' ? runAutoSubtitleJob : undefined;
    window.renderSubtitleTimeline = typeof renderSubtitleTimeline !== 'undefined' ? renderSubtitleTimeline : undefined;
    window.jumpToTime = typeof jumpToTime !== 'undefined' ? jumpToTime : undefined;
    window.editSubtitleText = typeof editSubtitleText !== 'undefined' ? editSubtitleText : undefined;
    window.openExportModal = typeof openExportModal !== 'undefined' ? openExportModal : undefined;
    window.closeExportModal = typeof closeExportModal !== 'undefined' ? closeExportModal : undefined;
    window.chooseExportMode = typeof chooseExportMode !== 'undefined' ? chooseExportMode : undefined;
    window.drawCanvasSubtitle = typeof drawCanvasSubtitle !== 'undefined' ? drawCanvasSubtitle : undefined;
    window.wrapLines = typeof wrapLines !== 'undefined' ? wrapLines : undefined;
    window.startClientSideHardsubBurn = typeof startClientSideHardsubBurn !== 'undefined' ? startClientSideHardsubBurn : undefined;
    window.renderLoop = typeof renderLoop !== 'undefined' ? renderLoop : undefined;
    window.cancelClientSideBurn = typeof cancelClientSideBurn !== 'undefined' ? cancelClientSideBurn : undefined;
    window.burnAndExportVideoServer = typeof burnAndExportVideoServer !== 'undefined' ? burnAndExportVideoServer : undefined;
    window.cleanServerStorage = typeof cleanServerStorage !== 'undefined' ? cleanServerStorage : undefined;
    window.formatSrtTime = typeof formatSrtTime !== 'undefined' ? formatSrtTime : undefined;
    window.formatVttTime = typeof formatVttTime !== 'undefined' ? formatVttTime : undefined;
    window.downloadCurrentSrt = typeof downloadCurrentSrt !== 'undefined' ? downloadCurrentSrt : undefined;
    window.downloadCurrentVtt = typeof downloadCurrentVtt !== 'undefined' ? downloadCurrentVtt : undefined;
    window.getYouTubeVideoId = typeof getYouTubeVideoId !== 'undefined' ? getYouTubeVideoId : undefined;
    window.showYouTubeEmbedFallback = typeof showYouTubeEmbedFallback !== 'undefined' ? showYouTubeEmbedFallback : undefined;
    window.loadYouTubeVideo = typeof loadYouTubeVideo !== 'undefined' ? loadYouTubeVideo : undefined;
  } catch (err) {
    console.error('[GeminiTrans Error Boundary - Tab Video]', err);
    if (window.showToast) {
      window.showToast('Lỗi khởi tạo module Tab Video: ' + err.message, 'error');
    }
  }
})(window, document);
