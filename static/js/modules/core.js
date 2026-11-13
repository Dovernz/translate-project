// ============================================================================
// GEMINITRANS MODULE: Core Management
// Error Boundary: Isolated execution - does not affect other tabs
// ============================================================================
(function(window, document) {
  'use strict';
  try {

    // Core shared state & fallbacks
    window.poolData = window.poolData || null;
    let poolData = window.poolData;
    window.currentVideoId = window.currentVideoId || null;
    let currentVideoId = window.currentVideoId;
    window.currentVideoSubtitles = window.currentVideoSubtitles || [];
    let currentVideoSubtitles = window.currentVideoSubtitles;

// ==========================================
    // I18N SYSTEM (TIẾNG VIỆT & ENGLISH)
    // ==========================================
    const I18N = {
      vi: {
        header_tagline: "",
        pool_loading: "Pool: Đang tải...",
        pool_status: "7 Keys: #{pointer}",
        tab_video: "Video",
        tab_translate: "Tài liệu",
        tab_document: "Tài liệu",
        tab_web: "Dịch Web",
        tab_transcribe: "Giọng nói",
        tab_manga: "Dịch Truyện",
        video_opt1_title: "Tải tệp video",
        video_opt1_formats: "MP4, MOV, MKV, WEBM",
        video_opt1_btn: "Chọn file",
        video_opt1_btn_change: "Đổi file",
        video_opt1_uploading: "Đang tải lên...",
        video_opt1_success: "Đã tải xong!",
        video_opt2_title: "Dán link YouTube hoặc video",
        video_opt2_formats: "YouTube, Direct MP4",
        video_opt2_placeholder: "https://www.youtube.com/watch?v=...",
        video_opt2_btn: "Nạp",
        player_placeholder: "Chọn file video hoặc dán link",
        badge_no_video: "Chưa tải video",
        badge_video_prefix: "Video: ",
        badge_url_loading: "Đang tải video...",
        badge_url_loaded: "Đã nạp: ",
        badge_youtube_embed: "Đang phát bằng YouTube",
        youtube_embed_title: "Trình phát video YouTube",
        youtube_download_limited: "Máy chủ hiện bị YouTube giới hạn nên không thể nạp video để tạo phụ đề. Bạn vẫn có thể xem bằng trình phát YouTube bên dưới; muốn tạo phụ đề, hãy tải tệp video lên từ thiết bị.",
        tab_audio_capture_title: "Thu âm thanh tab đang phát",
        tab_audio_capture_help: "Chia sẻ tab/màn hình và bật chia sẻ âm thanh. Không dùng micro. Cần cấp quyền thủ công; một số trình duyệt di động không cung cấp audio track.",
        tab_audio_capture_start: "Chọn tab có video",
        tab_audio_capture_stop: "Dừng thu",
        tab_audio_capture_idle: "Chưa chia sẻ tab âm thanh.",
        tab_audio_capture_select: "Trong hộp thoại chia sẻ, chọn tab video và bật chia sẻ âm thanh.",
        tab_audio_capture_no_audio: "Trình duyệt không cấp audio track. Hãy thử trình duyệt desktop hỗ trợ chia sẻ âm thanh tab; micro không được dùng thay thế.",
        tab_audio_capture_active: "Đang thu âm thanh tab. Gemini xử lý theo các đoạn ngắn; độ trễ phụ thuộc mạng và AI.",
        tab_audio_capture_stopped: "Đã dừng thu âm thanh tab.",
        tab_audio_capture_queue_full: "Gemini xử lý chậm hơn tốc độ thu; đã tự dừng để tránh mất các đoạn âm thanh đang chờ.",
        tab_audio_capture_unsupported: "Trình duyệt này không hỗ trợ chia sẻ màn hình/tab có âm thanh.",
        tab_audio_capture_error: "Không thể bắt âm thanh tab: {error}",
        tab_audio_capture_empty: "Đang thu nhưng chưa phát hiện lời thoại rõ ràng.",
        youtube_captions_loading: "Đang thử lấy phụ đề có sẵn từ YouTube...",
        youtube_captions_ready: "Đã lấy và dịch {count} câu phụ đề. Phát video để xem phụ đề đồng bộ.",
        youtube_captions_unavailable: "Không lấy được transcript công khai. Bạn vẫn có thể xem video; để tạo phụ đề, hãy tải video lên hoặc dùng thu âm thanh tab nếu trình duyệt hỗ trợ.",
        btn_auto_sub: "AI tạo Sub",
        btn_auto_sub_scanning: "Đang quét sub...",
        btn_export_video: "Xuất Video kèm Sub",
        dual_sub_title: "Song ngữ",
        cache_loaded_badge: "Đã nạp từ bộ nhớ đệm",
        btn_rescan_cache: "Quét lại",
        btn_fullscreen: "Toàn màn hình",
        customizer_title: "Tùy chỉnh phụ đề",
        realtime_preview_note: "Xem trước trực tiếp",
        mask_old_sub: "Che sub cũ",
        opacity_label: "Độ mờ đục:",
        color_title: "Màu sắc",
        text_color_label: "Màu chữ:",
        bg_color_label: "Màu nền:",
        font_size_label: "Cỡ chữ",
        margin_label: "Vị trí đáy",
        timeline_title: "Phụ đề",
        timeline_empty: "Chưa có phụ đề. Tải video lên để tự động tạo phụ đề.",
        timeline_count_cues: "{count} câu",
        timeline_scanning_msg: "Gemini đang nhận diện thoại & mốc thời gian...",
        timeline_scanning_sub: "Smart Key Pool tự động luân chuyển hạn ngạch",
        timeline_no_subs: "Không phát hiện thấy câu thoại trong video.",
        export_ready_title: "Phụ đề & Video đã sẵn sàng:",
        export_subtitles_only: "Phụ đề đã sẵn sàng:",
        btn_client_burn: "Xuất Zero-Storage",
        btn_server_burn: "Xuất Server FFmpeg",
        btn_dl_srt: "Tải .SRT",
        btn_dl_vtt: "Tải .VTT",
        btn_dl_video: "Tải MP4 Hardsub",
        btn_clean_server: "Dọn Server (0-Byte)",
        lang_auto: "Tự nhận diện ngôn ngữ",
        tier_label: "Model:",
        tier_bulk: "Gemini 3.5 Flash Lite (Bulk)",
        tier_ultra: "Gemma 4 26B (Ultra)",
        tier_standard: "Gemini 3.6 Flash (Standard)",
        tier_deep: "Gemini 3.8 Flash (Deep)",
        file_upload_btn: "Nạp file",
        src_box_title: "Văn bản gốc",
        src_placeholder: "Nhập văn bản cần dịch...",
        char_count_format: "{count} ký tự",
        btn_clear: "Xóa",
        btn_translate: "Dịch",
        target_box_title: "Bản dịch",
        streaming_status: "Đang dịch...",
        target_placeholder: "Bản dịch sẽ hiển thị ở đây...",
        btn_copy: "Sao chép",
        btn_download_txt: "Tải về (.txt)",
        transcribe_title: "Ghi âm hoặc tải file",
        record_idle: "Bấm micro để bắt đầu nói",
        record_listening: "Đang lắng nghe...",
        record_done: "Đã ghi âm xong. Bấm nút để phân tích!",
        record_or: "- hoặc -",
        btn_audio_file: "Chọn file âm thanh",
        btn_start_transcribe: "Phân tích âm thanh",
        transcribe_result_title: "Kết quả phiên âm",
        transcribe_placeholder: "Kết quả sẽ hiển thị tại đây...",
        transcribe_analyzing: "Gemini đang phân tích âm thanh...",
        modal_export_title: "Tùy chọn xuất video Hardsub",
        modal_export_desc: "Chọn phương thức in phụ đề phù hợp",
        opt_client_title: "Xuất trực tiếp trên trình duyệt",
        badge_recommended: "Khuyên dùng",
        opt_client_desc: "Xử lý video qua Canvas & MediaRecorder API trực tiếp trên máy của bạn. Tốc độ cao, bảo mật và không lưu trữ trên máy chủ.",
        opt_server_title: "Xuất qua máy chủ FFmpeg (MP4 H.264)",
        opt_server_desc: "Mã hóa H.264 qua FFmpeg trên máy chủ. Tự động xóa tệp tạm sau khi hoàn tất.",
        opt_subs_title: "Tải tệp phụ đề (.SRT / .VTT)",
        opt_subs_desc: "Tải tệp phụ đề chuẩn để sử dụng với các trình phát ngoại tuyến mà không cần mã hóa lại video.",
        burn_modal_title: "Đang Xuất Video kèm Sub trên trình duyệt",
        burn_modal_desc: "Đang đọc video và in phụ đề trực tiếp qua Canvas & MediaRecorder API...",
        burn_init: "Đang khởi tạo burner...",
        burn_encoding: "Đang render & encode...",
        burn_done: "Hoàn tất! Đang tạo file...",
        burn_safe_note: "Video được xử lý trực tiếp trên trình duyệt của bạn, bảo mật dữ liệu và không lưu trữ trên máy chủ.",
        burn_success_alert: "Xuất video Hardsub thành công! File đã tải về máy.",
        btn_cancel: "Hủy",
        pool_modal_title: "Smart Key Pool",
        pool_modal_desc: "Cân bằng tải Round-Robin và điều phối hạn ngạch API thông minh",
        th_stt: "STT",
        th_project: "Cloud Project",
        th_key: "Khóa",
        th_status: "Trạng thái",
        th_cooldown: "Cooldown",
        th_requests: "Lượt gọi",
        pool_footer: "Tự động cách ly key khi gặp mã phản hồi 429",
        btn_refresh: "Làm mới",
        status_ready: "SẴN SÀNG",
        status_cooldown: "COOLDOWN ({sec}s)",
        status_ready_short: "Sẵn sàng",
        btn_menu_text: "Menu",
        drawer_subtitle: "Trung tâm điều khiển",
        drawer_section_nav: "Điều hướng chức năng",
        drawer_tab_video: "Video Subtitles",
        drawer_tab_translate: "Dịch tài liệu & văn bản",
        drawer_tab_document: "Dịch tài liệu & văn bản",
        drawer_tab_web: "Dịch trang web",
        drawer_tab_transcribe: "Giọng nói",
        drawer_tab_manga: "Dịch Truyện",
        drawer_section_pref: "Cài đặt giao diện",
        drawer_lang_title: "Ngôn ngữ giao diện",
        drawer_theme_title: "Chế độ hiển thị (Theme)",
        theme_menu_title: "Giao diện (Chế độ & Màu)",
        drawer_theme_title: "Giao diện (Chế độ & Màu)",
        mode_dark: "Chế độ Tối 🌙",
        mode_light: "Chế độ Sáng ☀️",
        mode_dark_short: "Tối 🌙",
        mode_light_short: "Sáng ☀️",
        accent_section_title: "Màu điểm nhấn (Accent):",
        theme_dark: "Tối",
        theme_light: "Sáng",
        drawer_section_pool: "Trạng thái AI Studio Pool",
        pool_ready_summary: "{ready} Cloud Keys Sẵn Sàng",
        pool_drawer_desc: "Tự động cân bằng tải API keys.",
        drawer_section_links: "Liên kết",
        alert_no_video: "Vui lòng chọn video trước!",
        alert_no_subs: "Vui lòng quét phụ đề trước khi xuất video!",
        video_target_lang_label: "Dịch sang:",
        multi_sub_title: "Đa ngôn ngữ",
        btn_translating_sub: "Đang dịch...",
        alert_clean_success: "Đã dọn dẹp sạch server! 0-byte tồn đọng.",
        alert_copied: "Đã sao chép!",
        alert_no_text: "Vui lòng nhập nội dung!",
        alert_no_audio: "Vui lòng ghi âm hoặc tải file âm thanh!",
        manga_opt1_title: "Tải lên ảnh hoặc tệp ZIP",
        manga_drag_prompt: "Kéo thả tệp ZIP hoặc chọn nhiều ảnh trang truyện",
        manga_drag_hint: "Tự động nhận diện thứ tự trang tự nhiên (page 1, 2, ... 10)",
        manga_btn_choose: "Chọn tệp",
        manga_opt2_title: "Nạp từ liên kết web hoặc ảnh",
        manga_opt2_desc: "Nhập địa chỉ URL chương truyện hoặc liên kết hình ảnh trực tiếp để nạp vào trình đọc.",
        manga_btn_load_url: "Nạp chapter",
        manga_target_lang_label: "Ngôn ngữ dịch:",
        manga_view_trans: "Bản dịch",
        manga_view_orig: "Bản gốc",
        manga_view_bilingual: "Bóng thoại",
        manga_btn_paste: "Dán ảnh (Ctrl+V)",
        manga_paste_hint: "Hỗ trợ dán trực tiếp từ Clipboard hoặc ảnh chụp màn hình",
        manga_view_split: "Song song",
        manga_hold_orig: "Giữ xem Gốc",
        manga_lightbox_btn: "Phóng to",
        manga_btn_translate_all: "Dịch toàn bộ Chapter",
        manga_btn_export_zip: "Tải tệp ZIP",
        manga_empty_title: "Chưa có trang nào",
        manga_empty_desc: "Nhấn Ctrl+V để dán ảnh, tải ảnh/ZIP hoặc nhập URL truyện để dịch",
        manga_prev_chapter: "Chương trước",
        manga_next_chapter: "Chương tiếp",
        manga_select_chapter: "-- Chọn Chương Truyện --",
        manga_btn_load_and_translate: "Đọc & Dịch Ngay",
        manga_btn_scan_series: "Quét Chapter",
        manga_auto_translate_switch: "Tự động dịch khi đổi chương",
        manga_webtoon_scroll: "Cuộn dọc Webtoon",
        manga_scroll_top: "Lên đầu trang",
        manga_chapter_badge: "Chương",
        submode_text: "Văn bản",
        submode_web: "Trang web (URL)",
        web_input_title: "Dịch trang web",
        web_input_desc: "Dịch toàn bộ trang web sang ngôn ngữ đã chọn và giữ nguyên cấu trúc bố cục, bảng biểu và giao diện gốc.",
        btn_web_translate: "Dịch Trang Web",
        web_view_trans: "Bản dịch",
        web_view_orig: "Bản gốc",
        web_view_split: "Song song",
        web_btn_quick_switch: "Đổi chế độ xem",
        web_sync_scroll: "Đồng bộ cuộn",
        web_empty_title: "Chưa có trang web nào được thêm",
        web_empty_desc: "Nhập URL tài liệu để dịch.",
      },
      en: {
        header_tagline: "",
        pool_loading: "Pool: Loading...",
        pool_status: "7 Keys: #{pointer}",
        tab_video: "Video",
        tab_translate: "Document",
        tab_document: "Document",
        tab_web: "Web Translate",
        tab_transcribe: "Voice",
        tab_manga: "Manga",
        drawer_tab_manga: "Manga Translator",
        manga_opt1_title: "Upload Images or Chapter ZIP",
        manga_drag_prompt: "Drag & drop ZIP or multiple page images",
        manga_drag_hint: "Auto natural sorting for page orders (page 1, 2, ... 10)",
        manga_btn_choose: "Choose files",
        manga_opt2_title: "Load from Web Link or Image URL",
        manga_opt2_desc: "Automatically extracts all chapter images from comic websites, or direct image links.",
        manga_btn_load_url: "Load chapter",
        manga_target_lang_label: "Target Language:",
        manga_view_trans: "Translated",
        manga_view_orig: "Original",
        manga_view_bilingual: "Tooltips",
        manga_btn_paste: "Paste Image (Ctrl+V)",
        manga_paste_hint: "Support direct paste from Clipboard or screenshot",
        manga_view_split: "Side-by-Side",
        manga_hold_orig: "Hold to view Original",
        manga_lightbox_btn: "Zoom / Lightbox",
        manga_btn_translate_all: "Translate Entire Chapter",
        manga_btn_export_zip: "Download Chapter ZIP",
        manga_empty_title: "No pages loaded yet",
        manga_empty_desc: "Press Ctrl+V to paste an image, upload images/ZIP, or enter a comic URL above to start",
        manga_prev_chapter: "Prev Chapter",
        manga_next_chapter: "Next Chapter",
        manga_select_chapter: "-- Select Chapter --",
        manga_btn_load_and_translate: "Read & Translate Now",
        manga_btn_scan_series: "Scan Chapters",
        manga_auto_translate_switch: "Auto translate on chapter change",
        manga_webtoon_scroll: "Webtoon Vertical Scroll",
        manga_scroll_top: "Back to top",
        manga_chapter_badge: "Chapter",
        submode_text: "Plain Text",
        submode_web: "Web Page (URL)",
        web_input_title: "Web Translator",
        web_input_desc: "Translate web pages while preserving layout, structure, and original styling.",
        btn_web_translate: "Translate Webpage",
        web_view_trans: "Translated",
        web_view_orig: "Original",
        web_view_split: "Side-by-Side",
        web_btn_quick_switch: "Toggle View",
        web_sync_scroll: "Sync Scroll",
        web_empty_title: "No web page loaded yet",
        web_empty_desc: "Enter an article or document URL above to translate the entire webpage while preserving its original design.",
        video_opt1_title: "Upload video (.mp4, .mkv, .mov)",
        video_opt1_formats: "MP4, MOV, MKV, WEBM",
        video_opt1_btn: "Choose file",
        video_opt1_btn_change: "Change file",
        video_opt1_uploading: "Uploading...",
        video_opt1_success: "Uploaded!",
        video_opt2_title: "Paste YouTube / Web stream link",
        video_opt2_formats: "YouTube, Direct MP4",
        video_opt2_placeholder: "https://www.youtube.com/watch?v=...",
        video_opt2_btn: "Load",
        player_placeholder: "Choose a video file or paste a link to start",
        badge_no_video: "No video loaded",
        badge_video_prefix: "Video: ",
        badge_url_loading: "Loading video...",
        badge_url_loaded: "Loaded: ",
        badge_youtube_embed: "Playing with YouTube",
        youtube_embed_title: "YouTube video player",
        youtube_download_limited: "YouTube is limiting requests from the server, so the video cannot be imported for subtitle generation. You can still watch it in the YouTube player below; upload a video file from your device to generate subtitles.",
        tab_audio_capture_title: "Capture audio from a playing tab",
        tab_audio_capture_help: "Share a tab/screen and enable audio sharing. No microphone is used. Permission is required; some mobile browsers do not provide an audio track.",
        tab_audio_capture_start: "Choose video tab",
        tab_audio_capture_stop: "Stop capture",
        tab_audio_capture_idle: "No tab audio is being shared.",
        tab_audio_capture_select: "In the sharing dialog, choose the video tab and enable audio sharing.",
        tab_audio_capture_no_audio: "The browser did not provide an audio track. Try a desktop browser that supports tab-audio sharing; the microphone is not used as a fallback.",
        tab_audio_capture_active: "Capturing tab audio. Gemini processes short segments; latency depends on network and AI.",
        tab_audio_capture_stopped: "Tab audio capture stopped.",
        tab_audio_capture_queue_full: "Gemini is processing slower than the capture rate; capture stopped to avoid silently dropping queued audio.",
        tab_audio_capture_unsupported: "This browser does not support screen/tab sharing with audio.",
        tab_audio_capture_error: "Could not capture tab audio: {error}",
        tab_audio_capture_empty: "Capturing audio, but no clear speech was detected yet.",
        youtube_captions_loading: "Trying to retrieve available YouTube captions...",
        youtube_captions_ready: "Retrieved and translated {count} caption cues. Play the video to see synchronized subtitles.",
        youtube_captions_unavailable: "Could not retrieve a public transcript. You can still watch the video; upload a video file or try tab-audio capture if the browser supports it.",
        btn_auto_sub: "AI Scan Sub",
        btn_auto_sub_scanning: "Scanning sub...",
        btn_export_video: "Export Hardsub",
        dual_sub_title: "Bilingual",
        cache_loaded_badge: "Cached (0 tokens)",
        btn_rescan_cache: "Rescan",
        btn_fullscreen: "Fullscreen",
        customizer_title: "Subtitle Settings",
        realtime_preview_note: "Live Preview",
        mask_old_sub: "Mask old sub",
        opacity_label: "Opacity:",
        color_title: "Colors",
        text_color_label: "Text:",
        bg_color_label: "Background:",
        font_size_label: "Font size",
        margin_label: "Bottom margin",
        timeline_title: "Subtitles",
        timeline_empty: "No subtitles yet. Upload a video to generate subtitles automatically.",
        timeline_count_cues: "{count} cues",
        timeline_scanning_msg: "Gemini is recognizing dialogue & timestamps...",
        timeline_scanning_sub: "Smart Key Pool with auto quota rotation",
        timeline_no_subs: "No dialogue detected in video.",
        export_ready_title: "Subtitles & Video ready:",
        export_subtitles_only: "Subtitles ready:",
        btn_client_burn: "Export Zero-Storage",
        btn_server_burn: "Export Server FFmpeg",
        btn_dl_srt: "Download .SRT",
        btn_dl_vtt: "Download .VTT",
        btn_dl_video: "Download Hardsub MP4",
        btn_clean_server: "Clean Server (0-Byte)",
        lang_auto: "Auto-detect language",
        tier_label: "Model:",
        tier_bulk: "Gemini 3.5 Flash Lite (Bulk)",
        tier_ultra: "Gemma 4 26B (Ultra)",
        tier_standard: "Gemini 3.6 Flash (Standard)",
        tier_deep: "Gemini 3.8 Flash (Deep)",
        file_upload_btn: "Upload file",
        src_box_title: "Source",
        src_placeholder: "Type text to translate...",
        char_count_format: "{count} characters",
        btn_clear: "Clear",
        btn_translate: "Translate",
        target_box_title: "Translation",
        streaming_status: "Translating...",
        target_placeholder: "Translation will appear here...",
        btn_copy: "Copy",
        btn_download_txt: "Download (.txt)",
        transcribe_title: "Record or upload file",
        record_idle: "Click microphone to start speaking",
        record_listening: "Listening...",
        record_done: "Recording done. Click button to analyze!",
        record_or: "- or -",
        btn_audio_file: "Choose audio file",
        btn_start_transcribe: "Analyze audio",
        transcribe_result_title: "Transcription result",
        transcribe_placeholder: "Results will appear here...",
        transcribe_analyzing: "Gemini analyzing audio...",
        modal_export_title: "Hardsub Export Options",
        modal_export_desc: "Choose subtitle burning method",
        opt_client_title: "Browser Direct Export",
        badge_recommended: "Recommended",
        opt_client_desc: "Render subtitles with Canvas & MediaRecorder API in browser. Fast, private, zero server storage.",
        opt_server_title: "Server FFmpeg Export (MP4 H.264)",
        opt_server_desc: "H.264 encoding via server FFmpeg. Temp files automatically cleaned after download.",
        opt_subs_title: "Download Subtitles (.SRT / .VTT)",
        opt_subs_desc: "Download standard subtitles to watch offline without re-encoding video.",
        burn_modal_title: "Exporting Hardsub in Browser",
        burn_modal_desc: "Reading video and burning subtitles in browser...",
        burn_init: "Initializing burner...",
        burn_encoding: "Rendering & encoding...",
        burn_done: "Done! Preparing download...",
        burn_safe_note: "Processed directly in browser RAM, ensuring data privacy and zero server storage.",
        burn_success_alert: "Hardsub video exported successfully! Saved to your device.",
        btn_cancel: "Cancel",
        pool_modal_title: "Smart Key Pool",
        pool_modal_desc: "Automated Round-Robin load balancing & quota management",
        th_stt: "No.",
        th_project: "Cloud Project",
        th_key: "Key",
        th_status: "Status",
        th_cooldown: "Cooldown",
        th_requests: "Calls",
        pool_footer: "Automatic key quarantine on 429 rate limit",
        btn_refresh: "Refresh",
        status_ready: "READY",
        status_cooldown: "COOLDOWN ({sec}s)",
        status_ready_short: "Ready",
        btn_menu_text: "Menu",
        drawer_subtitle: "Control Center",
        drawer_section_nav: "Navigation",
        drawer_tab_video: "Video Subtitles",
        drawer_tab_translate: "Document & Text",
        drawer_tab_document: "Document & Text",
        drawer_tab_web: "Web Page Translator",
        drawer_tab_transcribe: "Voice Transcribe",
        drawer_section_pref: "Preferences",
        drawer_lang_title: "Interface Language",
        drawer_theme_title: "Appearance (Theme)",
        theme_menu_title: "Theme & Mode",
        drawer_theme_title: "Theme & Mode",
        mode_dark: "Dark Mode 🌙",
        mode_light: "Light Mode ☀️",
        mode_dark_short: "Dark 🌙",
        mode_light_short: "Light ☀️",
        accent_section_title: "Accent Palette:",
        theme_dark: "Dark",
        theme_light: "Light",
        drawer_section_pool: "AI Studio Pool Status",
        pool_ready_summary: "{ready} Cloud Keys Ready",
        pool_drawer_desc: "Auto Round-Robin rotation avoiding 15 RPM limits.",
        drawer_section_links: "Links",
        alert_no_video: "Please choose a video first!",
        alert_no_subs: "Please scan subtitles before exporting video!",
        video_target_lang_label: "Target Lang:",
        multi_sub_title: "Multi-Lang",
        btn_translating_sub: "Translating...",
        alert_clean_success: "Server cleaned up! 0 bytes remaining.",
        alert_copied: "Copied to clipboard!",
        alert_no_text: "Please enter text to translate!",
        alert_no_audio: "Please record or upload an audio file first!"
      }
    };

    let currentLang = localStorage.getItem('geminitrans_lang') || 'vi';

    function t(key, vars = {}) {
      const dict = I18N[currentLang] || I18N['vi'];
      let str = dict[key] || I18N['vi'][key] || key;
      for (const [k, v] of Object.entries(vars)) {
        str = str.replace(new RegExp(`\\{${k}\\}`, 'g'), v);
      }
      return str;
    }

    function setLanguage(lang) {
      if (!I18N[lang]) lang = 'vi';
      currentLang = lang;
      localStorage.setItem('geminitrans_lang', lang);

      // Update Drawer toggle buttons
      const dBtnVi = document.getElementById('drawer-lang-btn-vi');
      const dBtnEn = document.getElementById('drawer-lang-btn-en');
      if (dBtnVi && dBtnEn) {
        if (lang === 'vi') {
          dBtnVi.className = "flex-1 py-1.5 px-2 rounded-md text-xs font-semibold flex items-center justify-center gap-1.5 transition bg-indigo-600 text-white shadow cursor-pointer";
          dBtnEn.className = "flex-1 py-1.5 px-2 rounded-md text-xs font-semibold flex items-center justify-center gap-1.5 transition text-slate-400 hover:text-white cursor-pointer";
        } else {
          dBtnEn.className = "flex-1 py-1.5 px-2 rounded-md text-xs font-semibold flex items-center justify-center gap-1.5 transition bg-indigo-600 text-white shadow cursor-pointer";
          dBtnVi.className = "flex-1 py-1.5 px-2 rounded-md text-xs font-semibold flex items-center justify-center gap-1.5 transition text-slate-400 hover:text-white cursor-pointer";
        }
      }

      // Update Desktop Header toggle buttons if present
      const btnVi = document.getElementById('lang-btn-vi');
      const btnEn = document.getElementById('lang-btn-en');
      if (btnVi && btnEn) {
        if (lang === 'vi') {
          btnVi.className = "px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition bg-indigo-600 text-white shadow";
          btnEn.className = "px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition text-slate-400 hover:text-white";
        } else {
          btnEn.className = "px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition bg-indigo-600 text-white shadow";
          btnVi.className = "px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition text-slate-400 hover:text-white";
        }
      }

      // Update text in elements with data-i18n
      document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (key && I18N[lang][key]) {
          el.innerText = I18N[lang][key];
        }
      });

      // Update placeholders
      document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (key && I18N[lang][key]) {
          el.setAttribute('placeholder', I18N[lang][key]);
        }
      });

      // Update dynamic pool UI and indicators
      if (poolData) {
        renderPoolStatusUI();
      }
      if (!currentVideoId) {
        const vidBadge = document.getElementById('current-video-badge');
        if (vidBadge) vidBadge.innerText = t('badge_no_video');
      }
      const subBadge = document.getElementById('sub-count-badge');
      if (subBadge) subBadge.innerText = t('timeline_count_cues', { count: currentVideoSubtitles.length });
      updateCharCount();
      if (window.lucide && lucide.createIcons) {
        lucide.createIcons();
      }
    }

    // ==========================================


    // ==========================================================================
    // ORTHOGONAL THEME CONTROLLER (MODE: DARK/LIGHT + 5 ACCENT PALETTES)
    // ==========================================================================
    const ACCENT_THEMES = [
      {
        id: 'blue',
        name: 'Xanh Dương',
        nameEn: 'Ocean Blue',
        colorHex: '#2563eb',
        previewHex: '#3b82f6'
      },
      {
        id: 'orange',
        name: 'Cam Rực Rỡ',
        nameEn: 'Vibrant Orange',
        colorHex: '#ea580c',
        previewHex: '#f97316'
      },
      {
        id: 'emerald',
        name: 'Xanh Ngọc',
        nameEn: 'Emerald Mint',
        colorHex: '#059669',
        previewHex: '#10b981'
      },
      {
        id: 'crimson',
        name: 'Đỏ Ruby',
        nameEn: 'Crimson Ruby',
        colorHex: '#e11d48',
        previewHex: '#f43f5e'
      },
      {
        id: 'monochrome',
        name: 'Đơn Sắc',
        nameEn: 'Monochrome Slate',
        colorHex: '#64748b',
        previewHex: '#94a3b8'
      }
    ];

    let currentMode = 'dark';
    let currentAccent = 'blue';

    function initThemeSystem() {
      const validModes = ['dark', 'light'];
      const validAccents = ['blue', 'orange', 'emerald', 'crimson', 'monochrome'];
      
      let savedMode = localStorage.getItem('geminitrans_mode');
      let savedAccent = localStorage.getItem('geminitrans_accent');

      if (!savedMode || !savedAccent) {
        const legacyTheme = localStorage.getItem('geminitrans_theme');
        if (legacyTheme === 'theme-light' || legacyTheme === 'light') {
          savedMode = savedMode || 'light';
          savedAccent = savedAccent || 'blue';
        } else if (legacyTheme && legacyTheme.startsWith('theme-')) {
          savedMode = savedMode || 'dark';
          const c = legacyTheme.replace('theme-', '');
          savedAccent = validAccents.includes(c) ? c : 'blue';
        }
      }

      currentMode = validModes.includes(savedMode) ? savedMode : 'dark';
      currentAccent = validAccents.includes(savedAccent) ? savedAccent : 'blue';

      applyTheme(currentMode, currentAccent, false);
    }

    function setThemeMode(mode) {
      if (mode !== 'dark' && mode !== 'light') return;
      applyTheme(mode, currentAccent, true);
    }

    function toggleThemeMode() {
      const newMode = (currentMode === 'dark') ? 'light' : 'dark';
      applyTheme(newMode, currentAccent, true);
    }

    function setAccentTheme(accent) {
      if (!ACCENT_THEMES.some(a => a.id === accent)) return;
      applyTheme(currentMode, accent, true);
    }

    function applyTheme(mode, accent, save = true) {
      // Compatibility fallback: Nếu truyền chuỗi cũ như 'theme-blue' hay 'theme-light'
      if (arguments.length === 1 && typeof mode === 'string') {
        const legacyKey = mode;
        if (legacyKey === 'theme-light' || legacyKey === 'light') {
          mode = 'light';
          accent = currentAccent || 'blue';
        } else {
          mode = 'dark';
          const c = legacyKey.replace('theme-', '');
          accent = ACCENT_THEMES.some(a => a.id === c) ? c : 'blue';
        }
      }

      currentMode = mode || 'dark';
      currentAccent = accent || 'blue';

      if (save) {
        try {
          localStorage.setItem('geminitrans_mode', currentMode);
          localStorage.setItem('geminitrans_accent', currentAccent);
          localStorage.setItem('geminitrans_theme', 'theme-' + currentAccent);
        } catch (e) {}
      }

      const htmlEl = document.documentElement;
      htmlEl.setAttribute('data-mode', currentMode);
      htmlEl.setAttribute('data-accent', currentAccent);
      htmlEl.setAttribute('data-theme', 'theme-' + currentAccent);

      if (currentMode === 'light') {
        htmlEl.classList.remove('dark');
        htmlEl.classList.add('light');
      } else {
        htmlEl.classList.remove('light');
        htmlEl.classList.add('dark');
      }

      renderThemeUI();

      // Close popover if open
      const popover = document.getElementById('theme-menu-popover');
      if (popover && !popover.classList.contains('hidden')) {
        popover.classList.add('hidden');
      }
    }

    function renderThemeUI() {
      const isEn = (typeof currentLang !== 'undefined' && currentLang === 'en');
      const activeAccent = ACCENT_THEMES.find(a => a.id === currentAccent) || ACCENT_THEMES[0];
      const accentName = isEn ? activeAccent.nameEn : activeAccent.name;

      // 1. Header quick mode toggle button icon & text
      const headerModeIcon = document.getElementById('header-mode-icon');
      const headerModeText = document.getElementById('header-mode-text');
      const btnToggleMode = document.getElementById('btn-toggle-mode');
      if (headerModeIcon) {
        if (currentMode === 'dark') {
          headerModeIcon.setAttribute('data-lucide', 'sun');
          headerModeIcon.className = 'w-3.5 h-3.5 text-amber-400';
          if (headerModeText) headerModeText.textContent = isEn ? 'Dark 🌙' : 'Tối 🌙';
          if (btnToggleMode) btnToggleMode.title = isEn ? 'Switch to Light Mode' : 'Chuyển sang chế độ Sáng';
        } else {
          headerModeIcon.setAttribute('data-lucide', 'moon');
          headerModeIcon.className = 'w-3.5 h-3.5 text-indigo-500';
          if (headerModeText) headerModeText.textContent = isEn ? 'Light ☀️' : 'Sáng ☀️';
          if (btnToggleMode) btnToggleMode.title = isEn ? 'Switch to Dark Mode' : 'Chuyển sang chế độ Tối';
        }
      }

      // 2. Header Accent Dot & Name
      const headerDot = document.getElementById('header-theme-dot');
      if (headerDot) headerDot.style.backgroundColor = activeAccent.previewHex;
      const headerName = document.getElementById('header-theme-name');
      if (headerName) headerName.textContent = accentName;

      // 3. Popover Mode Segmented Buttons
      const popoverDark = document.getElementById('popover-mode-dark');
      const popoverLight = document.getElementById('popover-mode-light');
      if (popoverDark && popoverLight) {
        if (currentMode === 'dark') {
          popoverDark.className = 'flex-1 py-1.5 px-2 rounded-md text-xs font-semibold flex items-center justify-center gap-1.5 transition bg-indigo-600 text-white shadow cursor-pointer';
          popoverLight.className = 'flex-1 py-1.5 px-2 rounded-md text-xs font-semibold flex items-center justify-center gap-1.5 transition text-slate-400 hover:text-white cursor-pointer';
        } else {
          popoverDark.className = 'flex-1 py-1.5 px-2 rounded-md text-xs font-semibold flex items-center justify-center gap-1.5 transition text-slate-400 hover:text-white cursor-pointer';
          popoverLight.className = 'flex-1 py-1.5 px-2 rounded-md text-xs font-semibold flex items-center justify-center gap-1.5 transition bg-indigo-600 text-white shadow cursor-pointer';
        }
      }

      // 4. Popover Accent List Options
      const popoverContainer = document.getElementById('theme-popover-options');
      if (popoverContainer) {
        popoverContainer.innerHTML = ACCENT_THEMES.map(a => {
          const isActive = (a.id === currentAccent);
          const aName = isEn ? a.nameEn : a.name;
          return `
            <button onclick="setAccentTheme('${a.id}')" class="w-full flex items-center justify-between px-2.5 py-1.5 rounded-[8px] text-xs font-medium transition cursor-pointer ${
              isActive 
                ? 'theme-item-active text-white border border-slate-600 shadow-sm' 
                : 'text-slate-300 hover:text-white hover:bg-slate-800/80 border border-transparent'
            }">
              <span class="flex items-center gap-2.5">
                <span class="w-3.5 h-3.5 rounded-full border border-white/20 shadow-sm shrink-0" style="background-color: ${a.previewHex};"></span>
                <span>${aName}</span>
              </span>
              ${isActive ? '<i data-lucide="check" class="w-3.5 h-3.5 text-white"></i>' : ''}
            </button>
          `;
        }).join('');
      }

      // 5. Drawer Mode Segmented Buttons
      const drawerModeDark = document.getElementById('drawer-mode-btn-dark');
      const drawerModeLight = document.getElementById('drawer-mode-btn-light');
      if (drawerModeDark && drawerModeLight) {
        if (currentMode === 'dark') {
          drawerModeDark.className = 'flex-1 py-1.5 px-2 rounded-md text-xs font-semibold flex items-center justify-center gap-1.5 transition bg-indigo-600 text-white shadow cursor-pointer';
          drawerModeLight.className = 'flex-1 py-1.5 px-2 rounded-md text-xs font-semibold flex items-center justify-center gap-1.5 transition text-slate-400 hover:text-white cursor-pointer';
        } else {
          drawerModeDark.className = 'flex-1 py-1.5 px-2 rounded-md text-xs font-semibold flex items-center justify-center gap-1.5 transition text-slate-400 hover:text-white cursor-pointer';
          drawerModeLight.className = 'flex-1 py-1.5 px-2 rounded-md text-xs font-semibold flex items-center justify-center gap-1.5 transition bg-indigo-600 text-white shadow cursor-pointer';
        }
      }

      // 6. Drawer Current Theme Label
      const drawerThemeName = document.getElementById('drawer-current-theme-name');
      if (drawerThemeName) {
        const modeLabel = (currentMode === 'dark') ? (isEn ? 'Dark' : 'Tối') : (isEn ? 'Light' : 'Sáng');
        drawerThemeName.textContent = `${modeLabel} • ${accentName}`;
      }

      // 7. Drawer Accent Grid Options
      const drawerGrid = document.getElementById('drawer-theme-options-grid');
      if (drawerGrid) {
        drawerGrid.innerHTML = ACCENT_THEMES.map(a => {
          const isActive = (a.id === currentAccent);
          const aName = isEn ? a.nameEn : a.name;
          return `
            <button onclick="setAccentTheme('${a.id}')" class="flex items-center gap-2 p-2 rounded-[8px] text-left text-xs font-medium transition cursor-pointer ${
              isActive 
                ? 'theme-item-active text-white border border-slate-600 shadow-sm' 
                : 'bg-slate-900/70 text-slate-300 hover:text-white hover:bg-slate-800/90 border border-slate-700/60'
            }">
              <span class="w-3.5 h-3.5 rounded-full border border-white/20 shadow-sm shrink-0" style="background-color: ${a.previewHex};"></span>
              <span class="truncate flex-1">${aName}</span>
              ${isActive ? '<i data-lucide="check" class="w-3 h-3 text-white shrink-0"></i>' : ''}
            </button>
          `;
        }).join('');
      }

      if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
      }
    }

    function toggleThemeMenu(e) {
      if (e) e.stopPropagation();
      const popover = document.getElementById('theme-menu-popover');
      if (!popover) return;
      popover.classList.toggle('hidden');
    }

    document.addEventListener('click', function(e) {
      const popover = document.getElementById('theme-menu-popover');
      const btn = document.getElementById('btn-theme-dropdown');
      if (popover && !popover.classList.contains('hidden')) {
        if (!popover.contains(e.target) && (!btn || !btn.contains(e.target))) {
          popover.classList.add('hidden');
        }
      }
    });

    // Compatibility aliases
    const renderThemeSelectors = renderThemeUI;
    const setTheme = applyTheme;
    const AVAILABLE_THEMES = ACCENT_THEMES;

    // Initialize Theme System
    initThemeSystem();
    
