import base64
import io
import pandas as pd
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
from docx import Document
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

def process_file_for_llm(uploaded_file) -> Tuple[str, str]:
    """
    Обрабатывает файлы для Cotype_Pro (LLM)
    Возвращает кортеж (processed_content, error_message)
    """
    try:
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        if file_extension == 'txt':
            return process_txt_file(uploaded_file), ""
            
        elif file_extension == 'md':
            return process_md_file(uploaded_file), ""
            
        elif file_extension in ['csv']:
            return process_csv_file(uploaded_file), ""
            
        elif file_extension in ['xlsx', 'xls']:
            return process_excel_file(uploaded_file), ""
            
        elif file_extension == 'pdf':
            return process_pdf_with_ocr(uploaded_file), ""
            
        elif file_extension == 'docx':
            return process_docx_file(uploaded_file), ""
            
        elif file_extension in ['json', 'xml', 'py', 'js', 'html', 'css']:
            return process_text_based_file(uploaded_file), ""
            
        else:
            return "", f"❌ Неподдерживаемый формат файла: .{file_extension}"
            
    except Exception as e:
        logger.error(f"Error processing file {uploaded_file.name}: {e}")
        return "", f"❌ Ошибка обработки файла: {str(e)}"

def process_file_for_vlm(uploaded_file) -> Tuple[str, str]:
    """
    Обрабатывает файлы для Cotype_VL (VLM)
    Возвращает кортеж (base64_content, error_message)
    """
    try:
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        if file_extension in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']:
            return convert_image_to_base64(uploaded_file), ""
            
        elif file_extension == 'pdf':
            return convert_pdf_to_base64(uploaded_file), ""
            
        else:
            return "", f"❌ Для VLM блока поддерживаются только изображения и PDF"
            
    except Exception as e:
        logger.error(f"Error converting file {uploaded_file.name} to base64: {e}")
        return "", f"❌ Ошибка конвертации файла: {str(e)}"

def process_txt_file(uploaded_file) -> str:
    """Обрабатывает текстовые файлы"""
    try:
        content = uploaded_file.read().decode('utf-8')
        return f"📄 **Файл: {uploaded_file.name}**\n\n{content}"
    except UnicodeDecodeError:
        # Попытка с другой кодировкой
        content = uploaded_file.read().decode('latin-1')
        return f"📄 **Файл: {uploaded_file.name}**\n\n{content}"

def process_md_file(uploaded_file) -> str:
    """Обрабатывает Markdown файлы"""
    content = uploaded_file.read().decode('utf-8')
    return f"📝 **Markdown файл: {uploaded_file.name}**\n\n{content}"

def process_csv_file(uploaded_file) -> str:
    """Обрабатывает CSV файлы"""
    try:
        df = pd.read_csv(uploaded_file)
        content = f"📊 **CSV файл: {uploaded_file.name}**\n\n"
        content += f"Размер: {df.shape[0]} строк, {df.shape[1]} колонок\n\n"
        content += "Первые 10 строк:\n\n"
        content += df.head(10).to_string(index=False)
        content += "\n\nНазвания колонок:\n"
        content += ", ".join(df.columns.tolist())
        return content
    except Exception as e:
        raise Exception(f"Ошибка чтения CSV: {str(e)}")

def process_excel_file(uploaded_file) -> str:
    """Обрабатывает Excel файлы"""
    try:
        df = pd.read_excel(uploaded_file)
        content = f"📈 **Excel файл: {uploaded_file.name}**\n\n"
        content += f"Размер: {df.shape[0]} строк, {df.shape[1]} колонок\n\n"
        content += "Первые 10 строк:\n\n"
        content += df.head(10).to_string(index=False)
        content += "\n\nНазвания колонок:\n"
        content += ", ".join(df.columns.tolist())
        return content
    except Exception as e:
        raise Exception(f"Ошибка чтения Excel: {str(e)}")

