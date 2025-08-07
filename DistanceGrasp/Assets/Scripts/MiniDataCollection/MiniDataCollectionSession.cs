using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;
using Oculus.Interaction;
using UnityEngine.UI; 
using Newtonsoft.Json;

// #if UNITY_EDITOR
// using UnityEditor;
// using UnityEditor.Animations;
// #endif

public class MiniDataCollectionSession : MonoBehaviour
{
    public string TestUserId = "1";
    public string PrefabFolderName;
    public int neg2PosRatio = 5;
    public OVRHand leftHand;
    public HandVisual rightHandVisual;
    public Camera mainCamera;

    private GameObject[] allPrefabs;
    private GameObject[] roundPrefabs;
    private GameObject[] Objects;

    private Vector3 initial_position_obj = new Vector3(0.0f,-0.1f, 0.45f);
    private string sessionId;
    private int roundIndex;
    private int roundLength;
    private bool isRoundRunning = false;
    private bool sessionCompleted = false;
    private bool waitingForUserConfirm = false;

    private int trialIndex;
    private int trialLength;
    private string targetObjectName;
    private string startTimestamp;

    private bool isInReach = false;
    private bool indexFingerIsPinching = false;
    private bool midFingerIsPinching = false;
    private bool ringFingerIsPinching = false;

    private Dictionary<GameObject, (Vector3, Quaternion)> initialTransforms = new();

    private TrialLogger currentTrialLogger;
    private List<TrialLogger> allTrialLogs = new();
    private bool isRecordingContinuous = false;

    private Dictionary<string, int> replicateCounter = new();  // 记录“这个物体已经录了几次” → 决定 0/120/240°
    private int currentReplicateIndex = 0;  // 本 round 是该物体的第几次（0/1/2）
    // #if UNITY_EDITOR
    // private GameObjectRecorder handRecorder;
    // private GameObjectRecorder targetRecorder;
    // #endif

    void Start()
    {
        // 1. Load all prefabs
        allPrefabs = Resources.LoadAll<GameObject>(PrefabFolderName);
        var allObjectNames = allPrefabs.Select(p => p.name).ToList();

        // 2. Read existing recordings(#recordings for each object)
        var recordingCount = CountExistingRecordings(TestUserId);

        // 3. Initialize replicateCounter: how many times each object has been recorded 
        replicateCounter = new Dictionary<string, int>(recordingCount);

        // 4. Determine which objects to record, and how many times for each object
        List<GameObject> finalList = new();
        foreach (var prefab in allPrefabs)
        {
            string name = prefab.name;
            int existingCount = recordingCount.ContainsKey(name) ? recordingCount[name] : 0;
            int toAdd = Mathf.Max(0, 3 - existingCount); // 还需要录几次
            for (int i = 0; i < toAdd; i++)
            {
                finalList.Add(prefab); // 每需要录一次，就加入一份
            }
        }

        // 5. If no objects to record, exit the session
        if (finalList.Count == 0)
        {
            Debug.Log("[Session] All required rounds already recorded for this user.");
    #if UNITY_EDITOR
            UnityEditor.EditorApplication.isPlaying = false;
    #else
            Application.Quit();
    #endif
            return;
        }


        // // 5. Shuffle the final list to randomize the order of rounds
        // roundPrefabs = finalList.OrderBy(_ => UnityEngine.Random.value).ToArray();
        roundPrefabs = finalList.ToArray();

        // 7. Set #rounds
        roundLength = roundPrefabs.Length;

        // 8. Start the first round
        roundIndex = 0;
        StartNextRound();
    }

