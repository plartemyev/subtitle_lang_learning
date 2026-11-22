"""Custom-painted context phrase with pedagogical grammar symbols.

Replaces the plain-text phrase browser: every word carries its Montessori
symbol above the word, a per-family underline and a rich tooltip. The widget
is a pure renderer - display strings (tooltips, POS names) are built and
localized by the caller; nothing here reads the i18n catalogs.

Also hosts :class:`PosChip`, the small symbol-and-label pill used in the
details header and the legend row.
"""
import dataclasses

import PyQt6.QtCore
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen

from ui.qt import grammar
from ui.qt.grammar import Category


@dataclasses.dataclass
class TokenView:
    """One phrase word prepared for display by the caller (localized strings)."""
    text: str
    category: Category
    tooltip: str = ''
    selected: bool = False


class PhraseView(QtWidgets.QWidget):
    """Interlinear gloss: grammar symbol row above a wrapped word row."""

    SYMBOL_ZONE = max(grammar.SYMBOL_SIZES.values()) + 5  # px reserved above words
    TOKEN_PADDING = 3  # extra width around a selected word
    UNDERLINE_CLEARANCE = 2  # px between the font's underline pos and our line

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        font = self.font()
        font.setPointSizeF(font.pointSizeF() + 2)
        self.setFont(font)
        self._tokens = []
        self._positions = []  # (x, line_index) per token
        self._line_count = 1
        self._line_height = 1
        self._focus_index = -1  # keyboard-navigated token

    # ---------- data ----------

    def set_tokens(self, tokens: list[TokenView]):
        self._tokens = list(tokens)
        self._focus_index = -1
        self._relayout()
        self.update()

    # ---------- layout ----------

    def _relayout(self):
        metrics = self._font_metrics()
        self._line_height = (self.SYMBOL_ZONE + metrics.ascent() + metrics.descent()
                             + self.UNDERLINE_CLEARANCE)
        self._positions.clear()
        available = max(self.width(), 200)
        x = 0.0
        line = 0
        space_width = metrics.horizontalAdvance(' ')
        for index, token in enumerate(self._tokens):
            width = metrics.horizontalAdvance(token.text) + 2 * self.TOKEN_PADDING
            if x > 0 and x + width > available:
                line += 1
                x = 0.0
            self._positions.append((x, line))
            x += width + space_width
        self._line_count = line + 1
        self.setMinimumHeight(self._line_count * self._line_height + 8)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout()
        self.update()

    def _font_metrics(self) -> QFontMetrics:
        return QFontMetrics(self.font())

    def _token_rect(self, index: int) -> QRectF:
        metrics = self._font_metrics()
        x, line = self._positions[index]
        width = metrics.horizontalAdvance(self._tokens[index].text) + 2 * self.TOKEN_PADDING
        return QRectF(x, line * self._line_height, width, self._line_height)

    # ---------- painting ----------

    def paintEvent(self, event):
        if not self._tokens:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        metrics = self._font_metrics()
        ink = self.palette().color(self.palette().ColorRole.WindowText)
        bold_font = self.font()
        bold_font.setBold(True)
        for index, token in enumerate(self._tokens):
            x, line = self._positions[index]
            line_top = line * self._line_height
            width = metrics.horizontalAdvance(token.text) + 2 * self.TOKEN_PADDING
            baseline = line_top + self.SYMBOL_ZONE + metrics.ascent()
            if index == self._focus_index:
                self._paint_focus_ring(painter, QRectF(x - 1, line_top + 1, width + 2,
                                                       self._line_height - 2))
            if token.category is not Category.UNMARKED:
                grammar.draw_symbol(painter, x + width / 2, line_top + 2, token.category)
            color = grammar.WORD_COLORS[token.category] if token.category is not Category.UNMARKED else ink
            underline_style, underline_width = grammar.UNDERLINES[token.category]
            if token.selected:
                highlight = QColor(color)
                highlight.setAlpha(32)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(highlight)
                painter.drawRoundedRect(QRectF(x - 1, line_top + self.SYMBOL_ZONE - 3,
                                               width + 2, metrics.height() + 4), 3, 3)
                painter.setFont(bold_font)
            else:
                painter.setFont(self.font())
            painter.setPen(color)
            painter.drawText(QPointF(x + self.TOKEN_PADDING, baseline), token.text)
            if underline_style is not grammar.Underline.NONE:
                underline_y = baseline + metrics.underlinePos() + self.UNDERLINE_CLEARANCE - 1
                self._paint_underline(painter, x + self.TOKEN_PADDING, underline_y,
                                      width - 2 * self.TOKEN_PADDING,
                                      underline_style, underline_width, color)
        painter.end()

    def _paint_underline(self, painter, x, y, width, style, pen_width, color):
        if style is grammar.Underline.SOLID:
            pen = QPen(color)
            pen.setWidthF(pen_width)
            painter.setPen(pen)
            painter.drawLine(QPointF(x, y), QPointF(x + width, y))
        elif style is grammar.Underline.DOUBLE:
            pen = QPen(color)
            pen.setWidthF(1.0)
            painter.setPen(pen)
            painter.drawLine(QPointF(x, y), QPointF(x + width, y))
            painter.drawLine(QPointF(x, y + 2.2), QPointF(x + width, y + 2.2))
        elif style in (grammar.Underline.DASHED, grammar.Underline.DOTTED):
            pen = QPen(color)
            pen.setWidthF(pen_width)
            pattern = (3.5, 2.5) if style is grammar.Underline.DASHED else (0.8, 2.2)
            pen.setDashPattern([value / pen_width for value in pattern])
            painter.setPen(pen)
            painter.drawLine(QPointF(x, y), QPointF(x + width, y))
        elif style is grammar.Underline.WAVY:
            self._paint_wavy(painter, x, y, width, pen_width, color)

    @staticmethod
    def _paint_wavy(painter, x, y, width, pen_width, color):
        pen = QPen(color)
        pen.setWidthF(pen_width)
        painter.setPen(pen)
        path = QPainterPath(QPointF(x, y))
        half_period, amplitude = 3.0, 1.3
        cursor = x
        rising = True
        # loop bound derives from the pixel width, so it always terminates
        while cursor + half_period <= x + width:
            control_y = y - amplitude if rising else y + amplitude
            path.quadTo(QPointF(cursor + half_period / 2, control_y),
                        QPointF(cursor + half_period, y))
            cursor += half_period
            rising = not rising
        painter.drawPath(path)

    @staticmethod
    def _paint_focus_ring(painter, rect: QRectF):
        pen = QPen(painter.pen())
        pen.setColor(QColor('#93c5fd'))
        pen.setWidthF(1.5)
        pen.setStyle(QtCore.Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 3, 3)

    # ---------- interaction ----------

    def event(self, event: PyQt6.QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.Type.ToolTip:
            token = self._token_at(event.pos())
            if token is not None and self._tokens[token].tooltip:
                QtWidgets.QToolTip.showText(event.globalPos(),
                                            self._tokens[token].tooltip, self)
            return True
        return super().event(event)

    def keyPressEvent(self, event):
        key = event.key()
        if not self._tokens or key not in (QtCore.Qt.Key.Key_Left, QtCore.Qt.Key.Key_Right):
            super().keyPressEvent(event)
            return
        if self._focus_index < 0:
            self._focus_index = 0
        elif key == QtCore.Qt.Key.Key_Right:
            self._focus_index = min(self._focus_index + 1, len(self._tokens) - 1)
        else:
            self._focus_index = max(self._focus_index - 1, 0)
        self.update()
        token = self._tokens[self._focus_index]
        if token.tooltip:
            rect = self._token_rect(self._focus_index)
            anchor = self.mapToGlobal(rect.topLeft().toPoint())
            QtWidgets.QToolTip.showText(anchor, token.tooltip, self)

    def _token_at(self, position):
        point = QPointF(position)
        for index in range(len(self._tokens)):
            if self._token_rect(index).contains(point):
                return index
        return None


class PosChip(QtWidgets.QWidget):
    """Small pill: painted grammar symbol plus a small-caps category label."""

    def __init__(self, parent=None):
        super().__init__(parent)
        font = self.font()
        font.setCapitalization(QFont.Capitalization.SmallCaps)
        font.setPointSizeF(max(font.pointSizeF() - 1, 8))
        font.setWeight(QFont.Weight.DemiBold)
        font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 104)
        self.setFont(font)
        self._category = Category.UNMARKED
        self._label = ''

    def set_data(self, category: Category, label: str):
        self._category = category
        self._label = label
        size = self._chip_size()
        self.setMinimumSize(size)
        self.resize(size)
        self.update()

    def _chip_size(self) -> QtCore.QSize:
        metrics = QFontMetrics(self.font())
        symbol = grammar.SYMBOL_SIZES[self._category]
        pad_x, gap, pad_y = 9, 5, 3
        return QtCore.QSize(pad_x + symbol + gap + metrics.horizontalAdvance(self._label) + pad_x,
                            max(symbol, metrics.height()) + 2 * pad_y)

    def paintEvent(self, event):
        if self._category is Category.UNMARKED:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = grammar.SYMBOL_COLORS[self._category]
        border = QColor(color)
        border.setAlpha(90)
        background = QColor(color)
        background.setAlpha(26)
        painter.setPen(border)
        painter.setBrush(background)
        painter.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 5, 5)
        symbol = grammar.SYMBOL_SIZES[self._category]
        grammar.draw_symbol(painter, 9 + symbol / 2, (self.height() - symbol) / 2, self._category)
        metrics = QFontMetrics(self.font())
        text_color = grammar.WORD_COLORS[self._category]
        painter.setPen(text_color)
        baseline = (self.height() + metrics.ascent() - metrics.descent()) / 2
        painter.setFont(self.font())
        painter.drawText(QPointF(9 + symbol + 5, baseline), self._label)
        painter.end()
