using System;
using System.IO;
using Oculus.Interaction;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UIElements;
using System.Linq;

[DefaultExecutionOrder(50)]
public class MiniDataCollectionTrackData : MonoBehaviour
{
    public HandVisual currentHand;

    // public GameObject CenterEyeAnchor;
    public float heightOffset = 0.0f; // Offset from the eyes position
    public Transform ObjectCenter;
    [HideInInspector]
    public GameObject[] Objects;
    public GameObject[] Prefabs;

    public string PrefabFolderName;
    [HideInInspector]
    public string[] objNames;
    private readonly float updateInterval = 1.0f / 15.0f; // 15 fps
    private float nextUpdateTime = 0.0f;
    private static int objCount = 0;
    private Vector3 rootPosition;

    private long packetId = 0;

    public GameObject[] allObjects;
    public float densityFactor = 1.0f; // 1.0 = Normal, <1.0 = Spread out, >1.0 = More compact
    public Vector3 boxSize = new Vector3(1f, 1f, 1f); // Bounding box defining placement area
    private int objectCount ; // Number of objects to place
    public LayerMask objectLayer; // Set a layer for objects to check collisions
    
    public float depth = -5f; // CHANGE THIS TO CHANGE THE DEPTH OF THE OBJECTS
    public TelemetryMessage currentMessage;
    System.Random rng = new System.Random();

    private void Awake()
    {
        Prefabs = Resources.LoadAll<GameObject>(PrefabFolderName);

        objectCount = Prefabs.Length;

        Objects = new GameObject[objectCount];
        objNames = new string[objectCount];

        Vector3 startPos = transform.position;
        int attempts = 0;

        for (int i = 0; i < objectCount; i++)
        {
            GameObject instance = Instantiate(Prefabs[i % Prefabs.Length]);
            instance.name = Prefabs[i % Prefabs.Length].name;
            bool placed = false;

            while (!placed && attempts < 100) // Prevent infinite loops
            {
                Vector3 randomPos = new Vector3(
                    startPos.x + UnityEngine.Random.Range(-boxSize.x / 2, boxSize.x / 2) * densityFactor,
                    startPos.y + UnityEngine.Random.Range(-boxSize.y / 2, boxSize.y / 2) + heightOffset,
                    startPos.z + UnityEngine.Random.Range(-boxSize.z / 2, boxSize.z / 2) * densityFactor + depth
                );

                Collider[] colliders = Physics.OverlapBox(randomPos, instance.transform.localScale / 2, Quaternion.identity, objectLayer);

                if (colliders.Length == 0) // Ensure no overlap
                {
                    instance.transform.position = randomPos;
                    placed = true;
                }
                attempts++;
            }

            Objects[i] = instance;
            objNames[i] = instance.name;
        }

        Debug.Log($"Placed {objectCount} objects within a box of size {boxSize}.");

        string objLog = $"Initial {objCount} objects: ";
        for (int i = 0; i < objCount; i++)
        {
            objLog += Objects[i].name + "  ";
            objNames[i] = Objects[i].name;

        }
        Debug.Log(objLog);

    }

    
    private void OnDisable()
    {
        // Unsubscribe from the JointUpdated event
        // HandVisual.JointUpdated -= OnJointUpdated;
    }


    void Start()
    {
        
        // if (Objects == null)
        // {
        //     Debug.LogError("No Objs Exist");
        // }

        // objCount = Objects.Count();
        // objNames = new string[objCount];

        // string objLog = $"Initial {objCount} objects: ";
        // for (int i = 0; i < objCount; i++)
        // {
        //     objLog += Objects[i].name + "  ";
        //     objNames[i] = Objects[i].name;

        // }
        // Debug.Log(objLog);
    }

    void Update()
    {
        rootPosition = currentHand.Joints[0].position;
        
        // Debug.LogError($"rootPosition {rootPosition}");
        if (Time.time >= nextUpdateTime)
        {
            nextUpdateTime = Time.time + updateInterval;
            OnJointUpdated(out TelemetryMessage message);
            currentMessage = message;
        }
    }

    public struct TransformData
    {
        public Vector3 position;
        public Quaternion rotation;
    }

    public Vector3 GetCurrentRootPosition()
    {
        return rootPosition;
    }

    private void OnJointUpdated(out TelemetryMessage message)
    {
        message = new TelemetryMessage();
        if (currentHand == null)
        {
            Debug.Log("Right Hand not exists.");
            return;
        }

        message.packetIdx = packetId;
        packetId++;

        IList<Transform> joints = currentHand.Joints;
        if (joints == null || joints.Count == 0)
        {
            Debug.LogError("Transform list is empty or null.");
            return;
        }
        Transform root = joints[0];

        // Send wrist transform
        message.rootPosition = root.position;
        message.rootRotation = root.rotation;

        // Compute the joints' Relative Transform
        List<int> indexMapping = new List<int>
        {
            3, 4, 5, 19, // Thumb1-3, ThumbTip
            6, 7, 8, 20, // Index
            9, 10, 11, 21, //Middle
            12, 13, 14, 22, //Ring
            16, 17, 18, 23 //Pinky
        };

        for (int i = 0; i < TelemetryMessage.JOINT_COUNT; i++)
        {
            Transform t = joints[indexMapping[i]];

            // Send joint position relative to wrist
            Vector3 relativePosGlobal = t.position - root.position;

            // Convert the coordinates
            message.jointPositions[i] = relativePosGlobal;
        }

        // Debug.Log($"message: {message}, root: {root}");

        message.objectStates = AddObjectsToTelemetryMessage(root, out string objInfo);
        // LogObjData(objInfo);

    }

