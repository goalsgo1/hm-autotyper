"""
HM AutoTyper - 배포용 패키지 생성 스크립트
실행: python package_release.py

build_exe.py로 EXE를 먼저 빌드한 후 실행하세요.
EXE + LICENSE + 사용법 + 테스트 에디터를 ZIP으로 묶어줍니다.
"""
import os
import sys
import zipfile
import datetime

# ═══════════════════════════════════════════════════════════════
# 설정
# ═══════════════════════════════════════════════════════════════

VERSION = "3.0.0"
APP_NAME = "HM_AutoTyper"

# ZIP 안에 들어갈 폴더 이름
RELEASE_FOLDER = f"{APP_NAME}_v{VERSION}"

# ═══════════════════════════════════════════════════════════════
# 패키징할 파일 목록
# ═══════════════════════════════════════════════════════════════

def get_file_list(script_dir):
    """패키지에 포함할 파일 목록 반환: (실제경로, ZIP내경로) 튜플 리스트"""
    files = []

    # 1. EXE 파일 (필수)
    exe_path = os.path.join(script_dir, "dist", f"{APP_NAME}.exe")
    if not os.path.exists(exe_path):
        return None, f"EXE 파일을 찾을 수 없습니다: {exe_path}\n먼저 python build_exe.py를 실행하세요."
    files.append((exe_path, f"{RELEASE_FOLDER}/{APP_NAME}.exe"))

    # 2. LICENSE.txt (필수)
    license_path = os.path.join(script_dir, "LICENSE.txt")
    if not os.path.exists(license_path):
        return None, f"LICENSE.txt를 찾을 수 없습니다: {license_path}"
    files.append((license_path, f"{RELEASE_FOLDER}/LICENSE.txt"))

    # 3. 사용법.txt
    usage_path = os.path.join(script_dir, "docs", "사용법.txt")
    if os.path.exists(usage_path):
        files.append((usage_path, f"{RELEASE_FOLDER}/사용법.txt"))

    # 4. 테스트방법.txt
    test_guide_path = os.path.join(script_dir, "docs", "테스트방법.txt")
    if os.path.exists(test_guide_path):
        files.append((test_guide_path, f"{RELEASE_FOLDER}/테스트방법.txt"))

    # 5. test_editor.html
    test_editor_path = os.path.join(script_dir, "test_editor.html")
    if os.path.exists(test_editor_path):
        files.append((test_editor_path, f"{RELEASE_FOLDER}/test_editor.html"))

    return files, None


# ═══════════════════════════════════════════════════════════════
# 메인
# ═══════════════════════════════════════════════════════════════

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    print()
    print("=" * 60)
    print(f"  {APP_NAME} v{VERSION} 배포 패키지 생성")
    print("=" * 60)
    print()

    # 파일 목록 확인
    files, error = get_file_list(script_dir)
    if error:
        print(f"  [오류] {error}")
        sys.exit(1)

    # ZIP 파일명
    zip_name = f"{APP_NAME}_v{VERSION}.zip"
    zip_path = os.path.join(script_dir, zip_name)

    # 기존 ZIP 삭제
    if os.path.exists(zip_path):
        os.remove(zip_path)
        print(f"  기존 파일 삭제: {zip_name}")

    # ZIP 생성
    print(f"  패키지 생성 중: {zip_name}")
    print()

    total_size = 0
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for src_path, zip_inner_path in files:
            file_size = os.path.getsize(src_path)
            total_size += file_size
            size_str = format_size(file_size)
            print(f"    추가: {os.path.basename(src_path):30s} ({size_str})")
            zf.write(src_path, zip_inner_path)

    # 결과
    zip_size = os.path.getsize(zip_path)
    print()
    print("-" * 60)
    print(f"  파일 수:     {len(files)}개")
    print(f"  원본 크기:   {format_size(total_size)}")
    print(f"  압축 크기:   {format_size(zip_size)}")
    print(f"  압축률:      {(1 - zip_size / total_size) * 100:.1f}%")
    print()
    print(f"  생성 완료:   {zip_name}")
    print(f"  경로:        {zip_path}")
    print()
    print("  ZIP 파일 내부 구조:")
    print(f"    {RELEASE_FOLDER}/")
    for _, zip_inner_path in files:
        name = zip_inner_path.split("/", 1)[1]
        print(f"      ├── {name}")
    print()
    print("  이 ZIP 파일을 배포하면 됩니다.")
    print("=" * 60)
    print()


def format_size(size_bytes):
    """바이트를 읽기 좋은 단위로 변환"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


if __name__ == "__main__":
    main()
