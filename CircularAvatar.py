from PySide6.QtGui import QImage, QPixmap, QPainter, QBrush, Qt, QColor, QPainterPath
from PySide6.QtCore import QRect, QPoint

def mask_image(q_image, size=64, border_color=QColor(0, 255, 0), border_width=2):
    # Load image
    image = q_image

    # convert image to 32-bit ARGB (adds an alpha
    # channel ie transparency factor):
    image = image.convertToFormat(QImage.Format_ARGB32)

    # Crop image to a square:
    imgsize = min(image.width(), image.height())
    rect = QRect(
        (image.width() - imgsize) // 2,
        (image.height() - imgsize) // 2,
        imgsize,
        imgsize,
    )

    image = image.copy(rect)

    # Create the output image with the same dimensions
    # and an alpha channel and make it completely transparent:
    out_img = QImage(imgsize + 2 * border_width, imgsize + 2 * border_width, QImage.Format_ARGB32)
    out_img.fill(Qt.transparent)

    # Create a texture brush and paint a circle
    # with the original image onto the output image:
    brush = QBrush(image)

    # Paint the output image
    painter = QPainter(out_img)
    painter.setRenderHint(QPainter.Antialiasing)

    # Draw border
    border_radius = (imgsize + border_width) // 2
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(border_color))
    painter.drawEllipse(0, 0, imgsize + 2 * border_width, imgsize + 2 * border_width)

    # Create a QPainterPath for clipping
    clip_path = QPainterPath()
    clip_path.addEllipse(QPoint(border_width + imgsize // 2, border_width + imgsize // 2), imgsize // 2, imgsize // 2)
    painter.setClipPath(clip_path)

    # Set brush to draw the circular image
    painter.setBrush(brush)

    # Draw the circular image
    painter.drawEllipse(border_width, border_width, imgsize, imgsize)

    # closing painter event
    painter.end()

    # Convert the image to a pixmap and rescale it.
    pm = QPixmap.fromImage(out_img)

    # Resize pixmap to the desired size
    pm = pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    # return the pixmap data
    return pm
