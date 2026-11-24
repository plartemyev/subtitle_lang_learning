"""Left-to-right flow layout: a row of items that wraps at the available width.

Qt ships no flow layout and the legend chips need one: a box-layout row
cannot wrap, so its minimum width (the sum of the chips) pushed the window
wider on words with a long legend.
"""
from PyQt6 import QtCore, QtWidgets


class FlowLayout(QtWidgets.QLayout):
    """Items in rows, each as wide as the layout, stacked top to bottom."""

    H_SPACE = 6
    V_SPACE = 6

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []

    def addItem(self, item):
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return QtCore.Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._arrange(QtCore.QRect(0, 0, width, 0), dry_run=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._arrange(rect, dry_run=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QtCore.QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return size + QtCore.QSize(margins.left() + margins.right(),
                                   margins.top() + margins.bottom())

    def _arrange(self, rect, dry_run: bool) -> int:
        """Place the items top to bottom; return the height they need."""
        x, y, row_height = rect.x(), rect.y(), 0
        for item in self._items:
            hint = item.sizeHint()
            if x > rect.x() and x + hint.width() > rect.right() + 1:
                x = rect.x()
                y += row_height + self.V_SPACE
                row_height = 0
            if not dry_run:
                item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), hint))
            x += hint.width() + self.H_SPACE
            row_height = max(row_height, hint.height())
        return y + row_height - rect.y()