// ==========================================
// TAB SWITCH & URL HASH ROUTING
// ==========================================
const validTabs = ['video', 'document', 'web', 'transcribe', 'manga'];
const tabAliases = {
  'translate': 'document',
  'text': 'document',
  'doc': 'document',
  'subtitles': 'video',
  'subtitle': 'video',
  'audio': 'transcribe',
  'voice': 'transcribe',
  'speech': 'transcribe',
  'comic': 'manga',
  'webpage': 'web',
  'site': 'web'
};

function normalizeTab(t) {
  if (!t) return 'video';
  let clean = String(t).trim().toLowerCase();
  clean = clean.replace(/^#/, '').replace(/^\?/, '');
  if (clean.startsWith('tab=')) {
    clean = clean.substring(4);
  }
  if (clean.startsWith('tab-')) {
    clean = clean.substring(4);
  }
  if (tabAliases[clean]) {
    clean = tabAliases[clean];
  }
  return validTabs.includes(clean) ? clean : 'video';
}

function switchTab(tab, updateUrl = true) {
  const activeTab = normalizeTab(tab);
  
  // Pause uploaded video if tab is not video
  if (activeTab !== 'video') {
    const vEl = document.getElementById('uploadedVideo');
    if (vEl && typeof vEl.pause === 'function') {
      try { vEl.pause(); } catch(e) {}
    }
  }

  // Toggle sections
  validTabs.forEach(t => {
    const sec = document.getElementById('tab-' + t);
    if (sec) {
      if (t === activeTab) {
        sec.classList.remove('hidden');
      } else {
        sec.classList.add('hidden');
      }
    }
  });

  // Update header pill links active styling
  document.querySelectorAll('[id^="tab-btn-"]').forEach(el => {
    const linkTab = el.getAttribute('data-tab-link');
    if (linkTab === activeTab) {
      el.classList.add('bg-indigo-600', 'text-white', 'shadow-sm');
      el.classList.remove('text-slate-300', 'hover:text-white', 'hover:bg-slate-700/50', 'text-slate-400', 'hover:bg-slate-100');
    } else {
      el.classList.remove('bg-indigo-600', 'text-white', 'shadow-sm');
      // Re-apply inactive classes based on data mode or default state
      el.classList.add('text-slate-300', 'hover:text-white', 'hover:bg-slate-700/50');
    }
  });

  // Update drawer links active styling
  document.querySelectorAll('[id^="mobile-tab-btn-"]').forEach(el => {
    const linkTab = el.getAttribute('data-tab-link');
    if (linkTab === activeTab) {
      el.classList.add('bg-indigo-600', 'text-white', 'shadow-sm');
      el.classList.remove('text-slate-300', 'hover:text-white', 'hover:bg-slate-700/50');
    } else {
      el.classList.remove('bg-indigo-600', 'text-white', 'shadow-sm');
      el.classList.add('text-slate-300', 'hover:text-white', 'hover:bg-slate-700/50');
    }
  });

  if (updateUrl) {
    try {
      const url = new URL(window.location.href);
      url.searchParams.set('tab', activeTab);
      window.history.pushState({ tab: activeTab }, '', url.pathname + '?' + url.searchParams.toString());
    } catch (e) {
      console.error(e);
    }
  }

  if (typeof lucide !== 'undefined' && typeof lucide.createIcons === 'function') {
    try { lucide.createIcons(); } catch(e) {}
  }

  if (activeTab === 'manga' && typeof renderMangaWorkspace === 'function') {
    try { renderMangaWorkspace(); } catch(e) {}
  }
}

// Slide-over drawer controls
function toggleDrawer() {
  const drawer = document.getElementById('mobile-drawer');
  if (!drawer) return;
  const isOpen = !drawer.classList.contains('hidden');
  if (isOpen) {
    closeDrawer();
  } else {
    openDrawer();
  }
}

function openDrawer() {
  const drawer = document.getElementById('mobile-drawer');
  const panel = document.getElementById('mobile-drawer-panel');
  const backdrop = document.getElementById('mobile-drawer-backdrop');
  const menuButton = document.getElementById('btn-mobile-menu');
  if (!drawer || !panel || !backdrop) return;

  drawer.classList.remove('hidden');
  drawer.setAttribute('aria-hidden', 'false');
  if (menuButton) menuButton.setAttribute('aria-expanded', 'true');
  requestAnimationFrame(() => {
    panel.classList.remove('-translate-x-full');
    backdrop.classList.remove('opacity-0', 'pointer-events-none');
    backdrop.classList.add('opacity-100');
  });
}

function closeDrawer() {
  const drawer = document.getElementById('mobile-drawer');
  const panel = document.getElementById('mobile-drawer-panel');
  const backdrop = document.getElementById('mobile-drawer-backdrop');
  const menuButton = document.getElementById('btn-mobile-menu');
  if (!drawer || !panel || !backdrop || drawer.classList.contains('hidden')) return;

  panel.classList.add('-translate-x-full');
  backdrop.classList.remove('opacity-100');
  backdrop.classList.add('opacity-0', 'pointer-events-none');
  if (menuButton) menuButton.setAttribute('aria-expanded', 'false');
  window.setTimeout(() => {
    if (panel.classList.contains('-translate-x-full')) {
      drawer.classList.add('hidden');
      drawer.setAttribute('aria-hidden', 'true');
    }
  }, 300);
}

window.addEventListener('resize', () => {
  if (window.innerWidth >= 1024) {
    closeDrawer();
  }
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeDrawer();
  }
});

