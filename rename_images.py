import os
import random
from PIL import Image, ImageEnhance

def create_advanced_augmented_images(source_dir, output_dir, num_duplicates=10):
    """
    讀取來源資料夾中的圖片，為每張圖片產生指定數量的、經過多種隨機增強的複本，
    以確保每張圖片的數位指紋都不同，從而繞過 Vertex AI 的近乎重複檢測。
    """
    print(f"開始進行高級圖片增強，來源：'{source_dir}'，輸出到：'{output_dir}'")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"已建立輸出資料夾：'{output_dir}'")

    for f in os.listdir(output_dir):
        os.remove(os.path.join(output_dir, f))
    print("已清空輸出資料夾，準備產生新圖片。")

    try:
        source_files = [f for f in os.listdir(source_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not source_files:
            print(f"錯誤：在 '{source_dir}' 中沒有找到任何圖片檔案。")
            return
    except FileNotFoundError:
        print(f"錯誤：找不到來源資料夾 '{source_dir}'。")
        return

    total_created = 0
    for source_filename in source_files:
        base_name, ext = os.path.splitext(source_filename)
        source_path = os.path.join(source_dir, source_filename)
        print(f"\n正在處理 '{source_filename}'...")

        for i in range(num_duplicates):
            try:
                with Image.open(source_path) as img:
                    # 確保是 RGB 模式
                    if img.mode != 'RGB':
                        img = img.convert('RGB')

                    # 1. 隨機進行小角度旋轉
                    if random.random() > 0.5:
                        angle = random.uniform(-5, 5)
                        img = img.rotate(angle, resample=Image.BICUBIC, expand=True)
                        # 旋轉後可能會有多餘的黑邊，將其裁切掉
                        img = img.crop(img.getbbox())

                    # 2. 隨機進行水平翻轉
                    if random.random() > 0.5:
                        img = img.transpose(Image.FLIP_LEFT_RIGHT)

                    # 3. 隨機調整亮度
                    if random.random() > 0.5:
                        enhancer = ImageEnhance.Brightness(img)
                        factor = random.uniform(0.8, 1.2) # 在 80% 到 120% 之間調整
                        img = enhancer.enhance(factor)

                    # 4. 隨機調整對比度
                    if random.random() > 0.5:
                        enhancer = ImageEnhance.Contrast(img)
                        factor = random.uniform(0.8, 1.2)
                        img = enhancer.enhance(factor)
                    
                    # 5. 隨機調整飽和度
                    if random.random() > 0.5:
                        enhancer = ImageEnhance.Color(img)
                        factor = random.uniform(0.8, 1.2)
                        img = enhancer.enhance(factor)

                    new_filename = f"{base_name}_{i}.jpg"
                    new_path = os.path.join(output_dir, new_filename)
                    img.save(new_path, 'JPEG')
                    total_created += 1

            except Exception as e:
                print(f"處理 '{source_filename}' 的第 {i} 個複本時發生錯誤: {e}")
    
    print(f"\n高級增強完成！總共在 '{output_dir}' 中建立了 {total_created} 個獨一無二的圖片檔案。")


if __name__ == "__main__":
    # --- 請設定您的資料夾路徑 ---

    # 1. 包含您 3 張原始回饋圖片的資料夾
    SOURCE_IMAGE_DIRECTORY = "d:\\plant_backend\\static\\feedback_uploads"

    # 2. 用於存放 30 張新產生圖片的資料夾
    OUTPUT_DIRECTORY = "d:\\plant_backend\\augmented_images"
    
    # 在執行腳本前，請確保已安裝 Pillow 庫: pip install Pillow
    print("準備開始產生『高級增強版』玩具資料...")
    create_advanced_augmented_images(SOURCE_IMAGE_DIRECTORY, OUTPUT_DIRECTORY)