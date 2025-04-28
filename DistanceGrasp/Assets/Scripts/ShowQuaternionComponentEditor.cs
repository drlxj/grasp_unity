using UnityEngine;
using UnityEditor;

[CustomEditor(typeof(ShowQuaternionComponent))]
public class ShowQuaternionComponentEditor : Editor
{
    public override void OnInspectorGUI()
    {

        DrawDefaultInspector();


        ShowQuaternionComponent comp = (ShowQuaternionComponent)target;
        Transform t = comp.transform;
        Quaternion q = t.rotation;


        EditorGUILayout.Space();
        EditorGUILayout.LabelField("Quaternion (Read-Only)", EditorStyles.boldLabel);
        EditorGUILayout.Vector4Field("Rotation (x, y, z, w)", new Vector4(q.x, q.y, q.z, q.w));
        
        string quaternionFormatted = $"[{q.x:F2}, {q.y:F2}, {q.z:F2}, {q.w:F2}]";
        EditorGUILayout.LabelField("Formatted Quaternion:", quaternionFormatted);

        float norm = Mathf.Sqrt(q.x * q.x + q.y * q.y + q.z * q.z + q.w * q.w);
        EditorGUILayout.LabelField("Norm (Magnitude):", norm.ToString("F6"));

        if (Mathf.Abs(norm - 1f) < 1e-4f)
        {
            EditorGUILayout.HelpBox("This is a unit quaternion ✅", MessageType.Info);
        }
        else
        {
            EditorGUILayout.HelpBox("This is NOT a unit quaternion ❌", MessageType.Warning);
        }
    }
}
