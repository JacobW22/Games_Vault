# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'desktop_widget_form.ui'
##
## Created by: Qt User Interface Compiler version 6.7.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QMainWindow, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_DekstopWidget(object):
    def setupUi(self, DekstopWidget):
        if not DekstopWidget.objectName():
            DekstopWidget.setObjectName(u"DekstopWidget")
        DekstopWidget.resize(400, 600)
        palette = QPalette()
        brush = QBrush(QColor(0, 0, 0, 255))
        brush.setStyle(Qt.SolidPattern)
        palette.setBrush(QPalette.Active, QPalette.Window, brush)
        palette.setBrush(QPalette.Inactive, QPalette.Window, brush)
        palette.setBrush(QPalette.Disabled, QPalette.Base, brush)
        palette.setBrush(QPalette.Disabled, QPalette.Window, brush)
        DekstopWidget.setPalette(palette)
        DekstopWidget.setWindowOpacity(0.950000000000000)
        self.centralwidget = QWidget(DekstopWidget)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_2 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(15, 15, 0, 15)
        DekstopWidget.setCentralWidget(self.centralwidget)

        self.retranslateUi(DekstopWidget)

        QMetaObject.connectSlotsByName(DekstopWidget)
    # setupUi

    def retranslateUi(self, DekstopWidget):
        DekstopWidget.setWindowTitle(QCoreApplication.translate("DekstopWidget", u"DesktopWidget", None))
    # retranslateUi

