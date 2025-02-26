using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class Calibration : MonoBehaviour
{
    public GameObject HandVisual;

    public bool IsObjectPlacedCorrectly()
    {
        bool positionCorrect = Vector3.Distance(HandVisual.transform.position, this.transform.position) < 0.2f;
        bool rotationCorrect = Quaternion.Angle(HandVisual.transform.rotation, this.transform.rotation) < 15f;

        return positionCorrect && rotationCorrect;
    }
}
