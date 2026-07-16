import ast
import re
from pathlib import Path
from types import SimpleNamespace


MANAGER_SOURCE = (
    Path(__file__).resolve().parents[2]
    / "manager_server"
    / "전표 자동화 프로그램(담당자용)_v6.2.py"
)
AGENT_ADAPTER_SOURCE = Path(__file__).resolve().parents[1] / "app" / "agent_adapter.py"


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
    def info(self, *_args, **_kwargs):
        pass

    def warning(self, *_args, **_kwargs):
        pass


def test_finance_first_vendor_uses_exact_f9_keyboard_sequence():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")

    helper_start = source.index("def _seed_vendor_by_number_f9")
    helper_end = source.index("def _input_vendor_by_number_keyboard", helper_start)
    helper = source[helper_start:helper_end]
    expected_order = [
        "_click_form_xy",
        "pyautogui.press('f9')",
        "_find_vendor_popup",
        "_paste_text_fast",
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
    assert 'finance_vendor_entry_state = {"f9_seeded": False}' in source
    assert 'if account_key == "미지급금(원화)":' in source
    assert 'if not finance_vendor_entry_state["f9_seeded"]:' in source
    assert 'finance_vendor_entry_state["f9_seeded"] = True' in source
    assert "최초 F9 키보드 입력 완료, 이후 행 직접 입력 전환" in source
    assert "관리항목값 셀 직접 입력 후 Enter 완료" in source
    assert "거래처번호 팝업 입력 실패, 직접 입력 fallback" in source


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
    main_rect = _FakeRect(0, 0, 1600, 900)
    main = _FakeControl("분개전표입력 - K-System", "Window", main_rect)
    main_wrapper = _FakeControl("거래처DS - K-System", "Window", main_rect)
    main_wrapper.handle = main.handle

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
            "_find_internal_vendor_popup": lambda: None,
            "_log_vendor_popup_detection": lambda _popup: None,
            "time": SimpleNamespace(time=lambda: 0.0, sleep=lambda _seconds: None),
        },
    )

    popup = loaded["_find_vendor_popup"](timeout=1.0)

    assert popup["source"] == "internal-title"
    assert popup["root"] is main_wrapper
    assert popup["rect"].left == 8
    assert popup["rect"].top == 52


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


def test_finance_first_vendor_executes_exact_f9_key_order():
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
            "_find_vendor_popup": (
                lambda timeout=0: events.append(("popup-check", timeout))
                or {"source": "internal-title"}
            ),
            "_paste_text_fast": lambda text, label: events.append(("paste", text)),
            "pyautogui": _FakePyAutoGui,
            "time": SimpleNamespace(sleep=lambda _seconds: None),
            "mgmt_click_wait": 0.0,
            "mgmt_focus_wait": 0.0,
            "vendor_popup_open_wait": 0.0,
            "vendor_popup_focus_wait": 0.0,
            "vendor_popup_search_wait": 0.0,
            "mgmt_key_wait": 0.0,
            "ERP_FORM_WAIT": 0.0,
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    result = loaded["_seed_vendor_by_number_f9"](1118, 797, "1행 거래처", "A001")

    assert result is True
    assert events == [
        ("click", 1118, 797),
        ("key", "f9", 1),
        ("popup-check", 3.5),
        ("paste", "A001"),
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
            "_find_vendor_popup": lambda timeout=0: events.append(("popup-check", timeout)),
            "_paste_text_fast": lambda text, label: events.append(("paste", text)),
            "pyautogui": _FakePyAutoGui,
            "time": SimpleNamespace(sleep=lambda _seconds: None),
            "mgmt_click_wait": 0.0,
            "mgmt_focus_wait": 0.0,
            "vendor_popup_open_wait": 0.0,
            "vendor_popup_focus_wait": 0.0,
            "vendor_popup_search_wait": 0.0,
            "mgmt_key_wait": 0.0,
            "ERP_FORM_WAIT": 0.0,
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    result = loaded["_seed_vendor_by_number_f9"](1118, 797, "1행 거래처", "A001")

    assert result is False
    assert events == [
        ("click", 1118, 797),
        ("key", "f9", 1),
        ("popup-check", 3.5),
    ]


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
        "ERP_MENU_STEP_WAIT": "0.45",
        "ERP_MENU_TREE_WAIT": "0.18",
        "ERP_MENU_ENTRY_SETTLE_WAIT": "0.30",
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
            "_input_vendor_by_number_keyboard": lambda *_args, **_kwargs: events.append(("popup",)),
            "_input_value_xy": lambda *args, **kwargs: events.append(("input", args, kwargs)),
            "re": re,
            "self": SimpleNamespace(logger=_FakeLogger()),
            "row_no": 1,
            "account_key": "미지급금(원화)",
            "explicit_management": {"거래처": "A001"},
        },
    )
    fill = loaded["_fill_explicit_management_items"]

    fill()
    assert state["f9_seeded"] is True
    assert [event[0] for event in events] == ["seed"]

    loaded["row_no"] = 2
    loaded["explicit_management"] = {"거래처": "B002"}
    fill()
    assert [event[0] for event in events] == ["seed", "input"]
    _, direct_args, direct_kwargs = events[-1]
    assert direct_args[2] == "B002"
    assert direct_kwargs == {
        "enter_count": 1,
        "clear": False,
        "paste_settle_wait": 0.10,
        "commit_settle_wait": 0.16,
    }

    events.clear()
    loaded["row_no"] = 3
    loaded["account_key"] = "보통예금"
    loaded["explicit_management"] = {
        "계좌번호": "140-000-948562",
        "금융기관지점": "신한 수원금융센터",
        "거래처": "",
    }
    fill()

    assert [event[0] for event in events] == ["input", "input"]
    assert [event[1][2] for event in events] == ["140-000-948562", "신한 수원금융센터"]
    assert all(event[2] == {"enter_count": 1, "clear": True} for event in events)


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
    assert snapshot["rows"][24] == 691
    assert 25 not in snapshot["rows"]
    assert len(snapshot["slot_ys"]) == 24


