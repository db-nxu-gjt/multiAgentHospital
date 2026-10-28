"""
专业矢量图标渲染器

不使用 emoji，避免跨平台/打包字体差异导致截断或显示异常。
所有图标通过 QPainter 绘制为 QPixmap，可设置尺寸与颜色。
"""
from PyQt6.QtCore import Qt, QSize, QRect, QPoint
from PyQt6.QtGui import QPainter, QPixmap, QColor, QPen, QBrush, QFont, QFontMetrics


def _rounded_rect(painter: QPainter, rect, radius, fill, border=None):
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QBrush(fill))
    if border:
        painter.setPen(QPen(border, 1))
    else:
        painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(rect, radius, radius)


def _draw_text_center(painter: QPainter, rect, text, color, font_size):
    painter.setPen(QPen(color))
    font = QFont("Microsoft YaHei", font_size, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)


def hospital_icon(size: int = 48, color: str = "#1a73e8", bg: str = "#e8f1fd") -> QPixmap:
    """医院建筑+十字图标"""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    margin = size * 0.12
    body = QRect(int(margin), int(margin * 1.5), int(size - 2 * margin), int(size - 2 * margin))
    # 建筑主体
    p.setBrush(QBrush(QColor(bg)))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(body, size * 0.12, size * 0.12)
    # 屋顶
    roof = QRect(int(size * 0.2), int(size * 0.25), int(size * 0.6), int(size * 0.18))
    p.setBrush(QBrush(QColor(color)))
    p.drawRoundedRect(roof, size * 0.04, size * 0.04)
    # 十字
    cx, cy = size // 2, int(size * 0.62)
    bar_w, bar_h = int(size * 0.32), int(size * 0.10)
    p.drawRoundedRect(cx - bar_w // 2, cy - bar_h // 2, bar_w, bar_h, size * 0.02, size * 0.02)
    p.drawRoundedRect(cx - bar_h // 2, cy - bar_w // 2, bar_h, bar_w, size * 0.02, size * 0.02)
    # 门
    door = QRect(int(size * 0.42), int(size * 0.75), int(size * 0.16), int(size * 0.18))
    p.setBrush(QBrush(QColor(color).lighter(130)))
    p.drawRoundedRect(door, size * 0.02, size * 0.02)
    p.end()
    return pm


def dashboard_icon(size: int = 20, color: str = "#1a73e8") -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor(color)))
    w = size
    p.drawRoundedRect(int(w * 0.05), int(w * 0.05), int(w * 0.42), int(w * 0.42), 2, 2)
    p.drawRoundedRect(int(w * 0.53), int(w * 0.05), int(w * 0.42), int(w * 0.25), 2, 2)
    p.drawRoundedRect(int(w * 0.53), int(w * 0.38), int(w * 0.42), int(w * 0.57), 2, 2)
    p.drawRoundedRect(int(w * 0.05), int(w * 0.53), int(w * 0.42), int(w * 0.42), 2, 2)
    p.end()
    return pm


def patient_icon(size: int = 20, color: str = "#0d904f") -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(color), max(1.5, size * 0.12), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    head_r = size * 0.22
    p.drawEllipse(QPoint(int(size * 0.5), int(size * 0.32)), int(head_r), int(head_r))
    p.drawArc(int(size * 0.18), int(size * 0.55), int(size * 0.64), int(size * 0.55), 0, 180 * 16)
    p.end()
    return pm


def stethoscope_icon(size: int = 20, color: str = "#e8710a") -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), max(1.5, size * 0.12), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    # 简化为听诊器U形
    p.drawArc(int(size * 0.25), int(size * 0.15), int(size * 0.5), int(size * 0.5), 0, 180 * 16)
    p.drawLine(int(size * 0.25), int(size * 0.40), int(size * 0.25), int(size * 0.75))
    p.drawLine(int(size * 0.75), int(size * 0.40), int(size * 0.75), int(size * 0.75))
    p.drawEllipse(int(size * 0.20), int(size * 0.72), int(size * 0.10), int(size * 0.10))
    p.drawEllipse(int(size * 0.70), int(size * 0.72), int(size * 0.10), int(size * 0.10))
    p.end()
    return pm


