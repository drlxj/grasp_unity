using Assets.Oculus.VR.Editor;
using Oculus.Interaction.DebugTree;
using Oculus.Interaction.HandGrab;
using System;
using System.IO;
using System.Collections.Generic;
using System.Collections;
using TMPro;
using UnityEngine;
using System.Linq;
using UnityEngine.UI;
using Oculus.Interaction;

[DefaultExecutionOrder(100)]
public class MiniDataCollectionManager : MonoBehaviour
{
    [HideInInspector]
    public GameObject[] Objects;
    private int objectsLength;
    public Material glowMaterial;
    public GameObject progressBarPrefab;
    public GameObject posProgressBarPrefab;
    public GameObject gesProgressBarPrefab;
    private List<Slider> progressBars = new List<Slider>();
    private List<Slider> posProgressBars = new List<Slider>();
    private List<Slider> gesProgressBars = new List<Slider>();
    public Material originalMaterial;

    public string TestUserId;

    [Tooltip("For Each Character's meaning, check line 13-16 in Session.cs")]
    public string SessionTypes = "G";
    public GameObject CounterUI;

    private TextMeshProUGUI CounterText;
    [HideInInspector]
    private int TrialIndex;
    private bool Occlusion;
    private Dictionary<GameObject, (Vector3 position, Quaternion rotation)> initialTransforms = new Dictionary<GameObject, (Vector3, Quaternion)>();
    private string start_timestamp;

    private System.DateTime GraspingStartTime;
    private System.DateTime GraspingLimitedTime;
    private System.DateTime GraspingEndTime;
    private List<string> ObjectLogObjectInfo = new List<string>();
    private List<string> gestureLogAllScores = new List<string>();
    private bool ObjectLogHasCollected = false;
    public AudioSource audioSource;
    private bool isCountingDown = false;
    public OVRHand leftHand;
    private bool indexFingerIsPinching = false;
    private bool midFingerIsPinching = false;
    private bool ringFingerIsPinching = false;
    private bool isGrasping = false;


    private string TargetObjectName;

    private void Awake()
    {
        char SessionType = SessionTypes[0];

        PlayerPrefs.SetString("SessionType", SessionType.ToString());
        PlayerPrefs.Save();
        
        start_timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss.fff");

        CounterText = CounterUI.GetComponentInChildren<TextMeshProUGUI>();

    }

// TODO: the object doesn't return to the original place -> change control scene with less objects
// TODO: check out-of reach grasping with long distance 
    private void Start()
    {        
        Objects = this.GetComponent<MiniDataCollectionTrackData>().Objects;
        objectsLength = Objects.Length;
        TargetObjectName = this.GetComponent<MiniDataCollectionTrackData>().TargetObjName;

        foreach (var obj in Objects)
        {
            if (obj == null) continue;

            initialTransforms[obj] = (obj.transform.position, obj.transform.rotation);
        }

        TrialIndex = 0;

    }

    void Update()
    {   
        tryCollectObjectLog();

        if (objectsLength == TrialIndex )
        {

            writeObjectLog();
            // writeRotationSeqLog();
            writeGestureLog();
            Quit();
        }

        if (IsLeftHandIndexPinch() && !indexFingerIsPinching)
        {
            indexFingerIsPinching = true;
            if (isGrasping == false)
            {
                LogGesture(1);
                MoveObjectToGraspingPosition();
                isGrasping = true;
            } else {
                AppendWristPos();
                MoveObject();
            }
        }
        else if (!IsLeftHandIndexPinch())
        {  
            indexFingerIsPinching = false;
        }

        if (isGrasping == false){
            if (IsLeftHandMidPinch() && !midFingerIsPinching)
            {
                midFingerIsPinching = true;
                LogGesture(0);
                MoveObject();
            }
            else if (!IsLeftHandMidPinch())
            {
                midFingerIsPinching = false;
            }

            if (IsLeftHandRingPinch() && !ringFingerIsPinching)
            {
                ringFingerIsPinching = true;
                LogGesture(2);
                MoveObject();
            }
            else if (!IsLeftHandRingPinch())
            {
                ringFingerIsPinching = false;
            }
        }
        
    }

    private void writeObjectLog()
    {
        string objectInfoFolderPath = $"../collected_data/{TestUserId}/{TargetObjectName}/{start_timestamp}/meta_data/";
        if (!Directory.Exists(objectInfoFolderPath))
        {
            Directory.CreateDirectory(objectInfoFolderPath);
        }
        string objectInfoLogPath = objectInfoFolderPath + "ObjectInfoData.csv";
        using (StreamWriter writer = new StreamWriter(objectInfoLogPath, true))
        {
            foreach (var line in ObjectLogObjectInfo)
            {
                writer.WriteLine(line); 
            }
        }
    }

    private void writeRotationSeqLog()
    {
        List<Tuple<string, string>> RotationSeqNameObjectList = new List<Tuple<string, string>>();

        RotationSeqNameObjectList = this.GetComponent<MiniDataCollectionObjectTransformAssignment>().RotationSeqNameObjectList;
        string RotationSeqFolderPath = $"../collected_data/{TestUserId}/{TargetObjectName}/{start_timestamp}/meta_data/";
        if (!Directory.Exists(RotationSeqFolderPath))
        {
            Directory.CreateDirectory(RotationSeqFolderPath);
        }
        string RotationSeqLogPath = RotationSeqFolderPath + "RotationSeqData.csv";
        using (StreamWriter writer = new StreamWriter(RotationSeqLogPath, true))
        {
            foreach (var line in RotationSeqNameObjectList)
            {
                writer.WriteLine($"{line.Item1},{line.Item2}"); 
            }
        }
    }

