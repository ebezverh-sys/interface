import streamlit as st
import time
import datetime
import uuid
from adapter import send_to_engine, get_session, logger
from file_processors import process_file_for_llm, process_file_for_vlm

def generate_response(user_input: str) -> str:
    try:
        logger.info(f"Generating response for input: {user_input}...")
        
        # Получаем session id, если его нет
        if "session_id" not in st.session_state:
            logger.info("Getting new session_id...")
            st.session_state.session_id = get_session(st.session_state.user_id, st.session_state.platform_channel_url)
            logger.info(f"Received session_id: {st.session_state.session_id}")
        
        # Собираем метаданные с файлами
        meta = {}
        
        # Добавляем LLM файл если есть и еще не передавали
        if "llm_file" in st.session_state and not st.session_state.get("llm_file_sent", False):
            meta["llm_file"] = st.session_state.llm_file
            st.session_state.llm_file_sent = True
            logger.info("Added LLM file to metadata")
        
        # Добавляем VLM файл если есть и еще не передавали
        if "vlm_file" in st.session_state and not st.session_state.get("vlm_file_sent", False):
            meta["vlm_file"] = st.session_state.vlm_file
            st.session_state.vlm_file_sent = True
            logger.info("Added VLM file to metadata")
        
        start_time = time.time()
        api_response = send_to_engine(st.session_state.user_id, st.session_state.session_id, text=user_input, meta=meta, platform_channel_url=st.session_state.platform_channel_url)
        elapsed = time.time() - start_time
        logger.info(f"API response received in {elapsed:.2f}s")
        
        all_messages = []
        if isinstance(api_response, list):
            for response_item in api_response:
                if "payload" in response_item and "items" in response_item["payload"]:
                    items = response_item["payload"]["items"]
                    for item in items:
                        if "bubble" in item and "value" in item["bubble"]:
                            all_messages.append(item["bubble"]["value"])
        if all_messages:
            # Заменяем <br/> на переносы строк
            processed_messages = [msg.replace("<br/>", "\n") for msg in all_messages]
            return "\n\n---\n\n".join(processed_messages)
        return f"**API Response:**\n```json\n{str(api_response)}\n```"
    except Exception as e:
        logger.error(f"Error communicating with API: {e}")
        return f"Error communicating with API: {str(e)}"

st.set_page_config(
    page_title="Интерфейс к Платформе МВС ИИ",
    page_icon="",
    layout="wide",
)

st.title("Интерфейс к Платформе МВС ИИ")
st.markdown("Выберите канал и задайте свой вопрос")

# Поле для ввода URL на всю ширину сверху
if "platform_channel_url" not in st.session_state:
    st.session_state.platform_channel_url = "https://http-adapter-demo03.mws.ai.local/api/557cfd75-6f18-4e48-9af8-de9a2c40cbe6"

st.session_state.platform_channel_url = st.text_input(
    "URL канала платформы",
    value=st.session_state.platform_channel_url,
    help="Полный адрес канала для подключения к API",
    key="platform_channel_url_input"
)

# Создаем колонки: 1/4 для настроек, 3/4 для чата
settings_col, chat_col = st.columns([1, 3])

