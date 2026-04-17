import streamlit as st
import time
import datetime
import uuid
import base64
import json as json_lib
from pathlib import Path
from adapter import send_to_engine, get_session, logger
from file_processors import process_file_for_llm, process_file_for_vlm


def generate_response(user_input: str) -> str:
    try:
        logger.info(f"Generating response for input: {user_input}...")

        if "session_id" not in st.session_state:
            logger.info("Getting new session_id...")
            st.session_state.session_id = get_session(
                st.session_state.user_id, st.session_state.platform_channel_url
            )
            logger.info(f"Received session_id: {st.session_state.session_id}")

        meta = {}

        if "llm_file" in st.session_state and not st.session_state.get("llm_file_sent", False):
            meta["llm_file"] = st.session_state.llm_file
            st.session_state.llm_file_sent = True
            logger.info("Added LLM file to metadata")

        if "vlm_file" in st.session_state and not st.session_state.get("vlm_file_sent", False):
            meta["vlm_file"] = st.session_state.vlm_file
            st.session_state.vlm_file_sent = True
            logger.info("Added VLM file to metadata")

        start_time = time.time()
        api_response, request_json = send_to_engine(
            st.session_state.user_id,
            st.session_state.session_id,
            text=user_input,
            meta=meta,
            platform_channel_url=st.session_state.platform_channel_url,
        )
        elapsed = time.time() - start_time
        logger.info(f"API response received in {elapsed:.2f}s")

        st.session_state.last_request_json = request_json
        st.session_state.last_response_json = api_response

        all_messages = []
        if isinstance(api_response, list):
            for response_item in api_response:
                if "payload" in response_item and "items" in response_item["payload"]:
                    items = response_item["payload"]["items"]
                    for item in items:
                        if "bubble" in item and "value" in item["bubble"]:
                            all_messages.append(item["bubble"]["value"])
        if all_messages:
            processed_messages = [msg.replace("<br/>", "\n") for msg in all_messages]
            return "\n\n---\n\n".join(processed_messages)
        return f"**API Response:**\n```json\n{str(api_response)}\n```"
    except Exception as e:
        logger.error(f"Error communicating with API: {e}")
        return f"Error communicating with API: {str(e)}"


def get_local_logo_data_uri() -> str:
    logo_path = Path(__file__).parent / "assets" / "logo-mws.svg"
    if not logo_path.exists():
        return ""
    logo_bytes = logo_path.read_bytes()
    logo_b64 = base64.b64encode(logo_bytes).decode("utf-8")
    return f"data:image/svg+xml;base64,{logo_b64}"


st.set_page_config(
    page_title="Интерфейс к Платформе МВС ИИ",
    page_icon="💬",
    layout="wide",
)

# ─── Инициализация состояния ────────────────────────────────────────────────
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
    logger.info(f"New session started, user_id: {st.session_state.user_id}")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Управление каналами
if "channels" not in st.session_state:
    st.session_state.channels = [
        {
            "id": str(uuid.uuid4()),
            "name": "Канал 1",
            "url": "https://thrillingly-affordable-hippo.cloudpub.ru/api/e72f886e-4b62-47bb-894e-5622f3ea5ce3",
        }
    ]
if "active_channel_idx" not in st.session_state:
    st.session_state.active_channel_idx = 0

# Синхронизируем platform_channel_url с активным каналом
active_idx = st.session_state.active_channel_idx
if active_idx < len(st.session_state.channels):
    st.session_state.platform_channel_url = st.session_state.channels[active_idx]["url"]

if "debug_panel_open" not in st.session_state:
    st.session_state.debug_panel_open = False

