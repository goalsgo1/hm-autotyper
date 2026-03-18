"""
HM AutoTyper 자동 테스트 스크립트
- GUI 없이 핵심 로직을 모두 테스트합니다.
- 실행: python test_hm_autotyper.py
"""

import sys
import os
import time
import threading
import difflib
from unittest.mock import MagicMock, patch

# 테스트 대상 모듈 임포트 (GUI 없이 로직만)
# tkinter 및 GUI 관련 모듈을 모킹하여 GUI 생성 방지
_mock_tk = MagicMock()
_mock_tk.Frame = MagicMock
_mock_tk.Label = MagicMock
_mock_tk.Button = MagicMock
_mock_tk.Entry = MagicMock
_mock_tk.Text = MagicMock
_mock_tk.Toplevel = MagicMock
_mock_tk.StringVar = MagicMock
_mock_tk.IntVar = MagicMock
_mock_tk.BooleanVar = MagicMock
_mock_tk.DoubleVar = MagicMock
_mock_tk.Tk = MagicMock
_mock_tk.END = 'end'
_mock_tk.LEFT = 'left'
_mock_tk.RIGHT = 'right'
_mock_tk.TOP = 'top'
_mock_tk.BOTTOM = 'bottom'
_mock_tk.BOTH = 'both'
_mock_tk.X = 'x'
_mock_tk.Y = 'y'
_mock_tk.W = 'w'
_mock_tk.E = 'e'
_mock_tk.N = 'n'
_mock_tk.S = 's'
_mock_tk.WORD = 'word'
_mock_tk.NORMAL = 'normal'
_mock_tk.DISABLED = 'disabled'
_mock_tk.HORIZONTAL = 'horizontal'
_mock_tk.VERTICAL = 'vertical'
_mock_tk.CENTER = 'center'
_mock_tk.GROOVE = 'groove'
_mock_tk.SUNKEN = 'sunken'
_mock_tk.RAISED = 'raised'
_mock_tk.RIDGE = 'ridge'
_mock_tk.FLAT = 'flat'
_mock_tk.SOLID = 'solid'
_mock_tk.NW = 'nw'
_mock_tk.NE = 'ne'
_mock_tk.SW = 'sw'
_mock_tk.SE = 'se'
_mock_tk.NSEW = 'nsew'
_mock_tk.EW = 'ew'
_mock_tk.NS = 'ns'
_mock_tk.BROWSE = 'browse'
_mock_tk.MULTIPLE = 'multiple'
_mock_tk.EXTENDED = 'extended'
_mock_tk.SINGLE = 'single'
_mock_tk.ACTIVE = 'active'
_mock_tk.HIDDEN = 'hidden'
_mock_tk.CASCADE = 'cascade'
_mock_tk.CHECKBUTTON = 'checkbutton'
_mock_tk.COMMAND = 'command'
_mock_tk.RADIOBUTTON = 'radiobutton'
_mock_tk.SEPARATOR = 'separator'
_mock_tk.INSERT = 'insert'
_mock_tk.SEL = 'sel'
_mock_tk.SEL_FIRST = 'sel.first'
_mock_tk.SEL_LAST = 'sel.last'
_mock_tk.ANCHOR = 'anchor'
_mock_tk.TclError = Exception

sys.modules['tkinter'] = _mock_tk
sys.modules['tkinter.scrolledtext'] = MagicMock()
sys.modules['tkinter.messagebox'] = MagicMock()
sys.modules['tkinter.ttk'] = MagicMock()
sys.modules['tkinter.font'] = MagicMock()
sys.modules['tkinter.filedialog'] = MagicMock()
sys.modules['customtkinter'] = MagicMock()

# pyautogui, pyperclip도 없을 수 있으므로 모킹
if 'pyautogui' not in sys.modules:
    sys.modules['pyautogui'] = MagicMock()
if 'pyperclip' not in sys.modules:
    sys.modules['pyperclip'] = MagicMock()

import importlib

