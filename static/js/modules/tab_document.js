// ============================================================================
// GEMINITRANS MODULE: Tab Document
// Error Boundary: Isolated execution - does not affect other tabs
// ============================================================================
(function(window, document) {
  'use strict';
  try {
document.addEventListener('DOMContentLoaded', () => {
        const docSource = document.getElementById('doc-source-editor');
        const docTarget = document.getElementById('doc-target-editor');
        const docStatus = document.getElementById('doc-status');
        const docFileInput = document.getElementById('doc-file-input');
        let currentFilename = "";
        let debounceTimer;

        // Debounce function
        const debounce = (func, delay) => {
            return (...args) => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => func.apply(this, args), delay);
            };
        };

        const updateCounters = () => {
            document.getElementById('doc-source-counter').innerText = `${docSource.innerHTML.length} ký tự`;
            document.getElementById('doc-target-counter').innerText = `${docTarget.innerHTML.length} ký tự`;
        };

        const triggerTranslation = async () => {
            const text = docSource.innerHTML.trim();
            if (!text) return;
            
            docStatus.innerText = "Đang dịch...";
            docStatus.className = "text-xs font-medium px-3 py-1 rounded-full bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 animate-pulse";

            try {
                const response = await fetch('/api/translate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        text: text,
                        source_lang: document.getElementById('doc-source-lang').value,
                        target_lang: document.getElementById('doc-target-lang').value,
                        tier: document.getElementById('doc-model-tier').value,
                        stream: false
                    })
                });
                const data = await response.json();
                if (data.translated_text) {
                    docTarget.innerHTML = data.translated_text;
                    updateCounters();
                }
                docStatus.innerText = "Đã cập nhật";
                docStatus.className = "text-xs font-medium px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
                setTimeout(() => {
                    docStatus.innerText = "Sẵn sàng";
                    docStatus.className = "text-xs font-medium px-3 py-1 rounded-full bg-slate-700 text-slate-300 border border-slate-600";
                }, 2000);
            } catch (err) {
                console.error(err);
                docStatus.innerText = "Lỗi kết nối";
            }
        };

        docSource.addEventListener('input', () => {
            updateCounters();
            if (document.getElementById('doc-live-sync').checked) {
                debounce(triggerTranslation, 650)();
            }
        });

        docTarget.addEventListener('input', updateCounters);

        document.getElementById('doc-translate-now').addEventListener('click', triggerTranslation);

        document.getElementById('doc-swap-lang').addEventListener('click', () => {
            const s = document.getElementById('doc-source-lang');
            const t = document.getElementById('doc-target-lang');
            [s.value, t.value] = [t.value, s.value];
            const sVal = docSource.innerHTML;
            docSource.innerHTML = docTarget.innerHTML;
            docTarget.innerHTML = sVal;
            updateCounters();
        });

        document.getElementById('doc-clear-all').addEventListener('click', () => {
            if(confirm("Xóa toàn bộ nội dung?")) {
                docSource.innerHTML = "";
                docTarget.innerHTML = "";
                updateCounters();
            }
        });

        document.getElementById('doc-copy-target').addEventListener('click', () => {
            navigator.clipboard.writeText(docTarget.innerHTML);
            alert("Đã sao chép bản dịch!");
        });

        // File Handling
        const dropzone = document.getElementById('doc-dropzone');
        dropzone.addEventListener('click', () => docFileInput.click());
        
        docFileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            currentFilename = file.name;
            
            const formData = new FormData();
            formData.append('file', file);
            
            docStatus.innerText = "Đang nạp tệp...";
            try {
                const res = await fetch('/api/document/extract', { method: 'POST', body: formData });
                const data = await res.json();
                if (data.text) {
                    docSource.innerHTML = data.html || data.text;
                    document.getElementById('doc-file-badge').classList.remove('hidden');
                    document.getElementById('doc-upload-prompt').classList.add('hidden');
                    document.getElementById('doc-file-info').innerText = `${file.name} (${(file.size/1024).toFixed(1)} KB)`;
                    updateCounters();
                    triggerTranslation();
                }
            } catch (err) { alert("Lỗi nạp tệp"); }
        });

        document.getElementById('doc-remove-file').addEventListener('click', (e) => {
            e.stopPropagation();
            docFileInput.value = "";
            document.getElementById('doc-file-badge').classList.add('hidden');
            document.getElementById('doc-upload-prompt').classList.remove('hidden');
        });

        window.exportDoc = async (fmt) => {
            const content = docTarget.innerHTML;
            if (!content) return alert("Không có nội dung để xuất");
            
            try {
                const res = await fetch('/api/document/export-edited', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        content: content,
                        format: fmt,
                        filename: currentFilename || "translated_doc"
                    })
                });
                const blob = await res.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                const disposition = res.headers.get('Content-Disposition');
                let filename = `export.${fmt}`;
                if (disposition && disposition.indexOf('filename=') !== -1) {
                    filename = disposition.split('filename=')[1].replace(/"/g, '');
                }
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                a.remove();
            } catch (err) { alert("Lỗi khi xuất file"); }
        };

        if (window.lucide) lucide.createIcons();
    });


    // Expose functions to window for HTML inline event handlers
    window.debounce = typeof debounce !== 'undefined' ? debounce : undefined;
    window.updateCounters = typeof updateCounters !== 'undefined' ? updateCounters : undefined;
    window.triggerTranslation = typeof triggerTranslation !== 'undefined' ? triggerTranslation : undefined;
  } catch (err) {
    console.error('[GeminiTrans Error Boundary - Tab Document]', err);
    if (window.showToast) {
      window.showToast('Lỗi khởi tạo module Tab Document: ' + err.message, 'error');
    }
  }
})(window, document);
