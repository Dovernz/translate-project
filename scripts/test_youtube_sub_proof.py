import os
import json
import sys
from PIL import Image, ImageDraw, ImageFont

# Thêm thư mục gốc vào path để import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import asyncio
from app import _fetch_and_translate_youtube_captions

def test_youtube_subtitles():
    url = 'https://youtu.be/It79k94XMTw'
    lang = 'vi'
    output_dir = os.path.join(os.path.dirname(__file__), '../Docs/proofs')
    os.makedirs(output_dir, exist_ok=True)

    print(f"--- Đang fetch sub từ: {url} ---")
    cues = asyncio.run(_fetch_and_translate_youtube_captions(url, lang))

    # 1. Kiểm tra số lượng câu > 10
    assert len(cues) > 10, f"Số lượng câu quá ít: {len(cues)}"
    
    # 2. Kiểm tra duration <= 6.0s
    for i, cue in enumerate(cues):
        duration = cue['end'] - cue['start']
        assert duration <= 6.0, f"Cue {i} quá dài: {duration}s"

    # 3. Lưu JSON
    json_path = os.path.join(output_dir, 'youtube_subtitles_segmented_proof.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(cues, f, ensure_ascii=False, indent=4)

    # 4. Vẽ ảnh PNG
    img_width = 800
    img_height = len(cues) * 30 + 50
    image = Image.new('RGB', (img_width, img_height), color='white')
    draw = ImageDraw.Draw(image)
    
    # Sử dụng font mặc định (hoặc load font .ttf nếu cần tiếng Việt hiển thị tốt)
    y_text = 20
    draw.text((10, 5), f"Total Cues: {len(cues)} | Status: PASS", fill='blue')
    
    for i, cue in enumerate(cues[:20]): # Chỉ vẽ 20 câu đầu để tránh ảnh quá dài
        cue_txt = cue.get('translated') or cue.get('original') or cue.get('text', '')
        text = f"{i+1}. [{cue['start']:.1f}s - {cue['end']:.1f}s]: {cue_txt[:50]}..."
        draw.text((10, y_text + (i * 30)), text, fill='black')

    img_path = os.path.join(output_dir, 'youtube_subtitles_segmented_proof.png')
    image.save(img_path)

    print(f"Số lượng câu: {len(cues)}")
    print("Trạng thái: PASS")
    print(f"Đã lưu proof tại: {output_dir}")

if __name__ == "__main__":
    try:
        test_youtube_subtitles()
    except Exception as e:
        print(f"Trạng thái: FAIL - {e}")