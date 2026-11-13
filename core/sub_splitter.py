import math

def seconds_to_vtt_time(seconds: float) -> str:
    """Chuyển đổi số giây thành định dạng thời gian VTT: HH:MM:SS.mmm"""
    if seconds is None:
        seconds = 0.0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int(round((seconds - int(seconds)) * 1000))
    
    # Đề phòng trường hợp làm tròn milliseconds lên 1000
    if milliseconds >= 1000:
        milliseconds = 0
        secs += 1
    if secs >= 60:
        secs = 0
        minutes += 1
    if minutes >= 60:
        minutes = 0
        hours += 1

    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"

def _get_field(item, field_name, default=None):
    """Hỗ trợ lấy dữ liệu từ cả dict và object."""
    if isinstance(item, dict):
        return item.get(field_name, default)
    else:
        return getattr(item, field_name, default)

def segment_subtitles(subtitles, max_duration=6.0):
    """
    Chia nhỏ danh sách subtitle sao cho thời lượng mỗi cue không vượt quá max_duration.
    Hỗ trợ cả dict và object. Đảm bảo assert end - start <= max_duration.
    """
    processed_cues = []
    global_id = 1

    for sub in subtitles:
        # Lấy thông tin từ sub (hỗ trợ dict và object)
        start = _get_field(sub, 'start', 0.0)
        end = _get_field(sub, 'end', 0.0)
        
        # Lấy text từ các trường phổ biến ('text', 'original', 'content')
        text = _get_field(sub, 'text', None)
        if text is None:
            text = _get_field(sub, 'original', '')
            
        translated = _get_field(sub, 'translated', '')

        duration = end - start

        # Nếu duration nằm trong giới hạn cho phép, giữ nguyên
        if duration <= max_duration or duration <= 0:
            assert duration <= max_duration or duration <= 0, f"Duration {duration} vượt quá max_duration {max_duration}"
            
            cue_dict = {
                "id": global_id,
                "start": start,
                "end": end,
                "start_str": seconds_to_vtt_time(start),
                "end_str": seconds_to_vtt_time(end),
                "original": text,
                "text": text,
                "translated": translated
            }
            processed_cues.append(cue_dict)
            global_id += 1
        else:
            # Nếu vượt quá max_duration, tiến hành chia nhỏ
            num_parts = max(2, math.ceil(duration / max_duration))
            part_duration = duration / num_parts
            
            # Tách từ trong text
            words = text.split() if text else []
            num_words = len(words)
            
            for i in range(num_parts):
                part_start = start + i * part_duration
                # Đảm bảo phần cuối cùng khớp chính xác với end gốc
                part_end = start + (i + 1) * part_duration if i < num_parts - 1 else end
                
                actual_duration = part_end - part_start
                # Đảm bảo nghiêm ngặt điều kiện KHÔNG BAO GIỜ vượt quá max_duration (sai số do float nhỏ)
                assert actual_duration <= max_duration + 1e-5, f"Part duration {actual_duration} vượt quá max_duration {max_duration}"

                # Chia đều các từ cho các phần
                # Nếu hết từ thì để trống
                start_word_idx = (i * num_words) // num_parts
                end_word_idx = ((i + 1) * num_words) // num_parts
                
                if start_word_idx < num_words:
                    part_words = words[start_word_idx:end_word_idx]
                    part_text = " ".join(part_words)
                else:
                    part_text = ""

                cue_dict = {
                    "id": global_id,
                    "start": part_start,
                    "end": part_end,
                    "start_str": seconds_to_vtt_time(part_start),
                    "end_str": seconds_to_vtt_time(part_end),
                    "original": part_text,
                    "text": part_text,
                    "translated": translated if i == 0 else "" # Giữ bản dịch ở phần đầu hoặc để trống tùy ý
                }
                processed_cues.append(cue_dict)
                global_id += 1

    return processed_cues