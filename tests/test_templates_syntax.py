import re
from pathlib import Path
import pytest


def test_html_no_unquoted_js_identifiers():
    """Kiểm tra xem tệp templates/index.html có chứa lỗi

    JavaScript thiếu dấu nháy (unquoted identifier) trong các câu lệnh
    truy vấn DOM phổ biến như getElementById, querySelector, v.v.
    Ví dụ lỗi: getElementById(my-id) thay vì getElementById('my-id').
    """
    html_path = Path("templates/index.html")

    # Bỏ qua test nếu tệp không tồn tại
    if not html_path.exists():
        pytest.skip("Tệp templates/index.html không tồn tại.")

    content = html_path.read_text(encoding="utf-8")

    # Biểu thức chính quy tìm các hàm JS phổ biến nhận vào string nhưng thiếu dấu nháy
    # Ví dụ: getElementById(unquoted-id)
    pattern = re.compile(
        r"\b(?:getElementById|querySelector|querySelectorAll|getElementsByClassName|getElementsByTagName)\s*\(\s*([a-zA-Z0-9_-]+)\s*\)"
    )

    matches = pattern.findall(content)

    # Valid JavaScript variables cannot contain hyphens (-).
    # If a call contains a hyphen like getElementById(sub-card-), it is an invalid unquoted string or syntax error.
    invalid_matches = [m for m in matches if '-' in m]

    assert not invalid_matches, f"Found invalid unquoted identifiers with hyphens: {invalid_matches}"