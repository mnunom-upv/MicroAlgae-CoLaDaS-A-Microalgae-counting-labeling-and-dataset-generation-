import os
import sys
import cv2
import numpy as np
import ast
import random
from pathlib import Path


from PyQt6.QtWidgets import QListWidget, QListWidgetItem
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QSlider,
    QHBoxLayout, QPushButton, QFileDialog,
    QGraphicsView, QGraphicsScene, QLabel, QGraphicsLineItem,
    QGraphicsPixmapItem, QCheckBox, QDialog
)
from PyQt6.QtGui import QPixmap, QImage, QPen, QIcon, QColor
#from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtCore import *
from PyQt6.QtCore import QSize, Qt
from PyQt6 import QtCore, QtGui, QtWidgets
#
from PyQt6.QtWidgets import QMessageBox

class CustomDialog(QDialog):
    def __init__(self, Indice=-1, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit/Remove Microalgae")
        
        # Create layout and widgets
        layout = QVBoxLayout()
        label = QLabel("Remove selected item? ["+str(Indice)+"]")
        button = QPushButton("Yes")
        button2 = QPushButton("No")
        
        # Connect button signal to close the dialog
        button.clicked.connect(self.accept)
        button2.clicked.connect(self.reject)
        
        layout.addWidget(label)
        layout.addWidget(button)
        layout.addWidget(button2)
        self.setLayout(layout)


class MyElement:
    def __init__(self, numid, cad="", color=(255,0,0),coordinates=(0,0,0,0),filed=False):
        self.numid = numid
        self.strid = cad
        self.color = color
        self.coordinates = coordinates
        self.filed=filed
    def __repr__(self):
        return f"(numid {self.numid}, strid '{self.strid}', color '{self.color}, coordinates '{self.coordinates}')"


class ElementListModel(QtCore.QAbstractListModel):
    def __init__(self, elements=None, parent=None):
        super().__init__(parent)
        self.__elements = elements if elements is not None else []

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.__elements)

    def data(self, index, role):
        if not index.isValid() or not (0 <= index.row() < self.rowCount()):
            return None
        thiselement = self.__elements[index.row()]
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return str(thiselement.strid)
        if role == QtCore.Qt.ItemDataRole.UserRole:
            return thiselement



class ElementThumbDelegate(QtWidgets.QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        thiselement = index.data(QtCore.Qt.ItemDataRole.UserRole)
        if isinstance(thiselement, MyElement):
            #if thiselement.param == "a":
            option.features |= QtWidgets.QStyleOptionViewItem.ViewItemFeature.HasDecoration
            pixmap = QtGui.QPixmap(option.decorationSize)
            pixmap.fill(QtGui.QColor("#62c2ff"))

            painter = QtGui.QPainter(pixmap)
            color = QtGui.QColor(thiselement.color[2],thiselement.color[1],thiselement.color[0]) # BGR
            painter.fillRect(pixmap.rect().adjusted(2, 2, -2, -2), color)
            painter.end()
            option.icon = QtGui.QIcon(pixmap)

class GraphicsView(QGraphicsView):
    def GeneraColorAleatorio (self):
        nums = []
        for _ in range(3):
            nums.append(int(255*random.random()))
        nums = tuple(nums)
        #print (nums)
        return (nums)


    finished = pyqtSignal(tuple)
    def __init__(self):
        super().__init__()

        self.setScene(QGraphicsScene()  )
        self.pixmap_item = None
        self.image = None
        self.colorAleatorio=None

        # Zoom
        self.zoom_factor = 1.15
        self._empty = True

        # ROI
        self.draw_mode = False  #Este modo tiene qeu ser mutuamente excluyente con el otro
        self.draw_container_mode = False #Este modo tiene qeu ser mutuamente excluyente con el otro

        self.drawing = False
        self.start_point = None
        self.current_rect_item = None
        self.current_line_item = None
        #self.rois = []

        self.points = []          # Store rectangle corners


        self.setMouseTracking(True)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    # -------------------------
    # Load Image
    # -------------------------
    def set_image(self, image):
        self.scene().clear()
        self.image = image

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)

        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene().addItem(self.pixmap_item)
        Lista=self.scene().items()
        for index, element in enumerate(Lista):
            print (index, element)



        self.setSceneRect(QRectF(pixmap.rect()))
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

        self._empty = False
        #self.rois.clear()

    # -------------------------
    # Enable / Disable ROI Mode
    # -------------------------
    def set_draw_mode(self, enabled):
        self.draw_mode = enabled

        if enabled:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
        else:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)


    def set_draw_container_mode(self, enabled):
        self.draw_container_mode = enabled

        if enabled:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
        else:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    def set_line_width(self, ancho):
        self.ancho_linea = ancho


    # -------------------------
    # Zoom (disabled in ROI mode)
    # -------------------------
    def wheelEvent(self, event):
