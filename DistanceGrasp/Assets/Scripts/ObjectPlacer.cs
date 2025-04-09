//using System.Collections;
//using System.Collections.Generic;
//using UnityEngine;
//using Meta.WitAi.Json;

//// public class ObjectTransformData
//// {
////     public List<string> seq_name { get; set; }
////     public List<List<List<float>>> object_rotation { get; set; }

////     public override string ToString()
////     {
////         string seqNames = string.Join(", ", seq_name);
////         string rotations = "";

////         for (int i = 0; i < object_rotation.Count; i++)
////         {
////             rotations += $"Rotation {i}: {string.Join(", ", object_rotation[i])}\n";
////         }

////         return $"seq_name: [{seqNames}], \nobject_rotation: \n{rotations}";
////     }
//// }
//// public class ObjectTransformAssignment 
//// {
////     private Dictionary<string, ObjectTransformData> transformData;

////     public ObjectTransformAssignment(string fileName)
////     {
////         LoadTransformCandidates(fileName);
////     }

////     private void LoadTransformCandidates(string fileName)
////     {
////         TextAsset jsonFile = Resources.Load<TextAsset>(fileName);
////         string jsonContent = jsonFile.text;
////         transformData = JsonConvert.DeserializeObject<Dictionary<string, ObjectTransformData>>(jsonContent);
////         Debug.Log("Loaded transform candidates");
////     }

////     public void AssignRandomTransform(GameObject obj)
////     {
////         if (transformData == null || !transformData.ContainsKey(obj.name))
////         {
////             Debug.LogWarning($"No transform data found for {obj.name}");
////             return;
////         }

////         ObjectTransformData objectTransformSet = transformData[obj.name];

////         int randomIndex = Random.Range(0, objectTransformSet.seq_name.Count);
////         List<List<float>> objectRotationMatrix = objectTransformSet.object_rotation[randomIndex];

////         Matrix4x4 T_unity2python = new Matrix4x4(
////             new Vector4(-1, 0, 0, 0),
////             new Vector4(0, 1, 0, 0),
////             new Vector4(0, 0, 1, 0),
////             new Vector4(0, 0, 0, 1)
////         );

////         Matrix4x4 matrixPython = new Matrix4x4();
////         matrixPython.SetRow(0, new Vector4(objectRotationMatrix[0][0], objectRotationMatrix[0][1], objectRotationMatrix[0][2], 0));
////         matrixPython.SetRow(1, new Vector4(objectRotationMatrix[1][0], objectRotationMatrix[1][1], objectRotationMatrix[1][2], 0));
////         matrixPython.SetRow(2, new Vector4(objectRotationMatrix[2][0], objectRotationMatrix[2][1], objectRotationMatrix[2][2], 0));
////         matrixPython.SetRow(3, new Vector4(0, 0, 0, 1));

////         Matrix4x4 matrixUnity = T_unity2python * matrixPython * T_unity2python;
////         obj.transform.rotation = matrixUnity.rotation;

////         Debug.Log($"Assigned {obj.name} from {objectTransformSet.seq_name[randomIndex]} with rotation matrix");
////     }
//// }

//public class ObjectPlacer : MonoBehaviour
//{
//    public GameObject[] allObjects;  // List of all available objects to spawn
//    private int gridSize = 5;        // Grid size (gridSize x gridSize)
//    private float spacing = 0.7f;    // Distance between objects

//    private bool randomRotation = true;

//    private List<GameObject> selectedObjects = new List<GameObject>();
//    private List<GameObject> objectsInstance = new List<GameObject>();
//    public Material glowMaterial;
//    public OVRHand leftHand;
//    private float[,] distanceMap;     // Pre-stored height values
//    private Vector3[,] rotationMap; // Pre-stored rotation values

//    private List<int> availableIndices; // Stores available object indices
//    private Material originalMaterial; // Original material of the previous object
//    private GameObject currentGlowingObject; // Current glowing object
//    private int currentGroupIndex = 0; // Current group index (0, 1, 2)
//    private int currentObjectIndex = 0; // Current group index (0, 1, ...... 25)
//    private bool isTriggerHeld = false; // Check if trigger is held
//    private float holdDuration = 3f; // Duration to hold trigger to switch group
//    private float holdTimer = 0f; // Timer for trigger hold
//    private bool isGlowing = false;
//    //public TextMeshProUGUI textDisplay;
//    private bool isCountdownActive = false;

//    // Start is called before the first frame update
//    void Start()
//    {
//        // TODO: how to import Prefab in Assets/Resources
//        // TODO: how to assign the selected objects with DistanceGrasp features
//        // TODO: assign rotation accorditing to rotation list
//        // TODO: remove distanceMap
//        allObjects = Resources.LoadAll<GameObject>("Prefab"); 
//        if (allObjects == null || allObjects.Length < 75) return;

//        // Shuffle allObjects
//        FisherYatesShuffle(allObjects);

//        // Initialize height and rotation maps
//        distanceMap = new float[gridSize, gridSize];
//        rotationMap = new Vector3[gridSize, gridSize];
//        for (int row = 0; row < gridSize; row++)
//        {
//            for (int col = 0; col < gridSize; col++)
//            {
//                distanceMap[row, col] = Random.Range(2f, 5f);
//                rotationMap[row, col] = new Vector3(
//                    Random.Range(0f, 360f),
//                    Random.Range(0f, 360f),
//                    Random.Range(0f, 360f)
//                );
//            }
//        }

//        DisplayWelcomeText();
//        GenerateGrid();
//        InitializeAvailableIndices(); // Initialize available object indices
//    }

//    void DisplayWelcomeText()
//    {
//        textDisplay.text = "Welcome!";
//    }

