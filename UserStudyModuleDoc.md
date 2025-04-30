# DistanceGrasp Module Documentation

This module contains scripts for managing object interaction, gesture recognition, and data collection in a Unity-based application. Below is an overview of the functionality of each script:

---

## **SimpleTestManager.cs**
Manages the overall testing process, including trial progression, gesture logging, and user feedback.

### Key Features:
- **Trial Management**:
  - Tracks user interactions with objects and logs gesture data (e.g., correct, incorrect, or timeout).
  - Handles trial progression and resets object positions.
- **User Feedback**:
  - Displays countdown timers and progress bars for gesture scores.
  - Highlights target objects for better user guidance.
- **Data Logging**:
  - Writes collected data (e.g., object states, gestures) to CSV files for analysis.

---

## **ActionReceiver.cs**
Processes gesture recognition data and determines the most probable object based on confidence scores.

### Key Features:
- **Gesture Recognition**:
  - Processes incoming data to calculate gesture probabilities and relative object positions.
  - Updates the `DistanceHandGrabInteractor` with gesture probabilities and positions.
- **Error Handling**:
  - Logs errors for invalid data or out-of-bounds indices.

---

## **UdpSocket.cs**
Handles UDP communication for receiving and sending data between the Unity application and external systems.

### Key Features:
- **Data Transmission**:
  - Receives gesture data via UDP and forwards it to `ActionReceiver`.
  - Sends data to a remote endpoint.
- **Error Handling**:
  - Handles socket exceptions and ensures proper cleanup on disable.

---

## **TrackData.cs**
Tracks and manages objects in the scene, including their initialization and relative positions.

### Key Features:
- **Object Management**:
  - Loads and instantiates objects from prefabs.
  - Maintains a list of objects and their names for tracking.
- **Position Updates**:
  - Updates object states and positions relative to a hand's root position.
- **Data Transmission**:
  - Sends telemetry data (e.g., joint positions, object states) via UDP.

---

## **ObjectTransformAssignment.cs**
Assigns random transformations (rotation and position) to objects in the scene based on predefined data.

### Key Features:
- **Transformation Assignment**:
  - Loads transformation data from a JSON file.
  - Applies random rotations and positions to objects.
- **Debugging**:
  - Supports visualization of hand joints for debugging.


---

## **Messages.cs**
Defines data structures for telemetry and command messages used in communication.

### Key Features:
- **TelemetryMessage**:
  - Encodes joint positions, object states, and root transformations into byte arrays for transmission.
- **CommandMessage**:
  - Decodes received data into object positions, confidence scores, and object types.
