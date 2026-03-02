# COCO BBox Checker (PySide6)

簡單的 Python GUI 工具，用來讀取標準 COCO 格式標註 JSON，搭配圖片資料夾，視覺化顯示每張圖的 bounding box。

## 功能
- 載入 COCO JSON (`images`, `annotations`, `categories`)
- 載入圖片資料夾（依 `images[].file_name` 尋找檔案）
- 在圖片上繪製 bbox 與類別名稱
- 使用 `PageUp` / `PageDown` 切換上一張 / 下一張

## 安裝
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 執行
```bash
python main.py
```

## 使用流程
1. 點選「載入 COCO JSON」
2. 點選「選擇圖片資料夾」
3. 用按鈕或 `PageUp/PageDown` 切換影像
