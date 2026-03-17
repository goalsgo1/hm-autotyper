"""
HM AutoTyper - 개선된 자동 타이핑 프로그램
- 한/영 자동 전환 지원
- 3가지 타이핑 모드: 타이핑 / 클립보드 / 하이브리드
- 핫키 지원 (F6 시작, ESC 정지)
- 시작 전 카운트다운
- 진행률 표시
"""

import sys

# ═══════════════════════════════════════════════════════════════
# Windows 고해상도(DPI) 지원
# ═══════════════════════════════════════════════════════════════
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # Per-Monitor DPI Aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()  # 구형 Windows 호환
        except Exception:
            pass




# ═══════════════════════════════════════════════════════════════
# 메인 임포트
# ═══════════════════════════════════════════════════════════════

import time
import threading
import unicodedata
import difflib

# ─── Platform detection ───
IS_WINDOWS = sys.platform == "win32"

# ─── Conditional imports ───
try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0
except ImportError:
    pyautogui = None

try:
    import pyperclip
except ImportError:
    pyperclip = None

if IS_WINDOWS:
    import ctypes
    import ctypes.wintypes

    # ─── SendInput 유니코드 입력 구조체 ───
    INPUT_KEYBOARD = 1
    KEYEVENTF_UNICODE = 0x0004
    KEYEVENTF_KEYUP = 0x0002

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", ctypes.c_ushort),
            ("wScan", ctypes.c_ushort),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long),
                     ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
                     ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [("uMsg", ctypes.c_ulong), ("wParamL", ctypes.c_ushort),
                     ("wParamH", ctypes.c_ushort)]

    class _INPUT_UNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", ctypes.c_ulong), ("union", _INPUT_UNION)]

    def send_unicode_char(char):
        """SendInput으로 유니코드 문자를 직접 전송 (IME 완전 우회)"""
        code = ord(char)
        inputs = (INPUT * 2)()
        # Key down
        inputs[0].type = INPUT_KEYBOARD
        inputs[0].union.ki.wVk = 0
        inputs[0].union.ki.wScan = code
        inputs[0].union.ki.dwFlags = KEYEVENTF_UNICODE
        # Key up
        inputs[1].type = INPUT_KEYBOARD
        inputs[1].union.ki.wVk = 0
        inputs[1].union.ki.wScan = code
        inputs[1].union.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
        ctypes.windll.user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))

# ─── Try customtkinter, fallback to tkinter ───
try:
    import customtkinter as ctk
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    USE_CTK = True
except ImportError:
    USE_CTK = False

import tkinter as tk
from tkinter import scrolledtext, messagebox

# ═══════════════════════════════════════════════════════════════
# 한글 자모 분해 엔진
# ═══════════════════════════════════════════════════════════════

# 초성 (19개)
CHOSUNG_LIST = [
    'ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ',
    'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'
]

# 중성 (21개)
JUNGSUNG_LIST = [
    'ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ',
    'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ'
]

# 종성 (28개, 0번은 종성 없음)
JONGSUNG_LIST = [
    '', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ',
    'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ',
    'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'
]

# 자모 → 영문 키 매핑 (2벌식 기준)
JAMO_TO_KEY = {
    # 초성/종성 자음
    'ㄱ': 'r', 'ㄲ': ('shift', 'r'), 'ㄴ': 's', 'ㄷ': 'e',
    'ㄸ': ('shift', 'e'), 'ㄹ': 'f', 'ㅁ': 'a', 'ㅂ': 'q',
    'ㅃ': ('shift', 'q'), 'ㅅ': 't', 'ㅆ': ('shift', 't'),
    'ㅇ': 'd', 'ㅈ': 'w', 'ㅉ': ('shift', 'w'), 'ㅊ': 'c',
    'ㅋ': 'z', 'ㅌ': 'x', 'ㅍ': 'v', 'ㅎ': 'g',
    # 중성 모음
    'ㅏ': 'k', 'ㅐ': 'o', 'ㅑ': 'i', 'ㅒ': ('shift', 'o'),
    'ㅓ': 'j', 'ㅔ': 'p', 'ㅕ': 'u', 'ㅖ': ('shift', 'p'),
    'ㅗ': 'h', 'ㅛ': 'y', 'ㅜ': 'n', 'ㅠ': 'b',
    'ㅡ': 'm', 'ㅣ': 'l',
    # 복합 종성 (각각의 키를 순서대로 입력)
    'ㄳ': ['r', 't'], 'ㄵ': ['s', 'w'], 'ㄶ': ['s', 'g'],
    'ㄺ': ['f', 'r'], 'ㄻ': ['f', 'a'], 'ㄼ': ['f', 'q'],
    'ㄽ': ['f', 't'], 'ㄾ': ['f', 'x'], 'ㄿ': ['f', 'v'],
    'ㅀ': ['f', 'g'], 'ㅄ': ['q', 't'],
}

# 복합 모음 분해
COMPOUND_VOWELS = {
    'ㅘ': ['ㅗ', 'ㅏ'],  # h + k
    'ㅙ': ['ㅗ', 'ㅐ'],  # h + o
    'ㅚ': ['ㅗ', 'ㅣ'],  # h + l
    'ㅝ': ['ㅜ', 'ㅓ'],  # n + j
    'ㅞ': ['ㅜ', 'ㅔ'],  # n + p
    'ㅟ': ['ㅜ', 'ㅣ'],  # n + l
    'ㅢ': ['ㅡ', 'ㅣ'],  # m + l
}


def decompose_hangul(char):
    """한글 음절을 초성/중성/종성 자모 리스트로 분해"""
    code = ord(char) - 0xAC00
    if code < 0 or code > 11171:
        return [char]

    cho = code // (21 * 28)
    jung = (code % (21 * 28)) // 28
    jong = code % 28

    result = [CHOSUNG_LIST[cho], JUNGSUNG_LIST[jung]]
    if jong > 0:
        result.append(JONGSUNG_LIST[jong])
    return result


def jamo_to_keys(jamo):
    """자모 하나를 영문 키 시퀀스로 변환"""
    # 복합 모음 처리
    if jamo in COMPOUND_VOWELS:
        keys = []
        for sub_jamo in COMPOUND_VOWELS[jamo]:
            keys.extend(jamo_to_keys(sub_jamo))
        return keys

    mapping = JAMO_TO_KEY.get(jamo)
    if mapping is None:
        return [jamo]

    if isinstance(mapping, tuple):
        # Shift + key
        return [mapping]
    elif isinstance(mapping, list):
        # 복합 종성: 여러 키
        return mapping
    else:
        return [mapping]


def is_hangul(char):
    """유니코드 문자가 한글 음절인지 확인"""
    return 0xAC00 <= ord(char) <= 0xD7A3


def is_hangul_jamo(char):
    """유니코드 문자가 한글 자모인지 확인"""
    cp = ord(char)
    return (0x3131 <= cp <= 0x3163) or (0x1100 <= cp <= 0x11FF)


def is_ascii_printable(char):
    """ASCII 출력 가능 문자인지 확인"""
    return 0x20 <= ord(char) <= 0x7E


# Shift가 필요한 특수문자 매핑
SHIFT_CHARS = {
    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5',
    '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
    '_': '-', '+': '=', '{': '[', '}': ']', '|': '\\',
    ':': ';', '"': "'", '<': ',', '>': '.', '?': '/',
    '~': '`',
}


# ═══════════════════════════════════════════════════════════════
# IME 상태 감지 및 전환 (Windows 전용)
# ═══════════════════════════════════════════════════════════════

class IMEController:
    """Windows IME 한/영 상태를 감지하고 전환하는 컨트롤러

    전환 전략:
      1순위: WM_IME_CONTROL 메시지 — IME 윈도우에 직접 모드 설정 (빠르고 안정적)
      2순위: VK_HANGUL keybd_event — 한/영 키 시뮬레이션 (폴백)
    """

    VK_HANGUL = 0x15
    WM_IME_CONTROL = 0x0283
    IMC_GETCONVERSIONMODE = 0x0001
    IMC_SETCONVERSIONMODE = 0x0002
    IME_CMODE_HANGEUL = 0x01

    def __init__(self):
        if not IS_WINDOWS:
            self.available = False
            return
        try:
            self.user32 = ctypes.windll.user32
            self.imm32 = ctypes.windll.imm32
            self.available = True
        except Exception:
            self.available = False

    def get_foreground_hwnd(self):
        """현재 포커스된 창의 핸들 반환"""
        if not self.available:
            return None
        return self.user32.GetForegroundWindow()

    def _get_ime_hwnd(self):
        """현재 포커스 창의 IME 윈도우 핸들"""
        hwnd = self.user32.GetForegroundWindow()
        return self.imm32.ImmGetDefaultIMEWnd(hwnd)

    def is_hangul_mode(self):
        """현재 IME가 한글 모드인지 확인"""
        if not self.available:
            return False
        try:
            ime_hwnd = self._get_ime_hwnd()
            if ime_hwnd:
                result = self.user32.SendMessageW(
                    ime_hwnd, self.WM_IME_CONTROL, self.IMC_GETCONVERSIONMODE, 0)
                return bool(result & self.IME_CMODE_HANGEUL)
            return False
        except Exception:
            return False

    def set_hangul_mode(self, enable=True):
        """한글 모드 설정/해제. enable=True이면 한글, False이면 영문"""
        if not self.available:
            return
        if self.is_hangul_mode() == enable:
            return

        # 1순위: WM_IME_CONTROL 메시지로 직접 설정
        try:
            ime_hwnd = self._get_ime_hwnd()
            if ime_hwnd:
                current = self.user32.SendMessageW(
                    ime_hwnd, self.WM_IME_CONTROL, self.IMC_GETCONVERSIONMODE, 0)
                if enable:
                    new_mode = current | self.IME_CMODE_HANGEUL
                else:
                    new_mode = current & ~self.IME_CMODE_HANGEUL
                self.user32.SendMessageW(
                    ime_hwnd, self.WM_IME_CONTROL, self.IMC_SETCONVERSIONMODE, new_mode)
                time.sleep(0.03)
                if self.is_hangul_mode() == enable:
                    return
        except Exception:
            pass

        # 2순위: VK_HANGUL 키 시뮬레이션 (폴백)
        for _ in range(3):
            try:
                self.user32.keybd_event(self.VK_HANGUL, 0, 0, 0)
                time.sleep(0.01)
                self.user32.keybd_event(self.VK_HANGUL, 0, 0x0002, 0)
                time.sleep(0.12)
            except Exception:
                pass
            if self.is_hangul_mode() == enable:
                return

    def ensure_english_mode(self):
        """영문 모드로 전환 (이미 영문이면 아무것도 안 함)"""
        self.set_hangul_mode(False)

    def ensure_hangul_mode(self):
        """한글 모드로 전환 (이미 한글이면 아무것도 안 함)"""
        self.set_hangul_mode(True)

    def get_foreground_pid(self):
        """현재 포커스된 창의 프로세스 ID 반환"""
        if not self.available:
            return None
        try:
            hwnd = self.user32.GetForegroundWindow()
            pid = ctypes.wintypes.DWORD()
            self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            return pid.value
        except Exception:
            return None


# ═══════════════════════════════════════════════════════════════
# 타이핑 엔진
# ═══════════════════════════════════════════════════════════════