with settings_col:
    # Блок для Cotype_Pro файлов
    st.header("📄 Файлы для Cotype_Pro")
    st.markdown("*Текст, таблицы, PDF (OCR)*")
    
    llm_uploaded_file = st.file_uploader(
        "Загрузите файл",
        type=["txt", "md", "csv", "xlsx", "xls", "pdf", "docx", "json", "xml", "py", "js", "html", "css"],
        key="llm_file_uploader",
        help="Поддерживаемые форматы: текстовые, таблицы, PDF, документы"
    )
    
    if llm_uploaded_file is not None:
        with st.spinner("Обработка файла..."):
            processed_content, error = process_file_for_llm(llm_uploaded_file)
            if error:
                st.error(error)
            else:
                st.session_state.llm_file = processed_content
                st.success("✅ Файл обработан и готов к отправке")
                st.text_area("Предпросмотр:", processed_content, height=200)
    
    if "llm_file" in st.session_state:
        st.info("📋 LLM файл готов к отправке")
        if st.button("🗑️ Удалить LLM файл", key="clear_llm"):
            del st.session_state.llm_file
            st.rerun()
    
    st.markdown("---")
    
    # Блок для Cotype_VL файлов
    st.header("🖼️ Файлы для Cotype_VL")
    st.markdown("*Изображения, PDF (base64)*")
    
    vlm_uploaded_file = st.file_uploader(
        "Загрузите файл",
        type=["png", "jpg", "jpeg", "gif", "bmp", "webp", "pdf"],
        key="vlm_file_uploader",
        help="Поддерживаемые форматы: изображения, PDF"
    )
    
    if vlm_uploaded_file is not None:
        with st.spinner("Конвертация в base64..."):
            base64_content, error = process_file_for_vlm(vlm_uploaded_file)
            if error:
                st.error(error)
            else:
                st.session_state.vlm_file = base64_content
                st.success("✅ Файл сконвертирован в base64")
                st.text_area("Base64 (первые 200 символов):", base64_content[:200] + "...", height=100)
    
    if "vlm_file" in st.session_state:
        st.info("🖼️ VLM файл готов к отправке")
        if st.button("🗑️ Удалить VLM файл", key="clear_vlm"):
            del st.session_state.vlm_file
            # Сбрасываем флаг предпросмотра для следующего файла (временно отключен)
            # if "vlm_preview_shown" in st.session_state:
            #     del st.session_state.vlm_preview_shown
            st.rerun()
    
    st.markdown("---")
    
    # Блок настроек - перемещен в самый низ
    st.header("⚙️ Настройки")
    
    # Кнопка очистки чата
    if st.button("🗑️ Очистить чат", key="clear_chat"):
        st.session_state.messages = []
        # Сбрасываем session_id при очистке чата
        if "session_id" in st.session_state:
            del st.session_state.session_id
        # Сбрасываем файлы
        if "llm_file" in st.session_state:
            del st.session_state.llm_file
        if "vlm_file" in st.session_state:
            del st.session_state.vlm_file
        # Сбрасываем флаги отправки файлов
        if "llm_file_sent" in st.session_state:
            del st.session_state.llm_file_sent
        if "vlm_file_sent" in st.session_state:
            del st.session_state.vlm_file_sent
        st.rerun()

with chat_col:
    # ВРЕМЕННЫЙ ФУНКЦИОНАЛ: Предпросмотр обработанного изображения (временно отключен)
    # if "vlm_file" in st.session_state and "vlm_preview_shown" not in st.session_state:
    #     st.markdown("---")
    #     st.markdown("### 🖼️ Предпросмотр обработанного изображения (временно)")
    #     
    #     try:
    #         import io
    #         from PIL import Image
    #         import base64
    #         
    #         base64_content = st.session_state.vlm_file
    #         base64_data = base64_content.split(',')[1]
    #         img_bytes = base64.b64decode(base64_data)
    #         img = Image.open(io.BytesIO(img_bytes))
    #         
    #         st.image(img, caption="Обработанное изображение для VLM", use_column_width=True)
    #         st.info(f"Размер изображения: {img.width}x{img.height} px")
    #         
    #         # Помечаем, что предпросмотр уже показан
    #         st.session_state.vlm_preview_shown = True
    #         
    #     except Exception as e:
    #         st.warning(f"Не удалось показать предпросмотр: {e}")
    #     
    #     st.markdown("---")
    
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
        logger.info(f"New session started, user_id: {st.session_state.user_id}")
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Отображаем сообщения
    message_container = st.container()
    with message_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if "timestamp" in msg:
                    st.caption(msg["timestamp"].strftime('%H:%M:%S'))

    # Поле ввода всегда внизу
    if prompt := st.chat_input("Введите ваше сообщение..."):
        logger.info(f"User input: {prompt[:50]}...")
        
        # Добавляем сообщение пользователя
        user_timestamp = datetime.datetime.now()
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
            "timestamp": user_timestamp
        })
        
        # Показываем сообщение пользователя сразу
        with st.chat_message("user"):
            st.markdown(prompt)
            st.caption(user_timestamp.strftime('%H:%M:%S'))
        
        # Генерируем ответ с эффектом печатания
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_response = generate_response(prompt)
            displayed = ""
            
            # Эффект печати
            for word in full_response.split():
                displayed += word + " "
                placeholder.markdown(displayed)
                time.sleep(0.05)
            
            # Финальный вывод
            placeholder.markdown(full_response)
            timestamp = datetime.datetime.now()
            placeholder.caption(timestamp.strftime('%H:%M:%S'))
        
        # Добавляем ответ ассистента в сессию
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
            "timestamp": timestamp
        })
        
        # Перерисовываем чтобы обновить историю
        st.rerun()