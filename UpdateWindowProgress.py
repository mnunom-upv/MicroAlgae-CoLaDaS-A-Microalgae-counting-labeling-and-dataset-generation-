import sys
import time
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtWidgets import QListWidget, QListWidgetItem
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QSlider,
    QHBoxLayout, QPushButton, QFileDialog,
    QGraphicsView, QGraphicsScene, QLabel, QGraphicsLineItem,
    QGraphicsPixmapItem, QCheckBox, QDialog, QLineEdit
)
from PyQt6.QtGui import QPixmap, QImage, QPen, QIcon, QColor
#from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtCore import *
from PyQt6.QtCore import QSize, Qt
from PyQt6 import QtCore, QtGui, QtWidgets
#
from PyQt6.QtWidgets import QMessageBox


from CNNEvaluation_Microalgaes import *
from LocateCandidatesinDataset import *


# 1. Define the worker class that handles the heavy process
class HeavyWorker(QObject):
    # Signals to communicate progress back to the main UI
    progress_changed = pyqtSignal(int)
    task_finished = pyqtSignal()

    def run_heavy_task(self):
        """Simulates a heavy calculation or download."""
        #RutaDirectorio="18Agosto"

        print (self.RutaDirectorio)
        #exit()

        OBJ = ProcesadorCandidatos (self.RutaDirectorio)
        OBJ.ProcesadrDirectorio(self.progress_changed)

        #folder_path = Path(self.RutaDirectorio)
        folder_path = self.RutaDirectorio


        #folder_path = Path("18Agosto"+"/"+"18Agosto")

#        Objeto = CNNEValuacion (str(folder_path.name)+"/"+str(folder_path.name))
#        Objeto.evaluate()


        #Objeto = CNNEValuacion (str(folder_path.name)+"/"+str(folder_path.name),self.epocas)
        Objeto = CNNEValuacion (folder_path+"/"+folder_path,self.epocas)
        Objeto.evaluate(self.progress_changed)

        # 2. Load the bitmap/image from file
        self.pixmap = QPixmap("my_plot.png")
        self.label.setPixmap(self.pixmap.scaled(600, 800, Qt.AspectRatioMode.KeepAspectRatio))


#my_plot.png


        #for i in range(1, 101):
        #    time.sleep(0.05)  # Simulate work
        #    self.progress_changed.emit(i)  # Send progress to UI

        self.task_finished.emit()  # Notify UI that work is done





# 2. Define the "Please Wait" dialog window
class WaitDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Processing")
        self.setModal(True)  # Blocks interaction with the main window
        self.setFixedSize(300, 100)

        # Setup simple layout with label and progress bar
        layout = QVBoxLayout()
        self.label = QLabel("Please wait, processing data...", self)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)

        layout.addWidget(self.label)
        layout.addWidget(self.progress_bar)
        self.setLayout(layout)

    def update_progress(self, value):
        self.progress_bar.setValue(value)


# 3. Define the Main Window
class TrainingWindow(QWidget):

    def __init__(self,folder="10Agost"):
        super().__init__()
        self.setWindowTitle("Microalgae Training CNN Experimenter")
        self.folder=folder
        #self.setFixedSize(400, 200)

        # Main window button to trigger the task
        self.button = QPushButton("Train CNN", self)
        self.button.clicked.connect(self.start_process)
        self.button.setFixedWidth(200)
        B2 = QPushButton("P2")
        B2.setFixedWidth(200)

        B3 = QPushButton("P3")
        B3.setFixedWidth(200)

        self.QL1 = QLineEdit()
        self.QL1.setText("50")

        #self.setCentralWidget(self.button)

        self.label = QLabel(self)
        self.pixmap = QPixmap("Primitives.pngCacho.png")
        self.label.setFixedWidth(1000)
        self.label.setPixmap(self.pixmap.scaled(600, 800, Qt.AspectRatioMode.KeepAspectRatio))
        lbl = QLabel("Epochs: ")
        lbl.setFixedHeight(50)


        layoutV = QVBoxLayout()
        layoutV.addWidget(self.button)
        layoutV.addWidget(lbl)
        layoutV.addWidget(self.QL1)
        layoutV.addWidget(B2)
        layoutV.addWidget(B3)

        layoutH = QHBoxLayout()
        layoutH.addLayout(layoutV)
        layoutH.addWidget(self.label)
        self.setLayout(layoutH)
        self.resize(1000, 600)






    def start_process(self):
        # Disable button to prevent double-clicking
        self.button.setEnabled(False)

        # Initialize the dialog window
        self.wait_dialog = WaitDialog(self)

        self.pixmap = QPixmap("Primitives.pngCacho.png")
        self.label.setFixedWidth(1000)
        self.label.setPixmap(self.pixmap.scaled(600, 800, Qt.AspectRatioMode.KeepAspectRatio))


        # Setup Thread and Worker
        self.thread = QThread()
        self.worker = HeavyWorker()
        self.worker.label=self.label
        self.worker.epocas=int(self.QL1.text())
        self.worker.RutaDirectorio=self.folder


        # Move the worker logic to the background thread
        self.worker.moveToThread(self.thread)

        # Connect signals and slots
        self.thread.started.connect(self.worker.run_heavy_task)
        self.worker.progress_changed.connect(self.wait_dialog.update_progress)

        # Clean up threads and close dialog when done
        self.worker.task_finished.connect(self.thread.quit)
        self.worker.task_finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.wait_dialog.accept)
        self.thread.finished.connect(lambda: self.button.setEnabled(True))

        # Start the background thread and show the modal dialog
        self.thread.start()
        self.wait_dialog.exec()  # .exec() blocks main window interaction natively


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TrainingWindow()
    window.folder="18AgostoNueva"
    window.show()
    sys.exit(app.exec())