    void Update()
    {
        if (waitingForUserConfirm)
        {
            if (Input.GetKeyDown(KeyCode.Space)) // 临时用键盘测试
            {
                waitingForUserConfirm = false;
                isRoundRunning = true;
            }
            return; // 阻止 Update 执行其他逻辑
        }
        if (!isRoundRunning || sessionCompleted) return;

        // if (isRecordingContinuous && leftHand.IsTracked)
        if (isRecordingContinuous && isRoundRunning && trialIndex < neg2PosRatio + 1)
        {
            GameObject obj = Objects[trialIndex];
            currentTrialLogger.RecordFrame(rightHandVisual, obj, mainCamera);
        }

        RunRound();

        if (!isRoundRunning)
        {
            roundIndex++;
            StartNextRound();
        }

        // #if UNITY_EDITOR
        // if (handRecorder != null)
        // {
        //     handRecorder.TakeSnapshot(Time.deltaTime);
        // }
        // if (targetRecorder != null)
        // {
        //     targetRecorder.TakeSnapshot(Time.deltaTime);
        // }
        // #endif

    }
    
        public void OnUserConfirmNextRound() // Connect to PokeInteratable
    {
        waitingForUserConfirm = false;
        isRoundRunning = true;
    }

    private void StartNextRound()
    {
        if (roundIndex >= roundLength)
        {
            sessionCompleted = true;
            Debug.Log("[Session] All rounds complete.");
#if UNITY_EDITOR
            UnityEditor.EditorApplication.isPlaying = false;
#else
                Application.Quit();
#endif
            return;
        }

        targetObjectName = roundPrefabs[roundIndex].name;

        // —— According to history determine current replicateIndex (0/1/2) —— //
        if (!replicateCounter.ContainsKey(targetObjectName))
            replicateCounter[targetObjectName] = 0;       // The object has never been recorded before

        currentReplicateIndex = replicateCounter[targetObjectName] % 3; // 0→1→2
        replicateCounter[targetObjectName] += 1;  


        Debug.Log($"[Session] Round {roundIndex + 1} | Target {targetObjectName} | replicate {currentReplicateIndex}");

        ClearPreviousObjects();
        InitializeRoundObjects();
        InitializeRoundParameters();

        waitingForUserConfirm = true;

        // #if UNITY_EDITOR
        // if (handToRecord != null)
        // {
        //     handRecorder = new GameObjectRecorder(handToRecord);
        //     handRecorder.BindComponentsOfType<Transform>(handToRecord, true); // 记录所有子节点
        // }

        // if (trialIndex == 0 && Objects != null && Objects.Length > 0 && !waitingForUserConfirm)
        // {
        //     GameObject currentTarget = Objects[trialIndex];
        //     if (currentTarget != null)
        //     {
        //         targetRecorder = new GameObjectRecorder(currentTarget);
        //         targetRecorder.BindComponentsOfType<Transform>(currentTarget, false); // 仅目标物体 Transform
        //     }
        // }
        // #endif

    }

    private void ClearPreviousObjects()
    {
        if (Objects != null)
        {
            foreach (var obj in Objects)
            {
                if (obj != null)
                    Destroy(obj);
            }
        }
        Objects = null;
    }

    private void InitializeRoundObjects()
    {
        var shuffled = allPrefabs.OrderBy(_ => UnityEngine.Random.value).ToList();
        var target = shuffled.FirstOrDefault(p => p.name == targetObjectName);
        if (target != null) shuffled.Remove(target);
        if (target != null) shuffled.Insert(0, target);

        shuffled = shuffled.Take(neg2PosRatio + 1).ToList();
        Objects = new GameObject[shuffled.Count];

        for (int i = 0; i < shuffled.Count; i++)
        {
            var instance = Instantiate(shuffled[i]);
            instance.name = shuffled[i].name; 
            instance.transform.position = new Vector3(i, 0, 2);

            // —— Rotation Logic —— //
            Quaternion baseRot = instance.transform.rotation;
            float yAngle;
            float[] preset = { 0f, 120f, 240f };
            if (instance.name == targetObjectName)         // target object: 0/120/240°
            {
                yAngle = preset[currentReplicateIndex];
                if (currentReplicateIndex != 0) // 如果不是第一次录制，则随机偏移
                {
                    float delta_yAngle = UnityEngine.Random.Range(-60f, 60f);
                    yAngle += delta_yAngle;
                }
            }
            else                                           // distract object: random choose from 0/120/240°
            {
                float delta_yAngle = UnityEngine.Random.Range(-60f, 60f);
                yAngle = preset[UnityEngine.Random.Range(0, preset.Length)] + delta_yAngle;
            }
            instance.transform.rotation = Quaternion.Euler(0, yAngle, 0) * baseRot;

            Objects[i] = instance;
        }
    }

