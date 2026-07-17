# Computer-Assisted Counting, Labelling and Dataset Microalgae App

An interactive, graphical user interface (GUI) application powered by **PyQt6** and **OpenCV** designed for automated and manual tracking, annotation, profiling, and counting of microalgae in microscopy images. 

This repository provides an end-to-end workspace for researchers and lab technicians to import raw microscopy datasets, establish manual regions of interest (ROIs), extract object contours, isolate candidates via multi-threshold analysis pipelines, and evaluate counting models natively.

---

## 🚀 Key Features

* **Interactive Graphics View**: Supports seamless mouse panning and scroll-wheel zooming on high-resolution microscopic frames without performance drops.
* **Dynamic ROI & Polygon Annotation**: Easily mark ground-truth microalgae references using customizable rectangular selections with real-time feedback.
* **Multi-Threaded Progress UI**: Built-in frameless circular loading spinners (`CircularSpinner` & `CircularProgressDialog`) to ensure the user interface remains highly responsive during heavy computer vision batches.
* **Robust Candidate Detection Engine**: Combines 4 distinct computer vision approaches to extract cell coordinates:
  * Dynamic Otsu global thresholding contours.
  * Contrast Limited Adaptive Histogram Equalization (**CLAHE**) localized contour extraction.
  * Advanced feature blob extraction with `SimpleBlobDetector`.
  * Multi-range intensity masking pipelines.
* **Automated Data Validation & Verification**: Computes Euclidean distance arrays to automatically cross-check algorithmic predictions against manual annotations, isolating accurate matches, falsified indicators, and untracked artifacts.
* **Persistent Dataset Management**: Saves geometric markers and colors natively inside light `.txt` logs side-by-side with your microscopy files. Reload datasets instantly upon directory navigation.

---

## 🛠️ Architecture Overview

The system architecture is structured across clean, modular visual and logical processing components:

* **`GraphicsView`**: A custom `QGraphicsView` subclass handling matrix-to-viewport translations, interactive visual feedback, shape overlay tracking, and random color assignment pipelines.
* **`ElementListModel` & `ElementThumbDelegate`**: Model-View-Delegate structure designed to display real-time interactive tracking summaries, status indications, and color icons in a `QListView`.
* **`GenerateCandidates`**: The mathematical core containing localized algorithmic routines that execute overlapping feature extractions, filtering coordinate conflicts by enforcing configurable spatial minimum distance criteria.
* **`MainWindow`**: The central supervisor coordinating directory tree mapping, asynchronous worker feedback, target file over-writing workflows, and sub-window evaluations.

---

## 📦 Requirements & Installation

Ensure you have Python 3.10+ installed on your workspace environment.

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/microalgae-counting-app.git
cd microalgae-counting-app
```

### 2. Install Python Dependencies
Install required core numerical computing, computer vision, and desktop application libraries:
```bash
pip install numpy opencv-python scipy PyQt6
```

> **Note**: This application depends on companion analysis modules (`CNNEvaluation_Microalgaes`, `LocateCandidatesinDataset`, and `UpdateWindowProgress`). Make sure these remain stored in the root folder alongside the main script.

---

## 🔧 Usage Instructions

Launch the program using your console terminal environment:

```bash
python main.py
```

### 1. Loading Datasets
* Click on **"Choose folder"** in the left sidebar menu to point the system to your directory holding target image types (`.png`, `.jpg`, `.jpeg`).
* Select any item inside the localized workspace file list tree widget to load it onto the main interactive graphics viewport workspace automatically.

### 2. Manual Annotation
* Toggle the **"Mark microalga"** checkbox to enter design mode.
* Left-click and drag across a target microalgae structure to generate an annotated bounding shape box.
* The system automatically generates a text tracker file matching the path format `[filename].txt` to save target cell entries permanently.
* If a mistake is made, single-click an item in the **"Marked microalgae regions"** view to prompt an edit/remove confirmation dialog box.

### 3. Automated Analysis
* Adjust parameter range sliders to control algorithm sensitivity thresholds.
* Click **"Analyze all"** to launch evaluation loops spanning your loaded image sets, invoking integrated network evaluation sub-panels automatically.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
