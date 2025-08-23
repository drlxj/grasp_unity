using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using Newtonsoft.Json;

// 实验基本信息
[System.Serializable]
public class ExperimentInfo
{
    public string userID;
    public string experimentTimestamp;
    public string sessionType;
    public int timeLimit;
    public int totalObjects;
    public string prefabFolderName;
    public float angleStep;
}

// 物体初始化信息
[System.Serializable]
public class ObjectInitData
{
    public string objectName;
    public float[] initialPosition = new float[3];  // [x, y, z]
    public float[] initialRotation = new float[4]; // [x, y, z, w]
    public int objectID;
    
    public ObjectInitData(string name, Vector3 position, Quaternion rotation, int id)
    {
        objectName = name;
        initialPosition[0] = position.x;
        initialPosition[1] = position.y;
        initialPosition[2] = position.z;
        initialRotation[0] = rotation.x;
        initialRotation[1] = rotation.y;
        initialRotation[2] = rotation.z;
        initialRotation[3] = rotation.w;
        objectID = id;
    }
    
    public ObjectInitData() { }
}

// 每次Trial的详细信息
[System.Serializable]
public class TrialData
{
    public int trialIndex;
    public string targetObjectName;
    public int graspCount;
    public float graspingDuration;
    public bool isSuccessful;
    public DateTime startTime;
    public DateTime endTime;
    public List<GraspData> grasps = new List<GraspData>();
}

// 每次Grasp的详细信息
[System.Serializable]
public class GraspData
{
    public string selectedObjectName;
    
    // Python传输数据
    public int packetIdx; // 用于关联手势数据和分数数据
    public Dictionary<string, float> gestureScores = new Dictionary<string, float>();
    public Dictionary<string, float> positionScores = new Dictionary<string, float>();
    public Dictionary<string, float> finalScores = new Dictionary<string, float>();
    
    // 抓取结果
    public string graspResult; // "success", "wrong_object", "timeout"
    public float graspDuration;
    
    // 手势数据（传输到Python的）
    public object gestureData; // 可以存储手势数据对象
}

// 数据缓存项
[System.Serializable]
public class DataCache
{
    public int packetIdx;
    public object gestureData;  // 手势数据（改为 object 类型）
    public Dictionary<string, float> gestureScores;
    public Dictionary<string, float> positionScores;
    public Dictionary<string, float> finalScores;
    public DateTime timestamp;
    public bool isComplete;
}

public class UserStudyDataRecorder : MonoBehaviour
{
    private ExperimentInfo experimentInfo;
    private List<ObjectInitData> objectInitDataList = new List<ObjectInitData>();
    private List<TrialData> trialDataList = new List<TrialData>();
    
    private TrialData currentTrialData;
    private GraspData currentGraspData;
    private int currentGraspIndex = 0;
    
    // 数据缓存
    private Dictionary<int, DataCache> dataCache = new Dictionary<int, DataCache>();
    
    public static UserStudyDataRecorder Instance { get; private set; }
    
    private void Awake()
    {
        if (Instance == null)
        {
            Instance = this;
            DontDestroyOnLoad(gameObject);
        }
        else
        {
            Destroy(gameObject);
        }
    }
    
    // 初始化实验信息
    public void InitializeExperiment(string userID, string sessionType, int timeLimit, string prefabFolderName, float angleStep)
    {
        experimentInfo = new ExperimentInfo
        {
            userID = userID,
            experimentTimestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss"),
            sessionType = sessionType,
            timeLimit = timeLimit,
            prefabFolderName = prefabFolderName,
            angleStep = angleStep
        };
    }
    
    // 记录物体初始化信息
    public void RecordObjectInitialization(GameObject[] objects)
    {
        objectInitDataList.Clear();
        experimentInfo.totalObjects = objects.Length;
        
        for (int i = 0; i < objects.Length; i++)
        {
            if (objects[i] != null)
            {
                var objectData = new ObjectInitData(
                    objects[i].name,
                    objects[i].transform.position,
                    objects[i].transform.rotation,
                    i + 1
                );
                objectInitDataList.Add(objectData);
                Debug.Log($"Recorded object {i + 1}: {objects[i].name} at {objects[i].transform.position}");
            }
            else
            {
                Debug.LogWarning($"Object at index {i} is null");
            }
        }
        
        Debug.Log($"Recorded {objectInitDataList.Count} objects initialization data");
    }
    
    // 开始新的Trial
    public void StartNewTrial(int trialIndex, string targetObjectName)
    {
        currentTrialData = new TrialData
        {
            trialIndex = trialIndex,
            targetObjectName = targetObjectName,
            startTime = DateTime.Now,
            grasps = new List<GraspData>()
        };
        
        currentGraspIndex = 0;
    }
    
    // 开始新的Grasp
    public void StartNewGrasp(int packetIdx = 0)
    {
        currentGraspData = new GraspData
        {
            packetIdx = packetIdx,
            gestureScores = new Dictionary<string, float>(),
            positionScores = new Dictionary<string, float>(),
            finalScores = new Dictionary<string, float>(),
            gestureData = {} // 初始化手势数据字段
        };
        
        currentGraspIndex++;
    }
    

    
    // 记录抓取结果和Python分数（组合方法）
    public void RecordGraspResultWithScores(string selectedObjectName, string result, float duration,
                                          int packetIdx = 0)
    {
        // 如果没有当前的抓取数据，创建一个新的
        if (currentGraspData == null)
        {
            StartNewGrasp(packetIdx);
        }
        else if (packetIdx != 0)
        {
            // 如果已有抓取数据但packetIdx不同，更新它
            currentGraspData.packetIdx = packetIdx;
        }
        
        // 根据packetIdx查找完整数据
        DataCache cachedData = FindData(packetIdx);
        currentGraspData.gestureData = cachedData.gestureData;
        currentGraspData.gestureScores = new Dictionary<string, float>(cachedData.gestureScores);
        currentGraspData.positionScores = new Dictionary<string, float>(cachedData.positionScores);
        currentGraspData.finalScores = new Dictionary<string, float>(cachedData.finalScores);
        
        
        
        // 记录抓取结果
        currentGraspData.graspResult = result;
        currentGraspData.graspDuration = duration;
        
        // 添加到当前Trial
        currentTrialData.grasps.Add(currentGraspData);
        
        // 准备下一个抓取
        currentGraspData = null;
    }
    