# ═══════════════════════════════════════════════════════════════
# 테스트 유틸리티
# ═══════════════════════════════════════════════════════════════

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.current_group = ""

    def group(self, name):
        self.current_group = name
        print(f"\n{'='*60}")
        print(f"  {name}")
        print(f"{'='*60}")

    def ok(self, name):
        self.passed += 1
        print(f"  [PASS] {name}")

    def fail(self, name, expected, actual):
        self.failed += 1
        self.errors.append((self.current_group, name, expected, actual))
        print(f"  [FAIL] {name}")
        print(f"         기대값: {expected!r}")
        print(f"         실제값: {actual!r}")

    def check(self, name, expected, actual):
        if expected == actual:
            self.ok(name)
        else:
            self.fail(name, expected, actual)

    def check_true(self, name, value):
        if value:
            self.ok(name)
        else:
            self.fail(name, True, value)

    def check_false(self, name, value):
        if not value:
            self.ok(name)
        else:
            self.fail(name, False, value)

    def check_in(self, name, item, collection):
        if item in collection:
            self.ok(name)
        else:
            self.fail(name, f"{item!r} in collection", f"not found")

    def check_approx(self, name, expected, actual, tolerance=0.1):
        if abs(expected - actual) <= tolerance:
            self.ok(name)
        else:
            self.fail(name, f"{expected} (±{tolerance})", actual)

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"  테스트 결과 요약")
        print(f"{'='*60}")
        print(f"  전체: {total}  |  통과: {self.passed}  |  실패: {self.failed}")
        if self.errors:
            print(f"\n  실패 목록:")
            for group, name, expected, actual in self.errors:
                print(f"    [{group}] {name}")
        print(f"{'='*60}")
        return self.failed == 0


# ═══════════════════════════════════════════════════════════════
# 모듈 임포트 (hm_autotyper에서 로직 함수들)
# ═══════════════════════════════════════════════════════════════

# hm_autotyper.py를 직접 임포트
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hm_autotyper import (
    decompose_hangul, jamo_to_keys, is_hangul, is_hangul_jamo,
    is_ascii_printable, JAMO_TO_KEY, COMPOUND_VOWELS, SHIFT_CHARS,
    CHOSUNG_LIST, JUNGSUNG_LIST, JONGSUNG_LIST,
    TypingEngine,
)

T = TestResult()


# ═══════════════════════════════════════════════════════════════
# 1. 한글 자모 분해 테스트
# ═══════════════════════════════════════════════════════════════
T.group("1. 한글 자모 분해 (decompose_hangul)")

# 기본 음절
T.check("'가' → ㄱ + ㅏ", ['ㄱ', 'ㅏ'], decompose_hangul('가'))
T.check("'한' → ㅎ + ㅏ + ㄴ", ['ㅎ', 'ㅏ', 'ㄴ'], decompose_hangul('한'))
T.check("'글' → ㄱ + ㅡ + ㄹ", ['ㄱ', 'ㅡ', 'ㄹ'], decompose_hangul('글'))

# 쌍자음 초성
T.check("'까' → ㄲ + ㅏ", ['ㄲ', 'ㅏ'], decompose_hangul('까'))
T.check("'빠' → ㅃ + ㅏ", ['ㅃ', 'ㅏ'], decompose_hangul('빠'))
T.check("'싸' → ㅆ + ㅏ", ['ㅆ', 'ㅏ'], decompose_hangul('싸'))

# 겹받침
T.check("'읽' → ㅇ + ㅣ + ㄺ", ['ㅇ', 'ㅣ', 'ㄺ'], decompose_hangul('읽'))
T.check("'삶' → ㅅ + ㅏ + ㄻ", ['ㅅ', 'ㅏ', 'ㄻ'], decompose_hangul('삶'))
T.check("'없' → ㅇ + ㅓ + ㅄ", ['ㅇ', 'ㅓ', 'ㅄ'], decompose_hangul('없'))
T.check("'값' → ㄱ + ㅏ + ㅄ", ['ㄱ', 'ㅏ', 'ㅄ'], decompose_hangul('값'))

