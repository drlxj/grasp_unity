using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

public class Session : MonoBehaviour
{
    private static Dictionary<char, ExpConfig> expConfigs = new();
    private static Dictionary<int, List<char>> BLSMatrix = new();
    /*
     * Experiment Configuration Set here.
    
    // Default method: Unity Original SDK
    public float Weight = 0f;
    // Default Occlusion: No Occlusion
    public bool Occlusion = false;
    // Default Distance: 0.15f (Camera Distance: 3m)
    public float AngularDistance = 0.15f;

     */
    private void OnEnable()
    {
        expConfigs.Add('A', new ExpConfig(0f, false, 0.15f)); // origin, no occlusion, 0.15m angular distance
        expConfigs.Add('B', new ExpConfig(0f, false, 0.4f));
        expConfigs.Add('C', new ExpConfig(1f, false, 0.15f)); // ours, no occlusion, 0.15m angular distance
        expConfigs.Add('D', new ExpConfig(1f, false, 0.4f));
        expConfigs.Add('E', new ExpConfig(0f, true, 0.15f));
        expConfigs.Add('F', new ExpConfig(0f, true, 0.4f));
        expConfigs.Add('G', new ExpConfig(1f, true, 0.15f));
        expConfigs.Add('H', new ExpConfig(1f, true, 0.4f));
        expConfigs.Add('I', new ExpConfig(0.5f, false, 0.15f)); // combi, no occlusion, 0.15m angular distance
    }

    private void Start()
    {
        LoadBLSMatrix();
    }

    public static ExpConfig GetExpConfig(char type)
    {
        if (expConfigs.TryGetValue(type, out ExpConfig config))
        {
            return config;
        }
        else
        {
            return null;
        }
    }

    // BLS: Balanced Latin Square Generator
    private void LoadBLSMatrix()
    {
        string FolderPath = "../DistanceGrasp/Assets/UserStudy"; 
        using (StreamReader sr = new StreamReader(Path.Combine(FolderPath, "BLS.csv")))
        {
            string line;
            int cnt = 0;
            while ((line = sr.ReadLine()) != null)
            {
                BLSMatrix.Add(cnt++, ParseCSV(line));
            }
        }
    }

    private List<char> ParseCSV(string line)
    {
        List<char> tmp = new();
        foreach (string s in line.Split(","))
        {
            if (!string.IsNullOrEmpty(s))
            {
                tmp.Add(s[0]);
            }
        }
        return tmp;
    }

    // define the bls order according to #users
    public static List<char> GetConfigList()
    {
        // TODO: optimize folder hierachy: how to define user id, how to save performance for each task
        string FolderPath = "../DistanceGrasp/Assets/LogData"; // folder to save users data
        if (!Directory.Exists(FolderPath))
        {
            Debug.LogError("Log File Folder not exist.");
        }
        string[] filenames = Directory.GetFiles(FolderPath);
        int cnt = 0;
        foreach (string filename in filenames)
        {
            if (filename.Split('.')[1] == "csv")
            {
                cnt++;
            }
        }
        return BLSMatrix[cnt % 8];
    }

}