function switchDrawerTab(tab) {
  switchTab(tab, true);
  closeDrawer();
}

// Backward compatibility aliases
function toggleMobileMenu() { toggleDrawer(); }
function closeMobileMenu() { closeDrawer(); }
function switchMobileTab(tab) { switchDrawerTab(tab); }
function openMobilePoolModal() {
  if (typeof openPoolModal === 'function') openPoolModal();
  closeDrawer();
}

function initRouteTab() {
  const params = new URLSearchParams(window.location.search);
  const queryTab = params.get('tab');
  const hash = window.location.hash;
  const target = queryTab || hash;
  switchTab(normalizeTab(target), false);
}

const initHashRouting = initRouteTab;

window.addEventListener('popstate', () => initRouteTab());
window.addEventListener('hashchange', () => initRouteTab());
document.addEventListener('DOMContentLoaded', () => initRouteTab());

document.addEventListener('click', (e) => {
  const tabLink = e.target.closest('[data-tab-link]');
  if (!tabLink) return;
  // If middle click or modifier keys (Ctrl, Cmd, Shift, Alt), do NOT preventDefault! Let browser handle new tab!
  if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
  e.preventDefault();
  const tab = tabLink.getAttribute('data-tab-link');
  if (tab) {
    switchTab(tab, true);
    if (typeof closeDrawer === 'function') closeDrawer();
  }
});