class TypingEngine:
    """3가지 모드를 지원하는 타이핑 엔진"""

    MODE_TYPING = "typing"         # 자모 분해 타이핑
    MODE_CLIPBOARD = "clipboard"   # 전체 클립보드
    MODE_HYBRID = "hybrid"         # 하이브리드

    def __init__(self, mode=MODE_HYBRID, delay=0.05, on_progress=None, on_status=None,
                 focus_guard=True, start_index=0):
        self.mode = mode
        self.delay = delay
        self.on_progress = on_progress  # callback(current, total)
        self.on_status = on_status      # callback(message)
        self.focus_guard = focus_guard  # 포커스 이탈 시 자동 중지
        self.ime = IMEController()
        self._stop_event = threading.Event()
        self._original_clipboard = None
        self._target_pid = None  # 타이핑 대상 창의 PID
        self._start_index = start_index  # 이어쓰기 시작 위치
        self._last_index = 0             # 마지막으로 입력 완료한 위치

    def stop(self):
        """타이핑 중지"""
        self._stop_event.set()

    def is_stopped(self):
        return self._stop_event.is_set()

    def _check_focus(self):
        """포커스가 대상 창에서 벗어났는지 확인. 벗어났으면 자동 중지"""
        if not self.focus_guard or not self.ime.available:
            return True  # 가드 비활성이면 항상 통과
        current_pid = self.ime.get_foreground_pid()
        if self._target_pid is not None and current_pid != self._target_pid:
            self._update_status("포커스 이탈 감지 — 자동 중지됨")
            self.stop()
            return False
        return True

    def _update_progress(self, current, total):
        if self.on_progress:
            self.on_progress(current, total)

    def _update_status(self, msg):
        if self.on_status:
            self.on_status(msg)

    def _press_key(self, key):
        """키 하나를 입력 (shift 조합 포함)"""
        if pyautogui is None:
            return
        if isinstance(key, tuple):
            # (modifier, key) 형태
            pyautogui.hotkey(*key)
        else:
            pyautogui.press(key)

    def _type_ascii_char(self, char):
        """ASCII 문자를 정확하게 입력 (대문자/특수문자 Shift 처리 포함)"""
        if pyautogui is None:
            return
        if char.isupper():
            # 대문자: Shift + 소문자 키
            pyautogui.hotkey('shift', char.lower())
        elif char in SHIFT_CHARS:
            # 특수문자: Shift + 기본 키
            pyautogui.hotkey('shift', SHIFT_CHARS[char])
        else:
            # 소문자, 숫자, 기본 기호
            pyautogui.press(char)

    def _type_hangul_char(self, char):
        """한글 한 글자를 자모 분해하여 타이핑"""
        jamos = decompose_hangul(char)
        for jamo in jamos:
            if self.is_stopped():
                return
            keys = jamo_to_keys(jamo)
            for key in keys:
                self._press_key(key)

    def _type_via_clipboard(self, char):
        """클립보드를 통해 한 글자 입력"""
        if pyperclip is None or pyautogui is None:
            return
        pyperclip.copy(char)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.02)  # 클립보드 붙여넣기 처리 대기

    def _commit_ime_composition(self):
        """현재 IME 조합 중인 글자를 확정(commit)하여 버퍼 비움.
        한글 자모 입력 후 SendInput 유니코드로 전환하기 전에 반드시 호출.
        Right 키를 누르면 조합이 확정되고 커서가 글자 뒤(올바른 위치)로 이동함."""
        if pyautogui:
            pyautogui.press('right')
            time.sleep(0.02)

    def _send_unicode(self, char):
        """SendInput KEYEVENTF_UNICODE로 문자 직접 전송 (IME 우회)"""
        if IS_WINDOWS:
            send_unicode_char(char)
        elif pyperclip and pyautogui:
            self._type_via_clipboard(char)

    def _type_text_typing_mode(self, text):
        """타이핑 모드: 한글은 자모 분해, 영문/기호는 SendInput 유니코드 (IME 전환 불필요)"""
        total = len(text)
        in_hangul = None

        for i, char in enumerate(text):
            if self.is_stopped():
                break
            if not self._check_focus():
                break

            if i < self._start_index:
                self._update_progress(i + 1, total)
                continue

            if char in ('\n', '\r'):
                if in_hangul is True:
                    self._commit_ime_composition()
                pyautogui.press('enter') if pyautogui else None
            elif char == '\t':
                if in_hangul is True:
                    self._commit_ime_composition()
                pyautogui.press('tab') if pyautogui else None
            elif is_hangul(char) or is_hangul_jamo(char):
                # 한글 → IME 한글 모드에서 자모 분해 타이핑
                if in_hangul is not True or not self.ime.is_hangul_mode():
                    self.ime.ensure_hangul_mode()
                    in_hangul = True
                    time.sleep(0.03)
                if is_hangul(char):
                    self._type_hangul_char(char)
                else:
                    keys = jamo_to_keys(char)
                    for key in keys:
                        self._press_key(key)
            else:
                # 영문/숫자/기호/기타 → SendInput 유니코드로 직접 전송
                if in_hangul is True:
                    self._commit_ime_composition()  # 한글 조합 확정 후 전환
                    in_hangul = False
                self._send_unicode(char)

            self._last_index = i + 1
            self._update_progress(i + 1, total)
            if self.delay > 0:
                time.sleep(self.delay)

    def _type_text_clipboard_mode(self, text):
        """클립보드 모드: 모든 글자를 클립보드로 입력"""
        total = len(text)

        for i, char in enumerate(text):
            if self.is_stopped():
                break
            if not self._check_focus():
                break

            # 이어쓰기: 이미 입력된 부분 건너뛰기
            if i < self._start_index:
                self._update_progress(i + 1, total)
                continue

            if char in ('\n', '\r'):
                pyautogui.press('enter') if pyautogui else None
            elif char == '\t':
                pyautogui.press('tab') if pyautogui else None
            else:
                self._type_via_clipboard(char)

            self._last_index = i + 1
            self._update_progress(i + 1, total)
            if self.delay > 0:
                time.sleep(self.delay)

    def _type_text_hybrid_mode(self, text):
        """하이브리드 모드: 한글은 자모 분해 타이핑, 영어/기타는 SendInput 유니코드"""
        total = len(text)
        in_hangul = None

        for i, char in enumerate(text):
            if self.is_stopped():
                break
            if not self._check_focus():
                break

            if i < self._start_index:
                self._update_progress(i + 1, total)
                continue

            if char in ('\n', '\r'):
                if in_hangul is True:
                    self._commit_ime_composition()
                pyautogui.press('enter') if pyautogui else None
            elif char == '\t':
                if in_hangul is True:
                    self._commit_ime_composition()
                pyautogui.press('tab') if pyautogui else None
            elif is_hangul(char) or is_hangul_jamo(char):
                # 한글 → 자모 분해 타이핑
                if in_hangul is not True or not self.ime.is_hangul_mode():
                    self.ime.ensure_hangul_mode()
                    in_hangul = True
                    time.sleep(0.03)
                if is_hangul(char):
                    self._type_hangul_char(char)
                else:
                    keys = jamo_to_keys(char)
                    for key in keys:
                        self._press_key(key)
            else:
                # 영어/기타 → SendInput 유니코드 (IME 전환 불필요)
                if in_hangul is True:
                    self._commit_ime_composition()  # 한글 조합 확정 후 전환
                    in_hangul = False
                self._send_unicode(char)

            self._last_index = i + 1
            self._update_progress(i + 1, total)
            if self.delay > 0:
                time.sleep(self.delay)

    def type_text(self, text):
        """선택된 모드에 따라 텍스트 타이핑 실행"""
        self._stop_event.clear()
        text = text.replace('\r\n', '\n')  # 줄바꿈 정규화

        # 타이핑 대상 창의 PID 기록 (포커스 가드용)
        self._target_pid = self.ime.get_foreground_pid()

        # 원본 클립보드 백업
        if pyperclip:
            try:
                self._original_clipboard = pyperclip.paste()
            except Exception:
                self._original_clipboard = None

        try:
            if self.mode == self.MODE_TYPING:
                self._update_status("타이핑 모드로 입력 중...")
                self._type_text_typing_mode(text)
            elif self.mode == self.MODE_CLIPBOARD:
                self._update_status("클립보드 모드로 입력 중...")
                self._type_text_clipboard_mode(text)
            elif self.mode == self.MODE_HYBRID:
                self._update_status("하이브리드 모드로 입력 중...")
                self._type_text_hybrid_mode(text)
        finally:
            # 클립보드 복원
            if pyperclip and self._original_clipboard is not None:
                try:
                    pyperclip.copy(self._original_clipboard)
                except Exception:
                    pass

        if self.is_stopped():
            if self._last_index < len(text):
                self._update_status(
                    f"중지됨 ({self._last_index}/{len(text)}글자) — 다시 시작하면 이어쓰기 가능")
            else:
                self._update_status("중지됨")
        else:
            self._update_status("완료!")


# ═══════════════════════════════════════════════════════════════
# GUI 애플리케이션
# ═══════════════════════════════════════════════════════════════