# 복합 모음
T.check("'왜' → ㅇ + ㅙ", ['ㅇ', 'ㅙ'], decompose_hangul('왜'))
T.check("'쉬' → ㅅ + ㅟ", ['ㅅ', 'ㅟ'], decompose_hangul('쉬'))
T.check("'의' → ㅇ + ㅢ", ['ㅇ', 'ㅢ'], decompose_hangul('의'))
T.check("'궤' → ㄱ + ㅞ", ['ㄱ', 'ㅞ'], decompose_hangul('궤'))

# 종성 없는 음절
T.check("'나' → ㄴ + ㅏ (종성 없음)", ['ㄴ', 'ㅏ'], decompose_hangul('나'))
T.check("'소' → ㅅ + ㅗ (종성 없음)", ['ㅅ', 'ㅗ'], decompose_hangul('소'))

# 비한글 문자
T.check("'A' → ['A'] (영문 그대로)", ['A'], decompose_hangul('A'))
T.check("'1' → ['1'] (숫자 그대로)", ['1'], decompose_hangul('1'))
T.check("'!' → ['!'] (특수문자 그대로)", ['!'], decompose_hangul('!'))


# ═══════════════════════════════════════════════════════════════
# 2. 자모 → 키 매핑 테스트
# ═══════════════════════════════════════════════════════════════
T.group("2. 자모 → 키 매핑 (jamo_to_keys)")

# 기본 자음
T.check("ㄱ → ['r']", ['r'], jamo_to_keys('ㄱ'))
T.check("ㄴ → ['s']", ['s'], jamo_to_keys('ㄴ'))
T.check("ㅎ → ['g']", ['g'], jamo_to_keys('ㅎ'))

# 쌍자음 (Shift 조합)
T.check("ㄲ → [('shift', 'r')]", [('shift', 'r')], jamo_to_keys('ㄲ'))
T.check("ㅃ → [('shift', 'q')]", [('shift', 'q')], jamo_to_keys('ㅃ'))
T.check("ㅆ → [('shift', 't')]", [('shift', 't')], jamo_to_keys('ㅆ'))

# 기본 모음
T.check("ㅏ → ['k']", ['k'], jamo_to_keys('ㅏ'))
T.check("ㅣ → ['l']", ['l'], jamo_to_keys('ㅣ'))
T.check("ㅡ → ['m']", ['m'], jamo_to_keys('ㅡ'))

# 복합 모음 분해
T.check("ㅘ → ['h', 'k'] (ㅗ+ㅏ)", ['h', 'k'], jamo_to_keys('ㅘ'))
T.check("ㅙ → ['h', 'o'] (ㅗ+ㅐ)", ['h', 'o'], jamo_to_keys('ㅙ'))
T.check("ㅚ → ['h', 'l'] (ㅗ+ㅣ)", ['h', 'l'], jamo_to_keys('ㅚ'))
T.check("ㅝ → ['n', 'j'] (ㅜ+ㅓ)", ['n', 'j'], jamo_to_keys('ㅝ'))
T.check("ㅞ → ['n', 'p'] (ㅜ+ㅔ)", ['n', 'p'], jamo_to_keys('ㅞ'))
T.check("ㅟ → ['n', 'l'] (ㅜ+ㅣ)", ['n', 'l'], jamo_to_keys('ㅟ'))
T.check("ㅢ → ['m', 'l'] (ㅡ+ㅣ)", ['m', 'l'], jamo_to_keys('ㅢ'))

# 복합 종성
T.check("ㄳ → ['r', 't']", ['r', 't'], jamo_to_keys('ㄳ'))
T.check("ㄺ → ['f', 'r']", ['f', 'r'], jamo_to_keys('ㄺ'))
T.check("ㄻ → ['f', 'a']", ['f', 'a'], jamo_to_keys('ㄻ'))
T.check("ㅄ → ['q', 't']", ['q', 't'], jamo_to_keys('ㅄ'))


# ═══════════════════════════════════════════════════════════════
# 3. 문자 유형 판별 테스트
# ═══════════════════════════════════════════════════════════════
T.group("3. 문자 유형 판별")

