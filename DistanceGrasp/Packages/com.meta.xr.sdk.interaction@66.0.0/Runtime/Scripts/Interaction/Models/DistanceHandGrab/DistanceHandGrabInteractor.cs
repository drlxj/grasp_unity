/*
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 * All rights reserved.
 *
 * Licensed under the Oculus SDK License Agreement (the "License");
 * you may not use the Oculus SDK except in compliance with the License,
 * which is provided at the time of installation or download, or which
 * otherwise accompanies this software in either electronic or hard copy form.
 *
 * You may obtain a copy of the License at
 *
 * https://developer.oculus.com/licenses/oculussdk/
 *
 * Unless required by applicable law or agreed to in writing, the Oculus SDK
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

using Oculus.Interaction.Grab;
using Oculus.Interaction.GrabAPI;
using Oculus.Interaction.Input;
using Oculus.Interaction.Throw;
using System;
using System.IO;
using System.Collections.Generic;
using UnityEngine;

// TODO: there are many changes, try to understand all and create documentation

namespace Oculus.Interaction.HandGrab
{
    /// <summary>
    /// DistanceHandGrabInteractor lets you grab interactables at a distance with hands.
    /// It operates with HandGrabPoses to specify the final pose of the hand and manipulate the objects
    /// via IMovements in order to attract them, use them at a distance, etc.
    /// The DistanceHandGrabInteractor uses a IDistantCandidateComputer to detect far-away objects.
    /// </summary>
    public class DistanceHandGrabInteractor :
        PointerInteractor<DistanceHandGrabInteractor, DistanceHandGrabInteractable>,
        IHandGrabInteractor, IDistanceInteractor
    {
        #region CUSTOM
        [HideInInspector]
        public string UserID = "test";
        [HideInInspector]
        public float GestureWeight {get; set; }
        public bool DebugSwitch {get; set;}
        public List<string> candidateScores = new List<string>(); // ours: List to store the scores

        
        [HideInInspector]
        public GameObject GhostHand;
        [HideInInspector]
        public GameObject HandVisual;
        private bool Calibration;


        [HideInInspector]
        public GameObject TargetObject { get; set; }
        public GameObject LastObject { get; set; }
        public DistanceHandGrabInteractable Target {  get; set; }
        public float CatchTime { get; set; }
        public float StartTime { get; set; }
        private float TimeThreshold = 30f;
        private int MaxAttempt = 8;
        public int AttemptCount { get; set; }
        private bool RightObject;
        private string csvFilePath;
        
        public bool IsGestureProbability {  get; set; }
        public Dictionary<string, float> GestureProbabilityList { get; set; }
        public Dictionary<string, Vector3> RelativePosList { get; set; }

        public event EventHandler OnSelectTrue;
        public event EventHandler OnSelectEnd;
        public event EventHandler OnSelectFalse;
        public event EventHandler OnSelectInterrupt;

        #endregion

        /// <summary>
        /// The <cref="IHand" /> to use.
        /// </summary>
        [Tooltip("The hand to use.")]
        [SerializeField, Interface(typeof(IHand))]
        private UnityEngine.Object _hand;
        public IHand Hand { get; private set; }

        /// <summary>
        /// Detects when the hand grab selects or unselects.
        /// </summary>
        [Tooltip("Detects when the hand grab selects or unselects.")]
        [SerializeField]
        private HandGrabAPI _handGrabApi;

        [Header("Grabbing")]

        /// <summary>
        /// The grab types to support.
        /// </summary>
        [Tooltip("The grab types to support.")]
        [SerializeField]
        private GrabTypeFlags _supportedGrabTypes = GrabTypeFlags.All;

        /// <summary>
        /// The point on the hand used as the origin of the grab.
        /// </summary>
        [Tooltip("The point on the hand used as the origin of the grab.")]
        [SerializeField]
        private Transform _grabOrigin;

        /// <summary>
        /// Specifies an offset from the wrist that can be used to search for the best HandGrabInteractable available,
        /// act as a palm grab without a HandPose, and also act as an anchor for attaching the object.
        /// </summary>
        [Tooltip("Specifies an offset from the wrist that can be used to search for the best HandGrabInteractable available, act as a palm grab without a HandPose, and also act as an anchor for attaching the object.")]
        [SerializeField, Optional]
        private Transform _gripPoint;

        /// <summary>
        /// Specifies a moving point at the center of the tips of the currently pinching fingers.
        /// It's used to align interactables that don’t have a HandPose to the center of the pinch.
        /// </summary>
        [Tooltip("Specifies a moving point at the center of the tips of the currently pinching fingers. It's used to align interactables that don’t have a HandPose to the center of the pinch.")]
        [SerializeField, Optional]
        private Transform _pinchPoint;

        /// <summary>
        /// Determines how the object will move when thrown.
        /// </summary>
        [Tooltip("Determines how the object will move when thrown.")]
        [SerializeField, Interface(typeof(IThrowVelocityCalculator)), Optional(OptionalAttribute.Flag.Obsolete)]
        [Obsolete("Use " + nameof(Grabbable) + " instead")]
        private UnityEngine.Object _velocityCalculator;
        [Obsolete("Use " + nameof(Grabbable) + " instead")]
        public IThrowVelocityCalculator VelocityCalculator { get; set; }


        [SerializeField]
        private DistantCandidateComputer<DistanceHandGrabInteractor, DistanceHandGrabInteractable> _distantCandidateComputer
            = new DistantCandidateComputer<DistanceHandGrabInteractor, DistanceHandGrabInteractable>();

        private bool _handGrabShouldSelect = false;
        private bool _handGrabShouldUnselect = false;

        private HandGrabResult _cachedResult = new HandGrabResult();
        private GrabTypeFlags _currentGrabType = GrabTypeFlags.None;

        #region IHandGrabInteractor
        public IMovement Movement { get; set; }
        public bool MovementFinished { get; set; }

        public HandGrabTarget HandGrabTarget { get; } = new HandGrabTarget();

        public Transform WristPoint => _grabOrigin;
        public Transform PinchPoint => _pinchPoint;
        public Transform PalmPoint => _gripPoint;

        public HandGrabAPI HandGrabApi => _handGrabApi;
        public GrabTypeFlags SupportedGrabTypes => _supportedGrabTypes;
        public IHandGrabInteractable TargetInteractable => Interactable;
        #endregion

        public Pose Origin => _distantCandidateComputer.Origin;
        public Vector3 HitPoint { get; private set; }
        public IRelativeToRef DistanceInteractable => this.Interactable;

        #region IHandGrabState
        public virtual bool IsGrabbing => HasSelectedInteractable
            && (Movement != null && Movement.Stopped);
        public float FingersStrength { get; private set; }
        public float WristStrength { get; private set; }
        public Pose WristToGrabPoseOffset { get; private set; }

        /// <summary>
        /// Returns the fingers that are grabbing the interactable.
        /// </summary>
        public HandFingerFlags GrabbingFingers()
        {
            return this.GrabbingFingers(SelectedInteractable);
        }
        #endregion

        #region editor events
        protected virtual void Reset()
        {
            _hand = this.GetComponentInParent<IHand>() as MonoBehaviour;
            _handGrabApi = this.GetComponentInParent<HandGrabAPI>();
        }
        #endregion

        protected override void Awake()
        {
            base.Awake();
            Hand = _hand as IHand;
            VelocityCalculator = _velocityCalculator as IThrowVelocityCalculator;
            _nativeId = 0x4469737447726162;
        }


        protected override void Start()
        {
            this.BeginStart(ref _started, () => base.Start());
            this.AssertField(Hand, nameof(Hand));
            this.AssertField(_handGrabApi, nameof(_handGrabApi));
            this.AssertField(_distantCandidateComputer, nameof(_distantCandidateComputer));
            if (_velocityCalculator != null)
            {
                this.AssertField(VelocityCalculator, nameof(VelocityCalculator));
            }
            this.EndStart(ref _started);
            this.IsGestureProbability = false;
            this._distantCandidateComputer.DebugSwitch = DebugSwitch;
            this.RightObject = false;
            InitialLogFile(out csvFilePath);
            // TargetObject.GetComponentInChildren<MeshRenderer>().material.SetFloat("_Highlighted", 1);
        }

        private bool IsObjectPlacedCorrectly()
        {
            bool positionCorrect = Vector3.Distance(this.GetHandGrabPose().position, GhostHand.transform.position) < 0.5f;
            bool rotationCorrect = Mathf.Abs(Quaternion.Angle(this.GetHandGrabPose().rotation, GhostHand.transform.rotation)-90f) < 5f;
            // Debug.Log($"Rotation: {Quaternion.Angle(this.GetHandGrabPose().rotation, GhostHand.transform.rotation)}, Calibration: {Calibration}");
            return positionCorrect && rotationCorrect;
        }

        #region Custom Function
        public void ResetPerformance()
        {
            this.StartTime = Time.time;
            this.CatchTime = 0f;
            this.AttemptCount = 0;
        }

        public void ReHighlight()
        {
            if (LastObject != null)
            {
                LastObject.GetComponentInChildren<MeshRenderer>().sharedMaterial.SetFloat("_Highlighted", 0);
            }

            TargetObject.GetComponentInChildren<MeshRenderer>().sharedMaterial.SetFloat("_Highlighted", 1);
        }
        #endregion

        #region life cycle
        protected override void DoHoverUpdate()
        {
            base.DoHoverUpdate();

            _handGrabShouldSelect = false;

            if (Interactable == null)
            {
                return;
            }

            UpdateTarget(Interactable);

            // Decide pitch or Grab
            _currentGrabType = this.ComputeShouldSelect(Interactable);
            if (_currentGrabType != GrabTypeFlags.None)
            {
                _handGrabShouldSelect = true;
            }
        }

        protected override void InteractableSet(DistanceHandGrabInteractable interactable)
        {
            base.InteractableSet(interactable);
            UpdateTarget(Interactable);
        }

        protected override void InteractableUnset(DistanceHandGrabInteractable interactable)
        {
            base.InteractableUnset(interactable);
            SetGrabStrength(0f);
        }

        /*
        * NOTE:
        * Update the target position of the target
        */
        protected override void DoSelectUpdate()
        {
            _handGrabShouldUnselect = false;
            if (SelectedInteractable == null)
            {
                _handGrabShouldUnselect = true;
                return;
            }

            Vector3 offset = Vector3.zero;
            if (IsGestureProbability)
            {   
                // todo
                offset = RelativePosList[SelectedInteractable.GetObjName()];
                SelectedInteractable.ObjectOffset = offset;
            }

            UpdateTargetSliding(SelectedInteractable);

            Pose handGrabPose = this.GetHandGrabPose();
            Movement.UpdateTarget(handGrabPose);
            Movement.Tick();

            GrabTypeFlags selectingGrabs = this.ComputeShouldSelect(SelectedInteractable);
            GrabTypeFlags unselectingGrabs = this.ComputeShouldUnselect(SelectedInteractable);
            _currentGrabType |= selectingGrabs;
            _currentGrabType &= ~unselectingGrabs;

            if (unselectingGrabs != GrabTypeFlags.None
                && _currentGrabType == GrabTypeFlags.None)
            {
                _handGrabShouldUnselect = true;

            }
        }

        /*
        * NOTE:
        * Initial the target position of object
        */
        protected override void InteractableSelected(DistanceHandGrabInteractable interactable)
        {
            if (interactable != null)
            {
                // TODO: after selection, add predicted offset
                WristToGrabPoseOffset = this.GetGrabOffset();
                this.Movement = this.GenerateMovement(interactable);
                SetGrabStrength(1f);
                
                /*
                 Decide if the target is chosen correctly
                 */
                if (interactable.ObjID == Target.ObjID)
                {
                    RightObject = true;
                    CatchTime = Time.time - StartTime;
                    AttemptCount++;
                    LastObject = TargetObject;
                    Debug.Log($"Log: {CatchTime}s used for catching {interactable.GetObjName()}, total attempt: {AttemptCount}.");
                    AppendInfo(interactable, CatchTime, AttemptCount);
                    // Need to Reset
                    OnSelectTrue?.Invoke(this, EventArgs.Empty);
                } 
                else
                {
                    RightObject = false;
                    AttemptCount++;
                    // if (AttemptCount >= MaxAttempt) {
                    //     CatchTime = Time.time - StartTime;
                    //     LastObject = TargetObject;
                    //     Debug.Log($"Log: {CatchTime}s used for trying to catch {interactable.GetObjName()} but failed with {AttemptCount} chance.");
                    //     AppendInfo(interactable, CatchTime, AttemptCount);
                    //     OnSelectInterrupt?.Invoke(this, EventArgs.Empty);
                    // }
                    OnSelectFalse?.Invoke(this, EventArgs.Empty);
                }
            }

            // Only when the Movement is null it will recompute the position
            base.InteractableSelected(interactable);
        }

        protected override void InteractableUnselected(DistanceHandGrabInteractable interactable)
        {
            base.InteractableUnselected(interactable);
            OnSelectEnd?.Invoke(this, EventArgs.Empty);
            this.Movement = null;
            _currentGrabType = GrabTypeFlags.None;

            ReleaseVelocityInformation throwVelocity = VelocityCalculator != null ?
                VelocityCalculator.CalculateThrowVelocity(interactable.transform) :
                new ReleaseVelocityInformation(Vector3.zero, Vector3.zero, Vector3.zero);
            interactable.ApplyVelocities(throwVelocity.LinearVelocity, throwVelocity.AngularVelocity);
        }

        protected override void HandlePointerEventRaised(PointerEvent evt)
        {
            base.HandlePointerEventRaised(evt);

            if (SelectedInteractable == null
                || !SelectedInteractable.ResetGrabOnGrabsUpdated)
            {
                return;
            }

            if (evt.Identifier != Identifier &&
                (evt.Type == PointerEventType.Select || evt.Type == PointerEventType.Unselect))
            {
                // TODO: remains to find the reference
                WristToGrabPoseOffset = this.GetGrabOffset();
                SetTarget(SelectedInteractable, _currentGrabType);
                this.Movement = this.GenerateMovement(SelectedInteractable);

                Pose fromPose = this.GetTargetGrabPose();
                PointerEvent pe = new PointerEvent(Identifier, PointerEventType.Move, fromPose, Data);
                SelectedInteractable.PointableElement.ProcessPointerEvent(pe);
            }
        }

        protected override Pose ComputePointerPose()
        {
            if (Movement != null)
            {
                return Movement.Pose;
            }
            return this.GetHandGrabPose();
        }

        #endregion

        protected override bool ComputeShouldSelect()
        {
            return _handGrabShouldSelect;
        }

        protected override bool ComputeShouldUnselect()
        {
            return _handGrabShouldUnselect;
        }

        public override bool CanSelect(DistanceHandGrabInteractable interactable)
        {
            if (!base.CanSelect(interactable))
            {
                return false;
            }
            return this.CanInteractWith(interactable);
        }

        /*
         * NOTE: 
         * Compute both the shape probability and position probability to decide which object to choose
         */
        protected override DistanceHandGrabInteractable ComputeCandidate()
        {
            // Add Shape Probability
            DistanceHandGrabInteractable interactable;
            if (IsGestureProbability)
            {
                this._distantCandidateComputer.GestureWeight = GestureWeight;
                interactable = _distantCandidateComputer.ComputeCandidate(
                DistanceHandGrabInteractable.Registry, this, GestureProbabilityList, out Vector3 bestHitPoint);
                HitPoint = bestHitPoint;
                candidateScores = this._distantCandidateComputer.candidateScores;
            } 
            else
            {
                return null;
                interactable = _distantCandidateComputer.ComputeCandidate(
                DistanceHandGrabInteractable.Registry, this, out Vector3 bestHitPoint);
                HitPoint = bestHitPoint;
            }
            

            if (interactable == null)
            {
                return null;
            }

            GrabTypeFlags selectingGrabTypes = SelectingGrabTypes(interactable);
            GrabPoseScore score = this.GetPoseScore(interactable, selectingGrabTypes, ref _cachedResult);

            if (score.IsValid())
            {
                return interactable;
            }

            return null;
        }

        private GrabTypeFlags SelectingGrabTypes(IHandGrabInteractable interactable)
        {
            GrabTypeFlags selectingGrabTypes;
            if (State == InteractorState.Select
                || (selectingGrabTypes = this.ComputeShouldSelect(interactable)) == GrabTypeFlags.None)
            {
                HandGrabInteraction.ComputeHandGrabScore(this, interactable, out selectingGrabTypes);
            }

            if (selectingGrabTypes == GrabTypeFlags.None)
            {
                selectingGrabTypes = interactable.SupportedGrabTypes & this.SupportedGrabTypes;
            }

            return selectingGrabTypes;
        }

        private void UpdateTarget(IHandGrabInteractable interactable)
        {
            DistanceHandGrabInteractable tmp = interactable as DistanceHandGrabInteractable;
            Vector3 offset;
            if (IsGestureProbability)
            {
                offset = RelativePosList[tmp.GetObjName()];
            }
            else
            {
                offset = new Vector3(0,0,0);
            }
            // TODO: GetPoseOffset in HandGrabInteraction.cs are be refered in many areas
            Pose pose;
            this.Hand.GetRootPose(out pose);
            this.PinchPoint.position = offset + pose.position; 
            // Debug.Log("pred offset: " + offset.ToString());
            // Debug.Log("pred object position: " + PinchPoint.position.ToString());
            
            
            WristToGrabPoseOffset = this.GetGrabOffset();
            GrabTypeFlags selectingGrabTypes = SelectingGrabTypes(interactable);
            SetTarget(interactable, selectingGrabTypes);
            float grabStrength = HandGrabInteraction.ComputeHandGrabScore(this, interactable, out _);
            SetGrabStrength(grabStrength);
        }

        private void UpdateTargetSliding(IHandGrabInteractable interactable)
        {
            if (interactable.Slippiness <= 0f)
            {
                return;
            }
            float grabStrength = HandGrabInteraction.ComputeHandGrabScore(this, interactable,
                out GrabTypeFlags selectingGrabTypes, true);
            if (grabStrength <= interactable.Slippiness)
            {
                SetTarget(interactable, selectingGrabTypes);
            }
        }

        private void SetTarget(IHandGrabInteractable interactable, GrabTypeFlags selectingGrabTypes)
        {
            this.CalculateBestGrab(interactable, selectingGrabTypes, out GrabTypeFlags activeGrabType, ref _cachedResult);
            HandGrabTarget.Set(interactable.RelativeTo, interactable.HandAlignment, activeGrabType, _cachedResult);
        }

        private void SetGrabStrength(float strength)
        {
            FingersStrength = strength;
            WristStrength = strength;
        }

        private void InitialLogFile(out string csvFilePath)
        {
            string csvFileFolder = "../DistanceGrasp/Assets/LogData";
            csvFilePath = Path.Combine(csvFileFolder, UserID + "_RecordData.csv");

            using (StreamWriter writer = new StreamWriter(csvFilePath, false))
            {
                writer.WriteLine("ObjId, Name, CatchDuration, FirstSuccess, AttemptCount");
            }
        }

        private void AppendInfo(DistanceHandGrabInteractable obj, float time, int cnt)
        {
            int firstChance = cnt == 1 ? 1 : 0;
            using (StreamWriter writer = new StreamWriter(csvFilePath, true))
            {
                writer.WriteLine($" {obj.ObjID}, {obj.GetObjName()}, {time}, {firstChance}, {cnt}");
            }
        }


        #region Inject
        /// <summary>
        /// Adds a <cref="DistanceHandGrabInteractor"/> to a dynamically instantiated GameObject.
        /// </summary>
        public void InjectAllDistanceHandGrabInteractor(HandGrabAPI handGrabApi,
            DistantCandidateComputer<DistanceHandGrabInteractor, DistanceHandGrabInteractable> distantCandidateComputer,
            Transform grabOrigin,
            IHand hand, GrabTypeFlags supportedGrabTypes)
        {
            InjectHandGrabApi(handGrabApi);
            InjectDistantCandidateComputer(distantCandidateComputer);
            InjectGrabOrigin(grabOrigin);
            InjectHand(hand);
            InjectSupportedGrabTypes(supportedGrabTypes);
        }

        /// <summary>
        /// Adds a <cref="HandGrabAPI"/> to a dynamically instantiated GameObject.
        /// </summary>
        public void InjectHandGrabApi(HandGrabAPI handGrabApi)
        {
            _handGrabApi = handGrabApi;
        }

        /// <summary>
        /// Adds a <cref="DistantCandidateComputer"/> to a dynamically instantiated GameObject.
        /// </summary>
        public void InjectDistantCandidateComputer(
            DistantCandidateComputer<DistanceHandGrabInteractor, DistanceHandGrabInteractable> distantCandidateComputer)
        {
            _distantCandidateComputer = distantCandidateComputer;
        }

        /// <summary>
        /// Adds an <cref="IHand"/> to a dynamically instantiated GameObject.
        /// </summary>
        public void InjectHand(IHand hand)
        {
            _hand = hand as UnityEngine.Object;
            Hand = hand;
        }

        /// <summary>
        /// Adds a list of supported grabs to a dynamically instantiated GameObject.
        /// </summary>
        public void InjectSupportedGrabTypes(GrabTypeFlags supportedGrabTypes)
        {
            _supportedGrabTypes = supportedGrabTypes;
        }

        /// <summary>
        /// Adds a grab origin to a dynamically instantiated GameObject.
        /// </summary>
        public void InjectGrabOrigin(Transform grabOrigin)
        {
            _grabOrigin = grabOrigin;
        }

        /// <summary>
        /// Adds a grip point to a dynamically instantiated GameObject.
        /// </summary>
        public void InjectOptionalGripPoint(Transform gripPoint)
        {
            _gripPoint = gripPoint;
        }

        /// <summary>
        /// Adds a pinch point to a dynamically instantiated GameObject.
        /// </summary>
        public void InjectOptionalPinchPoint(Transform pinchPoint)
        {
            _pinchPoint = pinchPoint;
        }

        /// <summary>
        /// Adds a <cref="IThrowVelocityCalculator"/> to a dynamically instantiated GameObject.
        /// </summary>
        [Obsolete("Use " + nameof(Grabbable) + " instead")]
        public void InjectOptionalVelocityCalculator(IThrowVelocityCalculator velocityCalculator)
        {
            _velocityCalculator = velocityCalculator as UnityEngine.Object;
            VelocityCalculator = velocityCalculator;
        }
        #endregion
    }
}
