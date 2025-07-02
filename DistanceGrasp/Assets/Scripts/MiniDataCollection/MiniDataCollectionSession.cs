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
    // #if UNITY_EDITOR
    // private GameObjectRecorder handRecorder;
    // private GameObjectRecorder targetRecorder;
    // #endif

    void Start()
    {
        allPrefabs = Resources.LoadAll<GameObject>(PrefabFolderName);
        roundPrefabs = allPrefabs.OrderBy(_ => UnityEngine.Random.value).ToArray();
        roundLength = roundPrefabs.Length;
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
        Debug.Log($"[Session] Starting round {roundIndex + 1} with target {targetObjectName}");

        ClearPreviousObjects();
        InitializeRoundObjects();
        InitializeRoundParameters();

        // isRoundRunning = true;
        waitingForUserConfirm = true;
        // nextRoundButton.gameObject.SetActive(true);

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

            Quaternion originalRotation = instance.transform.rotation;
            float randomY = UnityEngine.Random.Range(-30f, 30f);
            Quaternion randomYRotation = Quaternion.Euler(0, randomY, 0);
            Quaternion newRotation = randomYRotation * originalRotation; ;
            instance.transform.rotation = newRotation;

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
        currentTrialLogger = new TrialLogger(TestUserId, sessionId, targetObjectName);
    }

    private void RunRound()
    {
         if (trialIndex == trialLength)
        {
            EndRound();
            return;
        }

        if (IsPinching(OVRHand.HandFinger.Index, ref indexFingerIsPinching))
        {
            if (!isInReach)
            {
                RecordTrial(1);
                MoveObjectToGraspingPosition();
                isInReach = true;
            }
            else
            {
                RecordInReach();
                SaveTrial();
                trialIndex++;
                if (trialIndex < trialLength)
                {
                    currentTrialLogger = new TrialLogger(TestUserId, sessionId, targetObjectName);
                    MoveObject();
                }
                isInReach = false;
            }
        }
        else if (!isInReach)
        {
            if (IsPinching(OVRHand.HandFinger.Middle, ref midFingerIsPinching))
            {
                RecordTrial(0);
                SaveTrial();
                trialIndex++;
                if (trialIndex < trialLength)
                {
                    currentTrialLogger = new TrialLogger(TestUserId, sessionId, targetObjectName);
                    MoveObject();
                }
            }
            else if (IsPinching(OVRHand.HandFinger.Ring, ref ringFingerIsPinching))
            {
                RecordTrial(2);
                SaveTrial();
                trialIndex++;
                if (trialIndex < trialLength)
                {
                    currentTrialLogger = new TrialLogger(TestUserId, sessionId, targetObjectName);
                    MoveObject();
                }
            }
        }
    // if (Input.GetKeyDown(KeyCode.Alpha1) || Input.GetKeyDown(KeyCode.Keypad1))
    //     {
    //         if (!isInReach)
    //         {
    //             RecordTrialGesture(1);
    //             MoveObjectToGraspingPosition();
    //             isInReach = true;
    //         }
    //         else
    //         {
    //             // Second index pinch confirms in-reach gesture 
    //             currentTrialRecord.inReachGesture = new Gesture(rightHandVisual); // labeledSessionData is updated as well
    //             MoveObject();                    // advance to next object
    //             isInReach = false;              
    //         }
    //     }
    //    else if (!isInReach)
    //     {
    //         if (Input.GetKeyDown(KeyCode.Alpha2) || Input.GetKeyDown(KeyCode.Keypad2))
    //         {
    //             RecordTrialGesture(0);
    //             MoveObject();
    //         }
    //         else if (Input.GetKeyDown(KeyCode.Alpha3) || Input.GetKeyDown(KeyCode.Keypad3))
    //         {
    //             RecordTrialGesture(2);
    //             MoveObject();
    //         }
    //     }
    }



   private void RecordTrial(int gestureLabel)
    {
        GameObject obj = Objects[trialIndex];
        currentTrialLogger.RecordFrame(rightHandVisual, obj, mainCamera, isLabeled: true);
        currentTrialLogger.SetLabel(gestureLabel, obj.name);
    }

    private void RecordInReach()
    {
        GameObject obj = Objects[trialIndex];
        currentTrialLogger.RecordFrame(rightHandVisual, obj, mainCamera, isInReach: true);
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
                obj.transform.position = new Vector3(0.0f, 0.0f, 0.5f);
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

    private int GetObjectTypeFromState(string objName)
    {
        // Dummy mapping function
        return 0;
    }
}
