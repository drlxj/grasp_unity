# Log File Documentation

This document aims to help developers understand the structure and content of the log files (`GestureData`, `GraspingData`, `ObjectData`) generated in the project. These log files record data related to user grasping actions, gesture scores, and object information in a virtual reality environment.

---

## 1. `GestureData` Log File

### File Path
../DistanceGrasp/Assets/LogData/GestureData_{start_timestamp}_{SessionType}.csv


### File Structure
Each line represents a record of a gesture action, with fields separated by commas`,`. The fields are as follows:

1. **Flag**: Indicates the correctness of the gesture.
   - `1`: Correct grasp.
   - `0`: Wrong grasp.
   - `2`: Left-hand pinch action.

2. **TargetObjectName**: The name of the current target object.

3. **RootRotation**: The rotation of the root node, formatted as `x|y|z|w`.

4. **RootPosition**: The position of the root node, formatted as `x|y|z`.

5. **JointPositions**: The positions of hand joints, formatted as `x|y|z`, with multiple joints separated by `/`.

6. **AllScores**: Gesture scoring information, containing the following subfields:
   - **Name**: The name of the target object.
   - **GestureScore**: The gesture score.
   - **PositionScore**: The position score.
   - **GestureWeight**: The gesture weight.
   - **FinalScore**: The final score.
   
   Multiple score entries are separated by `/`.

### Example
2,waterbottle,0.4395817|-0.6966669|-0.3264974|0.4634897,-0.1245807|-0.4953631|0.9272071,-0.02697116|-0.04012758|-0.01396227/-0.03894389|-0.06604475|-0.03059852/-0.04191834|-0.09880441|-0.04046988/-0.04060221|-0.1225408|-0.04827863/-0.03796357|-0.09112263|0.02003908/-0.03639448|-0.1295297|0.02289748/-0.03002787|-0.1494809|0.009802341/-0.02158952|-0.1619188|-0.00728035/-0.01871055|-0.08990759|0.03201693/-0.01409286|-0.1330218|0.03682327/-0.006369352|-0.1519417|0.0176844/-0.0003843307|-0.1580742|-0.006226361/0.002037942|-0.0859881|0.03295416/0.006618202|-0.1243468|0.04180163/0.01131779|-0.145645|0.02587545/0.01348275|-0.1556036|0.003290534/0.02298588|-0.07970726|0.0291245/0.02708793|-0.1099376|0.03576106/0.02965528|-0.1270365|0.02448541/0.02793562|-0.1388615|0.005639195,waterbottle|0.4561|0.9262|0.5|0.184/eyeglasses|0.666|0.7408|0.5|0.2149/toothpaste|0.9015|0.9484|0.5|0.3725/toruslarge|0.7253|0.7235|0.5|0.2286

---

## 2. `GraspingData` Log File

### File Path
../DistanceGrasp/Assets/LogData/GraspingData_{start_timestamp}_{SessionType}.csv

### File Structure
Each line represents a record of a grasping action, with fields separated by commas. The fields are as follows:

1. **TargetObjectName**: The name of the current target object.

2. **WrongGraspCount**: The number of wrong grasping attempts.

3. **GraspingStartTime**: The start time of the grasping action, formatted as `yyyy-MM-dd HH:mm:ss.fff`.

4. **GraspingEndTime**: The end time of the grasping action, formatted as `yyyy-MM-dd HH:mm:ss.fff`.

### Example
waterbottle,0,2025-03-20 10:16:02.842,2025-03-20 10:16:11.914

---

## 3. `ObjectData` Log File

### File Path
../DistanceGrasp/Assets/LogData/ObjectData_{start_timestamp}_{SessionType}.csv


### File Structure
Each line represents the initial state of an object, with fields separated by commas. The fields are as follows:

1. **ObjectType**: The type of the object, represented as an integer.

2. **Position**: The initial position of the object, formatted as `x|y|z`.

3. **Rotation**: The initial rotation of the object, formatted as `x|y|z|w`.

### Example
48,0.1|-2|0.1,0.4544623|0.7051379|-0.543018|-0.03709447


---

## 4. When Log Files Are Generated

- **GestureData**: Generated when the user performs a gesture action (e.g., grasping, left hand pinching). The system records gesture scores and related information.
- **GraspingData**: Generated when the user successfully grasps an object. The system records the time, target object, and number of wrong attempts.
- **ObjectData**: Generated during scene initialization. The system records the initial state of all objects.

---

## 5. When Log Files Are Output to Disk

- **Log File Writing Strategy**: All log files are written to disk when the program quits. This approach avoids potential performance lag caused by frequent output operations during runtime.


---

## 5. Use Cases for Log Files

- **Debugging and Analysis**: Developers can analyze user behavior patterns, gesture accuracy, and object initial states using these log files.
- **Performance Optimization**: By analyzing the timestamps of grasping actions, developers can optimize system responsiveness and user experience.
- **Data Visualization**: These log files can be used to generate visual reports, helping the team understand user interaction details.

---

## 6. Notes

- **Timestamps**: All timestamps are in local time, formatted as `yyyy-MM-dd HH:mm:ss.fff`.
- **Field Separator**: Log files use commas `,` as field separators. Ensure proper handling when parsing.
- **Log Path**: Log files are saved in the `../DistanceGrasp/Assets/LogData/` directory, with filenames containing timestamps and session types.

---