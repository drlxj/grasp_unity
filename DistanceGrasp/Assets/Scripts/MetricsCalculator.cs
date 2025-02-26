using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System.IO;

public class UserDataLog: MonoBehaviour
{
    public int ObjID;
    public string Name;
    public float CatchDuration;
    public bool FirstTry;
    public int AttemptCount;

    public UserDataLog(string text)
    {
        string[] values = text.Split(",");
        if (values.Length != 5 )
        {
            Debug.LogError("Wrong log");
        }
        ObjID = int.Parse(values[0]);
        Name = values[1];
        CatchDuration = float.Parse(values[2]);
        int first = int.Parse(values[3]);
        FirstTry = (first == 1);
        AttemptCount = int.Parse(values[4]);
    }
}

public class MetricsCalculator : MonoBehaviour
{
    private readonly static string csvFileFolder = "../DistanceGrasp/Assets/LogData/";

    public static void ComputeMetrics(string UserName)
    {
        List<UserDataLog> logs = new List<UserDataLog>();
        string csvFilePath = csvFileFolder + UserName + "_RecordData.csv";
        using (StreamReader sr = new(csvFilePath))
        {
            // Read CSV title
            string line = sr.ReadLine();
            while((line = sr.ReadLine()) != null)
            {
                logs.Add(new UserDataLog(line));
            }
        }

        int logCount = logs.Count;
        float TimeSum = 0;
        float Accuracy = 0;
        foreach (UserDataLog log in logs)
        {
            TimeSum += log.CatchDuration;
            Accuracy += 1.0f / (float)log.AttemptCount;
        }
        
        float AverageTime = TimeSum / logCount;
        Accuracy /= logCount;
        float ErrorRate = 1 - Accuracy;

        Debug.Log($"{UserName}'s final metrics: Average Time:{AverageTime}, Error Rate:{ErrorRate*100}%.");

        using (StreamWriter sw = new(csvFilePath, true))
        {
            sw.WriteLine($"-1, Average, {AverageTime}, 0, {ErrorRate}");
        }
    }

}
