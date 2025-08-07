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
using Oculus.Interaction;

[DefaultExecutionOrder(100)]
public class SimpleTestManager : MonoBehaviour
{
    [HideInInspector]
    public GameObject[] Objects;
    public DistanceHandGrabInteractor interactor;
    public Material glowMaterial;
    public Material originalMaterial;
    public int timeLimit = 7;

    [HideInInspector]
    public DistanceHandGrabInteractable Target;

    public string UserName;

    [Tooltip("For Each Character's meaning, check line 13-16 in Session.cs")]
    public string SessionTypes = "PC";
    private int SessionTypeIndex = 0;
    private int SessionTypeCount;
    private char SessionType;
    
    [Header("Manager References")]
    [SerializeField] private UIManager uiManager;
    [HideInInspector]
    private int TrialIndex;
    private BlockDataPackage BlockData;
    private float CurrentDistance;
    private bool Occlusion;
    private Dictionary<GameObject, (Vector3 position, Quaternion rotation)> initialTransforms = new Dictionary<GameObject, (Vector3, Quaternion)>();
    private int WrongGraspCount;
    private string TargetObjectName;
    private string start_timestamp;
    private System.DateTime GraspingStartTime;
    private System.DateTime GraspingLimitedTime;
    private System.DateTime GraspingEndTime;
    private List<string> ObjectLogObjectInfo = new List<string>();
    private Dictionary<char, List<string>> GraspingLogInfo = new Dictionary<char, List<string>>();
    private Dictionary<char, List<string>> gestureLogAllScores = new Dictionary<char, List<string>>();
    private bool ObjectLogHasCollected = false;
    public AudioSource audioSource;
    private bool isCountingDown = false;

    private void Awake()
    {
        SessionTypeCount = SessionTypes.Length;
        start_timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss.fff");

        interactor.UserID = UserName;
        interactor.OnSelectTrue += HandleSelectTrue;
        interactor.OnSelectFalse += HandleSelectFalse;
        interactor.OnSelectEnd += HandleSelectEnd;
        interactor.OnSelectInterrupt += HandleSelectInterrupt;

        // Auto-find UIManager if not assigned
        if (uiManager == null)
        {
            uiManager = FindObjectOfType<UIManager>();
            Debug.Log($"Auto-found UIManager: {uiManager != null}");
        }
    }

// TODO: the object doesn't return to the original place -> change control scene with less objects
// TODO: check out-of reach grasping with long distance 
    private IEnumerator Start()
    {   
        SessionType = SessionTypes[SessionTypeIndex];
        
        // Set counting down state and disable interactor
        isCountingDown = true;
        interactor.enabled = false;
        
        yield return StartCoroutine(uiManager.CountDown(SessionType, () => {
            // Callback when countdown is complete
            interactor.enabled = true;
            isCountingDown = false;
        }));

        SessionTypeIndex++;
        
        PlayerPrefs.SetString("SessionType", SessionType.ToString());
        PlayerPrefs.Save();

        if (!GraspingLogInfo.ContainsKey(SessionType))
        {
            GraspingLogInfo[SessionType] = new List<string>();
        }

        if (!gestureLogAllScores.ContainsKey(SessionType))
        {
            gestureLogAllScores[SessionType] = new List<string>();
        }
        
        Objects = this.GetComponent<TrackData>().Objects;

        foreach (var obj in Objects)
        {
            if (obj == null) continue;

            initialTransforms[obj] = (obj.transform.position, obj.transform.rotation);
        }

        SetConfig();

        TrialIndex = 0;

        InvokeTest();
    }

