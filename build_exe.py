"""
HM AutoTyper - EXE 빌드 스크립트 (진행률 표시 포함)
실행: python build_exe.py

옵션:
  --no-admin    관리자 권한 매니페스트 제외
  --console     콘솔 창 표시 (디버그용)
  --clean-only  빌드 캐시만 정리
"""
import subprocess
import sys
import os
import shutil
import time
import glob

# ═══════════════════════════════════════════════════════════════
# 설정
# ═══════════════════════════════════════════════════════════════

APP_NAME = "HM_AutoTyper"
SOURCE_FILE = "hm_autotyper.py"
VERSION = "3.0.0"
COPYRIGHT = "\u00a9 2026 haemin. All rights reserved."

HIDDEN_IMPORTS = [
    "pyautogui", "pyscreeze", "pytweening",
    "mouseinfo", "pygetwindow", "pymsgbox",
    "pyperclip",
]

# customtkinter 사용 시 추가 hidden imports
CTK_HIDDEN_IMPORTS = [
    "customtkinter",
    "darkdetect",
]

MANIFEST_CONTENT = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <application xmlns="urn:schemas-microsoft-com:asm.v3">
    <windowsSettings>
      <dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">true/pm</dpiAware>
      <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">PerMonitorV2</dpiAwareness>
    </windowsSettings>
  </application>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="requireAdministrator" uiAccess="false"/>
      </requestedPrivileges>
    </security>
  </trustInfo>
</assembly>
'''

MANIFEST_NO_ADMIN = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <application xmlns="urn:schemas-microsoft-com:asm.v3">
    <windowsSettings>
      <dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">true/pm</dpiAware>
      <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">PerMonitorV2</dpiAwareness>
    </windowsSettings>
  </application>
</assembly>
'''


# ═══════════════════════════════════════════════════════════════
# 진행률 표시 유틸리티
# ═══════════════════════════════════════════════════════════════

class ProgressTracker:
    """빌드 진행률 추적 및 표시"""

    def __init__(self, total_steps):
        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = time.time()
        self.step_times = []

    def step(self, description, detail=""):
        self.current_step += 1
        elapsed = time.time() - self.start_time
        pct = int(self.current_step / self.total_steps * 100)
        bar_len = 30
        filled = int(bar_len * self.current_step / self.total_steps)
        bar = "█" * filled + "░" * (bar_len - filled)

        print()
        print(f"  [{self.current_step}/{self.total_steps}] {bar} {pct}%  ({elapsed:.1f}s)")
        print(f"  → {description}")
        if detail:
            print(f"    {detail}")
        self.step_times.append(time.time())

    def done(self, success=True):
        elapsed = time.time() - self.start_time
        print()
        print("=" * 56)
        if success:
            print(f"  빌드 완료! (총 {elapsed:.1f}초 소요)")
        else:
            print(f"  빌드 실패. (총 {elapsed:.1f}초 경과)")
        print("=" * 56)


# ═══════════════════════════════════════════════════════════════
# 빌드 단계별 함수
# ═══════════════════════════════════════════════════════════════

def check_source(script_dir):
    """소스 파일 존재 확인"""
    source = os.path.join(script_dir, SOURCE_FILE)
    if not os.path.exists(source):
        print(f"  [오류] {SOURCE_FILE}을 찾을 수 없습니다!")
        print(f"  경로: {source}")
        return None
    size = os.path.getsize(source)
    lines = sum(1 for _ in open(source, encoding='utf-8'))
    print(f"    파일: {SOURCE_FILE} ({size:,} bytes, {lines:,} lines)")
    return source


def check_dependencies():
    """필요한 패키지 설치 확인 및 설치"""
    required = {
        'PyInstaller': 'pyinstaller',
        'pyautogui': 'pyautogui',
        'pyperclip': 'pyperclip',
    }
    optional = {
        'customtkinter': 'customtkinter',
    }

    missing = []
    for display_name, pkg_name in required.items():
        try:
            __import__(pkg_name.lower().replace('-', '_'))
            print(f"    [OK] {display_name}")
        except ImportError:
            missing.append(pkg_name)
            print(f"    [--] {display_name} (미설치)")

    has_ctk = False
    for display_name, pkg_name in optional.items():
        try:
            __import__(pkg_name.lower().replace('-', '_'))
            has_ctk = True
            print(f"    [OK] {display_name} (선택)")
        except ImportError:
            print(f"    [--] {display_name} (선택, 미설치)")

    if missing:
        print()
        print(f"    필수 패키지 설치 중: {', '.join(missing)}")
        for pkg in missing:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", pkg, "--user", "--no-cache-dir"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            print(f"      {pkg} 설치 완료")

    return has_ctk


