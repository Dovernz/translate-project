import os
import shutil
import re
from pathlib import Path

# Cấu hình đường dẫn
BASE_DIR = Path(r"d:\Thành\Translate\CODE")
APP_PY_PATH = BASE_DIR / "app.py"
INDEX_HTML_PATH = BASE_DIR / "templates" / "index.html"

def backup_file(file_path):
    """Tạo bản sao lưu cho tệp trước khi sửa đổi."""
    if file_path.exists():
        backup_path = file_path.with_suffix(file_path.suffix + ".bak")
        shutil.copy2(file_path, backup_path)
        print(f"[INFO] Đã sao lưu: {file_path} -> {backup_path}")
        return True
    return False

def patch_app_py():
    print(f"[PROCESS] Đang cập nhật {APP_PY_PATH}...")
    if not APP_PY_PATH.exists():
        print(f"[ERROR] Không tìm thấy {APP_PY_PATH}")
        return

    with open(APP_PY_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Thêm import
    if "from core.document_helper import translate_document" not in content:
        content = "from core.document_helper import translate_document\n" + content

    # 2. Thêm DOCS_OUTPUT_DIR sau OUTPUT_DIR
    if "DOCS_OUTPUT_DIR" not in content:
        docs_dir_code = '\nDOCS_OUTPUT_DIR = OUTPUT_DIR / "documents"\nDOCS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)\n'
        content = re.sub(r"(OUTPUT_DIR = .*?\n)", r"\1" + docs_dir_code, content)

    # 3. Cập nhật/Thêm các endpoint
    # Xóa endpoint cũ nếu có để ghi đè
    content = re.sub(r"@app\.post\(\"/api/document/extract\"\).*?def extract_document.*?\n(?=@app|\nif __name__)", "", content, flags=re.DOTALL)
    
    new_endpoints = """
@app.post("/api/document/extract")
async def extract_document(file: UploadFile = File(...)):
    try:
        ext = file.filename.split('.')[-1].lower()
        content = await file.read()
        preview_text = ""
        
        if ext == 'docx':
            import docx
            doc = docx.Document(io.BytesIO(content))
            preview_text = "\\n".join([p.text for p in doc.paragraphs[:20]])
        elif ext == 'pdf':
            import fitz
            doc = fitz.open(stream=content, filetype="pdf")
            preview_text = "\\n".join([page.get_text() for page in doc[:3]])
        elif ext in ['txt', 'md', 'srt']:
            preview_text = content.decode('utf-8', errors='ignore')[:2000]
            
        return {"success": True, "preview": preview_text, "filename": file.filename}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/document/translate-stream")
async def translate_document_stream(
    file: UploadFile = File(...),
    source_lang: str = Form(...),
    target_lang: str = Form(...),
    tier: str = Form("free")
):
    async def event_generator():
        doc_id = str(uuid.uuid4())
        temp_dir = DOCS_OUTPUT_DIR / doc_id
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = temp_dir / file.filename
        with open(file_path, "wb") as f:
            f.write(await file.read())

        try:
            # Queue để nhận progress từ core
            queue = asyncio.Queue()
            
            # Hàm callback để đẩy vào queue
            def progress_callback(data):
                asyncio.run_coroutine_threadsafe(queue.put(data), asyncio.get_event_loop())

            # Chạy translation trong thread riêng
            task = asyncio.create_task(translate_document(
                file_path, source_lang, target_lang, tier, progress_callback
            ))

            while True:
                data = await queue.get()
                if data["type"] == "done":
                    # Di chuyển file kết quả vào thư mục output
                    out_filename = data["filename"]
                    yield f"data: {json.dumps(data)}\\n\\n"
                    break
                elif data["type"] == "error":
                    yield f"data: {json.dumps(data)}\\n\\n"
                    break
                else:
                    yield f"data: {json.dumps(data)}\\n\\n"
            
            yield "data: [DONE]\\n\\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\\n\\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/api/document/translate")
async def translate_document_sync(
    file: UploadFile = File(...),
    source_lang: str = Form(...),
    target_lang: str = Form(...),
    tier: str = Form("free")
):
    # Fallback non-streaming
    return {"message": "Vui lòng sử dụng endpoint stream để nhận kết quả."}

@app.get("/api/document/download/{doc_id}/{filename}")
async def download_document(doc_id: str, filename: str):
    file_path = DOCS_OUTPUT_DIR / doc_id / filename
    if not file_path.exists():
        return {"error": "File không tồn tại"}
    return FileResponse(
        path=file_path, 
        filename=filename,
        media_type='application/octet-stream'
    )
"""
    # Chèn endpoint vào trước khối if __name__
    if 'if __name__ == "__main__":' in content:
        content = content.replace('if __name__ == "__main__":', new_endpoints + '\nif __name__ == "__main__":')
    else:
        content += new_endpoints

    with open(APP_PY_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    print("[SUCCESS] Đã cập nhật app.py")

def patch_index_html():
    print(f"[PROCESS] Đang cập nhật {INDEX_HTML_PATH}...")
    if not INDEX_HTML_PATH.exists():
        print(f"[ERROR] Không tìm thấy {INDEX_HTML_PATH}")
        return

    with open(INDEX_HTML_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Thay thế khối section tab-document
    new_section = """
        <section id="tab-document" class="tab-content hidden animate-fade-in">
            <div class="max-w-5xl mx-auto">
                <!-- Drop Zone -->
                <div id="doc-drop-zone" class="relative border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-2xl p-12 text-center hover:border-blue-500 dark:hover:border-blue-400 transition-all bg-white dark:bg-slate-800 shadow-sm group cursor-pointer">
                    <input type="file" id="doc-file-input" class="hidden" accept=".docx,.pdf,.txt,.srt,.md">
                    <div class="flex flex-col items-center">
                        <div class="w-20 h-20 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                            <i data-lucide="cloud-upload" class="w-10 h-10"></i>
                        </div>
                        <h3 class="text-xl font-semibold mb-2 text-slate-800 dark:text-slate-100">Kéo & thả tài liệu vào đây</h3>
                        <p class="text-slate-500 dark:text-slate-400 mb-4">Hoặc nhấp để duyệt file từ máy tính</p>
                        <div class="flex flex-wrap justify-center gap-2 mb-6">
                            <span class="px-3 py-1 bg-slate-100 dark:bg-slate-700 text-xs font-medium rounded-full">.DOCX</span>
                            <span class="px-3 py-1 bg-slate-100 dark:bg-slate-700 text-xs font-medium rounded-full">.PDF</span>
                            <span class="px-3 py-1 bg-slate-100 dark:bg-slate-700 text-xs font-medium rounded-full">.SRT</span>
                            <span class="px-3 py-1 bg-slate-100 dark:bg-slate-700 text-xs font-medium rounded-full">.MD</span>
                            <span class="px-3 py-1 bg-slate-100 dark:bg-slate-700 text-xs font-medium rounded-full">.TXT</span>
                        </div>
                        <div class="flex items-center text-emerald-600 dark:text-emerald-400 text-sm font-medium">
                            <i data-lucide="shield-check" class="w-4 h-4 mr-1.5"></i>
                            Bảo toàn 100% định dạng gốc
                        </div>
                    </div>
                </div>

                <!-- File Card (Hidden by default) -->
                <div id="doc-file-card" class="hidden mt-6 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 shadow-sm">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-4">
                            <div id="doc-icon-wrapper" class="p-3 bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 rounded-lg">
                                <i data-lucide="file-text" class="w-8 h-8"></i>
                            </div>
                            <div>
                                <h4 id="doc-filename" class="font-medium text-slate-800 dark:text-slate-100 truncate max-w-xs">filename.docx</h4>
                                <p id="doc-filesize" class="text-sm text-slate-500">0 KB</p>
                            </div>
                        </div>
                        <div class="flex space-x-2">
                            <button onclick="resetDocumentTranslator()" class="p-2 text-slate-400 hover:text-red-500 transition-colors">
                                <i data-lucide="trash-2" class="w-5 h-5"></i>
                            </button>
                        </div>
                    </div>
                    
                    <!-- Progress Bar -->
                    <div id="doc-progress-container" class="hidden mt-6">
                        <div class="flex justify-between text-sm mb-2">
                            <span id="doc-status-text" class="text-blue-600 dark:text-blue-400 font-medium italic">Đang chuẩn bị...</span>
                            <span id="doc-progress-percent" class="font-bold">0%</span>
                        </div>
                        <div class="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-2.5 overflow-hidden">
                            <div id="doc-progress-bar" class="bg-blue-600 h-full transition-all duration-300" style="width: 0%"></div>
                        </div>
                    </div>

                    <div class="mt-6 flex justify-center">
                        <button id="btn-start-doc-translate" onclick="startDocumentTranslation()" class="px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-semibold flex items-center shadow-lg shadow-blue-500/20 transition-all">
                            <i data-lucide="languages" class="w-5 h-5 mr-2"></i>
                            Bắt đầu dịch tài liệu
                        </button>
                    </div>
                </div>

                <!-- Dual View Preview -->
                <div id="doc-preview-area" class="hidden mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div class="flex flex-col">
                        <label class="text-sm font-bold text-slate-500 mb-2 uppercase tracking-wider">Nguồn gốc</label>
                        <div id="doc-source-preview" class="bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-xl p-4 h-80 overflow-y-auto text-sm text-slate-600 dark:text-slate-300 font-mono"></div>
                    </div>
                    <div class="flex flex-col">
                        <label class="text-sm font-bold text-slate-500 mb-2 uppercase tracking-wider">Bản dịch xem trước</label>
                        <div id="doc-target-preview" class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 h-80 overflow-y-auto text-sm text-slate-700 dark:text-slate-200 font-mono"></div>
                    </div>
                </div>

                <!-- Result Actions -->
                <div id="doc-result-actions" class="hidden mt-8 flex flex-col items-center space-y-4">
                    <div class="p-6 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-2xl text-center w-full">
                        <div class="inline-flex items-center justify-center w-12 h-12 bg-emerald-100 dark:bg-emerald-800 text-emerald-600 dark:text-emerald-400 rounded-full mb-4">
                            <i data-lucide="check-circle" class="w-6 h-6"></i>
                        </div>
                        <h3 class="text-lg font-bold text-slate-800 dark:text-slate-100 mb-1">Dịch hoàn tất!</h3>
                        <p class="text-slate-500 dark:text-slate-400 mb-6">Tài liệu của bạn đã sẵn sàng để tải về với định dạng gốc.</p>
                        
                        <div class="flex flex-wrap justify-center gap-4">
                            <button id="btn-download-doc" onclick="downloadDocumentResult()" class="px-8 py-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold flex items-center shadow-xl shadow-emerald-500/20 transition-all transform hover:-translate-y-1">
                                <i data-lucide="download" class="w-6 h-6 mr-2"></i>
                                Tải về tài liệu (.docx)
                            </button>
                            <button onclick="resetDocumentTranslator()" class="px-8 py-4 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-xl font-bold hover:bg-slate-300 dark:hover:bg-slate-600 transition-all">
                                Dịch file mới
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Switch to Text -->
                <div class="mt-12 text-center">
                    <button onclick="switchTab('text')" class="text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center font-medium">
                        <i data-lucide="type" class="w-4 h-4 mr-1.5"></i>
                        Hoặc chuyển sang dịch văn bản trực tiếp
                    </button>
                </div>
            </div>
        </section>
"""
    content = re.sub(r'<section id="tab-document".*?</section>', new_section, content, flags=re.DOTALL)

    # 2. Bổ sung JavaScript
    new_js = """
    // Document Translation Logic
    let currentDocFile = null;
    let translatedDocInfo = null;

    const docDropZone = document.getElementById('doc-drop-zone');
    const docFileInput = document.getElementById('doc-file-input');
    const docFileCard = document.getElementById('doc-file-card');
    const docPreviewArea = document.getElementById('doc-preview-area');
    const docResultActions = document.getElementById('doc-result-actions');

    // Drag & Drop events
    if(docDropZone) {
        docDropZone.addEventListener('click', () => docFileInput.click());
        docDropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            docDropZone.classList.add('border-blue-500', 'bg-blue-50', 'dark:bg-blue-900/20');
        });
        ['dragleave', 'drop'].forEach(evt => {
            docDropZone.addEventListener(evt, () => {
                docDropZone.classList.remove('border-blue-500', 'bg-blue-50', 'dark:bg-blue-900/20');
            });
        });
        docDropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            const files = e.dataTransfer.files;
            if(files.length) handleDocFileSelect(files[0]);
        });
    }

    if(docFileInput) {
        docFileInput.addEventListener('change', (e) => {
            if(e.target.files.length) handleDocFileSelect(e.target.files[0]);
        });
    }

    async function handleDocFileSelect(file) {
        const allowedExts = ['docx', 'pdf', 'txt', 'srt', 'md'];
        const ext = file.name.split('.').pop().toLowerCase();
        
        if(!allowedExts.includes(ext)) {
            showToast('Định dạng file không được hỗ trợ', 'error');
            return;
        }

        currentDocFile = file;
        docDropZone.classList.add('hidden');
        docFileCard.classList.remove('hidden');
        
        document.getElementById('doc-filename').textContent = file.name;
        document.getElementById('doc-filesize').textContent = (file.size / 1024).toFixed(1) + ' KB';
        
        // Extract preview
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const res = await fetch('/api/document/extract', { method: 'POST', body: formData });
            const data = await res.json();
            if(data.success) {
                docPreviewArea.classList.remove('hidden');
                document.getElementById('doc-source-preview').textContent = data.preview;
                document.getElementById('doc-target-preview').textContent = "Bản dịch sẽ xuất hiện tại đây...";
            }
        } catch(e) { console.error(e); }
        
        lucide.createIcons();
    }

    async function startDocumentTranslation() {
        if(!currentDocFile) return;
        
        const btn = document.getElementById('btn-start-doc-translate');
        const progressContainer = document.getElementById('doc-progress-container');
        const progressBar = document.getElementById('doc-progress-bar');
        const progressPercent = document.getElementById('doc-progress-percent');
        const statusText = document.getElementById('doc-status-text');
        
        btn.disabled = true;
        btn.classList.add('opacity-50', 'cursor-not-allowed');
        progressContainer.classList.remove('hidden');
        
        const formData = new FormData();
        formData.append('file', currentDocFile);
        formData.append('source_lang', document.getElementById('source-lang').value);
        formData.append('target_lang', document.getElementById('target-lang').value);
        formData.append('tier', 'free');

        try {
            const response = await fetch('/api/document/translate-stream', {
                method: 'POST',
                body: formData
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value);
                const lines = chunk.split('\\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataStr = line.replace('data: ', '').trim();
                        if (dataStr === '[DONE]') break;
                        
                        try {
                            const data = JSON.parse(dataStr);
                            if (data.type === 'progress') {
                                progressBar.style.width = data.percent + '%';
                                progressPercent.textContent = data.percent + '%';
                                statusText.textContent = data.message;
                                if(data.preview) {
                                    document.getElementById('doc-target-preview').textContent = data.preview;
                                }
                            } else if (data.type === 'done') {
                                translatedDocInfo = data;
                                finishDocTranslation();
                            } else if (data.type === 'error') {
                                showToast(data.message, 'error');
                                btn.disabled = false;
                                btn.classList.remove('opacity-50');
                            }
                        } catch (e) {}
                    }
                }
            }
        } catch (error) {
            showToast('Lỗi kết nối server', 'error');
            btn.disabled = false;
        }
    }

    function finishDocTranslation() {
        document.getElementById('doc-progress-container').classList.add('hidden');
        document.getElementById('btn-start-doc-translate').parentElement.classList.add('hidden');
        docResultActions.classList.remove('hidden');
        
        const btnDownload = document.getElementById('btn-download-doc');
        btnDownload.innerHTML = `<i data-lucide="download" class="w-6 h-6 mr-2"></i> Tải về ${translatedDocInfo.filename}`;
        
        if(translatedDocInfo.preview_text) {
            document.getElementById('doc-target-preview').textContent = translatedDocInfo.preview_text;
        }
        
        lucide.createIcons();
        showToast('Dịch tài liệu thành công!', 'success');
    }

    function downloadDocumentResult() {
        if(!translatedDocInfo) return;
        window.location.href = translatedDocInfo.download_url;
    }

    function resetDocumentTranslator() {
        currentDocFile = null;
        translatedDocInfo = null;
        docDropZone.classList.remove('hidden');
        docFileCard.classList.add('hidden');
        docPreviewArea.classList.add('hidden');
        docResultActions.classList.add('hidden');
        document.getElementById('doc-file-input').value = '';
        document.getElementById('btn-start-doc-translate').parentElement.classList.remove('hidden');
        document.getElementById('btn-start-doc-translate').disabled = false;
        document.getElementById('btn-start-doc-translate').classList.remove('opacity-50');
        document.getElementById('doc-progress-bar').style.width = '0%';
        lucide.createIcons();
    }
    """
    
    # Chèn JS vào trước thẻ đóng </body> hoặc cuối script hiện có
    if "</script>" in content:
        content = content.replace("</script>", new_js + "\n</script>")
    else:
        content = content.replace("</body>", f"<script>{new_js}</script></body>")

    with open(INDEX_HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    print("[SUCCESS] Đã cập nhật index.html")

def main():
    print("--- BẮT ĐẦU PATCH GEMINITRANS ---")
    
    # Đảm bảo thư mục tồn tại
    if not BASE_DIR.exists():
        print(f"[ERROR] Thư mục gốc {BASE_DIR} không tồn tại!")
        return

    # Sao lưu
    backup_file(APP_PY_PATH)
    backup_file(INDEX_HTML_PATH)

    # Thực hiện patch
    try:
        patch_app_py()
        patch_index_html()
        print("\n--- HOÀN TẤT CẬP NHẬT ---")
        print("Lưu ý: Đảm bảo bạn đã cài đặt các thư viện bổ sung: pip install python-docx PyMuPDF fitz")
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Có lỗi xảy ra: {e}")

if __name__ == "__main__":
    main()