def process_pdf_with_ocr(uploaded_file) -> str:
    """Обрабатывает PDF с помощью OCR"""
    try:
        pdf_bytes = uploaded_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        content = f"📕 **PDF файл: {uploaded_file.name}**\n\n"
        content += f"Количество страниц: {len(doc)}\n\n"
        
        full_text = ""
        
        # Сначала пробуем извлечь текст напрямую
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            if text.strip():
                full_text += f"\n--- Страница {page_num + 1} ---\n{text}\n"
        
        # Если текста мало, используем OCR
        if len(full_text.strip()) < 100:
            logger.info("Using OCR for PDF processing")
            for page_num in range(min(len(doc), 10)):  # Ограничиваем первые 10 страниц
                page = doc.load_page(page_num)
                pix = page.get_pixmap()
                img_bytes = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_bytes))
                
                text = pytesseract.image_to_string(image, lang='rus+eng')
                full_text += f"\n--- Страница {page_num + 1} (OCR) ---\n{text}\n"
        
        doc.close()
        return content + full_text
        
    except Exception as e:
        raise Exception(f"Ошибка обработки PDF: {str(e)}")

def process_docx_file(uploaded_file) -> str:
    """Обрабатывает DOCX файлы"""
    try:
        doc = Document(uploaded_file)
        content = f"📘 **DOCX файл: {uploaded_file.name}**\n\n"
        
        full_text = ""
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                full_text += paragraph.text + "\n"
        
        content += full_text
        return content
        
    except Exception as e:
        raise Exception(f"Ошибка чтения DOCX: {str(e)}")

def process_text_based_file(uploaded_file) -> str:
    """Обрабатывает текстовые файлы с кодом"""
    try:
        content = uploaded_file.read().decode('utf-8')
        file_extension = uploaded_file.name.split('.')[-1].lower()
        return f"💻 **{file_extension.upper()} файл: {uploaded_file.name}**\n\n```\n{content}\n```"
    except Exception as e:
        raise Exception(f"Ошибка чтения файла: {str(e)}")

def convert_image_to_base64(uploaded_file) -> str:
    """Конвертирует изображение в base64"""
    try:
        image_bytes = uploaded_file.read()
        base64_string = base64.b64encode(image_bytes).decode('utf-8')
        
        # Определяем MIME тип
        file_extension = uploaded_file.name.split('.')[-1].lower()
        mime_types = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'bmp': 'image/bmp',
            'webp': 'image/webp'
        }
        
        mime_type = mime_types.get(file_extension, 'image/png')
        
        return f"data:{mime_type};base64,{base64_string}"
        
    except Exception as e:
        raise Exception(f"Ошибка конвертации изображения: {str(e)}")

def convert_pdf_to_base64(uploaded_file) -> str:
    """Конвертирует PDF в изображение с ограничением на размер"""
    try:
        pdf_bytes = uploaded_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        if len(doc) == 0:
            raise Exception("PDF не содержит страниц")
        
        # Ограничиваем количество страниц
        max_pages = 10
        if len(doc) > max_pages:
            logger.warning(f"PDF имеет {len(doc)} страниц, будет обработано только первые {max_pages}")
        
        # Создаем универсальное изображение с ограничением
        universal_image = pdf_to_universal_grid(pdf_bytes, max_pages=max_pages)
        
        # Конвертируем в base64 с JPEG для сжатия
        img_bytes = io.BytesIO()
        universal_image.save(img_bytes, format='JPEG', quality=85, optimize=True)
        img_bytes.seek(0)
        
        base64_string = base64.b64encode(img_bytes.read()).decode('utf-8')
        doc.close()
        
        # Проверяем размер
        if len(base64_string) > 5_000_000:  # ~5MB limit
            raise Exception(f"PDF слишком большой после конвертации: {len(base64_string)} символов. Попробуйте PDF с меньшим количеством страниц.")
        
        logger.info(f"PDF конвертирован в base64: {len(base64_string)} символов")
        return f"data:image/jpeg;base64,{base64_string}"
        
    except Exception as e:
        raise Exception(f"Ошибка конвертации PDF: {str(e)}")