def test_uia_geometry_uses_row_26_when_viewport_expands():
    snapshot = _visible_voucher_snapshot(first_logical_row=1, full_row_count=26)

    assert snapshot["last_full_y"] == 731
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


def test_dynamic_next_row_reuses_24_or_26_row_bottom_anchor():
    loaded = _load_nested_functions(
        "_next_visible_voucher_row_y",
        namespace={"row_height": 20},
    )
    next_y = loaded["_next_visible_voucher_row_y"]

    row_24_snapshot = _visible_voucher_snapshot(first_logical_row=1, full_row_count=24)
    assert next_y(671, 24, row_24_snapshot) == (691, False)
    assert next_y(691, 25, row_24_snapshot) == (691, True)

    row_26_snapshot = _visible_voucher_snapshot(first_logical_row=1, full_row_count=26)
    assert next_y(711, 26, row_26_snapshot) == (731, False)
    assert next_y(731, 27, row_26_snapshot) == (731, True)


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


def test_advance_grid_row_refreshes_once_at_dynamic_bottom_then_reuses_anchor():
    for full_row_count in (24, 26):
        initial = _visible_voucher_snapshot(first_logical_row=1, full_row_count=full_row_count)
        refreshed = _visible_voucher_snapshot(first_logical_row=2, full_row_count=full_row_count)
        state = {"snapshot": initial, "bottom_scroll_mode": False}
        events = []

        class _FakePyAutoGui:
            @staticmethod
            def press(key):
                events.append(("key", key))

        def _refresh(expected_row_no=None):
            events.append(("refresh", expected_row_no))
            state["snapshot"] = refreshed
            return refreshed

        loaded = _load_nested_functions(
            "_next_visible_voucher_row_y",
            "_advance_grid_row",
            namespace={
                "row_height": 20,
                "row_geometry_state": state,
                "sequential_nav": True,
                "_click_form_xy": (
                    lambda x, y, label, wait=0: events.append(("click", x, y, wait))
                ),
                "summary_x": 970,
                "mgmt_key_wait": 0.05,
                "mgmt_commit_wait": 0.08,
                "pyautogui": _FakePyAutoGui,
                "time": SimpleNamespace(sleep=lambda seconds: events.append(("sleep", seconds))),
                "_refresh_voucher_row_snapshot": _refresh,
                "_fail_form": lambda message: (_ for _ in ()).throw(RuntimeError(message)),
            },
        )
        advance = loaded["_advance_grid_row"]
        bottom_y = initial["last_full_y"]
        next_row_no = full_row_count + 1

        assert advance(bottom_y, next_row_no) == refreshed["rows"][next_row_no]
        assert state["bottom_scroll_mode"] is True
        assert ("refresh", next_row_no) in events

        events.clear()
        assert advance(bottom_y, next_row_no + 1) == refreshed["last_full_y"]
        assert not any(event[0] == "refresh" for event in events)


def test_advance_grid_row_stops_when_expected_row_is_missing_after_refresh():
    initial = _visible_voucher_snapshot(first_logical_row=1, full_row_count=24)
    stale = _visible_voucher_snapshot(first_logical_row=1, full_row_count=24)
    state = {"snapshot": initial, "bottom_scroll_mode": False}

    loaded = _load_nested_functions(
        "_next_visible_voucher_row_y",
        "_advance_grid_row",
        namespace={
            "row_height": 20,
            "row_geometry_state": state,
            "sequential_nav": True,
            "_click_form_xy": lambda *_args, **_kwargs: None,
            "summary_x": 970,
            "mgmt_key_wait": 0.05,
            "mgmt_commit_wait": 0.08,
            "pyautogui": SimpleNamespace(press=lambda _key: None),
            "time": SimpleNamespace(sleep=lambda _seconds: None),
            "_refresh_voucher_row_snapshot": lambda expected_row_no=None: stale,
            "_fail_form": lambda message: (_ for _ in ()).throw(RuntimeError(message)),
        },
    )

    try:
        loaded["_advance_grid_row"](initial["last_full_y"], 25)
    except RuntimeError as exc:
        assert "25행이 마지막 완전 표시 행" in str(exc)
    else:
        raise AssertionError("stale UIA refresh must stop management entry")


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