    private void tryCollectObjectLog()
    {
        if (!ObjectLogHasCollected)
        {
            try
            {
                TelemetryMessage firstMessage = this.GetComponent<TrackData>().currentMessage;
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

    

    public void ResetObjects()
    {

        foreach (var obj in initialTransforms.Keys)
        {
            if (obj != null)
            {
                obj.transform.position = initialTransforms[obj].position;
                obj.transform.rotation = initialTransforms[obj].rotation;
            }
        }
    }

    private void ReHighlight()
    {
        if (interactor.LastObject != null)
        {
            Debug.Log("if (interactor.LastObject != null)");
            Renderer currentRenderer = interactor.LastObject.transform.Find("default").GetComponent<MeshRenderer>();
            currentRenderer.sharedMaterial = originalMaterial;
        }


        Renderer nextRenderer = interactor.TargetObject.transform.Find("default").GetComponent<MeshRenderer>();
        nextRenderer.sharedMaterial = glowMaterial;
    }

    void Update()
    {   
        if (isCountingDown)
        {
            return;
        }
        tryCollectObjectLog();
        uiManager.CreateOrUpdateProgressBars(interactor.candidateScores);
        checkGraspingTimeLimit();
    }

    private void checkGraspingTimeLimit()
    {
        TimeSpan remainingTime = GraspingLimitedTime - DateTime.Now;

        if (remainingTime.TotalSeconds <= 0)
        {
            // Time is up, handle the timeout case here
            // 9: Timeout
            LogGesture(9);
            interactor.LastObject = interactor.TargetObject;
            CorrectGrasp();
            ReHighlight();
            return;
        }

        uiManager.UpdateTimeRemaining(remainingTime.Seconds);
    }

    private void LogGesture(int correctGestureFlag)
    {   
        // correctGestureFlag: 
        // 1: correct grasp
        // 0: wrong grasp
        // 9: timeout
        string flag = correctGestureFlag.ToString();

        TelemetryMessage currentMessage = this.GetComponent<TrackData>().currentMessage;

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

        List<string> scoreList = new List<string>();

        foreach (var scoreEntry in interactor.candidateScores.Skip(1))
        {
            var parts = scoreEntry.Split(new char[] { ' ' }, System.StringSplitOptions.RemoveEmptyEntries);


            if (parts.Length >= 5)
            {
                string name = parts[0];
                float gestureScoreCandidateScores = float.Parse(parts[1]);
                float posScoreCandidateScores = float.Parse(parts[2]);
                float gestureWeightCandidateScores = float.Parse(parts[3]);
                float finalScoreCandidateScores = float.Parse(parts[4]);
                string scoreEntryString = $"{name}|{gestureScoreCandidateScores}|{posScoreCandidateScores}|{gestureWeightCandidateScores}|{finalScoreCandidateScores}";
                scoreList.Add(scoreEntryString);
            }
        }
        string allScores = string.Join("/", scoreList);
        string combinedInfo = $"{flag},{TargetObjectName},{rootRotationInfo},{rootPositionInfo},{allJoints},{allScores}";
        gestureLogAllScores[SessionType].Add(combinedInfo);
    }

    public void HandleSelectTrue(object sender, EventArgs e)
    {   
        LogGesture(1);
        // correctGestureFlag: 
        // 1: correct grasp
        CorrectGrasp();
    }

    public void HandleSelectFalse(object sender, EventArgs e)
    {   
        LogGesture(0);
        // correctGestureFlag: 
        // 0: wrong grasp
        WrongGrasp();
    }

    public void HandleSelectEnd(object sender, EventArgs e)
    {   
        ResetObjects();

        ReHighlight();
    }

    public void HandleSelectInterrupt(object sender, EventArgs e)
    {

    }

    public void SetConfig()
    {
        ExpConfig config = Session.GetExpConfig(SessionType);
        CurrentDistance = config.AngularDistance;
        Occlusion = config.Occlusion;
        interactor.GestureWeight = config.Weight;
    }
   
    public void InvokeTest()
    {
        UpdateTarget();
        ReHighlight();
    }

    public void UpdateTarget()
    {   
        GameObject currentObject = Objects[TrialIndex];
        TargetObjectName = currentObject.name;
        WrongGraspCount = 0;
        GraspingStartTime = System.DateTime.Now;
        GraspingLimitedTime = GraspingStartTime.AddSeconds(timeLimit);

        DistanceHandGrabInteractable target = currentObject.GetComponentInChildren<DistanceHandGrabInteractable>();

        target.ObjID = TrialIndex + 1;

        interactor.TargetObject = target.GetGameObject();

        interactor.Target = target;

        interactor.ResetPerformance();
    }
    
    

    public void CorrectGrasp()
    {
        
        if (audioSource != null)
        {
            audioSource.Play();
        }

        System.DateTime GraspingEndTime = System.DateTime.Now;

        var data = new string[] {
            TargetObjectName,
            WrongGraspCount.ToString(),
            GraspingStartTime.ToString("yyyy-MM-dd HH:mm:ss.fff"),
            GraspingEndTime.ToString("yyyy-MM-dd HH:mm:ss.fff"),
        };

        GraspingLogInfo[SessionType].Add(string.Join(",", data));

        TrialIndex++;
        if (TrialIndex >= Objects.Length)
        {   
            if (SessionTypeIndex >= SessionTypeCount)
            {   
                // If all sessions are finished, save the logs to CSV files and quit the application
                createFolderIfNotExists($"../user_study_data/{start_timestamp}/");
                createFolderIfNotExists($"../user_study_data/{start_timestamp}/meta_data/");
                createSessionTypeFolderIfNotExists(SessionTypes);
                writeObjectLog();
                writeRotationSeqLog();
                writeGestureLog();
                WriteGraspingLog();
                Quit();
            }
            else
            {
                // If all trials are finished, count down and move to the next session type
                StartCoroutine(Start());
                return;
            }
            
        }
        UpdateTarget();
        
    }

    public void WrongGrasp()
    {
        WrongGraspCount++;
    }

    private void createFolderIfNotExists(string folderPath)
    {
        if (!Directory.Exists(folderPath))
        {
            Directory.CreateDirectory(folderPath);
        }
    }

    private void createSessionTypeFolderIfNotExists(string sessionType)
    {
        for (int i = 0; i < SessionTypeCount; i++)
        {
            string sessionTypeFolderPath = $"../user_study_data/{start_timestamp}/{sessionType[i]}/";
            if (!Directory.Exists(sessionTypeFolderPath))
            {
                Directory.CreateDirectory(sessionTypeFolderPath);
            }
        }
    }

    private void writeObjectLog()
    {
        string objectInfoLogPath = $"../user_study_data/{start_timestamp}/meta_data/ObjectData.csv";
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

        RotationSeqNameObjectList = this.GetComponent<ObjectTransformAssignment>().RotationSeqNameObjectList;
        string RotationSeqLogPath = $"../user_study_data/{start_timestamp}/meta_data/RotationSeqData.csv";
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
        foreach (var entry in gestureLogAllScores)
        {
            string GestureLogPath = $"../user_study_data/{start_timestamp}/{entry.Key}/GestureData.csv";
            using (StreamWriter writer = new StreamWriter(GestureLogPath, true))
            {
                foreach (var line in entry.Value)
                {
                    writer.WriteLine(line); 
                }
            }
        }
    }

    private void  WriteGraspingLog()
    {
        foreach (var entry in GraspingLogInfo)
        {
            string GraspingLogPath = $"../user_study_data/{start_timestamp}/{entry.Key}/GraspingData.csv";
            using (StreamWriter writer = new StreamWriter(GraspingLogPath, true))
            {
                foreach (var line in entry.Value)
                {
                    writer.WriteLine(line); 
                }
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

