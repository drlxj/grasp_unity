using System.Collections;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using System.Linq;

public class UIManager : MonoBehaviour
{
    [Header("UI References")]
    [SerializeField] private GameObject counterUI;
    [SerializeField] private GameObject scoreUI;
    [SerializeField] private GameObject posScoreUI;
    [SerializeField] private GameObject gesScoreUI;
    
    [Header("Progress Bar Prefabs")]
    [SerializeField] private GameObject progressBarPrefab;
    [SerializeField] private GameObject posProgressBarPrefab;
    [SerializeField] private GameObject gesProgressBarPrefab;

    private TextMeshProUGUI counterText;
    private TextMeshProUGUI scoreText;
    private TextMeshProUGUI posScoreText;
    private TextMeshProUGUI gesScoreText;
    
    private List<Slider> progressBars = new List<Slider>();
    private List<Slider> posProgressBars = new List<Slider>();
    private List<Slider> gesProgressBars = new List<Slider>();

    private void Awake()
    {
        InitializeUIComponents();
    }

    private void InitializeUIComponents()
    {
        if (counterUI != null)
            counterText = counterUI.GetComponentInChildren<TextMeshProUGUI>();
        if (scoreUI != null)
            scoreText = scoreUI.GetComponentInChildren<TextMeshProUGUI>();
        if (posScoreUI != null)
            posScoreText = posScoreUI.GetComponentInChildren<TextMeshProUGUI>();
        if (gesScoreUI != null)
            gesScoreText = gesScoreUI.GetComponentInChildren<TextMeshProUGUI>();
            
        Debug.Log($"UI Components initialized - Counter: {counterText != null}, Score: {scoreText != null}, PosScore: {posScoreText != null}, GesScore: {gesScoreText != null}");
    }

    public IEnumerator CountDown(char sessionType, System.Action onCountDownComplete = null)
    {
        for (int i = 6; i > 0; i--)
        {
            if (counterText != null)
            {
                counterText.text = $"Next Session: {sessionType}\nStarting in {i}...";
                counterText.color = Color.yellow;
            }
            yield return new WaitForSeconds(1);
        }

        if (counterText != null)
        {
            counterText.text = "Go!";
            counterText.color = Color.red;
        }
        yield return new WaitForSeconds(1);

        if (counterText != null)
        {
            counterText.text = "";
            counterText.color = Color.white;
        }
        
        onCountDownComplete?.Invoke();
    }

    public void UpdateTimeRemaining(int seconds)
    {
        if (counterText != null)
        {
            counterText.text = $"Time Left: {seconds}s";
        }
    }

    public void CreateOrUpdateProgressBars(List<string> candidateScores)
    {
        if (candidateScores == null || candidateScores.Count == 0)
        {
            return;
        }
        
        if (!progressBars.Any())
        {
            CreateProgressBars(candidateScores);
        }
        else
        {
            UpdateProgressBars(candidateScores);
        }
    }

    private void CreateProgressBars(List<string> candidateScores)
    {
        // Check if prefabs are assigned
        if (progressBarPrefab == null)
        {
            Debug.LogError("progressBarPrefab is not assigned!");
            return;
        }
        if (posProgressBarPrefab == null)
        {
            Debug.LogError("posProgressBarPrefab is not assigned!");
            return;
        }
        if (gesProgressBarPrefab == null)
        {
            Debug.LogError("gesProgressBarPrefab is not assigned!");
            return;
        }
        
        foreach (var scoreEntry in candidateScores.Skip(1))
        {
            var parts = scoreEntry.Split(new char[] { ' ' }, System.StringSplitOptions.RemoveEmptyEntries);

            if (parts.Length >= 5)
            {
                CreateFinalScoreBar(parts);
                CreateGestureScoreBar(parts);
                CreatePositionScoreBar(parts);
            }
        }
    }

    private void CreateFinalScoreBar(string[] parts)
    {
        if (scoreText == null) return;
        
        string name = parts[0];
        float finalScore = float.Parse(parts[4]);

        GameObject sliderObject = Instantiate(progressBarPrefab, scoreText.transform);
        Slider progressBar = sliderObject.GetComponent<Slider>();

        progressBar.minValue = 0.0f;
        progressBar.maxValue = 1.0f;
        progressBar.value = finalScore;

        CreateScoreText(sliderObject, name, finalScore, new Color32(139, 0, 0, 255));
        progressBars.Add(progressBar);
    }

