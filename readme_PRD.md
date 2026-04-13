# 🌱 PlantLab — Product Requirements Document (PRD)

## 1. Overview

PlantLab is a multi-user, multi-device platform for monitoring and automating plant growth using AI + hardware.

The system integrates:

* Raspberry Pi-based plant devices
* Sensors (moisture, temperature, humidity)
* Camera for plant monitoring
* Web platform for users

Goal:
Build a system where users can **monitor, control, and analyze plant growth remotely**.

---

## 2. Problem

Existing plant systems:

* are closed systems (no extensibility)
* rely on simple rules (no intelligence)
* lack multi-user and multi-device support
* lack visual growth tracking

---

## 3. Goals (V1)

### Core goals:

* Web dashboard for plant monitoring
* Multi-user system
* Multi-device support
* Historical data logging
* Remote control of devices

### Success criteria:

* User can log in and see plant data
* System logs data continuously
* User can control pump and light remotely
* Supports multiple devices per user

---

## 4. Users

### Hobbyist

* 1–3 plants
* wants automation and insights

### Educator

* multiple plant systems
* classroom management

### Developer

* wants extensibility and APIs

---

## 5. Core Features

---

### 5.1 Authentication

* Google account sign-in for V1
* login/logout
* session management
* additional sign-in methods can be added later

---

### 5.2 Device Management

User can:

* add a device
* name device
* assign plant type
* assign location

---

### 5.3 Dashboard

Each device shows:

* latest image
* soil moisture
* temperature
* humidity
* light status
* pump status
* last watering time

---

### 5.4 Control

User can:

* turn pump ON/OFF
* turn light ON/OFF
* override automation

---

### 5.5 Automation

System automatically:

* waters when moisture < threshold
* controls light based on schedule

---

### 5.6 Data Logging

System stores:

* timestamp
* moisture
* temperature
* humidity
* pump events
* light events
* image path

---

### 5.7 History View

User can view:

* moisture over time
* temperature over time
* watering history
* event log

---

### 5.8 Image Timeline

* periodic plant images
* growth timeline
* visual history

---

### 5.9 Alerts

Trigger alerts when:

* moisture too low
* abnormal temperature/humidity
* device offline

---

### 5.10 Multi-Device Support

* one user → multiple devices
* one device → single owner

---

## 6. System Architecture

### Device Layer (Raspberry Pi)

* sensors:

  * moisture sensor (ADC)
  * DHT22
  * USB camera
* actuators:

  * pump (relay)
  * light (relay)

---

### Backend

* FastAPI
* REST API for device ingestion and user actions
* server-rendered dashboard routes

Environment variables:

* `PLANTLAB_SESSION_SECRET`
* `GOOGLE_CLIENT_ID`
* `GOOGLE_CLIENT_SECRET`

---

### Database

Start with:

* SQLite (MVP)

Later:

* PostgreSQL

---

### Frontend

* FastAPI + Jinja2 templates (V1)
* small vanilla JavaScript only where needed
* mobile-friendly web dashboard for iPhone Safari
* optional Add to Home Screen / PWA-style support
* React or native mobile app later, not V1

---

### Data Flow

Device → Backend API → Database
User → Web UI → Backend → Device
iPhone Safari → Mobile-friendly dashboard → Backend

---

## 7. Data Model

### User

* id
* email
* password_hash

### Device

* id
* user_id
* name
* location

### SensorReading

* id
* device_id
* timestamp
* moisture
* temperature
* humidity

### Event

* id
* device_id
* type (pump/light)
* timestamp

### Image

* id
* device_id
* path
* timestamp

---

## 8. API Requirements

### Device → Backend

POST /api/data

* send sensor data

POST /api/image

* upload image

---

### User → Backend

GET /api/devices
GET /api/device/{id}
POST /api/device/{id}/pump
POST /api/device/{id}/light

---

## 9. Non-Goals (V1)

* advanced AI diagnosis
* native mobile app / App Store app
* cloud scaling
* fertilizer automation
* complex permissions

---

## 10. Development Plan

### Phase 1

* local Pi system
* sensor + actuator control

### Phase 2

* backend API
* database

### Phase 3

* web dashboard

### Phase 4

* multi-user + multi-device

---

## 11. Key Principles

* keep system simple and modular
* prioritize reliability over complexity
* design for future scalability
* separate device logic and cloud logic

---

## 12. First Task for Codex

Implement:

1. FastAPI backend
2. SQLite database
3. user authentication
4. device model
5. sensor data ingestion API
6. basic dashboard

Keep code:

* modular
* readable
* production-ready structure
