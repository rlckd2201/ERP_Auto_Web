import ast
import re
from pathlib import Path
from types import SimpleNamespace


MANAGER_SOURCE = (
    Path(__file__).resolve().parents[2]
    / "manager_server"
    / "전표 자동화 프로그램(담당자용)_v6.2.py"
)


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
    ):
        self._text = text
        self._rect = rect
        self._visible = visible
        self._enabled = enabled
        self._parent = None
        self._children = []
        self.element_info = SimpleNamespace(control_type=control_type, name=text)
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


def test_finance_vendor_search_uses_vendor_number_filter():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")

    branch_start = source.index('if search_label == "거래처번호":')
    branch_end = source.index("# ERP 거래처 팝업은", branch_start)
    first_row_branch = source[branch_start:branch_end]

    assert first_row_branch.index("_input_vendor_popup_search_text") < first_row_branch.index(
        "_select_vendor_popup_filter"
    )
    assert first_row_branch.index("_select_vendor_popup_filter") < first_row_branch.index(
        "_click_vendor_popup_search_button"
    )
    assert first_row_branch.index("_click_vendor_popup_search_button") < first_row_branch.index(
        "_select_first_vendor_popup_result"
    )
    assert "pyautogui.press('enter')" not in first_row_branch
    assert (
        'return _input_vendor_by_popup_keyboard(x, y, label, vendor_code, "거래처번호", 2)'
        in source
    )
    assert (
        'return _input_vendor_by_popup_keyboard(x, y, label, vendor_code, "거래처코드", 2)'
        not in source
    )
    assert 'finance_vendor_entry_state = {"popup_seeded": False}' in source
    assert 'if account_key == "미지급금(원화)":' in source
    assert 'if not finance_vendor_entry_state["popup_seeded"]:' in source
    assert 'finance_vendor_entry_state["popup_seeded"] = True' in source
    assert "allow_result_enter_fallback=False" in source
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


def test_finance_first_vendor_result_requires_double_click_without_enter_fallback():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")

    helper_start = source.index("def _select_first_vendor_popup_result")
    helper_end = source.index("def _input_vendor_by_popup_keyboard", helper_start)
    helper = source[helper_start:helper_end]

    assert "_vendor_double_click_abs" in helper
    assert "vendor_popup_result_close_wait" in helper
    assert "if not allow_enter_fallback:" in helper
    assert helper.index("if not allow_enter_fallback:") < helper.index("pyautogui.press('enter')")
    assert "거래처 검색 첫 행 더블클릭 후 화면이 닫히지 않아 중단" in helper

    seed_start = source.index("def _seed_vendor_by_number_popup")
    seed_end = source.index("def _input_vendor_by_number_keyboard", seed_start)
    seed_helper = source[seed_start:seed_end]
    assert "allow_result_enter_fallback=False" in seed_helper


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


def test_finance_first_vendor_executes_required_search_order():
    events = []
    popup = {"source": "internal-uia"}
    popup_results = iter([None, popup])

    loaded = _load_nested_functions(
        "_input_vendor_by_popup_keyboard",
        namespace={
            "_find_vendor_popup": lambda timeout=0: next(popup_results),
            "_double_click_vendor_value_xy": lambda x, y, label, wait=0: events.append("cell-double-click"),
            "_input_vendor_popup_search_text": lambda *_args: events.append("search-value") or True,
            "_select_vendor_popup_filter": lambda *_args: events.append("vendor-number-filter") or True,
            "_click_vendor_popup_search_button": lambda *_args: events.append("search-button") or True,
            "_select_first_vendor_popup_result": (
                lambda *_args, **kwargs: events.append(
                    f"result-double-click:enter-fallback={kwargs['allow_enter_fallback']}"
                )
                or True
            ),
            "vendor_popup_open_wait": 0.0,
            "vendor_popup_focus_wait": 0.0,
            "vendor_popup_search_wait": 0.0,
            "ERP_FORM_WAIT": 0.0,
            "time": SimpleNamespace(sleep=lambda _seconds: None),
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    result = loaded["_input_vendor_by_popup_keyboard"](
        1118,
        797,
        "1행 거래처",
        "A001",
        "거래처번호",
        2,
        allow_result_enter_fallback=False,
    )

    assert result is True
    assert events == [
        "cell-double-click",
        "search-value",
        "vendor-number-filter",
        "search-button",
        "result-double-click:enter-fallback=False",
    ]


def test_finance_first_vendor_detects_same_handle_title_transition_after_double_click():
    events = []
    main_rect = _FakeRect(0, 0, 1600, 900)
    main = _FakeControl("분개전표입력 - K-System", "Window", main_rect)
    main_wrapper = _FakeControl("분개전표입력 - K-System", "Window", main_rect)
    main_wrapper.handle = main.handle

    class _FakeClock:
        now = 0.0

        @classmethod
        def time(cls):
            return cls.now

        @classmethod
        def sleep(cls, seconds):
            cls.now += max(0.01, float(seconds))

    class _FakeDesktop:
        def __init__(self, **_kwargs):
            pass

        def windows(self):
            return [main_wrapper]

    def _open_vendor_mdi(*_args, **_kwargs):
        events.append("cell-double-click")
        main_wrapper._text = "거래처DS - K-System"
        main_wrapper.element_info.name = main_wrapper._text

    loaded = _load_nested_functions(
        "_vendor_popup_context",
        "_find_vendor_popup",
        "_input_vendor_by_popup_keyboard",
        namespace={
            "Desktop": _FakeDesktop,
            "main_win": main,
            "_main_rect": lambda: main_rect,
            "_norm_text": lambda value: re.sub(r"\s+", "", str(value or "")),
            "UiaRect": _FakeRect,
            "_find_internal_vendor_popup": lambda: None,
            "_log_vendor_popup_detection": lambda _popup: None,
            "_double_click_vendor_value_xy": _open_vendor_mdi,
            "_input_vendor_popup_search_text": lambda *_args: events.append("search-value") or True,
            "_select_vendor_popup_filter": lambda *_args: events.append("vendor-number-filter") or True,
            "_click_vendor_popup_search_button": lambda *_args: events.append("search-button") or True,
            "_select_first_vendor_popup_result": (
                lambda *_args, **_kwargs: events.append("result-double-click") or True
            ),
            "vendor_popup_open_wait": 0.0,
            "vendor_popup_focus_wait": 0.0,
            "vendor_popup_search_wait": 0.0,
            "ERP_FORM_WAIT": 0.0,
            "time": _FakeClock,
            "self": SimpleNamespace(logger=_FakeLogger()),
        },
    )

    result = loaded["_input_vendor_by_popup_keyboard"](
        1118,
        797,
        "1행 거래처",
        "A001",
        "거래처번호",
        2,
        allow_result_enter_fallback=False,
    )

    assert result is True
    assert events == [
        "cell-double-click",
        "search-value",
        "vendor-number-filter",
        "search-button",
        "result-double-click",
    ]


def test_finance_vendor_state_uses_popup_once_then_preserves_bank_path():
    events = []
    state = {"popup_seeded": False}
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
            "_seed_vendor_by_number_popup": lambda x, y, label, text: (
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
    assert state["popup_seeded"] is True
    assert [event[0] for event in events] == ["seed"]

    loaded["row_no"] = 2
    loaded["explicit_management"] = {"거래처": "B002"}
    fill()
    assert [event[0] for event in events] == ["seed", "input"]
    _, direct_args, direct_kwargs = events[-1]
    assert direct_args[2] == "B002"
    assert direct_kwargs == {"enter_count": 1, "clear": False}

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
