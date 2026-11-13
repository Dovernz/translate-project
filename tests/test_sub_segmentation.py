import re
import pytest

from core.sub_splitter import segment_subtitles
from core.video_helper import parse_subtitles_from_ai


def _get(obj, key, default=None):
    """Helper function hỗ trợ truy cập thuộc tính object hoặc dict key."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class MockCue:
    """Mock object đại diện cho một phụ đề/cue."""
    def __init__(self, start, end, text="", start_str="", end_str=""):
        self.start = start
        self.end = end
        self.text = text
        self.start_str = start_str
        self.end_str = end_str

    def __repr__(self):
        return f"MockCue({self.start}->{self.end}, '{self.text}')"


def test_segment_subtitles_long_cue_split():
    """1. Kiểm tra cue dài 100 giây bị chia thành nhiều cue nhỏ <= 6s."""
    long_cue = MockCue(
        start=0.0,
        end=100.0,
        text="Đây là đoạn phụ đề rất dài kéo dài 100 giây cần phải được chia nhỏ thành nhiều đoạn.",
        start_str="00:00:00,000",
        end_str="00:01:40,000"
    )

    result = segment_subtitles([long_cue])

    assert len(result) > 1, "Cue dài 100 giây phải được chia thành nhiều cue nhỏ"
    for cue in result:
        start = _get(cue, "start")
        end = _get(cue, "end")
        duration = end - start
        assert duration <= 6.0 + 1e-5, f"Thời lượng của cue ({duration}s) không được vượt quá 6 giây"


def test_segment_subtitles_continuous_timestamps():
    """2. Kiểm tra start/end liên tục không bị gián đoạn, start_str/end_str hợp lệ."""
    long_cue = MockCue(
        start=0.0,
        end=100.0,
        text="Đoạn phụ đề kéo dài kiểm tra tính liên tục của mốc thời gian.",
        start_str="00:00:00,000",
        end_str="00:01:40,000"
    )

    result = segment_subtitles([long_cue])

    # Regex kiểm tra định dạng thời gian HH:MM:SS,mmm hoặc HH:MM:SS.mmm
    time_regex = re.compile(r"^\d{2}:\d{2}:\d{2}[,\.]\d{3}$")

    for i in range(len(result)):
        current_start = _get(result[i], "start")
        current_end = _get(result[i], "end")
        start_str = _get(result[i], "start_str")
        end_str = _get(result[i], "end_str")

        assert current_start < current_end, f"Cue {i}: start ({current_start}) phải nhỏ hơn end ({current_end})"

        if start_str and end_str:
            assert time_regex.match(start_str), f"Cue {i}: start_str không hợp lệ ({start_str})"
            assert time_regex.match(end_str), f"Cue {i}: end_str không hợp lệ ({end_str})"

        # Kiểm tra tính liên tục giữa cue hiện tại và cue tiếp theo
        if i < len(result) - 1:
            next_start = _get(result[i + 1], "start")
            assert pytest.approx(current_end) == next_start, (
                f"Gián đoạn thời gian tại vị trí cue {i} (end={current_end}) và cue {i+1} (start={next_start})"
            )


def test_segment_subtitles_short_cue_unchanged():
    """3. Kiểm tra cue ngắn <= 6s được giữ nguyên."""
    short_cue = MockCue(
        start=10.0,
        end=14.5,
        text="Phụ đề ngắn dưới 6 giây.",
        start_str="00:00:10,000",
        end_str="00:00:14,500"
    )

    result = segment_subtitles([short_cue])

    assert len(result) == 1, "Cue <= 6s phải giữ nguyên, không được phân chia"
    assert pytest.approx(_get(result[0], "start")) == 10.0
    assert pytest.approx(_get(result[0], "end")) == 14.5
    assert _get(result[0], "text") == "Phụ đề ngắn dưới 6 giây."


def test_parse_subtitles_from_ai_auto_segmentation():
    """4. Kiểm tra parse_subtitles_from_ai tự động phân đoạn."""
    ai_response = """
1
00:00:00,000 --> 00:01:40,000
Đây là đoạn phụ đề do AI phản hồi kéo dài 100 giây cần phải tự động chia nhỏ khi thực hiện parse.
"""

    parsed_cues = parse_subtitles_from_ai(ai_response)

    assert len(parsed_cues) > 1, "parse_subtitles_from_ai phải tự động chia các cue dài"

    for cue in parsed_cues:
        start = _get(cue, "start")
        end = _get(cue, "end")
        duration = end - start
        assert duration <= 6.0 + 1e-5, f"Cue sau khi parse tự động có thời lượng ({duration}s) vượt quá 6 giây"