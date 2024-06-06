from PySide6.QtWidgets import QMainWindow
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPalette, QColor
from layout.desktop_widget_form import Ui_DekstopWidget

class DesktopWidget(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Set up the UI
        self.ui = Ui_DekstopWidget()
        self.ui.setupUi(self)

        app_icon = QIcon(":/icons/resources\icons/app_icon.png")
        self.setWindowIcon(app_icon)
        self.setWindowFlags(Qt.Tool)
        self.setWindowTitle("Games Vault")

        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(0, 0, 0))
        self.setPalette(palette)

        self.draggable = False
        self.resizeable = False
        self.offset = None


    def mousePressEvent(self, event):
            if event.button() == Qt.LeftButton:
                self.draggable = True
                self.offset = event.pos()

                grip_area = self.rect().adjusted(self.width() - 20, self.height() - 20, 0, 0)
                if grip_area.contains(event.pos()):
                    self.resizeable = True
                    self.draggable = False

    def mouseMoveEvent(self, event):
        if self.draggable:
            self.move(self.pos() + event.pos() - self.offset)

        elif self.resizeable:
            self.resize(max(100, event.pos().x()), max(100, event.pos().y()))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.draggable = False
