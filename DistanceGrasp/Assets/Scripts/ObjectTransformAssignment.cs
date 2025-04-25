using System.Collections;
using System.Collections.Generic;
using Meta.WitAi.Json;
using UnityEngine;
using System;

// public class ObjectTransformData
// {
//     public List<string> seq_name { get; set; }
//     public List<List<List<float>>> object_rotation { get; set; }

//     public override string ToString()
//     {
//         string seqNames = string.Join(", ", seq_name);
//         string rotations = "";

//         for (int i = 0; i < object_rotation.Count; i++)
//         {
//             rotations += $"Rotation {i}: {string.Join(", ", object_rotation[i])}\n";
//         }

//         return $"seq_name: [{seqNames}], \nobject_rotation: \n{rotations}";
//     }
// }

public class ObjectTransformData
{
    public List<string> seq_name { get; set; }
    public List<List<List<float>>> object_rotation { get; set; }
    public List<List<float>> object_translation { get; set; }
    public List<List<List<float>>> subject_joints_pos_rel2wrist { get; set; }
    // public List<List<List<float>>> subject_vertices_pos_rel2wrist { get; set; }
    

    public override string ToString()
    {
        string seqNames = string.Join(", ", seq_name);
        string rotations = "";
        string translations = "";
        string joints = "";
        // string vertices = "";

        for (int i = 0; i < object_rotation.Count; i++)
        {
            rotations += $"Rotation {i}: {string.Join(", ", object_rotation[i])}\n";
        }

        for (int i = 0; i < object_translation.Count; i++)
        {
            translations += $"Translation {i}: {string.Join(", ", object_translation[i])}\n";
        }

        for (int i = 0; i < subject_joints_pos_rel2wrist.Count; i++)
        {
            joints += $"Joints {i}: {string.Join(", ", subject_joints_pos_rel2wrist[i])}\n";
        }

        // for (int i = 0; i < subject_vertices_pos_rel2wrist.Count; i++)
        // {
        //     vertices += $"Vertices {i}: {string.Join(", ", subject_vertices_pos_rel2wrist[i])}\n";
        // }

        return $"seq_name: [{seqNames}], \n" +
               $"object_rotation: \n{rotations}" +
               $"object_translation: \n{translations}" +
               $"subject_joints_pos_rel2wrist: \n{joints}"; //+
            //    $"subject_vertices_pos_rel2wrist: \n{vertices}";
    }
}



public class ObjectTransformAssignment : MonoBehaviour
{
    private GameObject[] objects;
    public string fileName; //"rotation_candidates_check_all";
    private Dictionary<string, ObjectTransformData> transformData;

    public List<Tuple<string, string>> RotationSeqNameObjectList = new List<Tuple<string, string>>();
    
    // Start is called before the first frame update
    void Start()
    {
        objects = GetComponent<TrackData>().Objects;
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
        
        transformData = JsonConvert.DeserializeObject<Dictionary<string, ObjectTransformData>>(jsonContent);

        // Debug.Log("Loaded transform candidates");
       
    }