    private void writeGestureLog()
    {   

        string GestureFolderPath = $"../collected_data/{TestUserId}/{TargetObjectName}/{start_timestamp}/";
        if (!Directory.Exists(GestureFolderPath))
        {
            Directory.CreateDirectory(GestureFolderPath);
        }
        
        string GestureLogPath = GestureFolderPath + "GestureData.csv";
        using (StreamWriter writer = new StreamWriter(GestureLogPath, true))
        {
            foreach (var entry in gestureLogAllScores)
            {
                writer.WriteLine(entry); 
            }
        }
    }

    private void LogGesture(int correctGestureFlag)
    {   
        // correctGestureFlag: 
        // 1: can grasp
        // 0: cannot grasp
        // 2: not sure
        string flag = correctGestureFlag.ToString();

        TelemetryMessage currentMessage = this.GetComponent<MiniDataCollectionTrackData>().currentMessage;

        Quaternion rootRotation = currentMessage.rootRotation;
        Vector3 rootPosition = currentMessage.rootPosition;
        Vector3[] jointPositions = currentMessage.jointPositions;
  
        List<string> jointStrings = new List<string>();

        string rootRotationInfo = $"{rootRotation.x}|{rootRotation.y}|{rootRotation.z}|{rootRotation.w}";
        string rootPositionInfo = $"{rootPosition.x}|{rootPosition.y}|{rootPosition.z}";

        foreach (var joint in jointPositions)
        {
            string jointInfo = $"{joint.x}|{joint.y}|{joint.z}";
            jointStrings.Add(jointInfo);
        }

        string allJoints = string.Join("/", jointStrings);

        string graspingObjectName = Objects[TrialIndex].name;

        string combinedInfo = $"{flag},{graspingObjectName},{rootRotationInfo},{rootPositionInfo},{allJoints}";
        gestureLogAllScores.Add(combinedInfo);
    }

    private bool IsLeftHandIndexPinch()
    {
        return leftHand.GetFingerIsPinching(OVRHand.HandFinger.Index);
    }

    private bool IsLeftHandMidPinch()
    {
        return leftHand.GetFingerIsPinching(OVRHand.HandFinger.Middle);
    }

    private bool IsLeftHandRingPinch()
    {
        return leftHand.GetFingerIsPinching(OVRHand.HandFinger.Ring);
    }


    private void MoveObject()
    {
        TrialIndex++;
        foreach (var obj in initialTransforms.Keys)
        {   

            Debug.Log($"Object name: {obj.name}, TargetObjectName: {TargetObjectName}");
            if (obj.name == TargetObjectName)
            {

                obj.transform.position = new Vector3(
                    initialTransforms[obj].position.x,
                    initialTransforms[obj].position.y - 0.5f,
                    initialTransforms[obj].position.z
                );
                obj.transform.rotation = initialTransforms[obj].rotation;
            } else {
                obj.transform.position = new Vector3(
                    initialTransforms[obj].position.x - 1.0f * (TrialIndex),
                    initialTransforms[obj].position.y,
                    initialTransforms[obj].position.z
                );
                obj.transform.rotation = initialTransforms[obj].rotation;
            }
        }
    }

    private void AppendWristPos()
    {   
        TelemetryMessage currentMessage = this.GetComponent<MiniDataCollectionTrackData>().currentMessage;
        Vector3 rootPosition = currentMessage.rootPosition;
        string wristPositionInfo = $"{rootPosition.x}|{rootPosition.y}|{rootPosition.z}";
        gestureLogAllScores[gestureLogAllScores.Count - 1] += $",{wristPositionInfo}";
        isGrasping = false;
    }

    private void MoveObjectToGraspingPosition()
    {
        foreach (var obj in initialTransforms.Keys)
        {
            if (obj.name == Objects[TrialIndex].name)
            {
                obj.transform.position = new Vector3(
                    0.0f,
                    0.0f,
                    0.5f
                );
                obj.transform.rotation = initialTransforms[obj].rotation;
            }
        }
    }

    private void tryCollectObjectLog()
    {
        if (!ObjectLogHasCollected)
        {
            try
            {
                TelemetryMessage firstMessage = this.GetComponent<MiniDataCollectionTrackData>().currentMessage;
                // Debug.Log("objectStates length: " + currentMessage.objectStates.Length);
                for (int i = 0; i < firstMessage.objectStates.Length; i++)
                {
                    ObjectState objectState = firstMessage.objectStates[i];
                    ObjectType objectType = objectState.objectType;
                    int objectTypeValue = (int)objectType;
                    string objectTypeString = objectTypeValue.ToString();

                    Quaternion rotation = objectState.orientation;
                    string rotationString = $"{rotation.x}|{rotation.y}|{rotation.z}|{rotation.w}";

                    Vector3 position = objectState.position;
                    string positionString = $"{position.x}|{position.y}|{position.z}";

                    string[] objectInfoData = { objectTypeString, positionString, rotationString };
                    ObjectLogObjectInfo.Add(string.Join(",", objectInfoData));
                }
                Debug.Log("private void tryCollectObjectLog()");
                ObjectLogHasCollected = true;
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"An error occurred while processing object states: {ex.Message}");
            }
        }
    }

    public static void Quit()
    {   
        #if UNITY_EDITOR
        UnityEditor.EditorApplication.isPlaying = false;
        #else
        Application.Quit();
        #endif
    }

}

