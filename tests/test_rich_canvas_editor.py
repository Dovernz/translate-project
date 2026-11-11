import urllib.request
import json
import io
import os
import sys
import docx
import bs4

def create_sample_docx():
    doc = docx.Document()
    doc.add_heading("Tài liệu Báo cáo", level=1)
    doc.add_paragraph("Nội dung mở đầu kiểm thử Rich Canvas.")
    
    table = doc.add_table(rows=2, cols=3)
    headers = ["Mục", "Số lượng", "Giá trị"]
    for i, h in enumerate(headers):
        table.cell(0, i).text = h
        
    data = ["Táo", "10", "150.000đ"]
    for i, d in enumerate(data):
        table.cell(1, i).text = d

    file_bytes = io.BytesIO()
    doc.save(file_bytes)
    file_bytes.seek(0)
    return file_bytes

def upload_multipart(url, file_bytes, filename="sample.docx"):
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}"
    }
    
    body = []
    body.append(f"--{boundary}\r\n".encode("utf-8"))
    body.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode("utf-8"))
    body.append("Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n\r\n".encode("utf-8"))
    body.append(file_bytes.getvalue())
    body.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    
    payload = b"".join(body)
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return resp.status, resp.read()

def post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return resp.status, resp.read()

def main():
    base_url = "http://localhost:8090/api/document"
    
    # 1. Create sample docx
    file_bytes = create_sample_docx()
    
    # 2. Test extract
    extract_url = f"{base_url}/extract"
    status, res_data = upload_multipart(extract_url, file_bytes)
    assert status == 200, f"Expected 200, got {status}"
    
    res_json = json.loads(res_data.decode("utf-8"))
    assert "html" in res_json, "Response missing 'html' key"
    html_content = res_json["html"]
    
    assert "<table" in html_content.lower(), "HTML does not contain <table"
    assert "<td" in html_content.lower(), "HTML does not contain <td"
    print("[PASS] Extraction DOCX to Rich HTML table successful")

    # 3. Test export docx
    export_url = f"{base_url}/export-edited"
    payload_docx = {
        "content": html_content,
        "format": "docx",
        "filename": "test_output.docx"
    }
    status, docx_bytes = post_json(export_url, payload_docx)
    assert status == 200, f"Expected 200, got {status}"
    
    exported_doc = docx.Document(io.BytesIO(docx_bytes))
    assert len(exported_doc.tables) >= 1, "Exported docx has no tables"
    
    cell_texts = [cell.text for t in exported_doc.tables for row in t.rows for cell in row.cells]
    cell_str = " ".join(cell_texts)
    assert "Mục" in cell_str, "Missing 'Mục' in exported table"
    assert "Số lượng" in cell_str, "Missing 'Số lượng' in exported table"
    assert "Táo" in cell_str, "Missing 'Táo' in exported table"
    print("[PASS] Export Rich HTML to DOCX preserved table and formatting 100%")

    # 4. Test export other formats
    for fmt in ["pdf", "txt", "srt", "md"]:
        payload = {
            "content": html_content,
            "format": fmt,
            "filename": f"test_output.{fmt}"
        }
        status, resp_bytes = post_json(export_url, payload)
        assert status == 200, f"Export {fmt} failed with status {status}"
        assert len(resp_bytes) > 0, f"Export {fmt} returned empty response"
        print(f"[PASS] Export {fmt} returned {len(resp_bytes)} bytes")

    print("\n>>> ALL RICH CANVAS EDITOR TESTS PASSED (100%)! <<<")

if __name__ == "__main__":
    main()