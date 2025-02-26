using UnityEngine;

public class OutlineManager : MonoBehaviour
{
    [SerializeField]
    private Material outlineMaterial;
    private GameObject currentOutline;

    private void OnEnable()
    {
        currentOutline = this.gameObject;
    }

    public void SetOutline(GameObject targetObject)
    {
        if (currentOutline != null)
        {
            Destroy(currentOutline);
        }
        Vector3 fixedPosition = transform.position;
        currentOutline = Instantiate(targetObject, fixedPosition, Random.rotation);
        if (currentOutline.GetComponent<Collider>() != null)
        {
            currentOutline.GetComponent<Collider>().enabled = false; 
        }
        ApplyOutlineMaterial(currentOutline); 

        currentOutline.isStatic = true;
    }

    private void ApplyOutlineMaterial(GameObject outlineObject)
    {
        Renderer[] renderers = outlineObject.GetComponentsInChildren<Renderer>();
        foreach (Renderer renderer in renderers)
        {
            renderer.material = outlineMaterial;
        }
    }

    public bool IsObjectPlacedCorrectly(GameObject targetObject)
    {
        if (currentOutline == null) return false;

        bool positionCorrect = Vector3.Distance(targetObject.transform.position, currentOutline.transform.position) < 0.1f;
        bool rotationCorrect = Quaternion.Angle(targetObject.transform.rotation, currentOutline.transform.rotation) < 5f;

        return positionCorrect && rotationCorrect;
    }
}
