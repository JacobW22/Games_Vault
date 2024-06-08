from PySide6 import QtWidgets
from PySide6 import QtCore
from PySide6.QtWidgets import QSizePolicy
from PySide6.QtCore import Qt, QRect, QPoint

class FlowLayout(QtWidgets.QLayout):
    def __init__(self, parent=None, hspacing=-1, vspacing=-1):
        super(FlowLayout, self).__init__(parent)
        self._hspacing = hspacing
        self._vspacing = vspacing
        self._items = []
        self.setContentsMargins(10, 5, 5, 10)

    def __del__(self):
        del self._items[:]

    def addItem(self, item):
        self._items.append(item)

    def horizontalSpacing(self):
        if self._hspacing >= 0:
            return self._hspacing
        else:
            return self.smartSpacing(
                QtWidgets.QStyle.PM_LayoutHorizontalSpacing)

    def verticalSpacing(self):
        if self._vspacing >= 0:
            return self._vspacing
        else:
            return self.smartSpacing(
                QtWidgets.QStyle.PM_LayoutVerticalSpacing)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)

    def expandingDirections(self):
        return QtCore.Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.doLayout(QtCore.QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QtCore.QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        left, top, right, bottom = self.getContentsMargins()
        size += QtCore.QSize(left + right, top + bottom)
        return size

    def doLayout(self, rect, testonly):
           lineheight = 0
           row_widths = [0]
           row = 0
           spacing = self.spacing()

           for item in self._items:
               wid = item.widget()
               space_x = spacing + wid.style().layoutSpacing(
                   QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal)
               item_width = item.sizeHint().width() + space_x
               if row_widths[row] + item_width < rect.width():
                   row_widths[row] += item_width
               else:
                   row += 1
                   row_widths.append(item_width)

           x = int((rect.width() - row_widths[0]) / 2)
           y = rect.top()

           row = 0
           for item in self._items:
               style = item.widget().style()
               layout_spacing_x = style.layoutSpacing(
                   QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal)
               layout_spacing_y = style.layoutSpacing(
                   QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical)
               space_x = spacing + layout_spacing_x
               space_y = spacing + layout_spacing_y
               next_x = x + item.sizeHint().width() + space_x
               if next_x - space_x > rect.right() and lineheight > 0:
                   row += 1
                   x = int((rect.width() - row_widths[row]) / 2)
                   y = y + lineheight + space_y
                   next_x = x + item.sizeHint().width() + space_x
                   lineheight = 0

               if not testonly:
                   item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

               x = next_x
               lineheight = max(lineheight, item.sizeHint().height())

           return y + lineheight - rect.y()

    def smartSpacing(self, pm):
        parent = self.parent()
        if parent is None:
            return -1
        elif parent.isWidgetType():
            return parent.style().pixelMetric(pm, None, parent)
        else:
            return parent.spacing()