#        if self._empty or self.draw_mode:
        if self._empty or self.draw_mode or self.draw_container_mode:
            return

        if event.angleDelta().y() > 0:
            factor = self.zoom_factor
        else:
            factor = 1 / self.zoom_factor

        self.scale(factor, factor)

    def removeItem(self, indice):
        Lista=self.scene().items()
        total=len(Lista)
        indicef=total-1-(indice+1)

        for index, element in enumerate(Lista):
            print (index, element)
            if indicef==index:
                self.scene().removeItem(element)


    def clear(self):
        Lista=self.scene().items()
        #total=len(Lista)
        #indicef=total-1-(indice+1)

        for index, element in enumerate(Lista):
            #print (index, element)
            if index>1:
                self.scene().removeItem(element)



    def addItem (self,x1=100,y1=100,x2=200,y2=200,r=-1,g=-1,b=-1):
        rect = QRectF()
        rect.setRect(x1,y1, x2, y2)
        
        if (r==-1):
            self.colorAleatorio = self.GeneraColorAleatorio()
            color = QColor(self.colorAleatorio[0], self.colorAleatorio[1], self.colorAleatorio[2])
        else:
            color = QColor(r, g, b)
        pen = QPen(color, int(self.ancho_linea/8))

        self.scene().addRect(rect,pen)
    # -------------------------
    # ROI Selection
    # -------------------------
    def mousePressEvent(self, event):
        if self.image is None:
            return

        if self.draw_mode and event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True

            #if len(self.points)<3:
            self.start_point = self.mapToScene(event.pos())
            
            rect = QRectF(self.start_point, self.start_point).normalized()
            self.colorAleatorio = self.GeneraColorAleatorio()
            color = QColor(self.colorAleatorio[0], self.colorAleatorio[1], self.colorAleatorio[2])

            #pen = QPen(Qt.GlobalColor.red, int(self.ancho_linea/8))
            pen = QPen(color, int(self.ancho_linea/8))
            #rect.setPen(pen)

            #self.current_rect_item.setRect(rect)

            self.current_rect_item = self.scene().addRect(rect,pen)
#            self.scene().addRect()
            Lista=self.scene().items()
            for index, element in enumerate(Lista):
                print (index, element)
            #print(Lista)




        elif self.draw_container_mode and event.button() == Qt.MouseButton.RightButton:
            print (" SE CANCELA EL PEDO !!")


        else:
            super().mousePressEvent(event)
            #if self.draw_container_mode and event.button() == Qt.MouseButton.LeftButton:
                #self.start_point = self.mapToScene(event.pos())
             #   print (" Tentativa seleccion de punto")

            #else:

             #   super().mousePressEvent(event)


    def mouseMoveEvent(self, event):
        if self.draw_mode and self.drawing and self.current_rect_item:
            current_point = self.mapToScene(event.pos())
            rect = QRectF(self.start_point, current_point).normalized()
            self.current_rect_item.setRect(rect)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.draw_mode and event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False

            rect = self.current_rect_item.rect()

            x1 = rect.left()
            y1 = rect.top()
            x2 = rect.right()
            y2 = rect.bottom()

            #self.rois.append((x1, y1, x2, y2))
            #self.view2.set_image(cropped_image)
            #cv2.imshow("XX",self.image)

            print("ROI stored:", (x1, y1, x2, y2))
            self.finished.emit((x1, y1, x2, y2,self.colorAleatorio[0],self.colorAleatorio[1],self.colorAleatorio[2],-1)) # Emite una señal

        else:
            super().mouseReleaseEvent(event)


