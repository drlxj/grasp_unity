using Oculus.Interaction.HandGrab;
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

public class ActionReceiver : MonoBehaviour
{
    [SerializeField]
    // private HandVisual currentHand;
    public DistanceHandGrabInteractor interactor;
    [Tooltip("The weight to decide the ratio of shape and position factors taken into consideration." +
        "\n1 means shape only and 0 means position only.")]
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


        Dictionary<string, float> gestureProbabilities = new();
        Dictionary<string, Vector3> relativePositions = new();


        for (int i = 0; i< latestMsg.objectCount; i++)
        {
            float gestureScore = latestMsg.confidenceScore[i];
            Vector3 position = latestMsg.objectPositions[i];
            int objTypesID = latestMsg.objTypesID[i];
            ObjectType objType = (ObjectType)objTypesID;
            string objectName = GetEnumName(objType);
            objectName = objectName.ToLower();

            gestureProbabilities[objectName] = gestureScore;
            relativePositions[objectName] = position;
        }
        if (latestMsg.objectCount != dataManager.Objects.Length)
        {
            Debug.LogError($"Object count mismatch: latestMsg.objectCount={latestMsg.objectCount}, dataManager.Objects.Length={dataManager.Objects.Length}.");
            return;
        }
        interactor.GestureProbabilityList = gestureProbabilities;
        interactor.RelativePosList = relativePositions;
        interactor.CurrentPacketId = (int)latestMsg.packetIdx;  // 设置当前packetId
              
    }

}