function handleMiddleClick(e) {
  if (e.button !== 1) return;
  const anchor = e.target.closest('a[href]');
  if (anchor && anchor.getAttribute('href') && anchor.getAttribute('href') !== '#') {
    return; // let browser natively open link in new tab
  }
  const target = e.target.closest('[data-tab-link], #header-logo, [data-href]');
  if (target) {
    let tab = 'video';
    if (target.hasAttribute('data-tab-link')) {
      tab = target.getAttribute('data-tab-link');
    } else if (target.id === 'header-logo') {
      tab = 'video';
    } else if (target.hasAttribute('data-href')) {
      tab = target.getAttribute('data-href').replace('#', '');
    }
    const url = window.location.pathname + '?tab=' + normalizeTab(tab);
    window.open(url, '_blank');
  }
}

document.addEventListener('auxclick', handleMiddleClick);

document.addEventListener('mousedown', (e) => {
  if (e.button === 1) {
    const anchor = e.target.closest('a[href]');
    if (anchor && anchor.getAttribute('href') && anchor.getAttribute('href') !== '#') {
      return; // Do NOT preventDefault! Allow native link middle-click in browser
    }
    const target = e.target.closest('[data-tab-link], #header-logo, [data-href]');
    if (target) e.preventDefault();
  }
});



    // ==========================================
    // UTILS & ESCAPING
    // ==========================================
    function escapeHtml(str) {
      if (!str) return '';
      return String(str).replace(/[&<>"']/g, function(m) {
        return {
          '&': '&amp;',
          '<': '&lt;',
          '>': '&gt;',
          '"': '&quot;',
          "'": '&#039;'
        }[m];
      });
    }

    // ==========================================
    // 1. DUAL SUBTITLES (BILINGUAL MODE)
    // ==========================================

    // ==========================================
    function renderPoolStatusUI() {
      if (!poolData) return;
      const total = poolData.total_keys || (poolData.keys ? poolData.keys.length : 0);
      const readyKeys = poolData.keys ? poolData.keys.filter(k => k.status === 'READY').length : total;

      // Drawer pool summary: "7 Cloud Keys Sẵn Sàng"
      const drawerSummary = document.getElementById('drawer-pool-summary');
      if (drawerSummary) {
        drawerSummary.innerText = t('pool_ready_summary', { ready: readyKeys, total: total });
      }

      // Drawer active pointer
      const drawerActivePtr = document.getElementById('drawer-pool-active-ptr');
      if (drawerActivePtr) {
        drawerActivePtr.innerText = `Key #${poolData.current_pointer || 1}`;
      }

      // Header / legacy status texts if any exist
      const pst = document.getElementById('pool-status-text');
      if (pst) pst.innerText = t('pool_status', { pointer: poolData.current_pointer || 1 });
      const mpst = document.getElementById('mobile-pool-status-text');
      if (mpst) mpst.innerText = t('pool_status', { pointer: poolData.current_pointer || 1 });

      // Populate Drawer Pool Table (TUYỆT ĐỐI ẨN 100% RAW/MASKED KEYS)
      const drawerTbody = document.getElementById('drawer-pool-table-body');
      if (drawerTbody && poolData.keys) {
        drawerTbody.innerHTML = '';
        poolData.keys.forEach(k => {
          const row = document.createElement('tr');
          row.className = k.is_current ? 'bg-indigo-950/40 font-medium' : 'hover:bg-slate-800/30';
          const statusBadge = k.status === 'READY' 
            ? `<span class="text-emerald-400 font-semibold inline-flex items-center gap-1"><span class="w-1.5 h-1.5 status-dot bg-emerald-400"></span>${t('status_ready_short')}</span>` 
            : `<span class="text-amber-400 font-semibold inline-flex items-center gap-1"><span class="w-1.5 h-1.5 status-dot bg-amber-400"></span>${k.cooldown_remaining}s</span>`;

          row.innerHTML = `
            <td class="py-2 px-2.5 font-semibold text-slate-200">
              Key #${k.index} ${k.is_current ? '<span class="text-indigo-400 text-[10px] ml-1">● Active</span>' : ''}
            </td>
            <td class="py-2 px-2">${statusBadge}</td>
            <td class="py-2 px-2.5 text-right font-mono text-slate-300">${k.requests}</td>
          `;
          drawerTbody.appendChild(row);
        });
      }

      // Update Modal Pool Table if opened (ZERO RAW KEYS DISPLAYED)
      const modalTbody = document.getElementById('pool-table-body');
      if (modalTbody && poolData.keys) {
        modalTbody.innerHTML = '';
        poolData.keys.forEach(k => {
          const row = document.createElement('tr');
          row.className = k.is_current ? 'bg-indigo-950/40' : '';
          const statusBadge = k.status === 'READY' 
            ? `<span class="text-emerald-400 font-bold">${t('status_ready')}</span>` 
            : `<span class="text-amber-400 font-bold">${t('status_cooldown', { sec: k.cooldown_remaining })}</span>`;

          row.innerHTML = `
            <td class="py-2.5 px-3 font-semibold text-slate-300">Key #${k.index} ${k.is_current ? '<span class="text-indigo-400 text-[10px] ml-1 font-sans">Active</span>' : ''}</td>
            <td class="py-2.5 px-3 font-medium text-slate-300">Cloud Project #${k.index}</td>
            <td class="py-2.5 px-3">${statusBadge}</td>
            <td class="py-2.5 px-3 text-slate-400">${k.cooldown_remaining > 0 ? k.cooldown_remaining + 's' : '0s'}</td>
            <td class="py-2.5 px-3 text-right font-semibold text-indigo-300">${k.requests}</td>
          `;
          modalTbody.appendChild(row);
        });
      }
    }

    async function fetchPoolStatus() {
      const refreshIcon = document.getElementById('pool-refresh-icon');
      if (refreshIcon) refreshIcon.classList.add('animate-spin');
      try {
        const res = await fetch('/api/pool-status');
        poolData = await res.json();
        renderPoolStatusUI();
      } catch (e) {
        console.error("Pool fetch error:", e);
      } finally {
        if (refreshIcon) {
          setTimeout(() => refreshIcon.classList.remove('animate-spin'), 400);
        }
      }
    }
    fetchPoolStatus();
    setInterval(fetchPoolStatus, 15000);

    
    // ==========================================
    // QR CODE MODAL FOR MOBILE / LAN CONNECTION
    // ==========================================
    let qrCodeInstance = null;

    function renderQrContent(targetUrl) {
      const input = document.getElementById('qr-lan-url-input');
      const container = document.getElementById('qr-canvas-container');
      if (input) input.value = targetUrl;
      if (container) {
        container.innerHTML = '';
        if (typeof QRCode !== 'undefined') {
          qrCodeInstance = new QRCode(container, {
            text: targetUrl,
            width: 180,
            height: 180,
            colorDark: "#0f172a",
            colorLight: "#ffffff",
            correctLevel: QRCode.CorrectLevel.M
          });
        } else {
          container.innerHTML = `<img src="https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(targetUrl)}" alt="QR Code" class="w-[180px] h-[180px] rounded" />`;
        }
      }
    }

    async function openQrModal() {
      const modal = document.getElementById('qr-mobile-modal');
      if (!modal) return;
      modal.classList.remove('hidden');
      if (window.lucide) lucide.createIcons();
      
      const defaultUrl = (window.location.origin && window.location.origin !== 'null' && window.location.origin.startsWith('http')) ? window.location.origin : 'http://172.30.80.28:8090';
      renderQrContent(defaultUrl);
      
      try {
        const res = await fetch('/api/network-info');
        const data = await res.json();
        const lanUrl = data.lan_url || defaultUrl;
        if (lanUrl !== defaultUrl) {
          renderQrContent(lanUrl);
        }
      } catch (err) {
        // keep default
      }
    }

    function checkAutoOpenQr() {
      if (window.location.hash === '#qr-mobile-modal' || window.location.search.includes('open_qr=1')) {
        openQrModal();
      }
    }
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', checkAutoOpenQr);
    } else {
      checkAutoOpenQr();
    }

    function closeQrModal() {
      const modal = document.getElementById('qr-mobile-modal');
      if (modal) modal.classList.add('hidden');
    }

    function copyQrLanUrl() {
      const input = document.getElementById('qr-lan-url-input');
      const btnText = document.getElementById('copy-qr-url-text');
      if (!input) return;
      const url = input.value;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(() => {
          if (btnText) {
            btnText.textContent = 'Đã chép! ✓';
            setTimeout(() => { btnText.textContent = 'Sao chép'; }, 2000);
          }
        }).catch(() => {
          input.select();
          document.execCommand('copy');
          if (btnText) {
            btnText.textContent = 'Đã chép! ✓';
            setTimeout(() => { btnText.textContent = 'Sao chép'; }, 2000);
          }
        });
      } else {
        input.select();
        document.execCommand('copy');
        if (btnText) {
          btnText.textContent = 'Đã chép! ✓';
          setTimeout(() => { btnText.textContent = 'Sao chép'; }, 2000);
        }
      }
    }

    function togglePoolModal() {
      const modal = document.getElementById('pool-modal');
      if (modal) modal.classList.toggle('hidden');
    }

    // ==========================================


    // ==========================================
    // GLOBAL TOAST NOTIFICATION HELPER
    // ==========================================
    function showToast(message, type = 'info') {
      let toast = document.getElementById('app-toast-notification');
      if (!toast) {
        toast = document.createElement('div');
        toast.id = 'app-toast-notification';
        toast.className = "fixed top-6 right-6 z-50 px-4 py-3 rounded-[10px] bg-slate-900/95 border border-cyan-500/50 shadow-lg border border-slate-800 text-white text-xs sm:text-sm font-semibold flex items-center gap-2.5 transition-all duration-300 pointer-events-none transform -translate-y-5 opacity-0 backdrop-blur";
        document.body.appendChild(toast);
      }
      const icon = type === 'error' ? 'alert-circle' : 'check-circle-2';
      const iconColor = type === 'error' ? 'text-rose-400' : 'text-cyan-400';
      toast.innerHTML = `<i data-lucide="${icon}" class="w-4 h-4 ${iconColor}"></i><span>${message}</span>`;
      if (window.lucide && lucide.createIcons) lucide.createIcons();
      toast.classList.remove('-translate-y-5', 'opacity-0');
      toast.classList.add('translate-y-0', 'opacity-100');
      setTimeout(() => {
        toast.classList.remove('translate-y-0', 'opacity-100');
        toast.classList.add('-translate-y-5', 'opacity-0');
      }, 3500);
    }

    // ==========================================
    // SUB-FEATURE: WEBPAGE TRANSLATOR CONTROLLER
    // ==========================================
    const webState = {
      subMode: 'text', // 'text' | 'web'
      viewMode: 'split', // 'translated' | 'original' | 'split'
      syncScroll: true,
      url: '',
      title: '',
      translatedTitle: '',
      originalHtml: '',
      translatedHtml: '',
      isLoading: false
    };


