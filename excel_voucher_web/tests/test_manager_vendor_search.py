import ast
import re
from pathlib import Path
from types import SimpleNamespace

import pytest


MANAGER_SOURCE = (
    Path(__file__).resolve().parents[2]
    / "manager_server"
    / "전표 자동화 프로그램(담당자용)_v6.2.py"
)
AGENT_ADAPTER_SOURCE = Path(__file__).resolve().parents[1] / "app" / "agent_adapter.py"
AGENT_WORKER_SOURCE = Path(__file__).resolve().parents[1] / "agent" / "agent_worker.py"
WEB_MAIN_SOURCE = Path(__file__).resolve().parents[1] / "app" / "main.py"


def _load_nested_functions(*names: str, namespace: dict | None = None) -> dict:
    tree = ast.parse(MANAGER_SOURCE.read_text(encoding="utf-8"))
    wanted = set(names)
    found = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in wanted and node.name not in found:
            found[node.name] = node
    missing = wanted - found.keys()
    assert not missing, f"manager helper not found: {sorted(missing)}"
    module = ast.Module(body=[found[name] for name in names], type_ignores=[])
    ast.fix_missing_locations(module)
    loaded = dict(namespace or {})
    exec(compile(module, str(MANAGER_SOURCE), "exec"), loaded)
    return loaded


class _FakeRect:
    def __init__(self, left: int, top: int, right: int, bottom: int):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom

    def width(self) -> int:
        return self.right - self.left

    def height(self) -> int:
        return self.bottom - self.top


class _FakeControl:
    _next_handle = 1

    def __init__(
        self,
        text: str,
        control_type: str,
        rect: _FakeRect,
        *,
        visible: bool = True,
        enabled: bool = True,
        automation_id: str = "",
        grid_row: int | None = None,
    ):
        self._text = text
        self._rect = rect
        self._visible = visible
        self._enabled = enabled
        self._parent = None
        self._children = []
        self.element_info = SimpleNamespace(
            control_type=control_type,
            name=text,
            automation_id=automation_id,
        )
        if grid_row is not None:
            self.iface_grid_item = SimpleNamespace(CurrentRow=grid_row)
        self.handle = self._next_handle
        self.click_count = 0
        type(self)._next_handle += 1

    def add(self, child: "_FakeControl") -> "_FakeControl":
        child._parent = self
        self._children.append(child)
        return child

    def descendants(self) -> list["_FakeControl"]:
        result = []
        for child in self._children:
            result.append(child)
            result.extend(child.descendants())
        return result

    def parent(self):
        return self._parent

    def rectangle(self) -> _FakeRect:
        return self._rect

    def window_text(self) -> str:
        return self._text

    def is_visible(self) -> bool:
        return self._visible

    def is_enabled(self) -> bool:
        return self._enabled

    def click_input(self):
        self.click_count += 1


class _FakeLogger:
    def debug(self, *_args, **_kwargs):
        pass

    def info(self, *_args, **_kwargs):
        pass

    def warning(self, *_args, **_kwargs):
        pass

    def error(self, *_args, **_kwargs):
        pass


def test_finance_first_vendor_uses_exact_f9_keyboard_sequence():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")

    helper_start = source.index("def _seed_vendor_by_number_f9")
    helper_end = source.index("def _input_finance_vendor_code_xy", helper_start)
    helper = source[helper_start:helper_end]
    expected_order = [
        "_click_form_xy",
        "pyautogui.press('f9')",
        "_replace_vendor_ds_search_text",
        "pyautogui.press('tab', presses=4",
        "pyautogui.press('down', presses=5",
        "pyautogui.press('up', presses=2",
        "pyautogui.press('tab', presses=3",
        "pyautogui.press('enter', presses=2",
    ]
    positions = [helper.index(token) for token in expected_order]

    assert positions == sorted(positions)
    assert "doubleClick" not in helper
    assert "_double_click" not in helper
    assert "_input_vendor_by_popup_keyboard" not in helper
    assert helper.count("pyautogui.press('f9')") == 1
    assert "if skip_visible_row_scan:" in helper
    assert "if not skip_visible_row_scan:" in helper
    assert helper.index("if skip_visible_row_scan:") < helper.index(
        "_wait_vendor_ds_foreground"
    )
    assert "_wait_first_vendor_value_committed(" not in helper
    assert "_management_value_visual_ink(" not in helper
    assert 'finance_vendor_entry_state = {"f9_seeded": False}' in source
    assert 'if account_key == "미지급금(원화)":' in source
    # 사용자 확정: 1행 전용 팝업 시퀀스는 더 이상 호출하지 않는다.
    # 1행부터 마지막 미지급금 행까지 동일한 입력→F9→Enter 흐름만 사용한다.
    assert source.count("_seed_vendor_by_number_f9") == 1
    assert 'if not finance_vendor_entry_state["f9_seeded"]:' not in source
    assert 'finance_vendor_entry_state["f9_seeded"] = True' in source
    assert "관리항목값 셀 키보드 입력 후 Enter 완료" in source
    assert "거래처번호 팝업 입력 실패, 직접 입력 fallback" in source


def test_fast_main_rect_uses_cached_geometry_before_uia_rectangle_call():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    helper_start = source.index("def _main_rect():")
    helper_end = source.index("def _click_form_xy", helper_start)
    helper = source[helper_start:helper_end]

    cache_guard = "if skip_visible_row_scan and main_rect_cache is not None:"
    assert cache_guard in helper
    rectangle_call = "main_rect_cache = main_win.rectangle()"
    assert helper.index(cache_guard) < helper.index(rectangle_call)
    assert helper.index("return main_rect_cache", helper.index(cache_guard)) < helper.index(
        rectangle_call
    )


def test_recovery_window_enumeration_filters_visibility_after_supported_call():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    helper_start = source.index("def _fast_recovery_main_window")
    helper_end = source.index("main_win = None", helper_start)
    helper = source[helper_start:helper_end]

    assert "windows = self.app.windows()" in helper
    assert "win.is_visible()" in helper
    assert ".windows(visible=True)" not in source


def test_vendor_popup_detects_internal_erp_page_and_filters_visible_controls():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")

    assert "def _find_internal_vendor_popup():" in source
    assert "main_win.descendants()" in source
    assert '"internal-uia"' in source
    assert '"internal-signature"' in source
    assert "def _visible_vendor_popup_controls" in source
    assert '_visible_vendor_popup_controls(popup, "ComboBox", top_band=True)' in source
    assert '_visible_vendor_popup_controls(popup, "Edit", top_band=True)' in source
    assert "not ctrl.is_visible() or not ctrl.is_enabled()" in source

    candidate_start = source.index("if candidates:", source.index("def _find_internal_vendor_popup():"))
    candidate_end = source.index("# 거래처ds는 ERP MDI 내부 화면", candidate_start)
    candidate_branch = source[candidate_start:candidate_end]
    assert 'candidate_popup = _vendor_popup_context(root, popup_rect, "internal-uia")' in candidate_branch
    assert 'candidate_popup,\n                            "ComboBox",' in candidate_branch
    assert 'candidate_popup,\n                            "Edit",' in candidate_branch
    assert "if candidate_combos and candidate_edits:" in candidate_branch
    assert candidate_branch.index("candidate_combos =") < candidate_branch.index("return candidate_popup")
    assert candidate_branch.index("candidate_edits =") < candidate_branch.index("return candidate_popup")


def test_generic_vendor_result_requires_double_click_without_unsafe_enter_fallback():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")

    helper_start = source.index("def _select_first_vendor_popup_result")
    helper_end = source.index("def _input_vendor_by_popup_keyboard", helper_start)
    helper = source[helper_start:helper_end]

    assert "_vendor_double_click_abs" in helper
    assert "vendor_popup_result_close_wait" in helper
    assert "if not allow_enter_fallback:" in helper
    assert helper.index("if not allow_enter_fallback:") < helper.index("pyautogui.press('enter')")
    assert "거래처 검색 첫 행 더블클릭 후 화면이 닫히지 않아 중단" in helper

def test_vendor_search_button_prefers_visible_uia_button_before_coordinate_fallback():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")

    helper_start = source.index("def _click_vendor_popup_search_button")
    helper_end = source.index("def _wait_vendor_popup_closed", helper_start)
    helper = source[helper_start:helper_end]

    assert '_visible_vendor_popup_controls(popup, "Button", top_band=True)' in helper
    assert "_direct_vendor_popup_text(button)" in helper
    assert "button.click_input()" in helper
    assert helper.index("button.click_input()") < helper.index("pyautogui.click(search_x, search_y)")


def test_vendor_double_click_uses_deliberate_mouse_down_up_sequence():
    events = []
    sleeps = []
    fake_pyautogui = SimpleNamespace(
        moveTo=lambda x, y: events.append(("move", x, y)),
        mouseDown=lambda button: events.append(("down", button)),
        mouseUp=lambda button: events.append(("up", button)),
    )
    loaded = _load_nested_functions(
        "_vendor_double_click_abs",
        namespace={
            "_release_modifiers": lambda *_args, **_kwargs: None,
            "pyautogui": fake_pyautogui,
            "time": SimpleNamespace(sleep=lambda seconds: sleeps.append(seconds)),
            "vendor_double_click_hold": 0.08,
            "vendor_double_click_interval": 0.18,
            "ERP_FORM_WAIT": 0.50,
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    loaded["_vendor_double_click_abs"](1118, 797, "1행 거래처 팝업 열기", wait=0.55)

    assert events == [
        ("move", 1118, 797),
        ("down", "left"),
        ("up", "left"),
        ("down", "left"),
        ("up", "left"),
    ]
    assert sleeps == [0.08, 0.18, 0.08, 0.55]


def test_internal_vendor_popup_rejects_result_grid_and_returns_mdi_root():
    main_rect = _FakeRect(0, 0, 1600, 900)
    main = _FakeControl("K-System", "Window", main_rect)
    shared_rect = _FakeRect(20, 60, 1580, 880)
    mdi = main.add(_FakeControl("", "Pane", shared_rect))
    mdi.add(_FakeControl("업체명", "ComboBox", _FakeRect(50, 95, 240, 125)))
    mdi.add(_FakeControl("", "Edit", _FakeRect(260, 95, 900, 125)))
    # Legacy UIA can expose a result-grid wrapper with the same bounds as its
    # MDI page. The grid must not suppress the distinct page candidate.
    result_grid = mdi.add(_FakeControl("", "DataGrid", shared_rect))
    result_grid.add(_FakeControl("거래처코드", "Header", _FakeRect(50, 190, 220, 220)))
    result_grid.add(_FakeControl("거래처명", "Header", _FakeRect(220, 190, 500, 220)))
    result_grid.add(_FakeControl("사업자번호", "Header", _FakeRect(500, 190, 700, 220)))

    loaded = _load_nested_functions(
        "_vendor_popup_context",
        "_vendor_popup_root",
        "_vendor_popup_rect",
        "_visible_vendor_popup_controls",
        "_direct_vendor_popup_text",
        "_vendor_control_identity",
        "_find_internal_vendor_popup",
        namespace={
            "main_win": main,
            "_main_rect": lambda: main_rect,
            "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")).lower(),
            "UiaRect": _FakeRect,
        },
    )

    popup = loaded["_find_internal_vendor_popup"]()

    assert popup["source"] == "internal-uia"
    assert popup["root"] is mdi
    assert popup["root"] is not result_grid


def test_same_handle_vendor_title_is_detected_as_internal_mdi_popup():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    helper_start = source.index("def _find_vendor_popup")
    helper_end = source.index("def _paste_text_fast", helper_start)
    helper = source[helper_start:helper_end]
    same_handle_return = helper.index("if same_handle_vendor_win is not None:")
    internal_scan = helper.index("popup = _find_internal_vendor_popup()")

    assert same_handle_return < internal_scan
    assert helper.index('"internal-title"', same_handle_return) < internal_scan

    main_rect = _FakeRect(0, 0, 1600, 900)
    main = _FakeControl("분개전표입력 - K-System", "Window", main_rect)
    main_wrapper = _FakeControl("거래처DS - K-System", "Window", main_rect)
    main_wrapper.handle = main.handle
    descendant_calls = []
    main.descendants = lambda: descendant_calls.append("main.descendants") or []
    main_wrapper.descendants = (
        lambda: descendant_calls.append("same-handle.descendants") or []
    )

    class _FakeDesktop:
        def __init__(self, **_kwargs):
            pass

        def windows(self):
            return [main_wrapper]

    loaded = _load_nested_functions(
        "_vendor_popup_context",
        "_find_vendor_popup",
        namespace={
            "Desktop": _FakeDesktop,
            "main_win": main,
            "_main_rect": lambda: main_rect,
            "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")).lower(),
            "UiaRect": _FakeRect,
            "_find_internal_vendor_popup": (
                lambda: descendant_calls.append("internal-uia-scan") or None
            ),
            "_log_vendor_popup_detection": lambda _popup: None,
            "time": SimpleNamespace(time=lambda: 0.0, sleep=lambda _seconds: None),
        },
    )

    popup = loaded["_find_vendor_popup"](timeout=1.0)

    assert popup["source"] == "internal-title"
    assert popup["root"] is main_wrapper
    assert popup["rect"].left == 8
    assert popup["rect"].top == 52
    assert descendant_calls == []


def test_same_handle_normal_erp_title_is_not_misclassified_as_vendor_popup():
    main = _FakeControl("분개전표입력 - K-System", "Window", _FakeRect(0, 0, 1600, 900))
    main_wrapper = _FakeControl("분개전표입력 - K-System", "Window", _FakeRect(0, 0, 1600, 900))
    main_wrapper.handle = main.handle
    internal_popup = {"root": "mdi", "rect": _FakeRect(20, 60, 1580, 880), "source": "internal-uia"}

    class _FakeDesktop:
        def __init__(self, **_kwargs):
            pass

        def windows(self):
            return [main_wrapper]

    loaded = _load_nested_functions(
        "_vendor_popup_context",
        "_find_vendor_popup",
        namespace={
            "Desktop": _FakeDesktop,
            "main_win": main,
            "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")).lower(),
            "_find_internal_vendor_popup": lambda: internal_popup,
            "_log_vendor_popup_detection": lambda _popup: None,
            "time": SimpleNamespace(time=lambda: 0.0, sleep=lambda _seconds: None),
        },
    )

    assert loaded["_find_vendor_popup"](timeout=1.0) is internal_popup


def test_vendor_search_button_chooses_nearest_exact_search_action():
    popup_rect = _FakeRect(0, 0, 1000, 600)
    far_search = _FakeControl("검색", "Button", _FakeRect(100, 40, 160, 70))
    wrong_nearby = _FakeControl("검색조건", "Button", _FakeRect(900, 40, 980, 70))
    target_search = _FakeControl("검색(F5)", "Button", _FakeRect(840, 40, 920, 70))
    fallback_clicks = []

    loaded = _load_nested_functions(
        "_click_vendor_popup_search_button",
        namespace={
            "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")).lower(),
            "_vendor_popup_rect": lambda _popup: popup_rect,
            "_visible_vendor_popup_controls": lambda *_args, **_kwargs: [
                far_search,
                wrong_nearby,
                target_search,
            ],
            "_direct_vendor_popup_text": lambda control: [
                re.sub(r"\s+", "", control.window_text()).lower()
            ],
            "vendor_popup_search_wait": 0.0,
            "pyautogui": SimpleNamespace(click=lambda x, y: fallback_clicks.append((x, y))),
            "time": SimpleNamespace(sleep=lambda _seconds: None),
            "re": re,
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    assert loaded["_click_vendor_popup_search_button"]({}, "1행 거래처") is True
    assert target_search.click_count == 1
    assert far_search.click_count == 0
    assert wrong_nearby.click_count == 0
    assert fallback_clicks == []


