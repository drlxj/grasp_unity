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

    [Header("Arc Placement Settings")]
    public float angleStep = 3.0f;           // 弧形区域的角度（度）
    private float arcRadius = 2.0f;           // 弧形区域的半径
    private float deltaHeight = 0.002f;          // 弧形区域的高度范围
    private float deltaRadius = 0.1f;        // 最小距离

    [HideInInspector]
    public GameObject[] Objects;
    [HideInInspector]
    public string[] objNames;

    private GameObject[] Prefabs;
    private int objectCount;
    private System.Random rng = new System.Random();
    private int[] placementOrder;  // 物体放置顺序数组

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
        expConfigs.Add('O', new ExpConfig(0f)); // pure pointing, native method
        expConfigs.Add('P', new ExpConfig(1f)); // pure pointing, head-hand
        expConfigs.Add('G', new ExpConfig(2f)); // pure gesture
        expConfigs.Add('C', new ExpConfig(3f)); // combi, pointing head-hand + gesture
    }

     private void Start()
    {
        // LoadBLSMatrix();
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
    /// 实例化并在弧形区域摆放物体
    /// </summary>
    private void InstantiateAndPlaceObjects()
    {
        Vector3 startPos = new Vector3(0, 0, 0);

        // All position candidates and then shuffle
        float arcAngle = objectCount * angleStep;
        float startAngle = -arcAngle / 2;
        List<Vector3> arcPositionList = new List<Vector3>();
        for (int i = 0; i < objectCount; i++)
        {
            float currentAngle = startAngle + (i * angleStep);
            float angleRad = currentAngle * Mathf.Deg2Rad;
            Vector3 arcPosition = CalculateArcPosition(startPos, currentAngle, angleRad);
            arcPosition.z += i%2 * deltaRadius;
            arcPositionList.Add(arcPosition);
        }
        FisherYatesShuffle(arcPositionList);
        
        
        for (int i = 0; i < objectCount; i++)
        {
            GameObject instance = Instantiate(Prefabs[i % Prefabs.Length]);
            instance.name = Prefabs[i % Prefabs.Length].name;
            instance.transform.position = arcPositionList[i];
            
            Objects[i] = instance;
            objNames[i] = instance.name;
        }

        Debug.Log($"Placed {objectCount} objects in an arc with radius {arcRadius}, angle {arcAngle}°, and height range {deltaHeight}.");
    }

    /// <summary>
    /// 计算弧形区域中的位置
    /// </summary>
    private Vector3 CalculateArcPosition(Vector3 centerPos, float angleDegrees, float angleRadians)
    {
        // 计算X和Z坐标（水平面上的弧形）
        float x = centerPos.x + arcRadius * angleRadians;
        float z = centerPos.z + arcRadius;
        
        // 计算Y坐标（高度）
        float deltaY = UnityEngine.Random.Range(0, deltaHeight);
        float y = centerPos.y + deltaY;
        
        return new Vector3(x, y, z);
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
    /// Fisher-Yates洗牌算法 - 用于GameObject数组
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

    private void FisherYatesShuffle(List<Vector3> list)
{
    for (int i = list.Count - 1; i > 0; i--)
    {
        int j = rng.Next(i + 1);
        Vector3 temp = list[i];
        list[i] = list[j];
        list[j] = temp;
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
    public float MethodID = 0f;


    public ExpConfig(float methodID)
    {
        MethodID = methodID;
    }

}