    void AssignRandomTransformToGameObjectSet()
    {
        // Set up the R_unity2python transformation
        Matrix4x4 T_unity2python = new Matrix4x4(
                                                    new Vector4(-1,  0,  0, 0),
                                                    new Vector4(0,  1,  0, 0),
                                                    new Vector4(0,  0,  1, 0),
                                                    new Vector4(0,  0,  0, 1)
                                                );
        Matrix4x4 T_python2unity = T_unity2python.inverse;
        Matrix4x4 T_camera = new Matrix4x4(
            new Vector4(1, 0, 0, 0),
            new Vector4(0, 0, -1, 0),
            new Vector4(0, 1, 0, 0),
            new Vector4(0, 0, 0, 1)
        );
        // Matrix4x4 T_python2unity = T_unity2python;

        for (int i = 0; i < objects.Length; i++)
        {
            GameObject current_object = objects[i];
           
            string object_name = current_object.name;
        
            object_name = object_name.Replace("_", "");

            Debug.Log($"object_name: {object_name}");

            ObjectTransformData object_transform_set = transformData[object_name];

            int randomIndex = UnityEngine.Random.Range(0, object_transform_set.seq_name.Count);
            // int randomIndex = 3;
            // if (object_name == "waterbottle")
            //     randomIndex = 290;

            List<List<float>> object_rotation_matrix = object_transform_set.object_rotation[randomIndex];


            //Create a Matrix4x4 and populate its rotation component
            Matrix4x4 matrix_python = new Matrix4x4();
            matrix_python.SetRow(0, new Vector4(object_rotation_matrix[0][0], object_rotation_matrix[0][1], object_rotation_matrix[0][2], 0));
            matrix_python.SetRow(1, new Vector4(object_rotation_matrix[1][0], object_rotation_matrix[1][1], object_rotation_matrix[1][2], 0));
            matrix_python.SetRow(2, new Vector4(object_rotation_matrix[2][0], object_rotation_matrix[2][1], object_rotation_matrix[2][2], 0));
            matrix_python.SetRow(3, new Vector4(0, 0, 0, 1));  // Set the last row for a valid transformation matrix
            // Debug.Log("-------");
            // Debug.Log(matrix_python.GetRow(0));
            // Debug.Log(matrix_python.GetRow(1));
            // Debug.Log(matrix_python.GetRow(2));
            // Debug.Log(matrix_python.GetRow(3));

            Matrix4x4 matrix_unity = T_camera* T_unity2python * matrix_python * T_unity2python;

            // Quaternion rotation_unity = matrix_unity.rotation;
            Quaternion rotation_unity = new Quaternion(0f, 0.7071068f, 0.7071068f, 0f);

            current_object.transform.rotation = rotation_unity;
            
            // Extract rotation as Quaternion and translation as Vector3
            // Quaternion rotation_unity = Quaternion.Euler(
            //                                 Mathf.Rad2Deg * -20.875f, 
            //                                 Mathf.Rad2Deg * -85.646f, 
            //                                 Mathf.Rad2Deg * -114.245f
            //                             ); // matrix_unity.rotation;

//            current_object.transform.rotation = new Vector3(-20.875f, -85.646f, -114.245f); //rotation_unity;
//            current_object.transform.eulerAngles = new Vector3(-20.875f, -85.646f, -114.245f);

            Matrix4x4 rotationMatrix = Matrix4x4.Rotate(current_object.transform.rotation);
            string matrixString = "";
            for (int id = 0; id < 3; id++)
            {
               matrixString += matrix_python[id, 0].ToString("F3") + " " +
                               matrix_python[id, 1].ToString("F3") + " " +
                               matrix_python[id, 2].ToString("F3") + "\n";
            }
            Debug.Log("Rotation Matrix:\n" + matrixString);
            // current_object.transform.eulerAngles = new Vector3(-84.0f, -0.3f, -117.03f);
            // Debug.Log($"object_quaternion: ({current_object.transform.rotation.w}, {current_object.transform.rotation.x}, {current_object.transform.rotation.y}, {current_object.transform.rotation.z})");
            // current_object.transform.position = object_translation;
            Debug.Log($"Assigned {object_name} from {object_transform_set.seq_name[randomIndex]} index {randomIndex} with matrix"  + string.Join(", ", object_rotation_matrix));

            RotationSeqNameObjectList.Add(new Tuple<string, string>(object_name, object_transform_set.seq_name[randomIndex]));

            // === HAND JOINTS VISUALIZATION ===
            // List<float> object_translation_list = object_transform_set.object_translation[randomIndex];
            // Vector3 object_translation = new Vector3(object_translation_list[0], object_translation_list[1], object_translation_list[2]);
            // List<List<float>> joint_positions = object_transform_set.subject_joints_pos_rel2wrist[randomIndex];
            // joint_positions.Add(new List<float> { 0.0f, 0.0f, 0.0f }); // Add the root joint
            // Matrix4x4 transformationMatrix = T_camera * T_python2unity;
            // foreach (Transform child in current_object.transform)
            // {
            //   if (child.name.StartsWith("Joint_"))
            //   {
            //       Destroy(child.gameObject);  // Clear previous joints
            //   }
            // }

            // for (int j = 0; j < joint_positions.Count; j++)
            // {
            //   Vector3 joint_position = new Vector3(joint_positions[j][0], joint_positions[j][1], joint_positions[j][2]);

            //   // Apply transformation to align with Unity's coordinate system
            //   joint_position =T_python2unity.MultiplyPoint3x4(joint_position - object_translation);

            //   // Instantiate a sphere at each joint position
            //   GameObject jointSphere = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            //   jointSphere.transform.position = current_object.transform.position + joint_position;
            //   jointSphere.transform.localScale = Vector3.one * 0.01f; // Small sphere size
            //   jointSphere.name = $"Joint_{i}";
            //   jointSphere.transform.parent = current_object.transform;

            //   // Change color of the first joint
            //    Renderer renderer = jointSphere.GetComponent<MeshRenderer>();
            //    if (renderer != null)
            //    {
            //        if (j == 20)
            //        {
            //            renderer.material.color = Color.red; // Set first joint to red
            //        }
            //        else if (j == 0 || j == 1 || j == 2 || j ==3)
            //        {
            //            renderer.material.color = Color.blue; // Default color for others
            //        }
            //        else if (j == 4 || j == 5 || j == 6 || j ==7)
            //        {
            //            renderer.material.color = Color.green; // Default color for others
            //        }
            //        else if (j == 8 || j == 9 || j == 10 || j ==11)
            //        {
            //            renderer.material.color = Color.yellow; // Default color for others
            //        }
            //        else if (j == 12 || j == 13 || j == 14 || j ==15)
            //        {
            //            renderer.material.color = Color.black; // Default color for others
            //        }
            //    }

            // }

        }
    }
}