//    void UpdateText()
//    {
//        if (textDisplay != null)
//        {
//            textDisplay.text = $"Current Group: {currentGroupIndex + 1}/3 \nNext Index: {currentObjectIndex}/25";
//        }
//    }


//    void UpdateTextIntervalGroup(int second)
//    {
//        if (textDisplay != null)
//        {
//            textDisplay.text = $"Next group starts in {second}...";
//        }
//    }

//    //void Update()
//    //{
//    //    //if (OVRInput.GetDown(OVRInput.Button.PrimaryIndexTrigger))
//    //    if (IsLeftHandFist())
//    //    {
//    //        Debug.Log("11111111111111111111111111111111111");
//    //        StartCoroutine(GlowNextObject());
//    //    }
//    //}

//    private void Update()
//    {
//        if (isCountdownActive) return;

//        if (IsLeftHandFist() && !isGlowing)
//        {
//            //Debug.Log("11111111111111111111111111111111111");
//            StartCoroutine(GlowNextObject());
//            isGlowing = true;
//            UpdateText();
//        }
//        else if (!IsLeftHandFist())
//        {
//            //Debug.Log("22222222222222222222222");
//            isGlowing = false;
//        }
//    }


//    private bool IsLeftHandFist()
//    {
//        return leftHand.GetFingerIsPinching(OVRHand.HandFinger.Index);
//    }



//    void GenerateGrid()
//    {
//        ClearOldObjects();

//        if (allObjects.Length < 75) return; // Ensure at least 75 objects

//        // Randomly select objects without duplicates for the current group
//        selectedObjects = new List<GameObject>(
//            allObjects.Skip(currentGroupIndex * 25).Take(25).OrderBy(x => Random.value)
//        );

//        Vector3 startPos = transform.position;
//        float offset = (gridSize - 1) * spacing * 0.5f;

//        Transform gridParent = new GameObject("GeneratedGrid").transform;

//        for (int row = 0; row < gridSize; row++)
//        {
//            for (int col = 0; col < gridSize; col++)
//            {
//                int index = row * gridSize + col;
//                GameObject obj = Instantiate(selectedObjects[index], gridParent);

//                float posX = col * spacing - offset;
//                float posY = row * spacing - offset;
//                float posZ = distanceMap[row, col];

//                obj.transform.position = new Vector3(startPos.x + posX, startPos.y + posY, posZ);

//                if (randomRotation)
//                {
//                    obj.transform.rotation = Quaternion.Euler(rotationMap[row, col]);
//                }

//                objectsInstance.Add(obj);
//            }
//        }
//    }

//    void ClearOldObjects()
//    {
//        foreach (var obj in objectsInstance)
//        {
//            Destroy(obj);
//        }
//        objectsInstance.Clear(); 
//    }

//    void InitializeAvailableIndices()
//    {
//        // Initialize available object indices for the current group
//        availableIndices = Enumerable.Range(0, selectedObjects.Count).ToList();
//        ShuffleAvailableIndices(); // Randomly shuffle index order
//    }

//    void ShuffleAvailableIndices()
//    {
//        // Fisher-Yates shuffle algorithm to randomly shuffle indices
//        for (int i = availableIndices.Count - 1; i > 0; i--)
//        {
//            int j = Random.Range(0, i + 1);
//            int temp = availableIndices[i];
//            availableIndices[i] = availableIndices[j];
//            availableIndices[j] = temp;
//        }
//    }

//    System.Random rng = new System.Random();

//    void FisherYatesShuffle(GameObject[] array)
//    {
//        for (int i = array.Length - 1; i > 0; i--)
//        {
//            int j = rng.Next(i + 1);

//            GameObject temp = array[i];
//            array[i] = array[j];
//            array[j] = temp;
//        }
//    }



//    IEnumerator GlowNextObject()
//    {
//        // Check if there are more objects to glow
//        if (availableIndices.Count == 0)
//        {
//            Debug.Log("All objects in this group have glowed. Switching to the next group.");

//            isCountdownActive = true;

//            if (currentGroupIndex != 2)
//            {
//                for (int i = 6; i > 0; i--)
//                {
//                    UpdateTextIntervalGroup(i);

//                    yield return new WaitForSeconds(1f);
//                }

//                currentGroupIndex++; // Move to the next group
//            }
//            else
//            {
//                for (int i = 6; i > 0; i--)
//                {
//                    FisherYatesShuffle(allObjects);
//                    textDisplay.text = $"Resetting to group 1 in {i}...";
//                    yield return new WaitForSeconds(1f);
//                }

//                currentGroupIndex = 0;
//            }

//            currentObjectIndex = 0;

//            GenerateGrid(); 
//            InitializeAvailableIndices();
//            UpdateText();
//            isCountdownActive = false;
//            yield break; 
//        }

//        // Restore the color of the current glowing object if it exists
//        if (currentGlowingObject != null)
//        {
//            Renderer currentRenderer = currentGlowingObject.transform.Find("default").GetComponent<MeshRenderer>();
//            currentRenderer.sharedMaterial = originalMaterial; // Restore original material
//        }

//        // Get the index of the next glowing object
//        int nextIndex = availableIndices[0];
//        currentObjectIndex++;
//        GameObject nextObject = objectsInstance[nextIndex];
//        Renderer nextRenderer = nextObject.transform.Find("default").GetComponent<MeshRenderer>();

//        originalMaterial = nextRenderer.sharedMaterial; // Store the original material of the current object
//        nextRenderer.sharedMaterial = glowMaterial; // Make the next object glow

//        currentGlowingObject = nextObject; // Update the current glowing object

//        // Remove the index of the glowing object from the available list
//        availableIndices.RemoveAt(0);

//        Debug.Log("Next glowing object: " + nextObject.name);
//    }
//}
