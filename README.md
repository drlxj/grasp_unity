# Grasping Unity Project

This project is designed to help users, even those with no prior experience, get started with using this Unity-based project. Follow the steps below to set up your environment and run the project.

## Prerequisites

Before you begin, ensure you have the following installed on your system:

1. **Unity Editor**: Version `2022.3.17f1`.  
    You can download it from the [Unity Hub](https://unity.com/download).
    Download specific version from(https://unity.com/releases/editor/whats-new/2022.3.17).

2. **Python**: Version `3.9.21`.  

## Setup Instructions

1. **Install Unity**:
    - Open Unity Hub.
    - Add the Unity version `2022.3.17f1` if not already installed.
    - Set up the project in Unity by opening the [DistanceGrasp] folder.

2. **Install Python**:
    - Ensure Python `3.9.21` is installed.

3. **Install Required Python Packages**:
    - Navigate to the [python] directory.
    - Install dependencies using `pip`:
      ```bash
      pip install -r requirements.txt
      ```

4. **Set Up Meta Quest 2**:
    - Use a USB cable to connect your Meta Quest 2 headset to your computer.

4. **Install Anaconda3**:
    - Download and install [Anaconda3](https://www.anaconda.com/) if it is not already installed on your system.

3. **Prepare Anaconda3 Environment**:
    - Install [Anaconda3] if not already installed.
    - Create a new environment for the project:
      ```bash
      conda env create -f environment.yml
      ```
    - Activate the environment:
      ```bash
      conda activate grab
      ```

## Project Structure

This project is organized into three main components:

1. **DistanceGrasp**:  
   This is the Unity project folder, which contains all the necessary files to run the VR environment. You can open this folder in the Unity Editor to start the simulation or application.

2. **model**:  
   This folder contains Python scripts and dependencies required to run the inference models. Make sure to install the required Python packages as outlined in the setup instructions.

3. **data_process**:  
   This folder is used for generating and processing statistical data after experiments. It includes scripts and tools for post-experiment data analysis.
  

## Environment Preparing

1. **Prepare Anaconda3 Environment for model**:
    - Install [Anaconda3] if not already installed.
    - Create a new environment for the project:
      ```bash
      conda env create -f environment.yml
      ```
    - Activate the environment:
      ```bash
      conda activate grab
      ```

2. **Configure VR Environment**:
    - Open the [DistanceGrasp] project using Unity Hub.
    - Use a USB cable to connect your Meta Quest 2 headset to your computer.
    - Follow the steps outlined in [this video](https://www.youtube.com/watch?v=tGZgJ5XtOXo) from **1:00 to 5:16** to configure the VR environment in Unity.

## How to Run the Project

Follow these steps to run the project:

1. **Run the Python Model**:
    - Navigate to the `model` folder.
    - Activate the Anaconda environment:
      ```bash
      conda activate grab
      ```
    - Locate the `app.py` file and run it.

2. **Open the Unity Project**:
    - Open the [DistanceGrasp](http://_vscodecontentref_/0) project using Unity Hub.
    - In the Unity Editor, navigate to the `Assets` folder and open the `Scenes` folder.
    - Select the `Simple_Test_2` scene.
    - Click the **Play** button at the top center of the Unity Editor to start the simulation.

3. **Conduct the Experiment**:
    - Wear the Meta Quest 2 headset.
    - Interact with the VR environment to perform the experiment.

4. **Perform Data Analysis**:
    - Navigate to the `DistanceGrasp` folder, then go to the `LogData` folder.
    - Locate the folder named with the experiment's start timestamp (e.g., `20250407_170650.731`). This folder contains the raw data for the experiment.
    - Copy the name of this folder.
    - Navigate to the `data_process` folder and open the `data_process.py` file.
    - Modify line 6 of the code:
      ```python
      INPUT_EXPERIMENT_TIMESTAMP = "your_experiment_timestamp"
      ```
      Replace `"your_experiment_timestamp"` with the name of the folder you copied earlier.
    - Run the [data_process.py](http://_vscodecontentref_/0) script.
    - After the script finishes, go back to the `LogData` folder and open the experiment's timestamp folder.
    - Inside the `processed_data` folder, you will find a CSV file containing the analysis results for the experiment.

## Modify Experiment Configuration

To customize the experiment settings, follow these steps:

1. **Open the Scene**:
    - Open the `Simple_Test_2` scene in the Unity Editor.

2. **Access the DataManager Object**:
    - In the Unity Editor, navigate to the **Hierarchy** panel (located in the top-left corner).
    - Select the `DataManager` object.

3. **Modify Configurable Options**:
    - In the **Inspector** panel (on the right side of the Unity Editor), you will see several configurable options:

      - **TrackData Component - Prefab Folder Name**:
        - This determines the types of objects that appear in the scene.
        - Available options:
          - `Prefab_goodcase`
          - `Prefab_goodcase_2`
          - `Prefab_badcase`
          - `Prefab_badcase_2`
        - Changing this value will alter the types of objects that appear in the scene.

      - **SimpleTestManager - Time Limit**:
        - This sets the time limit for grasping each object.
        - If the time limit is exceeded, the scene will automatically switch to the next object.
        - You can set this to any positive integer value.

      - **SimpleTestManager - Session Types**:
        - This defines the session types for the experiment.
        - You can use any combination of the following uppercase letters:
          - `G`: Gesture-only method.
          - `O`: Native pointing method.
          - `P`: Optimized pointing method.
          - `C`: Combination method (Gesture + Optimized Pointing).
        - Example: `GCOP` or `GP`.
        - After clicking the **Play** button, the experiment will proceed in the order defined by the session types. The session types are executed sequentially based on the alphabetical order of the letters provided.

4. **Save Changes**:
    - After making the desired changes, save the scene to apply the new configuration.

## Important Note

Before starting the experiment by clicking the **Play** button in Unity, make sure that the `app.py` file in the `model` folder has been restarted. This ensures that the Python backend is properly initialized and ready to handle the experiment data.