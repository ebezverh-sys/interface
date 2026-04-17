import streamlit as st
import time
import datetime
import uuid
import base64
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

        # Сохраняем отправляемый JSON для отладки
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

st.markdown(
    """
    <style>
        body {
            background-color: #F5F5F5;
        }

        .main {
            background: #F5F5F5;
            color: #1F2937;
        }

        .mts-topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.75rem 1.25rem;
            border-radius: 16px;
            margin-bottom: 1rem;
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .mts-brand {
            display: flex;
            align-items: center;
            gap: 0.85rem;
        }

        .mts-logo {
            width: 84px;
            height: 84px;
            object-fit: contain;
            border-radius: 10px;
            background: #FFFFFF;
            padding: 0.15rem;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .mts-title-block {
            display: flex;
            flex-direction: column;
            gap: 0.15rem;
        }

        .mts-title {
            font-size: 1.1rem;
            font-weight: 600;
            letter-spacing: 0.03em;
            color: #1F2937;
        }

        .mts-subtitle {
            font-size: 0.8rem;
            color: #6B7280;
        }

        .mts-status-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.1rem 0.6rem;
            border-radius: 999px;
            background: #DCFCE7;
            border: 1px solid #22C55E;
            font-size: 0.75rem;
            color: #166534;
        }

        .mts-status-dot {
            width: 7px;
            height: 7px;
            border-radius: 999px;
            background: #22C55E;
            box-shadow: 0 0 0 4px rgba(34, 197, 94, 0.25);
        }

        .mts-url-wrapper {
            display: flex;
            flex-direction: column;
            gap: 0.3rem;
            min-width: 320px;
            max-width: 540px;
        }

        .mts-url-label {
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #6B7280;
        }

        .mts-card {
            background: #FFFFFF;
            border-radius: 18px;
            padding: 0.85rem 1rem 1rem 1rem;
            border: 1px solid #E5E7EB;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            margin-bottom: 0.9rem;
        }

        .mts-card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.3rem;
        }

        .mts-card-title {
            font-size: 0.88rem;
            font-weight: 600;
            color: #1F2937;
            display: flex;
            align-items: center;
            gap: 0.35rem;
        }

        .mts-chip {
            display: inline-flex;
            align-items: center;
            padding: 0.08rem 0.55rem;
            border-radius: 999px;
            font-size: 0.7rem;
            border: 1px solid #E5E7EB;
            color: #FFFFFF;
            background: linear-gradient(135deg, #FF0033 0%, #FF5C7B 55%, #F97316 100%);
        }

        .mts-card-caption {
            font-size: 0.8rem;
            color: #6B7280;
            margin-bottom: 0.4rem;
        }

        div.stButton > button:first-child {
            border-radius: 999px;
            border: none;
            background: linear-gradient(135deg, #FF0033 0%, #FF5C7B 45%, #F97316 100%);
            color: #FFFFFF;
            font-weight: 500;
            font-size: 0.78rem;
            padding: 0.35rem 0.95rem;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        div.stButton > button:first-child:hover {
            background: linear-gradient(135deg, #FF2450 0%, #FF6C88 45%, #FB923C 100%);
        }

        div[data-baseweb="select"] > div {
            border-radius: 999px;
        }

        .chat-wrapper {
            background: #FFFFFF;
            border-radius: 18px;
            border: 1px solid #E5E7EB;
            padding: 0.85rem 1rem 0.5rem 1rem;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }

        .chat-message {
            padding: 0.55rem 0.8rem;
            border-radius: 14px;
            margin-bottom: 0.45rem;
            max-width: 92%;
            font-size: 0.9rem;
            line-height: 1.45;
        }

        .chat-user {
            margin-left: auto;
            background: #F3F4F6;
            border: 1px solid #D1D5DB;
        }

        .chat-assistant {
            margin-right: auto;
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
        }

        .chat-timestamp {
            font-size: 0.7rem;
            color: #6B7280;
            margin-top: 0.08rem;
        }

        .stChatInputContainer textarea {
            border-radius: 999px !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="mts-topbar">
        <div class="mts-brand">
            <img
                class="mts-logo"
                src="{get_local_logo_data_uri()}"
                alt="Логотип МВС ИИ"
            />
            <div class="mts-title-block">
                <div class="mts-title">Интерфейс к Платформе МВС ИИ</div>
                <div class="mts-subtitle">MTS AI · Cotype_Pro · Cotype_VL</div>
                <div class="mts-status-pill">
                    <span class="mts-status-dot"></span>
                    Доступ к платформе активен
                </div>
            </div>
        </div>
        <div class="mts-url-wrapper">
            <div class="mts-url-label">URL канала платформы</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if "platform_channel_url" not in st.session_state:
    st.session_state.platform_channel_url = "https://thrillingly-affordable-hippo.cloudpub.ru/api/e72f886e-4b62-47bb-894e-5622f3ea5ce3"

st.session_state.platform_channel_url = st.text_input(
    "",
    value=st.session_state.platform_channel_url,
    help="Полный адрес канала для подключения к API",
    key="platform_channel_url_input",
)

settings_col, chat_col, debug_col = st.columns([1, 3, 1])

with settings_col:
    st.markdown(
        """
        <div class="mts-card">
            <div class="mts-card-header">
                <div class="mts-card-title">
                    📄 Файлы для Cotype_Pro
                    <span class="mts-chip">LLM</span>
                </div>
            </div>
            <div class="mts-card-caption">
                Текст, таблицы, PDF (OCR). Данные используются как контекст для Pro‑модели.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    llm_uploaded_file = st.file_uploader(
        "Загрузите файл",
        type=[
            "txt",
            "md",
            "csv",
            "xlsx",
            "xls",
            "pdf",
            "docx",
            "json",
            "xml",
            "py",
            "js",
            "html",
            "css",
        ],
        key="llm_file_uploader",
        help="Поддерживаемые форматы: текстовые, таблицы, PDF, документы",
    )

    if llm_uploaded_file is not None:
        with st.spinner("Обработка файла..."):
            processed_content, error = process_file_for_llm(llm_uploaded_file)
            if error:
                st.error(error)
            else:
                st.session_state.llm_file = processed_content
                st.session_state.llm_file_sent = False
                st.success("✅ Файл обработан и готов к отправке")
                st.text_area("Предпросмотр:", processed_content, height=200)

    if "llm_file" in st.session_state:
        st.info("📋 LLM файл готов к отправке")
        if st.button("🗑️ Удалить LLM файл", key="clear_llm"):
            del st.session_state.llm_file
            st.rerun()

    st.markdown(
        """
        <div class="mts-card">
            <div class="mts-card-header">
                <div class="mts-card-title">
                    🖼️ Файлы для Cotype_VL
                    <span class="mts-chip">VLM</span>
                </div>
            </div>
            <div class="mts-card-caption">
                Изображения и PDF конвертируются в единый base64‑вид для визуальной модели.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    vlm_uploaded_file = st.file_uploader(
        "Загрузите файл",
        type=["png", "jpg", "jpeg", "gif", "bmp", "webp", "pdf"],
        key="vlm_file_uploader",
        help="Поддерживаемые форматы: изображения, PDF",
    )

    if vlm_uploaded_file is not None:
        with st.spinner("Конвертация в base64..."):
            base64_content, error = process_file_for_vlm(vlm_uploaded_file)
            if error:
                st.error(error)
            else:
                st.session_state.vlm_file = base64_content
                st.session_state.vlm_file_sent = False
                st.success("✅ Файл сконвертирован в base64")
                st.text_area(
                    "Base64 (первые 200 символов):", base64_content[:200] + "...", height=100
                )

    if "vlm_file" in st.session_state:
        st.info("🖼️ VLM файл готов к отправке")
        if st.button("🗑️ Удалить VLM файл", key="clear_vlm"):
            del st.session_state.vlm_file
            st.rerun()

    st.markdown(
        """
        <div class="mts-card">
            <div class="mts-card-header">
                <div class="mts-card-title">
                    ⚙️ Настройки
                </div>
            </div>
            <div class="mts-card-caption">
                Управляйте сессией диалога и контекстом файлов.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("🗑️ Очистить чат", key="clear_chat"):
        st.session_state.messages = []
        if "session_id" in st.session_state:
            del st.session_state.session_id
        if "llm_file" in st.session_state:
            del st.session_state.llm_file
        if "vlm_file" in st.session_state:
            del st.session_state.vlm_file
        if "llm_file_sent" in st.session_state:
            del st.session_state.llm_file_sent
        if "vlm_file_sent" in st.session_state:
            del st.session_state.vlm_file_sent
        if "last_request_json" in st.session_state:
            del st.session_state.last_request_json
        if "last_response_json" in st.session_state:
            del st.session_state.last_response_json
        st.rerun()

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

with chat_col:
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
        logger.info(f"New session started, user_id: {st.session_state.user_id}")
    if "messages" not in st.session_state:
        st.session_state.messages = []

    st.markdown('<div class="chat-wrapper">', unsafe_allow_html=True)
    message_container = st.container()
    with message_container:
        for msg in st.session_state.messages:
            role_class = "chat-user" if msg["role"] == "user" else "chat-assistant"
            content = msg["content"]
            timestamp = (
                msg["timestamp"].strftime("%H:%M:%S") if "timestamp" in msg else ""
            )
            st.markdown(
                f'<div class="chat-message {role_class}">{content}</div>'
                + (f'<div class="chat-timestamp">{timestamp}</div>' if timestamp else ""),
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)

    prompt = st.chat_input("Сформулируйте запрос к платформе МВС ИИ...")
    if prompt:
        logger.info(f"User input: {prompt[:50]}...")

        user_timestamp = datetime.datetime.now()
        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt,
                "timestamp": user_timestamp,
            }
        )

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

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": full_response,
                "timestamp": timestamp,
            }
        )

        st.rerun()