using System.Collections;
using System.Collections.Generic;
using Meta.WitAi.Json;
using UnityEngine;
using System;

public class QuatsObjectTransformData
{
    public List<List<float>> object_rotation { get; set; }
    public List<string> seq_name { get; set; }
}

public class MiniDataCollectionObjectTransformData
{
    public List<string> seq_name { get; set; }
    public List<List<List<float>>> object_rotation { get; set; }
    public List<List<float>> object_translation { get; set; }
    public List<List<List<float>>> subject_joints_pos_rel2wrist { get; set; }
    
}



public class MiniDataCollectionObjectTransformAssignment : MonoBehaviour
{
    private GameObject[] objects;
    public string fileName; //"rotation_candidates_check_all";

    private Dictionary<string, QuatsObjectTransformData> transformData;

    public List<Tuple<string, string>> RotationSeqNameObjectList = new List<Tuple<string, string>>();

    public int randomIndex = 1;
    
    // Start is called before the first frame update
    void Start()
    {
        objects = GetComponent<MiniDataCollectionTrackData>().Objects;
        LoadTransformCandidates();
        AssignRandomTransformToGameObjectSet();
        Debug.Log($"Assigned over");
    }

    // Update is called once per frame
    void Update()
    {
        
    }

    void LoadTransformCandidates()
    {
       
        TextAsset jsonFile = Resources.Load<TextAsset>(fileName);
        string jsonContent = jsonFile.text;
        
        transformData = JsonConvert.DeserializeObject<Dictionary<string, QuatsObjectTransformData>>(jsonContent);

        // Debug.Log("Loaded transform candidates");
       
    }

    void AssignRandomTransformToGameObjectSet()
    {

        for (int i = 0; i < objects.Length; i++)
        {
            GameObject current_object = objects[i];

            string object_name = current_object.name;

            object_name = object_name.Replace("_", "");

            Debug.Log($"object_name: {object_name}");

            QuatsObjectTransformData object_transform_set = transformData[object_name];

            // int randomIndex = UnityEngine.Random.Range(0, object_transform_set.seq_name.Count);;

            Quaternion rotation_unity;
            if (i != 0)
            {
                randomIndex = UnityEngine.Random.Range(0, object_transform_set.object_rotation.Count);
            }

            List<float> object_rotation_quaternion = object_transform_set.object_rotation[randomIndex];
            rotation_unity = new Quaternion(
                                            object_rotation_quaternion[0],
                                            object_rotation_quaternion[1],
                                            object_rotation_quaternion[2],
                                            object_rotation_quaternion[3]
                                        );
            rotation_unity = new Quaternion(object_rotation_quaternion[1], -object_rotation_quaternion[2], -object_rotation_quaternion[3], object_rotation_quaternion[0]); // python: (w, x, y, z) -> python: (x, y, z, w)
            current_object.transform.rotation = rotation_unity;
            Debug.Log($"Assigned {object_name} from {object_transform_set.seq_name[randomIndex]} index {randomIndex} with matrix" + string.Join(", ", rotation_unity));

        }
    }
}
