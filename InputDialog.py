from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QDialogButtonBox, QFormLayout, QLabel
from PySide6.QtCore import Qt

class InputDialog(QDialog):
    def __init__(self, title, input_label_text, info_message, parent=None):
        super().__init__(parent)

        self.setWindowTitle(title)
        self.layout = QVBoxLayout()

        self.form_layout = QFormLayout()
        self.input_field = QLineEdit()
        self.info = QLabel()

        self.form_layout.addRow(input_label_text, self.input_field)

        self.info.setText(info_message)
        self.info.setTextFormat(Qt.RichText)
        self.info.setContentsMargins(0, 5, 0, 10)
        self.info.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.info.setOpenExternalLinks(True)
        self.form_layout.addRow(self.info)

        self.layout.addLayout(self.form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

        self.setLayout(self.layout)
        self.input_field.setFocus()

    def get_input(self):
        return self.input_field.text()
