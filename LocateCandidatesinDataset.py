import cv2
import numpy as np
import csv
import re
import math
import os
from pathlib import Path

from CNNEvaluation_Microalgaes import *

class ProcesadorCandidatos():
    def __init__(self, dir_name):
        self.contadorImagenes=0
        self.dir_name = dir_name
        print ("create",self.dir_name)


    def LocalizarCandidatos (self, img, TXT_FILE, maximo=-1):
        # ==========================================================
        # PARAMETERS
        # ==========================================================

        MIN_SIZE = 3
        MAX_SIZE = 30

        MIN_AREA = 15
        MAX_AREA = 180

        MIN_SOLIDITY = 0.80
        MIN_EXTENT = 0.35

        MIN_RATIO = 0.60
        MAX_RATIO = 1.60

        MIN_CIRCULARITY = 0.30

        # ==========================================================
        # LOAD IMAGE
        # ==========================================================

        #img = cv2.imread(IMAGE_FILE)

        if img is None:
            raise Exception("Cannot load image.")

        output = img.copy()

        # ====================================================
        # Cargas Coordenadas de Archivos
        # ====================================================
        self.CargarAlgasRealesDeArchivo (TXT_FILE)

        # ====================================================
        # Calcular el Rectangulo Contenedor y Dibujarlo
        # ====================================================
        R=self.bounding_box_Marked_MicroAlgage()
        self.InicioY=R[1][1]
        self.InicioX=R[0][0]
        self.FinY=R[3][1]
        self.FinX=R[1][0]
        cv2.rectangle(
            output,
            (self.InicioX,self.InicioY),
            (self.FinX,self.FinY),
            (0,0,255),
            1
        )


        # ====================================================
        # Dibujar las Algas de Referencia
        # ====================================================

        self.DibujarAlgasReales (output)



        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # ==========================================================
        # REMOVE ILLUMINATION
        # ==========================================================

        background = cv2.GaussianBlur(gray, (51,51), 0)
        corrected = cv2.subtract(background, gray)

        # ==========================================================
        # CLAHE
        # ==========================================================

        clahe = cv2.createCLAHE(
            clipLimit=2.5,
            tileGridSize=(8,8)
        )

        corrected = clahe.apply(corrected)

        # ==========================================================
        # DIFFERENCE OF GAUSSIANS
        # ==========================================================

        g1 = cv2.GaussianBlur(corrected, (0,0), 1.2)
        g2 = cv2.GaussianBlur(corrected, (0,0), 4.0)

        dog = cv2.subtract(g1, g2)

        dog = cv2.normalize(
            dog,
            None,
            0,
            255,
            cv2.NORM_MINMAX
        )

        dog = dog.astype(np.uint8)

        # ==========================================================
        # THRESHOLD
        # ==========================================================

        _, binary = cv2.threshold(
            dog,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        # ==========================================================
        # REMOVE GRID
        # ==========================================================

        horizontal_kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (45,1)
        )

        vertical_kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (1,45)
        )

        horizontal = cv2.morphologyEx(
            binary,
            cv2.MORPH_OPEN,
            horizontal_kernel
        )

        vertical = cv2.morphologyEx(
            binary,
            cv2.MORPH_OPEN,
            vertical_kernel
        )

        grid = cv2.bitwise_or(horizontal, vertical)

        particles = cv2.subtract(binary, grid)

        # ==========================================================
        # CLEANUP
        # ==========================================================

        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (3,3)
        )

        particles = cv2.morphologyEx(
            particles,
            cv2.MORPH_OPEN,
            kernel
        )

        particles = cv2.morphologyEx(
            particles,
            cv2.MORPH_CLOSE,
            kernel
        )

        # ==========================================================
        # FIND CONTOURS
        # ==========================================================

        contours, _ = cv2.findContours(
            particles,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        results = []

        object_id = 1

        for cnt in contours:

            area = cv2.contourArea(cnt)

            if area < MIN_AREA or area > MAX_AREA:
                continue

            x, y, w, h = cv2.boundingRect(cnt)

            # Incluir solo candidatas dentro del BOX
#            if True:
            if self.InicioY < y < self.FinY and self.InicioX < x < self.FinX:

                if w < MIN_SIZE or w > MAX_SIZE:
                    continue

                if h < MIN_SIZE or h > MAX_SIZE:
                    continue

                ratio = w / float(h)

                if ratio < MIN_RATIO or ratio > MAX_RATIO:
                    continue

                rect_area = w * h
                extent = area / rect_area

                hull = cv2.convexHull(cnt)
                hull_area = cv2.contourArea(hull)

                if hull_area == 0:
                    continue

                solidity = area / hull_area

                perimeter = cv2.arcLength(cnt, True)

                if perimeter == 0:
                    continue

                circularity = 4 * np.pi * area / (perimeter * perimeter)

                if solidity < MIN_SOLIDITY:
                    continue

                if extent < MIN_EXTENT:
                    continue

                if circularity < MIN_CIRCULARITY:
                    continue

                M = cv2.moments(cnt)

                if M["m00"] == 0:
                    continue

                cx = int(M["m10"]/M["m00"])
                cy = int(M["m01"]/M["m00"])

                results.append([
                    object_id,
                    cx,
                    cy,
                    w,
                    h,
                    area,
                    ratio,
                    extent,
                    solidity,
                    circularity
                ])

                cv2.drawContours(output, [cnt], -1, (0,255,0), 2)

                cv2.rectangle(
                    output,
                    (x,y),
                    (x+w,y+h),
                    (0,0,255),
                    1
                )

                cv2.circle(
                    output,
                    (cx,cy),
                    2,
                    (255,0,0),
                    -1
                )

                cv2.putText(
                    output,
                    str(object_id),
                    (x,y-3),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (0,255,255),
                    1
                )

                object_id += 1

        # ==========================================================
        # SAVE CSV
        # ==========================================================

#        with open("detected_particles.csv", "w", newline="") as f:
#            writer = csv.writer(f)
#            writer.writerow([
#                "ID",
#                "CenterX",
#                "CenterY",
#                "Width",
#                "Height",
#                "Area",
#                "AspectRatio",
#                "Extent",
#                "Solidity",
                #"Circularity"
#            ])
 #           writer.writerows(results)


        print("--------------------------------")
        print("Detected particles:", len(results))
        print("--------------------------------")

        #cv2.imshow("DoG", dog)
        #cv2.imshow("Binary", binary)
        #cv2.imshow("Particles", particles)
        #cv2.imshow("Detected Objects", output)

        cv2.imwrite("Salida.png",output)

        #cv2.waitKey(0)
        #cv2.destroyAllWindows()



        self.matches = []
        # Maximum Euclidean distance (pixels)
        self.MAX_DISTANCE = 30.0
        self.matched_csv = set()
        #self.ObtenerAlgasSinMatch (results)
        R= self.ObtenerCandidatoSinMatchConAlga  (results, img, maximo)
        return (R)
        
    def DibujarAlgasReales (self, output):
        for txt in self.txt_objects:
            print ("testing",txt)

            cv2.circle(
                output,
                (txt["x"] ,txt["y"] ),
                5,
                (0,0,255),
                -1
            )


    def ObtenerAlgasSinMatch (self, results):

        for txt in self.txt_objects:
            print ("testing",txt)

            best = None
            best_distance = 1e9

            for csv_obj in results:
                d = math.hypot(
                    txt["x"] - csv_obj[1],
                    txt["y"] - csv_obj[2]
                )

                if d < best_distance:
                    best_distance = d
                    best = csv_obj

            if best_distance <= self.MAX_DISTANCE:
                self.matches.append({
                    "txt_id": txt["id"],
                    #"csv_id": best["id"],
                    "txt_x": txt["x"],
                    "txt_y": txt["y"],
                    "csv_x": best[1],
                    "csv_y": best[2],
                    "distance": best_distance
                })

                #self.matched_csv.add(best["id"])

#        print ()

    def ObtenerCandidatoSinMatchConAlga (self, results, img, maximo):
        Counter=0
        CounterUnmatched=0
        self.matches=[]
        self.unmatches=[]
        for csv_obj in results:
            best = None
            best_distance = 1e9

            for txt in self.txt_objects:
                #print ("testing",txt)
                d = math.hypot(
                    txt["x"] - csv_obj[1],
                    txt["y"] - csv_obj[2]
                )

                if d < best_distance:
                    best_distance = d
                    best = txt


            if best_distance <= self.MAX_DISTANCE:
                #print ("\t\t\t Found a Match in Algae",Counter)
                print ("=== Matched CSV ",csv_obj,best)    
                Counter+=1
#                self.matches.append({
#                    "txt_id": best["id"],
#                    "txt_x": best["x"],
#                    "txt_y": best["y"],
#                    "distance": best_distance
#                })
                self.matches.append(csv_obj)
            else:
                CounterUnmatched+=1
                print ("=== Unmatched CSV ",csv_obj)    
#                self.unmatches.append({
#                    "txt_id": csv_obj[0],
#                    "txt_x": csv_obj[1],
#                    "txt_y": csv_obj[2],
#                    "distance": best_distance
#                })
                self.unmatches.append(csv_obj)

        S= ""
        S+="=== Marked Algaes "+str(len(self.txt_objects))+"\n"
        S+="=== Total Candidates "+str(len(results))+"\n"
        S+="=== Counter Matched "+str(Counter)    +"\n"
        S+="=== Conteo No Match "+str(CounterUnmatched)+"\n"
        S+="=== Unmatched Algaes  "+str(len(self.txt_objects)-Counter)+"\n"
        R = [len(self.txt_objects),len(results),Counter,CounterUnmatched]
        print (S)    

#                "CenterX",
#                "CenterY",
#                "Width",
#                "Height",

        Minimo=min(Counter,CounterUnmatched)
        for i in range (Minimo):
            print (" Matched ",i,self.matches[i])
            print (" \t Unmatched ",i,self.unmatches[i])

            ImagenPos=img[
self.matches[i][2]-int(self.matches[i][4]):self.matches[i][2]+int(self.matches[i][4]),
self.matches[i][1]-int(self.matches[i][3]):self.matches[i][1]+int(self.matches[i][3])
]
            ImagenNeg=img[
self.unmatches[i][2]-int(self.unmatches[i][4]):self.unmatches[i][2]+int(self.unmatches[i][4]),
self.unmatches[i][1]-int(self.unmatches[i][3]):self.unmatches[i][1]+int(self.unmatches[i][3])
]
#            cv2.imshow("XXX",ImagenPos)
#            cv2.imshow("YYY",ImagenNeg)
#            cv2.waitKey()
            fixed_string = f"{self.contadorImagenes:05d}"
            print (self.dir_name+"/POS/img_"+fixed_string+".png")
            print (self.dir_name+"/NEG/img_"+fixed_string+".png")

            cv2.imwrite(self.dir_name+"/POS/img_"+fixed_string+".png",ImagenPos)
            cv2.imwrite(self.dir_name+"/NEG/img_"+fixed_string+".png",ImagenNeg)


            self.contadorImagenes+=1;        
        return (R)


    def CargarAlgasRealesDeArchivo (self, TXT_FILE):
        self.txt_objects = []
        pattern = re.compile(r"\((\d+),\s*(\d+)\)")
        with open(TXT_FILE, "r") as f:
            for idx, line in enumerate(f):
                m = pattern.search(line)

                if m is None:
                    continue

                x = int(m.group(1))
                y = int(m.group(2))

                self.txt_objects.append({
                    "id": idx + 1,
                    "x": x,
                    "y": y,
                    "line": line.strip()
                })

        print("TXT objects:", len(self.txt_objects))



    def bounding_box_Marked_MicroAlgage(self):
        """
        points: lista de tuplas [(x1, y1), (x2, y2), ...]
        return: lista de 4 esquinas del rectángulo
        """
        #if not points:
        #    raise ValueError("La lista de puntos está vacía")

        xs = []
        ys = []
        for e in self.txt_objects:
            #(x,y,x2,y2) = e.coordinates
            #print (e.coordinates)
            xs.append(e["x"])
            ys.append(e["y"])


#        xs = [p[0] for p in self.elements]
#        ys = [p[1] for p in self.elements]

        min_x = min(xs)
        max_x = max(xs)
        min_y = min(ys)
        max_y = max(ys)

        # Esquinas del rectángulo (en sentido horario)
        return [
            (min_x, min_y),  # esquina inferior izquierda
            (max_x, min_y),  # esquina inferior derecha
            (max_x, max_y),  # esquina superior derecha
            (min_x, max_y)   # esquina superior izquierda
        ]

    def ProcesadrDirectorio (self, emisor=None) :



        # Lists only .txt files in the specified directory
        #Directorio="18Agosto"
        Directorio=self.dir_name

        Ruta=Path(Directorio)
        files = list(Ruta.glob("*.jpg"))
        #dir_name = "18Agosto"

        Path(Directorio+"/"+Directorio).mkdir(parents=True, exist_ok=True)
        Path(Directorio+"/"+Directorio+"/POS").mkdir(parents=True, exist_ok=True)
        Path(Directorio+"/"+Directorio+"/NEG").mkdir(parents=True, exist_ok=True)
        #exit()

        #print (dir_name)


        #E = ProcesadorCandidatos(Directorio+"/"+Directorio)
        self.dir_name = Directorio+"/"+Directorio
        Res=""
        Matriz=[]
        indice=1
        for f in files:
            print (f)
            print (str(f)+".txt")
            if emisor is not None: emisor.emit(indice) 
            indice+=1


            IMAGE_FILE = str(f)
            ANNOT__FILE = str(f)+".txt"

            img = cv2.imread(IMAGE_FILE)

            Res += IMAGE_FILE + "\n" ;
            ResAnalisis = self.LocalizarCandidatos(img,ANNOT__FILE)
            Matriz.append([IMAGE_FILE,ResAnalisis])
        #    exit()

        SumaPos=0
        SumaNeg=0
        SumaBal=0
        for i in Matriz:
            V=i[1]
            print (i,V,min(V[2],V[3]))
            SumaPos+=V[2]
            SumaNeg+=V[3]
            SumaBal+=min(V[2],V[3])

        print(SumaPos,SumaNeg,SumaBal)

#OBJ = ProcesadorCandidatos ("18AGosto")
#OBJ.ProcesadrDirectorio()

#Objeto = CNNEValuacion ("18Agosto/18Agosto")
#Objeto.evaluate()