# ─── CSS ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
        /* ── Base ── */
        body, .main { background: #F5F5F5; color: #1F2937; }

        /* убираем лишние паддинги streamlit */
        .block-container { padding-top: 0.75rem !important; padding-bottom: 0 !important; }

        /* ── Topbar ── */
        .mts-topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 2rem 1.25rem;
            border-radius: 16px;
            margin-bottom: 0.75rem;
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            box-shadow: 0 4px 6px rgba(0,0,0,.08);
        }
        .mts-brand { display: flex; align-items: center; gap: 0.75rem; }
        .mts-logo {
            width: 72px; height: 72px; object-fit: contain;
            border-radius: 10px; background: #fff;
            padding: 0.1rem; box-shadow: 0 2px 4px rgba(0,0,0,.1);
        }
        .mts-title-block { display: flex; flex-direction: column; gap: 0.1rem; }
        .mts-title { font-size: 1.05rem; font-weight: 700; letter-spacing: .03em; color: #1F2937; }
        .mts-subtitle { font-size: 0.78rem; color: #6B7280; }
        .mts-status-pill {
            display: inline-flex; align-items: center; gap: .3rem;
            padding: .08rem .55rem; border-radius: 999px;
            background: #DCFCE7; border: 1px solid #22C55E;
            font-size: 0.72rem; color: #166534;
        }
        .mts-status-dot {
            width: 7px; height: 7px; border-radius: 999px;
            background: #22C55E; box-shadow: 0 0 0 3px rgba(34,197,94,.25);
        }

        /* ── Channel sidebar items ── */
        .channel-item {
            display: flex; align-items: center; gap: 0.45rem;
            padding: 0.5rem 0.65rem; border-radius: 10px;
            cursor: pointer; margin-bottom: 0.3rem;
            background: #F9FAFB; border: 1px solid #E5E7EB;
            transition: all .15s;
        }
        .channel-item.active {
            background: linear-gradient(135deg,#FF0033 0%,#FF5C7B 55%,#F97316 100%);
            border-color: transparent;
            color: #fff !important;
        }
        .channel-item.active .ch-name { color: #fff !important; }
        .ch-dot {
            width: 8px; height: 8px; border-radius: 999px;
            background: #22C55E; flex-shrink: 0;
        }
        .ch-name { font-size: 0.82rem; font-weight: 500; color: #1F2937; flex: 1; }

        /* ── Cards ── */
        .mts-card {
            background: #FFFFFF; border-radius: 14px;
            padding: 0.75rem 0.9rem; border: 1px solid #E5E7EB;
            box-shadow: 0 2px 4px rgba(0,0,0,.05); margin-bottom: 0.75rem;
        }
        .mts-card-title {
            font-size: 0.82rem; font-weight: 600; color: #1F2937;
            display: flex; align-items: center; gap: .35rem; margin-bottom: .2rem;
        }
        .mts-chip {
            display: inline-flex; align-items: center;
            padding: .06rem .5rem; border-radius: 999px;
            font-size: 0.68rem; color: #fff;
            background: linear-gradient(135deg,#FF0033 0%,#FF5C7B 55%,#F97316 100%);
        }
        .mts-card-caption { font-size: 0.76rem; color: #6B7280; }

        /* ── File upload zones (центр) ── */
        .file-zone-row {
            display: flex; gap: 0.75rem; margin-bottom: 0.65rem;
        }
        .file-zone {
            flex: 1; background: #FFFFFF; border: 1.5px dashed #D1D5DB;
            border-radius: 14px; padding: 0.65rem 0.8rem;
            text-align: center; transition: border-color .2s;
        }
        .file-zone.ready {
            border-color: #22C55E; background: #F0FDF4;
        }
        .file-zone-label {
            font-size: 0.78rem; font-weight: 600; color: #374151;
            display: flex; align-items: center; justify-content: center; gap: .3rem;
        }
        .file-zone-sub { font-size: 0.7rem; color: #6B7280; margin-top: .15rem; }
        .file-ready-badge {
            display: inline-flex; align-items: center; gap: .3rem;
            background: #DCFCE7; border: 1px solid #22C55E;
            color: #166534; border-radius: 999px;
            padding: .15rem .6rem; font-size: 0.72rem; margin-top: .3rem;
        }

        /* ── Buttons ── */
        div.stButton > button:first-child {
            border-radius: 999px; border: none;
            background: linear-gradient(135deg,#FF0033 0%,#FF5C7B 45%,#F97316 100%);
            color: #fff; font-weight: 500; font-size: 0.78rem;
            padding: .35rem .95rem; box-shadow: 0 2px 4px rgba(0,0,0,.1);
        }
        div.stButton > button:first-child:hover {
            background: linear-gradient(135deg,#FF2450 0%,#FF6C88 45%,#FB923C 100%);
        }

        /* ── Chat ── */
        .chat-wrapper {
            background: #FFFFFF; border-radius: 18px;
            border: 1px solid #E5E7EB; padding: .85rem 1rem .5rem 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,.05);
        }
        .chat-message {
            padding: .55rem .8rem; border-radius: 14px;
            margin-bottom: .45rem; max-width: 92%;
            font-size: 0.9rem; line-height: 1.45;
        }
        .chat-user { margin-left: auto; background: #F3F4F6; border: 1px solid #D1D5DB; }
        .chat-assistant { margin-right: auto; background: #fff; border: 1px solid #E5E7EB; }
        .chat-timestamp { font-size: .7rem; color: #6B7280; margin-top: .08rem; }
        .stChatInputContainer textarea { border-radius: 999px !important; }

        .sidebar-section-title {
            font-size: .72rem; text-transform: uppercase; letter-spacing: .08em;
            color: #6B7280; margin: .75rem 0 .4rem 0; font-weight: 600;
        }

        /* скрываем дефолтный st.sidebar чтобы управлять вручную */
        section[data-testid="stSidebar"] > div:first-child { padding-top: .5rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─── Левый сайдбар (каналы) ──────────────────────────────────────────────────
with st.sidebar:
    logo_uri = get_local_logo_data_uri()
    if logo_uri:
        st.markdown(
            f'<div style="text-align:center;margin-bottom:.5rem;">'
            f'<img src="{logo_uri}" style="width:168px;height:168px;object-fit:contain;border-radius:10px;">'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        '<div style="text-align:center;font-size:.9rem;font-weight:700;color:#1F2937;margin-bottom:.15rem;">MWS AI</div>'
        '<div style="text-align:center;font-size:.7rem;color:#6B7280;margin-bottom:1rem;">Cotype_Pro · Cotype_VL</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sidebar-section-title">Каналы подключения</div>', unsafe_allow_html=True)

    # Список каналов
    for i, ch in enumerate(st.session_state.channels):
        is_active = (i == st.session_state.active_channel_idx)
        col_btn, col_del = st.columns([5, 1])
        with col_btn:
            label = f"{'▶ ' if is_active else ''}{ch['name']}"
            if st.button(label, key=f"ch_select_{ch['id']}", use_container_width=True):
                st.session_state.active_channel_idx = i
                st.session_state.platform_channel_url = ch["url"]
                if "session_id" in st.session_state:
                    del st.session_state.session_id
                st.rerun()
        with col_del:
            if len(st.session_state.channels) > 1:
                if st.button("✕", key=f"ch_del_{ch['id']}"):
                    st.session_state.channels.pop(i)
                    if st.session_state.active_channel_idx >= len(st.session_state.channels):
                        st.session_state.active_channel_idx = len(st.session_state.channels) - 1
                    st.rerun()

    # Добавить канал
    if st.button("＋ Добавить канал", use_container_width=True):
        n = len(st.session_state.channels) + 1
        st.session_state.channels.append({
            "id": str(uuid.uuid4()),
            "name": f"Канал {n}",
            "url": "",
        })
        st.session_state.active_channel_idx = len(st.session_state.channels) - 1
        st.rerun()

    # Редактирование активного канала
    active_idx = st.session_state.active_channel_idx
    ch = st.session_state.channels[active_idx]

    st.markdown('<div class="sidebar-section-title" style="margin-top:1rem;">Настройки канала</div>', unsafe_allow_html=True)

    new_name = st.text_input("Имя канала", value=ch["name"], key=f"ch_name_edit_{ch['id']}")
    if new_name != ch["name"]:
        st.session_state.channels[active_idx]["name"] = new_name

    new_url = st.text_area("URL канала", value=ch["url"], key=f"ch_url_edit_{ch['id']}", height=100)
    if new_url != ch["url"]:
        st.session_state.channels[active_idx]["url"] = new_url
        st.session_state.platform_channel_url = new_url
        if "session_id" in st.session_state:
            del st.session_state.session_id

    st.markdown('<div class="sidebar-section-title" style="margin-top:1rem;">Сессия</div>', unsafe_allow_html=True)
    if st.button("🗑️ Очистить чат", use_container_width=True, key="clear_chat"):
        st.session_state.messages = []
        for key in ["session_id", "llm_file", "vlm_file", "llm_file_sent", "vlm_file_sent",
                    "last_request_json", "last_response_json"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# ─── Топбар ──────────────────────────────────────────────────────────────────
logo_uri = get_local_logo_data_uri()
active_channel_name = st.session_state.channels[st.session_state.active_channel_idx]["name"]
active_channel_url = st.session_state.channels[st.session_state.active_channel_idx]["url"]
url_short = (active_channel_url[:48] + "…") if len(active_channel_url) > 50 else active_channel_url

st.markdown(
    f"""
    <div class="mts-topbar">
        <div class="mts-brand">
            <div class="mts-title-block">
                <div class="mts-subtitle">MTS AI · Cotype_Pro · Cotype_VL</div>
                <div class="mts-status-pill">
                    <span class="mts-status-dot"></span>
                    Доступ к платформе активен
                </div>
            </div>
        </div>
        <div style="display:flex;align-items:center;gap:.65rem;">
            <div style="font-size:.72rem;text-transform:uppercase;letter-spacing:.07em;color:#6B7280;">Активный канал</div>
            <div style="
                background: linear-gradient(135deg,#FF0033 0%,#FF5C7B 55%,#F97316 100%);
                color:#fff; border-radius:8px; padding:.3rem .75rem;
                font-size:.8rem; font-weight:600;
            ">{active_channel_name}</div>
            <div style="font-size:.72rem;color:#9CA3AF;max-width:320px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{url_short}</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─── Кнопки управления сайдбарами ─────────────────────────────────────────────
col_left_toggle, col_center_spacer, col_right_toggle = st.columns([1, 6, 1])

with col_left_toggle:
    if st.button("◀", key="toggle_left_sidebar", help="Свернуть левый сайдбар"):
        pass  # Streamlit sidebar управляется встроенно

with col_right_toggle:
    toggle_label = "▶" if not st.session_state.debug_panel_open else "◀"
    if st.button(toggle_label, key="toggle_right_sidebar", help="Показать/скрыть отладку"):
        st.session_state.debug_panel_open = not st.session_state.debug_panel_open
        st.rerun()

# ─── Layout с правым сайдбаром ───────────────────────────────────────────────
if st.session_state.debug_panel_open:
    main_col, debug_col = st.columns([3, 1])
else:
    main_col = st.container()
    debug_col = None

# ─── Центральная область ─────────────────────────────────────────────────────
with main_col:
    # Обработка файлов (без отображения)
    if "llm_uploader_processed" not in st.session_state:
        st.session_state.llm_uploader_processed = None
    if "vlm_uploader_processed" not in st.session_state:
        st.session_state.vlm_uploader_processed = None

    # Скрытые file_uploader — будем рендерить их через st.columns, минималистично
    upload_col1, upload_col2 = st.columns(2)

with upload_col1:
    llm_ready = "llm_file" in st.session_state
    st.markdown(
        f"""
        <div class="file-zone {'ready' if llm_ready else ''}">
            <div class="file-zone-label">
                {'✅' if llm_ready else '📄'} Файл для LLM
                <span class="mts-chip">Cotype_Pro</span>
            </div>
            <div class="file-zone-sub">txt, md, csv, xlsx, pdf, docx, json, py…</div>
            {'<div class="file-ready-badge">✓ Файл загружен и готов</div>' if llm_ready else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )
    llm_uploaded_file = st.file_uploader(
        "LLM",
        type=["txt","md","csv","xlsx","xls","pdf","docx","json","xml","py","js","html","css"],
        key="llm_file_uploader",
        label_visibility="collapsed",
    )
    if llm_uploaded_file is not None and llm_uploaded_file.name != st.session_state.llm_uploader_processed:
        with st.spinner("Обработка…"):
            processed_content, error = process_file_for_llm(llm_uploaded_file)
        if error:
            st.error(error)
        else:
            st.session_state.llm_file = processed_content
            st.session_state.llm_file_sent = False
            st.session_state.llm_uploader_processed = llm_uploaded_file.name
            st.rerun()
    if llm_ready:
        if st.button("🗑️ Удалить LLM файл", key="clear_llm"):
            del st.session_state.llm_file
            st.session_state.llm_uploader_processed = None
            st.rerun()

with upload_col2:
    vlm_ready = "vlm_file" in st.session_state
    st.markdown(
        f"""
        <div class="file-zone {'ready' if vlm_ready else ''}">
            <div class="file-zone-label">
                {'✅' if vlm_ready else '🖼️'} Файл для VLM
                <span class="mts-chip">Cotype_VL</span>
            </div>
            <div class="file-zone-sub">png, jpg, gif, webp, pdf…</div>
            {'<div class="file-ready-badge">✓ Файл загружен и готов</div>' if vlm_ready else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )
    vlm_uploaded_file = st.file_uploader(
        "VLM",
        type=["png","jpg","jpeg","gif","bmp","webp","pdf"],
        key="vlm_file_uploader",
        label_visibility="collapsed",
    )
    if vlm_uploaded_file is not None and vlm_uploaded_file.name != st.session_state.vlm_uploader_processed:
        with st.spinner("Конвертация…"):
            base64_content, error = process_file_for_vlm(vlm_uploaded_file)
        if error:
            st.error(error)
        else:
            st.session_state.vlm_file = base64_content
            st.session_state.vlm_file_sent = False
            st.session_state.vlm_uploader_processed = vlm_uploaded_file.name
            st.rerun()
    if vlm_ready:
        if st.button("🗑️ Удалить VLM файл", key="clear_vlm"):
            del st.session_state.vlm_file
            st.session_state.vlm_uploader_processed = None
            st.rerun()

# ─── Правый сайдбар (отладка) ─────────────────────────────────────────────────
if debug_col is not None:
    with debug_col:
        st.markdown(
            """
            <div class="mts-card">
                <div class="mts-card-header">
                    <div class="mts-card-title">
                        🔍 Отладка
                    </div>
                </div>
                <div class="mts-card-caption">
                    Отправляемые и получаемые JSON
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if "last_request_json" in st.session_state:
            st.markdown("### 📤 Отправленный JSON")
            with st.expander("Показать запрос", expanded=True):
                st.json(st.session_state.last_request_json)
        else:
            st.info("📤 Нет отправленных запросов")

        if "last_response_json" in st.session_state:
            st.markdown("### 📥 Полученный JSON")
            with st.expander("Показать ответ", expanded=True):
                st.json(st.session_state.last_response_json)
        else:
            st.info("📥 Нет полученных ответов")

        if "session_id" in st.session_state:
            st.markdown("### 🆔 Session ID")
            st.code(st.session_state.session_id, language="text")
        else:
            st.info("🆔 Session ID не создан")

        if "user_id" in st.session_state:
            st.markdown("### 👤 User ID")
            st.code(st.session_state.user_id, language="text")

        if "llm_file" in st.session_state:
            st.markdown("### 📄 LLM файл")
            st.text(st.session_state.llm_file[:200] + "...")

        if "vlm_file" in st.session_state:
            st.markdown("### 🖼️ VLM файл")
            st.text(st.session_state.vlm_file[:200] + "...")

# ─── Чат (всегда виден) ─────────────────────────────────────────────────────────
st.markdown('<div class="chat-wrapper">', unsafe_allow_html=True)
message_container = st.container()
with message_container:
    for msg in st.session_state.messages:
        role_class = "chat-user" if msg["role"] == "user" else "chat-assistant"
        content = msg["content"]
        timestamp = msg["timestamp"].strftime("%H:%M:%S") if "timestamp" in msg else ""
        st.markdown(
            f'<div class="chat-message {role_class}">{content}</div>'
            + (f'<div class="chat-timestamp">{timestamp}</div>' if timestamp else ""),
            unsafe_allow_html=True,
        )
st.markdown("</div>", unsafe_allow_html=True)

# ─── Поле ввода (всегда видимо) ───────────────────────────────────────────────
prompt = st.chat_input("Сформулируйте запрос к платформе МВС ИИ…")
if prompt:
    logger.info(f"User input: {prompt[:50]}...")

    user_timestamp = datetime.datetime.now()
    st.session_state.messages.append({"role": "user", "content": prompt, "timestamp": user_timestamp})

    with st.chat_message("user"):
        st.markdown(prompt)
        st.caption(user_timestamp.strftime("%H:%M:%S"))

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = generate_response(prompt)
        displayed = ""
        for word in full_response.split():
            displayed += word + " "
            placeholder.markdown(displayed)
            time.sleep(0.05)
        placeholder.markdown(full_response)
        timestamp = datetime.datetime.now()
        placeholder.caption(timestamp.strftime("%H:%M:%S"))

    st.session_state.messages.append({"role": "assistant", "content": full_response, "timestamp": timestamp})
    st.rerun()