    private void InitializeRoundParameters()
    {
        trialIndex = 0;
        trialLength = Objects.Length;
        startTimestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
        sessionId = $"{targetObjectName}_{startTimestamp}";

        isInReach = false;
        indexFingerIsPinching = false;
        midFingerIsPinching = false;
        ringFingerIsPinching = false;

        initialTransforms.Clear();
        foreach (var obj in Objects)
        {
            initialTransforms[obj] = (obj.transform.position, obj.transform.rotation);
        }

        isRecordingContinuous = true;
        allTrialLogs.Clear();
        currentTrialLogger = new TrialLogger(TestUserId, sessionId, targetObjectName, trialIndex);
    }

    private void RunRound()
    {        
        if (trialIndex == trialLength)
        {
            EndRound();
            return;
        }


            
        if (isInReach)
        {
            if (Input.GetKeyDown(KeyCode.Alpha1) || Input.GetKeyDown(KeyCode.Keypad1))
            {
                RecordInReach(1);
                SaveTrial();
                trialIndex++;
                if (trialIndex < trialLength)
                {
                    currentTrialLogger = new TrialLogger(TestUserId, sessionId, targetObjectName, trialIndex);
                    MoveObject();
                }
                isInReach = false;
            }
            else if (Input.GetKeyDown(KeyCode.Alpha2) || Input.GetKeyDown(KeyCode.Keypad2))
            {
                RecordInReach(0);
                SaveTrial();
                trialIndex++;
                if (trialIndex < trialLength)
                {
                    currentTrialLogger = new TrialLogger(TestUserId, sessionId, targetObjectName, trialIndex);
                    MoveObject();
                }
                isInReach = false;
            }
            else if (Input.GetKeyDown(KeyCode.Alpha3) || Input.GetKeyDown(KeyCode.Keypad3))
            {
                RecordInReach(2);
                SaveTrial();
                trialIndex++;
                if (trialIndex < trialLength)
                {
                    currentTrialLogger = new TrialLogger(TestUserId, sessionId, targetObjectName, trialIndex);
                    MoveObject();
                }
                isInReach = false;
            }
            
            
        }
        
        else if (!isInReach)
        {
            if (Input.GetKeyDown(KeyCode.Alpha1) || Input.GetKeyDown(KeyCode.Keypad1))
            {
                RecordTrial(1);
                MoveObjectToGraspingPosition();
                isInReach = true;
            }
            else if (Input.GetKeyDown(KeyCode.Alpha2) || Input.GetKeyDown(KeyCode.Keypad2))
            {
                RecordTrial(0);
                SaveTrial();
                trialIndex++;
                if (trialIndex < trialLength)
                {
                    currentTrialLogger = new TrialLogger(TestUserId, sessionId, targetObjectName, trialIndex);
                    MoveObject();
                }
            }
            else if (Input.GetKeyDown(KeyCode.Alpha3) || Input.GetKeyDown(KeyCode.Keypad3))
            {
                RecordTrial(2);
                SaveTrial();
                trialIndex++;
                if (trialIndex < trialLength)
                {
                    currentTrialLogger = new TrialLogger(TestUserId, sessionId, targetObjectName, trialIndex);
                    MoveObject();
                }
            }
        }
    }



    private void RecordTrial(int gestureLabel)
    {
        GameObject obj = Objects[trialIndex];
        currentTrialLogger.RecordFrame(rightHandVisual, obj, mainCamera, isLabeled: true);
        currentTrialLogger.SetLabel(gestureLabel, obj.name, isInReach = false);
    }

