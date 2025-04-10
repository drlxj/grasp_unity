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
    public GameObject progressBarPrefab;
    public GameObject posProgressBarPrefab;
    public GameObject gesProgressBarPrefab;
    private List<Slider> progressBars = new List<Slider>();
    private List<Slider> posProgressBars = new List<Slider>();
    private List<Slider> gesProgressBars = new List<Slider>();
    public Material originalMaterial;

    [Tooltip("For Each Character's meaning, check line 13-16 in Session.cs")]
    public string SessionTypes = "G";
    public GameObject CounterUI;
    public GameObject ScoreUI;
    public GameObject PosScoreUI;
    public GameObject GesScoreUI;
    public TextMeshProUGUI ScoreText;
    public TextMeshProUGUI posScoreText;
    public TextMeshProUGUI gesScoreText;
    private TextMeshProUGUI CounterText;
    [HideInInspector]
    private int TrialIndex;
    private bool Occlusion;
    private Dictionary<GameObject, (Vector3 position, Quaternion rotation)> initialTransforms = new Dictionary<GameObject, (Vector3, Quaternion)>();
    public string TargetObjectName;
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
        char SessionType = SessionTypes[0];

        PlayerPrefs.SetString("SessionType", SessionType.ToString());
        PlayerPrefs.Save();
        
        start_timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss.fff");

        CounterText = CounterUI.GetComponentInChildren<TextMeshProUGUI>();

        ScoreText = ScoreUI.GetComponentInChildren<TextMeshProUGUI>();

        posScoreText = PosScoreUI.GetComponentInChildren<TextMeshProUGUI>();

        gesScoreText = GesScoreUI.GetComponentInChildren<TextMeshProUGUI>();

        CreateOrUpdateProgressBar();
    }

