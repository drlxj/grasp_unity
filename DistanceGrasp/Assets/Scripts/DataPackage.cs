using Oculus.Interaction.HandGrab;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;


/*
 * Definition of the data package, which is a trial in our study.
 */
public class DataPackage : MonoBehaviour
{
    [HideInInspector]
    public List<DistanceHandGrabInteractable> Combination;
    [HideInInspector]
    public List<DistanceHandGrabInteractable> OcclusionList;

    [HideInInspector]
    public DistanceHandGrabInteractable Target;
    
    [HideInInspector]
    public GameObject[] Objects;
    private int ObjectCount = 0;

    [HideInInspector]
    public int PackageID;
    private static int PackageIDCount = 0;

    public DataPackage(GameObject[] RefObjects, int ObjNum)
    {
        Combination = new List<DistanceHandGrabInteractable>();
        if (Objects == null || ObjectCount == 0)
        {
            Objects = RefObjects;
            ObjectCount = Objects.Length;
        }
        PackageID = PackageIDCount;
        PackageIDCount++;
        RandomPicker(ObjNum);
        System.Random rand = new System.Random();
        Target = Combination[rand.Next(Combination.Count)];

        // CheckData();
    }

    public DataPackage(List<DistanceHandGrabInteractable> combination, List<DistanceHandGrabInteractable> occlusion, DistanceHandGrabInteractable target)
    {
        this.Combination = combination;
        this.OcclusionList = occlusion;
        // Debug.Log("DataPackage Count: " + Combination.Count);
        this.Target = target;
        this.Objects = null;
        this.ObjectCount = 0;

        PackageID = PackageIDCount;
        PackageIDCount++;
        // CheckData();
    }

    private void RandomPicker(int num)
    {
        HashSet<int> selectedNumber = new HashSet<int>();
        selectedNumber.Clear();

        for (int i = 0; i < num; i++)
        {
            System.Random rand = new();
            int choice;
            do
            {
                 choice = rand.Next(ObjectCount);
            } while (selectedNumber.Contains(choice));

            selectedNumber.Add(choice);

            DistanceHandGrabInteractable interactable = Objects[choice].GetComponentInChildren<DistanceHandGrabInteractable>();
            Debug.Log($"num---: {num}");
            Debug.Log($"Objects[choice]: {Objects[choice].name}");

            this.Combination.Add(interactable);
        }
    }

    public void CheckData()
    {
        String log = $"Package{PackageID}: \n";
        foreach(DistanceHandGrabInteractable itr in this.Combination)
        {
            log += itr.GetObjName() + "  ";
        }
        log += "\n";
        if (OcclusionList != null) {
            foreach(DistanceHandGrabInteractable itr in this.OcclusionList)
            {
                log += itr.GetObjName() + "   ";
            }
        }
        
        log += $"\nTarget is {Target.GetObjName()}";
        Debug.Log(log);
    }
}



/*
 * Definition of a block of data in our study.
 */
public class BlockDataPackage : MonoBehaviour
{
    public List<DataPackage> DataPackages = new List<DataPackage>();
    public int BlockSize;

    public BlockDataPackage(GameObject[] RefObjects, int num, int BlockSizeNum = 2)
    {
        BlockSize = BlockSizeNum;
        for (int i = 0; i < BlockSize; i++)
        {
            Debug.Log($"BlockSize---: {BlockSize}");
            DataPackages.Add(new DataPackage(RefObjects, num));
        }
    }

    //public BlockDataPackage(GameObject[] RefObjects)
    //{
    //    for (int i = 0; i < RefObjects.Length; i++)
    //    {
    //        DataPackages.Add(new DataPackage(RefObjects[i], num));
    //    }
    //}

    public BlockDataPackage(List<DataPackage> dataPackages)
    {
        DataPackages = dataPackages;
        BlockSize = dataPackages.Count;
    }

    public List<DistanceHandGrabInteractable> GetCandidates(int idx)
    {
        return this.DataPackages[idx].Combination;
    }
    public List<DistanceHandGrabInteractable> GetOcclusionList(int idx)
    {
        return this.DataPackages[idx].OcclusionList;
    }

    public DistanceHandGrabInteractable GetTarget(int idx)
    {
        return this.DataPackages[idx].Target;
    }

    public BlockDataPackage ReOrder()
    {
        /*List<DataPackage> shuffled = new List<DataPackage>(DataPackages);
        Shuffle(shuffled);
        return new BlockDataPackage(shuffled);*/
        Shuffle(DataPackages);
        return this;
    }

    /*
     *  Fisher-Yates Algorithm
     */
    static void Shuffle<T>(List<T> list)
    {
        System.Random rng = new();
        int n = list.Count;
        while (n > 1)
        {
            n--;
            int k = rng.Next(n + 1);
            T value = list[k];
            list[k] = list[n];
            list[n] = value;
        }
    }

    private void DoubleShuffle(List<DataPackage> list1, List<DistanceHandGrabInteractable> list2)
    {
        int n = list1.Count;
        if (n != list2.Count)
        {
            Debug.LogError("Occlusion object number not match original object number");
        }

        System.Random rng = new();

        while (n > 1)
        {
            n--;
            int k = rng.Next(n + 1);

            (list1[n], list1[k]) = (list1[k], list1[n]);
            (list2[n], list2[k]) = (list2[k], list2[n]);
        }
    } 

}

/*
 * Simplified version of the data package, only store the index of each interactable
 * To enable storage and Reconstruction of Data.
*/
public class DataPackageSimplified : MonoBehaviour
{
    public List<int> TrialIndex;
    public int TargetIndex;

    public DataPackageSimplified(List<int> trialIndex, int targetIndex)
    {
        TrialIndex = trialIndex;
        TargetIndex = targetIndex;
    }

    public override string ToString()
    {
        string tmp = TargetIndex.ToString();
        foreach (int i in TrialIndex)
        {
            tmp += "," + i.ToString();
        }
        return tmp;
    }
}


public class ExpConfig : MonoBehaviour
{
    // Default method: Unity Original SDK
    public float Weight = 0f;
    // Default Occlusion: No Occlusion
    public bool Occlusion = false;
    // Default Distance: 0.15f (Camera Distance: 3m)
    public float AngularDistance = 0.15f;


    public ExpConfig(float weight, bool occlusion, float dis)
    {
        Weight = weight;
        Occlusion = occlusion;
        AngularDistance = dis;
    }

}