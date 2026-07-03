"""Todo 관리 앱 (Streamlit 버전)

원본은 HTML/CSS/Vanilla JS + Local Storage로 만든 앱이며,
이 파일은 동일한 기능(추가/수정/삭제/완료/카테고리/필터/진행률)을
Streamlit으로 옮긴 버전이다. 브라우저 Local Storage 대신, 서버 쪽
JSON 파일(todos.json, settings.json)에 저장해 새로고침·앱 재시작
후에도 Todo 목록과 마지막 선택 카테고리가 유지되도록 한다.
"""

import html
import json
import os
import uuid

import streamlit as st

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "todos.json")
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
CATEGORIES = ["업무", "개인", "공부"]
CATEGORY_COLORS = {
    "업무": "#3b82f6",
    "개인": "#22b06f",
    "공부": "#f5a623",
}

st.set_page_config(page_title="Todo 관리", page_icon="✅", layout="centered")


# ==============================================================================
# Local Storage 연동 (Local Storage 대신 서버의 JSON 파일 사용)
# ==============================================================================
def load_todos():
    """JSON 파일에서 Todo 목록을 불러온다. 없거나 손상되었으면 빈 목록을 반환한다."""
    if not os.path.exists(DATA_FILE):
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(data, list):
        return []

    todos = []
    for todo in data:
        if not isinstance(todo, dict) or not todo.get("text"):
            continue
        todos.append({
            "id": todo.get("id") or str(uuid.uuid4()),
            "text": str(todo["text"]),
            "category": todo.get("category") if todo.get("category") in CATEGORIES else CATEGORIES[0],
            "completed": bool(todo.get("completed", False)),
        })
    return todos


def save_todos(todos):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)


def load_last_category():
    """마지막으로 선택한 카테고리를 불러온다. 앱을 껐다 켜도 유지되도록 파일에 저장한다."""
    if not os.path.exists(SETTINGS_FILE):
        return CATEGORIES[0]

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
    except (OSError, json.JSONDecodeError):
        return CATEGORIES[0]

    category = settings.get("last_category") if isinstance(settings, dict) else None
    return category if category in CATEGORIES else CATEGORIES[0]


def save_last_category(category):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_category": category}, f, ensure_ascii=False, indent=2)


# ==============================================================================
# 세션 상태 초기화
# ==============================================================================
if "todos" not in st.session_state:
    st.session_state.todos = load_todos()
if "editing_id" not in st.session_state:
    st.session_state.editing_id = None
if "filter" not in st.session_state:
    st.session_state.filter = "전체"
if "last_category" not in st.session_state:
    st.session_state.last_category = load_last_category()


# ==============================================================================
# Todo 데이터 조작 (추가 / 수정 / 삭제 / 완료 토글)
# ==============================================================================
def add_todo(text, category):
    text = text.strip()
    if not text:
        return
    st.session_state.todos.append({
        "id": str(uuid.uuid4()),
        "text": text,
        "category": category,
        "completed": False,
    })
    save_todos(st.session_state.todos)


def update_todo(todo_id, new_text, new_category):
    new_text = new_text.strip()
    st.session_state.editing_id = None
    if not new_text:
        return

    for todo in st.session_state.todos:
        if todo["id"] == todo_id:
            todo["text"] = new_text
            todo["category"] = new_category
            break
    save_todos(st.session_state.todos)


def toggle_todo(todo_id):
    for todo in st.session_state.todos:
        if todo["id"] == todo_id:
            todo["completed"] = not todo["completed"]
            break
    save_todos(st.session_state.todos)


def delete_todo(todo_id):
    st.session_state.todos = [t for t in st.session_state.todos if t["id"] != todo_id]
    save_todos(st.session_state.todos)
    if st.session_state.editing_id == todo_id:
        st.session_state.editing_id = None


# ==============================================================================
# Header 영역
# ==============================================================================
st.markdown("<h1 style='text-align:center;'>Todo 관리</h1>", unsafe_allow_html=True)

# ==============================================================================
# Todo 입력 영역
# ==============================================================================
with st.form("add_todo_form", clear_on_submit=True):
    input_col, category_col, button_col = st.columns([3, 1, 1])
    new_text = input_col.text_input(
        "할 일", placeholder="할 일을 입력하세요", label_visibility="collapsed"
    )
    new_category = category_col.selectbox(
        "카테고리",
        CATEGORIES,
        index=CATEGORIES.index(st.session_state.last_category),
        label_visibility="collapsed",
    )
    submitted = button_col.form_submit_button("추가", use_container_width=True)

