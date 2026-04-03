import json
import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QFont, QKeySequence, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


@dataclass
class CocoImage:
    id: int
    file_name: str
    width: int
    height: int


@dataclass
class CocoAnno:
    image_id: int
    category_id: int
    bbox: List[float]


class CocoViewer(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("COCO BBox Viewer")
        self.resize(1200, 800)

        self.json_path: Optional[str] = None
        self.image_dir: Optional[str] = None

        self.images: List[CocoImage] = []
        self.annos_by_image: Dict[int, List[CocoAnno]] = {}
        self.categories: Dict[int, str] = {}
        self.image_index = 0
        self.current_pixmap: Optional[QPixmap] = None

        self.image_label = QLabel("請先載入 COCO JSON 與圖片資料夾")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background:#111; color:#ddd; border:1px solid #333;")
        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

        self.status_label = QLabel("未載入資料")

        btn_json = QPushButton("載入 COCO JSON")
        btn_json.clicked.connect(self.load_json)

        btn_dir = QPushButton("選擇圖片資料夾")
        btn_dir.clicked.connect(self.load_image_dir)

        btn_prev = QPushButton("上一張 (PageUp)")
        btn_prev.clicked.connect(self.prev_image)

        btn_next = QPushButton("下一張 (PageDown)")
        btn_next.clicked.connect(self.next_image)

        top_bar = QHBoxLayout()
        top_bar.addWidget(btn_json)
        top_bar.addWidget(btn_dir)
        top_bar.addStretch(1)
        top_bar.addWidget(btn_prev)
        top_bar.addWidget(btn_next)

        root = QVBoxLayout()
        root.addLayout(top_bar)
        root.addWidget(self.image_label, stretch=1)
        root.addWidget(self.status_label)

        container = QWidget()
        container.setLayout(root)
        self.setCentralWidget(container)

        self._install_shortcuts()

    def _install_shortcuts(self) -> None:
        prev_action = QAction(self)
        prev_action.setShortcut(QKeySequence(Qt.Key_PageUp))
        prev_action.triggered.connect(self.prev_image)
        self.addAction(prev_action)

        next_action = QAction(self)
        next_action.setShortcut(QKeySequence(Qt.Key_PageDown))
        next_action.triggered.connect(self.next_image)
        self.addAction(next_action)

    def load_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "選擇 COCO JSON", "", "JSON Files (*.json)")
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "讀取失敗", f"無法讀取 JSON:\n{e}")
            return

        self.json_path = path
        self.categories = {c["id"]: c["name"] for c in data.get("categories", [])}
        self.images = [
            CocoImage(
                id=img["id"],
                file_name=img["file_name"],
                width=img.get("width", 0),
                height=img.get("height", 0),
            )
            for img in data.get("images", [])
        ]
        self.images.sort(key=lambda x: x.file_name)

        self.annos_by_image.clear()
        for a in data.get("annotations", []):
            image_id = a.get("image_id")
            bbox = a.get("bbox")
            cat_id = a.get("category_id")
            if image_id is None or bbox is None or cat_id is None:
                continue
            self.annos_by_image.setdefault(image_id, []).append(
                CocoAnno(image_id=image_id, category_id=cat_id, bbox=bbox)
            )

        self.image_index = 0
        self._refresh_view()

    def load_image_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "選擇圖片資料夾")
        if not path:
            return
        self.image_dir = path
        self._refresh_view()

    def prev_image(self) -> None:
        if not self.images:
            return
        self.image_index = max(0, self.image_index - 1)
        self._refresh_view()

    def next_image(self) -> None:
        if not self.images:
            return
        self.image_index = min(len(self.images) - 1, self.image_index + 1)
        self._refresh_view()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._render_current_pixmap()

    def _refresh_view(self, redraw_only: bool = False) -> None:
        if not self.images:
            self.status_label.setText("尚未載入 COCO images")
            if not redraw_only:
                self.image_label.setText("請載入 COCO JSON")
                self.image_label.setPixmap(QPixmap())
                self.current_pixmap = None
            return
        if not self.image_dir:
            self.status_label.setText(f"已載入 JSON，共 {len(self.images)} 張。請選擇圖片資料夾")
            if not redraw_only:
                self.image_label.setText("請選擇圖片資料夾")
                self.image_label.setPixmap(QPixmap())
                self.current_pixmap = None
            return

        img_info = self.images[self.image_index]
        img_path = os.path.join(self.image_dir, img_info.file_name)

        pix = QPixmap(img_path)
        if pix.isNull():
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText(f"無法讀取圖片:\n{img_path}")
            self.status_label.setText(
                f"{self.image_index + 1}/{len(self.images)} - {img_info.file_name} (讀取失敗)"
            )
            self.current_pixmap = None
            return

        self._draw_annotations(pix, self.annos_by_image.get(img_info.id, []))
        self.current_pixmap = pix
        self._render_current_pixmap()

        count = len(self.annos_by_image.get(img_info.id, []))
        self.status_label.setText(
            f"{self.image_index + 1}/{len(self.images)} | {img_info.file_name} | 標註數: {count}"
        )

    def _draw_annotations(self, pix: QPixmap, annos: List[CocoAnno]) -> None:
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)
        font = QFont()
        font.setPointSize(10)
        painter.setFont(font)

        for anno in annos:
            x, y, w, h = anno.bbox
            color = self._color_for_category(anno.category_id)
            pen = QPen(color, 2)
            painter.setPen(pen)
            painter.drawRect(int(x), int(y), int(w), int(h))

            name = self.categories.get(anno.category_id, f"cat:{anno.category_id}")
            text = f"{name}"
            label_bg = QColor(255, 255, 210, 230)
            painter.fillRect(int(x), max(0, int(y) - 20), 180, 20, label_bg)
            painter.setPen(QColor(20, 20, 20))
            painter.drawText(int(x) + 4, max(14, int(y) - 5), text)
            painter.setPen(pen)

        painter.end()

    def _render_current_pixmap(self) -> None:
        if self.current_pixmap is None:
            return
        shown = self.current_pixmap.scaled(
            self.image_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.image_label.setPixmap(shown)

    def _color_for_category(self, category_id: int) -> QColor:
        seed = category_id * 2654435761 % 0xFFFFFF
        r = (seed >> 16) & 0xFF
        g = (seed >> 8) & 0xFF
        b = seed & 0xFF
        return QColor(r, g, b)


def main() -> None:
    app = QApplication(sys.argv)
    viewer = CocoViewer()
    viewer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
