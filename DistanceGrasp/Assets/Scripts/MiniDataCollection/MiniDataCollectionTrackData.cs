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
    MiniDataUdpSocket socket;
    public TelemetryMessage currentMessage;
    private long packetId = 0;
    public HandVisual currentHand;

    // public GameObject CenterEyeAnchor;
    public Transform ObjectCenter;
    [HideInInspector]
    public GameObject[] Objects;
    public GameObject[] Prefabs;
    public string PrefabFolderName;
    public string TargetObjName;
    [HideInInspector]
    public string[] objNames;
    private readonly float updateInterval = 1.0f / 15.0f; // 15 fps
    private float nextUpdateTime = 0.0f;
    private static int objCount = 0;
    private Vector3 rootPosition;
    public GameObject[] allObjects;

    private int objectCount ; // Number of objects to place

    Vector3 startPosition = new Vector3(0, 0, 2);

    private void Awake()
    {
        // Prefabs = Resources.LoadAll<GameObject>(PrefabFolderName);

        // objectCount = Prefabs.Length;

        // Objects = new GameObject[objectCount];
        // objNames = new string[objectCount];

        // // Add the TargetObjName object first if it exists
        // List<GameObject> sortedPrefabs = new List<GameObject>();
        // foreach (var prefab in Prefabs)
        // {
        //     if (prefab.name == TargetObjName)
        //     {
        //         sortedPrefabs.Add(prefab);
        //         break;
        //     }
        // }

        // // Add the rest of the objects, excluding the TargetObjName object
        // foreach (var prefab in Prefabs)
        // {
        //     if (prefab.name != TargetObjName)
        //     {
        //         sortedPrefabs.Add(prefab);
        //     }
        // }

        // // Update Prefabs with the sorted list
        // Prefabs = sortedPrefabs.ToArray();

        // Vector3 startPosition = new Vector3(0, 0, 2); // Starting position for the first object
        // for (int i = 0; i < Prefabs.Length; i++)
        // {
        //     GameObject instance = Instantiate(Prefabs[i]);
        //     instance.transform.position = new Vector3(startPosition.x + i, startPosition.y, startPosition.z);
        //     instance.name = Prefabs[i].name;

        //     Objects[i] = instance;
        //     objNames[i] = instance.name;
        // }

        // Load all prefabs from the specified folder
        Prefabs = Resources.LoadAll<GameObject>(PrefabFolderName);

        // Shuffle the Prefabs array
        Prefabs = Prefabs.OrderBy(_ => UnityEngine.Random.value).ToArray();

        // Create a list to store sorted prefabs
        List<GameObject> sortedPrefabs = new List<GameObject>();

        // Add the TargetObjName object first if it exists
        GameObject targetPrefab = Prefabs.FirstOrDefault(prefab => prefab.name == TargetObjName);
        if (targetPrefab != null)
        {
            sortedPrefabs.Add(targetPrefab);
        }

        // Add the rest of the objects, excluding the TargetObjName object
        foreach (var prefab in Prefabs)
        {
            if (prefab.name != TargetObjName)
            {
                sortedPrefabs.Add(prefab);
            }
        }

        // Limit the number of prefabs to 16
        sortedPrefabs = sortedPrefabs.Take(16).ToList();

        // Update Prefabs with the sorted list
        Prefabs = sortedPrefabs.ToArray();

        objectCount = Prefabs.Length;

        Debug.Log($"Object Count: {objectCount}");

        Objects = new GameObject[objectCount];
        objNames = new string[objectCount];

        Vector3 startPosition = new Vector3(0, 0, 2); // Starting position for the first object
        for (int i = 0; i < Prefabs.Length; i++)
        {
            GameObject instance = Instantiate(Prefabs[i]);
            instance.transform.position = new Vector3(startPosition.x + i, startPosition.y, startPosition.z);
            instance.name = Prefabs[i].name;

            Objects[i] = instance;
            objNames[i] = instance.name;
        }


    }

    
    private void OnEnable()
    {
        socket = FindObjectOfType<MiniDataUdpSocket>();
        if (socket == null)
        {
            Debug.Log("No socket found");
        }
        // Subscribe to the JointUpdated event
        // HandVisual.JointUpdated += OnJointUpdated;

        /*objCount = ObjectSet.transform.childCount;
        for (int i = 0; i < objCount; i++)
        {
            Objects.Append(ObjectSet.transform.GetChild(i).gameObject);
        }*/

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

        socket.SendData(message.ToBytes());
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