async function checkSystemUpdate() {
      try {
        const res = await fetch('/api/system/check-update');
        if (!res.ok) return;
        const data = await res.json();
        if (data.status === 'success' && data.has_update) {
          const banner = document.getElementById('system-update-banner');
          const msg = document.getElementById('update-banner-msg');
          if (banner && msg) {
            msg.innerHTML = 'Có <b>' + data.behind_count + '</b> bản cập nhật mới trên nhánh <code>' + data.branch + '</code>:<br><span class="text-indigo-300 font-mono text-[11px]">' + (data.remote_commit || 'Phiên bản mới nhất') + '</span>';
            banner.classList.remove('hidden');
            setTimeout(function() {
              banner.classList.remove('translate-y-4', 'opacity-0');
            }, 100);
            if (window.lucide) lucide.createIcons();
          }
        }
      } catch (err) {
        console.debug('Check update error:', err);
      }
    }

    function dismissUpdateBanner() {
      const banner = document.getElementById('system-update-banner');
      if (banner) {
        banner.classList.add('translate-y-4', 'opacity-0');
        setTimeout(function() { banner.classList.add('hidden'); }, 300);
      }
    }

    async function triggerSystemUpdate() {
      const btn = document.getElementById('btn-perform-update');
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i> Đang cập nhật...';
        if (window.lucide) lucide.createIcons();
      }

      try {
        const res = await fetch('/api/system/perform-update', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success') {
          if (btn) {
            btn.innerHTML = '<i data-lucide="check" class="w-3.5 h-3.5"></i> Hoàn tất! Đang tải lại...';
            btn.className = 'px-3.5 py-1.5 rounded-[8px] bg-emerald-600 text-white font-medium text-xs flex items-center gap-1.5';
            if (window.lucide) lucide.createIcons();
          }
          setTimeout(function() {
            window.location.reload();
          }, 1500);
        } else {
          alert('Cập nhật thất bại: ' + (data.message || 'Lỗi không xác định'));
          if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i> Thử lại';
            if (window.lucide) lucide.createIcons();
          }
        }
      } catch (err) {
        alert('Lỗi kết nối khi cập nhật: ' + err.message);
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = '<i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i> Thử lại';
          if (window.lucide) lucide.createIcons();
        }
      }
    }

    window.addEventListener('load', function() {
      setTimeout(checkSystemUpdate, 2000);
    });

