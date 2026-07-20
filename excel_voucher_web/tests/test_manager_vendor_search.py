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
        "ERP_MENU_STEP_WAIT": "0.60",
        "ERP_MENU_TREE_WAIT": "0.25",
        "ERP_MENU_ENTRY_SETTLE_WAIT": "0.40",
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

    assert fill() is False
    assert state["f9_seeded"] is True
    assert [event[0] for event in events] == ["seed"]

    loaded["row_no"] = 2
    loaded["explicit_management"] = {"거래처": "B002"}
    assert fill() is True
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
    assert fill() is False

    assert [event[0] for event in events] == ["input", "input"]
    assert [event[1][2] for event in events] == ["140-000-948562", "신한 수원금융센터"]
    assert all(event[2] == {"enter_count": 1, "clear": True} for event in events)


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
                "_current_row_account_matches": lambda *_args: True,
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


def test_fast_bank_fill_skips_second_uia_scan_and_inputs_two_values():
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
        assert [event[0] for event in events] == ["input", "input"]
        assert [event[1][0:3] for event in events] == [
            (1118, 797, "140-000-948562"),
            (1118, 817, "신한 수원금융센터"),
        ]
        assert all(event[2] == {"enter_count": 1, "clear": True} for event in events)


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


def _load_runtime_navigation(state, targeted_rows, events, selected_at_y=None):
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
    ready_state = {
        "snapshot": {
            "header_label": header,
            "header_value": header,
            "voucher_viewport_rect": (
                _FakeRect(60, 210, 1450, clip_bottom)
                if include_viewport
                else None
            ),
            "voucher_clip_bottom_abs": (
                int(viewport_clip_bottom if viewport_clip_bottom is not None else clip_bottom)
                if include_viewport
                else None
            ),
        }
    }
    loaded = _load_nested_functions(
        "_fast_visible_voucher_row_snapshot",
        namespace={
            "management_grid_ready_state": ready_state,
            "_main_rect": lambda: _FakeRect(0, 0, 1600, 900),
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


def test_fast_visible_snapshot_uses_cached_header_for_24_or_26_rows():
    for full_row_count, last_full_y in ((24, 691), (26, 731)):
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
    assert '_wait_for_management_grid_ready("text clipboard paste")' not in source

    initial_branch_start = helper.index("if skip_visible_row_scan:")
    initial_branch_end = helper.index("row_geometry_state =", initial_branch_start)
    initial_branch = helper[initial_branch_start:initial_branch_end]
    fast_call = initial_branch.index("_fast_visible_voucher_row_snapshot()")
    slow_else = initial_branch.index("else:", fast_call)
    full_call = initial_branch.index("_fully_visible_voucher_row_snapshot()", slow_else)

    assert fast_call < slow_else < full_call

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
