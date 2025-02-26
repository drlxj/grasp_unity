using Assets.Oculus.VR.Editor;
using Oculus.Interaction.DebugTree;
using Oculus.Interaction.HandGrab;
using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;

public class ControlTaskManager : MonoBehaviour
{
    [HideInInspector]
    public GameObject[] Objects;
    public GameObject ObjectSet;
    public GameObject BaseObject;
    public GameObject GhostHand;
    public GameObject HandVisual;
    public DistanceHandGrabInteractor interactor;

    public string UserName;
    public int ObjectDisplayed = 25;
    public int BlockSize = 18;
    private int MatrixSize;

    public GameObject CounterUI;
    private TextMeshProUGUI CounterText;

    // TODO: remove sessiontype later, and session order and session index doesn't process all exp types
    private List<char> SessionOrder;
    public char SessionType = 'N';
    private int SessionIndex;
    private BlockDataPackage BlockData;
    private int BlockIndex;
    private int TrialIndex;

    private float CurrentDistance;
    private bool Occlusion;

    private void Awake()
    {
        interactor.GhostHand = this.GhostHand;
        interactor.HandVisual = this.HandVisual;
    }

    void Start()
    {
        Objects = this.GetComponent<TrackData>().Objects;
        if (ObjectDisplayed > Objects.Length)
        {
            Debug.LogError("Not Enough Objects");
        }

        CounterText = CounterUI.GetComponentInChildren<TextMeshProUGUI>();
        string Counter = $"{TrialIndex}/{BlockSize}";
        CounterText.text = Counter;

        SessionOrder = Session.GetConfigList();
        SessionIndex = 0;
        SetConfig();
        BlockData = this.GetComponent<DataGenerator>().ReadBlock();
        BlockIndex = 0;
        MatrixSize = (int)Math.Sqrt(ObjectDisplayed);

        Debug.Log($"There are {ObjectDisplayed} objects in the scene at each time");


        interactor.UserID = UserName;
        interactor.OnSelectTrue += HandleSelectTrue;
        interactor.OnSelectFalse += HandleSelectFalse;
        interactor.OnSelectEnd += HandleSelectEnd;
        interactor.OnSelectInterrupt += HandleSelectInterrupt;


        InvokeTest();
    }

    public void HandleSelectTrue(object sender, EventArgs e)
    {
        // Update the trial index and the target
        CorrectGrasp();
    }

    public void HandleSelectFalse(object sender, EventArgs e)
    {
        WrongGrasp();
    }

    public void HandleSelectEnd(object sender, EventArgs e)
    {
        // Update other objects and their positions only after the selection process is done
        UpdateCandidate();
        interactor.ReHighlight();
    }

    public void HandleSelectInterrupt(object sender, EventArgs e)
    {
        // Ignore
    }

    public void SetConfig()
    {
        // TODO: SessionOrder[SessionIndex] doesn't iterate all exp types
        // ExpConfig config = Session.GetExpConfig(SessionOrder[SessionIndex]);
        ExpConfig config = Session.GetExpConfig(SessionType);
        CurrentDistance = config.AngularDistance;
        Occlusion = config.Occlusion;
        interactor.GestureWeight = config.Weight;
        Debug.Log($"{UserName}'s Current session type: {SessionOrder[SessionIndex]}");
    }
   
    public void InvokeTest()
    {
        UpdateTarget();
        interactor.ReHighlight();
        UpdateCandidate();
    }

    public void UpdateTarget()
    {
        UpdateCounter();
        DistanceHandGrabInteractable target = BlockData.GetTarget(TrialIndex);
        interactor.TargetObject = target.GetGameObject();
        interactor.Target = target;
        interactor.ResetPerformance();
    }

    public void UpdateCandidate()
    {
        List<DistanceHandGrabInteractable> candidates = BlockData.GetCandidates(TrialIndex);
        if (Occlusion)
        {
            List<DistanceHandGrabInteractable> occlusionList = BlockData.GetOcclusionList(TrialIndex);
            SetObjectPosition(candidates, occlusionList);
            HideOtherObjects(candidates, occlusionList);
        } 
        else
        {
            AssignCandidatePositions(candidates);
            HideOtherObjects(candidates);
        }
        
    }

    public void UpdateCounter()
    {
        string Counter = $"{TrialIndex}/{BlockSize}";
        CounterText.text = Counter;
    }