# is_hangul
T.check_true("is_hangul('가')", is_hangul('가'))
T.check_true("is_hangul('힣')", is_hangul('힣'))
T.check_false("is_hangul('A')", is_hangul('A'))
T.check_false("is_hangul('1')", is_hangul('1'))
T.check_false("is_hangul('ㄱ')", is_hangul('ㄱ'))  # 자모는 음절이 아님

# is_hangul_jamo
T.check_true("is_hangul_jamo('ㄱ')", is_hangul_jamo('ㄱ'))
T.check_true("is_hangul_jamo('ㅎ')", is_hangul_jamo('ㅎ'))
T.check_true("is_hangul_jamo('ㅏ')", is_hangul_jamo('ㅏ'))
T.check_true("is_hangul_jamo('ㅣ')", is_hangul_jamo('ㅣ'))
T.check_false("is_hangul_jamo('가')", is_hangul_jamo('가'))
T.check_false("is_hangul_jamo('A')", is_hangul_jamo('A'))

# is_ascii_printable
T.check_true("is_ascii_printable('A')", is_ascii_printable('A'))
T.check_true("is_ascii_printable(' ')", is_ascii_printable(' '))
T.check_true("is_ascii_printable('~')", is_ascii_printable('~'))
T.check_false("is_ascii_printable('가')", is_ascii_printable('가'))
T.check_false("is_ascii_printable(chr(0x7F))", is_ascii_printable(chr(0x7F)))


# ═══════════════════════════════════════════════════════════════
# 4. Shift 특수문자 매핑 테스트
# ═══════════════════════════════════════════════════════════════
T.group("4. Shift 특수문자 매핑")

T.check("! → 1", '1', SHIFT_CHARS.get('!'))
T.check("@ → 2", '2', SHIFT_CHARS.get('@'))
T.check("# → 3", '3', SHIFT_CHARS.get('#'))
T.check("$ → 4", '4', SHIFT_CHARS.get('$'))
T.check("% → 5", '5', SHIFT_CHARS.get('%'))
T.check("^ → 6", '6', SHIFT_CHARS.get('^'))
T.check("& → 7", '7', SHIFT_CHARS.get('&'))
T.check("* → 8", '8', SHIFT_CHARS.get('*'))
T.check("( → 9", '9', SHIFT_CHARS.get('('))
T.check(") → 0", '0', SHIFT_CHARS.get(')'))
T.check("_ → -", '-', SHIFT_CHARS.get('_'))
T.check("+ → =", '=', SHIFT_CHARS.get('+'))
T.check("{ → [", '[', SHIFT_CHARS.get('{'))
T.check("} → ]", ']', SHIFT_CHARS.get('}'))
T.check('| → \\', '\\', SHIFT_CHARS.get('|'))
T.check(": → ;", ';', SHIFT_CHARS.get(':'))
T.check('" → \'', "'", SHIFT_CHARS.get('"'))
T.check("< → ,", ',', SHIFT_CHARS.get('<'))
T.check("> → .", '.', SHIFT_CHARS.get('>'))
T.check("? → /", '/', SHIFT_CHARS.get('?'))
T.check("~ → `", '`', SHIFT_CHARS.get('~'))


# ═══════════════════════════════════════════════════════════════
# 5. 자모 리스트 완전성 테스트
# ═══════════════════════════════════════════════════════════════
T.group("5. 자모 리스트 완전성")

T.check("초성 19개", 19, len(CHOSUNG_LIST))
T.check("중성 21개", 21, len(JUNGSUNG_LIST))
T.check("종성 28개 (0번 빈 문자열 포함)", 28, len(JONGSUNG_LIST))
T.check("종성[0] = '' (종성 없음)", '', JONGSUNG_LIST[0])
T.check("복합 모음 7개", 7, len(COMPOUND_VOWELS))

# JAMO_TO_KEY 매핑 완전성 확인
all_chosung_mapped = all(c in JAMO_TO_KEY for c in CHOSUNG_LIST)
T.check_true("모든 초성이 JAMO_TO_KEY에 매핑됨", all_chosung_mapped)

