import sys

new_css = """/* Fine-tune Light Mode Components */
    html[data-mode="light"] nav.bg-slate-800\/80 {
      background-color: #e2e8f0 !important;
      border-color: #cbd5e1 !important;
    }
    html[data-mode="light"] nav button:not(.bg-indigo-600) {
      color: #475569 !important;
    }
    html[data-mode="light"] nav button:not(.bg-indigo-600):hover {
      color: #0f172a !important;
      background-color: rgba(255, 255, 255, 0.8) !important;
    }
    html[data-mode="light"] #header-logo div {
      background-color: var(--bg-surface-elevated) !important;
      border-color: var(--border-main) !important;
    }
    html[data-mode="light"] #header-logo i {
      color: var(--accent-primary) !important;
    }
    html[data-mode="light"] .shadow-inner {
      box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.05) !important;
    }
    html[data-mode="light"] .shadow-2xl {
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.06) !important;
    }
    /* Base Body and Fonts */
    body {
      font-family: 'Inter', sans-serif;
      background-color: var(--bg-app) !important;
      color: var(--text-primary) !important;
      transition: background-color 0.2s ease, color 0.2s ease;
    }

    header {
      background-color: var(--bg-surface) !important;
      border-color: var(--border-main) !important;
    }

    #mobile-drawer-panel, #pool-modal > div, #theme-menu-popover, #export-choice-modal > div, #client-burn-modal > div {
      background-color: var(--bg-surface) !important;
      border-color: var(--border-main) !important;
      color: var(--text-primary) !important;
    }

    /* ========================================================================== */
    /* UNIFIED SURFACE & CONTAINER SHADING RULES                                 */
    /* ========================================================================== */
    .bg-slate-950 {
      background-color: var(--bg-app) !important;
    }
    .bg-slate-900 {
      background-color: var(--bg-surface) !important;
    }
    .bg-slate-900\/80,
    .bg-slate-900\/90,
    .bg-slate-900\/60,
    .bg-slate-900\/50 {
      background-color: var(--bg-surface) !important;
    }
    .bg-slate-800,
    .bg-slate-800\/40,
    .bg-slate-800\/50,
    .bg-slate-800\/60,
    .bg-slate-800\/70,
    .bg-slate-800\/80,
    .bg-slate-800\/90 {
      background-color: var(--bg-surface-elevated) !important;
    }
    .hover\:bg-slate-800:hover,
    .hover\:bg-slate-700:hover,
    .hover\:bg-slate-700\/50:hover,
    .hover\:bg-slate-700\/80:hover {
      background-color: var(--bg-surface-elevated) !important;
      filter: brightness(1.08);
    }
    .border-slate-800,
    .border-slate-800\/50,
    .border-slate-800\/60,
    .border-slate-800\/70,
    .border-slate-800\/80 {
      border-color: var(--border-main) !important;
    }
    .border-slate-700,
    .border-slate-700\/60,
    .border-slate-700\/70,
    .border-slate-700\/80 {
      border-color: var(--border-subtle) !important;
    }
    .divide-slate-800,
    .divide-slate-800\/50,
    .divide-slate-800\/60 {
      border-color: var(--border-main) !important;
    }

    /* ========================================================================== */
    /* DUAL-COLOR TYPOGRAPHY: TRIỆT TIÊU TOÀN BỘ MÀU CHỮ VỤN VẶT                  */
    /* ========================================================================== */
    .text-white,
    .text-slate-100,
    .text-slate-200 {
      color: var(--text-primary);
    }
    .text-slate-300,
    .text-slate-400,
    .text-slate-500 {
      color: var(--text-secondary);
    }

    /* Đảm bảo chữ trên bề mặt cards/nội dung Light Mode luôn đậm nét chuẩn WCAG AAA/AA */
    html[data-mode="light"] .text-white,
    html.light .text-white,
    html[data-mode="light"] .text-slate-100,
    html.light .text-slate-100,
    html[data-mode="light"] .text-slate-200,
    html.light .text-slate-200 {
      color: #0f172a !important;
    }
    html[data-mode="light"] .text-slate-300,
    html.light .text-slate-300,
    html[data-mode="light"] .text-slate-400,
    html.light .text-slate-400,
    html[data-mode="light"] .text-slate-500,
    html.light .text-slate-500 {
      color: #475569 !important;
    }

    /* Đồng bộ các text/icon màu vụn vặt sang màu nhấn duy nhất của Theme */
    .text-cyan-400, .text-cyan-300, .text-cyan-200,
    .text-amber-400, .text-amber-300,
    .text-purple-400, .text-purple-300,
    .text-indigo-400, .text-indigo-300 {
      color: var(--accent-text) !important;
    }
    .fill-cyan-400, .fill-amber-400, .fill-indigo-400 {
      fill: var(--accent-text) !important;
    }

    /* Subtle Accent Backgrounds and Borders */
    .bg-cyan-500\/10, .bg-cyan-500\/15, .bg-cyan-500\/20,
    .bg-amber-500\/10, .bg-indigo-500\/10, .bg-indigo-500\/20 {
      background-color: var(--accent-subtle) !important;
    }
    .border-cyan-500\/20, .border-cyan-500\/30,
    .border-indigo-500\/20, .border-indigo-500\/30 {
      border-color: var(--accent-border) !important;
    }

    /* ========================================================================== */
    /* UNIFIED ACCENT CONTROLS & SOLID BUTTONS: BẢO VỆ CHỮ TRẮNG 100%             */
    /* ========================================================================== */
    .bg-indigo-600,
    .bg-indigo-500,
    .btn-solid-primary,
    button.bg-indigo-600,
    a.bg-indigo-600,
    label.bg-indigo-600,
    html[data-mode="light"] .bg-indigo-600,
    html[data-mode="light"] .btn-solid-primary,
    html[data-mode="light"] button.bg-indigo-600,
    html[data-mode="light"] a.bg-indigo-600,
    html[data-mode="light"] label.bg-indigo-600,
    html.light .bg-indigo-600,
    html.light .btn-solid-primary,
    html.light button.bg-indigo-600,
    html.light a.bg-indigo-600,
    html.light label.bg-indigo-600 {
      background-color: var(--accent-primary) !important;
      color: #ffffff !important;
      border-color: var(--accent-border) !important;
    }

    /* Bắt buộc toàn bộ phần tử con bên trong nút Accent (spans, icons, badges) giữ nguyên chữ TRẮNG tinh khôi */
    .bg-indigo-600 *,
    .bg-indigo-500 *,
    .btn-solid-primary *,
    button.bg-indigo-600 *,
    a.bg-indigo-600 *,
    label.bg-indigo-600 *,
    html[data-mode="light"] .bg-indigo-600 *,
    html[data-mode="light"] .bg-indigo-500 *,
    html[data-mode="light"] .btn-solid-primary *,
    html[data-mode="light"] button.bg-indigo-600 *,
    html[data-mode="light"] a.bg-indigo-600 *,
    html[data-mode="light"] label.bg-indigo-600 *,
    html.light .bg-indigo-600 *,
    html.light .btn-solid-primary *,
    html.light button.bg-indigo-600 *,
    html.light a.bg-indigo-600 *,
    html.light label.bg-indigo-600 * {
      color: #ffffff !important;
      fill: #ffffff !important;
    }

    .hover\:bg-indigo-700:hover,
    .hover\:bg-indigo-600:hover,
    .btn-solid-primary:hover,
    html[data-mode="light"] .bg-indigo-600:hover,
    html[data-mode="light"] .btn-solid-primary:hover,
    html[data-mode="light"] button.bg-indigo-600:hover {
      background-color: var(--accent-hover) !important;
      color: #ffffff !important;
    }

    .border-indigo-500,
    .border-indigo-600 {
      border-color: var(--accent-primary) !important;
    }
    .focus\:border-indigo-500:focus,
    .focus\:ring-indigo-500:focus {
      border-color: var(--accent-primary) !important;
      --tw-ring-color: var(--accent-primary) !important;
    }

    /* Bảo vệ các nút màu xanh lục / emerald (như nút Xuất Hardsub, Tải Manga zip) */
    .bg-emerald-600,
    button.bg-emerald-600,
    a.bg-emerald-600,
    html[data-mode="light"] .bg-emerald-600,
    html[data-mode="light"] button.bg-emerald-600,
    html[data-mode="light"] a.bg-emerald-600 {
      background-color: #059669 !important;
      color: #ffffff !important;
    }
    .bg-emerald-600 *,
    button.bg-emerald-600 *,
    a.bg-emerald-600 *,
    html[data-mode="light"] .bg-emerald-600 *,
    html[data-mode="light"] button.bg-emerald-600 *,
    html[data-mode="light"] a.bg-emerald-600 * {
      color: #ffffff !important;
      fill: #ffffff !important;
    }
    .bg-emerald-600:hover,
    button.bg-emerald-600:hover,
    html[data-mode="light"] .bg-emerald-600:hover,
    html[data-mode="light"] button.bg-emerald-600:hover {
      background-color: #047857 !important;
      color: #ffffff !important;
    }

    /* Nút phụ (Secondary Buttons) trong Light Mode: Nền xám sáng, viền rõ, chữ than đậm */
    html[data-mode="light"] button.bg-slate-800,
    html[data-mode="light"] button.bg-slate-700,
    html[data-mode="light"] a.bg-slate-800,
    html[data-mode="light"] a.bg-slate-700,
    html[data-mode="light"] label.bg-slate-800,
    html[data-mode="light"] label.bg-slate-700 {
      background-color: #f1f5f9 !important;
      color: #0f172a !important;
      border: 1px solid #cbd5e1 !important;
    }
    html[data-mode="light"] button.bg-slate-800 *,
    html[data-mode="light"] button.bg-slate-700 *,
    html[data-mode="light"] a.bg-slate-800 *,
    html[data-mode="light"] a.bg-slate-700 *,
    html[data-mode="light"] label.bg-slate-800 *,
    html[data-mode="light"] label.bg-slate-700 * {
      color: #0f172a !important;
    }
    html[data-mode="light"] button.bg-slate-800:hover,
    html[data-mode="light"] button.bg-slate-700:hover,
    html[data-mode="light"] a.bg-slate-800:hover,
    html[data-mode="light"] a.bg-slate-700:hover,
    html[data-mode="light"] label.bg-slate-800:hover,
    html[data-mode="light"] label.bg-slate-700:hover {
      background-color: #e2e8f0 !important;
      color: #000000 !important;
      border-color: #94a3b8 !important;
    }

    /* Inputs, select, and textarea chuẩn Light Mode */
    html[data-mode="light"] input[type="text"],
    html[data-mode="light"] input[type="number"],
    html[data-mode="light"] input[type="password"],
    html[data-mode="light"] textarea:not(#src-text):not(#target-text),
    html[data-mode="light"] select {
      background-color: #ffffff !important;
      color: #0f172a !important;
      border: 1px solid #cbd5e1 !important;
    }
    html[data-mode="light"] input::placeholder,
    html[data-mode="light"] textarea::placeholder {
      color: #94a3b8 !important;
      opacity: 1 !important;
    }
    html[data-mode="light"] input:focus,
    html[data-mode="light"] textarea:focus,
    html[data-mode="light"] select:focus {
      border-color: var(--accent-primary) !important;
      outline: 2px solid var(--accent-subtle) !important;
    }
    html[data-mode="light"] #src-text {
      background-color: transparent !important;
      border: none !important;
      color: #0f172a !important;
    }
    html[data-mode="light"] #target-text {
      color: #0f172a !important;
    }

    /* Inputs, select, and textarea mặc định Dark Mode */
    html[data-mode="dark"] input[type="text"],
    html[data-mode="dark"] input[type="number"],
    html[data-mode="dark"] input[type="password"],
    html[data-mode="dark"] textarea:not(#src-text):not(#target-text),
    html[data-mode="dark"] select {
      background-color: var(--bg-surface-elevated) !important;
      color: var(--text-primary) !important;
      border-color: var(--border-subtle) !important;
    }
    html[data-mode="dark"] input::placeholder,
    html[data-mode="dark"] textarea::placeholder {
      color: var(--text-secondary) !important;
      opacity: 0.7;
    }

    /* Strict 10px Max Border Radius Rule */
    * {
      border-radius: min(10px, inherit);
    }
    .rounded-\[8px\], .rounded-lg, .rounded-md, .rounded-xl {
      border-radius: 8px !important;
    }
    .rounded-full {
      border-radius: 9999px !important;
    }

    /* Status dot keeping indicator green */
    .status-dot {
      background-color: #10b981 !important;
    }

    /* Custom Theme Selector Styles */
    .theme-swatch-ring {
      transition: all 0.2s ease;
    }
    html[data-mode="dark"] .theme-item-active {
      border-color: var(--accent-primary) !important;
      background-color: var(--accent-subtle) !important;
      color: #ffffff !important;
    }
    html[data-mode="dark"] .theme-item-active * {
      color: var(--accent-text) !important;
    }
    html[data-mode="light"] .theme-item-active {
      border-color: var(--accent-primary) !important;
      background-color: var(--accent-subtle) !important;
      color: var(--accent-primary) !important;
      font-weight: 600 !important;
    }
    html[data-mode="light"] .theme-item-active * {
      color: var(--accent-primary) !important;
    }
    html[data-mode="light"] #theme-popover-options button:not(.theme-item-active),
    html[data-mode="light"] #drawer-theme-options-grid button:not(.theme-item-active) {
      color: #334155 !important;
      background-color: #ffffff !important;
      border: 1px solid #e2e8f0 !important;
    }
    html[data-mode="light"] #theme-popover-options button:not(.theme-item-active):hover,
    html[data-mode="light"] #drawer-theme-options-grid button:not(.theme-item-active):hover {
      color: #0f172a !important;
      background-color: #f1f5f9 !important;
      border-color: #cbd5e1 !important;
    }
    html[data-mode="light"] #popover-mode-dark:not(.bg-indigo-600),
    html[data-mode="light"] #popover-mode-light:not(.bg-indigo-600),
    html[data-mode="light"] #drawer-mode-btn-dark:not(.bg-indigo-600),
    html[data-mode="light"] #drawer-mode-btn-light:not(.bg-indigo-600),
    html[data-mode="light"] #drawer-lang-btn-vi:not(.bg-indigo-600),
    html[data-mode="light"] #drawer-lang-btn-en:not(.bg-indigo-600) {
      color: #475569 !important;
      background-color: transparent !important;
    }
    html[data-mode="light"] #popover-mode-dark:not(.bg-indigo-600):hover,
    html[data-mode="light"] #popover-mode-light:not(.bg-indigo-600):hover,
    html[data-mode="light"] #drawer-mode-btn-dark:not(.bg-indigo-600):hover,
    html[data-mode="light"] #drawer-mode-btn-light:not(.bg-indigo-600):hover,
    html[data-mode="light"] #drawer-lang-btn-vi:not(.bg-indigo-600):hover,
    html[data-mode="light"] #drawer-lang-btn-en:not(.bg-indigo-600):hover {
      color: #0f172a !important;
      background-color: rgba(255, 255, 255, 0.8) !important;
    }
"""

def patch_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    start_marker = '/* Fine-tune Light Mode Components */'
    end_marker = '</style>'

    idx_start = content.find(start_marker)
    idx_end = content.find(end_marker, idx_start)

    if idx_start == -1 or idx_end == -1:
        print(f'ERROR: markers not found in {path}')
        return False

    content_new = content[:idx_start] + new_css + '  ' + content[idx_end:]

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content_new)

    print(f'SUCCESS: Updated theme CSS in {path}')
    return True

if __name__ == '__main__':
    targets = [
        'D:/Thành/Translate/CODE/templates/index.html'
    ]
    for t in targets:
        patch_file(t)