// TODO: the object doesn't return to the original place -> change control scene with less objects
// TODO: check out-of reach grasping with long distance 
    private void Start()
    {        
        Objects = this.GetComponent<MiniDataCollectionTrackData>().Objects;

        foreach (var obj in Objects)
        {
            if (obj == null) continue;

            initialTransforms[obj] = (obj.transform.position, obj.transform.rotation);
        }

        TrialIndex = 0;
    }

    void Update()
    {   
        CreateOrUpdateProgressBar();
    }

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

    private void CreateOrUpdateProgressBar()
    {
        if (!progressBars.Any())
        {   

            foreach (var scoreEntry in interactor.candidateScores.Skip(1))
            {
                var parts = scoreEntry.Split(new char[] { ' ' }, System.StringSplitOptions.RemoveEmptyEntries);

                if (parts.Length >= 5)
                {   
                    // final score bars
                    string name = parts[0];
                    
                    float finalScoreCandidateScores = float.Parse(parts[4]);

                    GameObject sliderObject = Instantiate(progressBarPrefab, ScoreText.transform);
                    Slider progressBar = sliderObject.GetComponent<Slider>();

                    progressBar.minValue = 0.0f;
                    progressBar.maxValue = 1.0f;
                    progressBar.value = finalScoreCandidateScores;

                    GameObject scoreTextObject = new GameObject("ScoreText", typeof(TextMeshProUGUI));
                    scoreTextObject.transform.SetParent(sliderObject.transform, false);
                    TextMeshProUGUI scoreText = scoreTextObject.GetComponent<TextMeshProUGUI>();
                    scoreText.text = $"{name}: {finalScoreCandidateScores:F2}";

                    // \nG: {gestureScoreCandidateScores}, P: {posScoreCandidateScores}

                    scoreText.fontSize = 7;
                    scoreText.color = new Color32(139, 0, 0, 255);
                    scoreText.alignment = TextAlignmentOptions.Center;
                    RectTransform scoreTextRectTransform = scoreTextObject.GetComponent<RectTransform>();
                    scoreTextRectTransform.anchoredPosition = new Vector2(0, 8);
                    scoreTextRectTransform.sizeDelta = new Vector2(100, 20);

                    progressBars.Add(progressBar);

                    // gesture score bars
                    float gestureScoreCandidateScores = float.Parse(parts[1]);

                    GameObject gesSliderObject = Instantiate(gesProgressBarPrefab, gesScoreText.transform);
                    Slider gesProgressBar = gesSliderObject.GetComponent<Slider>();

                    gesProgressBar.minValue = 0.0f;
                    gesProgressBar.maxValue = 1.0f;
                    gesProgressBar.value = gestureScoreCandidateScores;

                    GameObject scoreTextObjectGes = new GameObject("ScoreText", typeof(TextMeshProUGUI));
                    scoreTextObjectGes.transform.SetParent(gesSliderObject.transform, false);
                    TextMeshProUGUI scoreTextGes = scoreTextObjectGes.GetComponent<TextMeshProUGUI>();
                    scoreTextGes.text = $"{name}: {gestureScoreCandidateScores:F2}";

                    scoreTextGes.fontSize = 7;
                    scoreTextGes.color = new Color32(0, 0, 139, 255);
                    scoreTextGes.alignment = TextAlignmentOptions.Center;
                    RectTransform scoreTextRectTransformGes = scoreTextObjectGes.GetComponent<RectTransform>();
                    scoreTextRectTransformGes.anchoredPosition = new Vector2(0, 8);
                    scoreTextRectTransformGes.sizeDelta = new Vector2(100, 20);

                    gesProgressBars.Add(gesProgressBar);

                    // position score bars
                    float posScoreCandidateScores = float.Parse(parts[2]);

                    GameObject posSliderObject = Instantiate(posProgressBarPrefab, posScoreText.transform);
                    Slider posProgressBar = posSliderObject.GetComponent<Slider>();

                    posProgressBar.minValue = 0.0f;
                    posProgressBar.maxValue = 1.0f;
                    posProgressBar.value = posScoreCandidateScores;

                    GameObject scoreTextObjectPos= new GameObject("ScoreText", typeof(TextMeshProUGUI));
                    scoreTextObjectPos.transform.SetParent(posSliderObject.transform, false);
                    TextMeshProUGUI scoreTextPos = scoreTextObjectPos.GetComponent<TextMeshProUGUI>();
                    scoreTextPos.text = $"{name}: {posScoreCandidateScores:F2}";

                    scoreTextPos.fontSize = 7;
                    scoreTextPos.color = new Color32(0, 139, 0, 255);
                    scoreTextPos.alignment = TextAlignmentOptions.Center;
                    RectTransform scoreTextRectTransformPos = scoreTextObjectPos.GetComponent<RectTransform>();
                    scoreTextRectTransformPos.anchoredPosition = new Vector2(0, 8);
                    scoreTextRectTransformPos.sizeDelta = new Vector2(100, 20);

                    posProgressBars.Add(posProgressBar);

                }
            }
        }
        else 
        {
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


                    float gestureScoreCandidateScores = float.Parse(parts[1]);
                    Slider gesProgressBar = gesProgressBars[index];
                    gesProgressBar.value = gestureScoreCandidateScores;

                    Transform scoreTextObjectGes = gesProgressBar.transform.Find("ScoreText");
                    if (scoreTextObjectGes != null)
                    {
                        TextMeshProUGUI scoreTextGes = scoreTextObjectGes.GetComponent<TextMeshProUGUI>();
                        scoreTextGes.text = $"{name}: {gestureScoreCandidateScores:F2}";
                    }

                    float posScoreCandidateScores = float.Parse(parts[2]);
                    Slider posProgressBar = posProgressBars[index];
                    posProgressBar.value = posScoreCandidateScores;

                    Transform scoreTextObjectPos = posProgressBar.transform.Find("ScoreText");
                    if (scoreTextObjectPos != null)
                    {
                        TextMeshProUGUI scoreTextPos = scoreTextObjectPos.GetComponent<TextMeshProUGUI>();
                        scoreTextPos.text = $"{name}: {posScoreCandidateScores:F2}";
                    }


                    index++;
                }
            }

        }
    }

}

