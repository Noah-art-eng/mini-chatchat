import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

import requests


API_BASE = os.getenv(
    "MINI_CHATCHAT_API_BASE",
    "http://127.0.0.1:8000"
).rstrip("/")

ROOT_DIR = Path(__file__).resolve().parents[1]
SAMPLE_FILE = ROOT_DIR / "test_files" / "sample_rag.txt"
EXPORT_KB = "e2e_export_import_test"
IMPORT_KB = "e2e_imported_test"


def pass_step(message):
    print(f"[PASS] {message}")


def fail_step(message, response=None):
    print(f"[FAIL] {message}")

    if response is not None:
        print(f"status={response.status_code}")
        print(f"body={response.text[:2000]}")

    sys.exit(1)


def request(method, path, **kwargs):
    try:
        return requests.request(
            method,
            f"{API_BASE}{path}",
            timeout=60,
            **kwargs,
        )
    except requests.RequestException as exc:
        print(f"[FAIL] request failed: {method} {path}")
        print(exc)
        sys.exit(1)


def json_response(response, message):
    try:
        return response.json()
    except ValueError:
        fail_step(message, response)


def expect_ok(response, message):
    if response.status_code >= 400:
        fail_step(message, response)

    data = None
    content_type = response.headers.get("content-type", "")

    if "application/json" in content_type:
        data = json_response(response, message)
        if data.get("error"):
            fail_step(message, response)

    pass_step(message)
    return data


def delete_kb_if_exists(kb_name):
    response = request("DELETE", f"/knowledge_bases/{kb_name}")

    if response.status_code >= 400:
        fail_step(f"delete existing KB {kb_name}", response)

    pass_step(f"delete existing KB if present: {kb_name}")


def create_and_switch_kb(kb_name):
    response = request(
        "POST",
        "/knowledge_bases",
        json={"kb_name": kb_name},
    )
    expect_ok(response, f"create KB {kb_name}")

    response = request(
        "POST",
        "/switch_kb",
        json={"kb_name": kb_name},
    )
    expect_ok(response, f"switch KB {kb_name}")


def upload_sample():
    with SAMPLE_FILE.open("rb") as file:
        response = request(
            "POST",
            "/upload",
            files={"file": (SAMPLE_FILE.name, file, "text/plain")},
        )

    expect_ok(response, "upload sample_rag.txt")


def get_documents():
    response = request("GET", "/documents")
    data = expect_ok(response, "GET /documents")
    return data.get("files", [])


def find_sample_document(files):
    return next(
        (
            item
            for item in files
            if item.get("filename") == SAMPLE_FILE.name
        ),
        None,
    )


def assert_sample_indexed():
    files = get_documents()
    sample = find_sample_document(files)

    if not sample:
        fail_step("sample_rag.txt not found in /documents")

    if sample.get("status") != "indexed":
        fail_step(
            f"sample_rag.txt status is {sample.get('status')}, expected indexed"
        )

    pass_step("sample_rag.txt exists with status=indexed")


def export_zip(temp_dir):
    response = request(
        "GET",
        f"/knowledge_bases/{EXPORT_KB}/export",
    )

    if response.status_code != 200:
        fail_step("export KB zip", response)

    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        fail_step("export returned JSON instead of zip", response)

    zip_path = Path(temp_dir) / f"{EXPORT_KB}_export.zip"
    zip_path.write_bytes(response.content)
    pass_step("export KB zip")
    return zip_path


def assert_export_zip(zip_path):
    with zipfile.ZipFile(zip_path, "r") as zip_file:
        names = zip_file.namelist()

        required = [
            "metadata.json",
            "content/",
            "uploads/",
            "vector_store/",
        ]

        for item in required:
            if item.endswith("/"):
                if not any(name.startswith(item) for name in names):
                    fail_step(f"zip missing {item}")
            elif item not in names:
                fail_step(f"zip missing {item}")

        metadata = json.loads(
            zip_file.read("metadata.json").decode("utf-8")
        )

    if metadata.get("version") != 1:
        fail_step("metadata version is not 1")

    if metadata.get("kb_name") != EXPORT_KB:
        fail_step("metadata kb_name mismatch")

    if not metadata.get("files"):
        fail_step("metadata files is empty")

    metadata_text = json.dumps(metadata)
    if "OPENAI_API_KEY" in metadata_text:
        fail_step("metadata contains OPENAI_API_KEY")

    pass_step("export zip structure and metadata")
    return metadata


def rewrite_zip_with_import_name(source_zip, temp_dir):
    extract_dir = Path(temp_dir) / "rewrite"
    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(source_zip, "r") as zip_file:
        zip_file.extractall(extract_dir)

    metadata_path = extract_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["kb_name"] = IMPORT_KB
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    target_zip = Path(temp_dir) / f"{IMPORT_KB}_import.zip"
    with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for path in extract_dir.rglob("*"):
            if path.is_file():
                zip_file.write(path, path.relative_to(extract_dir))

    pass_step("rewrite metadata kb_name and repack zip")
    return target_zip


def import_zip(zip_path):
    with zip_path.open("rb") as file:
        response = request(
            "POST",
            "/knowledge_bases/import",
            files={"file": (zip_path.name, file, "application/zip")},
            data={"override": "false"},
        )

    data = expect_ok(response, "import rewritten KB zip")

    if data.get("kb_name") != IMPORT_KB:
        fail_step("import response kb_name mismatch", response)

    pass_step("import response kb_name matches")


def switch_kb(kb_name):
    response = request(
        "POST",
        "/switch_kb",
        json={"kb_name": kb_name},
    )
    expect_ok(response, f"switch KB {kb_name}")


def verify_imported_search():
    response = request(
        "POST",
        "/kb_chat",
        json={
            "mode": "local_kb",
            "kb_name": IMPORT_KB,
            "query": "Mini ChatChat",
            "return_direct": True,
            "stream": False,
        },
    )
    data = expect_ok(response, "kb_chat return_direct imported KB")

    results = (
        data.get("sources")
        or data.get("results")
        or data.get("docs")
        or []
    )

    if not results:
        fail_step("kb_chat return_direct returned no sources", response)

    found = any(
        "sample_rag" in item.get("source", "")
        or "Mini ChatChat" in item.get("chunk", "")
        for item in results
    )

    if not found:
        fail_step(
            "kb_chat sources do not reference sample_rag or Mini ChatChat",
            response,
        )

    pass_step("imported KB return_direct search finds sample content")


def cleanup():
    for kb_name in (EXPORT_KB, IMPORT_KB):
        response = request("DELETE", f"/knowledge_bases/{kb_name}")
        if response.status_code >= 400:
            print(f"[WARN] cleanup failed for {kb_name}: {response.text[:500]}")
        else:
            pass_step(f"cleanup KB {kb_name}")


def main():
    print(f"API_BASE={API_BASE}")

    if not SAMPLE_FILE.exists():
        fail_step(f"missing test file: {SAMPLE_FILE}")

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            delete_kb_if_exists(EXPORT_KB)
            delete_kb_if_exists(IMPORT_KB)

            create_and_switch_kb(EXPORT_KB)
            upload_sample()
            assert_sample_indexed()

            exported_zip = export_zip(temp_dir)
            assert_export_zip(exported_zip)

            import_zip_path = rewrite_zip_with_import_name(
                exported_zip,
                temp_dir,
            )

            delete_kb_if_exists(IMPORT_KB)
            import_zip(import_zip_path)

            switch_kb(IMPORT_KB)
            assert_sample_indexed()
            verify_imported_search()
        finally:
            cleanup()

    print("[PASS] KB export/import E2E completed")


if __name__ == "__main__":
    main()
