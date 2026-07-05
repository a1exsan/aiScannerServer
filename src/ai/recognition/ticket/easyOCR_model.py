import os
import cv2
import numpy as np
import base64
import easyocr

class easyOCRreader:
    def __init__(self):
        self.recognized_text_label = None
        self.image_preview_widget = None
        self.fps_counter_label = None
        self.frame_count = 0

        self.size_params = (480, 270)

        self.reader = easyocr.Reader(['ru', 'en'], gpu=False)

    def recognise(self, image_data):
        try:
            self.frame_count += 1
            print(f" -> [FastAPI Поток] Получен кадр №{self.frame_count} ({len(image_data)} bytes)", flush=True)

            if self.fps_counter_label:
                self.fps_counter_label.set_text(f"Принято кадров: {self.frame_count}")

            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return {'status': 'next', 'message': 'Ошибка декодирования'}

            #cv2.imwrite('debug_raw.jpg', img)

            # Оптимизация размера для CPU (ускорение расчетов в 4 раза)
            img_resized = cv2.resize(img, self.size_params, interpolation=cv2.INTER_AREA)

            # ЗАПУСК ИНФЕРЕНСА (В пуле потоков)
            # easyocr принимает на вход обычную матрицу OpenCV напрямую
            ocr_result = self.reader.readtext(img_resized)

            lines_text = []
            text_found = False

            # РАЗБОР ФОРМАТА ОТВЕТА EASYOCR [ ( [box], "текст", уверенность ), ... ]
            if ocr_result and isinstance(ocr_result, list):
                h_orig, w_orig = img.shape[:2]
                h_res, w_res = img_resized.shape[:2]

                scale_x = w_orig / w_res
                scale_y = h_orig / h_res

                for item in ocr_result:
                    # Структура ответа EasyOCR строго: ( [координаты], "Чистый Текст", score )
                    box = item[0]
                    text = str(item[1]).strip()
                    score = float(item[2])

                    # Отсекаем явный шум, пропускаем нормальные русские слова
                    if text and score > 0.35:
                        lines_text.append(text)
                        text_found = True

                        # Восстанавливаем оригинальные координаты для отрисовки рамок
                        pts = np.array(box, dtype=np.float32)
                        pts[:, 0] *= scale_x
                        pts[:, 1] *= scale_y
                        pts = pts.astype(np.int32)

                        cv2.polylines(img, [pts], isClosed=True, color=(0, 0, 255), thickness=2)

            if text_found and len(lines_text) > 0:
                final_text = "\n\n".join(lines_text)
                #print(f"\n🚀 [ИИ УСПЕХ] ТЕКСТ УСПЕШНО ВЫТАЩЕН:\n{final_text}\n", flush=True)

                _, img_encoded = cv2.imencode('.jpg', img)
                img_base64 = base64.b64encode(img_encoded).decode('utf-8')

                save_path = 'uploaded_scan.jpg'
                cv2.imwrite(save_path, img)

                if self.recognized_text_label and self.image_preview_widget:
                    self.recognized_text_label.set_content(f"📋 **Результат EasyOCR:**\n\n{final_text}")
                    self.image_preview_widget.set_source('uploaded_scan.jpg?v=' + os.urandom(4).hex())

                return {
                    'status': 'stop',
                    'text': final_text,
                    'image': img_base64
                }

            else:
                return {'status': 'next', 'message': 'Поиск этикетки...'}

        except Exception as e:
            print(f" ❌ Ошибка ИИ-обработки кадра: {str(e)}", flush=True)
            return {'status': 'next', 'message': str(e)}