def clean_previous_build(script_dir):
    """이전 빌드 파일 정리"""
    cleaned = []

    # 기존 exe 삭제
    old_exe = os.path.join(script_dir, "dist", f"{APP_NAME}.exe")
    if os.path.exists(old_exe):
        try:
            os.remove(old_exe)
            cleaned.append(f"{APP_NAME}.exe")
        except PermissionError:
            print(f"    [오류] {APP_NAME}.exe가 실행 중입니다!")
            print("    작업 관리자에서 종료한 후 다시 시도하세요.")
            return False

    # .spec 파일 삭제
    old_spec = os.path.join(script_dir, f"{APP_NAME}.spec")
    if os.path.exists(old_spec):
        os.remove(old_spec)
        cleaned.append(f"{APP_NAME}.spec")

    # build 폴더 정리
    build_dir = os.path.join(script_dir, "build")
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir, ignore_errors=True)
        cleaned.append("build/")

    # __pycache__ 정리
    cache_dir = os.path.join(script_dir, "__pycache__")
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir, ignore_errors=True)
        cleaned.append("__pycache__/")

    if cleaned:
        print(f"    정리됨: {', '.join(cleaned)}")
    else:
        print("    정리할 파일 없음")

    return True


def create_manifest(script_dir, use_admin=True):
    """매니페스트 파일 생성"""
    manifest_path = os.path.join(script_dir, "uac.manifest")
    content = MANIFEST_CONTENT if use_admin else MANIFEST_NO_ADMIN
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(content)
    mode = "관리자 권한" if use_admin else "일반 권한"
    print(f"    모드: {mode}")
    print(f"    DPI 인식: PerMonitorV2")
    return manifest_path


def create_version_info(script_dir):
    """Windows EXE 파일 속성에 표시될 버전 정보 파일 생성"""
    parts = VERSION.split(".")
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0

    version_info = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, 0),
    prodvers=({major}, {minor}, {patch}, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [StringStruct(u'CompanyName', u'haemin (hm.autotyper@gmail.com)'),
           StringStruct(u'FileDescription', u'HM AutoTyper - Korean/English Auto Typing Program'),
           StringStruct(u'FileVersion', u'{VERSION}'),
           StringStruct(u'InternalName', u'{APP_NAME}'),
           StringStruct(u'LegalCopyright', u'{COPYRIGHT}'),
           StringStruct(u'OriginalFilename', u'{APP_NAME}.exe'),
           StringStruct(u'ProductName', u'HM AutoTyper'),
           StringStruct(u'ProductVersion', u'{VERSION}')])
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
    version_path = os.path.join(script_dir, "version_info.txt")
    with open(version_path, "w", encoding="utf-8") as f:
        f.write(version_info)
    print(f"    저작권: {COPYRIGHT}")
    return version_path


def run_pyinstaller(script_dir, source_file, manifest_path, version_path=None,
                    has_ctk=False, windowed=True):
    """PyInstaller 실행 (실시간 출력 파싱으로 진행률 표시)"""

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--clean",
        "--name", APP_NAME,
        "--manifest", manifest_path,
        "--distpath", os.path.join(script_dir, "dist"),
        "--workpath", os.path.join(script_dir, "build"),
        "--specpath", script_dir,
    ]

    if version_path:
        cmd.extend(["--version-file", version_path])

    if windowed:
        cmd.append("--windowed")

    # Hidden imports
    for imp in HIDDEN_IMPORTS:
        cmd.extend(["--hidden-import", imp])

    if has_ctk:
        for imp in CTK_HIDDEN_IMPORTS:
            cmd.extend(["--hidden-import", imp])

    cmd.append(source_file)

    print(f"    명령어: pyinstaller --onefile {'--windowed ' if windowed else ''}"
          f"--name {APP_NAME}")
    print()

    # 실시간 출력 파싱
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    phase_map = {
        'Analyzing': '의존성 분석 중',
        'Processing': '모듈 처리 중',
        'Building PYZ': '압축 아카이브 생성 중',
        'Building PKG': '패키지 빌드 중',
        'Building EXE': 'EXE 파일 생성 중',
        'Appending PKG': 'PKG 결합 중',
    }
    current_phase = ""
    dot_count = 0

    for line in process.stdout:
        line = line.strip()
        if not line:
            continue

        # 단계 감지
        detected = False
        for key, desc in phase_map.items():
            if key in line:
                if current_phase != key:
                    if current_phase:
                        print()  # 이전 줄 마무리
                    current_phase = key
                    dot_count = 0
                    sys.stdout.write(f"    [{desc}]")
                    sys.stdout.flush()
                detected = True
                break

        if not detected and current_phase:
            dot_count += 1
            if dot_count % 5 == 0:
                sys.stdout.write(".")
                sys.stdout.flush()

    if current_phase:
        print()  # 마지막 줄 마무리

    process.wait()
    return process.returncode