def test_finance_first_result_does_not_press_enter_when_mdi_stays_open():
    events = []

    class _FakeClock:
        now = 0.0

        @classmethod
        def time(cls):
            return cls.now

        @classmethod
        def sleep(cls, seconds):
            cls.now += max(0.01, float(seconds))

    class _FakePyAutoGui:
        @staticmethod
        def press(key, **_kwargs):
            events.append(f"press:{key}")

    loaded = _load_nested_functions(
        "_wait_vendor_popup_closed",
        "_select_first_vendor_popup_result",
        namespace={
            "time": _FakeClock,
            "pyautogui": _FakePyAutoGui,
            "_vendor_double_click_abs": lambda *_args, **_kwargs: events.append("doubleClick"),
            "_vendor_popup_rect": lambda popup: popup["rect"],
            "_find_vendor_popup": lambda timeout=0: object(),
            "ERP_FORM_WAIT": 0.05,
            "vendor_popup_result_close_wait": 0.30,
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    result = loaded["_select_first_vendor_popup_result"](
        {"rect": _FakeRect(20, 60, 1580, 880)},
        "1행 거래처",
        allow_enter_fallback=False,
    )

    assert result is False
    assert events == ["doubleClick"]


def test_vendor_popup_close_wait_ignores_single_transient_detection_miss():
    class _FakeClock:
        now = 0.0

        @classmethod
        def time(cls):
            return cls.now

        @classmethod
        def sleep(cls, seconds):
            cls.now += max(0.01, float(seconds))

    detections = iter([None, object(), None, None])
    calls = []
    loaded = _load_nested_functions(
        "_wait_vendor_popup_closed",
        namespace={
            "time": _FakeClock,
            "_find_vendor_popup": lambda timeout=0: calls.append(timeout) or next(detections),
        },
    )

    assert loaded["_wait_vendor_popup_closed"](1.0) is True
    assert len(calls) == 4


def test_finance_fast_first_vendor_executes_exact_f9_key_order_without_uia_probe():
    events = []

    class _FakePyAutoGui:
        @staticmethod
        def press(key, presses=1, interval=0):
            events.append(("key", key, presses))

    loaded = _load_nested_functions(
        "_seed_vendor_by_number_f9",
        namespace={
            "_click_form_xy": lambda x, y, label, wait=0: events.append(("click", x, y)),
            "_release_modifiers": lambda *_args, **_kwargs: None,
            "_foreground_window_title": lambda: (101, "대승"),
            "_window_process_id": lambda hwnd: 10772 if hwnd == 101 else 0,
            "_is_vendor_ds_title": lambda title: "거래처" in title and "ds" in title.lower(),
            "_wait_vendor_ds_foreground": lambda *_args: (_ for _ in ()).throw(
                AssertionError("fast F9 sequence must not inspect the vendor window")
            ),
            "_replace_vendor_ds_search_text": lambda text, label, wait: (
                events.append(("search", text)) or True
            ),
            "_find_vendor_popup": lambda timeout=0: (_ for _ in ()).throw(
                AssertionError("fast F9 sequence must not probe UIA")
            ),
            "pyautogui": _FakePyAutoGui,
            "time": SimpleNamespace(sleep=lambda _seconds: None),
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "mgmt_click_wait": 0.0,
            "mgmt_focus_wait": 0.0,
            "vendor_popup_open_wait": 0.0,
            "vendor_popup_focus_wait": 0.0,
            "vendor_popup_search_wait": 0.0,
            "mgmt_key_wait": 0.0,
            "ERP_FORM_WAIT": 0.0,
            "skip_visible_row_scan": True,
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    result = loaded["_seed_vendor_by_number_f9"](1118, 797, "1행 거래처", "A001")

    assert result is True
    assert events == [
        ("click", 1118, 797),
        ("key", "f9", 1),
        ("search", "A001"),
        ("key", "tab", 4),
        ("key", "down", 5),
        ("key", "up", 2),
        ("key", "tab", 3),
        ("key", "enter", 2),
    ]


def test_finance_first_vendor_stops_if_f9_does_not_open_vendor_screen():
    events = []

    class _FakePyAutoGui:
        @staticmethod
        def press(key, presses=1, interval=0):
            events.append(("key", key, presses))

    loaded = _load_nested_functions(
        "_seed_vendor_by_number_f9",
        namespace={
            "_click_form_xy": lambda x, y, label, wait=0: events.append(("click", x, y)),
            "_release_modifiers": lambda *_args, **_kwargs: None,
            "_foreground_window_title": lambda: (101, "대승"),
            "_window_process_id": lambda hwnd: 10772 if hwnd == 101 else 0,
            "_is_vendor_ds_title": lambda title: False,
            "_wait_vendor_ds_foreground": lambda process_id, timeout: (
                events.append(("vendor-ds", process_id)) or (0, "")
            ),
            "_replace_vendor_ds_search_text": lambda *_args: events.append(("search",)),
            "_find_vendor_popup": lambda timeout=0: events.append(("popup-check", timeout)),
            "pyautogui": _FakePyAutoGui,
            "time": SimpleNamespace(sleep=lambda _seconds: None),
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "mgmt_click_wait": 0.0,
            "mgmt_focus_wait": 0.0,
            "vendor_popup_open_wait": 0.0,
            "vendor_popup_focus_wait": 0.0,
            "vendor_popup_search_wait": 0.0,
            "mgmt_key_wait": 0.0,
            "ERP_FORM_WAIT": 0.0,
            "skip_visible_row_scan": False,
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    result = loaded["_seed_vendor_by_number_f9"](1118, 797, "1행 거래처", "A001")

    assert result is False
    assert events == [
        ("click", 1118, 797),
        ("key", "f9", 1),
        ("vendor-ds", 10772),
    ]


def test_vendor_ds_foreground_accepts_active_window_in_same_erp_process():
    class _FakeClock:
        now = 0.0

        @classmethod
        def time(cls):
            return cls.now

        @classmethod
        def sleep(cls, seconds):
            cls.now += max(0.01, float(seconds))

    loaded = _load_nested_functions(
        "_wait_vendor_ds_foreground",
        namespace={
            "time": _FakeClock,
            "_foreground_window_title": lambda: (202, "거래처_ds"),
            "_window_process_id": lambda hwnd: 10772 if hwnd == 202 else 0,
            "_is_vendor_ds_title": lambda title: title == "거래처_ds",
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    assert loaded["_wait_vendor_ds_foreground"](10772, 0.5) == (
        202,
        "거래처_ds",
    )


def test_vendor_ds_foreground_activates_background_same_pid_window_with_win32():
    events = []
    state = {"active": False}
    titles = {
        202: "거래처_ds",
        301: "거래처_ds",
        302: "다른화면",
    }
    process_ids = {101: 10772, 202: 10772, 301: 9900, 302: 10772}

    class _FakeClock:
        now = 0.0

        @classmethod
        def time(cls):
            return cls.now

        @classmethod
        def sleep(cls, seconds):
            cls.now += max(0.01, float(seconds))

    class _Buffer:
        value = ""

        def __len__(self):
            return 256

        def __len__(self):
            return 256

    class _FakeUser32:
        @staticmethod
        def EnumWindows(callback, _lparam):
            for hwnd in (301, 302, 202):
                callback(hwnd, 0)
            return True

        @staticmethod
        def IsWindowVisible(_hwnd):
            return True

        @staticmethod
        def GetWindowTextLengthW(hwnd):
            return len(titles.get(int(hwnd), ""))

        @staticmethod
        def GetWindowTextW(hwnd, buffer, _size):
            buffer.value = titles.get(int(hwnd), "")
            return len(buffer.value)

        @staticmethod
        def GetForegroundWindow():
            return 101

        @staticmethod
        def GetWindowThreadProcessId(hwnd, _process_id):
            return {101: 11, 202: 22}.get(int(hwnd), 0)

        @staticmethod
        def AttachThreadInput(current, target, attach):
            events.append(("attach", int(current), int(target), bool(attach)))
            return True

        @staticmethod
        def ShowWindow(hwnd, command):
            events.append(("show", int(hwnd), int(command)))
            return True

        @staticmethod
        def BringWindowToTop(hwnd):
            events.append(("bring", int(hwnd)))
            return True

        @staticmethod
        def SetForegroundWindow(hwnd):
            events.append(("foreground", int(hwnd)))
            state["active"] = True
            return True

        @staticmethod
        def SetActiveWindow(hwnd):
            events.append(("active", int(hwnd)))
            return True

        @staticmethod
        def SetFocus(hwnd):
            events.append(("focus", int(hwnd)))
            return True

    class _FakeKernel32:
        @staticmethod
        def GetCurrentThreadId():
            return 33

    fake_ctypes = SimpleNamespace(
        c_bool=bool,
        c_void_p=object,
        WINFUNCTYPE=lambda *_args: (lambda callback: callback),
        create_unicode_buffer=lambda _size: _Buffer(),
        windll=SimpleNamespace(user32=_FakeUser32(), kernel32=_FakeKernel32()),
    )

    loaded = _load_nested_functions(
        "_wait_vendor_ds_foreground",
        namespace={
            "ctypes": fake_ctypes,
            "time": _FakeClock,
            "_foreground_window_title": lambda: (
                (202, "거래처_ds") if state["active"] else (101, "대승")
            ),
            "_window_process_id": lambda hwnd: process_ids.get(int(hwnd), 0),
            "_is_vendor_ds_title": lambda title: title == "거래처_ds",
            "self": SimpleNamespace(
                logger=SimpleNamespace(
                    debug=lambda *args, **_kwargs: events.append(("debug", args)),
                    warning=lambda *args, **_kwargs: events.append(("warning", args)),
                    info=lambda *_args, **_kwargs: None,
                )
            ),
        },
    )

    result = loaded["_wait_vendor_ds_foreground"](10772, 0.5)
    assert result == (
        202,
        "거래처_ds",
    ), events
    assert ("show", 202, 9) in events
    assert ("bring", 202) in events
    assert ("foreground", 202) in events
    assert not any(event[0] == "show" and event[1] == 301 for event in events)


def test_finance_first_vendor_search_types_physically_without_clipboard():
    events = []

    class _FakePyAutoGui:
        @staticmethod
        def write(text, interval=0):
            events.append(("write", text, interval))

    loaded = _load_nested_functions(
        "_replace_vendor_ds_search_text",
        namespace={
            "re": re,
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "_release_modifiers": lambda label, wait=False: events.append(
                ("release", label)
            ),
            "_force_english_ime": lambda label="": events.append(("ime", label)),
            "pyautogui": _FakePyAutoGui,
            "time": SimpleNamespace(
                sleep=lambda seconds: events.append(("sleep", seconds))
            ),
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    assert loaded["_replace_vendor_ds_search_text"]("PT032", "1행 거래처", 0.40) is True
    assert events == [
        ("release", "1행 거래처 거래처번호 물리 키 입력 직전"),
        ("ime", "1행 거래처"),
        ("write", "PT032", 0.15),
        ("release", "1행 거래처 거래처번호 물리 키 입력 후"),
        ("sleep", 0.40),
    ]

    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    helper_start = source.index("def _replace_vendor_ds_search_text")
    helper_end = source.index("def _seed_vendor_by_number_f9", helper_start)
    helper = source[helper_start:helper_end]
    # 클립보드는 원격 도구와 공유되어 오염될 수 있어 값 입력에 쓰지 않는다.
    assert "pyperclip" not in helper
    assert "pyautogui.write(vendor_code" in helper
    assert "_force_english_ime(label)" in helper
    assert "_type_vendor_code" not in helper
    assert "_paste_text_fast" not in helper
    assert "_vendor_ds_search_visual_ink" not in helper


def test_vendor_code_input_uses_vk_packet_without_clipboard():
    calls = []
    ime = []

    def _send_keys(text, **kwargs):
        calls.append((text, kwargs))

    loaded = _load_nested_functions(
        "_type_vendor_code",
        namespace={
            "re": re,
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "send_keys": _send_keys,
            "_force_english_ime": lambda label="": ime.append(label),
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    assert loaded["_type_vendor_code"]("PT032", "1행 거래처", interval=0.01) is True
    assert calls == [
        (
            "PT032",
            {
                "pause": 0.05,
                "with_spaces": True,
                "vk_packet": True,
            },
        )
    ]
    assert ime == ["1행 거래처"]

    assert loaded["_type_vendor_code"]("거래처1", "2행 거래처") is False
    assert loaded["_type_vendor_code"]("PT 032", "2행 거래처") is False
    assert len(calls) == 1

    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    helper_start = source.index("def _type_vendor_code")
    helper_end = source.index("def _wait_first_vendor_value_committed", helper_start)
    helper = source[helper_start:helper_end]
    # 클립보드 미사용(VK_PACKET) — 원격 클립보드 오염과 IME 상태에 모두 무관.
    assert "pyperclip" not in helper
    assert "vk_packet=True" in helper
    assert "def _force_english_ime" in source
    assert "ImmSetConversionStatus" in source


@pytest.mark.parametrize("type_result", [True, False])
def test_finance_direct_vendor_waits_after_keyboard_input_before_single_enter(
    type_result,
):
    events = []

    class _FakePyAutoGui:
        @staticmethod
        def press(key, presses=1, interval=0):
            events.append(("key", key, presses))

    # 입력 전 빈 셀 → 타이핑된 코드 → Enter 확정 후 이름(코드) 변환 순서의
    # 셀 잉크 변화를 재현한다.
    ink_sequence = iter(
        [
            (0, 0, 0, 0),
            (30, 6, 12, 40),
            (90, 8, 30, 120),
        ]
    )

    def fake_ink(_x, _y):
        events.append(("ink",))
        return next(ink_sequence, (90, 8, 30, 120))

    loaded = _load_nested_functions(
        "_input_finance_vendor_code_xy",
        namespace={
            "re": re,
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "_management_value_visual_ink": fake_ink,
            "_click_form_xy": lambda x, y, label, wait=0: events.append(
                ("click", x, y, label)
            ),
            "_release_modifiers": lambda label, wait=False: events.append(
                ("release", label)
            ),
            "_type_vendor_code": lambda text, label, interval=None: (
                events.append(("type", text, label, interval)) or type_result
            ),
            "pyautogui": _FakePyAutoGui,
            "time": SimpleNamespace(
                sleep=lambda seconds: events.append(("sleep", seconds))
            ),
            "mgmt_click_wait": 0.0,
            "mgmt_focus_wait": 0.10,
            "mgmt_key_wait": 0.0,
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    result = loaded["_input_finance_vendor_code_xy"](
        1118, 797, "A001", "2행 거래처", 0.30, 0.40
    )

    assert result is type_result
    # 빈 셀 검사는 편집 반전을 피하려고 셀 클릭 전에 수행한다.
    assert events[0] == ("ink",)
    assert events[1] == ("click", 1118, 797, "2행 거래처")
    if type_result:
        typed_at = next(index for index, event in enumerate(events) if event[0] == "type")
        settle_at = events.index(("sleep", 0.30))
        f9_at = events.index(("key", "f9", 1))
        enter_at = events.index(("key", "enter", 1))
        commit_at = events.index(("sleep", 0.40))
        # 사용자 확정 흐름: 입력 → F9 → Enter 순서를 유지해야 한다.
        assert typed_at < settle_at < f9_at < enter_at < commit_at
        assert [event for event in events if event[:2] == ("key", "enter")] == [
            ("key", "enter", 1)
        ]
    else:
        assert not any(event[:2] == ("key", "enter") for event in events)
        assert not any(event[:2] == ("key", "f9") for event in events)

    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    helper_start = source.index("def _input_finance_vendor_code_xy")
    helper_end = source.index("def _input_vendor_by_number_keyboard", helper_start)
    helper = source[helper_start:helper_end]
    assert "pyperclip" not in helper
    assert "_paste_text_fast" not in helper
    # 입력 전 빈 셀 확인과 Enter 확정(이름 변환) 검증은 셀 잉크 검사로 한다.
    assert "_management_value_visual_ink" in helper
    assert "_raise_if_vendor_ds_open" not in helper
    assert "_recover_finance_vendor_ds_popup" not in helper


def test_finance_direct_vendor_stops_when_previous_row_value_still_visible():
    events = []
    loaded = _load_nested_functions(
        "_input_finance_vendor_code_xy",
        namespace={
            "re": re,
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "_click_form_xy": lambda *_args, **_kwargs: events.append(("click",)),
            "_release_modifiers": lambda *_args, **_kwargs: None,
            "_type_vendor_code": lambda *_args, **_kwargs: (
                events.append(("type",)) or True
            ),
            "_management_value_visual_ink": lambda _x, _y: (120, 10, 40, 160),
            "pyautogui": SimpleNamespace(
                press=lambda key, **_kwargs: events.append(("key", key))
            ),
            # 폴링 대기(지연 갱신)까지 소진되도록 time.time을 가짜 시계로 제공.
            "time": SimpleNamespace(
                sleep=lambda _seconds: None,
                time=lambda _c=iter(range(0, 1000)): float(next(_c)),
            ),
            "mgmt_click_wait": 0.0,
            "mgmt_focus_wait": 0.0,
            "mgmt_key_wait": 0.0,
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    assert loaded["_input_finance_vendor_code_xy"](
        1118, 797, "A001", "5행 거래처", 0.0, 0.0
    ) is False
    # 값이 계속 남아 있으면(지연 갱신 폴링 후에도) 타이핑도 Enter도 보내지
    # 않고 중단한다.
    assert ("type",) not in events
    assert not any(event[0] == "key" for event in events)


def test_finance_direct_vendor_confirms_when_name_appears():
    # 입력값(번호)이 셀에 반영된 뒤 F9→Enter로 이름(번호)로 변환되면
    # 잉크가 늘고 확정 성공으로 처리한다.
    pressed = []
    ink_seq = iter([
        (0, 0, 0, 0),      # 입력 전: 비어 있음
        (30, 6, 12, 26),   # 입력 후(F9 전): 번호가 셀에 반영됨
        (120, 8, 40, 150),  # Enter 후: 이름(번호)로 변환되어 잉크 증가
    ])
    loaded = _load_nested_functions(
        "_input_finance_vendor_code_xy",
        namespace={
            "re": re,
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "_click_form_xy": lambda *_args, **_kwargs: None,
            "_release_modifiers": lambda *_args, **_kwargs: None,
            "_type_vendor_code": lambda *_args, **_kwargs: True,
            "_management_value_visual_ink": lambda _x, _y: next(ink_seq, (0, 0, 0, 0)),
            "pyautogui": SimpleNamespace(
                press=lambda key, **_kwargs: pressed.append(key)
            ),
            "time": SimpleNamespace(sleep=lambda _seconds: None),
            "mgmt_click_wait": 0.0,
            "mgmt_focus_wait": 0.0,
            "mgmt_key_wait": 0.0,
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    assert loaded["_input_finance_vendor_code_xy"](
        1118, 797, "A001", "5행 거래처", 0.0, 0.0
    ) is True
    # 입력 → F9 → Enter 1회로 확정한다.
    assert pressed == ["f9", "enter"]


def test_finance_direct_vendor_reinputs_when_value_not_registered():
    # 입력 후에도 셀이 비어 있으면(F9 전 등록 실패) 재입력하고 F9는 보내지 않는다.
    pressed = []
    ink_seq = iter([
        (0, 0, 0, 0),      # 입력 전
        (0, 0, 0, 0),      # att1 입력 후: 셀 비어 있음(등록 안 됨) → 재입력
        (30, 6, 12, 26),   # att2 입력 후: 번호 반영
        (120, 8, 40, 150),  # att2 Enter 후: 변환됨
    ])
    loaded = _load_nested_functions(
        "_input_finance_vendor_code_xy",
        namespace={
            "re": re,
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "_click_form_xy": lambda *_args, **_kwargs: None,
            "_release_modifiers": lambda *_args, **_kwargs: None,
            "_type_vendor_code": lambda *_args, **_kwargs: True,
            "_management_value_visual_ink": lambda _x, _y: next(ink_seq, (0, 0, 0, 0)),
            "pyautogui": SimpleNamespace(
                press=lambda key, **_kwargs: pressed.append(key)
            ),
            "time": SimpleNamespace(sleep=lambda _seconds: None),
            "mgmt_click_wait": 0.0,
            "mgmt_focus_wait": 0.0,
            "mgmt_key_wait": 0.0,
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    assert loaded["_input_finance_vendor_code_xy"](
        1118, 756, "A001", "5행 거래처", 0.0, 0.0
    ) is True
    # 등록 실패한 att1에서는 F9를 보내지 않고, att2에서만 f9→enter를 보낸다.
    assert pressed == ["f9", "enter"]


def test_finance_direct_vendor_fails_when_popup_never_closes():
    # Enter 후 팝업(2324)이 계속 남아 ESC로도 닫히지 않으면 중단한다.
    pressed = []
    loaded = _load_nested_functions(
        "_input_finance_vendor_code_xy",
        namespace={
            "re": re,
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "_click_form_xy": lambda *_args, **_kwargs: None,
            "_release_modifiers": lambda *_args, **_kwargs: None,
            "_type_vendor_code": lambda *_args, **_kwargs: True,
            # 입력 전만 비어 있고 이후로는 계속 팝업(2324).
            "_management_value_visual_ink": (
                lambda _x, _y, _c={"n": 0}: (0, 0, 0, 0)
                if _c.__setitem__("n", _c["n"] + 1) or _c["n"] == 1
                else (2324, 14, 166, 348)
            ),
            "pyautogui": SimpleNamespace(
                press=lambda key, **_kwargs: pressed.append(key)
            ),
            "time": SimpleNamespace(sleep=lambda _seconds: None),
            "mgmt_click_wait": 0.0,
            "mgmt_focus_wait": 0.0,
            "mgmt_key_wait": 0.0,
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    assert loaded["_input_finance_vendor_code_xy"](
        1118, 756, "NY018", "169행 거래처", 0.0, 0.0
    ) is False
    # 팝업이 닫히지 않으면 ESC를 시도하고 실패로 중단한다.
    assert "esc" in pressed


def test_finance_direct_vendor_closes_leftover_popup_before_input():
    # 입력 전 값 셀이 팝업(2324)으로 덮여 있으면 ESC로 닫고 진행한다.
    pressed = []
    ink_seq = iter([
        (2324, 14, 166, 348),  # 입력 전: 이전 행 팝업이 남음
        (0, 0, 0, 0),        # ESC 후: 팝업 닫힘 확인 → close 반환
        (0, 0, 0, 0),        # pre 재측정(비어 있음)
        (30, 6, 12, 26),     # 입력 후(F9 전): 번호 반영
        (120, 8, 40, 150),   # Enter 후: 이름(번호)로 변환
    ])
    loaded = _load_nested_functions(
        "_input_finance_vendor_code_xy",
        namespace={
            "re": re,
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "_click_form_xy": lambda *_args, **_kwargs: None,
            "_release_modifiers": lambda *_args, **_kwargs: None,
            "_type_vendor_code": lambda *_args, **_kwargs: True,
            "_management_value_visual_ink": lambda _x, _y: next(ink_seq, (0, 0, 0, 0)),
            "pyautogui": SimpleNamespace(
                press=lambda key, **_kwargs: pressed.append(key)
            ),
            "time": SimpleNamespace(sleep=lambda _seconds: None),
            "mgmt_click_wait": 0.0,
            "mgmt_focus_wait": 0.0,
            "mgmt_key_wait": 0.0,
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    assert loaded["_input_finance_vendor_code_xy"](
        1118, 756, "PT032", "170행 거래처", 0.0, 0.0
    ) is True
    # 입력 전 팝업을 먼저 ESC로 닫고 그 다음 정상 입력(f9→enter)한다.
    assert pressed[0] == "esc"
    assert pressed[-2:] == ["f9", "enter"]


def test_grid_scrolls_to_top_before_management_fill():
    # 붙여넣기 후 그리드가 1행이 아닌 위치에 있을 수 있으므로, 관리항목
    # 입력 시작 전에 첫 셀 클릭 + Ctrl+Home으로 맨 위(1행)로 올려야 한다.
    source = MANAGER_SOURCE.read_text(encoding="utf-8")

    anchor = source.index("_paste_grid_until_reflected()")
    fill_at = source.index("_fill_management_items_by_coord()", anchor)
    between = source[anchor:fill_at]
    assert "pyautogui.hotkey('ctrl', 'home')" in between
    assert "ERP_GRID_SCROLL_TOP_BEFORE_MGMT" in between
    assert "first_account_cell_xy[0]" in between


def test_row_advance_recovery_lives_in_coord_fill_scope():
    # 전표 행 미이동 복구(Down 재전송)는 요약 앵커/스크롤 상태가 있는
    # _fill_management_items_by_coord 루프 안에 있어야 한다. 입력 함수
    # (_input_finance_vendor_code_xy)는 그 상태를 볼 수 없어 여기 두면
    # NameError가 난다.
    source = MANAGER_SOURCE.read_text(encoding="utf-8")

    coord_scope_start = source.index("def _fill_management_items_by_coord")
    recovery_at = source.index("전표 행 미이동 복구: ")
    assert recovery_at > coord_scope_start

    # 입력 함수 본문에는 스코프 밖 이름이 없어야 한다.
    input_start = source.index("def _input_finance_vendor_code_xy")
    input_end = source.index("def _input_vendor_by_number_keyboard", input_start)
    input_body = source[input_start:input_end]
    assert "row_geometry_state" not in input_body
    assert "_advance_grid_row" not in input_body

    # 복구 조건은 미지급금 거래처 입력 실패 + 스크롤 모드로 한정되고,
    # 복구 로직과 함께 coord-fill 함수 구역 안에 있어야 한다.
    coord_region = source[coord_scope_start:]
    recoverable_at = coord_region.index("거래처번호 직접 키보드 입력")
    assert 'if not recoverable:' in coord_region
    # Ctrl+Home 재탐색 블록이 추가되어 검사 창을 넓힌다(스크롤 모드 분기 보존 확인).
    assert "bottom_scroll_mode" in coord_region[recoverable_at : recoverable_at + 20000]
    assert "pyautogui.press('down')" in coord_region


def test_finance_direct_vendor_uses_safe_default_settle_times():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")

    # 입력 후 F9 전에 ERP가 값을 받아들일 시간을 충분히 준다(너무 빠르면
    # 검색이 빈 값이 되어 거래처가 확정되지 않는다).
    assert 'ERP_FINANCE_VENDOR_PASTE_SETTLE_WAIT", "1.20"' in source
    assert 'ERP_FINANCE_VENDOR_COMMIT_SETTLE_WAIT", "2.00"' in source
    assert 'ERP_FINANCE_ROW_ADVANCE_SETTLE_WAIT", "2.50"' in source
    assert 'ERP_MGMT_VENDOR_TYPE_INTERVAL", "0.15"' in source
    # 값 칸 스캔은 분할 바 위치와 무관하게 칸 전체를 덮어야 한다.
    assert 'ERP_MGMT_VALUE_SCAN_WIDTH", "350"' in source
    assert 'ERP_FINANCE_VENDOR_F9_WAIT", "1.00"' in source
    # 지점 자동입력 확인은 기본 6초(24회) 폴링한다.
    assert 'ERP_MGMT_BANK_BRANCH_CONFIRM_POLLS", "24"' in source
    # 관리항목 실패 시 무인 진단용 스크린샷을 저장한다.
    assert "def _save_management_failure_screenshot" in source


def test_finance_direct_vendor_waits_before_enter_and_before_next_row():
    events = []

    class _FakePyAutoGui:
        @staticmethod
        def hotkey(*keys):
            events.append(("hotkey", *keys))

        @staticmethod
        def press(key):
            events.append(("key", key))

    loaded = _load_nested_functions(
        "_type_or_paste_text",
        "_input_value_xy",
        namespace={
            "_click_form_xy": lambda x, y, label, wait=0: events.append(("click", x, y, wait)),
            "_release_modifiers": lambda label, wait=False: events.append(("release", label)),
            "mgmt_clipboard_cache": {"text": None},
            "pyperclip": SimpleNamespace(copy=lambda text: events.append(("copy", text))),
            "pyautogui": _FakePyAutoGui,
            "time": SimpleNamespace(sleep=lambda seconds: events.append(("sleep", seconds))),
            "mgmt_click_wait": 0.06,
            "mgmt_focus_wait": 0.05,
            "mgmt_commit_wait": 0.08,
            "mgmt_key_wait": 0.05,
            "mgmt_clipboard_wait": 0.02,
            "verbose_management_clear": False,
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    loaded["_input_value_xy"](
        1118,
        797,
        "B002",
        "2행 거래처",
        enter_count=1,
        clear=False,
        paste_settle_wait=0.10,
        commit_settle_wait=0.16,
    )

    assert events == [
        ("click", 1118, 797, 0.06),
        ("release", "2행 거래처 클릭 후"),
        ("sleep", 0.05),
        ("release", "2행 거래처 붙여넣기 직전"),
        ("copy", "B002"),
        ("sleep", 0.02),
        ("hotkey", "ctrl", "v"),
        ("release", "2행 거래처 붙여넣기 직후"),
        ("sleep", 0.10),
        ("release", "2행 거래처 Enter 직전"),
        ("key", "enter"),
        ("sleep", 0.16),
        ("sleep", 0.16),
    ]


def test_slip_tree_navigation_waits_between_each_menu_level():
    events = []
    loaded = _load_nested_functions(
        "_open_slip_menu_by_uia_path",
        namespace={
            "_tree_has": lambda _text: False,
            "_click_tree_item_by_text": (
                lambda text, *, expand=False, label=None: (
                    events.append(("tree", text, expand)) or True
                )
            ),
            "_click_slip_menu_by_uia": lambda: events.append(("entry",)) or True,
            "time": SimpleNamespace(
                sleep=lambda seconds: events.append(("sleep", seconds))
            ),
            "menu_tree_wait": 0.37,
        },
    )

    assert loaded["_open_slip_menu_by_uia_path"]() is True
    assert events == [
        ("tree", "전표", True),
        ("sleep", 0.37),
        ("tree", "전표처리", True),
        ("sleep", 0.37),
        ("entry",),
    ]


def test_ds_slip_menu_uses_coordinate_keyboard_sequence_with_waits():
    events = []
    loaded = _load_nested_functions(
        "_slip_menu_fallback_points",
        "_open_slip_menu_by_ds_coordinates",
        namespace={
            "_click_rel": lambda x, y, label: events.append(("click", x, y)),
            "pyautogui": SimpleNamespace(
                press=lambda key: events.append(("key", key))
            ),
            "time": SimpleNamespace(
                sleep=lambda seconds: events.append(("sleep", seconds))
            ),
            "menu_tree_wait": 0.25,
            "menu_step_wait": 0.60,
            "menu_entry_settle_wait": 0.40,
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "self": SimpleNamespace(corp_code="DS", logger=_FakeLogger()),
        },
    )

    assert loaded["_open_slip_menu_by_ds_coordinates"]() is True
    assert events == [
        ("click", 105, 137),
        ("sleep", 0.25),
        ("key", "right"),
        ("sleep", 0.60),
        ("click", 126, 166),
        ("sleep", 0.25),
        ("key", "right"),
        ("sleep", 0.60),
        ("click", 155, 195),
        ("sleep", 0.25),
        ("key", "enter"),
        ("sleep", 0.40),
    ]

    click_points = [event[1:] for event in events if event[0] == "click"]
    assert click_points == [(105, 137), (126, 166), (155, 195)]
    assert (126, 185) not in click_points
    assert (155, 220) not in click_points


def test_ds_accounting_menu_uses_only_fixed_coordinates_and_waits():
    events = []

    def _forbidden(*_args, **_kwargs):
        raise AssertionError("DS coordinate menu must not call UIA/tree helpers")

    loaded = _load_nested_functions(
        "_open_accounting_menu",
        namespace={
            "ds_coordinate_menu": True,
            "_click_rel": lambda x, y, label: events.append(("click", x, y)),
            "_click_text_exact": _forbidden,
            "_tree_has": _forbidden,
            "Desktop": _forbidden,
            "pyautogui": SimpleNamespace(
                press=lambda key: events.append(("key", key))
            ),
            "time": SimpleNamespace(
                sleep=lambda seconds: events.append(("sleep", seconds))
            ),
            "menu_step_wait": 0.60,
            "menu_entry_settle_wait": 0.40,
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "self": SimpleNamespace(corp_code="DS", logger=_FakeLogger()),
        },
    )

    assert loaded["_open_accounting_menu"]() is True
    assert events == [
        ("click", 30, 70),
        ("sleep", 0.60),
        ("click", 145, 70),
        ("sleep", 0.60),
        ("click", 304, 201),
        ("sleep", 0.60),
        ("key", "escape"),
        ("sleep", 0.40),
    ]


def test_ds_main_branch_is_coordinate_only_and_keeps_uia_in_non_ds_branch():
    manager_source = MANAGER_SOURCE.read_text(encoding="utf-8")
    adapter_source = AGENT_ADAPTER_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(manager_source)

    assert 'os.getenv("ERP_DS_MENU_COORDINATE_ONLY", "1")' in manager_source
    for env_name, value in {
        "ERP_DS_MENU_COORDINATE_ONLY": "1",
        "ERP_DS_ACCOUNTING_TILE_X": "304",
        "ERP_DS_ACCOUNTING_TILE_Y": "201",
        "ERP_DS_SLIP_ROOT_Y": "137",
        "ERP_DS_SLIP_ROW_H": "29",
        "ERP_DS_SLIP_ROOT_X": "105",
        "ERP_DS_SLIP_PROCESS_X": "126",
        "ERP_DS_SLIP_ENTRY_X": "155",
    }.items():
        assert f'os.environ["{env_name}"] = "{value}"' in adapter_source

    assert 'os.environ["ERP_DS_SLIP_ROOT_Y"] = "150"' not in adapter_source
    assert 'os.environ["ERP_DS_SLIP_ROW_H"] = "35"' not in adapter_source

    def _call_names(nodes):
        return {
            child.func.id
            for node in nodes
            for child in ast.walk(node)
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name)
        }

    ds_branches = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        if ast.unparse(node.test) != "ds_coordinate_menu":
            continue
        if "_open_slip_menu_by_ds_coordinates" in _call_names(node.body):
            ds_branches.append(node)

    assert len(ds_branches) == 1
    ds_branch = ds_branches[0]
    ds_calls = _call_names(ds_branch.body)
    non_ds_calls = _call_names(ds_branch.orelse)

    assert "_open_slip_menu_by_ds_coordinates" in ds_calls
    assert {
        "_open_slip_menu_by_uia_path",
        "_tree_has",
        "_click_slip_menu_by_uia",
    }.isdisjoint(ds_calls)
    assert "_open_slip_menu_by_uia_path" in non_ds_calls

    retry_branches = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        if ast.unparse(node.test) != "ds_coordinate_menu":
            continue
        body_calls = _call_names(node.body)
        else_calls = _call_names(node.orelse)
        if (
            "_click_slip_menu_by_uia" in else_calls
            and "_wait_slip_form_ready" in else_calls
        ):
            retry_branches.append(node)

    assert len(retry_branches) == 1
    retry_branch = retry_branches[0]
    retry_ds_calls = _call_names(retry_branch.body)
    retry_non_ds_calls = _call_names(retry_branch.orelse)

    assert {
        "_open_slip_menu_by_uia_path",
        "_tree_has",
        "_click_slip_menu_by_uia",
        "_click_rel",
        "_slip_menu_fallback_points",
    }.isdisjoint(retry_ds_calls)
    assert "_click_slip_menu_by_uia" in retry_non_ds_calls


def test_run_menu_initialization_does_not_call_setup_scoped_env_flag():
    """Menu startup must not depend on a helper local to _setup_slip_form."""
    tree = ast.parse(MANAGER_SOURCE.read_text(encoding="utf-8"))
    erp_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "ERPLoginBot"
    )
    run_unlocked = next(
        node
        for node in erp_class.body
        if isinstance(node, ast.FunctionDef) and node.name == "_run_unlocked"
    )
    setup_call = next(
        node
        for node in ast.walk(run_unlocked)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "self"
        and node.func.attr == "_setup_slip_form"
    )
    early_env_flag_calls = [
        node
        for node in ast.walk(run_unlocked)
        if isinstance(node, ast.Call)
        and node.lineno < setup_call.lineno
        and isinstance(node.func, ast.Name)
        and node.func.id == "_env_flag"
    ]

    assert early_env_flag_calls == []


def test_slip_entry_settles_before_immediate_uia_ready_check():
    events = []
    main = _FakeControl("K-System", "Window", _FakeRect(0, 0, 1600, 900))
    main.add(
        _FakeControl(
            "분개전표입력",
            "Text",
            _FakeRect(100, 180, 300, 220),
        )
    )
    loaded = _load_nested_functions(
        "_click_slip_menu_by_uia",
        "_wait_slip_form_ready",
        namespace={
            "main_win": main,
            "pyautogui": SimpleNamespace(
                click=lambda x, y: events.append(("click", x, y))
            ),
            "time": SimpleNamespace(
                time=lambda: 0.0,
                sleep=lambda seconds: events.append(("sleep", seconds)),
            ),
            "menu_entry_settle_wait": 0.61,
            "_slip_form_ready": lambda: events.append(("ready",)) or True,
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    assert loaded["_click_slip_menu_by_uia"]() is True
    assert loaded["_wait_slip_form_ready"](0.45) is True
    assert events == [
        ("click", 200, 200),
        ("sleep", 0.61),
        ("ready",),
    ]


def test_menu_timing_defaults_and_agent_launch_overrides_stay_in_sync():
    manager_source = MANAGER_SOURCE.read_text(encoding="utf-8")
    adapter_source = AGENT_ADAPTER_SOURCE.read_text(encoding="utf-8")
    expected = {
        "ERP_MENU_STEP_WAIT": "0.75",
        "ERP_MENU_TREE_WAIT": "0.35",
        "ERP_MENU_ENTRY_SETTLE_WAIT": "0.60",
    }

    for env_name, default in expected.items():
        assert f'os.getenv("{env_name}", "{default}")' in manager_source
        assert f'os.environ["{env_name}"] = "{default}"' in adapter_source

    helper_start = manager_source.index("def _open_accounting_menu")
    helper_end = manager_source.index("def _click_slip_menu_by_uia", helper_start)
    accounting_menu = manager_source[helper_start:helper_end]

    assert accounting_menu.count("time.sleep(menu_step_wait)") == 3
    assert "time.sleep(ERP_BLOCK_WAIT)" not in accounting_menu

    retry_start = manager_source.index(
        "if not opened_slip_form:",
        manager_source.index("opened_slip_form = _wait_slip_form_ready"),
    )
    retry_end = manager_source.index("if opened_slip_form:", retry_start)
    retry_flow = manager_source[retry_start:retry_end]
    enter_at = retry_flow.index('pyautogui.press("enter")')
    settle_at = retry_flow.index("time.sleep(menu_entry_settle_wait)", enter_at)
    ready_at = retry_flow.index(
        "opened_slip_form = _wait_slip_form_ready(0.35)",
        settle_at,
    )

    assert enter_at < settle_at < ready_at


def test_agent_launch_configures_fine_gdi_scan_and_two_sample_stability():
    manager_source = MANAGER_SOURCE.read_text(encoding="utf-8")
    adapter_source = AGENT_ADAPTER_SOURCE.read_text(encoding="utf-8")

    assert 'os.environ["ERP_MGMT_VISUAL_SCAN_STEP"] = "2"' in adapter_source
    assert 'os.environ["ERP_GRID_PASTE_VISUAL_STABLE_COUNT"] = "2"' in adapter_source
    assert 'os.environ["ERP_GRID_PASTE_READY_MAX_SECONDS"] = "180"' in adapter_source
    assert 'os.getenv("ERP_MGMT_VISUAL_SCAN_STEP", "4")' in manager_source
    assert 'os.getenv("ERP_MGMT_LABEL_X_MIN", "600")' in manager_source
    assert 'os.getenv("ERP_MGMT_LABEL_X_MAX", "900")' in manager_source
    assert 'os.getenv("ERP_GRID_PASTE_VISUAL_STABLE_COUNT", "2")' in manager_source
    assert 'os.getenv("ERP_GRID_PASTE_READY_MAX_SECONDS", "180")' in manager_source


def test_finance_vendor_state_uses_f9_once_then_preserves_bank_path():
    events = []
    state = {"f9_seeded": False}
    loaded = _load_nested_functions(
        "_fill_explicit_management_items",
        namespace={
            "management_active_row_context": {"row_no": None},
            "form_data": {"cash_processing_enabled": True},
            "_uncheck_cash_processing": lambda row_no: events.append(("uncheck", row_no)),
            "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")).lower(),
            "_management_grid_snapshot": lambda: {
                "label_norms": {"계좌번호", "금융기관지점"},
                "labels": ["계좌번호", "금융기관지점"],
            },
            "management_bank_coordinate_fallback_rows": set(),
            "_management_value_xy": lambda item_name, fallback_y: (1118, fallback_y),
            "finance_vendor_entry_state": state,
            "finance_vendor_paste_settle_wait": 0.10,
            "finance_vendor_commit_settle_wait": 0.16,
            "_seed_vendor_by_number_f9": lambda x, y, label, text: (
                events.append(("seed", x, y, label, text)) or True
            ),
            "_input_finance_vendor_code_xy": lambda *args: (
                events.append(("finance-input", args)) or True
            ),
            "_input_vendor_by_number_keyboard": lambda *_args, **_kwargs: events.append(("popup",)),
            "_input_bank_account_by_popup": lambda *args, **kwargs: (
                events.append(("bank-select", args, kwargs)) or True
            ),
            "_input_value_xy": lambda *args, **kwargs: events.append(("input", args, kwargs)),
            "re": re,
            "self": SimpleNamespace(logger=_FakeLogger()),
            "row_no": 1,
            "account_key": "미지급금(원화)",
            "explicit_management": {"거래처": "A001"},
        },
    )
    fill = loaded["_fill_explicit_management_items"]

    # 사용자 확정: 1행도 다른 행과 동일한 입력→F9→Enter 흐름을 쓴다.
    # 1행 전용 seed(거래처ds 팝업 시퀀스)는 호출되지 않는다.
    assert fill() is True
    assert state["f9_seeded"] is True
    assert [event[0] for event in events] == ["finance-input"]
    _, first_args = events[-1]
    assert first_args[2] == "A001"
    assert first_args[4:] == (0.10, 0.16)

    loaded["row_no"] = 2
    loaded["explicit_management"] = {"거래처": "B002"}
    assert fill() is True
    assert [event[0] for event in events] == ["finance-input", "finance-input"]
    _, direct_args = events[-1]
    assert direct_args[2] == "B002"
    assert direct_args[4:] == (0.10, 0.16)

    events.clear()
    loaded["row_no"] = 3
    loaded["account_key"] = "보통예금"
    loaded["explicit_management"] = {
        "계좌번호": "140-000-948562",
        "금융기관지점": "신한 수원금융센터",
        "거래처": "",
    }
    assert fill() is False

    assert [event[0] for event in events] == ["bank-select"]
    assert events[0][1] == (
        1118,
        797,
        "140-000-948562",
        "신한 수원금융센터",
        "3행 계좌번호",
    )


def test_management_value_xy_reuses_ready_snapshot_without_another_uia_scan():
    snapshot_calls = []
    vendor_norm = re.sub(r"\s+", "", "거래처").lower()
    ready_snapshot = {
        "header_value": {
            "rel_x": 1118,
            "rel_y": 777,
            "rect": _FakeRect(760, 767, 1038, 787),
        },
        "items": [
            {
                "text": "거래처",
                "norm": vendor_norm,
                "rel_x": 690,
                "rel_y": 797,
                "rect": _FakeRect(620, 787, 750, 807),
            }
        ],
        "labels": ["거래처"],
    }
    loaded = _load_nested_functions(
        "_management_value_xy",
        namespace={
            "management_grid_ready_state": {"snapshot": ready_snapshot},
            "management_value_xy_cache": {},
            "management_bank_coordinate_fallback_rows": set(),
            "management_active_row_context": {"row_no": 1},
            "_main_rect": lambda: _FakeRect(0, 0, 1600, 900),
            "_env_flag": lambda name, default="0": name == "ERP_FAST_MGMT_ANCHOR",
            "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")).lower(),
            "_management_grid_snapshot": (
                lambda: snapshot_calls.append("full-management-snapshot") or {}
            ),
            "time": SimpleNamespace(sleep=lambda _seconds: None),
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    assert loaded["_management_value_xy"]("거래처", 797) == (1118, 797)
    assert snapshot_calls == []


def test_fast_bank_coordinates_reuse_the_existing_first_management_row():
    vendor_norm = re.sub(r"\s+", "", "거래처").lower()
    bank_cache = {}
    loaded = _load_nested_functions(
        "_prepare_fast_bank_management_coordinates",
        namespace={
            "management_grid_ready_state": {
                "snapshot": {
                    "semantic_ready": True,
                    "header_value": {"rel_x": 1118, "rel_y": 777},
                    "items": [{"norm": vendor_norm, "rel_y": 797}],
                }
            },
            "management_value_xy_cache": {vendor_norm: (1118, 797)},
            "management_bank_value_xy_cache": bank_cache,
            "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")).lower(),
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    assert loaded["_prepare_fast_bank_management_coordinates"]() is True
    assert bank_cache["계좌번호"] == (1118, 797)
    assert bank_cache["금융기관지점"] == (1118, 817)


def test_fast_bank_coordinates_reject_visual_only_ready_snapshot():
    loaded = _load_nested_functions(
        "_prepare_fast_bank_management_coordinates",
        namespace={
            "management_grid_ready_state": {
                "snapshot": {
                    "visual_ready": True,
                    "label_norms": set(),
                    "items": [],
                }
            },
            "management_value_xy_cache": {},
            "management_bank_value_xy_cache": {},
            "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")).lower(),
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    assert loaded["_prepare_fast_bank_management_coordinates"]() is False


def test_fast_bank_coordinates_accept_stable_gdi_snapshot_with_cached_vendor_anchor():
    vendor_norm = re.sub(r"\s+", "", "거래처").lower()
    management_cache = {vendor_norm: (1118, 797)}
    bank_cache = {}
    loaded = _load_nested_functions(
        "_prepare_fast_bank_management_coordinates",
        namespace={
            "management_grid_ready_state": {
                "snapshot": {
                    "management_ready": True,
                    "ready_source": "gdi-visual-stable",
                    "stable_gdi_ready": True,
                    "visual_ready": True,
                }
            },
            "management_value_xy_cache": management_cache,
            "management_bank_value_xy_cache": bank_cache,
            "finance_vendor_entry_state": {"f9_seeded": True},
            "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")).lower(),
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    assert loaded["_prepare_fast_bank_management_coordinates"]() is True
    assert management_cache[vendor_norm] == (1118, 797)
    assert bank_cache[re.sub(r"\s+", "", "계좌번호").lower()] == (1118, 797)
    assert bank_cache[re.sub(r"\s+", "", "금융기관지점").lower()] == (1118, 817)


def test_fast_bank_coordinates_reject_stable_gdi_snapshot_without_cached_vendor_anchor():
    vendor_norm = re.sub(r"\s+", "", "거래처").lower()
    loaded = _load_nested_functions(
        "_prepare_fast_bank_management_coordinates",
        namespace={
            "management_grid_ready_state": {
                "snapshot": {
                    "management_ready": True,
                    "ready_source": "gdi-visual-stable",
                    "stable_gdi_ready": True,
                    "visual_ready": True,
                    # Stable GDI readiness must not derive a bank anchor from
                    # semantic-only fields when the cached vendor coordinate is absent.
                    "header_value": {"rel_x": 1118, "rel_y": 777},
                    "items": [{"norm": vendor_norm, "rel_y": 797}],
                }
            },
            "management_value_xy_cache": {},
            "management_bank_value_xy_cache": {},
            "finance_vendor_entry_state": {"f9_seeded": True},
            "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")).lower(),
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    assert loaded["_prepare_fast_bank_management_coordinates"]() is False


def test_fast_bank_coordinates_reject_stable_gdi_before_first_vendor_f9():
    vendor_norm = re.sub(r"\s+", "", "거래처").lower()
    bank_cache = {}
    loaded = _load_nested_functions(
        "_prepare_fast_bank_management_coordinates",
        namespace={
            "management_grid_ready_state": {
                "snapshot": {
                    "management_ready": True,
                    "ready_source": "gdi-visual-stable",
                    "stable_gdi_ready": True,
                }
            },
            "management_value_xy_cache": {vendor_norm: (1118, 797)},
            "management_bank_value_xy_cache": bank_cache,
            "finance_vendor_entry_state": {"f9_seeded": False},
            "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")).lower(),
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    assert loaded["_prepare_fast_bank_management_coordinates"]() is False
    assert bank_cache == {}


class _SyntheticGdiImage:
    def __init__(
        self,
        width,
        height,
        *,
        row_center_y=None,
        ink_sample_x=100,
        ink_color=(200, 20, 20),
        include_ink=True,
        include_upper_separator=True,
        include_lower_separator=True,
        include_left_border=True,
        include_divider=True,
        include_right_border=True,
        separator_rows=(),
    ):
        self.size = (width, height)
        self.row_center_y = row_center_y
        self.ink_sample_x = ink_sample_x
        self.ink_color = ink_color
        self.include_ink = include_ink
        self.include_upper_separator = include_upper_separator
        self.include_lower_separator = include_lower_separator
        self.include_left_border = include_left_border
        self.include_divider = include_divider
        self.include_right_border = include_right_border
        self.separator_rows = set(separator_rows)

    def getpixel(self, point):
        x, y = point
        if y in self.separator_rows:
            return (180, 180, 180)
        if self.row_center_y is not None:
            upper = self.row_center_y - 8
            lower = self.row_center_y + 12
            if (
                (self.include_upper_separator and y == upper)
                or (self.include_lower_separator and y == lower)
            ):
                return (180, 180, 180)
            if self.include_left_border and x == 80 and upper <= y <= lower:
                return (180, 180, 180)
            if self.include_divider and x == 200 and upper <= y <= lower:
                return (180, 180, 180)
            # scan_left=main.left+650 and value_x=1118, so x=494 is
            # exactly the management table's painted border at value_x+26.
            if self.include_right_border and x == 494 and upper <= y <= lower:
                return (180, 180, 180)
        if (
            self.row_center_y is not None
            and self.include_ink
            and self.ink_sample_x - 6 <= x <= self.ink_sample_x + 6
            and self.row_center_y - 3 <= y <= self.row_center_y + 7
        ):
            return self.ink_color
        if self.row_center_y is not None and y == 0 and x in {4, 8, 12, 16}:
            return (20, 20, 20)
        if self.row_center_y is not None and y == 0 and x in {
            20,
            24,
            28,
            32,
            36,
            40,
            44,
            48,
        }:
            return (180, 180, 180)
        return (255, 255, 255)


def _synthetic_gdi_visual_snapshot(
    visible_rows,
    *,
    red_sample_x=100,
    ink_color=(200, 20, 20),
    include_ink=True,
    include_upper_separator=True,
    include_lower_separator=True,
    include_left_border=True,
    include_divider=True,
    include_right_border=True,
    structure_band_top=None,
    structure_row_center_y=None,
    separators=True,
):
    main_rect = _FakeRect(10, 50, 1610, 1050)
    detected_band_top, red_sample_y, first_value_y, separator_lines = {
        # A splitter persisted high by the ERP user account leaves only ten
        # voucher rows; the production scanner must find the management pane
        # in its earlier 360px scan band instead of assuming the usual 720px.
        10: (420, 48, 470, (473, 481)),
        24: (720, 28, 750, (753, 761)),
        26: (720, 68, 790, (793, 801)),
    }[visible_rows]
    active_band_top = (
        detected_band_top if structure_band_top is None else structure_band_top
    )
    screenshot_regions = []

    def _screenshot(*, region):
        screenshot_regions.append(region)
        _, top, width, height = region
        if width > 1000:
            rows = (
                [line_abs - top for line_abs in separator_lines]
                if separators
                else []
            )
            return _SyntheticGdiImage(width, height, separator_rows=rows)
        active_y = (
            red_sample_y if structure_row_center_y is None else structure_row_center_y
        ) if top == main_rect.top + active_band_top else None
        return _SyntheticGdiImage(
            width,
            height,
            row_center_y=active_y,
            ink_sample_x=red_sample_x,
            ink_color=ink_color,
            include_ink=include_ink,
            include_upper_separator=include_upper_separator,
            include_lower_separator=include_lower_separator,
            include_left_border=include_left_border,
            include_divider=include_divider,
            include_right_border=include_right_border,
        )

    loaded = _load_nested_functions(
        "_management_grid_visual_boundary",
        "_management_grid_visual_snapshot",
        namespace={
            "_main_rect": lambda: main_rect,
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "pyautogui": SimpleNamespace(screenshot=_screenshot),
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )
    return loaded["_management_grid_visual_snapshot"](), main_rect, screenshot_regions


def test_gdi_visual_snapshot_uses_painted_separator_boundary_and_detailed_signature():
    for visible_rows, first_value_y, boundary_abs, boundary_rel, lines in (
        (24, 750, 753, 703, [753, 761]),
        (26, 790, 793, 743, [793, 801]),
    ):
        snapshot, _main_rect, screenshot_regions = _synthetic_gdi_visual_snapshot(
            visible_rows
        )

        assert snapshot["visual_ready"] is True
        assert snapshot["visual_band_top"] == 720
        assert snapshot["first_value_y"] == first_value_y
        assert snapshot["voucher_clip_bottom_abs"] == boundary_abs
        assert snapshot["voucher_clip_bottom_abs"] != 50 + first_value_y - 44
        assert snapshot["visual_signature"] == (
            720,
            first_value_y,
            boundary_rel,
            1,
        )
        assert snapshot["visual_counts"]["boundary"] == {
            "source": "painted-separator",
            "expected_offset": 48,
            "gaps": [8],
            "lines": lines,
        }
        assert len(screenshot_regions) == 5


def test_gdi_visual_boundary_keeps_44px_fallback_without_separator_lines():
    main_rect = _FakeRect(10, 50, 1610, 1050)
    loaded = _load_nested_functions(
        "_management_grid_visual_boundary",
        namespace={
            "_main_rect": lambda: main_rect,
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "pyautogui": SimpleNamespace(
                screenshot=lambda *, region: _SyntheticGdiImage(region[2], region[3])
            ),
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )
    first_value_abs = main_rect.top + 750
    fallback_abs = first_value_abs - 44
    boundary_abs, boundary_detail = loaded["_management_grid_visual_boundary"](
        first_value_abs,
        fallback_abs,
    )

    assert boundary_abs == fallback_abs
    assert boundary_detail == {"source": "offset-fallback", "lines": []}

    snapshot, main_rect, _regions = _synthetic_gdi_visual_snapshot(
        24,
        separators=False,
    )

    assert snapshot["first_value_y"] == 750
    assert snapshot["voucher_clip_bottom_abs"] == main_rect.top + 750 - 44
    assert snapshot["visual_ready"] is True
    assert snapshot["visual_signature"] == (720, 750, 706, 1)
    assert snapshot["visual_counts"]["boundary"] == {
        "source": "offset-fallback",
        "lines": [],
    }


def test_gdi_visual_snapshot_rejects_red_pixels_outside_label_roi():
    inside_edge, _main_rect, _regions = _synthetic_gdi_visual_snapshot(
        24,
        red_sample_x=100,
    )
    # scan_left + 300 resolves to x=960, outside the default label ROI x=600..900.
    snapshot, _main_rect, _regions = _synthetic_gdi_visual_snapshot(
        24,
        red_sample_x=300,
    )

    assert inside_edge["visual_ready"] is True
    assert snapshot["visual_ready"] is False
    assert snapshot["visual_signature"] is None
    assert snapshot["visual_counts"]["red"] == 0


def test_gdi_visual_snapshot_accepts_black_management_label_without_red_pixels():
    snapshot, _main_rect, _regions = _synthetic_gdi_visual_snapshot(
        24,
        ink_color=(20, 20, 20),
    )

    assert snapshot["visual_ready"] is True
    assert snapshot["first_value_y"] == 750
    assert snapshot["visual_counts"]["red"] == 0
    accepted_band = next(
        band
        for band in snapshot["visual_counts"]["bands"]
        if band["top"] == 720
    )
    assert accepted_band["structure"]["ink_pixels"] >= 2
    assert accepted_band["structure"]["right_border_x"] == 494


def test_gdi_visual_snapshot_infers_first_row_from_single_lower_separator():
    snapshot, _main_rect, _regions = _synthetic_gdi_visual_snapshot(
        24,
        include_upper_separator=False,
    )

    assert snapshot["visual_ready"] is True
    assert snapshot["first_value_y"] == 750
    active_band = next(
        band
        for band in snapshot["visual_counts"]["bands"]
        if band["top"] == 720
    )
    assert active_band["horizontal_lines"] == [40]
    assert active_band["structure"]["source"] == "inferred-single-line"
    assert active_band["structure"]["upper"] == 20
    assert active_band["structure"]["lower"] == 40


def test_gdi_inferred_header_interval_targets_next_data_row_without_moving_voucher_boundary():
    snapshot, main_rect, _regions = _synthetic_gdi_visual_snapshot(
        24,
        include_upper_separator=False,
        structure_row_center_y=14,
        separators=False,
    )

    assert snapshot["visual_ready"] is True
    active_band = next(
        band
        for band in snapshot["visual_counts"]["bands"]
        if band["top"] == 720
    )
    assert active_band["horizontal_lines"] == [26]
    assert active_band["structure"]["source"] == "inferred-single-line"
    assert active_band["structure"]["upper"] == 6
    assert active_band["structure"]["lower"] == 26
    assert snapshot["first_value_y"] == 756
    assert snapshot["voucher_clip_bottom_abs"] == main_rect.top + 692
    assert snapshot["visual_signature"] == (720, 756, 692, 1)


def test_gdi_single_separator_fallback_still_requires_triad_and_label_ink():
    for options in (
        {"include_right_border": False},
        {"include_ink": False},
    ):
        snapshot, _main_rect, _regions = _synthetic_gdi_visual_snapshot(
            24,
            include_upper_separator=False,
            **options,
        )

        assert snapshot["visual_ready"] is False
        assert snapshot["visual_signature"] is None
        active_band = next(
            band
            for band in snapshot["visual_counts"]["bands"]
            if band["top"] == 720
        )
        inferred_checks = [
            check
            for check in active_band["candidate_checks"]
            if check.get("source") == "inferred-single-line"
        ]
        assert inferred_checks
        assert not any(check["accepted"] for check in inferred_checks)


def test_gdi_visual_snapshot_rejects_row_geometry_without_management_right_border():
    snapshot, _main_rect, _regions = _synthetic_gdi_visual_snapshot(
        24,
        include_right_border=False,
    )

    assert snapshot["visual_ready"] is False
    assert snapshot["visual_signature"] is None
    active_band = next(
        band
        for band in snapshot["visual_counts"]["bands"]
        if band["top"] == 720
    )
    assert active_band["structure"] is None
    assert active_band["candidate_checks"]
    assert active_band["candidate_checks"][0]["right_border_score"] == 2


def test_gdi_visual_snapshot_rejects_text_left_of_management_label_cell():
    snapshot, _main_rect, _regions = _synthetic_gdi_visual_snapshot(
        24,
        red_sample_x=52,
    )

    assert snapshot["visual_ready"] is False
    active_band = next(
        band
        for band in snapshot["visual_counts"]["bands"]
        if band["top"] == 720
    )
    assert active_band["candidate_checks"][0]["ink_pixels"] == 0


def test_gdi_visual_snapshot_rejects_upper_voucher_grid_structure_alone():
    snapshot, _main_rect, _regions = _synthetic_gdi_visual_snapshot(
        24,
        structure_band_top=360,
        include_right_border=False,
    )

    assert snapshot["visual_ready"] is False
    assert snapshot["visual_signature"] is None
    upper_band = next(
        band
        for band in snapshot["visual_counts"]["bands"]
        if band["top"] == 360
    )
    assert upper_band["horizontal_lines"] == [20, 40]
    assert upper_band["structure"] is None


def test_gdi_visual_snapshot_requires_ink_inside_first_management_label_cell():
    snapshot, _main_rect, _regions = _synthetic_gdi_visual_snapshot(
        24,
        include_ink=False,
    )

    assert snapshot["visual_ready"] is False
    active_band = next(
        band
        for band in snapshot["visual_counts"]["bands"]
        if band["top"] == 720
    )
    assert active_band["candidate_checks"][0]["ink_pixels"] == 0


def test_management_ready_wait_accepts_two_matching_gdi_visual_snapshots_without_uia():
    vendor_norm = re.sub(r"\s+", "", "거래처").lower()
    initial_signature = (720, 796, 703, 1)
    signature = (720, 797, 703, 1)
    snapshots = [
        {
            "visual_ready": True,
            "visual_score": 50,
            "visual_signature": initial_signature,
            "value_x": 1118,
            "first_value_y": 797,
            "voucher_clip_bottom_abs": 703,
        },
        {
            "visual_ready": True,
            "visual_score": 50,
            "visual_signature": signature,
            "value_x": 1118,
            "first_value_y": 797,
            "voucher_clip_bottom_abs": 703,
        },
        {
            "visual_ready": True,
            "visual_score": 50,
            "visual_signature": signature,
            "value_x": 1118,
            "first_value_y": 797,
            "voucher_clip_bottom_abs": 703,
        },
    ]
    uia_calls = []
    management_cache = {}

    class _Clock:
        def __init__(self):
            self.now = 0.0

        def time(self):
            return self.now

        def sleep(self, seconds):
            self.now += float(seconds)

    clock = _Clock()
    loaded = _load_nested_functions(
        "_wait_for_management_grid_ready",
        namespace={
            "form_data": {"erp_line_management_items": [{"거래처": "V001"}]},
            "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")).lower(),
            "row_count": 1,
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "time": clock,
            "_management_grid_visual_snapshot": lambda *_args, **_kwargs: snapshots.pop(0),
            "_management_grid_snapshot": (
                lambda *_args, **_kwargs: uia_calls.append("uia") or {}
            ),
            "management_value_xy_cache": management_cache,
            "_fail_form": lambda message: (_ for _ in ()).throw(RuntimeError(message)),
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    result = loaded["_wait_for_management_grid_ready"]("test paste")

    assert result["management_ready"] is True
    assert result["ready_source"] == "gdi-visual-stable"
    assert result["stable_gdi_ready"] is True
    assert result["visual_signature"] == signature
    assert result["voucher_clip_bottom_abs"] == 703
    assert management_cache[vendor_norm] == (1118, 797)
    assert snapshots == []
    assert uia_calls == []


def test_management_ready_wait_does_not_accept_a_single_gdi_visual_snapshot():
    signature = (720, 797, 703, 1)
    calls = {"visual": 0, "uia": 0}

    class _Clock:
        def __init__(self):
            self.now = 0.0

        def time(self):
            return self.now

        def sleep(self, seconds):
            self.now += float(seconds)

    def _getenv(name, default=None):
        if name == "ERP_GRID_PASTE_READY_SECONDS_PER_ROW":
            return "10"
        if name == "ERP_GRID_PASTE_READY_MAX_SECONDS":
            return "180"
        if name == "ERP_GRID_PASTE_VISUAL_POLL_SECONDS":
            return "20"
        return default

    def _visual_snapshot(*_args, **_kwargs):
        calls["visual"] += 1
        if calls["visual"] == 1:
            return {
                "visual_ready": True,
                "visual_score": 50,
                "visual_signature": signature,
                "value_x": 1118,
                "first_value_y": 797,
            }
        return {
            "visual_ready": False,
            "visual_score": 0,
            "visual_signature": None,
            "value_x": None,
            "first_value_y": None,
        }

    clock = _Clock()
    loaded = _load_nested_functions(
        "_wait_for_management_grid_ready",
        namespace={
            "form_data": {"erp_line_management_items": [{"거래처": "V001"}]},
            "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")).lower(),
            "row_count": 210,
            "os": SimpleNamespace(getenv=_getenv),
            "time": clock,
            "_management_grid_visual_snapshot": _visual_snapshot,
            "_management_grid_snapshot": (
                lambda *_args, **_kwargs: calls.__setitem__("uia", calls["uia"] + 1) or {}
            ),
            "management_value_xy_cache": {},
            "_fail_form": lambda message: (_ for _ in ()).throw(RuntimeError(message)),
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    with pytest.raises(RuntimeError, match="하단 관리항목 표시 대기 실패"):
        loaded["_wait_for_management_grid_ready"]("test paste")

    assert clock.now == 180.0
    assert calls["visual"] == 10
    assert calls["uia"] == 0


def test_strict_bank_value_coordinates_do_not_run_a_management_uia_scan():
    for total_rows in (230, 300):
        snapshot_calls = []
        loaded = _load_nested_functions(
            "_management_value_xy",
            namespace={
                "management_grid_ready_state": {"snapshot": {}},
                "management_value_xy_cache": {},
                "management_bank_value_xy_cache": {
                    "계좌번호": (1118, 797),
                    "금융기관지점": (1118, 817),
                },
                "management_bank_coordinate_fallback_rows": {total_rows},
                "management_active_row_context": {"row_no": total_rows},
                "_main_rect": lambda: _FakeRect(0, 0, 1600, 900),
                "_env_flag": lambda _name, _default="0": True,
                "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")).lower(),
                "_management_grid_snapshot": (
                    lambda: snapshot_calls.append("full-management-snapshot") or {}
                ),
                "time": SimpleNamespace(sleep=lambda _seconds: None),
                "self": SimpleNamespace(logger=_FakeLogger()),
            },
        )

        assert loaded["_management_value_xy"]("계좌번호", 797) == (1118, 797)
        assert loaded["_management_value_xy"]("금융기관지점", 817) == (1118, 817)
        assert snapshot_calls == []


def test_fast_bank_row_check_bypasses_full_uia_visibility_scan():
    for total_rows in (230, 300):
        fallback_rows = set()
        full_scan_calls = []
        loaded = _load_nested_functions(
            "_ensure_bank_management_row",
            namespace={
                "skip_visible_row_scan": True,
                "_current_row_account_matches": lambda *_args: (_ for _ in ()).throw(
                    AssertionError("fast bank path must not use clipboard account verification")
                ),
                "_prepare_fast_bank_management_coordinates": lambda: True,
                "management_bank_coordinate_fallback_rows": fallback_rows,
                "_bank_management_visible": (
                    lambda: full_scan_calls.append("full-management-snapshot") or (False, {})
                ),
                "_fail_form": lambda message: (_ for _ in ()).throw(RuntimeError(message)),
                "time": SimpleNamespace(sleep=lambda _seconds: None),
                "mgmt_commit_wait": 0.08,
                "_double_click_form_xy": lambda *_args, **_kwargs: None,
                "summary_x": 970,
                "mgmt_summary_open_wait": 0.1,
                "self": SimpleNamespace(logger=_FakeLogger()),
            },
        )

        assert loaded["_ensure_bank_management_row"](
            total_rows,
            671,
            "보통예금",
        ) == 671
        assert fallback_rows == {total_rows}
        assert full_scan_calls == []


def test_bank_account_verification_retries_at_account_cell_center():
    clipboard = {"value": "original clipboard"}
    active_x = {"value": None}
    clicks = []

    def _click(x, y, label, **_kwargs):
        active_x["value"] = x
        clicks.append((x, y, label))

    def _hotkey(*keys):
        if keys == ("ctrl", "c"):
            clipboard["value"] = (
                "보통예금" if active_x["value"] == 295 else "6월 수시결제 - 신한은행"
            )

    loaded = _load_nested_functions(
        "_current_row_account_matches",
        namespace={
            "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")).lower(),
            "account_x": 229,
            "erp_rows": [],
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "pyperclip": SimpleNamespace(
                paste=lambda: clipboard["value"],
                copy=lambda value: clipboard.update(value=value),
            ),
            "pyautogui": SimpleNamespace(hotkey=_hotkey),
            "_click_form_xy": _click,
            "time": SimpleNamespace(sleep=lambda _seconds: None),
            "mgmt_key_wait": 0.05,
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    assert loaded["_current_row_account_matches"](210, 691, "보통예금") is True
    assert [event[0] for event in clicks] == [229, 295]
    assert clipboard["value"] == "original clipboard"


def test_bank_account_verification_accepts_only_the_expected_row_summary():
    for copied_text, expected in (
        ("6월 수시결제 - 신한은행\r\n", True),
        ("6월 수시결제 - 지엔지하이텍(GN023)", False),
    ):
        clipboard = {"value": "original clipboard"}

        def _hotkey(*keys):
            if keys == ("ctrl", "c"):
                clipboard["value"] = copied_text

        loaded = _load_nested_functions(
            "_current_row_account_matches",
            namespace={
                "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")).lower(),
                "account_x": 229,
                "erp_rows": ["보통예금\t\t0\t1000\t6월 수시결제 - 신한은행"],
                "os": SimpleNamespace(getenv=lambda _name, default=None: default),
                "pyperclip": SimpleNamespace(
                    paste=lambda: clipboard["value"],
                    copy=lambda value: clipboard.update(value=value),
                ),
                "pyautogui": SimpleNamespace(hotkey=_hotkey),
                "_click_form_xy": lambda *_args, **_kwargs: None,
                "time": SimpleNamespace(sleep=lambda _seconds: None),
                "mgmt_key_wait": 0.05,
                "self": SimpleNamespace(logger=_FakeLogger()),
            },
        )

        assert loaded["_current_row_account_matches"](1, 691, "보통예금") is expected
        assert clipboard["value"] == "original clipboard"


def test_fast_bank_fill_skips_second_uia_scan_and_selects_account_once():
    for total_rows in (230, 300):
        events = []
        active_context = {"row_no": None}
        loaded = _load_nested_functions(
            "_fill_explicit_management_items",
            namespace={
                "management_active_row_context": active_context,
                "form_data": {"cash_processing_enabled": True},
                "_uncheck_cash_processing": lambda row_no: events.append(("uncheck", row_no)),
                "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")).lower(),
                "_management_grid_snapshot": lambda: (_ for _ in ()).throw(
                    AssertionError("fast bank path must not enumerate the full UIA tree")
                ),
                "management_bank_coordinate_fallback_rows": {total_rows},
                "_management_value_xy": lambda item_name, fallback_y: {
                    "계좌번호": (1118, 797),
                    "금융기관지점": (1118, 817),
                }[item_name],
                "finance_vendor_entry_state": {"f9_seeded": True},
                "finance_vendor_paste_settle_wait": 0.10,
                "finance_vendor_commit_settle_wait": 0.16,
                "_seed_vendor_by_number_f9": lambda *_args, **_kwargs: True,
                "_input_vendor_by_number_keyboard": lambda *_args, **_kwargs: True,
                "_input_bank_account_by_popup": lambda *args, **kwargs: (
                    events.append(("bank-select", args, kwargs)) or True
                ),
                "_input_value_xy": lambda *args, **kwargs: events.append(("input", args, kwargs)),
                "re": re,
                "self": SimpleNamespace(logger=_FakeLogger()),
                "row_no": total_rows,
                "account_key": "보통예금",
                "explicit_management": {
                    "계좌번호": "140-000-948562",
                    "금융기관지점": "신한 수원금융센터",
                    "거래처": "",
                },
            },
        )

        loaded["_fill_explicit_management_items"]()

        assert active_context["row_no"] == total_rows
        assert [event[0] for event in events] == ["bank-select"]
        assert events[0][1] == (
            1118,
            797,
            "140-000-948562",
            "신한 수원금융센터",
            f"{total_rows}행 계좌번호",
        )


def test_bank_fill_forces_account_selection_before_auto_filled_branch():
    events = []
    loaded = _load_nested_functions(
        "_fill_explicit_management_items",
        namespace={
            "management_active_row_context": {"row_no": None},
            "form_data": {"cash_processing_enabled": True},
            "_uncheck_cash_processing": lambda *_args, **_kwargs: None,
            "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")).lower(),
            "_management_grid_snapshot": lambda: {
                "label_norms": {"계좌번호", "금융기관지점"},
                "labels": ["계좌번호", "금융기관지점"],
            },
            "management_bank_coordinate_fallback_rows": set(),
            "_management_value_xy": lambda item_name, fallback_y: (1118, 797),
            "finance_vendor_entry_state": {"f9_seeded": True},
            "finance_vendor_paste_settle_wait": 0.10,
            "finance_vendor_commit_settle_wait": 0.16,
            "_seed_vendor_by_number_f9": lambda *_args, **_kwargs: True,
            "_input_finance_vendor_code_xy": lambda *_args, **_kwargs: True,
            "_input_vendor_by_number_keyboard": lambda *_args, **_kwargs: True,
            "_input_bank_account_by_popup": lambda *args, **kwargs: (
                events.append(("bank-select", args, kwargs)) or True
            ),
            "_input_value_xy": lambda *args, **kwargs: events.append(
                ("forbidden-direct-input", args, kwargs)
            ),
            "re": re,
            "self": SimpleNamespace(logger=_FakeLogger()),
            "row_no": 210,
            "account_key": "보통예금",
            # Deliberately reverse the payload order.  The account selector must
            # still run first and the branch must never be entered directly.
            "explicit_management": {
                "금융기관지점": "신한 수원금융센터",
                "계좌번호": "140-000-948562",
                "거래처": "",
            },
        },
    )

    loaded["_fill_explicit_management_items"]()

    assert [event[0] for event in events] == ["bank-select"]
    assert events[0][1][2:4] == (
        "140-000-948562",
        "신한 수원금융센터",
    )


def test_bank_fill_rejects_branch_without_account_number():
    loaded = _load_nested_functions(
        "_fill_explicit_management_items",
        namespace={
            "management_active_row_context": {"row_no": None},
            "form_data": {"cash_processing_enabled": True},
            "_uncheck_cash_processing": lambda *_args, **_kwargs: None,
            "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")).lower(),
            "_management_grid_snapshot": lambda: {
                "label_norms": {"계좌번호", "금융기관지점"},
                "labels": ["계좌번호", "금융기관지점"],
            },
            "management_bank_coordinate_fallback_rows": set(),
            "_management_value_xy": lambda *_args, **_kwargs: (1118, 797),
            "finance_vendor_entry_state": {"f9_seeded": True},
            "finance_vendor_paste_settle_wait": 0.10,
            "finance_vendor_commit_settle_wait": 0.16,
            "_seed_vendor_by_number_f9": lambda *_args, **_kwargs: True,
            "_input_finance_vendor_code_xy": lambda *_args, **_kwargs: True,
            "_input_vendor_by_number_keyboard": lambda *_args, **_kwargs: True,
            "_input_bank_account_by_popup": lambda *_args, **_kwargs: True,
            "_input_value_xy": lambda *_args, **_kwargs: None,
            "re": re,
            "self": SimpleNamespace(logger=_FakeLogger()),
            "row_no": 210,
            "account_key": "보통예금",
            "explicit_management": {"금융기관지점": "신한 수원금융센터"},
        },
    )

    with pytest.raises(RuntimeError, match="보통예금 계좌번호가 없어"):
        loaded["_fill_explicit_management_items"]()


def test_bank_account_result_matches_account_and_branch_on_same_row():
    class WhiteImage:
        size = (600, 30)

        @staticmethod
        def getpixel(_point):
            return (255, 255, 255)

    popup_rect = _FakeRect(843, 540, 1743, 1040)
    account = _FakeControl(
        "140-000-948562",
        "Text",
        _FakeRect(900, 724, 1073, 744),
    )
    branch = _FakeControl(
        "신한 수원금융센터",
        "Text",
        _FakeRect(1242, 724, 1413, 744),
    )
    loaded = _load_nested_functions(
        "_bank_account_result_target",
        namespace={
            "_vendor_popup_rect": lambda _popup: popup_rect,
            "_visible_vendor_popup_controls": lambda _popup: [account, branch],
            "_direct_vendor_popup_text": lambda ctrl: [ctrl.window_text()],
            "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")).lower(),
            "pyautogui": SimpleNamespace(screenshot=lambda **_kwargs: WhiteImage()),
            "re": re,
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )
    target = loaded["_bank_account_result_target"]

    assert target({}, "140-000-948562", "신한 수원금융센터") == (
        986,
        734,
        "exact-uia",
    )
    assert target({}, "140-000-948562", "다른 금융기관지점") is None


def test_internal_bank_account_popup_uses_dialog_specific_mdi_signature():
    main = _FakeControl("대승", "Window", _FakeRect(0, 0, 1920, 1040))
    popup = main.add(
        _FakeControl("", "Pane", _FakeRect(843, 540, 1743, 1015))
    )
    popup.add(_FakeControl("계좌", "Text", _FakeRect(860, 545, 940, 570)))
    popup.add(_FakeControl("계좌번호", "Text", _FakeRect(900, 680, 1060, 700)))
    popup.add(_FakeControl("계좌명", "Text", _FakeRect(1060, 680, 1220, 700)))
    popup.add(
        _FakeControl("금융기관지점명", "Text", _FakeRect(1220, 680, 1400, 700))
    )
    popup.add(_FakeControl("계좌번호", "ComboBox", _FakeRect(860, 585, 1010, 615)))
    popup.add(_FakeControl("", "Edit", _FakeRect(1010, 585, 1600, 615)))
    loaded = _load_nested_functions(
        "_find_internal_bank_account_popup",
        namespace={
            "main_win": main,
            "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")).lower(),
            "_direct_vendor_popup_text": lambda ctrl: [
                re.sub(r"\s+", "", str(ctrl.window_text() or "")).lower()
            ],
            "_main_rect": lambda: main.rectangle(),
            "_vendor_control_identity": lambda ctrl: ("handle", ctrl.handle),
            "_vendor_popup_context": lambda root, rect, source: {
                "root": root,
                "rect": rect,
                "source": source,
            },
            "_visible_vendor_popup_controls": lambda candidate, control_type=None, top_band=False: [
                ctrl
                for ctrl in candidate["root"].descendants()
                if not control_type or ctrl.element_info.control_type == control_type
            ],
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    result = loaded["_find_internal_bank_account_popup"]()

    assert result["root"] is popup
    assert result["rect"] is popup.rectangle()
    assert result["source"] == "bank-account-internal-uia"


def test_internal_bank_account_popup_rejects_normal_management_labels():
    main = _FakeControl("대승", "Window", _FakeRect(0, 0, 1920, 1040))
    lower_form = main.add(
        _FakeControl("", "Pane", _FakeRect(60, 700, 1850, 1000))
    )
    lower_form.add(_FakeControl("계좌번호", "Text", _FakeRect(700, 720, 850, 745)))
    lower_form.add(
        _FakeControl("금융기관지점", "Text", _FakeRect(700, 745, 850, 770))
    )
    lower_form.add(_FakeControl("거래처", "Text", _FakeRect(700, 770, 850, 795)))
    loaded = _load_nested_functions(
        "_find_internal_bank_account_popup",
        namespace={
            "main_win": main,
            "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")).lower(),
            "_direct_vendor_popup_text": lambda ctrl: [
                re.sub(r"\s+", "", str(ctrl.window_text() or "")).lower()
            ],
            "_main_rect": lambda: main.rectangle(),
            "_vendor_control_identity": lambda ctrl: ("handle", ctrl.handle),
            "_vendor_popup_context": lambda root, rect, source: {
                "root": root,
                "rect": rect,
                "source": source,
            },
            "_visible_vendor_popup_controls": lambda *_args, **_kwargs: [],
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    assert loaded["_find_internal_bank_account_popup"]() is None


def test_bank_account_popup_falls_back_to_internal_mdi_detector():
    popup_rect = _FakeRect(843, 540, 1743, 1015)
    popup = {
        "root": object(),
        "rect": popup_rect,
        "source": "bank-account-internal-uia",
    }
    loaded = _load_nested_functions(
        "_find_bank_account_popup",
        namespace={
            "Desktop": lambda **_kwargs: SimpleNamespace(windows=lambda: []),
            "_find_internal_bank_account_popup": lambda: popup,
            "_vendor_popup_rect": lambda candidate: candidate["rect"],
            "time": SimpleNamespace(time=lambda: 100.0, sleep=lambda _seconds: None),
            "re": re,
            "self": SimpleNamespace(erp_process_pid=243, logger=_FakeLogger()),
        },
    )

    assert loaded["_find_bank_account_popup"](timeout=0.0) is popup


def test_bank_account_input_runs_fixed_sequence_without_popup_precheck():
    events = []

    def press(key, presses=1, **_kwargs):
        events.append(("press", key, presses))

    loaded = _load_nested_functions(
        "_input_bank_account_by_popup",
        namespace={
            "_click_form_xy": lambda *_args, **_kwargs: events.append(("click",)),
            "_release_modifiers": lambda *_args, **_kwargs: None,
            "_management_value_visual_ink": lambda *_args: (12, 4, 6, 14),
            "_force_english_ime": lambda *_args, **_kwargs: None,
            "_save_management_failure_screenshot": lambda *_args, **_kwargs: "",
            "pyautogui": SimpleNamespace(
                press=press,
                write=lambda value, **_kwargs: events.append(("write", value)),
            ),
            "bank_account_popup_state": {
                "opened": False,
                "closed": True,
                "source": "",
            },
            "mgmt_key_wait": 0.1,
            "mgmt_commit_wait": 0.16,
            "mgmt_click_wait": 0.1,
            "mgmt_focus_wait": 0.1,
            "vendor_popup_open_wait": 0.1,
            "vendor_popup_search_wait": 0.1,
            "ERP_FORM_WAIT": 0.1,
            "os": __import__("os"),
            "re": re,
            "time": SimpleNamespace(sleep=lambda _seconds: None),
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    assert loaded["_input_bank_account_by_popup"](
        1118,
        756,
        "140-000-948562",
        "신한 수원금융센터",
        "210행 계좌번호",
    ) is True
    assert events == [
        ("click",),
        ("press", "f9", 1),
        ("write", "140-000-948562"),
        ("press", "tab", 4),
        ("press", "up", 2),
        ("press", "tab", 3),
        ("press", "enter", 2),
    ]
    assert loaded["bank_account_popup_state"]["closed"] is True


def test_bank_account_input_requires_auto_filled_branch_after_sequence():
    pressed = []
    state = {"opened": False, "closed": True, "source": ""}
    loaded = _load_nested_functions(
        "_input_bank_account_by_popup",
        namespace={
            "_click_form_xy": lambda *_args, **_kwargs: None,
            "_release_modifiers": lambda *_args, **_kwargs: None,
            "_management_value_visual_ink": lambda *_args: (0, 0, 0, 0),
            "_force_english_ime": lambda *_args, **_kwargs: None,
            "_save_management_failure_screenshot": lambda *_args, **_kwargs: "",
            "pyautogui": SimpleNamespace(
                press=lambda key, **_kwargs: pressed.append(key),
                write=lambda *_args, **_kwargs: None,
            ),
            "bank_account_popup_state": state,
            "mgmt_key_wait": 0.1,
            "mgmt_commit_wait": 0.16,
            "mgmt_click_wait": 0.1,
            "mgmt_focus_wait": 0.1,
            "vendor_popup_open_wait": 0.1,
            "vendor_popup_search_wait": 0.1,
            "ERP_FORM_WAIT": 0.1,
            "os": __import__("os"),
            "re": re,
            "time": SimpleNamespace(sleep=lambda _seconds: None),
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    with pytest.raises(RuntimeError, match="금융기관지점 자동입력 화면"):
        loaded["_input_bank_account_by_popup"](
            1118,
            756,
            "140-000-948562",
            "신한 수원금융센터",
            "210행 계좌번호",
        )

    assert pressed == ["f9", "tab", "up", "tab", "enter"]
    assert state == {
        "opened": True,
        "closed": False,
        "source": "bank-account-f9-command",
    }


def test_bank_account_popup_uses_account_number_keyboard_sequence():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    helper_start = source.index("def _input_bank_account_by_popup")
    helper_end = source.index("def _input_vendor_value_xy", helper_start)
    helper = source[helper_start:helper_end]
    expected_order = [
        "_click_form_xy",
        'pyautogui.press("f9")',
        "pyautogui.write(account_no",
        'pyautogui.press("tab", presses=4',
        'pyautogui.press("up", presses=2',
        'pyautogui.press("tab", presses=3',
        'pyautogui.press("enter", presses=2',
    ]
    positions = [helper.index(token) for token in expected_order]

    assert positions == sorted(positions)
    assert "Tab 4 → Up 2 → Tab 3 → Enter 2" in helper
    assert "_bank_main_window_visual_snapshot" not in helper
    assert "_bank_visual_change_ratio" not in helper
    assert "pyautogui.hotkey" not in helper
    # 계좌 검색칸은 VK_PACKET/Ctrl+V를 모두 무시하므로 물리 키 + IME 영문
    # 강제 조합만 사용한다.
    assert "pyautogui.write(account_no" in helper
    assert "_force_english_ime(label)" in helper
    assert "_type_vendor_code(account_no" not in helper
    assert "_find_bank_account_popup" not in helper
    assert "_wait_bank_account_popup_closed" not in helper
    assert "_input_value_xy" not in helper
    assert "계좌번호 직접 확정" not in helper


def test_management_snapshot_caches_cash_processing_checkbox_once():
    class _FakeCheckBox(_FakeControl):
        def get_toggle_state(self):
            return 0

    checkbox = _FakeCheckBox(
        "출납처리여부",
        "CheckBox",
        _FakeRect(370, 750, 520, 790),
        automation_id="Check1",
    )
    loaded = _load_nested_functions(
        "_management_grid_snapshot",
        namespace={
            "_main_rect": lambda: _FakeRect(0, 0, 1600, 900),
            "_iter_visible": lambda: [checkbox],
            "_control_text": lambda ctrl: ctrl.window_text(),
            "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")).lower(),
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "pyautogui": SimpleNamespace(screenshot=lambda **_kwargs: None),
            "self": SimpleNamespace(logger=SimpleNamespace(debug=lambda *_args: None)),
        },
    )

    snapshot = loaded["_management_grid_snapshot"]()

    assert snapshot["cash_processing_checkbox"] is checkbox


def test_management_snapshot_caches_nameless_gdi_check1_by_lower_form_geometry():
    class _FakeCheckBox(_FakeControl):
        def get_toggle_state(self):
            return 1

    viewport = _FakeControl(
        "",
        "Custom",
        _FakeRect(60, 210, 1450, 718),
        automation_id="SS_Row",
    )
    scrollbar = _FakeControl(
        "",
        "ScrollBar",
        _FakeRect(60, 703, 1450, 718),
    )
    unrelated_top_check1 = _FakeCheckBox(
        "",
        "CheckBox",
        _FakeRect(260, 120, 430, 150),
        automation_id="Check1",
    )
    cash_checkbox = _FakeCheckBox(
        "",
        "CheckBox",
        _FakeRect(300, 716, 470, 746),
        automation_id="Check1",
    )
    loaded = _load_nested_functions(
        "_management_grid_snapshot",
        namespace={
            "_main_rect": lambda: _FakeRect(0, 0, 1600, 900),
            "_iter_visible": lambda: [
                unrelated_top_check1,
                viewport,
                scrollbar,
                cash_checkbox,
            ],
            "_control_text": lambda ctrl: ctrl.window_text(),
            "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")).lower(),
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "pyautogui": SimpleNamespace(screenshot=lambda **_kwargs: None),
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    snapshot = loaded["_management_grid_snapshot"]()

    assert snapshot["cash_processing_checkbox"] is cash_checkbox
    assert snapshot["voucher_clip_bottom_abs"] == 703


def test_fast_cash_processing_check_reuses_cached_control_without_descendants():
    for initial_state, expected_clicks in ((0, 0), (1, 1)):
        class _CachedCheckBox:
            def __init__(self):
                self.click_count = 0

            def get_toggle_state(self):
                return initial_state

            def click_input(self):
                self.click_count += 1

        checkbox = _CachedCheckBox()
        descendant_calls = []
        loaded = _load_nested_functions(
            "_uncheck_cash_processing",
            namespace={
                "skip_visible_row_scan": True,
                "management_grid_ready_state": {
                    "snapshot": {"cash_processing_checkbox": checkbox}
                },
                "_fail_form": lambda message: (_ for _ in ()).throw(RuntimeError(message)),
                "main_win": SimpleNamespace(
                    descendants=lambda **_kwargs: descendant_calls.append("descendants")
                ),
                "time": SimpleNamespace(sleep=lambda _seconds: None),
                "ERP_FORM_WAIT": 0.1,
                "_click_form_xy": lambda *_args, **_kwargs: None,
                "self": SimpleNamespace(logger=_FakeLogger()),
            },
        )

        loaded["_uncheck_cash_processing"](210)

        assert checkbox.click_count == expected_clicks
        assert descendant_calls == []


def test_fast_cash_processing_missing_or_stale_cache_continues_without_blind_click():
    class _StaleCheckBox:
        def get_toggle_state(self):
            raise RuntimeError("stale UIA element")

    for cached_checkbox in (None, _StaleCheckBox()):
        fail_calls = []
        descendant_calls = []
        coordinate_clicks = []
        loaded = _load_nested_functions(
            "_uncheck_cash_processing",
            namespace={
                "skip_visible_row_scan": True,
                "management_grid_ready_state": {
                    "snapshot": {"cash_processing_checkbox": cached_checkbox}
                },
                "_fail_form": lambda message: fail_calls.append(message),
                "main_win": SimpleNamespace(
                    descendants=lambda **_kwargs: descendant_calls.append("descendants")
                ),
                "time": SimpleNamespace(sleep=lambda _seconds: None),
                "ERP_FORM_WAIT": 0.1,
                "_click_form_xy": lambda *args, **kwargs: coordinate_clicks.append(
                    (args, kwargs)
                ),
                "self": SimpleNamespace(logger=_FakeLogger()),
            },
        )

        loaded["_uncheck_cash_processing"](1)

        assert fail_calls == []
        assert descendant_calls == []
        assert coordinate_clicks == []


def test_management_snapshot_caches_empty_text_voucher_viewport_for_fast_boundary():
    viewport = _FakeControl(
        "",
        "Custom",
        _FakeRect(60, 210, 1450, 783),
        automation_id="SS_Row",
    )
    scrollbar = _FakeControl(
        "",
        "ScrollBar",
        _FakeRect(60, 703, 1450, 718),
    )
    loaded = _load_nested_functions(
        "_management_grid_snapshot",
        namespace={
            "_main_rect": lambda: _FakeRect(0, 0, 1600, 900),
            "_iter_visible": lambda: [viewport, scrollbar],
            "_control_text": lambda ctrl: ctrl.window_text(),
            "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")),
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    snapshot = loaded["_management_grid_snapshot"]()

    assert snapshot["voucher_viewport_rect"] is viewport.rectangle()
    assert snapshot["voucher_clip_bottom_abs"] == 703
    assert snapshot["header_label"] is None
    assert snapshot["header_value"] is None


def _visible_voucher_snapshot(
    *,
    first_logical_row: int,
    full_row_count: int,
    clipped_provider_rect: bool = False,
):
    first_y = 231
    pitch = 20
    last_full_y = first_y + ((full_row_count - 1) * pitch)
    clip_bottom = last_full_y + 12
    controls = [
        _FakeControl(
            "",
            "Custom",
            _FakeRect(60, 210, 1450, clip_bottom + 80),
            automation_id="SS_Row",
        ),
        _FakeControl(
            "관리항목",
            "Header",
            _FakeRect(620, clip_bottom, 760, clip_bottom + 20),
        ),
    ]
    for slot in range(full_row_count):
        logical_row = first_logical_row + slot
        center_y = first_y + (slot * pitch)
        controls.append(
            _FakeControl(
                f"{logical_row:03d}",
                "Text",
                _FakeRect(90, center_y - 8, 135, center_y + 8),
            )
        )

    partial_row = first_logical_row + full_row_count
    partial_center = first_y + (full_row_count * pitch)
    if clipped_provider_rect:
        partial_rect = _FakeRect(90, clip_bottom - 5, 135, clip_bottom - 1)
    else:
        partial_rect = _FakeRect(90, partial_center - 13, 135, partial_center + 8)
    controls.append(_FakeControl(f"{partial_row:03d}", "Text", partial_rect))

    loaded = _load_nested_functions(
        "_median_number",
        "_fully_visible_voucher_row_snapshot",
        namespace={
            "_main_rect": lambda: _FakeRect(0, 0, 1600, 900),
            "_iter_visible": lambda: controls,
            "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")),
            "_control_text": lambda ctrl: ctrl.window_text(),
            "first_row_y": first_y,
            "row_height": pitch,
            "re": re,
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )
    return loaded["_fully_visible_voucher_row_snapshot"]()


def test_uia_geometry_uses_row_24_as_last_full_row():
    snapshot = _visible_voucher_snapshot(first_logical_row=1, full_row_count=24)

    assert snapshot["last_full_y"] == 691
    assert snapshot["scroll_anchor_y"] == 671
    assert snapshot["rows"][24] == 691
    assert 25 not in snapshot["rows"]
    assert len(snapshot["slot_ys"]) == 24


def test_uia_geometry_uses_row_26_when_viewport_expands():
    snapshot = _visible_voucher_snapshot(first_logical_row=1, full_row_count=26)

    assert snapshot["last_full_y"] == 731
    assert snapshot["scroll_anchor_y"] == 711
    assert snapshot["rows"][26] == 731
    assert 27 not in snapshot["rows"]
    assert len(snapshot["slot_ys"]) == 26


def test_uia_geometry_excludes_provider_clipped_partial_row():
    snapshot = _visible_voucher_snapshot(
        first_logical_row=1,
        full_row_count=24,
        clipped_provider_rect=True,
    )

    assert snapshot["last_full_y"] == 691
    assert 25 not in snapshot["rows"]


def test_uia_geometry_maps_scrolled_logical_row_to_dynamic_bottom():
    snapshot = _visible_voucher_snapshot(first_logical_row=2, full_row_count=24)

    assert snapshot["rows"][25] == snapshot["last_full_y"] == 691
    assert 26 not in snapshot["rows"]


def test_uia_geometry_supports_unnamed_data_items_with_grid_rows():
    first_y = 231
    pitch = 20
    clip_bottom = 703
    controls = [
        _FakeControl(
            "",
            "Custom",
            _FakeRect(60, 210, 1450, clip_bottom + 80),
            automation_id="SS_Row",
        ),
        _FakeControl("관리항목", "Header", _FakeRect(620, clip_bottom, 760, clip_bottom + 20)),
    ]
    for row_no in range(1, 25):
        center_y = first_y + ((row_no - 1) * pitch)
        controls.append(
            _FakeControl(
                "",
                "DataItem",
                _FakeRect(150, center_y - 8, 500, center_y + 8),
                grid_row=row_no - 1,
            )
        )
    controls.append(
        _FakeControl(
            "",
            "DataItem",
            _FakeRect(150, clip_bottom - 5, 500, clip_bottom - 1),
            grid_row=24,
        )
    )
    controls.append(
        _FakeControl(
            "",
            "DataItem",
            _FakeRect(100, 220, 1400, 650),
            grid_row=999,
        )
    )

    loaded = _load_nested_functions(
        "_median_number",
        "_fully_visible_voucher_row_snapshot",
        namespace={
            "_main_rect": lambda: _FakeRect(0, 0, 1600, 900),
            "_iter_visible": lambda: controls,
            "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")),
            "_control_text": lambda ctrl: ctrl.window_text(),
            "first_row_y": first_y,
            "row_height": pitch,
            "re": re,
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    snapshot = loaded["_fully_visible_voucher_row_snapshot"]()

    assert snapshot["last_full_y"] == 691
    assert snapshot["rows"][24] == 691
    assert snapshot["has_exact_row_numbers"] is False
    assert snapshot["has_logical_row_numbers"] is True
    assert 25 not in snapshot["rows"]
    assert 1000 not in snapshot["rows"]


def test_uia_exact_row_labels_override_relative_data_item_grid_rows_after_scroll():
    first_y = 231
    pitch = 20
    clip_bottom = 703
    controls = [
        _FakeControl(
            "",
            "Custom",
            _FakeRect(60, 210, 1450, clip_bottom + 80),
            automation_id="SS_Row",
        ),
        _FakeControl("관리항목", "Header", _FakeRect(620, clip_bottom, 760, clip_bottom + 20)),
    ]
    for slot in range(24):
        logical_row = slot + 2
        center_y = first_y + (slot * pitch)
        controls.append(
            _FakeControl(
                f"{logical_row:03d}",
                "Text",
                _FakeRect(90, center_y - 8, 135, center_y + 8),
            )
        )
        for column in range(5):
            controls.append(
                _FakeControl(
                    "",
                    "DataItem",
                    _FakeRect(150 + (column * 180), center_y - 8, 320 + (column * 180), center_y + 8),
                    grid_row=slot,
                )
            )
    controls.append(
        _FakeControl("026", "Text", _FakeRect(90, clip_bottom - 5, 135, clip_bottom - 1))
    )

    loaded = _load_nested_functions(
        "_median_number",
        "_fully_visible_voucher_row_snapshot",
        namespace={
            "_main_rect": lambda: _FakeRect(0, 0, 1600, 900),
            "_iter_visible": lambda: controls,
            "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")),
            "_control_text": lambda ctrl: ctrl.window_text(),
            "first_row_y": first_y,
            "row_height": pitch,
            "re": re,
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    snapshot = loaded["_fully_visible_voucher_row_snapshot"]()

    assert snapshot["rows"][25] == snapshot["last_full_y"] == 691
    assert 24 in snapshot["rows"]
    assert 1 not in snapshot["rows"]
    assert snapshot["has_exact_row_numbers"] is True


def test_dynamic_next_row_enters_scroll_mode_before_the_lookahead_row():
    loaded = _load_nested_functions(
        "_next_visible_voucher_row_y",
        namespace={"row_height": 20},
    )
    next_y = loaded["_next_visible_voucher_row_y"]

    row_24_snapshot = _visible_voucher_snapshot(first_logical_row=1, full_row_count=24)
    assert next_y(651, 23, row_24_snapshot) == (671, False)
    assert next_y(671, 24, row_24_snapshot) == (691, True)

    row_26_snapshot = _visible_voucher_snapshot(first_logical_row=1, full_row_count=26)
    assert next_y(691, 25, row_26_snapshot) == (711, False)
    assert next_y(711, 26, row_26_snapshot) == (731, True)


def test_initial_dynamic_snapshot_stops_if_grid_is_already_scrolled():
    scrolled = _visible_voucher_snapshot(first_logical_row=2, full_row_count=24)
    loaded = _load_nested_functions(
        "_validate_initial_voucher_row_snapshot",
        namespace={
            "_fail_form": lambda message: (_ for _ in ()).throw(RuntimeError(message)),
        },
    )

    try:
        loaded["_validate_initial_voucher_row_snapshot"](scrolled)
    except RuntimeError as exc:
        assert "001행을 찾지 못했습니다" in str(exc)
    else:
        raise AssertionError("already-scrolled ERP grid must stop before the first row click")


def test_targeted_uia_row_number_prefers_displayed_label_over_grid_item_index():
    calls = []
    conflicting = _FakeControl(
        "230",
        "Text",
        _FakeRect(90, 680, 135, 700),
        grid_row=0,
    )
    desktop = SimpleNamespace(
        from_point=lambda x, y: calls.append((x, y)) or conflicting
    )
    loaded = _load_nested_functions(
        "_uia_voucher_row_number_at_y",
        namespace={
            "_main_rect": lambda: _FakeRect(0, 0, 1600, 900),
            "row_number_x": 112,
            "_control_text": lambda ctrl: ctrl.window_text(),
            "rows_to_fill": 300,
            "initial_snapshot": {"slot_ys": list(range(231, 732, 20))},
            "re": re,
        },
    )

    assert loaded["_uia_voucher_row_number_at_y"](
        desktop,
        691,
        allow_grid_fallback=True,
    ) == 230
    assert calls == [(112, 691)]


def test_targeted_uia_row_number_ignores_short_child_viewport_index():
    parent_label = _FakeControl(
        "230",
        "Text",
        _FakeRect(90, 680, 135, 700),
    )
    viewport_child = parent_label.add(
        _FakeControl(
            "23",
            "DataItem",
            _FakeRect(95, 682, 130, 698),
            grid_row=22,
        )
    )
    desktop = SimpleNamespace(from_point=lambda _x, _y: viewport_child)
    loaded = _load_nested_functions(
        "_uia_voucher_row_number_at_y",
        namespace={
            "_main_rect": lambda: _FakeRect(0, 0, 1600, 900),
            "row_number_x": 112,
            "_control_text": lambda ctrl: ctrl.window_text(),
            "rows_to_fill": 300,
            "initial_snapshot": {"slot_ys": list(range(231, 732, 20))},
            "re": re,
        },
    )

    assert loaded["_uia_voucher_row_number_at_y"](
        desktop,
        691,
        allow_grid_fallback=True,
        expected_row_nos={230},
    ) == 230


def test_initial_point_uia_unavailable_uses_validated_viewport_geometry():
    snapshot = {
        "rows": {
            row_no: 231 + ((row_no - 1) * 20)
            for row_no in range(1, 25)
        },
        "slot_ys": list(range(231, 692, 20)),
    }
    loaded = _load_nested_functions(
        "_initial_voucher_rows_with_geometry_fallback",
        namespace={
            "_targeted_uia_voucher_rows": lambda *_args, **_kwargs: {},
            "_fail_form": lambda message: (_ for _ in ()).throw(
                RuntimeError(message)
            ),
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    rows, point_uia_complete = loaded[
        "_initial_voucher_rows_with_geometry_fallback"
    ](snapshot, {1, 24})

    assert rows == snapshot["rows"]
    assert rows[12] == 451
    assert point_uia_complete is False


def test_initial_geometry_fallback_still_stops_without_target_coordinates():
    loaded = _load_nested_functions(
        "_initial_voucher_rows_with_geometry_fallback",
        namespace={
            "_targeted_uia_voucher_rows": lambda *_args, **_kwargs: {},
            "_fail_form": lambda message: (_ for _ in ()).throw(
                RuntimeError(message)
            ),
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    try:
        loaded["_initial_voucher_rows_with_geometry_fallback"](
            {"rows": {1: 231}, "slot_ys": [231, 251]},
            {1, 2},
        )
    except RuntimeError as exc:
        assert "missing=[2]" in str(exc)
    else:
        raise AssertionError("missing geometry must still stop before ERP input")


def test_targeted_uia_selection_reads_selected_parent_without_descendants():
    parent = _FakeControl(
        "230",
        "DataItem",
        _FakeRect(90, 680, 135, 700),
    )
    parent.iface_selection_item = SimpleNamespace(CurrentIsSelected=True)
    child = parent.add(
        _FakeControl("", "Text", _FakeRect(95, 682, 130, 698))
    )
    child.iface_selection_item = SimpleNamespace(CurrentIsSelected=False)
    calls = []
    desktop = SimpleNamespace(
        from_point=lambda x, y: calls.append((x, y)) or child
    )
    loaded = _load_nested_functions(
        "_uia_voucher_row_selected_at_y",
        namespace={
            "_main_rect": lambda: _FakeRect(0, 0, 1600, 900),
            "row_number_x": 112,
        },
    )

    assert loaded["_uia_voucher_row_selected_at_y"](desktop, 691) is True
    assert calls == [(112, 691)]


def _runtime_calibration_state(snapshot):
    return {
        "snapshot": snapshot,
        "bottom_scroll_mode": False,
        "scroll_anchor_y": None,
        "calibrate_on_focus_row": None,
        "calibrate_after_commit": False,
        "calibration_focus_y": None,
        "calibration_focus_next_y": None,
        "calibration_row_no": len(snapshot.get("slot_ys") or []),
        "scroll_advance_mode": None,
    }


def _load_runtime_navigation(
    state,
    targeted_rows,
    events,
    selected_at_y=None,
    *,
    fast_mode=False,
):
    return _load_nested_functions(
        "_next_visible_voucher_row_y",
        "_set_calibrated_scroll_anchor",
        "_calibrate_focused_last_row",
        "_focus_grid_row",
        "_advance_grid_row",
        namespace={
            "row_geometry_state": state,
            "row_height": 20,
            "sequential_nav": True,
            "skip_visible_row_scan": fast_mode,
            "_targeted_uia_voucher_rows": targeted_rows,
            "_uia_voucher_row_selected_at_y": (
                selected_at_y or (lambda _desktop, _y: False)
            ),
            "Desktop": lambda backend=None: SimpleNamespace(backend=backend),
            "_double_click_form_xy": lambda x, y, label, wait=0: events.append(
                ("double-click", x, y, wait, label)
            ),
            "_click_form_xy": lambda x, y, label, wait=0: events.append(
                ("click", x, y, wait, label)
            ),
            "summary_x": 970,
            "mgmt_summary_open_wait": 0.55,
            "mgmt_key_wait": 0.05,
            "mgmt_commit_wait": 0.08,
            "finance_row_advance_settle_wait": 2.50,
            "pyautogui": SimpleNamespace(
                press=lambda key: events.append(("key", key))
            ),
            "time": SimpleNamespace(
                sleep=lambda seconds: events.append(("sleep", seconds))
            ),
            "_fail_form": lambda message: (_ for _ in ()).throw(
                RuntimeError(message)
            ),
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )


def test_boundary_focus_saves_live_current_and_next_row_map():
    for full_row_count in (24, 26):
        snapshot = _visible_voucher_snapshot(
            first_logical_row=1,
            full_row_count=full_row_count,
        )
        state = _runtime_calibration_state(snapshot)
        state["calibrate_on_focus_row"] = full_row_count
        moved_y = snapshot["last_full_y"] - snapshot["row_pitch"]
        probes = []
        events = []

        def _targeted(_snapshot, targets):
            probes.append(tuple(sorted(targets)))
            return {
                full_row_count: moved_y,
                full_row_count + 1: snapshot["last_full_y"],
            }

        loaded = _load_runtime_navigation(state, _targeted, events)
        assert loaded["_focus_grid_row"](
            full_row_count,
            snapshot["last_full_y"],
        ) == moved_y
        assert probes == [(full_row_count, full_row_count + 1)]
        assert events[0][:4] == (
            "double-click",
            970,
            snapshot["last_full_y"],
            0.55,
        )
        assert state["calibrate_after_commit"] is True
        assert state["calibration_focus_y"] == moved_y
        assert state["calibration_focus_next_y"] == snapshot["last_full_y"]
        assert state["bottom_scroll_mode"] is False


def test_runtime_anchor_branch_a_uses_down_when_enter_did_not_move():
    for full_row_count in (24, 26):
        for total_rows in (230, 300):
            snapshot = _visible_voucher_snapshot(
                first_logical_row=1,
                full_row_count=full_row_count,
            )
            state = _runtime_calibration_state(snapshot)
            state["calibrate_on_focus_row"] = full_row_count
            moved_y = snapshot["last_full_y"] - snapshot["row_pitch"]
            probes = []
            events = []

            def _targeted(_snapshot, targets):
                probes.append(tuple(sorted(targets)))
                if len(probes) < 3:
                    return {
                        full_row_count: moved_y,
                        full_row_count + 1: snapshot["last_full_y"],
                    }
                return {full_row_count + 1: moved_y}

            loaded = _load_runtime_navigation(state, _targeted, events)
            current_y = loaded["_focus_grid_row"](
                full_row_count,
                snapshot["last_full_y"],
            )
            assert loaded["_advance_grid_row"](
                current_y,
                full_row_count + 1,
                management_enter_sent=True,
            ) == moved_y

            assert probes == [
                (full_row_count, full_row_count + 1),
                (full_row_count, full_row_count + 1),
                (full_row_count + 1,),
            ]
            assert [event[0] for event in events] == [
                "double-click",
                "click",
                "key",
                "sleep",
            ]
            assert events[1][1:4] == (970, moved_y, 0.05)
            assert events[2] == ("key", "down")
            assert state["bottom_scroll_mode"] is True
            assert state["scroll_anchor_y"] == moved_y
            assert state["scroll_advance_mode"] == "down"
            assert state["calibrate_after_commit"] is False
            assert total_rows > full_row_count


def test_management_enter_observation_skips_down_for_viewport_or_selection():
    for observation in ("current-row-moved", "next-row-selected"):
        for full_row_count in (24, 26):
            for total_rows in (230, 300):
                snapshot = _visible_voucher_snapshot(
                    first_logical_row=1,
                    full_row_count=full_row_count,
                )
                state = _runtime_calibration_state(snapshot)
                state["calibrate_on_focus_row"] = full_row_count
                moved_y = snapshot["last_full_y"] - snapshot["row_pitch"]
                probes = []
                selected_probes = []
                events = []

                def _targeted(_snapshot, targets):
                    probes.append(tuple(sorted(targets)))
                    if observation == "current-row-moved":
                        if len(probes) == 1:
                            return {full_row_count: snapshot["last_full_y"]}
                        return {
                            full_row_count: moved_y,
                            full_row_count + 1: snapshot["last_full_y"],
                        }
                    return {
                        full_row_count: moved_y,
                        full_row_count + 1: snapshot["last_full_y"],
                    }

                def _selected(_desktop, y):
                    selected_probes.append(y)
                    return observation == "next-row-selected"

                loaded = _load_runtime_navigation(
                    state,
                    _targeted,
                    events,
                    selected_at_y=_selected,
                )
                current_y = loaded["_focus_grid_row"](
                    full_row_count,
                    snapshot["last_full_y"],
                )
                assert loaded["_advance_grid_row"](
                    current_y,
                    full_row_count + 1,
                    management_enter_sent=True,
                ) == snapshot["last_full_y"]

                assert probes == [
                    (full_row_count, full_row_count + 1),
                    (full_row_count, full_row_count + 1),
                ]
                assert selected_probes == [snapshot["last_full_y"]]
                assert [event[0] for event in events] == ["double-click"]
                assert state["bottom_scroll_mode"] is True
                assert state["scroll_anchor_y"] == snapshot["last_full_y"]
                assert state["scroll_advance_mode"] == "enter"
                assert state["calibrate_after_commit"] is False
                assert total_rows > full_row_count


def test_runtime_anchor_branch_b_fixes_last_y_after_down():
    for full_row_count in (24, 26):
        for total_rows in (230, 300):
            snapshot = _visible_voucher_snapshot(
                first_logical_row=1,
                full_row_count=full_row_count,
            )
            state = _runtime_calibration_state(snapshot)
            state["calibrate_on_focus_row"] = full_row_count
            probes = []
            events = []

            def _targeted(_snapshot, targets):
                probes.append(tuple(sorted(targets)))
                if len(probes) < 3:
                    return {full_row_count: snapshot["last_full_y"]}
                return {full_row_count + 1: snapshot["last_full_y"]}

            loaded = _load_runtime_navigation(state, _targeted, events)
            current_y = loaded["_focus_grid_row"](
                full_row_count,
                snapshot["last_full_y"],
            )
            assert loaded["_advance_grid_row"](
                current_y,
                full_row_count + 1,
                management_enter_sent=True,
            ) == snapshot["last_full_y"]

            assert probes == [
                (full_row_count, full_row_count + 1),
                (full_row_count, full_row_count + 1),
                (full_row_count + 1,),
            ]
            assert [event[0] for event in events] == [
                "double-click",
                "click",
                "key",
                "sleep",
            ]
            assert events[1][1:4] == (
                970,
                snapshot["last_full_y"],
                0.05,
            )
            assert state["bottom_scroll_mode"] is True
            assert state["scroll_anchor_y"] == snapshot["last_full_y"]
            assert state["scroll_advance_mode"] == "down"
            assert total_rows > full_row_count


def test_fixed_anchor_reuses_enter_or_down_mode_through_dynamic_total():
    for full_row_count, enter_anchor, down_anchor in (
        (24, 671, 691),
        (26, 711, 731),
    ):
        for total_rows in (230, 300):
            for mode, anchor_y in (("enter", enter_anchor), ("down", down_anchor)):
                snapshot = _visible_voucher_snapshot(
                    first_logical_row=1,
                    full_row_count=full_row_count,
                )
                state = _runtime_calibration_state(snapshot)
                state.update(
                    {
                        "bottom_scroll_mode": True,
                        "scroll_anchor_y": anchor_y,
                        "scroll_advance_mode": mode,
                    }
                )
                events = []
                loaded = _load_runtime_navigation(
                    state,
                    lambda *_args, **_kwargs: {},
                    events,
                )

                current_y = anchor_y
                for next_row_no in range(full_row_count + 1, total_rows + 1):
                    current_y = loaded["_advance_grid_row"](
                        current_y,
                        next_row_no,
                        management_enter_sent=True,
                    )
                    assert current_y == anchor_y

                move_count = total_rows - full_row_count
                if mode == "enter":
                    assert events == []
                else:
                    assert [event[0] for event in events] == [
                        value
                        for _ in range(move_count)
                        for value in ("click", "key", "sleep")
                    ]
                    assert sum(
                        event == ("key", "down") for event in events
                    ) == move_count


def test_fast_geometry_navigation_never_probes_uia_through_dynamic_bank_row():
    # The horizontal splitter can leave a short voucher viewport (for example,
    # 10 rows) or a taller one.  Navigation must use the runtime boundary, not
    # a workstation-specific fixed last-row number.
    for full_row_count in (10, 23, 24, 26):
        for total_rows in (210, 230, 300):
            snapshot = _visible_voucher_snapshot(
                first_logical_row=1,
                full_row_count=full_row_count,
            )
            state = _runtime_calibration_state(snapshot)
            state.update(
                {
                    "calibration_row_no": None,
                    "fixed_boundary_row_no": full_row_count,
                }
            )
            events = []

            def _forbidden_targeted_uia(*_args, **_kwargs):
                raise AssertionError("fast geometry navigation must not probe UIA")

            loaded = _load_runtime_navigation(
                state,
                _forbidden_targeted_uia,
                events,
                fast_mode=True,
            )

            current_y = snapshot["first_y"]
            focused_rows = []
            for row_no in range(1, total_rows + 1):
                current_y = loaded["_focus_grid_row"](row_no, current_y)
                focused_rows.append(row_no)
                if row_no == total_rows:
                    break
                current_y = loaded["_advance_grid_row"](
                    current_y,
                    row_no + 1,
                    management_enter_sent=True,
                )

            assert focused_rows == list(range(1, total_rows + 1))
            assert current_y == snapshot["last_full_y"]
            assert state["bottom_scroll_mode"] is True
            assert state["scroll_anchor_y"] == snapshot["last_full_y"]
            assert state["scroll_advance_mode"] == "down"
            assert sum(event == ("key", "down") for event in events) == total_rows - 1
            # 1행부터 마지막 행까지 모든 행 전환이 동일한 2.50초 대기를
            # 써야 한다(뷰포트 행 0.08초 잔존 금지 — 속도 균일). 최초 경계
            # 전환만 별도 계산이라 나머지 전 구간이 2.50초여야 한다.
            uniform_sleeps = sum(event == ("sleep", 2.50) for event in events)
            assert uniform_sleeps >= total_rows - 2
            assert not any(event == ("sleep", 0.08) for event in events)


def test_fast_geometry_boundary_uses_one_down_even_when_management_enter_was_sent():
    for full_row_count in (10, 23, 24, 26):
        snapshot = _visible_voucher_snapshot(
            first_logical_row=1,
            full_row_count=full_row_count,
        )
        state = _runtime_calibration_state(snapshot)
        state.update(
            {
                "calibration_row_no": None,
                "fixed_boundary_row_no": full_row_count,
            }
        )
        events = []

        loaded = _load_runtime_navigation(
            state,
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("fast geometry boundary must not probe UIA")
            ),
            events,
            fast_mode=True,
        )

        assert loaded["_advance_grid_row"](
            snapshot["last_full_y"],
            full_row_count + 1,
            management_enter_sent=True,
        ) == snapshot["last_full_y"]

        assert [event[0] for event in events] == ["click", "key", "sleep"]
        assert events[0][1:4] == (970, snapshot["last_full_y"], 0.05)
        assert events[1] == ("key", "down")
        # Down 후에는 다음 적요 더블클릭 전에 스크롤이 끝나도록
        # 전용 행 전환 대기를 사용해야 한다(밀림 방지).
        assert events[2] == ("sleep", 2.50)
        assert state["bottom_scroll_mode"] is True
        assert state["scroll_advance_mode"] == "down"


def test_full_runtime_navigation_reaches_dynamic_bank_row_without_gaps():
    for full_row_count in (24, 26):
        for total_rows in (230, 300):
            for scenario in ("branch-a-down", "enter-observed", "branch-b-down"):
                snapshot = _visible_voucher_snapshot(
                    first_logical_row=1,
                    full_row_count=full_row_count,
                )
                state = _runtime_calibration_state(snapshot)
                probes = []
                events = []
                moved_y = snapshot["last_full_y"] - snapshot["row_pitch"]
                pair_probe_count = {"value": 0}

                def _targeted(_snapshot, targets):
                    target_tuple = tuple(sorted(targets))
                    probes.append(target_tuple)
                    if target_tuple == (full_row_count,):
                        return {
                            full_row_count: (
                                moved_y
                                if scenario == "branch-a-down"
                                else snapshot["last_full_y"]
                            )
                        }
                    if target_tuple == (full_row_count + 1,):
                        return {
                            full_row_count + 1: (
                                moved_y
                                if scenario == "branch-a-down"
                                else snapshot["last_full_y"]
                            )
                        }
                    pair_probe_count["value"] += 1
                    pair_call = pair_probe_count["value"]
                    if scenario == "branch-a-down":
                        return {
                            full_row_count: moved_y,
                            full_row_count + 1: snapshot["last_full_y"],
                        }
                    if scenario == "enter-observed":
                        if pair_call == 1:
                            return {full_row_count: snapshot["last_full_y"]}
                        return {
                            full_row_count: moved_y,
                            full_row_count + 1: snapshot["last_full_y"],
                        }
                    return {full_row_count: snapshot["last_full_y"]}

                loaded = _load_runtime_navigation(state, _targeted, events)
                current_y = snapshot["first_y"]
                focused_rows = []
                bank_calls = []

                for row_no in range(1, total_rows + 1):
                    current_y = loaded["_focus_grid_row"](row_no, current_y)
                    focused_rows.append(row_no)
                    if row_no == total_rows:
                        bank_calls.append((row_no, current_y, "보통예금"))
                        break
                    current_y = loaded["_advance_grid_row"](
                        current_y,
                        row_no + 1,
                        management_enter_sent=True,
                    )

                expected_anchor = (
                    moved_y if scenario == "branch-a-down" else snapshot["last_full_y"]
                )
                assert focused_rows == list(range(1, total_rows + 1))
                assert bank_calls == [(total_rows, expected_anchor, "보통예금")]
                assert current_y == expected_anchor
                assert state["scroll_anchor_y"] == expected_anchor
                assert state["scroll_advance_mode"] == (
                    "enter" if scenario == "enter-observed" else "down"
                )
                down_count = sum(event == ("key", "down") for event in events)
                assert down_count == (
                    full_row_count - 2
                    if scenario == "enter-observed"
                    else total_rows - 2
                )


def test_gdi_point_uia_unavailable_uses_enter_geometry_through_dynamic_bank_row():
    for full_row_count in (24, 26):
        for total_rows in (210, 230, 300):
            for probe_mode in ("empty", "unrelated-row"):
                snapshot = _visible_voucher_snapshot(
                    first_logical_row=1,
                    full_row_count=full_row_count,
                )
                state = _runtime_calibration_state(snapshot)
                events = []
                loaded = _load_runtime_navigation(
                    state,
                    (
                        (lambda *_args, **_kwargs: {})
                        if probe_mode == "empty"
                        else (
                            lambda *_args, **_kwargs: {
                                1: snapshot["first_y"]
                            }
                        )
                    ),
                    events,
                )

                current_y = snapshot["first_y"]
                focused_rows = []
                for row_no in range(1, total_rows + 1):
                    current_y = loaded["_focus_grid_row"](row_no, current_y)
                    focused_rows.append(row_no)
                    if row_no == total_rows:
                        break
                    current_y = loaded["_advance_grid_row"](
                        current_y,
                        row_no + 1,
                        management_enter_sent=True,
                    )

                assert focused_rows == list(range(1, total_rows + 1))
                assert current_y == snapshot["last_full_y"]
                assert state["bottom_scroll_mode"] is True
                assert state["scroll_anchor_y"] == snapshot["last_full_y"]
                assert state["scroll_advance_mode"] == "enter"
                assert sum(event == ("key", "down") for event in events) == (
                    full_row_count - 2
                )


def test_management_navigation_always_builds_dynamic_uia_snapshot():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    start = source.index("def _fill_management_items_by_coord")
    end = source.index("def _wait_process_by_name", start)
    helper = source[start:end]

    assert "_fully_visible_voucher_row_snapshot()" in helper
    assert "_validate_initial_voucher_row_snapshot" in helper
    assert '"snapshot": initial_snapshot' in helper
    assert "ERP_MGMT_VISIBLE_ROWS_DEFAULT" not in helper
    assert "ERP_MGMT_GRID_BOTTOM_MARGIN" not in helper
    assert "current_y = max_row_y" not in helper
    assert "row_geometry_state[\"bottom_scroll_mode\"] = True" in helper
    assert "management_enter_sent = bool(" in helper
    assert "management_enter_sent=management_enter_sent" in helper
    assert 'row_geometry_state["scroll_advance_mode"] = str(advance_mode)' in helper


def _fast_visible_voucher_snapshot(
    *,
    full_row_count: int,
    expected_row_no: int | None = None,
    include_header: bool = True,
    include_viewport: bool = False,
    viewport_clip_bottom: int | None = None,
    ready_snapshot_override: dict | None = None,
    main_rect_override: _FakeRect | None = None,
):
    first_y = 231
    pitch = 20
    last_full_y = first_y + ((full_row_count - 1) * pitch)
    clip_bottom = last_full_y + 12
    header = None
    if include_header:
        header = {
            "rect": _FakeRect(620, clip_bottom, 760, clip_bottom + 20),
            "rel_y": clip_bottom + 10,
        }
    forbidden_calls = []
    ready_snapshot = ready_snapshot_override
    if ready_snapshot is None:
        ready_snapshot = {
            "header_label": header,
            "header_value": header,
            "voucher_viewport_rect": (
                _FakeRect(60, 210, 1450, clip_bottom)
                if include_viewport
                else None
            ),
            "voucher_clip_bottom_abs": (
                int(viewport_clip_bottom if viewport_clip_bottom is not None else clip_bottom)
                if include_viewport or viewport_clip_bottom is not None
                else None
            ),
        }
    ready_state = {"snapshot": ready_snapshot}
    main_rect = main_rect_override or _FakeRect(0, 0, 1600, 900)
    loaded = _load_nested_functions(
        "_fast_visible_voucher_row_snapshot",
        namespace={
            "management_grid_ready_state": ready_state,
            "_main_rect": lambda: main_rect,
            "first_row_y": first_y,
            "row_height": pitch,
            "os": SimpleNamespace(getenv=lambda _name, default=None: default),
            "self": SimpleNamespace(logger=_FakeLogger()),
            "_iter_visible": lambda *_args, **_kwargs: forbidden_calls.append("iter-visible"),
            "_fully_visible_voucher_row_snapshot": (
                lambda *_args, **_kwargs: forbidden_calls.append("full-snapshot")
            ),
        },
    )

    snapshot = loaded["_fast_visible_voucher_row_snapshot"](expected_row_no)
    assert forbidden_calls == []
    return snapshot


def test_fast_visible_snapshot_uses_cached_header_for_variable_viewport_height():
    for full_row_count, last_full_y in ((10, 411), (24, 691), (26, 731)):
        snapshot = _fast_visible_voucher_snapshot(full_row_count=full_row_count)

        assert snapshot["slot_ys"] == list(range(231, last_full_y + 1, 20))
        assert snapshot["rows"][1] == 231
        assert snapshot["rows"][full_row_count] == last_full_y
        assert snapshot["last_full_y"] == last_full_y
        assert snapshot["clip_bottom"] == last_full_y + 12
        assert snapshot["row_pitch"] == 20


def test_fast_visible_snapshot_keeps_initial_labels_and_derives_management_gap():
    for full_row_count, expected_row_no, last_full_y in (
        (24, 25, 691),
        (26, 27, 731),
    ):
        snapshot = _fast_visible_voucher_snapshot(
            full_row_count=full_row_count,
            expected_row_no=expected_row_no,
        )

        assert snapshot["rows"][1] == 231
        assert snapshot["rows"][full_row_count] == last_full_y
        assert expected_row_no not in snapshot["rows"]
        assert min(snapshot["rows"]) == 1
        assert max(snapshot["rows"]) == full_row_count
        assert len(snapshot["slot_ys"]) == full_row_count
        assert snapshot["management_value_y"] > snapshot["last_full_y"]
        assert snapshot["last_summary_raise"] == (
            snapshot["management_value_y"] - snapshot["last_full_y"]
        )


def test_fast_visible_snapshot_returns_none_without_cached_management_header():
    assert (
        _fast_visible_voucher_snapshot(
            full_row_count=24,
            include_header=False,
        )
        is None
    )


def test_fast_visible_snapshot_uses_cached_viewport_when_uia_header_text_is_missing():
    snapshot = _fast_visible_voucher_snapshot(
        full_row_count=24,
        include_header=False,
        include_viewport=True,
    )

    assert snapshot["last_full_y"] == 691
    assert snapshot["clip_bottom"] == 703
    assert snapshot["geometry_source"] == "ready-viewport-snapshot"


def test_fast_visible_snapshot_uses_dynamic_gdi_boundary_for_variable_viewport_height():
    for full_row_count, boundary, last_full_y in (
        (10, 423, 411),
        (24, 703, 691),
        (26, 743, 731),
    ):
        visual_snapshot, main_rect, _regions = _synthetic_gdi_visual_snapshot(
            full_row_count
        )
        assert visual_snapshot["voucher_clip_bottom_abs"] == main_rect.top + boundary

        snapshot = _fast_visible_voucher_snapshot(
            full_row_count=full_row_count,
            ready_snapshot_override=visual_snapshot,
            main_rect_override=main_rect,
        )

        assert snapshot["slot_ys"] == list(range(231, last_full_y + 1, 20))
        assert len(snapshot["slot_ys"]) == full_row_count
        assert snapshot["last_full_y"] == last_full_y
        assert snapshot["clip_bottom"] == boundary
        assert snapshot["geometry_source"] == "ready-viewport-snapshot"


def test_fast_visible_snapshot_uses_minimum_of_header_and_scrollbar_boundary():
    snapshot = _fast_visible_voucher_snapshot(
        full_row_count=25,
        include_header=True,
        include_viewport=True,
        viewport_clip_bottom=703,
    )

    assert snapshot["last_full_y"] == 691
    assert len(snapshot["slot_ys"]) == 24
    assert snapshot["geometry_source"] == "ready-header-viewport-snapshot"


def test_fast_snapshot_helper_and_skip_branch_never_run_full_uia_scan():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    assert (
        'management_grid_ready_state["snapshot"] = _wait_for_management_grid_ready('
        in source
    )
    fill_start = source.index("def _fill_management_items_by_coord")
    fill_end = source.index("def _wait_process_by_name", fill_start)
    helper = source[fill_start:fill_end]
    fast_start = helper.index("def _fast_visible_voucher_row_snapshot")
    fast_end = helper.index("def _fully_visible_voucher_row_snapshot", fast_start)
    fast_helper = helper[fast_start:fast_end]

    assert "_iter_visible" not in fast_helper
    assert ".descendants(" not in fast_helper
    assert "_fully_visible_voucher_row_snapshot" not in fast_helper
    assert 'ready_snapshot.get("voucher_clip_bottom_abs")' in fast_helper
    assert "if skip_visible_row_scan:" in helper
    assert '"text clipboard paste"' in source

    wait_start = source.index("def _wait_for_management_grid_ready")
    wait_end = source.index("management_value_xy_cache =", wait_start)
    wait_helper = source[wait_start:wait_end]
    assert "_management_grid_visual_snapshot()" in wait_helper
    assert "_management_grid_snapshot(" not in wait_helper
    assert "stable_visual_count >= stable_required" in wait_helper
    assert '"management_ready": True' in wait_helper
    assert '"ready_source": "gdi-visual-stable"' in wait_helper
    assert '"stable_gdi_ready": True' in wait_helper

    visual_start = source.index("def _management_grid_visual_snapshot")
    visual_end = source.index("def _management_grid_snapshot", visual_start)
    visual_helper = source[visual_start:visual_end]
    assert "_iter_visible" not in visual_helper
    assert "_management_grid_snapshot(" not in visual_helper
    assert "pyautogui.screenshot(" in visual_helper

    initial_branch_start = helper.index("if skip_visible_row_scan:")
    initial_branch_end = helper.index("row_geometry_state =", initial_branch_start)
    initial_branch = helper[initial_branch_start:initial_branch_end]
    fast_call = initial_branch.index("_fast_visible_voucher_row_snapshot()")
    slow_else = initial_branch.index("else:", fast_call)
    full_call = initial_branch.index("_fully_visible_voucher_row_snapshot()", slow_else)

    assert fast_call < slow_else < full_call
    fast_initialization = initial_branch[fast_call:slow_else]
    assert "_targeted_uia_voucher_rows" not in fast_initialization
    assert "_initial_voucher_rows_with_geometry_fallback" not in fast_initialization
    assert 'initial_snapshot.get("rows")' in fast_initialization
    assert '"fixed_boundary_row_no"' in helper

    point_start = helper.index("def _uia_voucher_row_number_at_y")
    point_end = helper.index("if skip_visible_row_scan:", point_start)
    targeted_helper = helper[point_start:point_end]

    assert "Desktop(backend=\"uia\")" in targeted_helper
    assert ".from_point(" in targeted_helper
    assert "_iter_visible" not in targeted_helper
    assert ".descendants(" not in targeted_helper
    assert "_fully_visible_voucher_row_snapshot" not in targeted_helper
    assert "def _refresh_voucher_row_snapshot" not in helper
    assert "for idx in range(rows_to_fill):" in helper
    assert "range(2, 211)" not in helper


def test_rd_viewer_detection_accepts_process_prefix_or_window_title():
    process = SimpleNamespace(
        pid=4321,
        info={"pid": 4321, "name": "RDViewer_64.exe"},
    )
    process_helpers = _load_nested_functions(
        "_find_rd_viewer_process",
        namespace={
            "psutil": SimpleNamespace(process_iter=lambda _attrs: [process]),
        },
    )

    found_process, found_name = process_helpers["_find_rd_viewer_process"]()

    assert found_process is process
    assert found_name == "rdviewer_64.exe"

    viewer_window = SimpleNamespace(
        window_text=lambda: "Report Designer Viewer - 전표",
    )

    def fake_desktop(*, backend):
        windows = [viewer_window] if backend == "win32" else []
        return SimpleNamespace(windows=lambda: windows)

    window_helpers = _load_nested_functions(
        "_find_rd_viewer_window",
        namespace={"Desktop": fake_desktop, "re": re},
    )

    found_window, backend, title = window_helpers["_find_rd_viewer_window"]()

    assert found_window is viewer_window
    assert backend == "win32"
    assert title == "Report Designer Viewer - 전표"


def test_erp_print_retries_existing_button_once_after_short_hotkey_probe():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    start = source.index("def _save_and_open_print_dialog")
    end = source.index("def _setup_by_coordinates_only", start)
    helper = source[start:end]

    hotkey_pos = helper.index("pyautogui.hotkey('ctrl', 'p')")
    first_wait_pos = helper.index("_wait_rd_viewer_ready(", hotkey_pos)
    focus_main_pos = helper.index("main_win.set_focus()", first_wait_pos)
    fallback_pos = helper.index("_click_print_button()", focus_main_pos)
    second_wait_pos = helper.index("_wait_rd_viewer_ready(", fallback_pos)
    viewer_focus_pos = helper.index("_focus_rd_viewer_window(", second_wait_pos)

    assert hotkey_pos < first_wait_pos < focus_main_pos < fallback_pos
    assert fallback_pos < second_wait_pos < viewer_focus_pos
    assert helper.count("_click_print_button()") == 1
    assert 'ERP_PRINT_VIEWER_INITIAL_DETECT_TIMEOUT_SECONDS", "8"' in helper
    assert "viewer_timeout - initial_viewer_timeout" in helper
    assert "ready_hint=viewer_ready" in helper

    process_start = source.index("def _find_rd_viewer_process")
    process_end = source.index("def _find_rd_viewer_window", process_start)
    assert 'name.startswith("rdviewer")' in source[process_start:process_end]

    focus_start = source.index("def _focus_rd_viewer_window")
    focus_end = source.index("def _close_rd_viewer", focus_start)
    focus_helper = source[focus_start:focus_end]
    assert "_find_rd_viewer_window()" in focus_helper
    assert "Application(backend=process_backend).connect(process=int(pid))" in focus_helper


def test_rd_timeout_uploads_runtime_diagnostics_and_screenshot():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    save_start = source.index("def _save_and_open_print_dialog")
    save_end = source.index("def _setup_by_coordinates_only", save_start)
    save_helper = source[save_start:save_end]
    final_timeout = save_helper.index('if not viewer_ready:', save_helper.index("_click_print_button()"))
    immediate_diag = save_helper.index(
        '"전표출력 버튼 클릭 직후"',
        save_helper.index("_click_print_button()"),
    )
    runtime_diag = save_helper.index(
        '_log_print_runtime_delta(\n                        "전표출력 버튼 fallback timeout"',
        final_timeout,
    )
    screenshot = save_helper.index("_save_print_timeout_screenshot()", runtime_diag)
    failure = save_helper.index("전표출력 후 RD Viewer가 감지되지 않아 인쇄를 중단합니다.", screenshot)
    assert immediate_diag < final_timeout < runtime_diag < screenshot < failure

    worker_source = AGENT_WORKER_SOURCE.read_text(encoding="utf-8")
    error_start = worker_source.index("except Exception as exc:")
    error_helper = worker_source[error_start:]
    assert 'f"{job_id}_print_timeout.png"' in error_helper
    assert '"print_screenshot"' in error_helper
    assert "_upload_job_artifact(" in error_helper


def test_resume_print_only_reuses_open_voucher_without_form_input_or_save():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    run_start = source.index("def _run_unlocked")
    setup_start = source.index("def _setup_slip_form", run_start)
    run_helper = source[run_start:setup_start]

    top_level_fallback = run_helper.index("_find_existing_erp_top_level_window(")
    recovery_guard = run_helper.index(
        "if resume_existing_voucher and not confirmed_pid:",
        top_level_fallback,
    )
    fresh_launch = run_helper.index("os.startfile(exe_path)")
    resume_branch = run_helper.index("if resume_existing_voucher:", fresh_launch)
    resume_verify = run_helper.index("self._resume_slip_form_ready(main_win)", resume_branch)
    resume_setup = run_helper.index("self._setup_slip_form(main_win)", resume_branch)
    menu_start = run_helper.index("내비게이션 시작", resume_setup)

    assert top_level_fallback < recovery_guard < fresh_launch < resume_branch < resume_verify < resume_setup < menu_start
    assert "if resume_existing_voucher and not existing_pids:" not in run_helper
    assert "fresh_start = False" in run_helper

    reconnect_start = run_helper.index("candidates = [")
    reconnect_end = run_helper.index("# 메모리가 날아갔으나", reconnect_start)
    reconnect_helper = run_helper[reconnect_start:reconnect_end]
    assert 'self.install_info.get("main_window_title", "")' in reconnect_helper
    for expected_title in ("대승", "일강", "제이엠", "더원"):
        assert f'"{expected_title}"' in reconnect_helper
    install_info_start = source.index("def get_install_info")
    install_info_end = source.index("def get_corp_info", install_info_start)
    assert '"main_window_title"' in source[install_info_start:install_info_end]

    save_start = source.index("def _save_and_open_print_dialog", setup_start)
    coord_start = source.index("def _setup_by_coordinates_only", save_start)
    save_helper = source[save_start:coord_start]
    assert 'if _env_flag("ERP_RESUME_PRINT_ONLY", "0"):' in save_helper
    assert "이미 저장된 현재 전표를 유지하고 Ctrl+S를 생략합니다." in save_helper
    resume_start = save_helper.index("ERP_RESUME_PRINT_ONLY")
    management_start = save_helper.index("ERP_RESUME_MANAGEMENT_SAVE_PRINT", resume_start)
    assert "_save_current_voucher_via_toolbar()" not in save_helper[
        resume_start:management_start
    ]
    assert "pyautogui.hotkey('ctrl', 's')" not in save_helper

    coord_call = source.index("\n            _setup_by_coordinates_only()", coord_start)
    pre_coord = source[coord_start:coord_call]
    resume_print = pre_coord.rindex("if resume_print_only_requested:")
    assert pre_coord.index("_save_and_open_print_dialog()", resume_print) < coord_call - coord_start


def test_resume_print_verifier_requires_slip_identity_and_form_structure():
    verifier = _load_nested_functions(
        "_resume_slip_form_ready",
        namespace={"re": re},
    )["_resume_slip_form_ready"]
    bot = SimpleNamespace(logger=_FakeLogger())
    rect = _FakeRect(0, 0, 1600, 900)

    ready_form = _FakeControl("대승", "Window", rect)
    ready_form.add(_FakeControl("분개전표입력", "Text", rect))
    ready_form.add(_FakeControl("신규", "Button", rect, automation_id="New"))
    ready_form.add(_FakeControl("전표출력", "Button", rect))
    assert verifier(bot, ready_form) is True

    home = _FakeControl("대승 Home", "Window", rect)
    home.add(_FakeControl("신규", "Button", rect, automation_id="New"))
    home.add(_FakeControl("전표출력", "Button", rect))
    assert verifier(bot, home) is False

    identity_only = _FakeControl("FrmAcSlip_GAAP", "Window", rect)
    assert verifier(bot, identity_only) is False


def test_resume_print_guard_structurally_prevents_new_button_click():
    tree = ast.parse(MANAGER_SOURCE.read_text(encoding="utf-8"))
    setup = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_setup_slip_form"
    )

    resume_assignment = next(
        node
        for node in setup.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "resume_existing_voucher" for target in node.targets)
    )
    def has_call(node, *, owner=None, name):
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            func = child.func
            if owner is None and isinstance(func, ast.Name) and func.id == name:
                return True
            if (
                owner is not None
                and isinstance(func, ast.Attribute)
                and func.attr == name
                and isinstance(func.value, ast.Name)
                and func.value.id == owner
            ):
                return True
        return False

    guarded_new = next(
        node
        for node in setup.body
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.UnaryOp)
        and isinstance(node.test.op, ast.Not)
        and isinstance(node.test.operand, ast.Name)
        and node.test.operand.id == "resume_existing_voucher"
        and has_call(node, owner="btn_new", name="click_input")
    )
    resume_output = next(
        node
        for node in setup.body
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Name)
        and node.test.id == "resume_print_only_requested"
        and has_call(node, name="_save_and_open_print_dialog")
    )

    assert resume_assignment.lineno < guarded_new.lineno < resume_output.lineno
    assert not has_call(resume_output, owner="btn_new", name="click_input")


def test_resume_management_reuses_existing_grid_and_runs_normal_management_loop():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    setup_start = source.index("def _setup_slip_form")
    setup_end = source.index("def _all_edits", setup_start)
    setup_helper = source[setup_start:setup_end]

    recovery_start = setup_helper.rindex("if resume_management_save_print:")
    recovery_end = setup_helper.index("if resume_print_only_requested:", recovery_start)
    recovery_branch = setup_helper[recovery_start:recovery_end]
    prepare_call = recovery_branch.index("_prepare_management_recovery_from_first_row()")
    management_call = recovery_branch.index("_fill_management_items_by_coord()")
    save_call = recovery_branch.index("_save_and_open_print_dialog()")

    assert prepare_call < management_call < save_call
    assert "_setup_by_coordinates_only()" not in recovery_branch
    assert "_paste_grid_until_reflected()" not in recovery_branch
    assert "pyautogui.hotkey('ctrl', 'v')" not in recovery_branch


def test_resume_management_prepares_first_row_with_gdi_snapshot_not_full_uia_walk():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    prepare_start = source.index("def _prepare_management_recovery_from_first_row")
    prepare_end = source.index("def _wait_process_by_name", prepare_start)
    prepare_helper = source[prepare_start:prepare_end]

    assert "pyautogui.hotkey('ctrl', 'home')" in prepare_helper
    assert "expected_first_account" in prepare_helper
    assert "expected_first_debit" in prepare_helper
    assert "expected_first_credit" in prepare_helper
    assert "expected_first_summary" in prepare_helper
    assert "1행 전표 식별값 검증" in prepare_helper
    assert "_management_grid_visual_snapshot()" in prepare_helper
    assert 'ready_snapshot["stable_gdi_ready"]' not in prepare_helper
    assert '"stable_gdi_ready": True' in prepare_helper
    assert 'management_value_xy_cache[vendor_key]' in prepare_helper
    assert 'finance_vendor_entry_state["f9_seeded"] = False' in prepare_helper
    assert "main_win.descendants" not in prepare_helper
    assert "_management_grid_snapshot()" not in prepare_helper


def test_recovery_preflight_uses_top_level_windows_and_skips_generic_popup_loop():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    run_start = source.index("def _run_unlocked")
    setup_start = source.index("def _setup_slip_form", run_start)
    run_helper = source[run_start:setup_start]
    fast_start = run_helper.index("def _fast_recovery_main_window")
    fast_end = run_helper.index("main_win = None", fast_start)
    fast_helper = run_helper[fast_start:fast_end]

    assert "self.app.windows()" in fast_helper
    assert "win.is_visible()" in fast_helper
    assert 'auto_id.lower() == "mainwindow"' in fast_helper
    assert "width < 640 or height < 400" in fast_helper
    assert "max(" in fast_helper
    assert ".descendants(" not in fast_helper
    assert "pyautogui.press" not in fast_helper

    assert "if resume_existing_voucher:\n                main_win = _fast_recovery_main_window()" in run_helper
    assert "while not resume_existing_voucher and time.time() < login_wait_deadline:" in run_helper
    assert "if not main_win and not resume_existing_voucher:" in run_helper
    assert "if not resume_existing_voucher and _is_password_change_blocker(main_win):" in run_helper

    slow_guard = (
        "if existing_pids and not confirmed_pid and not resume_existing_voucher:"
    )
    recovery_attach = "if resume_existing_voucher and not confirmed_pid:"
    slow_start = run_helper.index(slow_guard)
    recovery_start = run_helper.index(recovery_attach, slow_start)
    slow_branch = run_helper[slow_start:recovery_start]
    assert "temp_app.windows(title_re=" in slow_branch
    assert "not resume_existing_voucher" in slow_branch.splitlines()[0]


def test_recovery_process_name_miss_uses_large_top_level_erp_window_without_tree_scan():
    descendant_calls = []

    class FakeWindow:
        def __init__(self, title, auto_id, rect, pid, visible=True):
            self._title = title
            self._rect = rect
            self._visible = visible
            self._pid = pid
            self.element_info = SimpleNamespace(
                automation_id=auto_id,
                process_id=pid,
            )

        def is_visible(self):
            return self._visible

        def window_text(self):
            return self._title

        def rectangle(self):
            return self._rect

        def process_id(self):
            return self._pid

        def descendants(self, *_args, **_kwargs):
            descendant_calls.append(self._title)
            raise AssertionError("top-level recovery must not enumerate descendants")

    unrelated = FakeWindow(
        "메일 - Daou Office",
        "mainwindow",
        _FakeRect(0, 0, 2560, 1440),
        91,
    )
    wrong_corporation = FakeWindow(
        "대승정밀 - 분개전표입력",
        "mainwindow",
        _FakeRect(0, 0, 2560, 1440),
        92,
    )
    erp = FakeWindow(
        "대승 - 분개전표입력",
        "mainwindow",
        _FakeRect(0, 0, 1920, 1080),
        243,
    )
    fake_desktop = lambda **_kwargs: SimpleNamespace(
        windows=lambda: [unrelated, wrong_corporation, erp]
    )
    finder = _load_nested_functions(
        "_find_existing_erp_top_level_window",
        namespace={"Desktop": fake_desktop},
    )["_find_existing_erp_top_level_window"]

    match = finder(
        ["대승"],
        excluded_keywords=["대승정밀"],
        logger=_FakeLogger(),
    )

    assert match["pid"] == 243
    assert match["window"] is erp
    assert match["width"] == 1920
    assert match["height"] == 1080
    assert descendant_calls == []


def test_recovery_process_name_fallback_runs_before_failure_and_never_launches_new_erp():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    run_start = source.index("def _run_unlocked")
    setup_start = source.index("def _setup_slip_form", run_start)
    run_helper = source[run_start:setup_start]

    fallback = run_helper.index("top_level_match = _find_existing_erp_top_level_window(")
    final_guard = run_helper.index(
        "if resume_existing_voucher and not confirmed_pid:",
        fallback,
    )
    fresh_launch = run_helper.index("os.startfile(exe_path)")

    assert fallback < final_guard < fresh_launch
    assert "if resume_existing_voucher and not existing_pids:" not in run_helper
    assert "if not confirmed_pid:" in run_helper[final_guard:fresh_launch]
    fallback_branch = run_helper[fallback:final_guard]
    assert "confirmed_pid = fallback_pid" in fallback_branch
    assert "existing_pids.add(fallback_pid)" in fallback_branch
    assert "self.app = fallback_app" in fallback_branch
    assert "self.manager.erp_pids[self.corp_code] = fallback_pid" in fallback_branch


def test_management_recovery_defers_form_validation_to_exact_first_row_check():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    run_start = source.index("def _run_unlocked")
    setup_start = source.index("def _setup_slip_form", run_start)
    run_helper = source[run_start:setup_start]
    recovery_dispatch = run_helper.index("if resume_existing_voucher:", run_helper.index("메뉴 진입 전 ERP 메인 창"))
    dispatch_end = run_helper.index("time.sleep(menu_step_wait)", recovery_dispatch)
    dispatch = run_helper[recovery_dispatch:dispatch_end]

    assert "resume_print_only_requested" in dispatch
    assert "self._resume_slip_form_ready(main_win)" in dispatch
    assert dispatch.index("resume_print_only_requested") < dispatch.index("self._resume_slip_form_ready(main_win)")
    assert "resume_management_save_print\n                            and not self._resume_slip_form_ready" not in dispatch

    setup_end = source.index("def _all_edits", setup_start)
    setup_helper = source[setup_start:setup_end]
    management_start = setup_helper.rindex("if resume_management_save_print:")
    management_end = setup_helper.index("if resume_print_only_requested:", management_start)
    management_branch = setup_helper[management_start:management_end]
    assert "_prepare_management_recovery_from_first_row()" in management_branch
    assert "_resume_slip_form_ready" not in management_branch


def test_management_recovery_only_dismisses_verified_stale_save_required_message():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    setup_start = source.index("def _setup_slip_form")
    setup_end = source.index("def _all_edits", setup_start)
    setup_helper = source[setup_start:setup_end]
    management_start = setup_helper.rindex("if resume_management_save_print:")
    management_end = setup_helper.index("if resume_print_only_requested:", management_start)
    management_branch = setup_helper[management_start:management_end]

    find_message = management_branch.index("_find_erp_message_snapshot()")
    verify_phrase = management_branch.index("save_required_phrase not in stale_compact", find_message)
    unknown_failure = management_branch.index("알 수 없는 ERP Message", verify_phrase)
    dismiss = management_branch.index("_dismiss_verified_erp_message(", unknown_failure)
    first_row = management_branch.index("_prepare_management_recovery_from_first_row()", dismiss)
    assert find_message < verify_phrase < unknown_failure < dismiss < first_row
    assert "pyautogui.press(\"n\")" not in management_branch
    assert "pyautogui.press(\"escape\")" not in management_branch


def test_resume_print_only_is_admin_only_and_cleared_for_normal_jobs():
    web_source = WEB_MAIN_SOURCE.read_text(encoding="utf-8")
    upload_start = web_source.index("def api_upload_voucher")
    upload_end = web_source.index('@app.get("/api/jobs")', upload_start)
    upload_helper = web_source[upload_start:upload_end]
    assert "resume_print_only: str = Form(default=\"0\")" in upload_helper
    assert "resume_print_only_enabled and not (user and user.is_admin)" in upload_helper
    assert '"resume_print_only": resume_print_only_enabled' in upload_helper

    adapter_source = AGENT_ADAPTER_SOURCE.read_text(encoding="utf-8")
    assert "resume_print_only = _resume_print_only_requested(payload)" in adapter_source
    assert (
        'os.environ["ERP_RESUME_PRINT_ONLY"] = "1" if resume_print_only else "0"'
        in adapter_source
    )


def test_erp_message_snapshot_uses_only_same_process_message_window():
    class FakeText:
        def __init__(self, text):
            self._text = text
            self.element_info = SimpleNamespace(name=text, control_type="Text")

        def window_text(self):
            return self._text

        def texts(self):
            return [self._text]

    class FakeWindow(FakeText):
        def __init__(self, pid, title, body):
            super().__init__(title)
            self._pid = pid
            self._children = [FakeText(body)]
            self.element_info.process_id = pid

        def process_id(self):
            return self._pid

        def descendants(self):
            return list(self._children)

    unrelated = FakeWindow(999, "Message", "저장 후 출력해 주십시오.")
    erp_message = FakeWindow(243, "Message", "저장되었습니다.")

    def fake_desktop(*, backend):
        return SimpleNamespace(windows=lambda: [unrelated, erp_message] if backend == "win32" else [])

    bot = SimpleNamespace(erp_process_pid=243, logger=_FakeLogger())
    find_message = _load_nested_functions(
        "_find_erp_message_snapshot",
        namespace={"Desktop": fake_desktop, "re": re, "self": bot},
    )["_find_erp_message_snapshot"]

    snapshot = find_message()

    assert snapshot["window"] is erp_message
    assert snapshot["pid"] == 243
    assert "저장되었습니다." in snapshot["text"]
    assert "저장 후 출력해 주십시오." not in snapshot["text"]


def test_save_message_reads_uia_first_and_waits_for_late_dialog():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")

    find_start = source.index("def _find_erp_message_snapshot")
    find_end = source.index("def _wait_erp_message", find_start)
    find_helper = source[find_start:find_end]
    # WPF Message 창의 문구/버튼은 uia로만 읽히므로 uia를 먼저 시도해야 한다.
    assert 'for backend in ("uia", "win32"):' in find_helper
    assert 'for backend in ("win32", "uia"):' not in find_helper

    save_start = source.index("def _save_current_voucher_via_toolbar")
    save_end = source.index("def _wait_rd_viewer_ready", save_start)
    save_helper = source[save_start:save_end]
    # 대형 전표는 저장 확인창이 늦게 뜨므로 기본 대기가 충분히 길어야 한다.
    assert 'os.getenv("ERP_SAVE_CONFIRM_TIMEOUT_SECONDS", "60")' in save_helper


def test_verified_erp_message_dismissal_never_enters_unknown_dialog():
    pressed = []
    bot = SimpleNamespace(logger=_FakeLogger())
    compact_and_dismiss = _load_nested_functions(
        "_erp_message_compact",
        "_dismiss_verified_erp_message",
        namespace={
            "re": re,
            "pyautogui": SimpleNamespace(press=lambda key: pressed.append(key)),
            "time": SimpleNamespace(sleep=lambda _seconds: None),
            "ERP_SETTLE_WAIT": 0,
            "self": bot,
        },
    )
    dismiss = compact_and_dismiss["_dismiss_verified_erp_message"]
    snapshot = {
        "title": "Message",
        "text": "알 수 없는 오류",
        "window": SimpleNamespace(descendants=lambda **_kwargs: []),
    }

    with pytest.raises(RuntimeError, match="검증되지 않은 ERP Message"):
        dismiss(snapshot, ("저장되었습니다",))

    assert pressed == []


def test_save_and_print_guard_rejects_open_account_lookup_popup():
    class FakePopup:
        def __init__(self, title, pid, rect):
            self._title = title
            self._pid = pid
            self._rect = rect
            self.element_info = SimpleNamespace(process_id=pid)

        def window_text(self):
            return self._title

        def process_id(self):
            return self._pid

        def is_visible(self):
            return True

        def rectangle(self):
            return self._rect

    account_popup = FakePopup("계좌", 243, _FakeRect(843, 540, 1743, 1040))
    unrelated_popup = FakePopup("계좌", 999, _FakeRect(200, 200, 1000, 800))
    main_window = FakePopup("대승", 243, _FakeRect(0, 0, 1920, 1040))

    loaded = _load_nested_functions(
        "_visible_erp_management_lookup_popups",
        "_assert_no_erp_management_lookup_popup",
        namespace={
            "Desktop": lambda **_kwargs: SimpleNamespace(
                windows=lambda: [main_window, unrelated_popup, account_popup]
            ),
            "re": re,
            "bank_account_popup_state": {
                "opened": False,
                "closed": True,
                "source": "",
            },
            "self": SimpleNamespace(erp_process_pid=243, logger=_FakeLogger()),
        },
    )

    blockers = loaded["_visible_erp_management_lookup_popups"]()
    assert len(blockers) == 1
    assert blockers[0][0:2] == ("계좌", 243)
    with pytest.raises(RuntimeError, match="계좌/거래처 선택 팝업이 닫히지 않아"):
        loaded["_assert_no_erp_management_lookup_popup"]("저장 전")


def test_lookup_popup_guard_blocks_unclosed_internal_account_state():
    loaded = _load_nested_functions(
        "_visible_erp_management_lookup_popups",
        namespace={
            "Desktop": lambda **_kwargs: SimpleNamespace(windows=lambda: []),
            "re": re,
            "bank_account_popup_state": {
                "opened": True,
                "closed": False,
                "source": "bank-account-internal-uia",
            },
            "self": SimpleNamespace(erp_process_pid=243, logger=_FakeLogger()),
        },
    )

    blockers = loaded["_visible_erp_management_lookup_popups"]()

    assert blockers == [
        ("계좌(internal-state)", 243, "bank-account-internal-uia")
    ]


def test_save_and_print_paths_call_lookup_popup_guard_before_actions():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    save_start = source.index("def _save_current_voucher_via_toolbar")
    save_end = source.index("def _wait_rd_viewer_ready", save_start)
    save_helper = source[save_start:save_end]
    assert '_assert_no_erp_management_lookup_popup("저장 전")' in save_helper
    assert save_helper.index('_assert_no_erp_management_lookup_popup("저장 전")') < save_helper.index(
        "_click_save_button()"
    )

    print_start = source.index("def _save_and_open_print_dialog")
    print_end = source.index("pyautogui.hotkey('ctrl', 'p')", print_start)
    print_helper = source[print_start:print_end]
    assert '_assert_no_erp_management_lookup_popup("출력 전")' in print_helper


def test_save_toolbar_click_verifies_exact_point_control_without_tree_scan(monkeypatch):
    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    save_click_start = source.index("def _click_save_button")
    save_click_end = source.index("def _save_current_voucher_via_toolbar", save_click_start)
    assert 'ERP_SAVE_BUTTON_XY", "250,80"' in source[save_click_start:save_click_end]

    monkeypatch.setenv("ERP_SAVE_BUTTON_XY", "222,77")
    clicked = []
    bot = SimpleNamespace(logger=_FakeLogger())
    save_control = SimpleNamespace(
        handle=101,
        element_info=SimpleNamespace(name="저장", runtime_id=(1, 2, 3)),
        window_text=lambda: "저장",
        is_visible=lambda: True,
        is_enabled=lambda: True,
        parent=lambda: None,
    )
    click_save = _load_nested_functions(
        "_click_save_button",
        namespace={
            "os": __import__("os"),
            "re": re,
            "Desktop": lambda **_kwargs: SimpleNamespace(
                from_point=lambda x, y: save_control
            ),
            "_main_rect": lambda: SimpleNamespace(left=10, top=20),
            "_click_form_xy": lambda x, y, label, wait=None: clicked.append((x, y, label, wait)),
            "_env_flag": lambda *_args: False,
            "ERP_SETTLE_WAIT": 0.18,
            "self": bot,
        },
    )["_click_save_button"]

    assert click_save() is True
    assert clicked == [(222, 77, "ERP 상단 '저장' 툴바 버튼", 0.18)]


def test_save_toolbar_never_clicks_when_point_is_not_exact_save(monkeypatch):
    monkeypatch.setenv("ERP_SAVE_BUTTON_XY", "222,77")
    clicked = []
    bot = SimpleNamespace(logger=_FakeLogger())
    wrong_control = SimpleNamespace(
        handle=102,
        element_info=SimpleNamespace(name="복사하여저장", runtime_id=(4, 5, 6)),
        window_text=lambda: "복사하여저장",
        is_visible=lambda: True,
        is_enabled=lambda: True,
        parent=lambda: None,
    )
    click_save = _load_nested_functions(
        "_click_save_button",
        namespace={
            "os": __import__("os"),
            "re": re,
            "Desktop": lambda **_kwargs: SimpleNamespace(
                from_point=lambda _x, _y: wrong_control
            ),
            "_main_rect": lambda: SimpleNamespace(left=0, top=0),
            "_click_form_xy": lambda *args, **kwargs: clicked.append((args, kwargs)),
            "_env_flag": lambda *_args: False,
            "ERP_SETTLE_WAIT": 0.18,
            "self": bot,
        },
    )["_click_save_button"]

    with pytest.raises(RuntimeError, match="정확한 '저장' UI 요소"):
        click_save()

    assert clicked == []


def test_management_save_allows_no_message_then_uses_print_stage_verification(monkeypatch):
    monkeypatch.setenv("ERP_SAVE_CONFIRM_TIMEOUT_SECONDS", "1")
    clicked = []
    bot = SimpleNamespace(logger=_FakeLogger())
    save_current = _load_nested_functions(
        "_save_current_voucher_via_toolbar",
        namespace={
            "os": __import__("os"),
            "re": re,
            "time": SimpleNamespace(sleep=lambda _seconds: None),
            "ERP_SETTLE_WAIT": 0,
                "main_win": SimpleNamespace(is_minimized=lambda: False, set_focus=lambda: None),
                "_assert_no_erp_management_lookup_popup": lambda _context: None,
                "_find_erp_message_snapshot": lambda: None,
            "_click_save_button": lambda: clicked.append("save"),
            "_wait_erp_message": lambda _timeout: None,
            "_erp_message_compact": lambda snapshot: "" if not snapshot else snapshot["text"],
            "_dismiss_verified_erp_message": lambda *_args, **_kwargs: True,
            "self": bot,
        },
    )["_save_current_voucher_via_toolbar"]

    assert save_current() is True
    assert clicked == ["save"]


def test_rd_wait_fails_immediately_on_save_required_message():
    bot = SimpleNamespace(logger=_FakeLogger())
    helpers = _load_nested_functions(
        "_erp_message_compact",
        "_wait_rd_viewer_ready",
        namespace={
            "re": re,
            "time": SimpleNamespace(time=lambda: 0.0, sleep=lambda _seconds: None),
            "_find_erp_message_snapshot": lambda: {
                "title": "Message",
                "text": "저장 후 출력해 주십시오.",
            },
            "_find_rd_viewer_window": lambda: (_ for _ in ()).throw(
                AssertionError("RD lookup must not run")
            ),
            "_find_rd_viewer_process": lambda: (None, ""),
            "ERP_CLICK_WAIT": 0.08,
            "self": bot,
        },
    )
    wait_ready = helpers["_wait_rd_viewer_ready"]

    with pytest.raises(RuntimeError, match="저장 후 출력해 주십시오"):
        wait_ready(timeout_sec=45, phase="Ctrl+P")


def test_management_save_precedes_print_and_rd_timeout_scales_with_row_count():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    start = source.index("def _save_and_open_print_dialog")
    end = source.index("def _setup_by_coordinates_only", start)
    helper = source[start:end]

    management_flag = helper.index('ERP_RESUME_MANAGEMENT_SAVE_PRINT')
    safe_save = helper.index("_save_current_voucher_via_toolbar()", management_flag)
    print_hotkey = helper.index("pyautogui.hotkey('ctrl', 'p')", safe_save)
    assert management_flag < safe_save < print_hotkey
    assert helper.count("_save_current_voucher_via_toolbar()") == 2
    assert "Ctrl+S 저장 시작" not in helper
    assert "pyautogui.hotkey('ctrl', 's')" not in helper
    assert "저장 알림 닫기용 Enter" not in helper
    assert 'ERP_PRINT_VIEWER_SECONDS_PER_ROW", "0.8"' in helper
    assert 'ERP_PRINT_VIEWER_INITIAL_SECONDS_PER_ROW", "0.5"' in helper
    assert "effective_row_count * max(0.0, viewer_seconds_per_row)" in helper
    assert "viewer_cap = min(300.0" in helper


def test_fresh_rd_window_rejects_stale_baseline_identity():
    class FakeWindow:
        def __init__(self, *, pid, handle, title, rect):
            self._pid = pid
            self.handle = handle
            self._title = title
            self._rect = rect
            self.element_info = SimpleNamespace(process_id=pid, class_name="RDFrame")

        def is_visible(self):
            return True

        def process_id(self):
            return self._pid

        def window_text(self):
            return self._title

        def class_name(self):
            return "RDFrame"

        def rectangle(self):
            return self._rect

    rect = _FakeRect(10, 20, 900, 700)
    stale = FakeWindow(
        pid=501,
        handle=1001,
        title="Report Designer Viewer - old",
        rect=rect,
    )
    windows = [stale]

    def fake_desktop(*, backend):
        return SimpleNamespace(windows=lambda: windows if backend == "win32" else [])

    find_fresh = _load_nested_functions(
        "_find_fresh_rd_viewer_window",
        namespace={"Desktop": fake_desktop, "re": re},
    )["_find_fresh_rd_viewer_window"]
    baseline = {
        "processes": {501: "rdviewer_u.exe"},
        "windows": [
            {
                "pid": 501,
                "handle": 1001,
                "title": "Report Designer Viewer - old",
                "class": "RDFrame",
                "rect": "10,20,900,700",
            }
        ],
    }

    assert find_fresh(baseline, preferred_pids=set()) == (None, "", "", {})

    replacement = FakeWindow(
        pid=501,
        handle=1002,
        title="Report Designer Viewer - old",
        rect=rect,
    )
    windows[:] = [replacement]
    found, backend, title, meta = find_fresh(baseline, preferred_pids=set())
    assert found is replacement
    assert backend == "win32"
    assert title == "Report Designer Viewer - old"
    assert meta["handle"] == 1002


def test_rd_wait_does_not_return_process_before_visible_new_window():
    process = SimpleNamespace(pid=777)
    viewer = SimpleNamespace()
    calls = []

    def find_fresh(_baseline, preferred_pids):
        calls.append(set(preferred_pids))
        if len(calls) == 1:
            return None, "", "", {}
        return (
            viewer,
            "win32",
            "Report Designer Viewer",
            {
                "pid": 777,
                "identity": (777, 88, "Report Designer Viewer", "RDFrame", "0,0,800,600"),
            },
        )

    clock_value = {"value": 0.0}

    def clock():
        value = clock_value["value"]
        clock_value["value"] += 0.1
        return value

    bot = SimpleNamespace(logger=_FakeLogger())
    helpers = _load_nested_functions(
        "_erp_message_compact",
        "_wait_rd_viewer_ready",
        namespace={
            "re": re,
            "time": SimpleNamespace(time=clock, sleep=lambda _seconds: None),
            "_find_erp_message_snapshot": lambda: None,
            "_new_rd_viewer_processes": lambda _baseline: [(process, "rdviewer_u.exe")],
            "_find_fresh_rd_viewer_window": find_fresh,
            "ERP_CLICK_WAIT": 0.08,
            "self": bot,
        },
    )
    baseline = {"processes": {501: "rdviewer_u.exe"}, "windows": []}

    ready = helpers["_wait_rd_viewer_ready"](
        timeout_sec=1,
        phase="Ctrl+P",
        baseline=baseline,
    )

    assert len(calls) == 2
    assert ready["window"] is viewer
    assert ready["pid"] == 777
    assert ready["baseline"] is baseline


def test_print_wait_uses_baseline_and_skips_duplicate_click_for_pending_new_process():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    start = source.index("def _save_and_open_print_dialog")
    end = source.index("def _setup_by_coordinates_only", start)
    helper = source[start:end]

    assert helper.count("baseline=print_runtime_baseline") == 2
    pending_guard = helper.index("if pending_new_processes:")
    fallback_click = helper.index("_click_print_button()", pending_guard)
    remaining_wait = helper.index("remaining_viewer_timeout =", fallback_click)
    pending_block = helper[pending_guard:remaining_wait]
    assert pending_block.index("else:") < pending_block.index("_click_print_button()")
    assert "중복 출력 클릭을 생략" in pending_block

    focus_start = source.index("def _focus_rd_viewer_window")
    focus_end = source.index("def _close_rd_viewer", focus_start)
    focus_helper = source[focus_start:focus_end]
    strict_guard = focus_helper.index("if strict_baseline is not None:")
    assert focus_helper.index("_find_fresh_rd_viewer_window(", strict_guard) < focus_helper.index(
        "_find_rd_viewer_process()",
        strict_guard,
    )
    assert "Never replace the verified fresh window with a stale Viewer" in focus_helper


def test_waits_for_slow_paste_completion_before_management_fill():
    # ERP는 210행을 순차적으로(느리게) 붙여넣는다(사용자 실기기 확인).
    # 모든 행이 다 들어가기 전에는 하단 관리항목값 칸이 나타나지 않으므로,
    # 하단 차변합계가 안정될 때까지(= 붙여넣기 완료) 기다린 뒤 관리항목
    # 입력을 시작해야 한다. 붙여넣기 도중 합계는 0이라 잉크가 작으므로
    # 최소 잉크 문턱(min_ink)으로 "0"을 완료로 오탐하지 않아야 한다.
    source = MANAGER_SOURCE.read_text(encoding="utf-8")

    anchor = source.index("_paste_grid_until_reflected()")
    fill_at = source.index("_fill_management_items_by_coord()", anchor)
    between = source[anchor:fill_at]
    assert "ERP_WAIT_PASTE_TOTAL_STABLE" in between
    assert "ERP_PASTE_TOTAL_MIN_INK" in between
    assert "ERP_PASTE_TOTAL_TIMEOUT" in between
    assert "붙여넣기 완료 감지" in between

    # 완료 대기(합계 안정)는 Ctrl+Home 스크롤과 관리준비 감지보다 먼저 실행돼야 한다.
    wait_at = between.index("ERP_WAIT_PASTE_TOTAL_STABLE")
    scroll_at = between.index("ERP_GRID_SCROLL_TOP_BEFORE_MGMT")
    assert wait_at < scroll_at

    # "0" 오탐 방지: 안정 판정은 min_ink 문턱을 통과한 잉크만 인정해야 한다.
    assert "cur_ink >= min_ink" in between


def test_paste_total_box_uses_measured_coordinates_and_threshold():
    # 실기기(1920x1080) 실패 스크린샷 실측: 차변합계 박스 (110,936) 160x17,
    # 숫자 밝기 190~199(연회색)라 문턱 215 필요. 이전 기본값(200,897/문턱
    # 125)은 빈 여백을 봐서 ink=0으로 10분 시간초과했다(작업 c7cfe6b99a2f).
    source = MANAGER_SOURCE.read_text(encoding="utf-8")

    anchor = source.index("_paste_grid_until_reflected()")
    fill_at = source.index("_fill_management_items_by_coord()", anchor)
    between = source[anchor:fill_at]
    assert '"ERP_TOTAL_BOX_X", "110"' in between
    assert '"ERP_TOTAL_BOX_Y", "936"' in between
    assert '"ERP_PASTE_TOTAL_INK_THR", "215"' in between
    assert '"ERP_PASTE_TOTAL_MIN_INK", "20"' in between


def test_precheck_waits_for_slow_panel_refresh_before_abort():
    # 행 이동 뒤 하단 패널 갱신이 느려 이전 행 확정값이 잠시 남는다(18행
    # 실패 스크린샷: 더블클릭 0.65초 후에도 이전 행 값 표시, 몇 초 뒤
    # 비워짐). 미이동 단정 전에 비워질 때까지 폴링해야 한다.
    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    input_start = source.index("def _input_finance_vendor_code_xy")
    input_end = source.index("def _input_vendor_by_number_keyboard", input_start)
    input_body = source[input_start:input_end]

    assert "ERP_MGMT_PANEL_REFRESH_WAIT" in input_body
    assert "지연 갱신" in input_body
    # 폴링이 중단 판정보다 먼저 와야 한다.
    poll_at = input_body.index("ERP_MGMT_PANEL_REFRESH_WAIT")
    abort_at = input_body.index("클릭 전 관리항목값 셀이 비어 있지")
    assert poll_at < abort_at
    # 스코프 안전: 입력 함수 로컬/공유 헬퍼만 사용해야 한다.
    assert "row_geometry_state" not in input_body
    assert "summary_x" not in input_body


def test_viewport_rows_also_recover_from_missed_advance():
    # 미이동 복구가 스크롤 모드 전용이라 뷰포트 행(1~23)은 즉시 실패했다
    # (18행 사례). 뷰포트 행은 해당 y 재더블클릭이 복구다.
    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    coord_scope_start = source.index("def _fill_management_items_by_coord")
    viewport_recovery_at = source.index("적요 재더블클릭")
    assert viewport_recovery_at > coord_scope_start
    # recoverable 판정이 더 이상 bottom_scroll_mode에 묶여 있지 않아야 한다.
    rec_at = source.index('"거래처번호 직접 키보드 입력" in str(fill_exc)')
    rec_block = source[rec_at:rec_at + 220]
    assert "bottom_scroll_mode" not in rec_block.split("recoverable")[0]
    assert "fill_attempt < fill_attempts - 1" in rec_block


def test_missed_advance_escalates_to_ctrl_home_renavigation():
    # 86행 사례: ERP가 그리드를 맨 아래(210행)로 돌발 점프시키면 Down
    # 재전송(가벼운 복구)은 무력하다. 2차부터는 Ctrl+Home으로 1행 복귀 후
    # Down×(row_no-1)로 목표 행까지 결정적으로 재탐색해야 한다.
    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    coord_scope_start = source.index("def _fill_management_items_by_coord")
    renav_at = source.index("Ctrl+Home 재탐색")
    assert renav_at > coord_scope_start

    rec_at = source.index('"거래처번호 직접 키보드 입력" in str(fill_exc)')
    block = source[rec_at:rec_at + 20000]
    # 재탐색은 가벼운 복구(1차) 다음(2차 이상)에만 발동한다.
    assert "if fill_attempt >= 1:" in block
    # Ctrl+Home → Down 반복 → 재선택 순서.
    home_at = block.index("pyautogui.hotkey('ctrl', 'home')")
    downs_at = block.index("for _ in range(row_no - 1):")
    reselect_at = block.index("재탐색 재선택")
    assert home_at < downs_at < reselect_at
    # 뷰포트/스크롤 두 좌표 모두 계산한다.
    assert "first_row_y + (row_no - 1) * row_height" in block
    assert '"scroll_anchor_y"' in block or "scroll_anchor_y" in block
    # 기존 가벼운 복구(재더블클릭·Down 재전송)도 보존된다.
    assert "적요 재더블클릭" in block
    assert "Down 재전송" in block


def test_renavigation_verifies_arrival_row_by_summary_before_input():
    # 적대 검증에서 확정된 결함 보완: 재탐색이 Down 유실/돌발 점프 재발로
    # 엉뚱한 "빈" 행에 착지하면 빈칸 가드를 통과해 다른 행에 거래처가
    # 입력될 수 있다. 적요(행마다 거래처명이 달라 유일)를 복사해 목표
    # 행과 대조하고, 일치할 때만 재선택·입력을 진행해야 한다.
    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    rec_at = source.index('"거래처번호 직접 키보드 입력" in str(fill_exc)')
    block = source[rec_at:rec_at + 20000]

    # 검증이 재선택(더블클릭)보다 먼저 온다.
    verify_at = block.index("재탐색 적요 검증 클릭")
    reselect_at = block.index("재탐색 재선택")
    assert verify_at < reselect_at
    # 적요 유일성 대조: erp_rows의 마지막 탭 필드와 정규화 비교.
    assert "renav_expected_summary" in block
    assert "_norm_text(renav_copied)" in block
    # 불일치·복사 불능이면 재탐색 반복, 소진 시 입력 경로에 절대 들어가지
    # 않고 즉시 raise(안전 실패). continue로 넘기면 다음 시도의 첫 동작이
    # 입력 함수 호출이라 잘못 선택된 빈 행에 입력될 수 있다(검증으로 확정).
    assert "재탐색을 반복합니다" in block
    assert "잘못된 행 입력을 막기 위해 중단합니다" in block
    raise_at = block.index("잘못된 행 입력을 막기 위해 중단합니다")
    assert raise_at < reselect_at
    assert "ERP_FINANCE_RENAV_VERIFY_RETRIES" in block
    # 클립보드는 sentinel 가드 + 원복.
    assert "renav_sentinel" in block
    assert "pyperclip.copy(renav_old_clip)" in block
