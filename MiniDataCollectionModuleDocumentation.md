# MiniDataCollection Module Documentation

This module contains scripts for managing data collection in a Unity-based application, focusing on object interaction and gesture recognition. Below is a brief overview of the functionality of each script:

---

## MiniDataCollectionActionReceiver.cs
Handles the processing of gesture recognition data and determines the most probable object based on confidence scores.

### Key Features:
- **Gesture Recognition**:
  - Processes incoming data to calculate gesture probabilities and relative object positions.
  - Determines the most probable object based on the highest confidence score exceeding a threshold.
- **Data Handling**:
  - Updates the `DistanceHandGrabInteractor` with gesture probabilities and positions.
  - Logs errors for invalid data or out-of-bounds indices.

---

## MiniDataUdpSocket.cs
Manages UDP communication for receiving and sending data between the Unity application and external systems.

### Key Features:
- **Data Transmission**:
  - Receives gesture data via UDP and forwards it to `MiniDataCollectionActionReceiver`.
  - Sends data to a remote endpoint.
- **Error Handling**:
  - Handles socket exceptions and ensures proper cleanup on disable.

---

## MiniDataCollectionTrackData.cs
Tracks and manages objects in the scene, including their initialization and relative positions.

### Key Features:
- **Object Management**:
  - Loads and instantiates objects from prefabs.
  - Maintains a list of objects and their names for tracking.
- **Position Updates**:
  - Updates object states and positions relative to a hand's root position.

---

## MiniDataCollectionObjectTransformAssignment.cs
Assigns random transformations (rotation and position) to objects in the scene based on predefined data.

### Key Features:
- **Transformation Assignment**:
  - Loads transformation data from a JSON file.
  - Applies random rotations and positions to objects.
- **Debugging**:
  - Supports visualization of hand joints for debugging.

---

## MiniDataCollectionManager.cs
Manages the overall data collection process, including trial progression and logging.

### Key Features:
- **Trial Management**:
  - Tracks user interactions with objects and logs gesture data.
  - Handles trial progression and resets object positions.
- **Data Logging**:
  - Writes collected data (e.g., object states, gestures) to CSV files for analysis.