def verify_output(script_dir):
    """생성된 EXE 파일 확인"""
    exe_path = os.path.join(script_dir, "dist", f"{APP_NAME}.exe")
    if os.path.exists(exe_path):
        size = os.path.getsize(exe_path)
        size_mb = size / (1024 * 1024)
        print(f"    파일: {exe_path}")
        print(f"    크기: {size_mb:.1f} MB ({size:,} bytes)")
        return exe_path
    else:
        print("    [오류] EXE 파일이 생성되지 않았습니다!")
        return None


def cleanup_temp(script_dir, manifest_path):
    """임시 파일 정리"""
    cleaned = []
    if manifest_path and os.path.exists(manifest_path):
        os.remove(manifest_path)
        cleaned.append("uac.manifest")

    version_info_path = os.path.join(script_dir, "version_info.txt")
    if os.path.exists(version_info_path):
        os.remove(version_info_path)
        cleaned.append("version_info.txt")

    # build 폴더는 선택적으로 유지 (디버그용)
    build_dir = os.path.join(script_dir, "build")
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir, ignore_errors=True)
        cleaned.append("build/")

    if cleaned:
        print(f"    정리됨: {', '.join(cleaned)}")


# ═══════════════════════════════════════════════════════════════
# 메인
# ═══════════════════════════════════════════════════════════════

def main():
    args = sys.argv[1:]
    use_admin = "--no-admin" not in args
    windowed = "--console" not in args
    clean_only = "--clean-only" in args

    script_dir = os.path.dirname(os.path.abspath(__file__))

    print()
    print("=" * 56)
    print(f"  {APP_NAME} v{VERSION} - EXE 빌드")
    print("=" * 56)

    if clean_only:
        print("\n  [정리 모드]")
        clean_previous_build(script_dir)
        print("\n  정리 완료!")
        return

    total_steps = 7
    progress = ProgressTracker(total_steps)

    # Step 1: 소스 파일 확인
    progress.step("소스 파일 확인")
    source_file = check_source(script_dir)
    if not source_file:
        progress.done(False)
        return

    # Step 2: 의존성 확인
    progress.step("패키지 의존성 확인")
    has_ctk = check_dependencies()

    # Step 3: 이전 빌드 정리
    progress.step("이전 빌드 파일 정리")
    if not clean_previous_build(script_dir):
        progress.done(False)
        return

    # Step 4: 매니페스트 생성
    progress.step("매니페스트 및 버전 정보 생성")
    manifest_path = create_manifest(script_dir, use_admin)
    version_path = create_version_info(script_dir)

    # Step 5: PyInstaller 빌드
    progress.step("PyInstaller EXE 빌드", "이 단계는 1~3분 소요될 수 있습니다...")
    returncode = run_pyinstaller(
        script_dir, source_file, manifest_path,
        version_path=version_path,
        has_ctk=has_ctk, windowed=windowed
    )

    # Step 6: 결과 확인
    progress.step("빌드 결과 확인")
    if returncode == 0:
        exe_path = verify_output(script_dir)
    else:
        exe_path = None
        print("    [오류] PyInstaller가 오류 코드를 반환했습니다.")

    # Step 7: 임시 파일 정리
    progress.step("임시 파일 정리")
    cleanup_temp(script_dir, manifest_path)

    # 최종 결과
    if exe_path:
        progress.done(True)
        print()
        print(f"  실행 파일: dist\\{APP_NAME}.exe")
        if use_admin:
            print("  (관리자 권한으로 실행됩니다)")
        print()
        print("  사용법:")
        print(f"    1. dist\\{APP_NAME}.exe 실행")
        print("    2. 텍스트 입력 후 F6으로 시작")
        print("    3. 대상 창에서 타이핑 진행")
    else:
        progress.done(False)
        print()
        print("  문제 해결:")
        print("    1. 안티바이러스가 차단하는지 확인")
        print("    2. pip install pyinstaller --upgrade")
        print("    3. --console 옵션으로 재시도")

    print()
    # 스크립트에서 직접 실행 시에만 input 대기
    if sys.stdin.isatty():
        input("아무 키나 눌러 종료...")


if __name__ == "__main__":
    main()