class HmAutotyperApp:
    """HM AutoTyper 메인 GUI"""

    COUNTDOWN_SECONDS = 3
    DEFAULT_DELAY_MS = 50

    def __init__(self):
        # ── 메인 윈도우 생성 ──
        if USE_CTK:
            self.root = ctk.CTk()
        else:
            self.root = tk.Tk()
        self.root.title("HM AutoTyper v3.1  \u00a9 2026 haemin")
        self.root.geometry("1160x960")
        self.root.minsize(960, 700)
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        self._typing_thread = None
        self._engine = None
        self._is_running = False
        self._countdown_id = None
        self._last_typed_index = 0   # 마지막으로 입력 완료된 글자 인덱스
        self._last_text = ""         # 마지막 타이핑 텍스트 (이어쓰기 비교용)

        self._build_ui()
        self._register_hotkeys()

    # ── UI 구성 ──
    def _build_ui(self):
        pad = {"padx": 12, "pady": 4}

        # --- 타이틀 + 정보 아이콘 ---
        title_row = tk.Frame(self.root)
        title_row.pack(fill="x", pady=(12, 0))

        if USE_CTK:
            ctk.CTkLabel(title_row, text="HM AutoTyper",
                         font=ctk.CTkFont(size=20, weight="bold")).pack(side="left", padx=(16, 0), expand=True)
        else:
            tk.Label(title_row, text="HM AutoTyper",
                     font=("Arial", 18, "bold")).pack(side="left", padx=(16, 0), expand=True)

        # 사용법 버튼 — 오른쪽 상단
        info_btn = tk.Label(title_row, text="  사용법  ", font=("맑은 고딕", 11),
                            fg="white", bg="#3498db", cursor="hand2",
                            relief="flat", padx=10, pady=2)
        info_btn.pack(side="right", padx=(0, 16))
        info_btn.bind("<Button-1>", lambda e: self._show_info_popup())
        info_btn.bind("<Enter>", lambda e: info_btn.config(bg="#2980b9"))
        info_btn.bind("<Leave>", lambda e: info_btn.config(bg="#3498db"))

        if USE_CTK:
            ctk.CTkLabel(self.root, text="F6: 시작  |  F7: 검증  |  ESC: 정지",
                         font=ctk.CTkFont(size=12), text_color="gray").pack(pady=(0, 8))
        else:
            tk.Label(self.root, text="F6: 시작  |  F7: 검증  |  ESC: 정지",
                     font=("Arial", 10), fg="gray").pack(pady=(0, 8))

        # --- 텍스트 입력 영역 ---
        text_frame = tk.Frame(self.root)
        text_frame.pack(**pad, fill="both", expand=True)

        self.text_area = scrolledtext.ScrolledText(
            text_frame, wrap=tk.WORD, font=("맑은 고딕", 11), height=8
        )
        self.text_area.pack(fill="both", expand=True)

        # --- 설정 프레임 ---
        if USE_CTK:
            settings_frame = ctk.CTkFrame(self.root)
        else:
            settings_frame = tk.LabelFrame(self.root, text="설정", padx=8, pady=4)
        settings_frame.pack(**pad, fill="x")

        # 모드 선택
        mode_frame = tk.Frame(settings_frame)
        mode_frame.pack(fill="x", pady=4, padx=8)

        if USE_CTK:
            ctk.CTkLabel(mode_frame, text="모드:", font=ctk.CTkFont(size=13)).pack(anchor="w")
        else:
            tk.Label(mode_frame, text="모드:", font=("Arial", 11)).pack(anchor="w")

        self.mode_var = tk.StringVar(value=TypingEngine.MODE_HYBRID)
        modes = [
            ("⭐ 하이브리드 (추천) — 한글: 타이핑 효과 / 영어: 클립보드", TypingEngine.MODE_HYBRID),
            ("⌨ 타이핑 (한/영 자동전환) — 모두 키보드 시뮬레이션", TypingEngine.MODE_TYPING),
            ("📋 클립보드 (가장 안정) — 모두 붙여넣기 방식", TypingEngine.MODE_CLIPBOARD),
        ]
        for text, value in modes:
            rb = tk.Radiobutton(mode_frame, text=text, variable=self.mode_var,
                                value=value, font=("맑은 고딕", 10), anchor="w")
            rb.pack(fill="x", padx=16, pady=1)

        # 딜레이 설정
        delay_row = tk.Frame(settings_frame)
        delay_row.pack(fill="x", pady=4, padx=8)

        if USE_CTK:
            ctk.CTkLabel(delay_row, text="딜레이(ms):", font=ctk.CTkFont(size=13)).pack(side="left")
        else:
            tk.Label(delay_row, text="딜레이(ms):", font=("Arial", 11)).pack(side="left")

        self.delay_var = tk.IntVar(value=self.DEFAULT_DELAY_MS)
        self.delay_scale = tk.Scale(delay_row, from_=0, to=500, orient="horizontal",
                                    variable=self.delay_var, length=500, showvalue=True)
        self.delay_scale.pack(side="left", padx=8)

        # 포커스 가드 체크박스
        guard_row = tk.Frame(settings_frame)
        guard_row.pack(fill="x", pady=4, padx=8)

        self.focus_guard_var = tk.BooleanVar(value=True)

        # 큰 체크박스를 위한 캔버스 기반 커스텀 위젯
        guard_inner = tk.Frame(guard_row)
        guard_inner.pack(anchor="w")

        cb_size = 22  # 체크박스 크기 (픽셀)
        self._guard_canvas = tk.Canvas(guard_inner, width=cb_size, height=cb_size,
                                        highlightthickness=1, highlightbackground="#888",
                                        bg="white", cursor="hand2")
        self._guard_canvas.pack(side="left", padx=(0, 8), pady=4)

        def _draw_check():
            self._guard_canvas.delete("check")
            if self.focus_guard_var.get():
                # 체크 표시 그리기
                self._guard_canvas.create_line(4, 11, 9, 17, fill="#27ae60", width=3, tags="check")
                self._guard_canvas.create_line(9, 17, 19, 5, fill="#27ae60", width=3, tags="check")

        def _toggle_guard(event=None):
            self.focus_guard_var.set(not self.focus_guard_var.get())
            _draw_check()

        self._guard_canvas.bind("<Button-1>", _toggle_guard)
        _draw_check()  # 초기 상태 표시

        guard_label = tk.Label(guard_inner,
                               text="포커스 이탈 시 자동 중지 (다른 창 클릭하면 타이핑 멈춤)",
                               font=("맑은 고딕", 10), cursor="hand2")
        guard_label.pack(side="left")
        guard_label.bind("<Button-1>", _toggle_guard)

        # 이어쓰기 체크박스
        resume_row = tk.Frame(settings_frame)
        resume_row.pack(fill="x", pady=4, padx=8)

        self.resume_enabled_var = tk.BooleanVar(value=True)

        resume_inner = tk.Frame(resume_row)
        resume_inner.pack(anchor="w")

        self._resume_canvas = tk.Canvas(resume_inner, width=cb_size, height=cb_size,
                                         highlightthickness=1, highlightbackground="#888",
                                         bg="white", cursor="hand2")
        self._resume_canvas.pack(side="left", padx=(0, 8), pady=4)

        def _draw_resume_check():
            self._resume_canvas.delete("check")
            if self.resume_enabled_var.get():
                self._resume_canvas.create_line(4, 11, 9, 17, fill="#2980b9", width=3, tags="check")
                self._resume_canvas.create_line(9, 17, 19, 5, fill="#2980b9", width=3, tags="check")

        def _toggle_resume(event=None):
            self.resume_enabled_var.set(not self.resume_enabled_var.get())
            _draw_resume_check()
            # 이어쓰기 끄면 저장된 진행 기록 초기화
            if not self.resume_enabled_var.get():
                self._last_typed_index = 0
                self._last_text = ""

        self._resume_canvas.bind("<Button-1>", _toggle_resume)
        _draw_resume_check()

        resume_label = tk.Label(resume_inner,
                                text="이어쓰기 (중단 후 다시 시작하면 이어서 입력)",
                                font=("맑은 고딕", 10), cursor="hand2")
        resume_label.pack(side="left")
        resume_label.bind("<Button-1>", _toggle_resume)

        # --- 하단 영역 (side="bottom"으로 먼저 배치하여 항상 표시) ---

        # 상태 라벨 (맨 아래)
        if USE_CTK:
            self.status_label = ctk.CTkLabel(self.root, text="",
                                             font=ctk.CTkFont(size=11), text_color="gray")
        else:
            self.status_label = tk.Label(self.root, text="", font=("맑은 고딕", 9), fg="gray")
        self.status_label.pack(side="bottom", pady=(0, 8))

        # 버튼
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(side="bottom", pady=8)

        if USE_CTK:
            self.start_btn = ctk.CTkButton(btn_frame, text="시작 (F6)", width=140,
                                           height=40, command=self._on_start_click,
                                           font=ctk.CTkFont(size=14, weight="bold"))
            self.start_btn.pack(side="left", padx=6)

            self.stop_btn = ctk.CTkButton(btn_frame, text="정지 (ESC)", width=140,
                                          height=40, command=self._on_stop_click,
                                          fg_color="#c0392b", hover_color="#e74c3c",
                                          font=ctk.CTkFont(size=14, weight="bold"),
                                          state="disabled")
            self.stop_btn.pack(side="left", padx=6)

            self.verify_btn = ctk.CTkButton(btn_frame, text="검증 (F7)", width=120,
                                            height=40, command=self._on_verify_click,
                                            fg_color="#8e44ad", hover_color="#9b59b6",
                                            font=ctk.CTkFont(size=13, weight="bold"))
            self.verify_btn.pack(side="left", padx=4)

            self.reset_btn = ctk.CTkButton(btn_frame, text="초기화", width=90,
                                            height=40, command=self._on_reset_click,
                                            fg_color="#7f8c8d", hover_color="#95a5a6",
                                            font=ctk.CTkFont(size=13, weight="bold"))
            self.reset_btn.pack(side="left", padx=4)

        else:
            self.start_btn = tk.Button(btn_frame, text="시작 (F6)", width=12,
                                       height=1, command=self._on_start_click,
                                       font=("맑은 고딕", 11, "bold"), bg="#27ae60", fg="white")
            self.start_btn.pack(side="left", padx=4)

            self.stop_btn = tk.Button(btn_frame, text="정지 (ESC)", width=12,
                                      height=1, command=self._on_stop_click,
                                      font=("맑은 고딕", 11, "bold"), bg="#c0392b", fg="white",
                                      state="disabled")
            self.stop_btn.pack(side="left", padx=4)

            self.verify_btn = tk.Button(btn_frame, text="검증 (F7)", width=12,
                                        height=1, command=self._on_verify_click,
                                        font=("맑은 고딕", 11, "bold"), bg="#8e44ad", fg="white")
            self.verify_btn.pack(side="left", padx=4)

            self.reset_btn = tk.Button(btn_frame, text="초기화", width=8,
                                        height=1, command=self._on_reset_click,
                                        font=("맑은 고딕", 11, "bold"), bg="#7f8c8d", fg="white")
            self.reset_btn.pack(side="left", padx=6)

        # 진행률 라벨
        self.progress_label = tk.Label(self.root, text="대기 중", font=("맑은 고딕", 10))
        self.progress_label.pack(side="bottom", pady=2)

        # 진행률 바
        progress_frame = tk.Frame(self.root)
        progress_frame.pack(side="bottom", **pad, fill="x")

        if USE_CTK:
            self.progress_bar = ctk.CTkProgressBar(progress_frame, width=800)
            self.progress_bar.pack(fill="x", padx=4, pady=2)
            self.progress_bar.set(0)
        else:
            import tkinter.ttk as ttk
            self.progress_bar = ttk.Progressbar(progress_frame, length=800, mode='determinate')
            self.progress_bar.pack(fill="x", padx=4, pady=2)

    # ── 핫키 등록 ──
    def _register_hotkeys(self):
        self.root.bind("<F6>", lambda e: self._on_start_click())
        self.root.bind("<Escape>", lambda e: self._on_stop_click())
        self.root.bind("<F7>", lambda e: self._on_verify_click())
        # 전역 핫키는 keyboard 라이브러리 필요 (선택적)
        try:
            import keyboard as kb
            kb.add_hotkey('F6', self._on_start_click)
            kb.add_hotkey('escape', self._on_stop_click)
            kb.add_hotkey('F7', self._on_verify_click)
        except ImportError:
            pass
        except Exception:
            pass

    # ── 이벤트 핸들러 ──
    def _on_start_click(self):
        if self._is_running:
            return

        text = self.text_area.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("알림", "타이핑할 텍스트를 입력해주세요.")
            return

        self._pending_text = text

        # 이어쓰기 분석 모드: 체크박스 ON이고, 이전에 중단된 기록이 있을 때
        if (self.resume_enabled_var.get()
                and self._last_typed_index > 0
                and self._last_typed_index < len(text)
                and text == self._last_text):
            # 대상 창 텍스트를 읽어서 분석
            self._is_running = True
            self._set_buttons_running(True)
            self._set_status("3초 후 대상 창 분석... (대상 창에 포커스를 이동하세요)", "orange")
            self._resume_analysis_countdown(3)
        else:
            # 일반 시작 (처음부터)
            self._is_running = True
            self._resume_index = 0
            self._set_buttons_running(True)
            self._start_countdown(text)

    # ── 이어쓰기 분석 ──
    def _resume_analysis_countdown(self, remaining):
        if remaining > 0:
            self._set_status(f"{remaining}초 후 대상 창 분석... (대상 창에 포커스를 이동하세요)", "orange")
            self._set_progress_label(f"분석 카운트다운: {remaining}초")
            self._countdown_id = self.root.after(
                1000, self._resume_analysis_countdown, remaining - 1)
        else:
            self._countdown_id = None
            self._perform_resume_analysis()

    def _perform_resume_analysis(self):
        """대상 창 텍스트를 Ctrl+A → Ctrl+C로 읽어와 원문과 비교 분석"""
        def run():
            try:
                if not pyperclip or not pyautogui:
                    self.root.after(0, self._resume_analysis_fallback)
                    return

                # 클립보드 백업
                try:
                    backup = pyperclip.paste()
                except Exception:
                    backup = None

                # 대상 창에서 전체 선택 → 복사
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.3)
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(0.3)
                pyautogui.press('right')  # 선택 해제

                typed_text = pyperclip.paste()

                # 클립보드 복원
                if backup is not None:
                    try:
                        pyperclip.copy(backup)
                    except Exception:
                        pass

                self.root.after(0, self._show_resume_analysis, typed_text)

            except Exception as ex:
                self.root.after(0, lambda: messagebox.showerror("오류", str(ex)))
                self.root.after(0, self._resume_analysis_fallback)

        threading.Thread(target=run, daemon=True).start()

    def _resume_analysis_fallback(self):
        """분석 실패 시 기존 방식으로 폴백"""
        self._resume_index = self._last_typed_index
        self._start_countdown(self._pending_text)

    def _find_resume_point(self, original, typed):
        """원문과 입력된 텍스트를 비교하여 중단 지점과 오류를 분석"""
        original = original.replace('\r\n', '\n')
        typed = typed.replace('\r\n', '\n')

        if not typed.strip():
            return {'resume_index': 0, 'errors': [], 'typed_len': 0,
                    'match_ratio': 0.0, 'status': 'empty'}

        # SequenceMatcher로 매칭 분석
        sm = difflib.SequenceMatcher(None, original, typed, autojunk=False)
        match_ratio = sm.ratio()

        # 매칭 블록들을 분석하여 중단 지점 추정
        matching_blocks = sm.get_matching_blocks()

        # 원문에서 마지막으로 매칭된 위치 = 중단 지점
        last_matched_orig = 0
        for block in matching_blocks:
            end_orig = block.a + block.size
            if end_orig > last_matched_orig:
                last_matched_orig = end_orig

        # 오류 목록 (입력된 부분에서의 차이)
        errors = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'equal':
                continue
            # 중단 지점 이전의 오류만 수집
            if i1 < last_matched_orig or (tag == 'insert' and j1 < len(typed)):
                line = original[:i1].count('\n') + 1
                last_nl = original[:i1].rfind('\n')
                col = i1 - last_nl
                errors.append({
                    'type': tag,
                    'pos': i1,
                    'orig': original[i1:i2],
                    'typed': typed[j1:j2],
                    'line': line,
                    'col': col,
                    'orig_range': (i1, i2),
                    'typed_range': (j1, j2),
                })

        # 완료 여부 판단
        if match_ratio > 0.98 and len(typed) >= len(original) * 0.95:
            status = 'complete'
        elif len(typed.strip()) == 0:
            status = 'empty'
        else:
            status = 'partial'

        return {
            'resume_index': last_matched_orig,
            'errors': errors,
            'typed_len': len(typed),
            'match_ratio': match_ratio,
            'status': status,
        }

    def _show_resume_analysis(self, typed_text):
        """분석 결과를 팝업으로 표시하여 사용자가 선택할 수 있게 함"""
        original = self._pending_text.replace('\r\n', '\n')
        analysis = self._find_resume_point(original, typed_text)

        # 분석 중 상태 해제 (팝업에서 다시 시작)
        self._is_running = False
        self._set_buttons_running(False)

        resume_idx = analysis['resume_index']
        total = len(original)
        errors = analysis['errors']
        ratio = analysis['match_ratio'] * 100

        # 완료된 경우
        if analysis['status'] == 'complete' and not errors:
            self._set_status("이미 완료됨 — 원문과 일치합니다!", "#27ae60")
            messagebox.showinfo("분석 결과", "대상 창의 텍스트가 원문과 이미 일치합니다.")
            return

        # 비어있는 경우
        if analysis['status'] == 'empty':
            self._set_status("대상 창이 비어있음 — 처음부터 시작합니다.", "blue")
            self._is_running = True
            self._resume_index = 0
            self._set_buttons_running(True)
            self._start_countdown(self._pending_text)
            return

        # --- 분석 결과 팝업 ---
        popup = tk.Toplevel(self.root)
        popup.title("이어쓰기 분석 결과")
        popup.transient(self.root)
        popup.grab_set()

        main_w = self.root.winfo_width()
        main_h = self.root.winfo_height()
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        popup.geometry(f"{main_w}x{main_h}+{main_x + 40}+{main_y + 40}")
        popup.minsize(960, 700)
        popup.resizable(True, True)

        # 상단 요약
        summary_frame = tk.Frame(popup)
        summary_frame.pack(fill="x", padx=20, pady=(16, 4))

        tk.Label(summary_frame, text="이어쓰기 분석 결과",
                 font=("맑은 고딕", 16, "bold")).pack(anchor="w")

        tk.Frame(popup, height=2, bg="#ddd").pack(fill="x", padx=20, pady=8)

        # 진행 상황
        info_frame = tk.Frame(popup)
        info_frame.pack(fill="x", padx=20, pady=4)

        progress_pct = (resume_idx / total * 100) if total > 0 else 0
        error_count = len(errors)

        info_lines = [
            f"원문: {total}글자",
            f"입력 진행: {resume_idx} / {total}글자 ({progress_pct:.1f}%)",
            f"일치율: {ratio:.1f}%",
            f"오류: {error_count}건 {'(수정 필요)' if error_count > 0 else '(없음)'}",
            f"남은 글자: {total - resume_idx}글자",
        ]
        for line in info_lines:
            tk.Label(info_frame, text=line, font=("맑은 고딕", 11),
                     anchor="w").pack(fill="x", pady=1)

        # 오류 상세 (있을 경우)
        if errors:
            tk.Frame(popup, height=1, bg="#eee").pack(fill="x", padx=20, pady=8)

            error_frame = tk.LabelFrame(popup, text=f"발견된 오류 ({error_count}건)",
                                         padx=8, pady=4)
            error_frame.pack(fill="both", expand=True, padx=20, pady=4)

            err_scroll = tk.Scrollbar(error_frame)
            err_scroll.pack(side="right", fill="y")

            err_text = tk.Text(error_frame, font=("Consolas", 10), wrap="none",
                                height=8, yscrollcommand=err_scroll.set)
            err_text.pack(fill="both", expand=True)
            err_scroll.config(command=err_text.yview)

            err_text.tag_configure("header", font=("맑은 고딕", 10, "bold"),
                                    background="#ecf0f1")
            err_text.tag_configure("err_replace", foreground="#e74c3c")
            err_text.tag_configure("err_delete", foreground="#e67e22")
            err_text.tag_configure("err_insert", foreground="#3498db")

            err_text.insert("end",
                f"{'#':>3}  {'줄':>4}  {'컬럼':>4}  {'유형':<6}  {'원문':<20}  {'입력됨':<20}\n",
                "header")
            err_text.insert("end", "\u2500" * 65 + "\n")

            type_names = {'replace': '교체', 'delete': '누락', 'insert': '추가'}
            type_tags = {'replace': 'err_replace', 'delete': 'err_delete',
                         'insert': 'err_insert'}
            for idx, err in enumerate(errors[:50]):  # 최대 50건
                orig_d = repr(err['orig'])[:18] if err['orig'] else '(없음)'
                typed_d = repr(err['typed'])[:18] if err['typed'] else '(없음)'
                tag = type_tags.get(err['type'], 'err_replace')
                line = (f"{idx+1:>3}  {err['line']:>4}  {err['col']:>4}  "
                        f"{type_names.get(err['type'], err['type']):<6}  "
                        f"{orig_d:<20}  {typed_d:<20}\n")
                err_text.insert("end", line, tag)

            err_text.config(state="disabled")

        # --- 텍스트 비교 미리보기 ---
        tk.Frame(popup, height=1, bg="#eee").pack(fill="x", padx=20, pady=8)

        preview_frame = tk.LabelFrame(popup,
            text="텍스트 비교 (빨강: 오류 / 초록: 중단 지점 이후 = 아직 입력 안 됨)",
            padx=4, pady=4)
        preview_frame.pack(fill="both", expand=True, padx=20, pady=4)

        prev_scroll = tk.Scrollbar(preview_frame)
        prev_scroll.pack(side="right", fill="y")

        prev_text = tk.Text(preview_frame, font=("맑은 고딕", 10), wrap="word",
                             height=6, yscrollcommand=prev_scroll.set)
        prev_text.pack(fill="both", expand=True)
        prev_scroll.config(command=prev_text.yview)

        prev_text.tag_configure("match", foreground="black")
        prev_text.tag_configure("error", foreground="white", background="#e74c3c")
        prev_text.tag_configure("remaining", foreground="white", background="#27ae60")
        prev_text.tag_configure("cursor_mark", foreground="white", background="#8e44ad",
                                 font=("맑은 고딕", 10, "bold"))

        # 원문을 중단 지점 기준으로 표시
        typed_part = original[:resume_idx]
        remaining_part = original[resume_idx:]

        # 입력된 부분 (오류 하이라이트)
        if errors:
            sm = difflib.SequenceMatcher(None, original[:resume_idx],
                                          typed_text.replace('\r\n', '\n')[:len(typed_text)],
                                          autojunk=False)
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag == 'equal':
                    prev_text.insert("end", original[i1:i2], "match")
                else:
                    prev_text.insert("end", original[i1:i2], "error")
        else:
            prev_text.insert("end", typed_part, "match")

        # 중단 지점 마커
        prev_text.insert("end", " \u25b6 ", "cursor_mark")

        # 남은 부분
        remaining_preview = remaining_part[:200]
        if len(remaining_part) > 200:
            remaining_preview += "..."
        prev_text.insert("end", remaining_preview, "remaining")

        prev_text.config(state="disabled")

        # --- 버튼 (BOTTOM에 먼저 pack → 항상 표시) ---
        btn_area = tk.Frame(popup)
        btn_area.pack(side="bottom", fill="x", padx=16, pady=(0, 10))

        def _do_resume():
            popup.destroy()
            self._is_running = True
            self._resume_index = resume_idx
            self._set_buttons_running(True)
            self._set_status("3초 후 이어서 입력... (대상 창에 포커스를 이동하세요)", "orange")
            self._start_countdown(self._pending_text)

        def _do_fix_then_resume():
            popup.destroy()
            self._verify_errors = errors
            self._verify_typed = typed_text
            self._pending_resume_index = resume_idx
            self._is_running = True
            self._set_buttons_running(True)
            self._set_status("3초 후 오류 수정(클립보드) 시작...", "orange")
            self._fix_countdown(3, "fix_then_resume", None)

        def _do_fix_typing_then_resume():
            popup.destroy()
            self._verify_errors = errors
            self._verify_typed = typed_text
            self._pending_resume_index = resume_idx
            self._is_running = True
            self._set_buttons_running(True)
            self._set_status("3초 후 오류 수정(타이핑) 시작... (대상 창에 포커스를 이동하세요)", "orange")
            self._fix_countdown(3, "fix_typing_then_resume", None)

        def _do_restart():
            popup.destroy()
            self._is_running = True
            self._resume_index = 0
            self._set_buttons_running(True)
            self._start_countdown(self._pending_text)

        def _do_cancel():
            popup.destroy()
            self._is_running = False
            self._set_buttons_running(False)
            self._set_status("취소됨", "gray")

        # 오류가 있으면 수정 버튼 표시
        if errors:
            fix_frame = tk.Frame(btn_area)
            fix_frame.pack(fill="x", pady=(0, 4))

            tk.Label(fix_frame, text="오류수정:", font=("맑은 고딕", 9),
                     fg="#7f8c8d").pack(side="left", padx=(0, 4))
            tk.Button(fix_frame, text="수정 후 이어쓰기 (붙여넣기)", width=24,
                      font=("맑은 고딕", 10, "bold"), bg="#e74c3c", fg="white",
                      command=_do_fix_then_resume).pack(side="left", padx=3)
            tk.Button(fix_frame, text="수정 후 이어쓰기 (타이핑)", width=24,
                      font=("맑은 고딕", 10, "bold"), bg="#16a085", fg="white",
                      command=_do_fix_typing_then_resume).pack(side="left", padx=3)

        action_frame = tk.Frame(btn_area)
        action_frame.pack(fill="x", pady=(0, 0))

        tk.Button(action_frame, text=f"이어쓰기 ({resume_idx}자부터)", width=20,
                  font=("맑은 고딕", 10, "bold"), bg="#27ae60", fg="white",
                  command=_do_resume).pack(side="left", padx=3)

        tk.Button(action_frame, text="처음부터 다시", width=14,
                  font=("맑은 고딕", 10), bg="#3498db", fg="white",
                  command=_do_restart).pack(side="left", padx=3)

        tk.Button(action_frame, text="취소", width=8,
                  font=("맑은 고딕", 10), bg="#95a5a6", fg="white",
                  command=_do_cancel).pack(side="right", padx=3)

        if errors:
            tk.Label(action_frame,
                     text="* 붙여넣기 차단시 타이핑 사용",
                     font=("맑은 고딕", 9), fg="#e67e22").pack(side="right", padx=6)

        tk.Frame(popup, height=1, bg="#eee").pack(side="bottom", fill="x", padx=20, pady=(4, 0))

    def _start_countdown(self, text, remaining=None):
        if remaining is None:
            remaining = self.COUNTDOWN_SECONDS

        if remaining > 0:
            self._set_status(f"{remaining}초 후 시작... (대상 창에 포커스를 이동하세요)", "orange")
            self._set_progress_label(f"카운트다운: {remaining}초")
            self._countdown_id = self.root.after(1000, self._start_countdown, text, remaining - 1)
        else:
            self._countdown_id = None
            self._begin_typing(text)

    def _begin_typing(self, text):
        mode = self.mode_var.get()
        delay_ms = self.delay_var.get()
        delay_sec = delay_ms / 1000.0

        self._engine = TypingEngine(
            mode=mode,
            delay=delay_sec,
            on_progress=self._on_engine_progress,
            on_status=self._on_engine_status,
            focus_guard=self.focus_guard_var.get(),
            start_index=self._resume_index,
        )
        self._last_text = text  # 이어쓰기 비교용 텍스트 저장

        def run():
            try:
                self._engine.type_text(text)
            except Exception as ex:
                self.root.after(0, lambda: messagebox.showerror("오류", str(ex)))
            finally:
                self.root.after(0, self._on_typing_done)

        self._typing_thread = threading.Thread(target=run, daemon=True)
        self._typing_thread.start()

    def _on_stop_click(self):
        if self._countdown_id:
            self.root.after_cancel(self._countdown_id)
            self._countdown_id = None
        if self._engine:
            self._engine.stop()
        self._on_typing_done()

    def _on_reset_click(self):
        """진행 상태 초기화 — 이어쓰기 위치, 진행률, 상태 메시지를 모두 리셋"""
        if self._is_running:
            return  # 실행 중에는 무시

        # 이어쓰기 관련 초기화
        self._last_typed_index = 0
        self._last_text = ""
        if self._engine:
            self._engine._last_index = 0
            self._engine._start_index = 0

        # 진행률 바 초기화
        if USE_CTK:
            self.progress_bar.set(0)
        else:
            self.progress_bar['value'] = 0
        self._set_progress_label("대기 중")

        # 상태 메시지 초기화
        self._set_status("초기화 완료", "#e67e22")

        # 0.5초 뒤 상태 메시지도 클리어
        self.root.after(1500, lambda: self._set_status(""))

    def _on_typing_done(self):
        # 엔진의 마지막 입력 위치 저장 (이어쓰기용)
        if self._engine:
            self._last_typed_index = self._engine._last_index
        self._is_running = False
        self._set_buttons_running(False)

    def _on_engine_progress(self, current, total):
        self.root.after(0, self._update_progress_ui, current, total)

    def _on_engine_status(self, msg):
        self.root.after(0, self._set_status, msg, "blue")

    # ── UI 업데이트 헬퍼 ──
    def _update_progress_ui(self, current, total):
        ratio = current / total if total > 0 else 0
        if USE_CTK:
            self.progress_bar.set(ratio)
        else:
            self.progress_bar['value'] = ratio * 100
        self._set_progress_label(f"{current} / {total} 글자  ({ratio*100:.0f}%)")

    def _set_progress_label(self, text):
        self.progress_label.config(text=text)

    def _set_status(self, msg, color="gray"):
        if USE_CTK:
            self.status_label.configure(text=msg, text_color=color)
        else:
            self.status_label.config(text=msg, fg=color)

    def _set_buttons_running(self, running):
        if USE_CTK:
            self.start_btn.configure(state="disabled" if running else "normal")
            self.stop_btn.configure(state="normal" if running else "disabled")
            self.reset_btn.configure(state="disabled" if running else "normal")
            self.verify_btn.configure(state="disabled" if running else "normal")
        else:
            self.start_btn.config(state="disabled" if running else "normal")
            self.stop_btn.config(state="disabled" if not running else "normal")
            self.reset_btn.config(state="disabled" if running else "normal")
            self.verify_btn.config(state="disabled" if running else "normal")

    # ══════════════════════════════════════════════════════
    # 검증 기능
    # ══════════════════════════════════════════════════════

    def _on_verify_click(self):
        """검증 버튼 클릭: 3초 카운트다운 후 대상 창 텍스트를 가져와 비교"""
        if self._is_running:
            return

        self._original_text = self.text_area.get("1.0", tk.END).strip()
        if not self._original_text:
            messagebox.showwarning("알림", "비교할 원문 텍스트가 없습니다.")
            return

        self._is_running = True
        self._set_buttons_running(True)
        self._set_status("3초 후 검증 시작... (대상 창에 포커스를 이동하세요)", "orange")
        self._verify_countdown(3)

    def _verify_countdown(self, remaining):
        if remaining > 0:
            self._set_status(f"{remaining}초 후 검증... (대상 창에 포커스를 이동하세요)", "orange")
            self._set_progress_label(f"검증 카운트다운: {remaining}초")
            self._countdown_id = self.root.after(1000, self._verify_countdown, remaining - 1)
        else:
            self._countdown_id = None
            self._perform_verification()

    def _perform_verification(self):
        """대상 창에서 Ctrl+A → Ctrl+C → 클립보드 텍스트를 원문과 비교"""
        def run():
            try:
                if pyperclip:
                    # 클립보드 백업
                    try:
                        backup = pyperclip.paste()
                    except Exception:
                        backup = None

                    # 대상 창에서 전체 선택 후 복사
                    if pyautogui:
                        pyautogui.hotkey('ctrl', 'a')
                        time.sleep(0.3)
                        pyautogui.hotkey('ctrl', 'c')
                        time.sleep(0.3)
                        # 선택 해제 (오른쪽 화살표로 커서만 이동)
                        pyautogui.press('right')

                    typed_text = pyperclip.paste()

                    # 클립보드 복원
                    if backup is not None:
                        try:
                            pyperclip.copy(backup)
                        except Exception:
                            pass

                    self.root.after(0, self._show_verify_result, typed_text)
                else:
                    self.root.after(0, lambda: messagebox.showerror(
                        "오류", "pyperclip이 설치되지 않았습니다."))
            except Exception as ex:
                self.root.after(0, lambda: messagebox.showerror("오류", str(ex)))
            finally:
                self.root.after(0, self._on_verify_done)

        threading.Thread(target=run, daemon=True).start()

    def _on_verify_done(self):
        self._is_running = False
        self._set_buttons_running(False)

    def _compute_diffs(self, original, typed):
        """원문과 입력된 텍스트의 차이를 계산하여 오류 목록 반환"""
        # 줄바꿈 정규화
        original = original.replace('\r\n', '\n')
        typed = typed.replace('\r\n', '\n')

        errors = []  # [(위치, 원문_조각, 입력_조각, 줄번호, 컬럼), ...]
        sm = difflib.SequenceMatcher(None, original, typed, autojunk=False)

        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'equal':
                continue
            # 줄번호/컬럼 계산 (원문 기준)
            line = original[:i1].count('\n') + 1
            last_nl = original[:i1].rfind('\n')
            col = i1 - last_nl  # 1-based
            errors.append({
                'type': tag,
                'pos': i1,
                'orig': original[i1:i2],
                'typed': typed[j1:j2],
                'line': line,
                'col': col,
                'orig_range': (i1, i2),
                'typed_range': (j1, j2),
            })

        return errors

    def _show_verify_result(self, typed_text):
        """검증 결과를 팝업으로 표시"""
        original = self._original_text.replace('\r\n', '\n')
        typed = typed_text.replace('\r\n', '\n')

        errors = self._compute_diffs(original, typed)

        if not errors:
            self._set_status("검증 완료: 원문과 100% 일치!", "#27ae60")
            messagebox.showinfo("검증 결과", "원문과 입력된 텍스트가 완벽하게 일치합니다!")
            return

        # 일치율 계산
        sm = difflib.SequenceMatcher(None, original, typed, autojunk=False)
        ratio = sm.ratio() * 100
        self._set_status(f"검증 완료: 일치율 {ratio:.1f}% — 오류 {len(errors)}건 발견", "#e74c3c")

        # 오류 저장 (수정 기능에서 사용)
        self._verify_errors = errors
        self._verify_typed = typed

        # --- 검증 결과 팝업 ---
        popup = tk.Toplevel(self.root)
        popup.title(f"검증 결과 — 일치율 {ratio:.1f}%")
        self._verify_popup = popup

        main_w = self.root.winfo_width()
        main_h = self.root.winfo_height()
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        popup.geometry(f"{main_w}x{main_h}+{main_x + 40}+{main_y + 40}")
        popup.minsize(800, 500)
        popup.resizable(True, True)
        popup.transient(self.root)

        # ── 하단 버튼 (BOTTOM에 먼저 pack → 창 크기 무관 항상 표시) ──
        bottom_area = tk.Frame(popup)
        bottom_area.pack(side="bottom", fill="x", padx=12, pady=(0, 8))

        # 클립보드 방식
        btn_frame1 = tk.Frame(bottom_area)
        btn_frame1.pack(fill="x", pady=(4, 0))

        tk.Label(btn_frame1, text="클립보드:", font=("맑은 고딕", 9),
                 fg="#7f8c8d").pack(side="left", padx=(0, 4))
        tk.Button(btn_frame1, text="전체 교체 (붙여넣기)", width=20,
                  font=("맑은 고딕", 10, "bold"), bg="#2980b9", fg="white",
                  command=lambda: self._fix_replace_all(popup)).pack(side="left", padx=3)
        tk.Button(btn_frame1, text="개별 수정 시작", width=14,
                  font=("맑은 고딕", 10, "bold"), bg="#e67e22", fg="white",
                  command=lambda: self._fix_errors_sequential(popup)).pack(side="left", padx=3)
        tk.Button(btn_frame1, text="닫기", width=8,
                  font=("맑은 고딕", 10), bg="#95a5a6", fg="white",
                  command=popup.destroy).pack(side="right", padx=3)

        # 타이핑 방식
        btn_frame2 = tk.Frame(bottom_area)
        btn_frame2.pack(fill="x", pady=(4, 0))

        tk.Label(btn_frame2, text="타이핑:", font=("맑은 고딕", 9),
                 fg="#7f8c8d").pack(side="left", padx=(0, 4))
        tk.Button(btn_frame2, text="전체 교체 (타이핑)", width=20,
                  font=("맑은 고딕", 10, "bold"), bg="#16a085", fg="white",
                  command=lambda: self._fix_replace_all_typing(popup)).pack(side="left", padx=3)
        tk.Label(btn_frame2,
                 text="* 붙여넣기 차단시 타이핑 사용",
                 font=("맑은 고딕", 9), fg="#e67e22").pack(side="right")

        # ── 상단 요약 ──
        summary_frame = tk.Frame(popup)
        summary_frame.pack(fill="x", padx=16, pady=(8, 4))

        # 오류 목록 + 미리보기 영역
        paned = tk.PanedWindow(popup, orient="vertical", sashwidth=6)
        paned.pack(fill="both", expand=True, padx=16, pady=(4, 8))

        # 상단: 텍스트 비교 (색상 하이라이트)
        compare_frame = tk.LabelFrame(popup, text="텍스트 비교 (빨강: 오류 / 초록: 올바른 텍스트)", padx=4, pady=4)

        compare_scroll = tk.Scrollbar(compare_frame)
        compare_scroll.pack(side="right", fill="y")

        self._compare_text = tk.Text(compare_frame, font=("맑은 고딕", 11), wrap="word",
                                      height=12, yscrollcommand=compare_scroll.set)
        self._compare_text.pack(fill="both", expand=True)
        compare_scroll.config(command=self._compare_text.yview)

        self._compare_text.tag_configure("match", foreground="black")
        self._compare_text.tag_configure("error_orig", foreground="white", background="#e74c3c",
                                          font=("맑은 고딕", 11, "bold"))
        self._compare_text.tag_configure("error_typed", foreground="white", background="#3498db",
                                          font=("맑은 고딕", 11, "bold"))
        self._compare_text.tag_configure("missing", foreground="white", background="#e67e22",
                                          font=("맑은 고딕", 11, "bold"))
        self._compare_text.tag_configure("section_label", foreground="#888",
                                          font=("맑은 고딕", 10, "bold"))

        # 원문 기준으로 색상 표시
        self._compare_text.insert("end", "[ 원문 기준 비교 ]\n", "section_label")
        sm = difflib.SequenceMatcher(None, original, typed, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'equal':
                self._compare_text.insert("end", original[i1:i2], "match")
            elif tag == 'replace':
                self._compare_text.insert("end", original[i1:i2], "error_orig")
            elif tag == 'delete':
                self._compare_text.insert("end", original[i1:i2], "missing")
            elif tag == 'insert':
                display = typed[j1:j2]
                if display.strip():
                    self._compare_text.insert("end", f"[+{display}]", "error_typed")

        self._compare_text.config(state="disabled")
        paned.add(compare_frame)

        # 하단: 오류 목록 테이블
        list_frame = tk.LabelFrame(popup, text=f"오류 목록 ({len(errors)}건)", padx=4, pady=4)

        list_scroll = tk.Scrollbar(list_frame)
        list_scroll.pack(side="right", fill="y")

        self._error_list = tk.Text(list_frame, font=("Consolas", 10), wrap="none",
                                    height=8, yscrollcommand=list_scroll.set)
        self._error_list.pack(fill="both", expand=True)
        list_scroll.config(command=self._error_list.yview)

        self._error_list.tag_configure("header", font=("맑은 고딕", 10, "bold"),
                                        background="#ecf0f1")
        self._error_list.tag_configure("replace_tag", foreground="#e74c3c")
        self._error_list.tag_configure("delete_tag", foreground="#e67e22")
        self._error_list.tag_configure("insert_tag", foreground="#3498db")

        self._error_list.insert("end",
            f"{'#':>4}  {'줄':>4}  {'컬럼':>4}  {'유형':<8} {'원문':<20} {'입력됨':<20}\n", "header")
        self._error_list.insert("end", "\u2500" * 70 + "\n")

        type_names = {'replace': '교체', 'delete': '누락', 'insert': '추가됨'}
        type_tags = {'replace': 'replace_tag', 'delete': 'delete_tag', 'insert': 'insert_tag'}

        for idx, err in enumerate(errors):
            orig_disp = repr(err['orig'])[:18] if err['orig'] else '(없음)'
            typed_disp = repr(err['typed'])[:18] if err['typed'] else '(없음)'
            type_name = type_names.get(err['type'], err['type'])
            tag = type_tags.get(err['type'], 'replace_tag')
            line = f"{idx+1:>4}  {err['line']:>4}  {err['col']:>4}  {type_name:<8} {orig_disp:<20} {typed_disp:<20}\n"
            self._error_list.insert("end", line, tag)

        self._error_list.config(state="disabled")
        paned.add(list_frame)

    def _fix_replace_all(self, popup):
        """전체 교체: 대상 창에서 Ctrl+A → 원문 전체를 클립보드로 붙여넣기"""
        answer = messagebox.askyesno(
            "전체 교체",
            "대상 창의 텍스트를 전체 선택 후 원문으로 교체합니다.\n\n"
            "3초 후 실행됩니다. 대상 창에 포커스를 이동하세요.\n\n"
            "진행할까요?",
            parent=popup
        )
        if not answer:
            return

        popup.destroy()
        original = self._original_text.replace('\r\n', '\n')
        self._is_running = True
        self._set_buttons_running(True)
        self._set_status("3초 후 전체 교체... (대상 창에 포커스를 이동하세요)", "orange")
        self._fix_countdown(3, "replace_all", original)

    def _fix_replace_all_typing(self, popup):
        """전체 교체 (타이핑 모드): Ctrl+A → Delete → TypingEngine으로 전체 재입력
        붙여넣기가 차단된 환경에서 사용"""
        answer = messagebox.askyesno(
            "전체 교체 (타이핑 모드)",
            "대상 창의 텍스트를 전체 삭제 후, 원문을 처음부터\n"
            "키보드 타이핑으로 다시 입력합니다.\n\n"
            "붙여넣기(Ctrl+V)를 사용하지 않으므로\n"
            "복사/붙여넣기 차단 환경에서도 작동합니다.\n\n"
            "3초 후 실행됩니다. 대상 창에 포커스를 이동하세요.\n\n"
            "진행할까요?",
            parent=popup
        )
        if not answer:
            return

        popup.destroy()
        original = self._original_text.replace('\r\n', '\n')
        self._is_running = True
        self._set_buttons_running(True)
        self._set_status("3초 후 타이핑 모드 전체 교체... (대상 창에 포커스를 이동하세요)", "orange")
        self._fix_countdown(3, "replace_all_typing", original)

    def _execute_replace_all_typing(self, original_text):
        """대상 창에서 전체 선택 → 삭제 → TypingEngine으로 전체 재입력"""
        def run():
            try:
                if not pyautogui:
                    self.root.after(0, lambda: messagebox.showerror(
                        "오류", "pyautogui가 설치되지 않았습니다."))
                    return

                # 1. 대상 창에서 전체 선택 후 삭제
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.3)
                pyautogui.press('delete')
                time.sleep(0.3)

                # 2. TypingEngine으로 전체 재입력
                delay_ms = 50
                try:
                    delay_ms = int(self.delay_var.get())
                except Exception:
                    delay_ms = 50
                delay_sec = delay_ms / 1000.0

                mode_val = self.mode_var.get() if hasattr(self, 'mode_var') else "hybrid"

                engine = TypingEngine(
                    mode=mode_val,
                    delay=delay_sec,
                    on_progress=self._on_engine_progress,
                    on_status=self._on_engine_status,
                    focus_guard=False,  # 이미 포커스 이동 완료
                    start_index=0,
                )
                self._engine = engine

                engine.type_text(original_text)

                if engine.is_stopped():
                    self.root.after(0, self._set_status,
                                    "타이핑 교체가 중단되었습니다.", "#e67e22")
                else:
                    self.root.after(0, self._set_status,
                                    "타이핑 모드 전체 교체 완료!", "#27ae60")

            except Exception as ex:
                self.root.after(0, lambda: messagebox.showerror("오류", str(ex)))
            finally:
                self.root.after(0, self._on_fix_done)

        threading.Thread(target=run, daemon=True).start()

    def _fix_errors_sequential(self, popup):
        """개별 수정: 오류를 하나씩 찾아서 수정"""
        if not self._verify_errors:
            messagebox.showinfo("알림", "수정할 오류가 없습니다.", parent=popup)
            return

        answer = messagebox.askyesno(
            "개별 수정",
            f"총 {len(self._verify_errors)}건의 오류를 순서대로 수정합니다.\n\n"
            "Ctrl+H (찾기/바꾸기)를 사용하여 오류를 수정합니다.\n"
            "3초 후 실행됩니다. 대상 창에 포커스를 이동하세요.\n\n"
            "진행할까요?",
            parent=popup
        )
        if not answer:
            return

        popup.destroy()
        self._is_running = True
        self._set_buttons_running(True)
        self._set_status("3초 후 개별 수정 시작... (대상 창에 포커스를 이동하세요)", "orange")
        self._fix_countdown(3, "sequential", None)

    def _fix_countdown(self, remaining, fix_mode, data):
        if remaining > 0:
            self._set_status(f"{remaining}초 후 수정 시작...", "orange")
            self._countdown_id = self.root.after(1000, self._fix_countdown,
                                                  remaining - 1, fix_mode, data)
        else:
            self._countdown_id = None
            if fix_mode == "replace_all":
                self._execute_replace_all(data)
            elif fix_mode == "replace_all_typing":
                self._execute_replace_all_typing(data)
            elif fix_mode == "fix_typing_then_resume":
                self._execute_fix_typing_then_resume()
            elif fix_mode == "sequential":
                self._execute_sequential_fix()
            elif fix_mode == "fix_then_resume":
                self._execute_fix_then_resume()

    def _execute_replace_all(self, original_text):
        """대상 창에서 전체 선택 후 원문 붙여넣기"""
        def run():
            try:
                if pyperclip and pyautogui:
                    # 원문을 클립보드에 복사
                    pyperclip.copy(original_text)
                    time.sleep(0.1)
                    # 대상 창에서 전체 선택 후 붙여넣기
                    pyautogui.hotkey('ctrl', 'a')
                    time.sleep(0.2)
                    pyautogui.hotkey('ctrl', 'v')
                    time.sleep(0.3)
                    self.root.after(0, self._set_status,
                                    "전체 교체 완료! 검증(F7)으로 다시 확인하세요.", "#27ae60")
            except Exception as ex:
                self.root.after(0, lambda: messagebox.showerror("오류", str(ex)))
            finally:
                self.root.after(0, self._on_fix_done)

        threading.Thread(target=run, daemon=True).start()

    def _execute_sequential_fix(self):
        """오류를 하나씩 Ctrl+H로 수정"""
        errors = self._verify_errors
        # replace/delete만 수정 가능 (insert는 대상 창에 추가된 것이므로 수동 처리)
        fixable = [e for e in errors if e['type'] in ('replace', 'delete')]

        if not fixable:
            self._set_status("자동 수정 가능한 오류가 없습니다.", "orange")
            self._on_fix_done()
            return

        def run():
            try:
                if not pyautogui:
                    return

                total_fixes = len(fixable)

                for idx, err in enumerate(fixable):
                    # Ctrl+Home으로 문서 맨 앞으로
                    pyautogui.hotkey('ctrl', 'Home')
                    time.sleep(0.2)

                    # 커서를 오류 위치로 이동 (줄 → 컬럼)
                    target_line = err['line']
                    target_col = err['col']

                    # 줄 이동 (Down 키)
                    if target_line > 1:
                        for _ in range(target_line - 1):
                            pyautogui.press('down')
                            time.sleep(0.01)
                    # Home으로 줄 맨 앞
                    pyautogui.press('home')
                    time.sleep(0.05)
                    # 컬럼 이동 (Right 키)
                    if target_col > 1:
                        for _ in range(target_col - 1):
                            pyautogui.press('right')
                            time.sleep(0.01)

                    # 오류 범위 선택 (Shift+Right)
                    orig_len = len(err['orig'])
                    if orig_len > 0:
                        for _ in range(orig_len):
                            pyautogui.hotkey('shift', 'right')
                            time.sleep(0.01)

                    time.sleep(0.1)

                    # 올바른 텍스트로 교체 (클립보드 방식)
                    correct = err['orig']  # 원문이 정답
                    if err['type'] == 'replace':
                        # 틀린 부분을 선택한 상태에서 올바른 텍스트 붙여넣기
                        if pyperclip:
                            pyperclip.copy(correct)
                            pyautogui.hotkey('ctrl', 'v')
                            time.sleep(0.1)
                    elif err['type'] == 'delete':
                        # 누락된 텍스트를 현재 위치에 삽입
                        pyautogui.press('right')  # 선택 해제
                        time.sleep(0.05)
                        # 뒤로 돌아가서 삽입 위치에
                        for _ in range(orig_len):
                            pyautogui.press('left')
                            time.sleep(0.01)
                        if pyperclip:
                            pyperclip.copy(correct)
                            pyautogui.hotkey('ctrl', 'v')
                            time.sleep(0.1)

                    self.root.after(0, self._set_status,
                                    f"수정 중... {idx+1}/{total_fixes}", "#e67e22")
                    time.sleep(0.2)

                self.root.after(0, self._set_status,
                                f"개별 수정 완료 ({total_fixes}건)! 검증(F7)으로 다시 확인하세요.",
                                "#27ae60")
            except Exception as ex:
                self.root.after(0, lambda: messagebox.showerror("오류", str(ex)))
            finally:
                self.root.after(0, self._on_fix_done)

        threading.Thread(target=run, daemon=True).start()

    def _execute_fix_then_resume(self):
        """오류를 수정한 뒤 자동으로 이어쓰기까지 진행"""
        errors = self._verify_errors
        fixable = [e for e in errors if e['type'] in ('replace', 'delete')]
        resume_idx = getattr(self, '_pending_resume_index', 0)

        def run():
            try:
                if not pyautogui:
                    return

                # 1단계: 오류 수정
                if fixable:
                    total_fixes = len(fixable)
                    for idx, err in enumerate(fixable):
                        pyautogui.hotkey('ctrl', 'Home')
                        time.sleep(0.2)

                        target_line = err['line']
                        target_col = err['col']

                        if target_line > 1:
                            for _ in range(target_line - 1):
                                pyautogui.press('down')
                                time.sleep(0.01)
                        pyautogui.press('home')
                        time.sleep(0.05)
                        if target_col > 1:
                            for _ in range(target_col - 1):
                                pyautogui.press('right')
                                time.sleep(0.01)

                        orig_len = len(err['orig'])
                        if orig_len > 0:
                            for _ in range(orig_len):
                                pyautogui.hotkey('shift', 'right')
                                time.sleep(0.01)

                        time.sleep(0.1)

                        correct = err['orig']
                        if err['type'] == 'replace':
                            if pyperclip:
                                pyperclip.copy(correct)
                                pyautogui.hotkey('ctrl', 'v')
                                time.sleep(0.1)
                        elif err['type'] == 'delete':
                            pyautogui.press('right')
                            time.sleep(0.05)
                            for _ in range(orig_len):
                                pyautogui.press('left')
                                time.sleep(0.01)
                            if pyperclip:
                                pyperclip.copy(correct)
                                pyautogui.hotkey('ctrl', 'v')
                                time.sleep(0.1)

                        self.root.after(0, self._set_status,
                                        f"오류 수정 중... {idx+1}/{total_fixes}", "#e67e22")
                        time.sleep(0.2)

                    self.root.after(0, self._set_status,
                                    f"오류 {total_fixes}건 수정 완료! 이어쓰기로 전환...", "#27ae60")
                    time.sleep(0.5)

                # 2단계: 커서를 문서 끝으로 이동 후 이어쓰기 시작
                pyautogui.hotkey('ctrl', 'End')
                time.sleep(0.2)

                self.root.after(0, self._start_resume_typing, resume_idx)

            except Exception as ex:
                self.root.after(0, lambda: messagebox.showerror("오류", str(ex)))
                self.root.after(0, self._on_fix_done)

        threading.Thread(target=run, daemon=True).start()

    def _execute_fix_typing_then_resume(self):
        """타이핑 방식으로 오류를 수정한 뒤 자동으로 이어쓰기 (클립보드 미사용)"""
        errors = self._verify_errors
        fixable = [e for e in errors if e['type'] in ('replace', 'delete')]
        resume_idx = getattr(self, '_pending_resume_index', 0)
        original = self._pending_text

        def run():
            try:
                if not pyautogui:
                    return

                # 타이핑 방식 수정: Ctrl+A → Delete → 처음부터 resume_idx 까지 재입력
                # 개별 오류를 찾아가며 수정하는 것보다 전체 재타이핑이 더 안정적
                self.root.after(0, self._set_status, "전체 선택 후 삭제 중...", "#e67e22")

                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.3)
                pyautogui.press('delete')
                time.sleep(0.3)

                # resume_idx까지의 텍스트를 타이핑 엔진으로 입력
                text_to_fix = original[:resume_idx]

                if text_to_fix:
                    self.root.after(0, self._set_status,
                                    f"수정된 텍스트 재입력 중... (0/{resume_idx}자)", "#e67e22")

                    delay_ms = 50
                    try:
                        delay_ms = int(self.delay_var.get())
                    except Exception:
                        delay_ms = 50
                    delay_sec = delay_ms / 1000.0

                    mode_val = self.mode_var.get() if hasattr(self, 'mode_var') else "hybrid"

                    engine = TypingEngine(
                        mode=mode_val,
                        delay=delay_sec,
                        on_progress=self._on_engine_progress,
                        on_status=lambda msg: self.root.after(
                            0, self._set_status, f"수정 재입력: {msg}", "#e67e22"),
                        focus_guard=False,
                        start_index=0,
                    )
                    self._engine = engine
                    engine.type_text(text_to_fix)

                    if engine.is_stopped():
                        self.root.after(0, self._set_status, "수정 재입력 중단됨", "#e67e22")
                        self.root.after(0, self._on_fix_done)
                        return

                self.root.after(0, self._set_status,
                                f"수정 완료! 이어쓰기로 전환... ({resume_idx}자부터)", "#27ae60")
                time.sleep(0.3)

                # 이어쓰기 시작
                self.root.after(0, self._start_resume_typing, resume_idx)

            except Exception as ex:
                self.root.after(0, lambda: messagebox.showerror("오류", str(ex)))
                self.root.after(0, self._on_fix_done)

        threading.Thread(target=run, daemon=True).start()

    def _start_resume_typing(self, resume_idx):
        """오류 수정 후 이어쓰기 타이핑 시작"""
        self._resume_index = resume_idx
        self._begin_typing(self._pending_text)

    def _on_fix_done(self):
        self._is_running = False
        self._set_buttons_running(False)

    def _show_info_popup(self):
        """프로그램 기능 설명 팝업 (메인 윈도우와 동일 크기)"""
        popup = tk.Toplevel(self.root)
        popup.title("프로그램 안내")

        # 메인 윈도우와 동일한 크기로 설정
        main_w = self.root.winfo_width()
        main_h = self.root.winfo_height()
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        popup.geometry(f"{main_w}x{main_h}+{main_x + 40}+{main_y + 40}")
        popup.minsize(960, 700)
        popup.resizable(True, True)
        popup.transient(self.root)
        popup.grab_set()

        # 제목 영역
        title_frame = tk.Frame(popup)
        title_frame.pack(fill="x", padx=40, pady=(30, 8))
        tk.Label(title_frame, text="HM AutoTyper v3.1", font=("Arial", 24, "bold")).pack()
        tk.Label(title_frame, text="SendInput 유니코드 · 한/영 자동 전환 · 이어쓰기 · 검증 · 붙여넣기 차단 우회",
                 font=("맑은 고딕", 12), fg="gray").pack(pady=(4, 0))
        tk.Label(title_frame, text="\u00a9 2026 haemin. All rights reserved. 무단 배포 및 판매 금지.",
                 font=("맑은 고딕", 10), fg="#e74c3c").pack(pady=(6, 0))
        tk.Label(title_frame, text="문의: hm.autotyper@gmail.com",
                 font=("맑은 고딕", 10), fg="#7f8c8d").pack(pady=(2, 0))

        # 구분선
        tk.Frame(popup, height=2, bg="#ddd").pack(fill="x", padx=40, pady=12)

        # 스크롤 가능한 텍스트 영역
        text_frame = tk.Frame(popup)
        text_frame.pack(fill="both", expand=True, padx=40, pady=(8, 8))

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")

        info_widget = tk.Text(text_frame, font=("맑은 고딕", 12), wrap="word",
                              relief="flat", bg=popup.cget("bg"), cursor="arrow",
                              spacing1=2, spacing3=2,
                              yscrollcommand=scrollbar.set)
        info_widget.pack(fill="both", expand=True)
        scrollbar.config(command=info_widget.yview)

        # 텍스트 스타일 태그
        info_widget.tag_configure("section", font=("맑은 고딕", 16, "bold"),
                                  spacing1=20, spacing3=10)
        info_widget.tag_configure("subsection", font=("맑은 고딕", 13, "bold"),
                                  spacing1=14, spacing3=6)
        info_widget.tag_configure("mode_title", font=("맑은 고딕", 12, "bold"),
                                  spacing1=10, spacing3=2)
        info_widget.tag_configure("desc", font=("맑은 고딕", 11),
                                  lmargin1=40, lmargin2=40, spacing3=4)
        info_widget.tag_configure("hotkey", font=("Consolas", 11),
                                  lmargin1=40, lmargin2=40, spacing3=2)
        info_widget.tag_configure("feature", font=("맑은 고딕", 11),
                                  lmargin1=40, lmargin2=52, spacing3=4)
        info_widget.tag_configure("table_header", font=("맑은 고딕", 11, "bold"),
                                  background="#e8e8e8", spacing1=2, spacing3=2)
        info_widget.tag_configure("table_row", font=("맑은 고딕", 10),
                                  spacing1=1, spacing3=1)
        info_widget.tag_configure("table_row_alt", font=("맑은 고딕", 10),
                                  background="#f5f5f5", spacing1=1, spacing3=1)
        info_widget.tag_configure("divider", font=("Arial", 4),
                                  spacing1=8, spacing3=8)
        info_widget.tag_configure("tip", font=("맑은 고딕", 11, "italic"),
                                  foreground="#2980b9", lmargin1=40, lmargin2=40, spacing3=4)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 1. 빠른 시작 가이드
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        info_widget.insert("end", "1. 빠른 시작 가이드\n", "section")

        info_widget.insert("end", "  \u2460  텍스트 입력\n", "mode_title")
        info_widget.insert("end", "메인 화면의 텍스트 영역에 자동 타이핑할 내용을 입력하거나 Ctrl+V로 붙여넣기합니다.\n\n", "desc")

        info_widget.insert("end", "  \u2461  모드 선택\n", "mode_title")
        info_widget.insert("end", "설정 패널에서 타이핑 / 클립보드 / 하이브리드 중 원하는 모드를 선택합니다. 잘 모르겠으면 하이브리드(기본값)를 그대로 사용하세요.\n\n", "desc")

        info_widget.insert("end", "  \u2462  딜레이 조절\n", "mode_title")
        info_widget.insert("end", "슬라이더로 글자 간 입력 속도를 0~500ms 범위에서 설정합니다. 기본값 50ms를 추천합니다.\n\n", "desc")

        info_widget.insert("end", "  \u2463  시작 (F6)\n", "mode_title")
        info_widget.insert("end", "\"시작(F6)\" 버튼 또는 F6 키를 누르면 3초 카운트다운이 시작됩니다. 카운트다운 동안 타이핑할 대상 창(메모장, 브라우저 입력란 등)을 클릭하여 포커스를 이동하세요. 3초 후 자동으로 타이핑이 시작됩니다.\n\n", "desc")

        info_widget.insert("end", "  \u2464  정지 (ESC)\n", "mode_title")
        info_widget.insert("end", "\"정지(ESC)\" 버튼 또는 ESC 키를 누르면 즉시 정지합니다. 포커스 가드가 켜져 있으면 다른 창을 클릭하는 것만으로도 자동으로 정지됩니다.\n\n", "desc")

        info_widget.insert("end", "  \u2465  검증 (F7)\n", "mode_title")
        info_widget.insert("end", "타이핑 완료 후 \"검증(F7)\" 버튼 또는 F7 키를 누르면, 대상 창의 텍스트를 자동으로 읽어와 원문과 비교합니다. 오류가 있으면 어디가 다른지 색상으로 표시해줍니다.\n\n", "desc")

        info_widget.insert("end", "\ud83d\udca1 전체 흐름: 텍스트 입력 \u2192 시작(F6) \u2192 대상 창 클릭 \u2192 자동 타이핑 \u2192 검증(F7) \u2192 수정\n\n", "tip")

        # 구분선
        info_widget.insert("end", "\u2500" * 60 + "\n", "divider")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 2. 타이핑 모드
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        info_widget.insert("end", "2. 타이핑 모드 안내\n", "section")

        info_widget.insert("end", "  \u2b50  하이브리드 (추천)\n", "mode_title")
        info_widget.insert("end", "한글은 자모 분해로 실제 타이핑하는 것처럼 입력하고, 영어/숫자/기호는 SendInput 유니코드로 직접 입력합니다. 클립보드를 사용하지 않으며, 한/영 IME 전환도 불필요합니다. 대부분의 상황에서 권장됩니다.\n\n", "desc")

        info_widget.insert("end", "  \u2328  타이핑\n", "mode_title")
        info_widget.insert("end", "한글은 자모 분해 키보드 시뮬레이션으로, 영문/숫자/기호는 SendInput 유니코드로 입력합니다. 한/영 IME 전환 없이 영문을 OS에 직접 유니코드로 전달하므로 한/영 전환 오류가 발생하지 않습니다. 클립보드를 사용하지 않아 붙여넣기 차단 환경에서도 작동합니다.\n\n", "desc")

        info_widget.insert("end", "  \U0001f4cb  클립보드 (가장 안정)\n", "mode_title")
        info_widget.insert("end", "모든 글자를 한 글자씩 클립보드에 복사 후 Ctrl+V로 붙여넣기합니다. 타이핑 효과는 없지만 오타가 거의 발생하지 않아 정확성이 가장 중요할 때 사용합니다.\n\n", "desc")

        info_widget.insert("end", "  \u2714  v3.1 핵심 개선: SendInput 유니코드 입력\n", "mode_title")
        info_widget.insert("end", "v3.0까지는 영문 입력 시 IME를 영문 모드로 전환해야 했는데, 이 전환이 불안정하여 한글 자모가 깨지는 문제가 있었습니다. v3.1에서는 영문/숫자/특수문자를 Windows SendInput API의 KEYEVENTF_UNICODE 플래그로 직접 전송합니다. 이 방식은 IME를 완전히 우회하여 한글 모드 상태에서도 영문이 정확히 입력됩니다. 한\u2192영 전환 자체가 사라졌기 때문에 전환 실패가 원천 불가능합니다.\n\n", "desc")

        info_widget.insert("end", "\ud83d\udca1 어떤 모드를 선택할지 모르겠다면 하이브리드(기본값)를 사용하세요.\n\n", "tip")

        # 구분선
        info_widget.insert("end", "\u2500" * 60 + "\n", "divider")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 3. 핫키
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        info_widget.insert("end", "3. 핫키\n", "section")
        info_widget.insert("end", "  F6           타이핑 시작 (3초 카운트다운 후)\n", "hotkey")
        info_widget.insert("end", "  F7           검증 시작 (대상 창 텍스트와 원문 비교)\n", "hotkey")
        info_widget.insert("end", "  ESC         타이핑 즉시 정지\n\n", "hotkey")
        info_widget.insert("end", "keyboard 라이브러리가 설치되어 있으면 프로그램에 포커스가 없어도 핫키가 동작합니다.\n\n", "desc")

        # 구분선
        info_widget.insert("end", "\u2500" * 60 + "\n", "divider")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 4. 설정 옵션
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        info_widget.insert("end", "4. 설정 옵션\n", "section")

        info_widget.insert("end", "  포커스 이탈 시 자동 중지\n", "subsection")
        info_widget.insert("end", "타이핑 도중 다른 창을 클릭하면 즉시 타이핑을 멈추는 안전장치입니다. 실수로 다른 곳에 타이핑되는 것을 방지합니다. 기본값: 켜짐\n\n", "desc")

        info_widget.insert("end", "  이어쓰기\n", "subsection")
        info_widget.insert("end", "타이핑이 중간에 중단된 경우(포커스 이탈, ESC 등), 다시 시작(F6)을 누르면 \"이어서 입력할지 / 처음부터 다시 할지\" 선택할 수 있습니다. 이어쓰기를 선택하면 중단된 지점부터 타이핑을 계속합니다. 기본값: 켜짐\n\n", "desc")
        info_widget.insert("end", "\ud83d\udca1 이어쓰기는 텍스트 내용이 바뀌지 않은 경우에만 동작합니다. 텍스트를 수정하면 자동으로 처음부터 시작합니다.\n\n", "tip")

        info_widget.insert("end", "  딜레이(ms)\n", "subsection")
        info_widget.insert("end", "글자와 글자 사이의 대기 시간입니다. 슬라이더로 0~500ms까지 조절할 수 있습니다. 딜레이가 짧을수록 빠르지만 오타가 발생할 수 있습니다.\n\n", "desc")


        info_widget.insert("end", "  초기화\n", "subsection")
        info_widget.insert("end", "타이핑을 정지한 후 \"초기화\" 버튼을 누르면 진행 상태를 처음부터 다시 시작할 수 있습니다. 이어쓰기 위치, 진행률 바, 상태 메시지가 모두 리셋됩니다. 텍스트 내용은 유지됩니다.\n\n", "desc")

        # 구분선
        info_widget.insert("end", "\u2500" * 60 + "\n", "divider")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 5. 검증 기능
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        info_widget.insert("end", "5. 검증 기능 (F7)\n", "section")
        info_widget.insert("end", "타이핑 완료 후 입력된 내용이 원문과 일치하는지 자동으로 확인하는 기능입니다.\n\n", "desc")

        info_widget.insert("end", "  클립보드 검증 (기본)\n", "subsection")
        info_widget.insert("end", "  \u2460  타이핑이 완료된 상태에서 \"검증(F7)\" 버튼을 클릭합니다.\n", "feature")
        info_widget.insert("end", "  \u2461  3초 카운트다운 동안 대상 창(타이핑된 곳)을 클릭합니다.\n", "feature")
        info_widget.insert("end", "  \u2462  프로그램이 자동으로 Ctrl+A(전체선택) \u2192 Ctrl+C(복사)를 실행합니다.\n", "feature")
        info_widget.insert("end", "  \u2463  복사된 텍스트와 원문을 비교하여 결과 팝업을 표시합니다.\n\n", "feature")

        info_widget.insert("end", "  검증 결과 화면\n", "subsection")
        info_widget.insert("end", "  \u2022  상단 요약 \u2014 일치율(%), 오류 건수, 원문/입력 글자 수\n", "feature")
        info_widget.insert("end", "  \u2022  텍스트 비교 \u2014 원문 기준으로 색상 하이라이트 표시\n", "feature")
        info_widget.insert("end", "       빨강: 잘못 입력된 부분 / 주황: 누락된 부분 / 파랑: 추가로 입력된 부분\n", "feature")
        info_widget.insert("end", "  \u2022  오류 목록 \u2014 각 오류의 줄 번호, 컬럼 위치, 유형, 원문 vs 입력됨\n", "feature")
        info_widget.insert("end", "  \u2022  수정 버튼 \u2014 클립보드 방식(전체교체/개별수정) 제공\n\n", "feature")

        info_widget.insert("end", "\ud83d\udca1 일반 프로그램(메모장, 워드 등)에서는 F7 클립보드 검증을 사용하세요.\n", "tip")

        # 구분선
        info_widget.insert("end", "\u2500" * 60 + "\n", "divider")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 6. 오류 수정 기능
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        info_widget.insert("end", "6. 오류 수정 기능\n", "section")
        info_widget.insert("end", "검증 결과에서 오류가 발견되면 클립보드 방식과 타이핑 방식, 두 가지 계열로 수정할 수 있습니다.\n\n", "desc")

        info_widget.insert("end", "  [클립보드 방식] 전체 교체 붙여넣기\n", "subsection")
        info_widget.insert("end", "대상 창의 텍스트를 Ctrl+A로 전체 선택한 뒤, 원문 전체를 클립보드로 붙여넣어 교체합니다. 가장 확실하고 빠른 방법입니다. 붙여넣기가 가능한 환경에서 사용하세요.\n\n", "desc")

        info_widget.insert("end", "  [클립보드 방식] 개별 수정\n", "subsection")
        info_widget.insert("end", "오류가 발견된 위치로 커서를 자동으로 이동시켜 하나씩 수정합니다. 동작 순서:\n", "desc")
        info_widget.insert("end", "  \u2460  Ctrl+Home으로 문서 맨 앞으로 이동\n", "feature")
        info_widget.insert("end", "  \u2461  방향키로 오류 위치(줄, 컬럼)까지 커서 이동\n", "feature")
        info_widget.insert("end", "  \u2462  Shift+방향키로 오류 범위 선택\n", "feature")
        info_widget.insert("end", "  \u2463  올바른 텍스트를 클립보드로 붙여넣어 교체\n", "feature")
        info_widget.insert("end", "  \u2464  다음 오류로 이동하여 반복\n\n", "feature")

        info_widget.insert("end", "  [타이핑 방식] 전체 교체 타이핑\n", "subsection")
        info_widget.insert("end", "붙여넣기가 차단된 환경(블로그, 시험 사이트 등)에서 사용합니다. Ctrl+A \u2192 Delete로 기존 텍스트를 모두 지운 뒤, 타이핑 엔진으로 원문 전체를 처음부터 다시 입력합니다.\n\n", "desc")

        info_widget.insert("end", "  [타이핑 방식] 오류 수정 후 이어쓰기\n", "subsection")
        info_widget.insert("end", "이어쓰기 분석 결과 화면에서 사용합니다. 기존 텍스트를 지우고 오류 지점까지 타이핑으로 재입력한 뒤, 나머지 텍스트를 이어서 타이핑합니다. 붙여넣기가 차단된 환경에서 이어쓰기가 필요할 때 유용합니다.\n\n", "desc")

        info_widget.insert("end", "\ud83d\udca1 붙여넣기가 되는 환경 \u2192 클립보드 방식(전체교체 붙여넣기 / 개별수정)을 사용하세요.\n", "tip")
        info_widget.insert("end", "\ud83d\udca1 붙여넣기 차단 환경 \u2192 타이핑 방식(전체교체 타이핑)을 사용하세요.\n", "tip")
        info_widget.insert("end", "\ud83d\udca1 수정 후에는 검증(F7)으로 다시 확인하는 것을 권장합니다.\n\n", "tip")

        # 구분선
        info_widget.insert("end", "\u2500" * 60 + "\n", "divider")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 7. 딜레이 가이드
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        info_widget.insert("end", "7. 딜레이 설정 가이드\n", "section")

        info_widget.insert("end", "  권장 딜레이\n", "subsection")
        info_widget.insert("end", "  30~50ms      빠르면서도 안정적 (일반 권장)\n", "hotkey")
        info_widget.insert("end", "  50ms 이상     안정성이 중요할 때\n", "hotkey")
        info_widget.insert("end", "  10ms 이하     환경에 따라 오타 발생 가능\n\n", "hotkey")

        info_widget.insert("end", "  모드별 오타 특성\n", "subsection")
        info_widget.insert("end", "  \u2022  타이핑/하이브리드 모드 \u2014 한글 자모 분해 시 딜레이가 너무 짧으면 OS 입력 버퍼가 밀려 글자가 깨질 수 있습니다. 영문은 SendInput 유니코드로 처리되어 오타가 거의 없습니다.\n", "feature")
        info_widget.insert("end", "  \u2022  클립보드 모드 \u2014 붙여넣기 방식이므로 딜레이와 오타는 거의 무관합니다.\n\n", "feature")

        info_widget.insert("end", "\ud83d\udca1 오타가 발생하면 딜레이를 50ms 이상으로 올리거나, 검증(F7) 후 자동 수정을 활용하세요.\n\n", "tip")

        # 구분선
        info_widget.insert("end", "\u2500" * 60 + "\n", "divider")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 8. 주요 기능 목록
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        info_widget.insert("end", "8. 주요 기능 목록\n", "section")
        info_widget.insert("end", "  \u2022  SendInput 유니코드 입력 \u2014 영문/숫자/기호를 IME 우회하여 직접 전송, 한/영 전환 오류 원천 차단\n", "feature")
        info_widget.insert("end", "  \u2022  한글 자모 분해 타이핑 \u2014 한글 구간에서 IME 한글 모드 자동 전환, 매 글자마다 상태 확인\n", "feature")
        info_widget.insert("end", "  \u2022  3가지 타이핑 모드 \u2014 상황에 맞게 타이핑 / 클립보드 / 하이브리드 선택\n", "feature")
        info_widget.insert("end", "  \u2022  딜레이 조절 \u2014 글자 간 입력 속도를 0~500ms로 자유롭게 설정\n", "feature")
        info_widget.insert("end", "  \u2022  포커스 가드 \u2014 다른 창을 클릭하면 타이핑 자동 중지 (안전장치)\n", "feature")
        info_widget.insert("end", "  \u2022  이어쓰기 \u2014 중단 후 다시 시작하면 이어서 입력 가능\n", "feature")
        info_widget.insert("end", "  \u2022  초기화 \u2014 진행 상태를 리셋하여 처음부터 다시 시작\n", "feature")
        info_widget.insert("end", "  \u2022  검증 (F7) \u2014 타이핑 결과를 원문과 비교하여 차이점 표시\n", "feature")
        info_widget.insert("end", "  \u2022  자동 수정 (클립보드) \u2014 전체 교체 붙여넣기 또는 개별 오류 위치 수정\n", "feature")
        info_widget.insert("end", "  \u2022  자동 수정 (타이핑) \u2014 전체 교체 타이핑 또는 오류 수정 후 이어쓰기\n", "feature")
        info_widget.insert("end", "  \u2022  진행률 표시 \u2014 프로그레스 바와 글자 수로 실시간 진행 확인\n", "feature")
        info_widget.insert("end", "  \u2022  클립보드 복원 \u2014 타이핑 완료 후 원래 클립보드 내용을 자동 복원\n", "feature")
        info_widget.insert("end", "  \u2022  3초 카운트다운 \u2014 시작 전 대상 창으로 포커스를 이동할 시간 확보\n", "feature")
        info_widget.insert("end", "  \u2022  고해상도 DPI 지원 \u2014 고해상도 모니터에서도 선명한 UI\n\n", "feature")

        # 구분선
        info_widget.insert("end", "\u2500" * 60 + "\n", "divider")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 9. 비교표 (원본 vs HM)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        info_widget.insert("end", "9. 원본(autotyper.exe) vs HM AutoTyper v3.1 비교\n", "section")

        # 테이블 데이터
        table_data = [
            ("타이핑 모드",      "1가지 (자모 분해만)",                    "3가지 (타이핑/클립보드/하이브리드)"),
            ("한/영 전환",       "수동 (사용자가 직접 설정)",              "SendInput 유니코드 (전환 불필요)"),
            ("핫키",             "없음 (버튼 클릭만)",                     "F6 시작 / F7 검증 / ESC 정지"),
            ("시작 방식",        "바로 시작",                              "3초 카운트다운 후 시작"),
            ("진행률 표시",      "없음",                                   "프로그레스 바 + 글자 수 표시"),
            ("포커스 가드",      "없음",                                   "다른 창 클릭 시 자동 중지"),
            ("클립보드 복원",    "없음",                                   "타이핑 후 자동 복원"),
            ("검증 기능",        "없음",                                   "클립보드 검증 (Ctrl+A → Ctrl+C)"),
            ("오류 수정",        "없음",                                   "클립보드 방식 + 타이핑 방식 4가지"),
            ("초기화",           "없음",                                   "진행 상태 리셋 후 처음부터 시작"),
            ("이어쓰기",         "없음",                                   "중단 지점부터 이어서 입력"),
            ("영문/특수문자",    "단순 write()",                           "SendInput 유니코드 직접 전송"),
            ("복합 모음/종성",   "기본적",                                 "ㅘ,ㅙ,ㅚ / ㄳ,ㄵ 등 완전 지원"),
            ("UI 크기",          "400\u00d7480 (고정)",                    "1160\u00d7960 (리사이즈 가능)"),
            ("다크모드",         "없음",                                   "customtkinter 지원 시 가능"),
            ("DPI 지원",         "없음",                                   "고해상도 모니터 대응"),
            ("붙여넣기 차단 우회", "없음",                                 "타이핑 방식 전체교체/이어쓰기"),
        ]

        # 컬럼 너비 (문자 수 기준)
        col_w = [20, 28, 36]

        def pad_text(text, width):
            """한글 포함 문자열을 고정 너비로 패딩"""
            display_len = 0
            for ch in text:
                if ord(ch) > 0x7F:
                    display_len += 2
                else:
                    display_len += 1
            padding = max(0, width - display_len)
            return text + " " * padding

        # 헤더
        header = "  " + pad_text("항목", col_w[0]) + pad_text("원본 (autotyper.exe)", col_w[1]) + pad_text("HM AutoTyper", col_w[2])
        info_widget.insert("end", header + "\n", "table_header")

        # 데이터 행
        for idx, (item, original, hm) in enumerate(table_data):
            row = "  " + pad_text(item, col_w[0]) + pad_text(original, col_w[1]) + pad_text(hm, col_w[2])
            tag = "table_row_alt" if idx % 2 == 1 else "table_row"
            info_widget.insert("end", row + "\n", tag)

        info_widget.insert("end", "\n", "desc")

        # 저작권
        info_widget.tag_configure("copyright", font=("맑은 고딕", 10, "bold"),
                                  foreground="#e74c3c", justify="center",
                                  spacing1=16, spacing3=4)
        info_widget.insert("end", "\u2500" * 60 + "\n", "divider")
        info_widget.insert("end", "\u00a9 2026 haemin. All rights reserved.\n", "copyright")
        info_widget.insert("end", "본 소프트웨어의 무단 배포, 판매, 수정 후 재배포를 금지합니다.\n", "copyright")
        info_widget.insert("end", "문의: hm.autotyper@gmail.com\n", "copyright")

        info_widget.config(state="disabled")  # 읽기 전용

        # 닫기 버튼
        btn_frame = tk.Frame(popup)
        btn_frame.pack(fill="x", padx=40, pady=(8, 24))
        tk.Button(btn_frame, text="닫기", width=16, height=2,
                  font=("맑은 고딕", 12, "bold"), bg="#3498db", fg="white",
                  command=popup.destroy).pack()

    def _on_closing(self):
        if self._engine:
            self._engine.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


# ═══════════════════════════════════════════════════════════════
# 엔트리포인트
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = HmAutotyperApp()
    app.run()
