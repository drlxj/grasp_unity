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

using Oculus.Interaction.HandGrab;
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace Oculus.Interaction
{
    /// <summary>
    /// This Candidate Computer uses DistantPointDetectorFrustums in order to find the best candidate.
    /// Candidates must implement ICollidersRef in order to be detected by the frustums.
    /// </summary>
    /// <typeparam name="TInteractable"></typeparam>
    [Serializable]
    public class DistantCandidateComputer<TInteractor, TInteractable>
        where TInteractor : Interactor<TInteractor, TInteractable>
        where TInteractable : Interactable<TInteractor, TInteractable>, ICollidersRef
    {
        public bool DebugSwitch {get; set;} // ours: for debug
        public float GestureWeight {  get; set; } // ours: shape weight
        public List<string> candidateScores = new List<string>(); // ours: List to store the scores
        /// <summary>
        /// <cref="ConicalFrustum"> used to detect and select objects.
        /// </summary>
        [Tooltip("Frustum used to detect and select objects.")]
        [SerializeField]
        private DistantPointDetectorFrustums _detectionFrustums;
        public DistantPointDetectorFrustums DetectionFrustums
        {
            get
            {
                return _detectionFrustums;
            }
            set
            {
                _detectionFrustums = value;
                _detector = new DistantPointDetector(value);
            }
        }

        /// <summary>
        /// How long you must hover over an object before it's considered a candidate for interaction.
        /// </summary>
        [Tooltip("How long you must hover over an object before it's considered a candidate for interaction.")]
        [SerializeField]
        private float _detectionDelay = 0f;
        public float DetectionDelay
        {
            get
            {
                return _detectionDelay;
            }
            set
            {
                _detectionDelay = value;
            }
        }

        private float _hoverStartTime;
        private DistantPointDetector _detector;

        private TInteractable _stableCandidate;
        private TInteractable _pointedCandidate;

        public virtual Pose Origin
        {
            get
            {
                return new Pose(_detectionFrustums.SelectionFrustum.StartPoint,
                    Quaternion.LookRotation(_detectionFrustums.SelectionFrustum.Direction));
            }
        }

        /// <summary>
        /// Determines the best available interactable.
        /// </summary>
        public virtual TInteractable ComputeCandidate(
            InteractableRegistry<TInteractor, TInteractable> registry,
            TInteractor interactor,
             out Vector3 bestHitPoint)
        {
            if (_detector == null)
            {
                _detector = new DistantPointDetector(DetectionFrustums);
            }
            if (_stableCandidate != null
                  && _detector.IsPointingWithoutAid(_stableCandidate.Colliders, out bestHitPoint))
            {
                return _stableCandidate;
            }

            if (_stableCandidate != null
                && !_detector.ComputeIsPointing(_stableCandidate.Colliders, false,
                        out float score, out Vector3 hitPoint))
            {
                _stableCandidate = null;
            }

            TInteractable candidate = ComputeBestInteractable(
                registry.List(interactor),
                _stableCandidate == null,
                out bestHitPoint);
            
            if (candidate != _pointedCandidate)
            {
                _pointedCandidate = candidate;
                if (candidate != null)
                {
                    _hoverStartTime = Time.time;
                }
            }

            if ((_stableCandidate == null
                    && candidate != null)
                || (_stableCandidate != null
                    && candidate != null
                    && _stableCandidate != candidate
                    && Time.time - _hoverStartTime >= _detectionDelay))
            {
                _pointedCandidate = null;
                _stableCandidate = candidate;
            }

            return _stableCandidate;
        }

        /// <summary>
        /// Ours: ComputeCandidate() with extra input shape probability
        /// </summary>
        public virtual TInteractable ComputeCandidate(
            InteractableRegistry<TInteractor, TInteractable> registry,
            TInteractor interactor,
            Dictionary<string, float> shapeProbability, 
             out Vector3 bestHitPoint)
        {
            if (_detector == null)
            {
                _detector = new DistantPointDetector(DetectionFrustums);
            }
            if (_stableCandidate != null
                  && _detector.IsPointingWithoutAid(_stableCandidate.Colliders, out bestHitPoint))
            {
                return _stableCandidate;
            }

            if (_stableCandidate != null
                && !_detector.ComputeIsPointing(_stableCandidate.Colliders, false,
                        out float score, out Vector3 hitPoint))
            {
                _stableCandidate = null;
            }

            TInteractable candidate = ComputeBestInteractable(
                registry.List(interactor),
                _stableCandidate == null,
                shapeProbability,
                out bestHitPoint);

            if (candidate != _pointedCandidate)
            {
                _pointedCandidate = candidate;
                if (candidate != null)
                {
                    _hoverStartTime = Time.time;
                }
            }

            if ((_stableCandidate == null
                    && candidate != null)
                || (_stableCandidate != null
                    && candidate != null
                    && _stableCandidate != candidate
                    && Time.time - _hoverStartTime >= _detectionDelay))
            {
                _pointedCandidate = null;
                _stableCandidate = candidate;
            }

            return _stableCandidate;
        }
        
        private TInteractable ComputeBestInteractable(IEnumerable<TInteractable> candidates,
            bool narrowSearch, out Vector3 bestHitPoint)
        {
            TInteractable bestInteractable = null;
            float bestScore = float.NegativeInfinity;
            bestHitPoint = Vector3.zero;

            foreach (TInteractable candidate in candidates)
            {
                if (_detector.ComputeIsPointing(candidate.Colliders, narrowSearch, out float score, out Vector3 hitPoint)
                    && score > bestScore)
                {
                    bestScore = score;
                    bestInteractable = candidate;
                    bestHitPoint = hitPoint;
                }
            }
            return bestInteractable;
        }
        /// <summary>
        /// Ours: ComputeBestInteractable() finds the best Interactable based on both shape and direction
        /// </summary>
        private TInteractable ComputeBestInteractable(IEnumerable<TInteractable> candidates,
            bool narrowSearch, Dictionary<string, float> gestureProbability, out Vector3 bestHitPoint)
        {
            if (gestureProbability.Count != candidates.Count())
            {
                Debug.LogError($"Interable objects mismatch: Python list {gestureProbability.Count}, " +
                    $"Unity list: {candidates.Count()}");
            }

            TInteractable bestInteractable = null;
            float bestScore = 0f; 
            bestHitPoint = Vector3.zero;
            candidateScores.Clear();
            candidateScores.Add($"{"Name",-15} {"Gesture",8} {"Pos",8} {"Weight",8} {"Final",8}");
            foreach (TInteractable candidate in candidates)
            {
                // Get position score of the candidate
                if (!_detector.ComputeIsPointing(candidate.Colliders, narrowSearch, out float posScore, out Vector3 hitPoint))
                    // check if user hand is in vision
                {
                    if (GestureWeight < 0.01) {
                        // use unity method
                        continue;
                    }
                }

                // Get shape score of the candidate
                DistanceHandGrabInteractable tmp = candidate as DistanceHandGrabInteractable;
                string name = tmp.GetObjName();
                float gestureScore = gestureProbability[name];

                if (gestureScore < 0.5)
                {
                    gestureScore = 0.0f;
                }
                    

                // combination
                float finalScore = ComputeFinalScore(gestureScore, posScore, GestureWeight);

                // Store scores for display
                candidateScores.Add($"{name,-15} {gestureScore,8:F4} {posScore,8:F4} {GestureWeight,8:F2} {finalScore,8:F4}");

                if (finalScore > bestScore)
                {
                    bestScore = finalScore;
                    bestInteractable = candidate;
                    bestHitPoint = hitPoint;
                }
            }
            
            return bestInteractable;
        }

        /// <summary>
        /// Ours: Compute final score based on weights
        /// </summary>
        private float ComputeFinalScore(float gestureScore, float posScore, float GestureWeight)
        {   
            if ( posScore < 0.5)
            {
                return 0.0f;
            }
            return GestureWeight * gestureScore + (1 - GestureWeight) * posScore;
        }
    }
}