if submitted:
    add_todo(new_text, new_category)
    st.session_state.last_category = new_category
    save_last_category(new_category)
    st.rerun()

# ==============================================================================
# 진행률 영역 (전체 개수 / 완료 개수 / 퍼센트 / Progress Bar)
# 필터와 무관하게 항상 전체 Todo 기준으로 계산한다.
# ==============================================================================
todos = st.session_state.todos
total = len(todos)
completed_count = sum(1 for t in todos if t["completed"])
percentage = round(completed_count / total * 100) if total else 0

stat_cols = st.columns(3)
stat_cols[0].metric("전체", f"{total}개")
stat_cols[1].metric("완료", f"{completed_count}개")
stat_cols[2].metric("진행률", f"{percentage}%")
st.progress(percentage / 100)

st.divider()

# ==============================================================================
# 카테고리 필터
# ==============================================================================
filter_options = ["전체"] + CATEGORIES
st.session_state.filter = st.radio(
    "카테고리 필터",
    filter_options,
    index=filter_options.index(st.session_state.filter),
    horizontal=True,
    label_visibility="collapsed",
)

if st.session_state.filter == "전체":
    visible_todos = todos
else:
    visible_todos = [t for t in todos if t["category"] == st.session_state.filter]

# ==============================================================================
# Todo 목록 영역
# ==============================================================================
if not visible_todos:
    if total == 0:
        st.info("할 일이 없습니다. 새로운 할 일을 추가해보세요!")
    else:
        st.info("이 카테고리에 해당하는 할 일이 없습니다.")

for todo in visible_todos:
    with st.container(border=True):
        if st.session_state.editing_id == todo["id"]:
            # 수정 모드: 텍스트 입력 + 카테고리 선택 + 저장/취소
            edit_text_col, edit_category_col = st.columns([3, 1])
            edited_text = edit_text_col.text_input(
                "수정",
                value=todo["text"],
                key=f"edit_text_{todo['id']}",
                label_visibility="collapsed",
            )
            edited_category = edit_category_col.selectbox(
                "카테고리 수정",
                CATEGORIES,
                index=CATEGORIES.index(todo["category"]),
                key=f"edit_category_{todo['id']}",
                label_visibility="collapsed",
            )

            save_col, cancel_col = st.columns(2)
            if save_col.button("저장", key=f"save_{todo['id']}", use_container_width=True):
                update_todo(todo["id"], edited_text, edited_category)
                st.rerun()
            if cancel_col.button("취소", key=f"cancel_{todo['id']}", use_container_width=True):
                st.session_state.editing_id = None
                st.rerun()
        else:
            # 보기 모드: 체크박스 + 카테고리 배지 + 텍스트 + 수정/삭제 버튼
            check_col, category_col, text_col, edit_col, delete_col = st.columns(
                [0.6, 1, 4, 1, 1]
            )

            checked = check_col.checkbox(
                "완료", value=todo["completed"], key=f"check_{todo['id']}",
                label_visibility="collapsed",
            )
            if checked != todo["completed"]:
                toggle_todo(todo["id"])
                st.rerun()

            color = CATEGORY_COLORS.get(todo["category"], "#999999")
            category_col.markdown(
                f"<span style='background:{color}22;color:{color};padding:3px 10px;"
                f"border-radius:999px;font-size:0.75rem;font-weight:600;"
                f"white-space:nowrap;'>{html.escape(todo['category'])}</span>",
                unsafe_allow_html=True,
            )

            safe_text = html.escape(todo["text"])
            if todo["completed"]:
                # 완료 시 취소선 + 회색 글자 처리
                text_col.markdown(
                    f"<span style='color:#999999;text-decoration:line-through;'>{safe_text}</span>",
                    unsafe_allow_html=True,
                )
            else:
                text_col.markdown(f"<span>{safe_text}</span>", unsafe_allow_html=True)

            if edit_col.button("수정", key=f"edit_{todo['id']}", use_container_width=True):
                st.session_state.editing_id = todo["id"]
                st.rerun()
            if delete_col.button("삭제", key=f"delete_{todo['id']}", use_container_width=True):
                delete_todo(todo["id"])
                st.rerun()
