// ============================================================================
// GEMINITRANS MODULE: Tab Audio
// Error Boundary: Isolated execution - does not affect other tabs
// ============================================================================
(function(window, document) {
  'use strict';
  try {
    // ==========================================
    // TAB 3: AUDIO TRANSCRIBE
    // ==========================================
    async function toggleRecord() {
      const btn = document.getElementById('btn-record');
      const status = document.getElementById('record-status');
      const timer = document.getElementById('record-timer');

      if (!mediaRecorder || mediaRecorder.state === 'inactive') {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          mediaRecorder = new MediaRecorder(stream);
          const chunks = [];
          mediaRecorder.ondataavailable = e => chunks.push(e.data);
          mediaRecorder.onstop = () => {
            audioBlob = new Blob(chunks, { type: 'audio/mp3' });
            document.getElementById('audio-file-name').innerText = `Record (${recordSeconds}s)`;
            status.innerText = t('record_done');
          };
          mediaRecorder.start();
          recordSeconds = 0;
          recordInterval = setInterval(() => {
            recordSeconds++;
            timer.innerText = `${String(Math.floor(recordSeconds / 60)).padStart(2, '0')}:${String(recordSeconds % 60).padStart(2, '0')}`;
          }, 1000);
          btn.className = "w-16 h-16 rounded-[10px] bg-red-600 text-white animate-pulse flex items-center justify-center mx-auto transition cursor-pointer";
          status.innerText = t('record_listening');
        } catch (err) {
          alert("Microphone error: " + err.message);
        }
      } else {
        mediaRecorder.stop();
        clearInterval(recordInterval);
        btn.className = "w-16 h-16 rounded-[10px] bg-red-500/20 text-red-400 border border-red-500/30 flex items-center justify-center mx-auto transition cursor-pointer";
      }
    }
    function handleAudioUpload(e) {
      const file = e.target.files[0];
      if (file) {
        audioBlob = file;
        document.getElementById('audio-file-name').innerText = `File: ${file.name} (${(file.size/1024/1024).toFixed(2)} MB)`;
      }
    }
    async function startTranscribe() {
      if (!audioBlob) return alert(t('alert_no_audio'));
      const out = document.getElementById('transcribe-output');
      out.innerHTML = `<div class="text-indigo-400 flex items-center gap-2"><span class="w-2.5 h-2.5 status-dot bg-indigo-400 animate-ping"></span> ${t('transcribe_analyzing')}</div>`;
      const form = new FormData();
      form.append('file', audioBlob, 'audio.mp3');
      form.append('translate_to_vi', true);
      try {
        const res = await fetch('/api/transcribe', { method: 'POST', body: form });
        const data = await res.json();
        out.innerText = data.result || JSON.stringify(data);
      } catch (err) {
        out.innerText = "Error: " + err.message;
      } finally {
        fetchPoolStatus();
      }
    }
    function copyTranscribeText() {
      navigator.clipboard.writeText(document.getElementById('transcribe-output').innerText);
      alert(t('alert_copied'));
    }

    // Restore Dual Subtitles preference from localStorage
    try {
      const savedDual = localStorage.getItem('geminitrans_dual_sub');
      const dualToggle = document.getElementById('dual-sub-toggle');
      if (dualToggle && savedDual !== null) {
        dualToggle.checked = (savedDual === '1');
      }
    } catch (e) {}


    // ==========================================


    // Expose functions to window for HTML inline event handlers
    window.toggleRecord = typeof toggleRecord !== 'undefined' ? toggleRecord : undefined;
    window.handleAudioUpload = typeof handleAudioUpload !== 'undefined' ? handleAudioUpload : undefined;
    window.startTranscribe = typeof startTranscribe !== 'undefined' ? startTranscribe : undefined;
    window.copyTranscribeText = typeof copyTranscribeText !== 'undefined' ? copyTranscribeText : undefined;
  } catch (err) {
    console.error('[GeminiTrans Error Boundary - Tab Audio]', err);
    if (window.showToast) {
      window.showToast('Lỗi khởi tạo module Tab Audio: ' + err.message, 'error');
    }
  }
})(window, document);
