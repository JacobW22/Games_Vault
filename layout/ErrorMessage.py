from PySide6.QtWidgets import QMessageBox
from PySide6.QtGui import QIcon

class ErrorMessage(QMessageBox):
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Error")
        self.setText(message)
        self.setIcon(QMessageBox.Critical)
        self.setWindowIcon(QIcon(":/icons/resources\icons/app_icon.png"))
