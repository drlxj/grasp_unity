using System;
using System.IO;
using Oculus.Interaction;
using System.Collections.Generic;
using UnityEngine;
using Newtonsoft.Json;

[DefaultExecutionOrder(50)]
public class TrackData : MonoBehaviour
{
    UdpSocket socket;
    public HandVisual currentHand;

    // public GameObject CenterEyeAnchor;
    public float heightOffset = 0.0f; // Offset from the eyes position
    public Transform ObjectCenter;
    [HideInInspector]
    public GameObject[] Objects;
    
    private readonly float updateInterval = 1.0f / 15.0f; // 15 fps
    private float nextUpdateTime = 0.0f;
    private static int objCount = 0;
    private Vector3 rootPosition;

    private int packetId = 0;
    
    public TelemetryMessage currentMessage;
    
    // 事件：当发送数据包时通知
    public static event System.Action<int> OnTelemetryDataSent;

    private void Awake()
    {
        // 从Session获取物体
        RefreshObjectReferences();
    }

    /// <summary>
    /// 刷新物体引用
    /// </summary>
    public void RefreshObjectReferences()
    {
        var session = FindObjectOfType<Session>();
        if (session != null)
        {
            Objects = session.GetObjects();
            if (Objects != null)
            {
                objCount = Objects.Length;
                Debug.Log($"TrackData: Loaded {objCount} objects from Session");
            }
            else
            {
                Debug.LogWarning("TrackData: No objects found in Session");
            }
        }
        else
        {
            Debug.LogError("TrackData: No Session found in scene");
        }
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
    }
    
    private void OnDisable()
    {
        // Unsubscribe from the JointUpdated event
        // HandVisual.JointUpdated -= OnJointUpdated;
    }

    void Start()
    {
        // 确保物体引用是最新的
        if (Objects == null || Objects.Length == 0)
        {
            RefreshObjectReferences();
        }
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

        message.objectStates = AddObjectsToTelemetryMessage(root, out string objInfo);
        
        // 缓存手势数据
        if (UserStudyDataRecorder.Instance != null)
        {
            UserStudyDataRecorder.Instance.CacheGestureData((int)message.packetIdx, message);
        }
        
        // 通知SimpleTestManager更新packetId
        OnTelemetryDataSent?.Invoke((int)message.packetIdx);
        
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