class MainWindow(QWidget):
    def on_worker_finished(self, result): # Al termianr la selección
    	result=tuple(map(int, result))
    	(x1,y1,x2,y2,r,g,b,TXT)=result
    	if TXT==-1: # Seleccion un rectangulo delimitador 
    	    print ("Marcar punto en la imagen",x1,y1,x2,y2)
    	    #colorAleatorio = self.GeneraColorAleatorio()

    	    #Cadena="Loc:["+str(self.LastPoint.x())+","+str(self.LastPoint.y())+"]"+"Color:"+str(colorAleatorio)
    	    Cadena="Loc:["
#    	    self.elements.append(MyElement(len(self.elements),str(len(self.elements))+Cadena,colorAleatorio,(self.LastPoint.x(),self.LastPoint.y())))    
    	    self.elements.append(MyElement(len(self.elements),str(len(self.elements))+Cadena,(b,g,r),(x1,y1,x2,y2)))    

#    	    self.elements.insert(0,MyElement(len(self.elements),str(len(self.elements))+Cadena,(b,g,r),(100,100)))    

    	    self.viewModelListView = ElementListModel(self.elements)
    	    self.ListView.setModel(self.viewModelListView)



    	if TXT==-21: # Seleccion un rectangulo delimitador 
        	gray_image_full = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)    	
        	clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        	imageCLAHE= clahe.apply(gray_image_full)
        	cropped_imageCLAHE = imageCLAHE[y1:y2, x1:x2]    	

        	cropped_image = self.image[y1:y2, x1:x2]
        	copy_cropped_image  = cropped_image.copy()
        	copy_cropped_image2 = cropped_image.copy()    	
        	
        	gray_image = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2GRAY)

        	#blurred = cv2.medianBlur(cropped_imageCLAHE, 5)
        	blurred = cv2.medianBlur(gray_image, 5)
        	
        	ret, thresh = cv2.threshold(gray_image, 127, 255, cv2.THRESH_OTSU  | cv2.THRESH_BINARY_INV)
    #    	contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        	contours, hierarchy = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        	cv2.drawContours(copy_cropped_image, contours, -1, (0, 255, 0), 3)
        	
        	
        	sorted_contours_desc = sorted(contours, key=cv2.contourArea, reverse=True)
        	print ("Contornos encontrados ",len(sorted_contours_desc))
        	for cnt in sorted_contours_desc:
        		# Get the straight bounding rectangle (x, y, width, height)
        		x, y, w, h = cv2.boundingRect(cnt)
        		print (" Ancho ",w," Alto: ",h)  
        		self.ListaWHs.append([w,h])
        		self.LabelSup.setText(""+str(self.ListaWHs))
        		  
        		# Draw the rectangle on the original image
        		cv2.rectangle(copy_cropped_image, (x, y), (x + w, y + h), (0, 255, 0), 2) # (0, 255, 0) is green, 2 is thickness
    #    		break # Solo me interesan las cosas GRANDES!

     #   	if (len(cnt)>0): # Detecta circulo si se encontro un contorno
        		circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, dp=1, minDist=1,param1=20, param2=w, minRadius=0, maxRadius=50)
	        	if circles is not None:
	        		print ("Cir-Culos encontrados ",len(circles))
	        		circles = np.uint16(np.around(circles))
	        		for i in circles[0, :]:
	        			cv2.circle(copy_cropped_image2, (i[0], i[1]), i[2], (0, 255, 255), 2) # Outer
	        			#cv2.circle(copy_cropped_image2, (i[0], i[1]), 1, (0, 100, 100), 3) # Centerif circles is not 
	        			
	        	else:
	        		print (" No hay Cir-CULOS")

        		break
        	
        	
        	
        		    	
        	self.view2.set_image(cropped_image)
        	self.view3.set_image(thresh)
        	self.view4.set_image(copy_cropped_image)
        	self.view5.set_image(copy_cropped_image2)
    	#else: # Seleccion un rectangulo delimitador 
        #	print ("Marcar punto en la imagen",x1,y1,x2,y2)
        #	self.ListaEsquinasROI.append([x1,y1])
        #	colorAleatorio = self.GeneraColorAleatorio()


        

    def draw_objects_from_file(self, image, text_file, image_width=800, image_height=600):
        """
        Reads a text file containing lines with:
        (x, y, r) (b, g, r)
        and draws circles using OpenCV.

        """
        colores = [
            (255,0,0),
            (0,255,0),
            (0,0,255),
            (0,255,255),
            (255,255,0),
            (255,0,255)    	         	           
        ]
        self.ListaCoordenadasMicroalgasEtiquetadas=[]
        self.view.clear()
        self.elements=[]
        conteo=1

        #print (text_file+".txt","type:",type(text_file))
        ArchivoTexto = Path(text_file)
        if (ArchivoTexto.is_file()):
            with open(text_file, 'r') as file:
        	    for line in file:
        	        line = line.strip()
        	        if not line:
        	            continue

        	        # Split into two tuples
        	        parts = line.split("\n")
        	        tuples=parts[0].split(")(")
        	        tuples[0]=tuples[0]+")" #parts[0].split(")(")
        	        tuples[1]="("+tuples[1] #parts[0].split(")(")

        	        my_tupleA = ast.literal_eval(tuples[0])
        	        my_tupleB = ast.literal_eval(tuples[1])
                


        	        x, y = my_tupleA
        	        #b, g, r = my_tupleB
        	        #r, g, b = my_tupleB
        	        #my_tupleB = self.view.GeneraColorAleatorio()
        	        #b, g, r = my_tupleB

        	        #if (conteo%1)==1:
            	    #    my_tupleB = (0,0,255) # ROJO?=> BGR
        	        #elif (conteo%2)==1:
            	    #    my_tupleB = (0,255,0) # ROJO?=> BGR
        	        #elif (conteo%3)==1:
            	    #    my_tupleB = (255,0,0) # ROJO?=> BGR
        	        #else:
            	    #    my_tupleB = (255,0,255) # ROJO?=> BGR
        	        my_tupleB = colores[(conteo - 1) % len(colores)]        
        	        r, g, b = my_tupleB
        	        #radio=80
        	        #print ("\t","S: ",tuples[0],"T: ",my_tupleA)
        	        print ("\t","S: ",tuples[1],"T: ",my_tupleB)


        	        self.ListaCoordenadasMicroalgasEtiquetadas.append(my_tupleA)
        	        self.view.addItem(x-10,y-10,20,20,r,g,b)
    #    	        self.elements.append(MyElement(len(self.elements),str(len(self.elements))+"XXX",my_tupleB, my_tupleA))    
        	        self.elements.append(MyElement(len(self.elements),str(len(self.elements))+"XXX",(b,g,r), my_tupleA))    
        	        #self.elements.insert (0, MyElement(len(self.elements),str(len(self.elements))+"XXX",my_tupleB, my_tupleA))  
        	        conteo+=1  


        self.viewModelListView = ElementListModel(self.elements)
        self.ListView.setModel(self.viewModelListView)

    	        #No dibujar nada
    	        #cv2.circle(image, (x-int(radio/2), y-int(radio/2)), radio, (b, g, r), 4)
        self.infoAlgasEtiquetadas.setText("Total Reference Algaes: "+str(len(self.ListaCoordenadasMicroalgasEtiquetadas)))

        return (image)
			    	
    def __init__(self):
        super().__init__()
        self.ListaCoordenadasMicroalgasEtiquetadas=[] # Lista de coordenadas de referencia (Leida de archivo)

        BUTTON_SIZE = QSize(300, 30)


        self.ListaWHs=[] # Lista que almacena lista (w,h) de las celular seleccionadas por el usuairo
        self.ListaEsquinasROI=[] # Lista que almacena 4 esquinas de la ROI

        self.setWindowTitle("Computer-Assisted Microalgae Counting App")

        self.view = GraphicsView()
        self.view.setMinimumSize(900, 700)
        self.view.finished.connect(self.on_worker_finished) # Conecta la señal con un metodo

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

        #self.load_button = QPushButton("Load Image")

        self.draw_toggle = QCheckBox("Mark microalga")
        self.draw_toggle.setEnabled(False) 
        self.iconoUndo = QPushButton ()
        icon = app.style().standardIcon(app.style().StandardPixmap.SP_DialogCancelButton)
        #self.iconoUndo.setIcon(QIcon("redcross.png"))
        self.iconoUndo.setIcon(icon)
        self.iconoUndo.setToolTip("Removes <b>rectangle</b> selection")
        self.iconoUndo.setIconSize(QSize(32, 32))
        self.iconoUndo.setMaximumWidth(50)
        self.iconoUndo.setEnabled(False) 


        #self.draw_rectangle_toggle = QCheckBox("Draw Rectangle")
        #self.draw_rectangle_toggle.setEnabled(False) 

        self.iconCleanROIs = QPushButton ()
        #self.iconCleanROIs.setIcon(QIcon("clean.png"))
        icon2 = app.style().standardIcon(app.style().StandardPixmap.SP_TrashIcon)
        self.iconCleanROIs.setIcon(icon2)
        self.iconCleanROIs.setToolTip("Clean marked reference <b>microalgae</b>")
        self.iconCleanROIs.setIconSize(QSize(32, 32))
        self.iconCleanROIs.setMaximumWidth(50)
        self.iconCleanROIs.setEnabled(False) 

        self.count_button = QPushButton("Count")
        self.count_button.setEnabled(False) 

        #self.load_button.clicked.connect(self.load_image)
        self.draw_toggle.toggled.connect(self.toggle_draw_mode)

        #self.draw_rectangle_toggle.toggled.connect(self.toggle_draw_rectangle_mode)
        #self.count_button.clicked.connect(self.CalculaTodosLosCirculos)
        self.count_button.clicked.connect(self.AislarAreaInteres)

        top_layout = QHBoxLayout()
        #top_layout.addWidget(self.load_button)
        #top_layout.addWidget(self.draw_rectangle_toggle)
        top_layout.addWidget(self.iconoUndo)
        top_layout.addWidget(self.draw_toggle)
        top_layout.addWidget(self.iconCleanROIs)
        top_layout.addWidget(self.count_button)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(1)
        self.slider.setMaximum(20)
        self.slider.setValue(10) # Set initial value
        self.slider.setSingleStep(1) # Sets keyboard navigation step

        self.slider2 = QSlider(Qt.Orientation.Horizontal)
        self.slider2.setMinimum(1)
        self.slider2.setMaximum(20)
        self.slider2.setValue(10) # Set initial value
        self.slider2.setSingleStep(1) # Sets keyboard navigation step


        self.locate = QPushButton("LocateAlgae")
        layoutSlider_mas_boton = QHBoxLayout()
        layoutSlider_mas_boton.addWidget(self.slider)
        layoutSlider_mas_boton.addWidget(self.slider2)
        layoutSlider_mas_boton.addWidget(self.locate)
        self.locate.clicked.connect(self.locate_reference_microalgae)
        self.locate.setEnabled(False) 

        self.currentImage=QLabel ("Current image: N/A")
        self.infoAlgasEtiquetadas=QLabel ("Total Reference Algaes: N/A")
        #self.infoAlgasEtiquetadasROI=QLabel ("Total Reference Algaes in ROI: N/A")

        layout = QVBoxLayout()
        layoutH = QHBoxLayout()
        layout.addLayout(top_layout)
        #self.LabelSup=QLabel("Size of selected areas: ")
        #layout.addWidget(self.LabelSup)
        layout.addWidget(self.currentImage)
        #layout.addWidget(self.slider)
        layout.addLayout(layoutSlider_mas_boton)
        layout.addWidget(self.infoAlgasEtiquetadas)
        #layout.addWidget(self.infoAlgasEtiquetadasROI)
        layout.addWidget(self.view)
        
        layoutPreviews = QVBoxLayout()
        layoutPreviews.addWidget(self.viewG3)
        layoutPreviews.addWidget(self.view2)
        layoutPreviews.addWidget(self.view3)
        layoutPreviews.addWidget(self.view4)
        layoutPreviews.addWidget(self.view5)

        
        #layoutRight = QVBoxLayout()
        #layoutRight.addWidget(self.viewG2)
        #layoutRight.addWidget(self.viewG4)

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
        #top_layoutxX.addStretch()
        top_layoutxX.addWidget(self.ChooseFolderButton)
        self.lbl_CurrentFolder = QLabel (" ")
        self.lbl_CurrentFolder.setFixedWidth(300)
        self.lbl_CurrentFile = QLabel (" ")
        self.lbl_CurrentFile.setFixedWidth(300)

        top_layoutxX.addWidget(QLabel ("Current Folder: "))
        top_layoutxX.addWidget(self.lbl_CurrentFolder)
        #top_layoutxX.addWidget(QLabel ("Current File: "))
        #top_layoutxX.addWidget(self.lbl_CurrentFile)
        #top_layoutxX.addWidget(QtWidgets.QListView())
