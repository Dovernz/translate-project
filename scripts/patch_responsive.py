import os
import re

html_path = r"D:\Thành\Translate\CODE\templates\index.html"

with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Meta Viewport
old_meta = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
new_meta = '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">'
if old_meta in content:
    content = content.replace(old_meta, new_meta, 1)
    print("1. Meta viewport updated.")
else:
    print("1. Meta viewport already updated or not found.")

# 2. Anti-overflow CSS & Touch Target
css_target = "</style>"
css_replacement = """    /* Responsive Layout & Touch Targets Enhancement */
    html, body {
      overflow-x: hidden !important;
      max-width: 100vw;
      -webkit-tap-highlight-color: transparent;
    }
    @media (max-width: 1023px) {
      button, [role="button"], select, input[type="button"], input[type="submit"] {
        min-height: 40px;
      }
    }
  </style>"""
if "/* Responsive Layout & Touch Targets Enhancement */" not in content and css_target in content:
    content = content.replace(css_target, css_replacement, 1)
    print("2. Responsive CSS added.")
else:
    print("2. Responsive CSS already exists or style tag not found.")

# 3. Hamburger menu button visibility: flex lg:hidden
old_btn = 'id="btn-mobile-menu" onclick="toggleDrawer()" class="p-2 sm:px-3 sm:py-2 rounded-[8px] bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white border border-slate-700 transition cursor-pointer active:scale-95 flex items-center gap-2 shadow-sm"'
new_btn = 'id="btn-mobile-menu" onclick="toggleDrawer()" class="flex lg:hidden p-2 sm:px-3 sm:py-2 rounded-[8px] bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white border border-slate-700 transition cursor-pointer active:scale-95 items-center justify-center gap-2 shadow-sm min-h-[40px] min-w-[40px]"'
if old_btn in content:
    content = content.replace(old_btn, new_btn, 1)
    print("3. Hamburger button updated to flex lg:hidden.")
else:
    print("3. Hamburger button already updated or not matched.")

# 4. Center horizontal nav tabs: hidden lg:flex
old_nav = '<nav class="hidden md:flex items-center bg-slate-800/80 p-1 rounded-[8px] border border-slate-700/70 shadow-inner gap-1">'
new_nav = '<nav class="hidden lg:flex items-center bg-slate-800/80 p-1 rounded-[8px] border border-slate-700/70 shadow-inner gap-1">'
if old_nav in content:
    content = content.replace(old_nav, new_nav, 1)
    print("4. Nav tabs updated to hidden lg:flex.")
else:
    print("4. Nav tabs already updated or not matched.")

# 5. Header status button
old_status = """        <span class="text-xs px-2.5 py-1 rounded-[6px] bg-slate-800/80 text-slate-300 font-mono text-[11px] hidden sm:inline-flex items-center gap-1.5 border border-slate-700/80">
          <span class="w-1.5 h-1.5 status-dot bg-emerald-400"></span> 7 Keys Ready
        </span>"""
new_status = """        <button onclick="togglePoolModal()" class="text-xs px-2.5 py-1.5 rounded-[6px] bg-slate-800/80 hover:bg-slate-700 text-slate-300 font-mono text-[11px] hidden sm:inline-flex items-center gap-1.5 border border-slate-700/80 cursor-pointer transition shadow-sm" title="Xem trạng thái AI Studio Pool">
          <span class="w-1.5 h-1.5 status-dot bg-emerald-400"></span> 7 Keys Ready
        </button>"""
if old_status in content:
    content = content.replace(old_status, new_status, 1)
    print("5. Status pill updated to clickable button.")
else:
    print("5. Status pill already updated or not matched.")

# 6. Video subtitle customizer controls grid: grid-cols-1 sm:grid-cols-2 lg:grid-cols-4
old_sub_grid = '<div class="grid grid-cols-2 lg:grid-cols-4 gap-2.5 sm:gap-3 text-xs">'
new_sub_grid = '<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 sm:gap-3 text-xs">'
if old_sub_grid in content:
    content = content.replace(old_sub_grid, new_sub_grid, 1)
    print("6. Video customizer grid updated to grid-cols-1 sm:grid-cols-2 lg:grid-cols-4.")
else:
    print("6. Video customizer grid already updated or not matched.")

# 7. Document tab source & target grid: grid-cols-1 lg:grid-cols-2
old_doc_grid = '<div class="grid grid-cols-1 md:grid-cols-2 gap-4">'
new_doc_grid = '<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">'
if old_doc_grid in content:
    content = content.replace(old_doc_grid, new_doc_grid, 1)
    print("7. Document editor grid updated to grid-cols-1 lg:grid-cols-2.")
else:
    print("7. Document editor grid already updated or not matched.")

# 8. Transcribe tab grid: grid-cols-1 lg:grid-cols-3
old_trans_grid = '<div class="grid grid-cols-1 md:grid-cols-3 gap-4">'
new_trans_grid = '<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">'
if old_trans_grid in content:
    content = content.replace(old_trans_grid, new_trans_grid, 1)
    print("8. Transcribe grid updated to grid-cols-1 lg:grid-cols-3.")
else:
    print("8. Transcribe grid already updated or not matched.")

# 9. Modals max-width & margin auto
old_modal_export = '<div class="bg-slate-900 border border-slate-800 rounded-[10px] max-w-lg w-full p-6 shadow-lg border border-slate-800 space-y-4">'
new_modal_export = '<div class="bg-slate-900 border border-slate-800 rounded-[10px] w-full max-w-md sm:max-w-lg mx-auto p-4 sm:p-6 shadow-lg border border-slate-800 space-y-4">'
if old_modal_export in content:
    content = content.replace(old_modal_export, new_modal_export, 1)
    print("9a. Export modal updated.")

old_modal_burn = '<div class="bg-slate-900 border border-slate-800 rounded-[10px] max-w-md w-full p-6 shadow-lg border border-slate-800 space-y-4 text-center">'
new_modal_burn = '<div class="bg-slate-900 border border-slate-800 rounded-[10px] w-full max-w-sm sm:max-w-md mx-auto p-4 sm:p-6 shadow-lg border border-slate-800 space-y-4 text-center">'
if old_modal_burn in content:
    content = content.replace(old_modal_burn, new_modal_burn, 1)
    print("9b. Client burn modal updated.")

old_modal_pool = '<div class="bg-slate-900 border border-slate-800 rounded-[10px] max-w-2xl w-full p-6 shadow-lg border border-slate-800 space-y-4">'
new_modal_pool = '<div class="bg-slate-900 border border-slate-800 rounded-[10px] w-full max-w-md sm:max-w-2xl mx-auto p-4 sm:p-6 shadow-lg border border-slate-800 space-y-4">'
if old_modal_pool in content:
    content = content.replace(old_modal_pool, new_modal_pool, 1)
    print("9c. Pool modal updated.")

# 10. Auto-close drawer on window resize >= 1024px
resize_code = """    // Auto-close drawer when resizing to desktop >= 1024px
    window.addEventListener('resize', () => {
      if (window.innerWidth >= 1024) {
        const drawer = document.getElementById('mobile-drawer');
        if (drawer && !drawer.classList.contains('hidden')) {
          closeDrawer();
        }
      }
    });
"""
if "window.innerWidth >= 1024" not in content and "function switchDrawerTab(tab)" in content:
    content = content.replace("function switchDrawerTab(tab) {", resize_code + "\n    function switchDrawerTab(tab) {", 1)
    print("10. Window resize listener added.")
else:
    print("10. Window resize listener already exists or target not found.")

with open(html_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Finished saving updated index.html!")
