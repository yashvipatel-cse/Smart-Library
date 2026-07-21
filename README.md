# 📚 SmartLib – AI Powered Library Management System

### Intelligent Library Shelf Monitoring using **YOLOv8 • OCR • OpenCV • Spring Boot • Flask • ESP32 RFID**

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Java](https://img.shields.io/badge/Java-17-orange.svg)
![Spring Boot](https://img.shields.io/badge/Spring_Boot-3.x-brightgreen.svg)
![Flask](https://img.shields.io/badge/Flask-Backend-lightgrey.svg)
![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-red.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer_Vision-blue.svg)
![MySQL](https://img.shields.io/badge/MySQL-Database-blue.svg)
![ESP32](https://img.shields.io/badge/ESP32-RFID-success.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 📖 Overview

SmartLib is an AI-powered library management system that automates book detection, OCR-based identification, misplaced book detection, and RFID-assisted library management.

Traditional library systems rely on manual inspection and barcode scanning. SmartLib simplifies this process by combining Computer Vision, Object Detection, Optical Character Recognition (OCR), and RFID technologies into one intelligent platform.

Using a single image of a bookshelf, the system can:

* Detect books automatically
* Extract book spines
* Read labels using OCR
* Match books with the library database
* Identify misplaced books
* Support RFID-based inventory management

---

## ✨ Features

### 🤖 Artificial Intelligence

* YOLOv8 book detection
* OCR-based book identification
* OpenCV image preprocessing
* Automatic ROI extraction

### 📚 Library Management

* Book registration and management
* Shelf monitoring
* Misplaced book detection
* Scan history
* Search and filtering

### 📡 Embedded System

* ESP32 integration
* MFRC522 RFID reader support
* RFID-based book lookup
* Real-time communication

### 💻 Web Application

* Spring Boot REST API
* Flask AI service
* Responsive dashboard
* Dark theme UI

---

## 🏗️ Project Structure

```text
SmarLIB_FINAL/
├── backend/                # Spring Boot backend
├── frontend/               # Web dashboard
├── mobile-app/             # Mobile application
├── python-ocr-service/     # YOLO and OCR services
├── esp32-rfid/             # ESP32 RFID module
├── database/               # SQL scripts
├── docs/                   # Architecture and report
├── screenshots/            # Project screenshots
└── README.md
```

---

## 🛠️ Tech Stack

### Backend

* Java 17
* Spring Boot
* Maven

### AI & Computer Vision

* Python
* Flask
* YOLOv8
* OpenCV

### Database

* MySQL

### Embedded System

* ESP32
* MFRC522 RFID Module

### Frontend

* HTML
* CSS
* JavaScript

---

## 🔄 Workflow

```text
Bookshelf Image
        │
        ▼
YOLOv8 Object Detection
        │
        ▼
Book Spine Extraction
        │
        ▼
OpenCV Preprocessing
        │
        ▼
OCR Recognition
        │
        ▼
Book Number Extraction
        │
        ▼
Flask AI Service
        │
        ▼
Spring Boot REST API
        │
        ▼
MySQL Database
        │
        ▼
Shelf Validation
        │
        ▼
Misplaced Book Detection
```

---

## 📂 Documentation

Project documentation is available in:

* `docs/architecture.png`
* `docs/workflow.png`
* `docs/timeline.png`
* `docs/Smart Library Management System_REPORT_FINAL.pdf`

---

## 📸 Screenshots

Add screenshots from:

* Dashboard
* Camera Scan
* Detection Results
* Mobile App

---

## 📜 License

This project is licensed under the MIT License.