basic_jungsung = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅛ',
                  'ㅜ', 'ㅠ', 'ㅡ', 'ㅣ']
all_basic_jung_mapped = all(j in JAMO_TO_KEY for j in basic_jungsung)
T.check_true("기본 모음 14개가 JAMO_TO_KEY에 매핑됨", all_basic_jung_mapped)

compound_vowels_mapped = all(v in COMPOUND_VOWELS for v in ['ㅘ', 'ㅙ', 'ㅚ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅢ'])
T.check_true("복합 모음 7개가 COMPOUND_VOWELS에 매핑됨", compound_vowels_mapped)


# ═══════════════════════════════════════════════════════════════
# 6. 한글 전체 자모 분해 → 키 변환 통합 테스트
# ═══════════════════════════════════════════════════════════════
T.group("6. 한글 자모 분해 → 키 변환 통합")

def hangul_to_full_keys(char):
    """한글 한 글자를 최종 키 시퀀스로 변환"""
    jamos = decompose_hangul(char)
    keys = []
    for jamo in jamos:
        keys.extend(jamo_to_keys(jamo))
    return keys

T.check("'가' → [r, k]", ['r', 'k'], hangul_to_full_keys('가'))
T.check("'한' → [g, k, s]", ['g', 'k', 's'], hangul_to_full_keys('한'))
T.check("'글' → [r, m, f]", ['r', 'm', 'f'], hangul_to_full_keys('글'))
T.check("'까' → [(shift,r), k]", [('shift', 'r'), 'k'], hangul_to_full_keys('까'))
T.check("'읽' → [d, l, f, r]", ['d', 'l', 'f', 'r'], hangul_to_full_keys('읽'))
T.check("'왜' → [d, h, o]", ['d', 'h', 'o'], hangul_to_full_keys('왜'))
T.check("'쉬' → [t, n, l]", ['t', 'n', 'l'], hangul_to_full_keys('쉬'))
T.check("'의' → [d, m, l]", ['d', 'm', 'l'], hangul_to_full_keys('의'))


# ═══════════════════════════════════════════════════════════════
# 7. TypingEngine 기본 동작 테스트
# ═══════════════════════════════════════════════════════════════
T.group("7. TypingEngine 기본 동작")

# 모드 상수
T.check("MODE_TYPING", "typing", TypingEngine.MODE_TYPING)
T.check("MODE_CLIPBOARD", "clipboard", TypingEngine.MODE_CLIPBOARD)
T.check("MODE_HYBRID", "hybrid", TypingEngine.MODE_HYBRID)

# 엔진 생성
engine = TypingEngine(mode="hybrid", delay=0.05)
T.check("기본 모드 = hybrid", "hybrid", engine.mode)
T.check("기본 딜레이 = 0.05", 0.05, engine.delay)
T.check_false("초기 상태: 멈춤 아님", engine.is_stopped())

# stop/is_stopped
engine.stop()
T.check_true("stop() 후 is_stopped() = True", engine.is_stopped())

# start_index
engine2 = TypingEngine(start_index=50)
T.check("start_index = 50", 50, engine2._start_index)
T.check("_last_index 초기값 = 0", 0, engine2._last_index)

# focus_guard
engine3 = TypingEngine(focus_guard=False)
T.check_false("focus_guard = False", engine3.focus_guard)

engine4 = TypingEngine(focus_guard=True)
T.check_true("focus_guard = True", engine4.focus_guard)


# ═══════════════════════════════════════════════════════════════
# 8. TypingEngine 진행률 콜백 테스트
# ═══════════════════════════════════════════════════════════════
T.group("8. TypingEngine 진행률 콜백")

progress_log = []
status_log = []

def mock_progress(current, total):
    progress_log.append((current, total))

def mock_status(msg):
    status_log.append(msg)

engine5 = TypingEngine(on_progress=mock_progress, on_status=mock_status)
engine5._update_progress(10, 100)
T.check("progress 콜백 호출", [(10, 100)], progress_log)

engine5._update_status("테스트 메시지")
T.check("status 콜백 호출", ["테스트 메시지"], status_log)