#        self.QListWidgetArchivos=QListWidget()
        self.QListWidgetArchivos=QListWidget()
        #self.QListWidgetArchivos.setMinimumSize(BUTTON_SIZE)
  #      self.QListWidgetArchivos.setFixedWidth(300)
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
        # Antes de cargar el archivo seleccionado, se actualizará el TEXT con las coordenadas (independientemente si sufrio cambios o no)
        ArchivoAnterior=self.lbl_CurrentFolder.text()+"/"+self.lbl_CurrentFile.text()
        QMessageBox.information(None, "Success", "Update"+ArchivoAnterior)        

        ArchivoTexto = Path(ArchivoAnterior)
        if (ArchivoTexto.is_file()):
            Lista= self.elements
            for index, element in enumerate(Lista):
                print (index, element)
        #Lista=self.scene().items()

        #for index, element in enumerate(Lista

#          rect = self.current_rect_item.rect()

#            x1 = rect.left()
#            y1 = rect.top()
#            x2 = rect.right()
#            y2 = rect.bottom()            

        # Access the text of the clicked item
        print(f"Clicked: {item.text()}")
        self.lbl_CurrentFile.setText(item.text())
        Archivo=self.lbl_CurrentFolder.text()+"/"+item.text()
        print (Archivo)

        #self.ListaCoordenadasMicroalgasEtiquetadas=[]
        #self.view.clear()
        #self.elements=[]

        #reply = QMessageBox.question(None, "Confirm", "Do you want to save?")

        self.CargarImagen (Archivo)

    def load_folder(self):
        # Parameters: (parent, caption, directory, options)
        folder_path = QFileDialog.getExistingDirectory(
            self, 
            "Select Folder"
        )
        print (folder_path)

        self.ListaCoordenadasMicroalgasEtiquetadas=[]
        self.view.clear()
        self.elements=[]


        self.QListWidgetArchivos.clear()
        self.lbl_CurrentFolder.setText(folder_path)

