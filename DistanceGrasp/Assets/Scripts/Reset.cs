using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class Reset : MonoBehaviour
{

    private Dictionary<Transform, (Vector3, Quaternion)> initialTransforms = new Dictionary<Transform, (Vector3, Quaternion)>();

    // Start is called before the first frame update
    void Start()
    {
        StoreInitialTransforms(transform);
    }

    private void StoreInitialTransforms(Transform currentTransform)
    {
        foreach (Transform child in currentTransform)
        {
            initialTransforms[child] = (child.localPosition, child.localRotation);
            StoreInitialTransforms(child);
        }
    }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.Space))
        {
            OnButtonClick();
        }
    }

    public void OnButtonClick()
    {
        foreach (KeyValuePair<Transform, (Vector3, Quaternion)> entry in initialTransforms)
        {
            entry.Key.localPosition = entry.Value.Item1; 
            entry.Key.localRotation = entry.Value.Item2; 
        }
    }
}
