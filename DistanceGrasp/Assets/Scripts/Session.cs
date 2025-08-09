using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

public class Session : MonoBehaviour
{
    public static Dictionary<char, ExpConfig> expConfigs = new();
    private static Dictionary<int, List<char>> BLSMatrix = new();

    [Header("Object Generation Settings")]
    public string prefabFolderName = "Prefab_test";
    public float densityFactor = 1.0f;
    public Vector3 boxSize = new Vector3(0.3f, 0.3f, 2f);
    public float heightOffset = 0.0f;
    public float depth = 2f;
    public LayerMask objectLayer;

    [HideInInspector]
    public GameObject[] Objects;
    [HideInInspector]
    public string[] objNames;

    private GameObject[] Prefabs;
    private int objectCount;
    private System.Random rng = new System.Random();

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
        expConfigs.Add('O', new ExpConfig(0f, true, 0.15f)); // pure pointing, native method
        expConfigs.Add('P', new ExpConfig(0f, false, 0.4f)); // pure pointing, head-hand
        expConfigs.Add('G', new ExpConfig(1f, true, 0.15f)); // pure gesture
        expConfigs.Add('C', new ExpConfig(0.5f, false, 0.15f)); // combi, pointing head-hand + gesture
    }

    private void Start()
    {
        LoadBLSMatrix();
        GenerateObjects();
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

    /// <summary>
    /// 生成物体并摆放
    /// </summary>
    private void GenerateObjects()
    {
        LoadPrefabs();
        InstantiateAndPlaceObjects();
        // LogObjectInfo();
    }

    /// <summary>
    /// 加载预制体
    /// </summary>
    private void LoadPrefabs()
    {
        Prefabs = Resources.LoadAll<GameObject>(prefabFolderName);
        if (Prefabs == null || Prefabs.Length == 0)
        {
            Debug.LogError($"No prefabs found in folder: {prefabFolderName}");
            return;
        }

        FisherYatesShuffle(Prefabs);
        objectCount = Prefabs.Length;
        Objects = new GameObject[objectCount];
        objNames = new string[objectCount];

        Debug.Log($"Loaded {objectCount} prefabs from {prefabFolderName}");
    }

    /// <summary>
    /// 实例化并摆放物体
    /// </summary>
    private void InstantiateAndPlaceObjects()
    {
        Vector3 startPos = transform.position;
        int attempts = 0;

        for (int i = 0; i < objectCount; i++)
        {
            GameObject instance = Instantiate(Prefabs[i % Prefabs.Length]);
            instance.name = Prefabs[i % Prefabs.Length].name;
            bool placed = false;

            while (!placed && attempts < 100) // Prevent infinite loops
            {
                Vector3 randomPos = CalculateRandomPosition(startPos, instance);
                Collider[] colliders = Physics.OverlapBox(randomPos, instance.transform.localScale / 2, Quaternion.identity, objectLayer);

                if (colliders.Length == 0) // Ensure no overlap
                {
                    instance.transform.position = randomPos;
                    placed = true;
                }
                attempts++;
            }

            Objects[i] = instance;
            objNames[i] = instance.name;
        }

        Debug.Log($"Placed {objectCount} objects within a box of size {boxSize}.");
    }

    /// <summary>
    /// 计算随机位置
    /// </summary>
    private Vector3 CalculateRandomPosition(Vector3 startPos, GameObject instance)
    {
        return new Vector3(
            startPos.x + UnityEngine.Random.Range(-boxSize.x / 2, boxSize.x / 2) * densityFactor,
            startPos.y + UnityEngine.Random.Range(-boxSize.y / 2, boxSize.y / 2) + heightOffset,
            startPos.z + UnityEngine.Random.Range(-boxSize.z / 2, boxSize.z / 2) * densityFactor + depth
        );
    }

    /// <summary>
    /// 检查位置是否有效
    /// </summary>
    private bool IsPositionValid(Vector3 position, GameObject instance)
    {
        Collider[] colliders = Physics.OverlapBox(position, instance.transform.localScale / 2, Quaternion.identity, objectLayer);
        return colliders.Length == 0;
    }

    /// <summary>
    /// 记录物体信息
    /// </summary>
    private void LogObjectInfo()
    {
        string objLog = $"Initial {objectCount} objects: ";
        for (int i = 0; i < objectCount; i++)
        {
            objLog += Objects[i].name + "  ";
            objNames[i] = Objects[i].name;
        }
        Debug.Log(objLog);
    }

    /// <summary>
    /// Fisher-Yates洗牌算法
    /// </summary>
    private void FisherYatesShuffle(GameObject[] array)
    {
        for (int i = array.Length - 1; i > 0; i--)
        {
            int j = rng.Next(i + 1);
            GameObject temp = array[i];
            array[i] = array[j];
            array[j] = temp;
        }
    }

    /// <summary>
    /// 获取物体数组
    /// </summary>
    public GameObject[] GetObjects()
    {
        return Objects;
    }

    /// <summary>
    /// 获取物体名称数组
    /// </summary>
    public string[] GetObjectNames()
    {
        return objNames;
    }

    /// <summary>
    /// 重新生成物体
    /// </summary>
    public void RegenerateObjects()
    {
        // 清理现有物体
        if (Objects != null)
        {
            foreach (var obj in Objects)
            {
                if (obj != null)
                {
                    DestroyImmediate(obj);
                }
            }
        }

        GenerateObjects();
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