#        files = [f for f in Path(folder_path).iterdir() if f.is_file()]

        extensions = ("*.png", "*.jpg", "*.jpeg")
        files = []
        for ext in extensions:
            files.extend(Path(folder_path).glob(ext))

        if (len(files)>0):

            #TODO: Extract images from folder path and popuplate a LIST
            self.lbl_CurrentFile.setText(files[0].name)
            for f in files:
                print (f)
                self.QListWidgetArchivos.addItem(f.name) 

            self.QListWidgetArchivos.setCurrentRow(0)  
            self.CargarImagen (str(files[0]))



            #TODO: Habilitar controles

    def CargarImagen (self,file_path):
        if file_path:
            self.image = cv2.imread(file_path)
            self.image_Copia = cv2.imread(file_path)

            basename2 = os.path.basename(file_path)
            self.AnchoLinea = int(self.image.shape[0]/200)

            self.view.set_line_width(self.AnchoLinea)
            self.viewG2.set_line_width(self.AnchoLinea)

#            self.currentImage.setText("Current image:   "+basename2+" Dimensiones: ["+str(self.image.shape)+"]"+"AnchoLin"+str(self.AnchoLinea))
            self.currentImage.setText("Current image:   "+basename2+" Dimensiones: ["+str(self.image.shape)+"]")

            self.view.set_image(self.image)
            self.draw_toggle.setEnabled(True) 
            #self.draw_rectangle_toggle.setEnabled(True) 
            self.count_button.setEnabled(True) 
            self.iconoUndo.setEnabled(True) 
            self.iconCleanROIs.setEnabled(True) 
            self.locate.setEnabled(True) 
            print ("\t\t\t",file_path+".txt")
            ArchivoTexto = Path(file_path+".txt")
            print (ArchivoTexto.is_file())
            #if (ArchivoTexto.is_file()):
            Imagen3 = self.draw_objects_from_file(self.image_Copia,str(file_path)+".txt")
            self.viewG3.set_image(Imagen3) 


    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        self.CargarImagen (file_path)



    def MyMouseClickedOnListView (self,e):
        IndiceCliqueado=self.ListView.currentIndex().row()
        dialog = CustomDialog(Indice=IndiceCliqueado)
        if dialog.exec() == 1:

            print ("Puto Indice Clicquetao",IndiceCliqueado)
            if (self.elements[IndiceCliqueado].filed):
                self.elements[IndiceCliqueado].filed=False
            else:
                self.elements[IndiceCliqueado].filed=True

    	    #self.elements.append(MyElement(len(self.elements),str(len(self.elements))+Cadena,(b,g,r),(100,100)))    
            self.elements.pop(IndiceCliqueado)
            self.viewModelListView = ElementListModel(self.elements)
            self.ListView.setModel(self.viewModelListView)

            self.view.removeItem(IndiceCliqueado)




        # Actualizar la vista
        #self.ActualizarImagen()

    def GeneraColorAleatorio (self):
        nums = []
        for _ in range(3):
            nums.append(int(255*random.random()))
        nums = tuple(nums)
        #print (nums)
        return (nums)




    def locate_reference_microalgae (self):
        print ("Locating Microalgaes ---")
        if len (self.ListaEsquinasROI)==4:
            print ("ESI:",self.ListaEsquinasROI[0])
            print ("ESD:",self.ListaEsquinasROI[1])
            print ("EID:",self.ListaEsquinasROI[2])
            print ("EII:",self.ListaEsquinasROI[1])

