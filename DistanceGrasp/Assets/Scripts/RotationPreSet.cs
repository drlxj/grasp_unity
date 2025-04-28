using System.Collections.Generic;
using System.IO;
using UnityEngine;
using Newtonsoft.Json;

public class RotationPreSet : MonoBehaviour
{
    public string PrefabFolderName;
    public int[] Y_Angles;

    private Dictionary<string, Dictionary<string, List<List<float>>>> jsonData = new Dictionary<string, Dictionary<string, List<List<float>>>>();

    void Start()
    {
        // Load all prefabs from the specified folder
        GameObject[] Prefabs = Resources.LoadAll<GameObject>(PrefabFolderName);

        foreach (var prefab in Prefabs)
        {
            // Read current prefab's transform
            Transform prefabTransform = prefab.transform;
            Vector3 prefabEulerAngles = prefabTransform.eulerAngles;

            // List to store quaternion rotations for the current prefab
            List<List<float>> prefabQuaternionList = new List<List<float>>();

            foreach (var angle in Y_Angles)
            {
                // Create new euler angles and set to prefab's transform
                Vector3 newPrefabEulerAngles = new Vector3(prefabEulerAngles.x, prefabEulerAngles.y + angle, prefabEulerAngles.z);
                prefabTransform.eulerAngles = newPrefabEulerAngles;

                // Convert to quaternion
                Quaternion prefabQuaternion = prefabTransform.rotation;

                // Extract x, y, z, w and round to 6 decimal places
                List<float> quaternionComponents = new List<float>
                {
                    (float)System.Math.Round(prefabQuaternion.x, 6),
                    (float)System.Math.Round(prefabQuaternion.y, 6),
                    (float)System.Math.Round(prefabQuaternion.z, 6),
                    (float)System.Math.Round(prefabQuaternion.w, 6)
                };

                // Add to the prefab's quaternion list
                prefabQuaternionList.Add(quaternionComponents);
            }

            // Add prefab's quaternion list to jsonData
            jsonData[prefab.name] = new Dictionary<string, List<List<float>>>
            {
                { "object_rotation", prefabQuaternionList }
            };
        }

        // Serialize jsonData to JSON format
        string json = JsonConvert.SerializeObject(jsonData, Formatting.Indented);

        // Save JSON to file
        string timestamp = System.DateTime.Now.ToString("yyyyMMdd_HHmmss");
        string path = $"Assets/Resources/quaternion_candidates_{timestamp}.json";
        File.WriteAllText(path, json);
        Debug.Log("JSON data saved to: " + path);
    }

    
    void Update()
    {
        Quit();
    }

    public static void Quit()
    {
#if UNITY_EDITOR
        UnityEditor.EditorApplication.isPlaying = false;
#else
        Application.Quit();
#endif
    }
}