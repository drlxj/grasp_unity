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
    public DistanceHandGrabInteractor interactor;
    public Material glowMaterial;
    public Material originalMaterial;

    [HideInInspector]
    public DistanceHandGrabInteractable Target;

    [Tooltip("For Each Character's meaning, check line 13-16 in Session.cs")]
    public GameObject CounterUI;
    private TextMeshProUGUI CounterText;
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
        start_timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss.fff");

        CounterText = CounterUI.GetComponentInChildren<TextMeshProUGUI>();
    }

// TODO: the object doesn't return to the original place -> change control scene with less objects
// TODO: check out-of reach grasping with long distance 
    private void Start()
    {           
        Objects = this.GetComponent<TrackData>().Objects;

        foreach (var obj in Objects)
        {
            if (obj == null) continue;

            initialTransforms[obj] = (obj.transform.position, obj.transform.rotation);
        }

        TrialIndex = 0;
    }

    void Update()
    {   

    }

    // private void LogGesture(int correctGestureFlag)
    // {   
    //     // correctGestureFlag: 
    //     // 1: correct grasp
    //     // 0: wrong grasp
    //     // 9: timeout
    //     string flag = correctGestureFlag.ToString();

    //     TelemetryMessage currentMessage = this.GetComponent<TrackData>().currentMessage;

    //     Quaternion rootRotation = currentMessage.rootRotation;
    //     Vector3 rootPosition = currentMessage.rootPosition;
    //     Vector3[] jointPositions = currentMessage.jointPositions;
  
    //     List<string> jointStrings = new List<string>();

    //     string rootRotationInfo = $"{rootRotation.x}|{rootRotation.y}|{rootRotation.z}|{rootRotation.w}";
    //     string rootPositionInfo = $"{rootPosition.x}|{rootPosition.y}|{rootPosition.z}";

    //     foreach (var joint in jointPositions)
    //     {
    //         string jointInfo = $"{joint.x}|{joint.y}|{joint.z}";
    //         jointStrings.Add(jointInfo);
    //     }

    //     string allJoints = string.Join("/", jointStrings);

    //     List<string> scoreList = new List<string>();

    //     foreach (var scoreEntry in interactor.candidateScores.Skip(1))
    //     {
    //         var parts = scoreEntry.Split(new char[] { ' ' }, System.StringSplitOptions.RemoveEmptyEntries);


    //         if (parts.Length >= 5)
    //         {
    //             string name = parts[0];
    //             float gestureScoreCandidateScores = float.Parse(parts[1]);
    //             float posScoreCandidateScores = float.Parse(parts[2]);
    //             float gestureWeightCandidateScores = float.Parse(parts[3]);
    //             float finalScoreCandidateScores = float.Parse(parts[4]);
    //             string scoreEntryString = $"{name}|{gestureScoreCandidateScores}|{posScoreCandidateScores}|{gestureWeightCandidateScores}|{finalScoreCandidateScores}";
    //             scoreList.Add(scoreEntryString);
    //         }
    //     }
    //     string allScores = string.Join("/", scoreList);
    //     string combinedInfo = $"{flag},{TargetObjectName},{rootRotationInfo},{rootPositionInfo},{allJoints},{allScores}";
    //     gestureLogAllScores[SessionType].Add(combinedInfo);


    // }

    // public void UpdateTarget()
    // {   
    //     GameObject currentObject = Objects[TrialIndex];
    //     TargetObjectName = currentObject.name;
    //     WrongGraspCount = 0;
    //     GraspingStartTime = System.DateTime.Now;
    //     GraspingLimitedTime = GraspingStartTime.AddSeconds(timeLimit);

    //     DistanceHandGrabInteractable target = currentObject.GetComponentInChildren<DistanceHandGrabInteractable>();

    //     target.ObjID = TrialIndex + 1;

    //     interactor.TargetObject = target.GetGameObject();

    //     interactor.Target = target;

    //     interactor.ResetPerformance();
    // }
    
    //private void createFolderIfNotExists(string folderPath)
    //{
    //    if (!Directory.Exists(folderPath))
    //    {
    //        Directory.CreateDirectory(folderPath);
    //    }
    //}

    //private void createSessionTypeFolderIfNotExists(string sessionType)
    //{
    //    for (int i = 0; i < SessionTypeCount; i++)
    //    {
    //        string sessionTypeFolderPath = $"../DistanceGrasp/Assets/LogData/{start_timestamp}/{sessionType[i]}/";
    //        if (!Directory.Exists(sessionTypeFolderPath))
    //        {
    //            Directory.CreateDirectory(sessionTypeFolderPath);
    //        }
    //    }
    //}

    private void writeObjectLog()
    {
        string objectInfoLogPath = $"../DistanceGrasp/Assets/LogData/{start_timestamp}/meta_data/ObjectData.csv";
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
        string RotationSeqLogPath = $"../DistanceGrasp/Assets/LogData/{start_timestamp}/meta_data/RotationSeqData.csv";
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
            string GestureLogPath = $"../DistanceGrasp/Assets/LogData/{start_timestamp}/{entry.Key}/GestureData.csv";
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
            string GraspingLogPath = $"../DistanceGrasp/Assets/LogData/{start_timestamp}/{entry.Key}/GraspingData.csv";
            using (StreamWriter writer = new StreamWriter(GraspingLogPath, true))
            {
                foreach (var line in entry.Value)
                {
                    writer.WriteLine(line); 
                }
            }
        }
    }

    //private IEnumerator CountDown()
    //{   
    //    isCountingDown = true; 
    //    // char nextSessionType = SessionTypes[SessionTypeIndex];
    //    interactor.enabled = false;

    //    for (int i = 6; i > 0; i--)
    //    {
    //        CounterText.text = $"Next Session: {SessionType}\nStarting in {i}...";
    //        CounterText.color = Color.yellow; 
    //        yield return new WaitForSeconds(1);
    //    }

    //    CounterText.text = "Go!";
    //    CounterText.color = Color.red;
    //    yield return new WaitForSeconds(1); 

    //    CounterText.text = "";

    //    interactor.enabled = true;
    //    CounterText.color = Color.white;
    //    isCountingDown = false;
    //}

   

    //public static void Quit()
    //{   
    //    #if UNITY_EDITOR
    //    UnityEditor.EditorApplication.isPlaying = false;
    //    #else
    //    Application.Quit();
    //    #endif
    //}

}

