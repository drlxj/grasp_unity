using Assets.Oculus.VR.Editor;
using Oculus.Interaction.DebugTree;
using Oculus.Interaction.HandGrab;
using System;
using System.IO;
using System.Collections.Generic;
using TMPro;
using UnityEngine;

[DefaultExecutionOrder(100)]
public class SimpleTestManager : MonoBehaviour
{
    [HideInInspector]
    public GameObject[] Objects;


    //public GameObject ObjectSet;
    //public GameObject BaseObject;    

    public DistanceHandGrabInteractor interactor;
    public Material glowMaterial;

    public Material originalMaterial;

    [HideInInspector]
    public DistanceHandGrabInteractable Target;

    public string UserName;
    //private int ObjectInScene = 4;
    //public int BlockSize = 1;

    [Tooltip("For Each Character's meaning, check line 13-23 in Session.cs")]
    public char SessionType = 'N';

    public GameObject CounterUI;
    private TextMeshProUGUI CounterText;
    public GameObject ScoreUI;
    public TextMeshProUGUI ScoreText;
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
    private System.DateTime GraspingEndTime;

    private void Awake()
    {
        start_timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
    }

// TODO: the object doesn't return to the original place -> change control scene with less objects
// TODO: check out-of reach grasping with long distance 
    void Start()
    {
        Objects = this.GetComponent<TrackData>().Objects;

        foreach (var obj in Objects)
        {
            if (obj != null)
            {
                initialTransforms[obj] = (obj.transform.position, obj.transform.rotation);

                // Debug.Log($"obj.transform.rotation:  {obj.transform.rotation}"); 
                // PrintMeshVertices(obj);

            }
        }


        //if (ObjectInScene > Objects.Length)
        //{
        //    Debug.LogError("Not Enough Objects");
        //}

        CounterText = CounterUI.GetComponentInChildren<TextMeshProUGUI>();
        //string Counter = $"{TrialIndex}/{BlockSize}";
        //CounterText.text = Counter;

        ScoreText = ScoreUI.GetComponentInChildren<TextMeshProUGUI>();
        ScoreText.text = "";

        SetConfig();
        //BlockData =  new BlockDataPackage(Objects, ObjectInScene, BlockSize);
        TrialIndex = 0;

        //Debug.Log($"There are {ObjectInScene} objects in the scene at each time");


        interactor.UserID = UserName;
        interactor.OnSelectTrue += HandleSelectTrue;
        interactor.OnSelectFalse += HandleSelectFalse;
        interactor.OnSelectEnd += HandleSelectEnd;
        interactor.OnSelectInterrupt += HandleSelectInterrupt;

        InvokeTest();
    }

    void PrintMeshVertices(GameObject obj)
    {
        Debug.Log($"PrintMeshVertice()");
        MeshFilter meshFilter = obj.transform.Find("default").GetComponent<MeshFilter>();
        if (meshFilter != null)
        {
            Mesh mesh = meshFilter.mesh;
            Vector3[] vertices = mesh.vertices;

            Debug.Log($"Vertices for {obj.name}:");
            foreach (Vector3 vertex in vertices)
            {
                Debug.Log(vertex);
            }
        }
        else
        {
            Debug.LogError($"No MeshFilter found on {obj.name}.");
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
            //interactor.LastObject.GetComponentInChildren<MeshRenderer>().sharedMaterial.SetFloat("_Highlighted", 0);
            Renderer currentRenderer = interactor.LastObject.transform.Find("default").GetComponent<MeshRenderer>();
            currentRenderer.sharedMaterial = originalMaterial;
        }

        //interactor.TargetObject.GetComponentInChildren<MeshRenderer>().sharedMaterial.SetFloat("_Highlighted", 1);
        Renderer nextRenderer = interactor.TargetObject.transform.Find("default").GetComponent<MeshRenderer>();
        nextRenderer.sharedMaterial = glowMaterial;
    }

