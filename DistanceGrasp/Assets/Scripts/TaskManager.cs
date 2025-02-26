using Oculus.Interaction.HandGrab;
using Oculus.Interaction;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using TMPro;
using System;

public class TaskManager : MonoBehaviour
{
    public DistanceHandGrabInteractor interactor;
    public List<GameObject> TrailObjects;
    public List<GameObject> TargetObjects;
    public GameObject AllObjects;

    public GameObject HintUI;
    private TextMeshProUGUI HintText;
    public GameObject InstructionUI;
    private TextMeshProUGUI InstructionText;

    private int Session = 0;
    private int CurrentIndex = 0;
    // Start is called before the first frame update
    void Start()
    {
        if (TrailObjects == null || TargetObjects == null)
        {
            Debug.LogError("Cannot find the Target Object.");
        }

        interactor.OnSelectTrue += HandleSelectTrue;
        interactor.OnSelectFalse += HandleSelectFalse;

        GameObject instructionTextObject = GameObject.Find("InstructionText");
        if (instructionTextObject != null)
        {
            InstructionText = instructionTextObject.GetComponent<TextMeshProUGUI>();
        }
        HintText = HintUI.GetComponentInChildren<TextMeshProUGUI>();

        // Start Trail GUI
        string WelcomeText = "Welcome to our user study. " +
            "Before our real experience, we'll start with a trial. Please follow our instruction to" +
            $" grasp the highlighted\n <color=#FFFF00>{TrailObjects[CurrentIndex].name}</color>.";
        InstructionText.text = WelcomeText;
        InstructionUI.SetActive(true);
        HintUI.SetActive(false);
    }

    // Update is called once per frame
    void Update()
    {
        ;
    }

    public void Reset()
    {
        interactor.ResetPerformance();
        AllObjects.GetComponent<Reset>().OnButtonClick();
    }

    public void DisplayHint(string curText, float delay)
    {
        HintText.text = curText;
        HintUI.SetActive(true);
        StartCoroutine(DisableObjAfterDelay(delay));
    }

    private IEnumerator DisableObjAfterDelay(float delay)
    {
        yield return new WaitForSeconds(delay);
        HintUI.SetActive(false);
    }

    public void HandleSelectTrue(object sender, EventArgs e)
    {
        if (Session == 1) 
        {
            GetRightObjInTrail();
        }
        else if (Session == 2)
        {
            GetRightObjInTest();
        } else
        {
            Debug.LogError("Run out of the circle.");
        }
    } 
    
    public void HandleSelectFalse(object sender, EventArgs e)
    {
        GetWrongObj();
    }

    #region Trail
    // On Click Welcome GUI's button
    public void StartTrail()
    {
        Session = 1;
        interactor.TargetObject = TrailObjects[CurrentIndex];
        interactor.Target = TrailObjects[CurrentIndex].GetComponentInChildren<DistanceHandGrabInteractable>();
        Reset();
    }

    public void GetRightObjInTrail()
    {
        CurrentIndex++;
        // If finish all the objects in Trail, continue to test
        if (CurrentIndex == TrailObjects.Count)
        {
            AllObjects.GetComponent<Reset>().OnButtonClick();
            CurrentIndex = 0;
            StartTest();
            return;
        }
        AllObjects.GetComponent<Reset>().OnButtonClick();

        string SuccessText = $"Great! Let's go with \n <color=#FFFF00>{TrailObjects[CurrentIndex].name}</color>.";
        DisplayHint(SuccessText, 2f);

        interactor.TargetObject = TrailObjects[CurrentIndex];
        interactor.Target = TrailObjects[CurrentIndex].GetComponentInChildren<DistanceHandGrabInteractable>();
        interactor.ResetPerformance();
    }

    public void GetWrongObj()
    {
        string FailureText = "<color=#f56969>Oops, you failed! Please Try again.</color>";
        DisplayHint(FailureText, 1.5f);
    }
    #endregion

    #region Test
    public void StartTest()
    {
        Session = 2;
        interactor.TargetObject = TargetObjects[CurrentIndex];
        interactor.Target = TargetObjects[CurrentIndex].GetComponentInChildren<DistanceHandGrabInteractable>();
        Reset();

        string TransitionText = "Great! You've finished the trail. " +
            $"Now let's start the test. \nFirst get <color=#FFFF00>{TargetObjects[CurrentIndex].name}</color>.";
        DisplayHint(TransitionText, 6f);
    }

    public void GetRightObjInTest()
    {
        CurrentIndex++;
        // If finish all the objects in test, return
        if (CurrentIndex == TargetObjects.Count)
        {
            AllObjects.GetComponent<Reset>().OnButtonClick();
            string CongratsText = "Congrats! You've finished all the test.";
            DisplayHint(CongratsText, 3f);
            return;
        }
        AllObjects.GetComponent<Reset>().OnButtonClick();

        string SuccessText1 = $"Good! How about \n <color=#FFFF00>{TargetObjects[CurrentIndex].name}</color>?";
        string SuccessText2 = $"Great! Let's go with \n <color=#FFFF00>{TargetObjects[CurrentIndex].name}</color>.";
        string SuccessText3 = $"Well done! Next is \n <color=#FFFF00>{TargetObjects[CurrentIndex].name}</color>.";

        DisplayHint(RandomPicker(new List<string> {SuccessText1, SuccessText2, SuccessText3}), 2f);
        interactor.TargetObject = TargetObjects[CurrentIndex];
        interactor.Target = TargetObjects[CurrentIndex].GetComponentInChildren<DistanceHandGrabInteractable>();
        interactor.ResetPerformance();
    }
    #endregion

    private string RandomPicker(List<string> TextList)
    {
        System.Random random = new System.Random();
        int choice = random.Next(0, TextList.Count - 1);
        return TextList[choice];
    }
}