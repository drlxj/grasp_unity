using Oculus.Interaction.HandGrab;
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using UnityEngine;

public class DataGenerator : MonoBehaviour
{
    public bool GenerateFile = false;
    private string FileName = "Trials";
    private string CSVFileName;
    private string FilePath;
    private int BlockSize = 5; 
    private int ObjectDisplayed;
    private int MatrixSize;
    private string FolderPath = "../DistanceGrasp/Assets/UserStudy";


    private GameObject[] Objects;
    private int objectCount;
    private List<DataPackageSimplified> FinalData = new();

    private void OnEnable()
    {
        Objects = this.GetComponent<TrackData>().Objects;
        objectCount = Objects.Length;
        //BlockSize = this.GetComponent<ControlTaskManager>().BlockSize;
        //BlockSize = 18;
        //ObjectDisplayed = this.GetComponent<ControlTaskManager>().ObjectDisplayed;
        //ObjectDisplayed = 25;
        MatrixSize = (int)Math.Sqrt(ObjectDisplayed);;

        CSVFileName = FileName + ".csv";
        FilePath = Path.Combine(FolderPath, CSVFileName);
        if (!File.Exists(FilePath)|| !GenerateFile)
        {
            Debug.LogError($"The file at path {FilePath} does not exist.");
            return;
        }
    }

    // Start is called before the first frame update
    void Start()
    {
        CSVFileName = FileName + ".csv";
        FilePath = Path.Combine(FolderPath, CSVFileName);
        if (!File.Exists(FilePath) || GenerateFile)
        {
            GenerateTrialsWithTargetAndObjectOrder();
        } 
    }
    /// <summary>
    /// Calculate indices of (n-2)x(n-2) central block from a nxn matrix
    /// </summary>
    /// <param name="matrixSize"></param>
    /// <returns></returns>
    private List<int> GenerateCentralIndices(int matrixSize)
    {
        List<int> centralIndices = new List<int>();

        int startRow = 1;
        int endRow = matrixSize-1;
        int startCol = 1;
        int endCol = matrixSize-1;
        for (int row = startRow; row < endRow; row++)
        {
            for (int col = startCol; col < endCol; col++)
            {
                centralIndices.Add(row * matrixSize + col);
            }
        }

        return centralIndices;
    }

    private void GenerateTrialsWithTargetAndObjectOrder()
    
    {
        List<int> mapping = GenerateCentralIndices(MatrixSize);
        Dictionary<int, bool> checkData = new();
        for (int i = 0; i< objectCount; i++)
        {
            checkData[i] = false;
        }
        HashSet<int> selectedNumber = new();
        System.Random rand = new();
        
        // For each block, generate [BlockSize] trials
        int count = mapping.Count();
        for (int i = 0; i < BlockSize; i++)
        {
            int targetIndex = mapping[i%count];

            int targetInteractable = 0;
            List<int> combination = new();

            selectedNumber.Clear();

            // For each trial, generate [objectInScene - 1] objects and 1 target
            // And [objectInScene] occlusion objects
            for (int j = 0; j < ObjectDisplayed * 2; j++)
            {
                int choice;
                if (j == targetIndex)
                {
                    do
                    {
                        choice = rand.Next(objectCount);
                    } while (selectedNumber.Contains(choice) || checkData[choice]);

                    checkData[choice] = true;
                    targetInteractable = choice;
                    combination.Add(choice);
                } 
                else
                {
                    do
                    {
                        choice = rand.Next(objectCount);
                    } while (selectedNumber.Contains(choice));
                    combination.Add(choice);
                }
                
                selectedNumber.Add(choice);
            }

            FinalData.Add(new DataPackageSimplified(combination, targetInteractable));
        }
        StoreBlock();
        Debug.Log("Trial Data generated.");
    }


    private void StoreBlock()
    {
        using (StreamWriter sw = new(FilePath))
        {
            sw.WriteLine("Target," + string.Join(",", Enumerable.Range(1, ObjectDisplayed * 2)));
            foreach (DataPackageSimplified data in FinalData)
            {
                sw.WriteLine(data.ToString());
            }
        }
    }


    public BlockDataPackage ReadBlock()
    {
        List<DataPackage> data = new List<DataPackage>();
        using (StreamReader sr = new StreamReader(FilePath))
        {
            sr.ReadLine();
            string line;
            while((line = sr.ReadLine()) != null)
            {
                data.Add(ParseData(line));
            }
        }
        return new BlockDataPackage(data).ReOrder();
    }


    private DataPackage ParseData(string str)
    {
        List<int> ints = str.Split(',').Select(s => Convert.ToInt32(s.Trim())).ToList();
        /*string log = "";
        foreach(int i in ints)
        {
            log += ints[i] + "   ";
        }
        Debug.Log("LogOut: " + log);*/
        DistanceHandGrabInteractable Target = Objects[ints[0]].GetComponentInChildren<DistanceHandGrabInteractable>();
        List<DistanceHandGrabInteractable> data = new();
        List<DistanceHandGrabInteractable> occlusion = new();
        for (int i = 1; i < ObjectDisplayed + 1; i++)
        {
            data.Add(Objects[ints[i]].GetComponentInChildren<DistanceHandGrabInteractable>());
        }
        for (int i = ObjectDisplayed + 1; i < ObjectDisplayed*2 + 1; i++)
        {
            occlusion.Add(Objects[ints[i]].GetComponentInChildren<DistanceHandGrabInteractable>());
        }
        return new DataPackage(data, occlusion, Target);
    }
} 