    // 缓存手势数据
    public void CacheGestureData(int packetIdx, TelemetryMessage message)
    {
        CleanupExpiredCache();
        
        if (!dataCache.ContainsKey(packetIdx))
        {
            dataCache[packetIdx] = new DataCache { packetIdx = packetIdx, timestamp = DateTime.Now };
        }
        
        // 创建简化的手势数据结构，参考ObjectInitData的保存方式
        var simplifiedGestureData = new
        {
            packetIdx = message.packetIdx,
            rootPosition = new float[] { message.rootPosition.x, message.rootPosition.y, message.rootPosition.z },
            rootRotation = new float[] { message.rootRotation.x, message.rootRotation.y, message.rootRotation.z, message.rootRotation.w },
            jointPositions = message.jointPositions.Select(pos => new float[] { pos.x, pos.y, pos.z }).ToArray(),
            objectCount = message.objectStates?.Length ?? 0
        };
        
        dataCache[packetIdx].gestureData = simplifiedGestureData;  
        
        Debug.Log($"Cached gesture data for packetIdx: {packetIdx}");
    }
    
    // 缓存分数数据
    public void CacheScoreData(int packetIdx, Dictionary<string, float> gestureScores, 
                              Dictionary<string, float> positionScores, Dictionary<string, float> finalScores)
    {
        if (dataCache.TryGetValue(packetIdx, out DataCache cache))
        {
            cache.gestureScores = gestureScores;
            cache.positionScores = positionScores;
            cache.finalScores = finalScores;
            cache.isComplete = true;
            Debug.Log($"Cached score data for packetIdx: {packetIdx}");
        }
    }
    
    // 根据packetIdx查找完整数据
    private DataCache FindData(int packetIdx)
    {
        if (dataCache.TryGetValue(packetIdx, out DataCache cache) && cache.isComplete)
        {
            Debug.Log($"Found complete data for packetIdx: {packetIdx}");
            return cache;
        }
        
        Debug.LogWarning($"No complete data found for packetIdx: {packetIdx}");
        return null;
    }
    
    // 清理过期缓存
    private void CleanupExpiredCache()
    {
        var expiredKeys = new List<int>();
        var cutoffTime = DateTime.Now.AddSeconds(-5);
        
        foreach (var kvp in dataCache)
        {
            if (kvp.Value.timestamp < cutoffTime)
            {
                expiredKeys.Add(kvp.Key);
            }
        }
        
        foreach (var key in expiredKeys)
        {
            dataCache.Remove(key);
        }
    }
    
    // 清空 Trial 数据（开始新的 session 时调用）
    public void ClearTrialData()
    {
        trialDataList.Clear();
        Debug.Log("Cleared trial data for new session");
    }
    
    // 完成Trial
    public void CompleteTrial(bool isSuccessful, int graspCount, float totalDuration)
    {
        if (currentTrialData != null)
        {
            currentTrialData.isSuccessful = isSuccessful;
            currentTrialData.graspCount = graspCount;
            currentTrialData.graspingDuration = totalDuration;
            currentTrialData.endTime = DateTime.Now;
            
            trialDataList.Add(currentTrialData);
        }
    }
    
    // 保存数据到文件
    public void SaveDataToFiles()
    {
        string folderPath = $"../user_study_data/{experimentInfo.userID}/{experimentInfo.prefabFolderName}/{experimentInfo.sessionType}/";
        Directory.CreateDirectory(folderPath);
        
        // 保存实验基本信息
        SaveExperimentInfo(folderPath);
        
        // 保存物体初始化信息
        SaveObjectInitData(folderPath);
        
        // 保存Trial数据
        SaveTrialData(folderPath);
        
        Debug.Log($"Data saved to: {folderPath}");
    }
    
    private void SaveExperimentInfo(string folderPath)
    {
        string filePath = Path.Combine(folderPath, "ExperimentInfo.json");
        var settings = new JsonSerializerSettings
        {
            ReferenceLoopHandling = ReferenceLoopHandling.Ignore,
            Formatting = Formatting.Indented
        };
        string json = JsonConvert.SerializeObject(experimentInfo, settings);
        File.WriteAllText(filePath, json);
    }
    
    private void SaveObjectInitData(string folderPath)
    {
        string filePath = Path.Combine(folderPath, "ObjectInitData.json");
        // string json = JsonUtility.ToJson(new { objects = objectInitDataList }, true);
        string json = JsonConvert.SerializeObject(objectInitDataList, Formatting.Indented);
        File.WriteAllText(filePath, json);
    }
    
    private void SaveTrialData(string folderPath)
    {
        string filePath = Path.Combine(folderPath, "TrialData.json");
        string json = JsonConvert.SerializeObject(trialDataList , Formatting.Indented);
        File.WriteAllText(filePath, json);
    }
    

}