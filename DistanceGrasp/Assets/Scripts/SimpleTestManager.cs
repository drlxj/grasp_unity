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
public class SimpleTestManager : MonoBehaviour
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
    public int timeLimit = 7;

    [HideInInspector]
    public DistanceHandGrabInteractable Target;

    public string UserName;

    [Tooltip("For Each Character's meaning, check line 13-16 in Session.cs")]
    public string SessionTypes = "PC";
    private int SessionTypeIndex = 0;
    private int SessionTypeCount;
    private char SessionType;
    public GameObject CounterUI;
    private TextMeshProUGUI CounterText;
    public GameObject ScoreUI;
    public GameObject PosScoreUI;
    public GameObject GesScoreUI;
    public TextMeshProUGUI ScoreText;
    public TextMeshProUGUI posScoreText;
    public TextMeshProUGUI gesScoreText;
    [HideInInspector]
    private int TrialIndex;
    private BlockDataPackage BlockData;
    private Dictionary<GameObject, (Vector3 position, Quaternion rotation)> initialTransforms = new Dictionary<GameObject, (Vector3, Quaternion)>();
    private int WrongGraspCount;
    private string TargetObjectName;
    private string SelectedObjectName;
    private System.DateTime GraspingStartTime;
    private System.DateTime GraspingLimitedTime;
    private System.DateTime GraspingEndTime;
    public AudioSource audioSource;
    private bool isCountingDown = false;
    
    private UserStudyDataRecorder dataRecorder;
    private int currentPacketId = 0;

    private void Awake()
    {
        SessionTypeCount = SessionTypes.Length;

        interactor.UserID = UserName;
        interactor.OnSelectTrue += HandleSelectTrue;
        interactor.OnSelectFalse += HandleSelectFalse;
        interactor.OnSelectEnd += HandleSelectEnd;
        interactor.OnSelectInterrupt += HandleSelectInterrupt;

        CounterText = CounterUI.GetComponentInChildren<TextMeshProUGUI>();
        ScoreText = ScoreUI.GetComponentInChildren<TextMeshProUGUI>();
        posScoreText = PosScoreUI.GetComponentInChildren<TextMeshProUGUI>();
        gesScoreText = GesScoreUI.GetComponentInChildren<TextMeshProUGUI>();

        dataRecorder = UserStudyDataRecorder.Instance;
        
        TrackData.OnTelemetryDataSent += OnTelemetryDataSent;
    }
    
    private void OnTelemetryDataSent(int packetId)
    {
        currentPacketId = packetId;
        Debug.Log($"Received packetId: {packetId}");
    }
    

    private IEnumerator Start()
    {   
        SessionType = SessionTypes[SessionTypeIndex];
        
        yield return StartCoroutine(CountDown());

        SessionTypeIndex++;
        
        PlayerPrefs.SetString("SessionType", SessionType.ToString());
        PlayerPrefs.Save();
        SetConfig();
        
        Objects = this.GetComponent<TrackData>().Objects;
        foreach (var obj in Objects)
        {
            if (obj == null) continue;
            initialTransforms[obj] = (obj.transform.position, obj.transform.rotation);
        }

        Session session = FindObjectOfType<Session>();
        string prefabFolderName = session.prefabFolderName;
        float angleStep = session.angleStep;
        dataRecorder.InitializeExperiment(UserName, SessionType.ToString(), timeLimit, prefabFolderName, angleStep);
        dataRecorder.RecordObjectInitialization(Objects);

        // 清空之前的 trial 数据，开始新的 session
        dataRecorder.ClearTrialData();

        TrialIndex = 0;
        InvokeTest();
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
        CreateOrUpdateProgressBar();
        checkGraspingTimeLimit();
    }

    private void checkGraspingTimeLimit()
    {
        TimeSpan remainingTime = GraspingLimitedTime - DateTime.Now;

        if (remainingTime.TotalSeconds <= 0)
        {
            // Time is up, handle the timeout case here
            // 9: Timeout
            dataRecorder.RecordGraspResultWithScores(SelectedObjectName, "timeout", 
                (float)(DateTime.Now - GraspingStartTime).TotalSeconds, currentPacketId-1);
            
            interactor.LastObject = interactor.TargetObject;

            CompleteCurrentTrial(false);
            ReHighlight();
            return;
        }

        CounterText.text = $"Time Left: {remainingTime.Seconds}s";
    }

    public void HandleSelectTrue(object sender, EventArgs e)
    {   
        // correctGestureFlag: 
        // 1: correct grasp
        dataRecorder.RecordGraspResultWithScores(SelectedObjectName, "success", 
            (float)(DateTime.Now - GraspingStartTime).TotalSeconds, currentPacketId-1);
        CompleteCurrentTrial(true);
    }

    public void HandleSelectFalse(object sender, EventArgs e)
    {   
        // correctGestureFlag: 
        // 0: wrong grasp
        dataRecorder.RecordGraspResultWithScores(SelectedObjectName, "wrong_object", 
            (float)(DateTime.Now - GraspingStartTime).TotalSeconds, currentPacketId-1);
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
        interactor.MethodID = config.MethodID;
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
        dataRecorder.StartNewTrial(TrialIndex, TargetObjectName);

        Debug.Log($"UpdateTarget: {TargetObjectName}");
    }
    


    public void CompleteCurrentTrial(bool isSuccessful)
    {

        dataRecorder.CompleteTrial(isSuccessful, WrongGraspCount, (float)(DateTime.Now - GraspingStartTime).TotalSeconds);

        if (audioSource != null)
        {
            audioSource.Play();
        }

        TrialIndex++;
        if (TrialIndex >= Objects.Length)
        {
            if (SessionTypeIndex >= SessionTypeCount)
            {
                // If all sessions are finished, quit the application
                Quit();
            }
            else
            {
                // 当前session结束，保存数据
                dataRecorder.SaveDataToFiles();
                
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

    private IEnumerator CountDown()
    {   
        isCountingDown = true; 
        // char nextSessionType = SessionTypes[SessionTypeIndex];
        interactor.enabled = false;

        for (int i = 6; i > 0; i--)
        {
            CounterText.text = $"Next Session: {SessionType}\nStarting in {i}...";
            CounterText.color = Color.yellow; 
            yield return new WaitForSeconds(1);
        }

        CounterText.text = "Go!";
        CounterText.color = Color.red;
        yield return new WaitForSeconds(1); 

        CounterText.text = "";

        interactor.enabled = true;
        CounterText.color = Color.white;
        isCountingDown = false;
    }

    private void CreateOrUpdateProgressBar()
    {
        if (!progressBars.Any())
        {   
            // 解析分数并保存到 UserStudyDataRecorder
            Dictionary<string, float> gestureScores = new Dictionary<string, float>();
            Dictionary<string, float> positionScores = new Dictionary<string, float>();
            Dictionary<string, float> finalScores = new Dictionary<string, float>();
            
            foreach (var scoreEntry in interactor.candidateScores.Skip(1))
            {
                var parts = scoreEntry.Split(new char[] { ' ' }, System.StringSplitOptions.RemoveEmptyEntries);

                if (parts.Length >= 6)  // 现在有6列：PacketID, Name, Gesture, Pos, Weight, Final
                {   
                    // final score bars
                    string name = parts[1];  // 第1列是Name（跳过第0列PacketID）
                    
                    float finalScoreCandidateScores = float.Parse(parts[5]);  // 第5列是Final

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
                    float gestureScoreCandidateScores = float.Parse(parts[2]);  // 第2列是Gesture

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
                    float posScoreCandidateScores = float.Parse(parts[3]);  // 第3列是Pos

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
                    
                    // 保存分数到字典中
                    gestureScores[name] = gestureScoreCandidateScores;
                    positionScores[name] = posScoreCandidateScores;
                    finalScores[name] = finalScoreCandidateScores;

                }
            }
            
            // 保存分数到 UserStudyDataRecorder
            if (dataRecorder != null && currentPacketId > 0)
            {
                dataRecorder.CacheScoreData(currentPacketId, gestureScores, positionScores, finalScores);
                Debug.Log($"Saved scores to UserStudyDataRecorder for packetId: {currentPacketId}");
            }
        }
        else 
        {
            // 更新现有进度条并保存分数
            int index = 0;
            Dictionary<string, float> gestureScores = new Dictionary<string, float>();
            Dictionary<string, float> positionScores = new Dictionary<string, float>();
            Dictionary<string, float> finalScores = new Dictionary<string, float>();

            foreach (var scoreEntry in interactor.candidateScores.Skip(1))
            {
                var parts = scoreEntry.Split(new char[] { ' ' }, System.StringSplitOptions.RemoveEmptyEntries);

                if (parts.Length >= 6)  // 现在有6列：PacketID, Name, Gesture, Pos, Weight, Final
                {
                    string name = parts[1];  // 第1列是Name（跳过第0列PacketID）
                    
                    float finalScoreCandidateScores = float.Parse(parts[5]);  // 第5列是Final
                    Slider progressBar = progressBars[index];
                    progressBar.value = finalScoreCandidateScores;

                    Transform scoreTextObject = progressBar.transform.Find("ScoreText");
                    if (scoreTextObject != null)
                    {
                        TextMeshProUGUI scoreText = scoreTextObject.GetComponent<TextMeshProUGUI>();
                        scoreText.text = $"{name}: {finalScoreCandidateScores:F2}";
                    }

                    float gestureScoreCandidateScores = float.Parse(parts[2]);  // 第2列是Gesture
                    Slider gesProgressBar = gesProgressBars[index];
                    gesProgressBar.value = gestureScoreCandidateScores;

                    Transform scoreTextObjectGes = gesProgressBar.transform.Find("ScoreText");
                    if (scoreTextObjectGes != null)
                    {
                        TextMeshProUGUI scoreTextGes = scoreTextObjectGes.GetComponent<TextMeshProUGUI>();
                        scoreTextGes.text = $"{name}: {gestureScoreCandidateScores:F2}";
                    }

                    float posScoreCandidateScores = float.Parse(parts[3]);  // 第3列是Pos
                    Slider posProgressBar = posProgressBars[index];
                    posProgressBar.value = posScoreCandidateScores;

                    Transform scoreTextObjectPos = posProgressBar.transform.Find("ScoreText");
                    if (scoreTextObjectPos != null)
                    {
                        TextMeshProUGUI scoreTextPos = scoreTextObjectPos.GetComponent<TextMeshProUGUI>();
                        scoreTextPos.text = $"{name}: {posScoreCandidateScores:F2}";
                    }

                    // 保存分数到字典中
                    gestureScores[name] = gestureScoreCandidateScores;
                    positionScores[name] = posScoreCandidateScores;
                    finalScores[name] = finalScoreCandidateScores;

                    index++;
                }
            }
            
            // 保存分数到 UserStudyDataRecorder
            if (dataRecorder != null && currentPacketId > 0)
            {
                dataRecorder.CacheScoreData(currentPacketId, gestureScores, positionScores, finalScores);
                Debug.Log($"Updated scores in UserStudyDataRecorder for packetId: {currentPacketId}");
            }
        }
    }

    


    private void OnDestroy()
    {
        // 取消订阅事件
        TrackData.OnTelemetryDataSent -= OnTelemetryDataSent;
    }
    
    public static void Quit()
    {   
        // 保存实验数据
        if (UserStudyDataRecorder.Instance != null)
        {
            UserStudyDataRecorder.Instance.SaveDataToFiles();
        }
        
        #if UNITY_EDITOR
        UnityEditor.EditorApplication.isPlaying = false;
        #else
        Application.Quit();
        #endif
    }

}