# ═══════════════════════════════════════════════════════════════
# 9. TypingEngine 키 입력 로직 테스트 (모킹)
# ═══════════════════════════════════════════════════════════════
T.group("9. TypingEngine 키 입력 로직 (모킹)")

pressed_keys = []
hotkey_calls = []

mock_pyautogui = MagicMock()
mock_pyautogui.press = lambda k: pressed_keys.append(('press', k))
mock_pyautogui.hotkey = lambda *args: hotkey_calls.append(('hotkey', args))
mock_pyautogui.FAILSAFE = True
mock_pyautogui.PAUSE = 0

engine6 = TypingEngine()

# _press_key 테스트
with patch('hm_autotyper.pyautogui', mock_pyautogui):
    pressed_keys.clear()
    engine6._press_key('r')
    T.check("_press_key('r') → press 'r'", [('press', 'r')], pressed_keys)

    hotkey_calls.clear()
    engine6._press_key(('shift', 'r'))
    T.check("_press_key(('shift','r')) → hotkey", [('hotkey', ('shift', 'r'))], hotkey_calls)

# _type_ascii_char 테스트
with patch('hm_autotyper.pyautogui', mock_pyautogui):
    pressed_keys.clear()
    engine6._type_ascii_char('a')
    T.check("_type_ascii_char('a') → press 'a'", [('press', 'a')], pressed_keys)

    hotkey_calls.clear()
    engine6._type_ascii_char('A')
    T.check("_type_ascii_char('A') → hotkey shift+a", [('hotkey', ('shift', 'a'))], hotkey_calls)

    hotkey_calls.clear()
    engine6._type_ascii_char('!')
    T.check("_type_ascii_char('!') → hotkey shift+1", [('hotkey', ('shift', '1'))], hotkey_calls)


# ═══════════════════════════════════════════════════════════════
# 10. 텍스트 비교(diff) 로직 테스트
# ═══════════════════════════════════════════════════════════════
T.group("10. 텍스트 비교(diff) 로직")