def report_icon(size: int = 20, color: str = "#9c27b0") -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(color), max(1.5, size * 0.10)))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(int(size * 0.20), int(size * 0.10), int(size * 0.60), int(size * 0.80), 2, 2)
    p.setPen(QPen(QColor(color), max(1.2, size * 0.08)))
    for i, y in enumerate([0.32, 0.45, 0.58, 0.71]):
        p.drawLine(int(size * 0.28), int(size * y), int(size * (0.72 if i < 3 else 0.55)), int(size * y))
    p.end()
    return pm


def folder_icon(size: int = 20, color: str = "#5f6368") -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor(color)))
    p.drawRoundedRect(int(size * 0.10), int(size * 0.30), int(size * 0.80), int(size * 0.55), 3, 3)
    p.drawRoundedRect(int(size * 0.10), int(size * 0.18), int(size * 0.40), int(size * 0.22), 3, 3)
    p.end()
    return pm


def gear_icon(size: int = 20, color: str = "#607d8b") -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor(color)))
    cx, cy, r = size // 2, size // 2, size * 0.38
    teeth = 8
    for i in range(teeth):
        angle = i * 360 / teeth
        p.save()
        p.translate(cx, cy)
        p.rotate(angle)
        p.drawRoundedRect(int(-size * 0.06), int(-r - size * 0.06), int(size * 0.12), int(size * 0.22), 1, 1)
        p.restore()
    p.drawEllipse(QPoint(cx, cy), int(size * 0.22), int(size * 0.22))
    p.setBrush(QBrush(QColor("white")))
    p.drawEllipse(QPoint(cx, cy), int(size * 0.10), int(size * 0.10))
    p.end()
    return pm


def shield_icon(size: int = 20, color: str = "#d93025") -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(color), max(1.5, size * 0.10)))
    p.setBrush(Qt.BrushStyle.NoBrush)
    path_points = [
        QPoint(int(size * 0.5), int(size * 0.10)),
        QPoint(int(size * 0.85), int(size * 0.25)),
        QPoint(int(size * 0.75), int(size * 0.75)),
        QPoint(int(size * 0.5), int(size * 0.90)),
        QPoint(int(size * 0.25), int(size * 0.75)),
        QPoint(int(size * 0.15), int(size * 0.25)),
    ]
    p.drawPolygon(*path_points)
    p.setPen(QPen(QColor(color), max(2, size * 0.14), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(int(size * 0.5), int(size * 0.38), int(size * 0.5), int(size * 0.55))
    p.drawPoint(int(size * 0.5), int(size * 0.65))
    p.end()
    return pm


def check_icon(size: int = 16, color: str = "#0d904f") -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(color), max(2, size * 0.15), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(int(size * 0.20), int(size * 0.50), int(size * 0.42), int(size * 0.72))
    p.drawLine(int(size * 0.40), int(size * 0.72), int(size * 0.82), int(size * 0.28))
    p.end()
    return pm


def user_icon(size: int = 20, color: str = "#5f6368") -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(color), max(1.5, size * 0.12), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawEllipse(QPoint(int(size * 0.5), int(size * 0.32)), int(size * 0.18), int(size * 0.18))
    p.drawArc(int(size * 0.22), int(size * 0.52), int(size * 0.56), int(size * 0.50), 0, 180 * 16)
    p.end()
    return pm


def lock_icon(size: int = 20, color: str = "#5f6368") -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(color), max(1.5, size * 0.12)))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawArc(int(size * 0.28), int(size * 0.12), int(size * 0.44), int(size * 0.40), 0, 180 * 16)
    p.drawRoundedRect(int(size * 0.18), int(size * 0.40), int(size * 0.64), int(size * 0.48), 3, 3)
    p.drawLine(int(size * 0.5), int(size * 0.58), int(size * 0.5), int(size * 0.68))
    p.end()
    return pm