def pdf_to_universal_grid(pdf_bytes, max_width=1200, max_cell_height=800, padding=20, max_pages=10):
    """
    Универсальный алгоритм конвертации PDF в изображение с гибридной сеткой
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    portrait_pages = []
    landscape_pages = []
    
    # Уменьшаем DPI для многостраничных PDF
    dpi = 100 if len(doc) > 5 else 150
    
    # Анализируем и конвертируем страницы с ограничением
    for page_num in range(min(len(doc), max_pages)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(dpi=dpi)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        
        # Классифицируем по ориентации с порогом
        if img.height > img.width * 1.2:  # Портрет (с запасом)
            portrait_pages.append(img)
        else:  # Ландшафт или квадрат
            landscape_pages.append(img)
    
    result_images = []
    
    # Обрабатываем портретные страницы (2 колонки)
    if portrait_pages:
        portrait_grid = create_smart_grid(portrait_pages, 2, max_cell_height, max_width)
        result_images.append(portrait_grid)
    
    # Обрабатываем ландшафтные страницы (1 колонка)
    if landscape_pages:
        landscape_grid = create_smart_grid(landscape_pages, 1, max_cell_height, max_width)
        result_images.append(landscape_grid)
    
    doc.close()
    
    # Склеиваем все группы вертикально
    if len(result_images) == 1:
        return result_images[0]
    else:
        return concatenate_vertically(result_images, padding)

def create_smart_grid(images, cols=2, max_cell_height=800, max_width=1200):
    """
    Создает умную сетку с масштабированием и защитой от разрезания
    """
    if not images:
        return Image.new('RGB', (100, 100), color='white')
    
    # Масштабируем изображения до единого размера
    processed_images = []
    for img in images:
        # Сначала масштабируем по высоте если нужно
        if img.height > max_cell_height:
            scale_ratio = max_cell_height / img.height
            new_width = int(img.width * scale_ratio)
            img = img.resize((new_width, max_cell_height), Image.Resampling.LANCZOS)
        
        # Затем по ширине если нужно
        if img.width > max_width // cols:
            scale_ratio = (max_width // cols) / img.width
            new_height = int(img.height * scale_ratio)
            img = img.resize((max_width // cols, new_height), Image.Resampling.LANCZOS)
        
        processed_images.append(img)
    
    # Определяем размеры ячеек
    cell_width = max(img.width for img in processed_images)
    cell_height = max(img.height for img in processed_images)
    
    # Рассчитываем размеры сетки
    rows = (len(processed_images) + cols - 1) // cols
    grid_width = cell_width * cols
    grid_height = cell_height * rows
    
    # Создаем сетку
    grid_image = Image.new('RGB', (grid_width, grid_height), color='white')
    
    # Размещаем изображения
    for idx, img in enumerate(processed_images):
        row = idx // cols
        col = idx % cols
        
        # Центрируем изображение в ячейке
        x_offset = col * cell_width + (cell_width - img.width) // 2
        y_offset = row * cell_height + (cell_height - img.height) // 2
        
        grid_image.paste(img, (x_offset, y_offset))
    
    return grid_image

def concatenate_vertically(images, padding=20):
    """
    Склеивает изображения вертикально с отступами
    """
    if not images:
        return Image.new('RGB', (100, 100), color='white')
    
    # Определяем размеры итогового изображения
    max_width = max(img.width for img in images)
    total_height = sum(img.height for img in images) + padding * (len(images) - 1)
    
    # Создаем итоговое изображение
    result = Image.new('RGB', (max_width, total_height), color='white')
    
    # Размещаем изображения с центрированием
    y_offset = 0
    for img in images:
        x_offset = (max_width - img.width) // 2
        result.paste(img, (x_offset, y_offset))
        y_offset += img.height + padding
    
    return result
