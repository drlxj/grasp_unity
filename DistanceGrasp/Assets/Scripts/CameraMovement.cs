using System.Collections;
using System.Collections.Generic;
using System.Diagnostics.CodeAnalysis;
using UnityEngine;

// Used to store the proposed camera positions when in play mode.
public class CameraMovement : MonoBehaviour
{

    public Transform[] locations; // a list of target camera positions
    public static Transform currentCamera; // current camera position
    private static int currentIndex = 0;

    // Start is called before the first frame update
    private void OnEnable()
    {
        //currentCamera = locations[currentIndex];
    }

    void Start()
    {
        if (locations == null || locations.Length == 0)
        {
            Debug.Log("No effective location.");
            return;
        }
        setLocation();
    }

    // Update is called once per frame
    void Update()
    {
        if (Input.GetKeyDown(KeyCode.D))
        {

            currentIndex = (currentIndex + 1) % locations.Length;
            setLocation();
        }
        else if (Input.GetKeyDown(KeyCode.A))
        {

            currentIndex = (currentIndex - 1 + locations.Length) % locations.Length;
            setLocation();
        }


        //currentCamera = locations[currentIndex];
    }

    private void setLocation()
    {
        transform.position = locations[currentIndex].position;
        transform.rotation = locations[currentIndex].rotation;
    }

    public void GetNext()
    {
        currentIndex = (currentIndex + 1) % locations.Length;
        setLocation();
        currentCamera = locations[currentIndex];
    }

    public void GetLast()
    {
        currentIndex = (currentIndex - 1 + locations.Length) % locations.Length;
        setLocation();
        currentCamera = locations[currentIndex];
    }
}
