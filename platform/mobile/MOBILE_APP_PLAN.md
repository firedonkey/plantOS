# Mobile App Plan

Create the first version of the PlantLab mobile app using Expo React Native + TypeScript.

## Goal

Build an iOS-first mobile dashboard for the existing PlantLab backend. Keep the architecture reusable for Android later.

## Use

- Expo React Native
- TypeScript
- Expo Router if appropriate
- clean modern UI
- API layer separated from screens
- environment variable for backend API base URL

## Backend assumption

Assume the backend is a FastAPI server with REST endpoints.

If exact endpoints do not exist yet:

- create the frontend API wrapper with placeholder endpoint paths
- provide mock fallback data

## Core screens

1. Login screen
   - email/password placeholder login for now
   - store auth token locally
   - add clear TODO for Google OAuth or mobile auth later

2. Device list screen
   - fetch user devices
   - show device name, online or offline status, and latest sensor summary

3. Device dashboard screen
   - show:
     - temperature
     - humidity
     - soil moisture
     - water level
     - light status
     - pump status
     - latest camera image
     - last seen time
   - include refresh button

4. Manual control section
   - light on or off button
   - pump run button
   - capture image button

5. History screen
   - show simple sensor history list or basic chart placeholder
   - keep structure ready for real charts later

6. Settings screen
   - API URL display
   - logout button
   - app version placeholder

## Requirements

- strong TypeScript types for `Device`, `SensorReading`, `DeviceCommand`, and `LatestImage`
- loading and error states on all API screens
- mock data mode if API calls fail
- do not implement BLE provisioning yet
- do not implement push notifications yet
- add TODO notes that push notifications require an Expo development build or native capabilities, not just Expo Go
- make the UI feel like a premium smart home or plant lab product
- use simple cards, status chips, and readable spacing

## Acceptance criteria

- `npx expo start` runs
- the app opens in Expo Go on iPhone
- placeholder login works
- mock PlantLab device data is visible
- a device dashboard can be opened
- manual control buttons call the API wrapper or mock handler
- code stays clean enough for later BLE provisioning and Android support

## After implementation

Report:

- exactly what files were created or changed
- how to run it on iPhone
- which backend endpoints still need to be implemented next
