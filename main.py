import sys
import os
import math
import random
import ast
from pathlib import Path
from typing import List, Tuple
import numpy as np
import cv2
from scipy.spatial import distance

from PyQt6.QtCore import Qt, QSize, QRectF, QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QPixmap, QImage, QIcon
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QSlider, QHBoxLayout, 
    QPushButton, QFileDialog, QGraphicsView, QGraphicsScene, 
    QLabel, QGraphicsPixmapItem, QCheckBox, QDialog, 
    QListWidget, QMessageBox
)

#from CNNEvaluation_Microalgaes import *
#from LocateCandidatesinDataset import *
from UpdateWindowProgress import *


class CircularSpinner(QWidget):
    """
    A custom widget that displays a circular loading spinner animation.
    """
    def __init__(self, parent=None, radius=20, line_width=4):
        super().__init__(parent)
        self.angle = 0
        self.radius = radius
        self.line_width = line_width

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.timer.start(30)

        self.setMinimumSize(2 * (radius + line_width), 2 * (radius + line_width))

    def rotate(self):
        """Increments the current rotation angle of the spinner."""
        self.angle = (self.angle + 10) % 360
        self.update()

    def paintEvent(self, event):
        """Paints the rotating arc onto the widget surface."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(
            self.line_width, self.line_width,
            -self.line_width, -self.line_width
        )

        pen = QPen(QColor(100, 150, 255), self.line_width)
        painter.setPen(pen)

        painter.drawArc(rect, int(self.angle * 16), int(120 * 16))


class ProgressSignals(QObject):
    """
    Signals used for safe multi-threaded communication with progress dialogs.
    """
    update_text = pyqtSignal(str)
    close = pyqtSignal()


class CircularProgressDialog(QDialog):
    """
    A frameless dialog displaying a message along with a circular spinner.
    """
    def __init__(self, message="Loading...", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        self.signals = ProgressSignals()
        self.spinner = CircularSpinner()
        self.label = QLabel(message)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(self.spinner, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.setFixedSize(200, 150)

        self.signals.update_text.connect(self._set_message)
        self.signals.close.connect(self._close_dialog)

    def set_message(self, text):
        """Updates the dialog message from the main thread."""
        self._set_message(text)

    def set_message_threadsafe(self, text):
        """Emits a signal to safely update the message from worker threads."""
        self.signals.update_text.emit(text)

    def close_dialog(self):
        """Closes the dialog from the main thread."""
        self._close_dialog()

    def close_threadsafe(self):
        """Emits a signal to safely close the dialog from worker threads."""
        self.signals.close.emit()

    def _set_message(self, text):
        """Internal method to update the label text UI component."""
        self.label.setText(text)

    def _close_dialog(self):
        """Internal method to trigger the dialog acceptance and close it."""
        self.accept()


class CustomDialog(QDialog):
    """
    Confirmation dialog for editing or removing a selected microalgae item.
    """
    def __init__(self, Indice=-1, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit/Remove Microalgae")
        
        layout = QVBoxLayout()
        label = QLabel(f"Remove selected item? [{Indice}]")
        button = QPushButton("Yes")
        button2 = QPushButton("No")
        
        button.clicked.connect(self.accept)
        button2.clicked.connect(self.reject)
        
        layout.addWidget(label)
        layout.addWidget(button)
        layout.addWidget(button2)
        self.setLayout(layout)


class MyElement:
    """
    Represents a marked microalgae unit containing ID, color, and bounding coordinates.
    """
    def __init__(self, numid, cad="", color=(255,0,0), coordinates=(0,0,0,0), filed=False):
        self.numid = numid
        self.strid = cad
        self.color = color
        self.coordinates = coordinates
        self.filed = filed

    def __repr__(self):
        return f"(numid {self.numid}, strid '{self.strid}', color '{self.color}', coordinates '{self.coordinates}')"


class ElementListModel(QtCore.QAbstractListModel):
    """
    List model acting as the data source provider for the QListView widget.
    """
    def __init__(self, elements=None, parent=None):
        super().__init__(parent)
        self.__elements = elements if elements is not None else []

    def rowCount(self, parent=QtCore.QModelIndex()):
        """Returns the total amount of available dataset elements."""
        return len(self.__elements)

    def data(self, index, role):
        """Fetches display and configuration roles depending on active view context."""
        if not index.isValid() or not (0 <= index.row() < self.rowCount()):
            return None
        thiselement = self.__elements[index.row()]
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return str(thiselement.strid)
        if role == QtCore.Qt.ItemDataRole.UserRole:
            return thiselement


class ElementThumbDelegate(QtWidgets.QStyledItemDelegate):
    """
    Custom view delegate to render colored status boxes beside microalgae items.
    """
    def initStyleOption(self, option, index):
        """Appends color indicators matching specific row features dynamically."""
        super().initStyleOption(option, index)
        thiselement = index.data(QtCore.Qt.ItemDataRole.UserRole)
        if isinstance(thiselement, MyElement):
            option.features |= QtWidgets.QStyleOptionViewItem.ViewItemFeature.HasDecoration
            pixmap = QtGui.QPixmap(option.decorationSize)
            pixmap.fill(QtGui.QColor("#62c2ff"))

            painter = QtGui.QPainter(pixmap)
            color = QtGui.QColor(thiselement.color[2], thiselement.color[1], thiselement.color[0])
            painter.fillRect(pixmap.rect().adjusted(2, 2, -2, -2), color)
            painter.end()
            option.icon = QtGui.QIcon(pixmap)


class GraphicsView(QGraphicsView):
    """
    Interactive widget for plotting pictures, adjusting zoom levels, and drawing ROIs.
    """
    finished = pyqtSignal(tuple)

    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene())
        self.pixmap_item = None
        self.image = None
        self.colorAleatorio = None
        self.ancho_linea = 4

        self.zoom_factor = 1.15
        self._empty = True

        self.draw_mode = False
        self.draw_container_mode = False

        self.drawing = False
        self.start_point = None
        self.current_rect_item = None
        self.points = []

        self.setMouseTracking(True)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    def GeneraColorAleatorio(self):
        """Generates a random BGR color tuple."""
        nums = [int(255 * random.random()) for _ in range(3)]
        return tuple(nums)

    def set_image(self, image):
        """Converts and loads a standard CV2 BGR numpy frame into the active viewport scene."""
        self.scene().clear()
        self.image = image

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)

        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene().addItem(self.pixmap_item)

        self.setSceneRect(QRectF(pixmap.rect()))
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._empty = False

    def set_draw_mode(self, enabled):
        """Enables or disables rectangular ROI drawing behavior."""
        self.draw_mode = enabled
        if enabled:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
        else:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    def set_draw_container_mode(self, enabled):
        """Enables or disables bounding container drawing behavior options."""
        self.draw_container_mode = enabled
        if enabled:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
        else:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    def set_line_width(self, ancho):
        """Sets standard painter stroke width parameters for target rectangles."""
        self.ancho_linea = ancho

    def wheelEvent(self, event):
        """Handles zooming inputs depending on current mouse position and window mode status."""
        if self._empty or self.draw_mode or self.draw_container_mode:
            return

        if event.angleDelta().y() > 0:
            factor = self.zoom_factor
        else:
            factor = 1 / self.zoom_factor

        self.scale(factor, factor)

    def removeItem(self, indice):
        """Deletes a specific shape index context directly from the viewport layout stack."""
        Lista = self.scene().items()
        total = len(Lista)
        indicef = total - 1 - (indice + 1)

        for index, element in enumerate(Lista):
            if indicef == index:
                self.scene().removeItem(element)

    def clear(self):
        """Clears all annotated shapes overlay tracking items except base images."""
        Lista = self.scene().items()
        for index, element in enumerate(Lista):
            if index > 1:
                self.scene().removeItem(element)

    def addItem(self, x1=100, y1=100, x2=200, y2=200, r=-1, g=-1, b=-1, ancholinea=4):
        """Draws custom rectangle overlay outlines based on raw coordinates."""
        rect = QRectF()
        rect.setRect(x1, y1, x2, y2)
        
        if r == -1:
            self.colorAleatorio = self.GeneraColorAleatorio()
            color = QColor(self.colorAleatorio[0], self.colorAleatorio[1], self.colorAleatorio[2])
        else:
            color = QColor(r, g, b)
        pen = QPen(color, int(ancholinea))
        self.scene().addRect(rect, pen)

    def mousePressEvent(self, event):
        """Registers mouse button inputs to begin path configuration or cancel workflows."""
        if self.image is None:
            return

        if self.draw_mode and event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.start_point = self.mapToScene(event.pos())
            
            rect = QRectF(self.start_point, self.start_point).normalized()
            self.colorAleatorio = self.GeneraColorAleatorio()
            color = QColor(self.colorAleatorio[0], self.colorAleatorio[1], self.colorAleatorio[2])
            pen = QPen(color, int(self.ancho_linea / 8))
            self.current_rect_item = self.scene().addRect(rect, pen)

        elif self.draw_container_mode and event.button() == Qt.MouseButton.RightButton:
            print("Action cancelled.")
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Updates shape geometry settings dynamically while mouse tracking is active."""
        if self.draw_mode and self.drawing and self.current_rect_item:
            current_point = self.mapToScene(event.pos())
            rect = QRectF(self.start_point, current_point).normalized()
            self.current_rect_item.setRect(rect)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Saves current geometry points and triggers completion callbacks on layout release."""
        if self.draw_mode and event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False
            rect = self.current_rect_item.rect()

            x1 = rect.left()
            y1 = rect.top()
            x2 = rect.right()
            y2 = rect.bottom()

            print("ROI stored:", (x1, y1, x2, y2))
            self.finished.emit((x1, y1, x2, y2, self.colorAleatorio[0], self.colorAleatorio[1], self.colorAleatorio[2], -1))
        else:
            super().mouseReleaseEvent(event)


class MainWindow(QWidget):
    """
    Main Application view containing image loaders, annotation lists, and analysis options.
    """
    def encontrar_Contorno_Microalga(self, cachoOrig, cachoProcesar):
        """Locates external outlines using dynamic thresholds and basic otsu binarization."""
        Thresholds = [16, 32, 64, 92, 128, 156, 192, 200, 215]
        index = 0
        ListaNumeroContornosEncontrados = []

        blurred = cv2.cvtColor(cachoProcesar, cv2.COLOR_BGR2GRAY)
        ret, thresh = cv2.threshold(blurred, -1, 255, cv2.THRESH_OTSU)
        contours, hierarchy = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        sorted_contours_desc = sorted(contours, key=cv2.contourArea, reverse=True)
        ListaNumeroContornosEncontrados.append(len(sorted_contours_desc))
        cv2.drawContours(cachoProcesar, contours, -1, (0, 255, 0), 1)           

        thresh = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)

        if len(sorted_contours_desc) == 2:
            print(sorted_contours_desc[1])
            x, y, w, h = cv2.boundingRect(sorted_contours_desc[1])
            print("Contours located: ", len(sorted_contours_desc), x, y, w, h)
            cv2.rectangle(cachoOrig, (x, y), (x + w, y + h), (0, 0, 255), 2)
            img_horizontal = cv2.hconcat([cachoOrig, thresh, cachoProcesar])
            cv2.imshow("Cacho-OTSU", img_horizontal)

            self.DimensionesObjetoInteres.append((w, h))
            print("Marked Dimensions: ", self.DimensionesObjetoInteres)
        else:
            while index < len(Thresholds) - 1:
                cachoProcesar1 = cachoProcesar.copy()
                blurred = cv2.cvtColor(cachoProcesar1, cv2.COLOR_BGR2GRAY)
                ret, thresh = cv2.threshold(blurred, Thresholds[index], 255, cv2.THRESH_BINARY)
                contours, hierarchy = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(cachoProcesar1, contours, -1, (0, 0, 255), 1)          
                    
                sorted_contours_desc = sorted(contours, key=cv2.contourArea, reverse=True)
                print("Contours located: ", len(sorted_contours_desc))
                if len(sorted_contours_desc) > 1:
                    x, y, w, h = cv2.boundingRect(sorted_contours_desc[1])
                    cv2.rectangle(cachoOrig, (x, y), (x + w, y + h), (0, 0, 255), 2)
                    self.DimensionesObjetoInteres.append((w, h))
                    thresh = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
                    img_horizontal = cv2.hconcat([cachoOrig, thresh, cachoProcesar1])
                    
                    print("Marked Dimensions:", self.DimensionesObjetoInteres)
                    cv2.imshow("[Final]Cacho-cnt" + str(index), img_horizontal)
                    return None
                    
                ListaNumeroContornosEncontrados.append(len(sorted_contours_desc))
                index += 1
                print("Stop index indicator:", index)
                thresh = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
                img_horizontal = cv2.hconcat([cachoOrig, thresh, cachoProcesar1])
                cv2.imshow("Cacho-cnt" + str(index), img_horizontal)
            print(ListaNumeroContornosEncontrados)   

    def process_user_selection(self, Cacho):
        """Crops image chunks and initializes the automated contour evaluation process."""
        cachoProcesar = Cacho.copy()
        cachoOrig = Cacho.copy()
        self.encontrar_Contorno_Microalga(cachoOrig, cachoProcesar)

    def on_worker_finished(self, result):
        """Processes image coordinate outputs once a user-drawn ROI box is successfully created."""
        result = tuple(map(int, result))
        (x1, y1, x2, y2, r, g, b, TXT) = result
        if TXT == -1:
            print("Plot point onto active view layout:", x1, y1, x2, y2)
            Cadena = "Loc:["
            self.elements.append(MyElement(len(self.elements), str(len(self.elements)) + Cadena, (b, g, r), (x1, y1, x2, y2)))    

            Cachito = self.image[y1:y2, x1:x2]
            print(Cachito.shape)

            if (Cachito.shape[0] > 0) and Cachito.shape[1] > 0: 
                self.process_user_selection(Cachito)

                self.viewModelListView = ElementListModel(self.elements)
                self.ListView.setModel(self.viewModelListView)
                lines = []
                midx = int(np.mean([x1, x2]))
                midy = int(np.mean([y1, y2]))
                tupla1 = (midx, midy)
                lines.append(str(tupla1) + str((r, g, b)) + "\n")

                self.TamanosSelecciones.append((abs(x1 - x2), abs(y1 - y2)))
                print(self.TamanosSelecciones)
                result1 = max(self.TamanosSelecciones, key=lambda x: x[0])
                result2 = max(self.TamanosSelecciones, key=lambda x: x[1])
                print("Maximum measurements: ", result1[0], result2[1])

                FileToOverwrite = self.lbl_CurrentFolder.text() + "/" + self.lbl_CurrentFile.text() + ".txt"    
                print("Target tracking file path:", FileToOverwrite)

                with open(FileToOverwrite, "a") as file:
                    file.writelines(lines)

        if TXT == -21: 
            gray_image_full = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)       
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            imageCLAHE = clahe.apply(gray_image_full)
            cropped_imageCLAHE = imageCLAHE[y1:y2, x1:x2]       

            cropped_image = self.image[y1:y2, x1:x2]
            copy_cropped_image = cropped_image.copy()
            copy_cropped_image2 = cropped_image.copy()      
            
            gray_image = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2GRAY)
            blurred = cv2.medianBlur(gray_image, 5)
            
            ret, thresh = cv2.threshold(gray_image, 127, 255, cv2.THRESH_OTSU | cv2.THRESH_BINARY_INV)
            contours, hierarchy = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(copy_cropped_image, contours, -1, (0, 255, 0), 3)
            
            sorted_contours_desc = sorted(contours, key=cv2.contourArea, reverse=True)
            print("Contours located: ", len(sorted_contours_desc))
            for cnt in sorted_contours_desc:
                x, y, w, h = cv2.boundingRect(cnt)
                print("Width: ", w, " Height: ", h)  
                self.ListaWHs.append([w, h])
                self.LabelSup.setText("" + str(self.ListaWHs))
                  
                cv2.rectangle(copy_cropped_image, (x, y), (x + w, y + h), (0, 255, 0), 2)

                circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, dp=1, minDist=1, param1=20, param2=w, minRadius=0, maxRadius=50)
                if circles is not None:
                    print("Circles located: ", len(circles))
                    circles = np.uint16(np.around(circles))
                    for i in circles[0, :]:
                        cv2.circle(copy_cropped_image2, (i[0], i[1]), i[2], (0, 255, 255), 2)
                else:
                    print("Circles missing or empty.")
                break
            
            self.view2.set_image(cropped_image)
            self.view3.set_image(thresh)
            self.view4.set_image(copy_cropped_image)
            self.view5.set_image(copy_cropped_image2)

    def DeleteLineNumberFromMicroalgeFile(self, line_to_delete):
        """Overwrites tracking files by excluding an explicitly chosen coordinate row entry."""
        filename = self.lbl_CurrentFolder.text() + "/" + self.lbl_CurrentFile.text() + ".txt"    

        with open(filename, "r") as file:
            lines = file.readlines()        

        with open(filename, "w") as file:
            for index, line in enumerate(lines):
                if index != line_to_delete:
                    file.write(line)
        
    def draw_objects_from_file(self, image, text_file, image_width=800, image_height=600):
        """Reads a txt coordinate listing to draw point indicators across visual maps."""
        colores = [
            (255,0,0), (0,255,0), (0,0,255),
            (0,255,255), (255,255,0), (255,0,255)                            
        ]
        self.ListaCoordenadasMicroalgasEtiquetadas = []
        self.view.clear()
        self.elements = []
        conteo = 1

        ArchivoTexto = Path(text_file)
        if ArchivoTexto.is_file():
            with open(text_file, 'r') as file:
                for line in file:
                    line = line.strip()
                    if not line:
                        continue

                    parts = line.split("\n")
                    tuples = parts[0].split(")(")
                    tuples[0] = tuples[0] + ")"
                    tuples[1] = "(" + tuples[1]

                    my_tupleA = ast.literal_eval(tuples[0])
                    my_tupleB = colores[(conteo - 1) % len(colores)]        
                    r, g, b = my_tupleB                
                    
                    self.ListaCoordenadasMicroalgasEtiquetadas.append(my_tupleA)
                    x, y = my_tupleA
                    self.view.addItem(x - 10, y - 10, 20, 20, r, g, b)
                    self.elements.append(MyElement(len(self.elements), str(len(self.elements)) + "XXX", (b, g, r), (x, y, 0, 0)))    
                    conteo += 1  

        self.viewModelListView = ElementListModel(self.elements)
        self.ListView.setModel(self.viewModelListView)
        self.infoAlgasEtiquetadas.setText("Total Reference Algaes: " + str(len(self.ListaCoordenadasMicroalgasEtiquetadas)))
        return image
                    
    def __init__(self):
        super().__init__()
        self.ListaCoordenadasMicroalgasEtiquetadas = []
        self.DimensionesObjetoInteres = []
        self.TamanosSelecciones = []
        BUTTON_SIZE = QSize(300, 30)

        self.ListaWHs = []
        self.ListaEsquinasROI = []

        self.setWindowTitle("Computer-Assisted Microalgae Counting App")

        self.view = GraphicsView()
        self.view.setMinimumSize(900, 700)
        self.view.finished.connect(self.on_worker_finished)

        self.viewG2 = GraphicsView()
        self.viewG2.setMinimumSize(700, 400)
        self.viewG4 = GraphicsView()
        self.viewG4.setMinimumSize(700, 400)
        self.viewG3 = GraphicsView()
        self.viewG3.setMinimumSize(120, 120)

        self.view.set_line_width(8)
        self.viewG2.set_line_width(8)
        
        self.view2 = GraphicsView()
        self.view2.setMinimumSize(120, 120)
        self.view3 = GraphicsView()
        self.view3.setMinimumSize(120, 120)        
        self.view4 = GraphicsView()
        self.view4.setMinimumSize(120, 120)        
        self.view5 = GraphicsView()
        self.view5.setMinimumSize(120, 120)        

        self.draw_toggle = QCheckBox("Mark microalga")
        self.draw_toggle.setEnabled(False) 
        self.iconoUndo = QPushButton()
        icon = app.style().standardIcon(app.style().StandardPixmap.SP_DialogCancelButton)
        self.iconoUndo.setIcon(icon)
        self.iconoUndo.setToolTip("Removes <b>rectangle</b> selection")
        self.iconoUndo.setIconSize(QSize(32, 32))
        self.iconoUndo.setMaximumWidth(50)
        self.iconoUndo.setEnabled(False) 

        self.iconCleanROIs = QPushButton()
        icon2 = app.style().standardIcon(app.style().StandardPixmap.SP_TrashIcon)
        self.iconCleanROIs.setIcon(icon2)
        self.iconCleanROIs.setToolTip("Clean marked reference <b>microalgae</b>")
        self.iconCleanROIs.setIconSize(QSize(32, 32))
        self.iconCleanROIs.setMaximumWidth(50)
        self.iconCleanROIs.setEnabled(False) 

        self.count_button2 = QPushButton("Analyze all")
        self.draw_toggle.toggled.connect(self.toggle_draw_mode)
        self.count_button2.clicked.connect(self.AislarTodasLasAreasInteres)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.iconoUndo)
        top_layout.addWidget(self.draw_toggle)
        top_layout.addWidget(self.iconCleanROIs)
        top_layout.addWidget(self.count_button2)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(1)
        self.slider.setMaximum(20)
        self.slider.setValue(10)
        self.slider.setSingleStep(1)

        self.slider2 = QSlider(Qt.Orientation.Horizontal)
        self.slider2.setMinimum(1)
        self.slider2.setMaximum(20)
        self.slider2.setValue(10)
        self.slider2.setSingleStep(1)

        self.locate = QPushButton("LocateAlgae")
        layoutSlider_mas_boton = QHBoxLayout()
        layoutSlider_mas_boton.addWidget(self.slider)
        layoutSlider_mas_boton.addWidget(self.slider2)
        layoutSlider_mas_boton.addWidget(self.locate)
        self.locate.clicked.connect(self.locate_reference_microalgae)
        self.locate.setEnabled(False) 

        self.currentImage = QLabel("Current image: N/A")
        self.infoAlgasEtiquetadas = QLabel("Total Reference Algaes: N/A")

        layout = QVBoxLayout()
        layoutH = QHBoxLayout()
        layout.addLayout(top_layout)
        layout.addWidget(self.currentImage)
        layout.addLayout(layoutSlider_mas_boton)
        layout.addWidget(self.infoAlgasEtiquetadas)
        layout.addWidget(self.view)
        
        layoutPreviews = QVBoxLayout()
        layoutPreviews.addWidget(self.viewG3)
        layoutPreviews.addWidget(self.view2)
        layoutPreviews.addWidget(self.view3)
        layoutPreviews.addWidget(self.view4)
        layoutPreviews.addWidget(self.view5)

        self.elements = []
        self.ListView = QtWidgets.QListView()
        self.viewModelListView = ElementListModel(self.elements)
        self.ListView.setModel(self.viewModelListView)
        self.ListView.setItemDelegate(ElementThumbDelegate(self.ListView))
        self.ListView.mouseReleaseEvent = self.MyMouseClickedOnListView
        self.ListView.setMinimumSize(BUTTON_SIZE)

        self.ChooseFolderButton = QPushButton("Choose folder")
        self.ChooseFolderButton.clicked.connect(self.load_folder)
        
        top_layoutxX = QVBoxLayout()
        top_layoutxX.addWidget(self.ChooseFolderButton)
        self.lbl_CurrentFolder = QLabel(" ")
        self.lbl_CurrentFolder.setFixedWidth(300)
        self.lbl_CurrentFile = QLabel(" ")
        self.lbl_CurrentFile.setFixedWidth(300)

        top_layoutxX.addWidget(QLabel("Current Folder: "))
        top_layoutxX.addWidget(self.lbl_CurrentFolder)
        self.QListWidgetArchivos = QListWidget()
        top_layoutxX.addWidget(self.QListWidgetArchivos)
        self.QListWidgetArchivos.itemClicked.connect(self.handle_click)

        layoutH.addLayout(top_layoutxX)
        layoutH.addLayout(layout)
        layoutH.addLayout(layoutPreviews)
        top_layoutx = QVBoxLayout()
        top_layoutx.addWidget(QLabel("Marked microalgae regions"))
        top_layoutx.addWidget(self.ListView)
        layoutH.addLayout(top_layoutx)

        self.setLayout(layoutH)
        self.resize(1400, 100)

    def handle_click(self, item):
        """Displays target confirmation boxes and reloads file systems on user list selection."""
        ArchivoAnterior = self.lbl_CurrentFolder.text() + "/" + self.lbl_CurrentFile.text()
        QMessageBox.information(None, "Success", "Update" + ArchivoAnterior)        

        ArchivoTexto = Path(ArchivoAnterior)
        if ArchivoTexto.is_file():
            Lista = self.elements
            for index, element in enumerate(Lista):
                asas = "X"

        print(f"Clicked: {item.text()}")
        self.lbl_CurrentFile.setText(item.text())
        Archivo = self.lbl_CurrentFolder.text() + "/" + item.text()
        print(Archivo)
        self.CargarImagen(Archivo)

    def load_folder(self):
        """Triggers directory choice prompt menus and initializes system image element list trees."""
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        print(folder_path)

        self.ListaCoordenadasMicroalgasEtiquetadas = []
        self.view.clear()
        self.elements = []
        self.QListWidgetArchivos.clear()
        self.lbl_CurrentFolder.setText(folder_path)

        extensions = ("*.png", "*.jpg", "*.jpeg")
        files = []
        for ext in extensions:
            files.extend(Path(folder_path).glob(ext))

        if len(files) > 0:
            self.lbl_CurrentFile.setText(files[0].name)
            for f in files:
                print(f)
                self.QListWidgetArchivos.addItem(f.name) 

            self.QListWidgetArchivos.setCurrentRow(0)  
            self.CargarImagen(str(files[0]))

    def CargarImagen(self, file_path):
        """Loads and converts requested file paths to map components onto graphics workspace displays."""
        if file_path:
            self.image = cv2.imread(file_path)
            self.image_Copia = cv2.imread(file_path)

            basename2 = os.path.basename(file_path)
            self.AnchoLinea = int(self.image.shape[0] / 200)

            self.view.set_line_width(self.AnchoLinea)
            self.viewG2.set_line_width(self.AnchoLinea)

            self.currentImage.setText("Current image:   " + basename2 + " Dimensiones: [" + str(self.image.shape) + "]")

            self.view.set_image(self.image)
            self.draw_toggle.setEnabled(True) 
            self.iconoUndo.setEnabled(True) 
            self.iconCleanROIs.setEnabled(True) 
            self.locate.setEnabled(True) 
            Imagen3 = self.draw_objects_from_file(self.image_Copia, str(file_path) + ".txt")
            self.viewG3.set_image(Imagen3) 

    def load_image(self):
        """Opens a generic file choosing menu modal dialog specifically tailored for images."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        self.CargarImagen(file_path)

    def MyMouseClickedOnListView(self, e):
        """Launches contextual choice workflows when interacting with annotation data sets."""
        IndiceCliqueado = self.ListView.currentIndex().row()
        dialog = CustomDialog(Indice=IndiceCliqueado)
        if dialog.exec() == 1:
            print("Target entry row selected:", IndiceCliqueado)
            if self.elements[IndiceCliqueado].filed:
                self.elements[IndiceCliqueado].filed = False
            else:
                self.elements[IndiceCliqueado].filed = True

            self.DeleteLineNumberFromMicroalgeFile(IndiceCliqueado)
            self.elements.pop(IndiceCliqueado)
            self.viewModelListView = ElementListModel(self.elements)
            self.ListView.setModel(self.viewModelListView)
            self.view.removeItem(IndiceCliqueado)

    def GeneraColorAleatorio(self):
        """Generates random three-channel integer configurations."""
        nums = [int(255 * random.random()) for _ in range(3)]
        return tuple(nums)

    def locate_reference_microalgae(self):
        """Validates bounding boxes logic against tracking records."""
        print("Locating Microalgaes ---")
        if len(self.ListaEsquinasROI) == 4:
            print("ESI:", self.ListaEsquinasROI[0])
            print("ESD:", self.ListaEsquinasROI[1])
            print("EID:", self.ListaEsquinasROI[2])
            print("EII:", self.ListaEsquinasROI[1])

            for e in self.ListaCoordenadasMicroalgasEtiquetadas:
                print(e)
        else:
            return None

    def toggle_draw_mode(self, checked):
        """Toggles active drawing behaviors inside main view screens."""
        self.view.set_draw_mode(checked)

    def toggle_draw_rectangle_mode(self, checked):
        """Switches bounding structural constraint choices on display frames."""
        self.view.set_draw_container_mode(checked)
        print("Draw layout rectangle: ", checked)

    def update(self):
        """Updates display metrics inside the messaging window component."""
        self.dialog.set_message("Processing data...")
    
    def finish(self):
        """Safely dismisses active messaging and dialogue models."""
        self.dialog.close_dialog()

    def AislarTodasLasAreasInteres(self):
        """Launches target evaluation models across selected tracking libraries."""
        RutaDirectorio = self.lbl_CurrentFolder.text()
        foldername = os.path.basename(RutaDirectorio)
        print("Full path view: ", RutaDirectorio)
        print("Target folder: ", foldername)

        self.second_window = None 
        if self.second_window is None:
            self.second_window = TrainingWindow(foldername)
        self.second_window.show()

    def euclidean_distance(self, p1, p2):
        """Computes the basic Euclidean separation between two points."""
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)          

    def filter_close_points(self, list1, list2, threshold):
        """Excludes entries within list1 that sit closer to point components within list2 than predefined limits."""
        for index, p2 in enumerate(list2):
            for p1 in list1:            
                if self.euclidean_distance(p1, p2) <= threshold:
                    print("index context match:", index)
                    break

        filtered = []
        index_of_matched_microalgae = []
        for p1 in list1:
            is_close = False
            for index, p2 in enumerate(list2):
                if self.euclidean_distance(p1, p2) <= threshold:
                    index_of_matched_microalgae.append(index)
                    is_close = True
                    break
            if not is_close:
                filtered.append(p1)
        print("Index of matched Microalgaes", index_of_matched_microalgae)        
        return filtered    







if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
