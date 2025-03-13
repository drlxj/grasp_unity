using Assets.Oculus.VR.Editor;
using Oculus.Interaction.DebugTree;
using Oculus.Interaction.HandGrab;
using System;
using System.IO;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using System.Linq;
using UnityEngine.UI;

[DefaultExecutionOrder(100)]
public class SimpleTestManager : MonoBehaviour
{
    [HideInInspector]
    public GameObject[] Objects;


    //public GameObject ObjectSet;
    //public GameObject BaseObject;    

    public DistanceHandGrabInteractor interactor;
    public Material glowMaterial;
    public GameObject progressBarPrefab;
    private List<Slider> progressBars = new List<Slider>();
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
        start_timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss.fff");
    }

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

// TODO: the object doesn't return to the original place -> change control scene with less objects
// TODO: check out-of reach grasping with long distance 
    void Start()
    {
        Objects = this.GetComponent<TrackData>().Objects;

        // FisherYatesShuffle(Objects);

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

        //CreateOrUpdateProgressBar();

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

    private void CreateOrUpdateProgressBar()
    {
        if (!progressBars.Any())
        {

            foreach (var scoreEntry in interactor.candidateScores.Skip(1))
            {
                var parts = scoreEntry.Split(new char[] { ' ' }, System.StringSplitOptions.RemoveEmptyEntries);

                if (parts.Length >= 5)
                {
                    string name = parts[0];
                    float finalScoreCandidateScores = float.Parse(parts[4]);

                    GameObject sliderObject = Instantiate(progressBarPrefab, ScoreText.transform);
                    Slider progressBar = sliderObject.GetComponent<Slider>();

                    progressBar.minValue = 0.0f;
                    progressBar.maxValue = 1.0f;
                    progressBar.value = finalScoreCandidateScores;

                    RectTransform sliderRectTransform = sliderObject.GetComponent<RectTransform>();

                    sliderRectTransform.sizeDelta = new Vector2(200, 25);

                    GameObject scoreTextObject = new GameObject("ScoreText", typeof(TextMeshProUGUI));
                    scoreTextObject.transform.SetParent(sliderObject.transform, false);
                    TextMeshProUGUI scoreText = scoreTextObject.GetComponent<TextMeshProUGUI>();
                    scoreText.text = $"{name}: {finalScoreCandidateScores:F2}";
                    scoreText.fontSize = 10;
                    scoreText.alignment = TextAlignmentOptions.Center;
                    RectTransform scoreTextRectTransform = scoreTextObject.GetComponent<RectTransform>();
                    scoreTextRectTransform.anchoredPosition = new Vector2(0, 10);
                    scoreTextRectTransform.sizeDelta = new Vector2(100, 20);

                    progressBars.Add(progressBar);

                }
            }
        }
        else {
            int index = 0;

            foreach (var scoreEntry in interactor.candidateScores.Skip(1))
            {
                var parts = scoreEntry.Split(new char[] { ' ' }, System.StringSplitOptions.RemoveEmptyEntries);

                if (parts.Length >= 5)
                {
                    string name = parts[0];
                    float finalScoreCandidateScores = float.Parse(parts[4]);

                    Slider progressBar = progressBars[index];
                    progressBar.value = finalScoreCandidateScores;

                    Transform scoreTextObject = progressBar.transform.Find("ScoreText");
                    if (scoreTextObject != null)
                    {
                        TextMeshProUGUI scoreText = scoreTextObject.GetComponent<TextMeshProUGUI>();
                        scoreText.text = $"{name}: {finalScoreCandidateScores:F2}";
                    }

                    index++;
                }

                
            }

        }
    }

    //public void UpdateProgressBar(float value)
    //{
    //    if (progressBar != null)
    //    {
    //        progressBar.value = value;
    //    }
    //}

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
        //ScoreText.text = string.Join("\n", interactor.candidateScores);
        CreateOrUpdateProgressBar();
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
    
    public AudioSource audioSource;

    public void CorrectGrasp()
    {
        
        if (audioSource != null)
        {
            audioSource.Play();
        }

        System.DateTime GraspingEndTime = System.DateTime.Now;

        Dictionary<string, (float, float, float, float)> scoresDictionary = new Dictionary<string, (float, float, float, float)>();

        foreach (var scoreEntry in interactor.candidateScores.Skip(1))
        {
            var parts = scoreEntry.Split(new char[] { ' ' }, System.StringSplitOptions.RemoveEmptyEntries);

            Debug.Log($"Split result: {string.Join(", ", parts)}");

            if (parts.Length >= 5)
            {
                string name = parts[0];
                float gestureScoreCandidateScores = float.Parse(parts[1]);
                float posScoreCandidateScores = float.Parse(parts[2]);
                float gestureWeightCandidateScores = float.Parse(parts[3]);
                float finalScoreCandidateScores = float.Parse(parts[4]);

                scoresDictionary[name] = (gestureScoreCandidateScores, posScoreCandidateScores, gestureWeightCandidateScores, finalScoreCandidateScores);
            }
        }



        scoresDictionary.TryGetValue(TargetObjectName, out var scores);
    
        var (gestureScore, posScore, gestureWeight, finalScore) = scores;

        var data = new string[] {
            TargetObjectName,
            WrongGraspCount.ToString(),
            GraspingStartTime.ToString("yyyy-MM-dd HH:mm:ss.fff"),
            GraspingEndTime.ToString("yyyy-MM-dd HH:mm:ss.fff"),
            gestureScore.ToString(),
            posScore.ToString(),
            gestureWeight.ToString(),
            finalScore.ToString()
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