#            for e in self.ListaEsquinasROI:
#                print (e)

            for e in self.ListaCoordenadasMicroalgasEtiquetadas:
                print (e)
    	        #cv2.circle(image, (x-int(radio/2), y-int(radio/2)), radio, (b, g, r), 4)
        else:
            return None

    def toggle_draw_mode(self, checked):
        self.view.set_draw_mode(checked)

    def toggle_draw_rectangle_mode(self, checked):
#        self.view.set_draw_rectangle_mode(checked)
        self.view.set_draw_container_mode(checked)
        print ("Dibujar Rectangolo Contenedor",checked)

    def AislarAreaInteres (self):

        original=self.image.copy()
		
        (height, width,_) = self.image.shape
        black_image = np.zeros((height, width, 3), np.uint8)            
        print ("DImensiones Originales:",height, width)


        if len(self.ListaEsquinasROI)==4:
            x1, y1 = self.ListaEsquinasROI[0]
            x2, y2 = self.ListaEsquinasROI[1]
            x3, y3 = self.ListaEsquinasROI[2]                
            x4, y4 = self.ListaEsquinasROI[3]


            four_points = np.array([[[x1, y1]], [[x2, y2]], [[x3, y3]], [[x4, y4]]], dtype=np.int32)            

            cv2.fillPoly(black_image, pts=[four_points], color=(255, 255, 255))

            grayMask = cv2.cvtColor(black_image, cv2.COLOR_BGR2GRAY)


            R=cv2.bitwise_and(original, original, mask=grayMask)
