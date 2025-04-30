# RotationPreSet.cs

This script generates predefined rotation data for a set of prefabs and saves it as a JSON file. It is used to create a library of quaternion rotations for objects in the scene.

## Key Features:
- **Prefab Rotation Generation**:
  - Loads all prefabs from a specified folder (`PrefabFolderName`).
  - Iterates through a list of predefined Y-axis angles (`Y_Angles`) and applies rotations to each prefab.
  - Converts the resulting rotations to quaternions and stores them in a structured format.

- **JSON Serialization**:
  - Serializes the generated rotation data into a JSON file.
  - Saves the JSON file with a timestamped filename in the `Assets/Resources` directory.

- **Utility Functionality**:
  - Includes a `Quit` method to exit the application or stop play mode in the Unity Editor.

## Workflow:
1. **Start Method**:
   - Loads prefabs and calculates quaternion rotations for each prefab based on the specified Y-axis angles.
   - Stores the rotation data in a dictionary (`jsonData`) with the prefab name as the key.
   - Serializes the dictionary into a JSON file and saves it to disk.

2. **Update Method**:
   - Calls the `Quit` method to terminate the application or stop play mode.

## Example Output:
The JSON file contains rotation data for each prefab in the following format:
```json
{
  "PrefabName": {
    "object_rotation": [
      [0.0, 0.0, 0.0, 1.0],
      [0.0, 0.707107, 0.0, 0.707107],
      ...
    ]
  }
}