// ==========================================
    // CONNECTION WATCHDOG / HEARTBEAT
    // ==========================================
    let isServerShuttingDown = false;
    let failedPingCount = 0;
    const MAX_FAILED_PINGS = 2;

    function closeTabOrRedirect() {
      try {
        window.open('', '_self', '');
        window.close();
      } catch (e) {}
      setTimeout(() => {
        document.body.innerHTML = `
          <div style="display:flex;height:100vh;align-items:center;justify-content:center;background:#0b0f19;color:#94a3b8;font-family:system-ui,-apple-system,sans-serif;text-align:center;padding:20px;">
            <div style="max-width:480px;background:#1e293b;border:1px solid #334155;border-radius:16px;padding:32px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.5);">
              <div style="font-size:48px;margin-bottom:16px;">🔌</div>
              <h1 style="color:#f1f5f9;font-size:22px;font-weight:700;margin-bottom:10px;">GeminiTrans đã tắt hoàn toàn</h1>
              <p style="color:#94a3b8;font-size:14px;line-height:1.6;margin-bottom:20px;">Máy chủ backend đã dừng. Bạn có thể đóng tab này an toàn bằng phím tắt <kbd style="background:#0f172a;padding:2px 6px;border-radius:4px;border:1px solid #475569;color:#e2e8f0;">Ctrl + W</kbd>.</p>
            </div>
          </div>`;
      }, 300);
    }

    function triggerShutdownUI() {
      if (isServerShuttingDown) return;
      isServerShuttingDown = true;
      const overlay = document.getElementById('shutdown-overlay');
      if (overlay) {
        overlay.classList.remove('opacity-0', 'pointer-events-none');
        overlay.classList.add('opacity-100', 'pointer-events-auto');
      }
      setTimeout(closeTabOrRedirect, 4000);
    }

    async function checkServerHeartbeat() {
      if (isServerShuttingDown) return;
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 2000);
        const res = await fetch('/api/pool-status', { signal: controller.signal });
        clearTimeout(timeoutId);
        
        if (res.ok) {
          const data = await res.json();
          failedPingCount = 0;
          if (data && data.status === 'shutting_down') {
            triggerShutdownUI();
            return;
          }
        } else if (res.status === 502 || res.status === 503 || res.status === 504) {
          failedPingCount++;
          if (failedPingCount >= MAX_FAILED_PINGS) {
            triggerShutdownUI();
          }
        }
      } catch (err) {
        failedPingCount++;
        if (failedPingCount >= MAX_FAILED_PINGS) {
          triggerShutdownUI();
        }
      }
    }

    setInterval(checkServerHeartbeat, 2500);


    // Expose functions to window for HTML inline event handlers
    window.I18N = typeof I18N !== 'undefined' ? I18N : undefined;
    window.t = typeof t !== 'undefined' ? t : undefined;
    window.setLanguage = typeof setLanguage !== 'undefined' ? setLanguage : undefined;
    window.currentLang = typeof currentLang !== 'undefined' ? currentLang : undefined;
    window.poolData = typeof poolData !== 'undefined' ? poolData : undefined;
    window.ACCENT_THEMES = typeof ACCENT_THEMES !== 'undefined' ? ACCENT_THEMES : undefined;
    window.currentMode = typeof currentMode !== 'undefined' ? currentMode : undefined;
    window.currentAccent = typeof currentAccent !== 'undefined' ? currentAccent : undefined;
    window.initThemeSystem = typeof initThemeSystem !== 'undefined' ? initThemeSystem : undefined;
    window.setThemeMode = typeof setThemeMode !== 'undefined' ? setThemeMode : undefined;
    window.toggleThemeMode = typeof toggleThemeMode !== 'undefined' ? toggleThemeMode : undefined;
    window.setAccentTheme = typeof setAccentTheme !== 'undefined' ? setAccentTheme : undefined;
    window.applyTheme = typeof applyTheme !== 'undefined' ? applyTheme : undefined;
    window.renderThemeUI = typeof renderThemeUI !== 'undefined' ? renderThemeUI : undefined;
    window.toggleThemeMenu = typeof toggleThemeMenu !== 'undefined' ? toggleThemeMenu : undefined;
    window.switchTab = typeof switchTab !== 'undefined' ? switchTab : undefined;
    window.normalizeTab = typeof normalizeTab !== 'undefined' ? normalizeTab : undefined;
    window.initRouteTab = typeof initRouteTab !== 'undefined' ? initRouteTab : undefined;
    window.initHashRouting = typeof initHashRouting !== 'undefined' ? initHashRouting : undefined;
    window.toggleDrawer = typeof toggleDrawer !== 'undefined' ? toggleDrawer : undefined;
    window.openDrawer = typeof openDrawer !== 'undefined' ? openDrawer : undefined;
    window.closeDrawer = typeof closeDrawer !== 'undefined' ? closeDrawer : undefined;
    window.switchDrawerTab = typeof switchDrawerTab !== 'undefined' ? switchDrawerTab : undefined;
    window.toggleMobileMenu = typeof toggleMobileMenu !== 'undefined' ? toggleMobileMenu : undefined;
    window.closeMobileMenu = typeof closeMobileMenu !== 'undefined' ? closeMobileMenu : undefined;
    window.switchMobileTab = typeof switchMobileTab !== 'undefined' ? switchMobileTab : undefined;
    window.openMobilePoolModal = typeof openMobilePoolModal !== 'undefined' ? openMobilePoolModal : undefined;
    window.handleMiddleClick = typeof handleMiddleClick !== 'undefined' ? handleMiddleClick : undefined;
    window.escapeHtml = typeof escapeHtml !== 'undefined' ? escapeHtml : undefined;
    window.renderPoolStatusUI = typeof renderPoolStatusUI !== 'undefined' ? renderPoolStatusUI : undefined;
    window.fetchPoolStatus = typeof fetchPoolStatus !== 'undefined' ? fetchPoolStatus : undefined;
    window.togglePoolModal = typeof togglePoolModal !== 'undefined' ? togglePoolModal : undefined;
    window.renderQrContent = typeof renderQrContent !== 'undefined' ? renderQrContent : undefined;
    window.openQrModal = typeof openQrModal !== 'undefined' ? openQrModal : undefined;
    window.checkAutoOpenQr = typeof checkAutoOpenQr !== 'undefined' ? checkAutoOpenQr : undefined;
    window.closeQrModal = typeof closeQrModal !== 'undefined' ? closeQrModal : undefined;
    window.copyQrLanUrl = typeof copyQrLanUrl !== 'undefined' ? copyQrLanUrl : undefined;
    window.showToast = typeof showToast !== 'undefined' ? showToast : undefined;
    window.checkSystemUpdate = typeof checkSystemUpdate !== 'undefined' ? checkSystemUpdate : undefined;
    window.dismissUpdateBanner = typeof dismissUpdateBanner !== 'undefined' ? dismissUpdateBanner : undefined;
    window.triggerSystemUpdate = typeof triggerSystemUpdate !== 'undefined' ? triggerSystemUpdate : undefined;
    window.closeTabOrRedirect = typeof closeTabOrRedirect !== 'undefined' ? closeTabOrRedirect : undefined;
    window.triggerShutdownUI = typeof triggerShutdownUI !== 'undefined' ? triggerShutdownUI : undefined;
    window.checkServerHeartbeat = typeof checkServerHeartbeat !== 'undefined' ? checkServerHeartbeat : undefined;
  } catch (err) {
    console.error('[GeminiTrans Error Boundary - Core Management]', err);
    if (window.showToast) {
      window.showToast('Lỗi khởi tạo module Core Management: ' + err.message, 'error');
    }
  }
})(window, document);