    private void RecordInReach(int gestureLabel)
    {
        GameObject obj = Objects[trialIndex];
        currentTrialLogger.RecordFrame(rightHandVisual, obj, mainCamera, isInReach: true);
        currentTrialLogger.SetLabel(gestureLabel, obj.name, isInReach = true);
    }

    private void SaveTrial()
    {
        allTrialLogs.Add(currentTrialLogger);
    }


    private bool IsPinching(OVRHand.HandFinger finger, ref bool pinchFlag)
    {
        bool isPinching = leftHand.GetFingerIsPinching(finger);
        if (isPinching && !pinchFlag)
        {
            pinchFlag = true;
            return true;
        }
        else if (!isPinching)
        {
            pinchFlag = false;
        }
        return false;
    }

    private void MoveObject()
    {
        foreach (var obj in initialTransforms.Keys)
        {
            if (obj.name == targetObjectName)
            {
                obj.transform.position = new Vector3(
                    initialTransforms[obj].Item1.x,
                    initialTransforms[obj].Item1.y - 0.5f,
                    initialTransforms[obj].Item1.z
                );
                obj.transform.rotation = initialTransforms[obj].Item2;
            }
            else
            {
                obj.transform.position = new Vector3(
                    initialTransforms[obj].Item1.x - 1.0f * trialIndex,
                    initialTransforms[obj].Item1.y,
                    initialTransforms[obj].Item1.z
                );
                obj.transform.rotation = initialTransforms[obj].Item2;
            }
        }
    }

    private void MoveObjectToGraspingPosition()
    {
        foreach (var obj in initialTransforms.Keys)
        {
            if (obj.name == Objects[trialIndex].name)
            {
                obj.transform.position = initial_position_obj;
                obj.transform.rotation = initialTransforms[obj].Item2;
            }
        }
    }

    private void EndRound()
    {
        isRecordingContinuous = false;
        isRoundRunning = false;

        string basePath = $"../collected_data/s{TestUserId}/{targetObjectName}/{startTimestamp}/";
        if (!Directory.Exists(basePath)) Directory.CreateDirectory(basePath);

        string json = JsonConvert.SerializeObject(allTrialLogs, Formatting.None);
        File.WriteAllText(Path.Combine(basePath, "all_trials.json"), json);

        Debug.Log("[Save] Gesture logs saved to: " + basePath);

        // #if UNITY_EDITOR
        // string folderPath = "Assets/RecordedAnimations";
        // if (!AssetDatabase.IsValidFolder(folderPath))
        // {
        //     AssetDatabase.CreateFolder("Assets", "RecordedAnimations");
        // }

        // string baseName = $"{sessionId}_{targetObjectName}";

        // if (handRecorder != null)
        // {
        //     AnimationClip clip = new AnimationClip();
        //     handRecorder.SaveToClip(clip);
        //     AssetDatabase.CreateAsset(clip, $"{folderPath}/{baseName}_hand.anim");
        // }

        // if (targetRecorder != null)
        // {
        //     AnimationClip clip = new AnimationClip();
        //     targetRecorder.SaveToClip(clip);
        //     AssetDatabase.CreateAsset(clip, $"{folderPath}/{baseName}_object.anim");
        // }

        // AssetDatabase.SaveAssets();
        // Debug.Log($"[Animation] Saved hand + object clips to {folderPath}/");
        // #endif


    }

    private Dictionary<string, int> CountExistingRecordings(string userId)
    {
        string baseUserFolder = $"../collected_data/s{userId}/";
        var result = new Dictionary<string, int>();

        if (!Directory.Exists(baseUserFolder)) return result;

        foreach (var objectFolder in Directory.GetDirectories(baseUserFolder))
        {
            string objName = Path.GetFileName(objectFolder);
            int count = Directory.GetDirectories(objectFolder).Length;   // 每个时间戳目录算一轮
            result[objName] = count;
        }
        return result;
    }

}