    private void CreateGestureScoreBar(string[] parts)
    {
        if (gesScoreText == null) return;
        
        string name = parts[0];
        float gestureScore = float.Parse(parts[1]);

        GameObject gesSliderObject = Instantiate(gesProgressBarPrefab, gesScoreText.transform);
        Slider gesProgressBar = gesSliderObject.GetComponent<Slider>();

        gesProgressBar.minValue = 0.0f;
        gesProgressBar.maxValue = 1.0f;
        gesProgressBar.value = gestureScore;

        CreateScoreText(gesSliderObject, name, gestureScore, new Color32(0, 0, 139, 255));
        gesProgressBars.Add(gesProgressBar);
    }

    private void CreatePositionScoreBar(string[] parts)
    {
        if (posScoreText == null) return;
        
        string name = parts[0];
        float posScore = float.Parse(parts[2]);

        GameObject posSliderObject = Instantiate(posProgressBarPrefab, posScoreText.transform);
        Slider posProgressBar = posSliderObject.GetComponent<Slider>();

        posProgressBar.minValue = 0.0f;
        posProgressBar.maxValue = 1.0f;
        posProgressBar.value = posScore;

        CreateScoreText(posSliderObject, name, posScore, new Color32(0, 139, 0, 255));
        posProgressBars.Add(posProgressBar);
    }

    private void CreateScoreText(GameObject parent, string name, float score, Color color)
    {
        GameObject scoreTextObject = new GameObject("ScoreText", typeof(TextMeshProUGUI));
        scoreTextObject.transform.SetParent(parent.transform, false);
        TextMeshProUGUI scoreTextComponent = scoreTextObject.GetComponent<TextMeshProUGUI>();
        scoreTextComponent.text = $"{name}: {score:F2}";
        scoreTextComponent.fontSize = 7;
        scoreTextComponent.color = color;
        scoreTextComponent.alignment = TextAlignmentOptions.Center;
        
        RectTransform scoreTextRectTransform = scoreTextObject.GetComponent<RectTransform>();
        scoreTextRectTransform.anchoredPosition = new Vector2(0, 8);
        scoreTextRectTransform.sizeDelta = new Vector2(100, 20);
    }

    private void UpdateProgressBars(List<string> candidateScores)
    {
        int index = 0;

        foreach (var scoreEntry in candidateScores.Skip(1))
        {
            var parts = scoreEntry.Split(new char[] { ' ' }, System.StringSplitOptions.RemoveEmptyEntries);

            if (parts.Length >= 5 && index < progressBars.Count)
            {
                string name = parts[0];
                float finalScore = float.Parse(parts[4]);
                float gestureScore = float.Parse(parts[1]);
                float posScore = float.Parse(parts[2]);

                UpdateProgressBar(progressBars[index], name, finalScore);
                UpdateProgressBar(gesProgressBars[index], name, gestureScore);
                UpdateProgressBar(posProgressBars[index], name, posScore);

                index++;
            }
        }
    }

    private void UpdateProgressBar(Slider progressBar, string name, float score)
    {
        if (progressBar == null) return;
        
        progressBar.value = score;
        Transform scoreTextObject = progressBar.transform.Find("ScoreText");
        if (scoreTextObject != null)
        {
            TextMeshProUGUI scoreText = scoreTextObject.GetComponent<TextMeshProUGUI>();
            if (scoreText != null)
            {
                scoreText.text = $"{name}: {score:F2}";
            }
        }
    }

    public void ClearProgressBars()
    {
        foreach (var bar in progressBars)
        {
            if (bar != null) Destroy(bar.gameObject);
        }
        foreach (var bar in posProgressBars)
        {
            if (bar != null) Destroy(bar.gameObject);
        }
        foreach (var bar in gesProgressBars)
        {
            if (bar != null) Destroy(bar.gameObject);
        }
        
        progressBars.Clear();
        posProgressBars.Clear();
        gesProgressBars.Clear();
    }
    
    // Test method to manually set candidate scores for debugging
    [ContextMenu("Test Progress Bars")]
    public void TestProgressBars()
    {
        var testScores = new List<string>
        {
            "Name            Gesture    Pos     Weight   Final",
            "apple           0.8500   0.7500   0.50    0.8000",
            "banana          0.6500   0.8500   0.50    0.7500",
            "mug             0.4500   0.9500   0.50    0.7000"
        };
        
        CreateOrUpdateProgressBars(testScores);
        Debug.Log("Test data set for progress bars");
    }
}