    void Update(){
        ScoreText.text = string.Join("\n", interactor.candidateScores);
    }

    public void HandleSelectTrue(object sender, EventArgs e)
    {
        Debug.Log($"xxxx interactor.Target.id: {interactor.Target.ObjID}");
        // ResetObjects();
        // Update trial data
        CorrectGrasp();
    }

    public void HandleSelectFalse(object sender, EventArgs e)
    {   
        // ResetObjects();
        WrongGrasp();
    }

    public void HandleSelectEnd(object sender, EventArgs e)
    {   
        ResetObjects();
        //UpdateCandidate();
        ReHighlight();
        //interactor.ReHighlight();
        //Debug.Log($"ReHighlight called on: {interactor.TargetObject.name}");
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
        Debug.Log($"{UserName}'s Current session type: {SessionType}");
    }
   
    public void InvokeTest()
    {
        UpdateTarget();
        ReHighlight();
        //interactor.ReHighlight();
        //Debug.Log($"ReHighlight called on: {interactor.TargetObject.name}");
        //UpdateCandidate();
    }

    public void UpdateTarget()
    {   
        
        //UpdateCounter();
        //DistanceHandGrabInteractable target = BlockData.GetTarget(TrialIndex);
        GameObject currentObject = Objects[TrialIndex];
        TargetObjectName = currentObject.name;
        WrongGraspCount = 0;
        GraspingStartTime = System.DateTime.Now;
        Debug.Log($"GraspingStartTime: {GraspingStartTime.ToString("yyyy-MM-dd HH:mm:ss")}");
        DistanceHandGrabInteractable target = currentObject.GetComponentInChildren<DistanceHandGrabInteractable>();

        target.ObjID = TrialIndex + 1;

        interactor.TargetObject = target.GetGameObject();

        interactor.Target = target;
        Debug.Log($"target.ObjID: {target.ObjID}");
        //interactor.Target.ObjID = target.ObjID;
        interactor.ResetPerformance();
    }

    //public void UpdateCandidate()
    //{
    //    List<DistanceHandGrabInteractable> candidates = BlockData.GetCandidates(TrialIndex);
    //    if (Occlusion)
    //    {
    //        List<DistanceHandGrabInteractable> occlusionList = BlockData.GetOcclusionList(TrialIndex);
    //        // SetObjectPosition(candidates, occlusionList);
    //        // HideOtherObjects(candidates, occlusionList);
    //    } 
    //    else
    //    {
    //        // AssignCandidatePositions(candidates);
    //        // HideOtherObjects(candidates);
    //    }
        
    //}

    //public void UpdateCounter()
    //{
    //    string Counter = $"{TrialIndex}/{BlockSize}";
    //    CounterText.text = Counter;
    //}

    public void CorrectGrasp()
    {
        System.DateTime GraspingEndTime = System.DateTime.Now;
        var data = new string[] {
            TargetObjectName,
            WrongGraspCount.ToString(),
            GraspingStartTime.ToString("yyyy-MM-dd HH:mm:ss"),
            GraspingEndTime.ToString("yyyy-MM-dd HH:mm:ss")
        };

        
        string LogPath = $"../DistanceGrasp/Assets/LogData/GraspingData_{start_timestamp}_{SessionType}.csv";

        using (StreamWriter writer = new StreamWriter(LogPath, true))
        {
            writer.WriteLine(string.Join(",", data));
        }

        

        TrialIndex++;
        //Debug.Log($"xxxx TrialIndex: {TrialIndex}");
        //Debug.Log($"xxxx Objects.Length: {Objects.Length}");
        if (TrialIndex >= Objects.Length)
        {
            Debug.Log("xxxx if (TrialIndex >= Objects.Length)");
            //MetricsCalculator.ComputeMetrics(UserName);
            Debug.Log($"Quit()");
            Quit();
        }
        UpdateTarget();
        
    }

    public void WrongGrasp()
    {
        WrongGraspCount++;
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