    public void CorrectGrasp()
    {
        TrialIndex++;
        if (TrialIndex >= BlockSize) // User performance evaluation after a block is done
        {
            MetricsCalculator.ComputeMetrics(UserName);
            TrialIndex = 0;
            Quit();
            BlockIndex++;
            // TODO: why go to a new session, when block index is 3 -> correct it
            if (BlockIndex == 3)
            {
                BlockIndex = 0;
                BlockData.ReOrder();
                SessionIndex++;
                SetConfig();
                if (SessionIndex == SessionOrder.Count)
                {
                    Quit();
                }
            }
        }
        UpdateTarget();
    }

    public void WrongGrasp()
    {
        ;
    }

    public static void Quit()
    {
        #if UNITY_EDITOR
        UnityEditor.EditorApplication.isPlaying = false;
        #else
        Application.Quit();
        #endif
    }

    private List<Vector3> GenerateObjectPositions()
    {
        Vector3 verticalOffset = new Vector3(0, CurrentDistance, 0);
        Vector3 horizontalOffset = new Vector3(0, 0, CurrentDistance);
        Vector3 depth = new Vector3(0.15f, 0, 0);
        Vector3 basePosition = BaseObject.transform.position;

        List<Vector3> targetPosition = new();

        if (!Occlusion)
        {
            for (int i = 0; i < ObjectDisplayed / MatrixSize; i++)
            {
                for (int j = -MatrixSize / 2; j <= MatrixSize / 2; j++) // Generalize the horizontal placement
                {
                    targetPosition.Add(basePosition + j * horizontalOffset);
                }
                basePosition += verticalOffset; // Move to the next row
            }
        }
        else
        {
            for (int i = 0; i < ObjectDisplayed / MatrixSize; i++)
            {
                for (int j = -MatrixSize / 2; j <= MatrixSize / 2; j++)
                {
                    targetPosition.Add(basePosition + j * horizontalOffset);
                }
                basePosition += verticalOffset;
            }

            basePosition = BaseObject.transform.position;
            for (int i = 0; i < ObjectDisplayed / MatrixSize; i++)
            {
                for (int j = -MatrixSize / 2; j <= MatrixSize / 2; j++)
                {
                    targetPosition.Add(basePosition + j * horizontalOffset + ((j % 2 == 0) ? depth : -depth)); // Adjust with depth
                }
                basePosition += verticalOffset;
            }
        }

        return targetPosition;
    }

    private void AssignCandidatePositions(List<DistanceHandGrabInteractable> candidates)
    {
        List<Vector3> positionList = GenerateObjectPositions();
        for (int i = 0; i < candidates.Count; i++)
        {
            candidates[i].SetObjectPos(positionList[i]);
        }
    }


    private void SetObjectPosition(List<DistanceHandGrabInteractable> candidates, List<DistanceHandGrabInteractable> occlusionList)
    {
        List<Vector3> positionList = GenerateObjectPositions();
        for (int i = 0; i < candidates.Count; i++)
        {
            candidates[i].SetObjectPos(positionList[i]);
        }
        for (int i = 0; i < occlusionList.Count; i++)
        {
            occlusionList[i].SetObjectPos(positionList[i + ObjectDisplayed]);
        }
    }

    private void HideOtherObjects(List<DistanceHandGrabInteractable> candidates)
    {
        List<GameObject> candidateObjects = new();
        foreach (var candidate in candidates)
        {
            candidateObjects.Add(candidate.GetGameObject());
        }

        Vector3 hidePos = BaseObject.transform.position;
        hidePos.x = - hidePos.x;

        foreach (var obj in Objects)
        {
            if (candidateObjects.Contains(obj))
            {
                continue;
            }
            else
            {
                obj.transform.position = hidePos;
            }
        }
    }


    private void HideOtherObjects(List<DistanceHandGrabInteractable> candidates, List<DistanceHandGrabInteractable> occlusionList)
    {
        List<GameObject> candidateObjects = new();
        foreach (var candidate in candidates)
        {
            candidateObjects.Add(candidate.GetGameObject());
        }
        foreach (var occlusion in occlusionList)
        {
            candidateObjects.Add(occlusion.GetGameObject());
        }

        Vector3 hidePos = BaseObject.transform.position;
        hidePos.x = -hidePos.x;

        foreach (var obj in Objects)
        {
            if (candidateObjects.Contains(obj))
            {
                continue;
            }
            else
            {
                obj.transform.position = hidePos;
            }
        }
    }
}
