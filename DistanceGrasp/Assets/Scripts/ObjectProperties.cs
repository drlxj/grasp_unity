using Oculus.Interaction;
using Oculus.Interaction.HandGrab;
using System;
using UnityEngine;

public class ObjectProperties : MonoBehaviour
{
    // public Oculus.Interaction.HandGrab.DistanceHandGrabInteractable interactible;

    public ObjectType ObjectType;

    [HideInInspector]
    public int ObjIdx;
    private static int objCount = 0;

    /*public ObjectProperties() 
    {
        string name = this.name;
        if (Enum.TryParse(name, out ObjectType type))
        {
            ObjectType =  type;
        } 
    }*/

    // Start is called before the first frame update
    public void Start()
    {
        this.ObjIdx = objCount;
        objCount += 1;
        DistanceHandGrabInteractable interactable = this.GetComponentInChildren<DistanceHandGrabInteractable>();
        interactable.ObjID = ObjIdx;
    }

    // Update is called once per frame
    public void Update()
    {

    }

    public float GetID()
    {
        return ObjIdx;
    }

}