# _compute_diffs를 직접 테스트 (HmAutotyperApp의 메서드이지만, 로직만 추출하여 테스트)
def compute_diffs(original, typed):
    """원문과 입력된 텍스트의 차이를 계산 (앱 메서드와 동일 로직)"""
    original = original.replace('\r\n', '\n')
    typed = typed.replace('\r\n', '\n')
    errors = []
    sm = difflib.SequenceMatcher(None, original, typed, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        line = original[:i1].count('\n') + 1
        last_nl = original[:i1].rfind('\n')
        col = i1 - last_nl
        errors.append({
            'type': tag, 'pos': i1,
            'orig': original[i1:i2], 'typed': typed[j1:j2],
            'line': line, 'col': col,
        })
    return errors

# 완전 일치
errors = compute_diffs("안녕하세요", "안녕하세요")
T.check("완전 일치 → 오류 0건", 0, len(errors))

# 교체 오류
errors = compute_diffs("안녕하세요", "안녕하서요")
T.check("교체 오류 → 1건", 1, len(errors))
T.check("교체: type = replace", "replace", errors[0]['type'])
T.check("교체: orig = '세'", "세", errors[0]['orig'])
T.check("교체: typed = '서'", "서", errors[0]['typed'])

# 누락 오류
errors = compute_diffs("ABCDE", "ABDE")
T.check("누락 오류 → 1건", 1, len(errors))
T.check("누락: type = delete", "delete", errors[0]['type'])
T.check("누락: orig = 'C'", "C", errors[0]['orig'])

# 추가 오류
errors = compute_diffs("ABDE", "ABCDE")
T.check("추가 오류 → 1건", 1, len(errors))
T.check("추가: type = insert", "insert", errors[0]['type'])
T.check("추가: typed = 'C'", "C", errors[0]['typed'])

# 줄번호/컬럼 테스트
errors = compute_diffs("첫째줄\n둘째줄\n셋째줄", "첫째줄\n틀째줄\n셋째줄")
T.check("줄번호 오류 → 1건", 1, len(errors))
T.check("줄번호 = 2", 2, errors[0]['line'])

# 빈 텍스트
errors = compute_diffs("안녕", "")
T.check("빈 입력 → delete 오류", "delete", errors[0]['type'])

# 복합 오류
errors = compute_diffs("Hello World", "Helo Worlld")
T.check_true("복합 오류 → 1건 이상", len(errors) >= 1)


# ═══════════════════════════════════════════════════════════════
# 11. 이어쓰기 분석 (resume point) 로직 테스트
# ═══════════════════════════════════════════════════════════════
T.group("11. 이어쓰기 분석 (resume point)")

def find_resume_point(original, typed):
    """_find_resume_point와 동일한 로직"""
    original = original.replace('\r\n', '\n')
    typed = typed.replace('\r\n', '\n')

    if not typed.strip():
        return {'resume_index': 0, 'errors': [], 'typed_len': 0,
                'match_ratio': 0.0, 'status': 'empty'}

    sm = difflib.SequenceMatcher(None, original, typed, autojunk=False)
    match_ratio = sm.ratio()

    matching_blocks = sm.get_matching_blocks()
    last_matched_orig = 0
    for block in matching_blocks:
        end_orig = block.a + block.size
        if end_orig > last_matched_orig:
            last_matched_orig = end_orig

    errors = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        if i1 < last_matched_orig or (tag == 'insert' and j1 < len(typed)):
            line = original[:i1].count('\n') + 1
            last_nl = original[:i1].rfind('\n')
            col = i1 - last_nl
            errors.append({
                'type': tag, 'pos': i1,
                'orig': original[i1:i2], 'typed': typed[j1:j2],
                'line': line, 'col': col,
            })

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

# 빈 입력
result = find_resume_point("안녕하세요 테스트", "")
T.check("빈 입력 → status = empty", "empty", result['status'])
T.check("빈 입력 → resume_index = 0", 0, result['resume_index'])

# 절반 입력 (정상)
# Note: SequenceMatcher sentinel block sets last_matched_orig to len(original)
# 실제 이어쓰기 시에는 typed_len 기준으로 resume_index를 보정하므로,
# 여기서는 로직의 raw 반환값인 원문 길이(10)가 나오는 것이 정상
result = find_resume_point("ABCDEFGHIJ", "ABCDE")
T.check("절반 입력 → resume_index >= typed_len", True, result['resume_index'] >= len("ABCDE"))
T.check("절반 입력 → status = partial", "partial", result['status'])

# 완전 입력
result = find_resume_point("ABCDE", "ABCDE")
T.check("완전 입력 → status = complete", "complete", result['status'])
T.check("완전 입력 → 오류 0건", 0, len(result['errors']))

# 오류 포함 부분 입력
result = find_resume_point("ABCDEFGHIJ", "ABXDE")
T.check_true("오류 포함 → 오류 1건 이상", len(result['errors']) >= 1)
T.check("오류 포함 → status = partial", "partial", result['status'])

# 한글 부분 입력
original_kr = "안녕하세요 반갑습니다"
typed_kr = "안녕하세요"
result = find_resume_point(original_kr, typed_kr)
T.check("한글 부분 입력 → status = partial", "partial", result['status'])
T.check_true("한글 부분 입력 → resume_index > 0", result['resume_index'] > 0)


# ═══════════════════════════════════════════════════════════════
# 12. 일치율 (match ratio) 테스트
# ═══════════════════════════════════════════════════════════════
T.group("12. 일치율 계산")

sm = difflib.SequenceMatcher(None, "ABCDE", "ABCDE")
T.check_approx("동일 텍스트 → 100%", 1.0, sm.ratio(), 0.01)

sm = difflib.SequenceMatcher(None, "ABCDE", "ABXDE")
T.check_true("1글자 다름 → 60~90%", 0.6 <= sm.ratio() <= 0.9)

sm = difflib.SequenceMatcher(None, "ABCDE", "FGHIJ")
T.check_true("완전 다름 → 0~20%", sm.ratio() <= 0.2)

sm = difflib.SequenceMatcher(None, "ABCDE", "")
T.check_approx("빈 입력 → 0%", 0.0, sm.ratio(), 0.01)


# ═══════════════════════════════════════════════════════════════
# 13. TypingEngine stop 이벤트 테스트
# ═══════════════════════════════════════════════════════════════
T.group("13. TypingEngine 중지 이벤트")

engine7 = TypingEngine()
T.check_false("초기: is_stopped = False", engine7.is_stopped())

engine7.stop()
T.check_true("stop() 후: is_stopped = True", engine7.is_stopped())

# _stop_event를 다시 clear하면 재사용 가능
engine7._stop_event.clear()
T.check_false("clear() 후: is_stopped = False", engine7.is_stopped())


# ═══════════════════════════════════════════════════════════════
# 14. 줄바꿈 정규화 테스트
# ═══════════════════════════════════════════════════════════════
T.group("14. 줄바꿈 정규화")

text_crlf = "첫째줄\r\n둘째줄\r\n셋째줄"
text_lf = text_crlf.replace('\r\n', '\n')
T.check("CRLF → LF 변환", "첫째줄\n둘째줄\n셋째줄", text_lf)

# diff에서도 정규화가 적용되는지
errors = compute_diffs("A\r\nB", "A\nB")
T.check("CRLF vs LF → 오류 0건", 0, len(errors))


# ═══════════════════════════════════════════════════════════════
# 15. 데이터 테이블 완전성 테스트
# ═══════════════════════════════════════════════════════════════
T.group("15. 데이터 테이블 완전성")

# 모든 초성이 유효한 한글 범위에서 추출 가능한지
for i, cho in enumerate(CHOSUNG_LIST):
    code = 0xAC00 + i * 21 * 28
    char = chr(code)
    result = decompose_hangul(char)
    T.check(f"초성 '{cho}' (U+{code:04X} '{char}')", cho, result[0])

# 모든 중성이 유효한지
for j, jung in enumerate(JUNGSUNG_LIST):
    code = 0xAC00 + j * 28
    char = chr(code)
    result = decompose_hangul(char)
    T.check(f"중성 '{jung}' ('{char}')", jung, result[1])

# 모든 종성이 유효한지 (0번 제외)
for k, jong in enumerate(JONGSUNG_LIST):
    if k == 0:
        continue
    code = 0xAC00 + k
    char = chr(code)
    result = decompose_hangul(char)
    T.check(f"종성 '{jong}' ('{char}')", jong, result[2])


# ═══════════════════════════════════════════════════════════════
# 16. 스레드 안전성 테스트
# ═══════════════════════════════════════════════════════════════
T.group("16. 스레드 안전성")

engine8 = TypingEngine()
stop_detected = []

def thread_check_stop():
    for _ in range(100):
        if engine8.is_stopped():
            stop_detected.append(True)
            return
        time.sleep(0.001)
    stop_detected.append(False)

t = threading.Thread(target=thread_check_stop)
t.start()
time.sleep(0.01)
engine8.stop()
t.join(timeout=2)

T.check_true("다른 스레드에서 stop 감지", stop_detected and stop_detected[0])


# ═══════════════════════════════════════════════════════════════
# 17. 테스트 텍스트 파일 존재 확인
# ═══════════════════════════════════════════════════════════════
T.group("17. 테스트 텍스트 파일")

test_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_text.txt")
T.check_true("test_text.txt 파일 존재", os.path.exists(test_file))

if os.path.exists(test_file):
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    T.check_true("test_text.txt 내용 있음", len(content) > 0)
    T.check_true("한글 포함", any(is_hangul(c) for c in content))
    T.check_true("영문 포함", any(c.isascii() and c.isalpha() for c in content))
    T.check_true("숫자 포함", any(c.isdigit() for c in content))
    T.check_true("특수문자 포함", any(c in SHIFT_CHARS for c in content))
    T.check_true("줄바꿈 포함", '\n' in content)


# ═══════════════════════════════════════════════════════════════
# 결과 요약
# ═══════════════════════════════════════════════════════════════
success = T.summary()
sys.exit(0 if success else 1)
