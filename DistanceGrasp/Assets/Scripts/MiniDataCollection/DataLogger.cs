using System;
using System.Collections.Generic;
using UnityEngine;
using Oculus.Interaction;

[Serializable]
public class PoseArray
{
    public List<float[]> position = new();
    public List<float[]> rotation = new();

    public void Add(Vector3 pos, Quaternion rot)
    {
        position.Add(new float[] { pos.x, pos.y, pos.z });
        rotation.Add(new float[] { rot.x, rot.y, rot.z, rot.w });
    }
}

[Serializable]
public class Gesture
{
    public static readonly List<int> IndexMapping = new()
    {
        0,              // root 
        3, 4, 5, 19,    // thumb
        6, 7, 8, 20,    // index
        9, 10, 11, 21,  // middle
        12, 13, 14, 22, // ring
        16, 17, 18, 23  // pinky
    };

    public List<List<float[]>> jointsPositionWorld = new();
    public List<List<float[]>> jointsRotationWorld = new();

    public List<List<float[]>> jointsPositionCamera = new();
    public List<List<float[]>> jointsRotationCamera = new();

    public void AddFrame(HandVisual hand, Camera camera)
    {
        var posWorldFrame = new List<float[]>();
        var rotWorldFrame = new List<float[]>();
        var posCamFrame = new List<float[]>();
        var rotCamFrame = new List<float[]>();

        foreach (int i in IndexMapping)
        {
            var joint = hand.Joints[i];

            // World
            posWorldFrame.Add(new float[] { joint.position.x, joint.position.y, joint.position.z });
            rotWorldFrame.Add(new float[] { joint.rotation.x, joint.rotation.y, joint.rotation.z, joint.rotation.w });

            // Camera
            Vector3 camPos = camera.transform.InverseTransformPoint(joint.position);
            Quaternion camRot = Quaternion.Inverse(camera.transform.rotation) * joint.rotation;

            posCamFrame.Add(new float[] { camPos.x, camPos.y, camPos.z });
            rotCamFrame.Add(new float[] { camRot.x, camRot.y, camRot.z, camRot.w });
        }

        jointsPositionWorld.Add(posWorldFrame);
        jointsRotationWorld.Add(rotWorldFrame);
        jointsPositionCamera.Add(posCamFrame);
        jointsRotationCamera.Add(rotCamFrame);
    }
}


[Serializable]
public class TrialLogger
{
    public string userId;
    public string sessionId;
    public string targetObjectName;
    public string objectName;
    public int trialIndex;
    public int label;

    public PoseArray objectPoseWorld = new();
    public PoseArray objectPoseCamera = new();
    public PoseArray cameraPoseWorld = new();

    public Gesture gestures = new();
    public List<bool> isLabeledFrame = new();
    public List<bool> isInReachFrame = new();

    public TrialLogger(string userId, string sessionId, string targetObjectName)
    {
        this.userId = userId;
        this.sessionId = sessionId;
        this.targetObjectName = targetObjectName;
    }

    public void RecordFrame(HandVisual hand, GameObject obj, Camera cam, bool isLabeled = false, bool isInReach = false)
    {
        if (hand == null || obj == null) return;

        objectPoseWorld.Add(obj.transform.position, obj.transform.rotation);

        Vector3 posCam = cam.transform.InverseTransformPoint(obj.transform.position);
        Quaternion rotCam = Quaternion.Inverse(cam.transform.rotation) * obj.transform.rotation;
        objectPoseCamera.Add(posCam, rotCam);

        gestures.AddFrame(hand, cam);
        isLabeledFrame.Add(isLabeled);
        isInReachFrame.Add(isInReach);

        cameraPoseWorld.Add(cam.transform.position, cam.transform.rotation);
    }

    public void SetLabel(int gestureLabel, string objectName)
    {
        this.label = gestureLabel;
        this.objectName = objectName;
    }
}