#            R = cv2.cvtColor(R, cv2.COLOR_BGR2GRAY)

            #self.viewG2.set_image(R)                
            self.CalculaTodosLosCirculos (R)
        else: return None


    def CalculaTodosLosCirculos (self, imagenEntrada):
	# Convert to grayscale. 
        gray = cv2.cvtColor(imagenEntrada, cv2.COLOR_BGR2GRAY) 
        imageCirculosEncontrados=imagenEntrada.copy()

	# Blur using 3 * 3 kernel. 
        gray_blurred = cv2.blur(gray, (3, 3)) 

	# Apply Hough transform on the blurred image. 
        detected_circles = cv2.HoughCircles(gray_blurred, 
					cv2.HOUGH_GRADIENT, 1, 1, param1 = 20, 
				param2 = 15, minRadius = 1, maxRadius = 15) 
				
#    		circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, dp=1, minDist=1,param1=20, param2=w, minRadius=0, maxRadius=50)
				

	# Draw circles that are detected. 
        if detected_circles is not None: 

		# Convert the circle parameters a, b and r to integers. 
        	detected_circles = np.uint16(np.around(detected_circles)) 

        	for pt in detected_circles[0, :]: 
        		a, b, r = pt[0], pt[1], pt[2] 

			# Draw the circumference of the circle. 
        		cv2.circle(imageCirculosEncontrados, (a, b), r, (255, 0, 0), 5) 

			# Draw a small circle (of radius 1) to show the center. 
        		cv2.circle(imageCirculosEncontrados, (a, b), 1, (0, 0, 255), 3) 

        self.viewG2.set_image(imageCirculosEncontrados)                


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())



