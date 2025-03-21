﻿using System;
using System.IO;
using Oculus.Interaction;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UIElements;
using System.Linq;

[DefaultExecutionOrder(50)]
public class TrackData : MonoBehaviour
{
    UdpSocket socket;
    public HandVisual currentHand;
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
    public int gridSize = 2; // CHANGE
    public float spacing = 0.1f; // CHANGE
    public float depth = -5f; // CHANGE

    public TelemetryMessage currentMessage;

    System.Random rng = new System.Random();

    void FisherYatesShuffle(GameObject[] array)
    {
        for (int i = array.Length - 1; i > 0; i--)
        {
            int j = rng.Next(i + 1);

            GameObject temp = array[i];
            array[i] = array[j];
            array[j] = temp;
        }
    }

    public void FisherYatesShuffleInt(List<int> list)
    {
        int[] array = list.ToArray();

        for (int i = array.Length - 1; i > 0; i--)
        {
            int j = rng.Next(i + 1);
            int temp = array[i];
            array[i] = array[j];
            array[j] = temp;
        }

        for (int i = 0; i < array.Length; i++)
        {
            list[i] = array[i];
        }
    }

    private void Awake()
    {
        Prefabs = Resources.LoadAll<GameObject>(PrefabFolderName);
        FisherYatesShuffle(Prefabs);

        Objects = new GameObject[gridSize * gridSize]; 

        Vector3 startPos = transform.position;
        float offset = (gridSize - 1) * spacing * 0.5f;

        //for (int row = 0; row < gridSize; row++)
        //{
        //    for (int col = 0; col < gridSize; col++)
        //    {
        //        distanceMap[row, col] = 2f;
        //    }
        //}

        List<int> positionIndices = Enumerable.Range(0, gridSize * gridSize).ToList();
        FisherYatesShuffleInt(positionIndices);

        // Debug.Log("Shuffled positionIndices: " + string.Join(", ", positionIndices));

        for (int i = 0; i < gridSize * gridSize; i++)
        {
            int randomIndex = positionIndices[i]; 

            GameObject instance = Instantiate(Prefabs[i]); 
            instance.name = Prefabs[i].name;

            int randRow = randomIndex / gridSize;
            int randCol = randomIndex % gridSize;

            float posX = randCol * spacing - offset;
            float posY = depth;
            float posZ = randRow * spacing - offset;

            instance.transform.position = new Vector3(startPos.x + posX, posY, startPos.z + posZ);

            Objects[i] = instance; 

        }

        // if (Objects == null)
        // {
        //     Debug.LogError("No Objs Exist");
        // }

        objCount = Objects.Count();
        objNames = new string[objCount];

        string objLog = $"Initial {objCount} objects: ";
        for (int i = 0; i < objCount; i++)
        {
            objLog += Objects[i].name + "  ";
            objNames[i] = Objects[i].name;

        }
        Debug.Log(objLog);

        // FisherYatesShuffle(Objects);


        //for (int i = 0; i < allObjects.Length; i++)
        //{
        //    //Vector3 position = new Vector3(i % gridSize, -1f, i / gridSize);
        //    //GameObject instance = Instantiate(allObjects[i], position, Quaternion.identity);

        //    instance.name = allObjects[i].name;
        //}

    }

    

    private void OnEnable()
    {
        socket = FindObjectOfType<UdpSocket>();
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