    private void LogData(string dataType, string[] pos)
    {
        string folderPath = "../DistanceGrasp/Assets/LogData";
        string csvFileName = dataType + ".csv";
        string filePath = Path.Combine(folderPath, csvFileName);

        if (!Directory.Exists(folderPath))
        {
            Directory.CreateDirectory(folderPath);
            Debug.Log(folderPath + " folder Created.");
        }


        if (!File.Exists(filePath))
        {
            string[] columnNames = {
                //"RootX", "RootY", "RootZ",
                "Thumb1X", "Thumb1Y", "Thumb1Z",
                "Thumb2X", "Thumb2Y", "Thumb2Z",
                "Thumb3X", "Thumb3Y", "Thumb3Z",
                "ThumbTipX", "ThumbTipY", "ThumbTipZ",
                "Index1X", "Index1Y", "Index1Z",
                "Index2X", "Index2Y", "Index2Z",
                "Index3X", "Index3Y", "Index3Z",
                "IndexTipX", "IndexTipY", "IndexTipZ",
                "Middle1X", "Middle1Y", "Middle1Z",
                "Middle2X", "Middle2Y", "Middle2Z",
                "Middle3X", "Middle3Y", "Middle3Z",
                "MiddleTipX", "MiddleTipY", "MiddleTipZ",
                "Ring1X", "Ring1Y", "Ring1Z",
                "Ring2X", "Ring2Y", "Ring2Z",
                "Ring3X", "Ring3Y", "Ring3Z",
                "RingTipX", "RingTipY", "RingTipZ",
                "Pinky1X", "Pinky1Y", "Pinky1Z",
                "Pinky2X", "Pinky2Y", "Pinky2Z",
                "Pinky3X", "Pinky3Y", "Pinky3Z",
                "PinkyTipX", "PinkyTipY", "PinkyTipZ"
            };

            using StreamWriter writer = File.CreateText(filePath);
            writer.WriteLine(string.Join(",", columnNames));
            writer.WriteLine(string.Join(",", pos));
            //Debug.Log(dataType + " data created.");
        } else {
            using StreamWriter writer = new(filePath, append: true);
            writer.WriteLine(string.Join(",", pos));
            //Debug.Log(dataType + " data appended.");
        }
    }

    private string[] GetPos(TelemetryMessage msg)
    {
        List<string> result = new List<string>();
        foreach (var pos in msg.jointPositions)
        {
            string positionString = $"{pos.x},{pos.y},{pos.z}";
            result.Add(positionString);
        }
        return result.ToArray();
    }


    private ObjectState[] AddObjectsToTelemetryMessage(Transform root, out string objInfo)
    {
        objInfo = string.Empty;

        ObjectState[] objStates = new ObjectState[Objects.Length];
        for (int i = 0; i < objStates.Length; i++)
        {
            objStates[i] = new ObjectState();

            Vector3 relativePosGlobal = Objects[i].transform.position - root.position;
            objStates[i].position = relativePosGlobal;
            objStates[i].orientation = Objects[i].transform.rotation;
//            objStates[i].orientation = Objects[i].transform.eulerAngles;
//            Debug.Log($"Object {i} orientation+++: {objStates[i].orientation}");
            //objStates[i].objectType = Objects[i].GetComponent<ObjectProperties>().ObjectType;
            string objectTypeStr = Objects[i].name.ToUpper();
            objectTypeStr = objectTypeStr.Replace("_", "");
            objStates[i].objectType = (ObjectType)Enum.Parse(typeof(ObjectType), objectTypeStr);

            //Debug.Log($"Object at index {i}: {objStates[i].objectType}");

            //objStates[i].objIdx = Objects[i].GetComponent<ObjectProperties>().ObjIdx;
            //Debug.Log($"objIdx at index {i}: {objStates[i].objIdx}");
        }
        return objStates;
    }

    private void LogObjData(string info)
    {
        string objFilePath = "../DistanceGrasp/Assets/LogData/objData.csv";

        if (!File.Exists(objFilePath))
        {
            // String[] Columns =
            // {
            //     "ObjIdx", "ObjType", "posX", "posY", "posZ",
            //     "oriX", "oriY", "oriZ", "oriW"
            // };
            String[] Columns =
            {
                "ObjIdx", "ObjType", "posX", "posY", "posZ",
                "oriX", "oriY", "oriZ"
            };
            using StreamWriter writer = File.CreateText(objFilePath);
            writer.WriteLine(string.Join(",", Columns));
            writer.WriteLine(info);
        } else
        {
            using StreamWriter writer = new(objFilePath, append: true);
            writer.WriteLine(info);
        }
    }
}
