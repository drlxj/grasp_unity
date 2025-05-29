using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class TestOffset : MonoBehaviour
{
    public Transform targetObject;
    public OVRHand rightHand;
    public Transform wrist;
    private OVRSkeleton skeleton;  

    void Start(){
        skeleton = rightHand.GetComponent<OVRSkeleton>();
        if (skeleton == null)
        {
            Debug.LogError("OVRSkeleton not found on the right hand.");
        }
    }
    void Update()
    {
        wrist = skeleton.transform;
        if (wrist != null && targetObject != null)
        {
            // Calculate object position relative to the wrist
            Vector3 objectPositionRelativeToWrist = wrist.InverseTransformPoint(targetObject.position);
            
            // // Debugging: print wrist and target object positions
            // Debug.Log("Wrist position: " + wrist.position.ToString());
            // Debug.Log("Target object position: " + targetObject.position.ToString());
            // Debug.Log("Relative offset: " + objectPositionRelativeToWrist.ToString());
        }
        else
        {
            Debug.LogWarning("Wrist or target object is null.");
        }
    }
}
