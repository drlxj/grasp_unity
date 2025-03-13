using Oculus.Interaction.HandGrab;
using System;
using System.Collections.Generic;
using UnityEngine;

public class ActionReceiver : MonoBehaviour
{
    [SerializeField]
    // private HandVisual currentHand;
    public DistanceHandGrabInteractor interactor;
    [Tooltip("The weight to decide the ratio of shape and position factors taken into consideration." +
        "\n1 means shape only and 0 means position only.")]
    [Range (0f, 1f)]
    public float gestureWeight = 0.5f;
    [Tooltip("This value serves as a shape matching threshold, " +
        "with values above the threshold indicating a successful match.")]
    [Range(0f, 1f)]
    public float confidenceThreshold = 0.8f;
    public bool DebugSwitch;
    private static CommandMessage latestMsg = null;

    private static readonly Lazy<Dictionary<ObjectType, string>> _enumNameCache =
        new(() =>
        {
            var dict = new Dictionary<ObjectType, string>();
            foreach (ObjectType type in Enum.GetValues(typeof(ObjectType)))
            {
                dict[type] = type.ToString();
            }
            return dict;
        });


    TrackData dataManager;
    void Awake()
    {
        interactor.GestureWeight = gestureWeight;
        this.interactor.DebugSwitch = DebugSwitch;
    }

    // Start is called before the first frame update
    void Start()
    {
        dataManager = FindObjectOfType<TrackData>();
        if (dataManager == null )
        {
            Debug.LogError("Cannot find the Data Manager");
        }
    }

    // Update is called once per frame
    void Update()
    {

    }

    public static string GetEnumName(ObjectType objType)
    {
        return _enumNameCache.Value.TryGetValue(objType, out string name) ? name : "Unknown";
    }

    public void GetMostProbableObjIdx(byte[] data)
    {
        latestMsg = new CommandMessage(data);

        float maxScore = float.NegativeInfinity;
        int maxIdx = -1;

        Dictionary<string, float> gestureProbabilities = new();
        Dictionary<string, Vector3> relativePositions = new();


        for (int i = 0; i< latestMsg.objectCount; i++)
        {
            // string objectName = dataManager.objNames[i];
            float confidence = latestMsg.confidenceScore[i];
            int objTypesID = latestMsg.objTypesID[i];
            ObjectType objType = (ObjectType)objTypesID;
            string objectName = GetEnumName(objType);
            objectName = objectName.ToLower();

            Vector3 position = latestMsg.objectPositions[i];

            gestureProbabilities[objectName] = confidence;
            relativePositions[objectName] = position;

            if (confidence > maxScore && confidence > confidenceThreshold){
                maxIdx = i;
                maxScore = confidence;
            }
        }
        if (maxIdx < 0)
        {
            interactor.IsGestureProbability = false; 
            interactor.GestureProbabilityList = new Dictionary<string, float>();
            interactor.RelativePosList = new Dictionary<string, Vector3>();
            Debug.Log("No max score found now.");
        }  
        if (maxIdx >= dataManager.Objects.Length)
        {
            Debug.LogError("Index out of bounds in object detection.");
            return;
        }
        interactor.GestureProbabilityList = gestureProbabilities;
        interactor.RelativePosList = relativePositions;        
    }

}
