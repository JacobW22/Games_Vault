from PySide6.QtWidgets import QMessageBox, QLabel, QDialogButtonBox
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

class MessageBox(QMessageBox):
    def __init__(self, title, info_message, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setText(info_message)
        self.setWindowIcon(QIcon(":/icons/resources\icons/app_icon.png"))

        self.layout().setContentsMargins(20, 15, 15, 15)
        qt_msgbox_label = self.findChild(QLabel, "qt_msgbox_label")
        qt_msgbox_label.setAlignment(Qt.AlignCenter)
        qt_msgbox_label.setTextFormat(Qt.RichText)
        qt_msgbox_buttonbox = self.findChild(QDialogButtonBox, "qt_msgbox_buttonbox")
        qt_msgbox_buttonbox.setCenterButtons(True)

        self.layout().removeWidget(qt_msgbox_label)

        self.layout().addWidget(qt_msgbox_label, 0, 0, alignment=Qt.AlignCenter)