def logout_icon(size: int = 20, color: str = "#d93025") -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(color), max(1.5, size * 0.12), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(int(size * 0.55), int(size * 0.20), int(size * 0.55), int(size * 0.45))
    p.drawLine(int(size * 0.55), int(size * 0.55), int(size * 0.55), int(size * 0.80))
    p.drawLine(int(size * 0.55), int(size * 0.50), int(size * 0.82), int(size * 0.50))
    p.drawArc(int(size * 0.10), int(size * 0.18), int(size * 0.55), int(size * 0.64), 90 * 16, 180 * 16)
    p.end()
    return pm


def upload_icon(size: int = 20, color: str = "#2563eb") -> QPixmap:
    """上传图标：带向上箭头的托盘"""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(color), max(1.5, size * 0.12), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    # 向上箭头
    p.drawLine(int(size * 0.5), int(size * 0.72), int(size * 0.5), int(size * 0.28))
    p.drawLine(int(size * 0.32), int(size * 0.46), int(size * 0.5), int(size * 0.28))
    p.drawLine(int(size * 0.68), int(size * 0.46), int(size * 0.5), int(size * 0.28))
    # 托盘底边
    p.drawLine(int(size * 0.22), int(size * 0.72), int(size * 0.78), int(size * 0.72))
    p.end()
    return pm


def image_icon(size: int = 20, color: str = "#0d904f") -> QPixmap:
    """图片图标：简化的风景画"""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(color), max(1.5, size * 0.10)))
    p.setBrush(Qt.BrushStyle.NoBrush)
    # 外框
    p.drawRoundedRect(int(size * 0.15), int(size * 0.20), int(size * 0.70), int(size * 0.60), 2, 2)
    # 山
    p.drawLine(int(size * 0.22), int(size * 0.68), int(size * 0.42), int(size * 0.48))
    p.drawLine(int(size * 0.42), int(size * 0.48), int(size * 0.60), int(size * 0.62))
    p.drawLine(int(size * 0.60), int(size * 0.62), int(size * 0.78), int(size * 0.44))
    # 太阳
    p.drawEllipse(int(size * 0.58), int(size * 0.30), int(size * 0.10), int(size * 0.10))
    p.end()
    return pm


def back_icon(size: int = 20, color: str = "#64748b") -> QPixmap:
    """返回箭头图标"""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), max(2, size * 0.14), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.drawLine(int(size * 0.82), int(size * 0.5), int(size * 0.28), int(size * 0.5))
    p.drawLine(int(size * 0.28), int(size * 0.5), int(size * 0.52), int(size * 0.26))
    p.drawLine(int(size * 0.28), int(size * 0.5), int(size * 0.52), int(size * 0.74))
    p.end()
    return pm


def link_icon(size: int = 20, color: str = "#2563eb") -> QPixmap:
    """系统集成图标：两个相连节点"""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), max(1.6, size * 0.11), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    r = size * 0.18
    p.drawEllipse(QPoint(int(size * 0.28), int(size * 0.5)), int(r), int(r))
    p.drawEllipse(QPoint(int(size * 0.72), int(size * 0.5)), int(r), int(r))
    p.drawLine(int(size * 0.44), int(size * 0.5), int(size * 0.56), int(size * 0.5))
    p.end()
    return pm


def chart_icon(size: int = 20, color: str = "#9c27b0") -> QPixmap:
    """质控统计报表图标：柱状图"""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor(color)))
    p.drawRoundedRect(int(size * 0.14), int(size * 0.52), int(size * 0.18), int(size * 0.36), 1, 1)
    p.drawRoundedRect(int(size * 0.41), int(size * 0.30), int(size * 0.18), int(size * 0.58), 1, 1)
    p.drawRoundedRect(int(size * 0.68), int(size * 0.12), int(size * 0.18), int(size * 0.76), 1, 1)
    p.end()
    return pm


def avatar_icon(size: int = 64, name: str = "", color: str = "#1a73e8") -> QPixmap:
    """生成用户头像：首字大写圆形背景"""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor(color)))
    p.drawEllipse(0, 0, size, size)
    text = (name[:1] or "U").upper()
    p.setPen(QPen(QColor("white")))
    font = QFont("Microsoft YaHei", int(size * 0.42), QFont.Weight.Bold)
    p.setFont(font)
    p.drawText(QRect(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, text)
    p.end()
    return pm
