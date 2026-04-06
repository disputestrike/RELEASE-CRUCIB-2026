/**
 * CostEstimator — pre-execution cost estimate widget.
 * Shows before plan approval so user knows what they're committing.
 * Props: goal, token, onEstimateReady
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { Zap, Info } from 'lucide-react';
import { API_BASE } from '../../apiBase';
import './CostEstimator.css';

export default function CostEstimator({ goal, token, buildTarget, onEstimateReady }) {
  const [estimate, setEstimate] = useState(null);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef(null);

  const fetchEstimate = useCallback(async (g) => {
    setLoading(true);
    try {
      const headers = {};
      if (token) headers.Authorization = `Bearer ${token}`;
      const res = await axios.post(
        `${API_BASE}/orchestrator/estimate`,
        { goal: g, build_target: buildTarget || undefined },
        { headers },
      );
      const est = res.data?.estimate;
      setEstimate(est);
      onEstimateReady?.(est);
    } catch {
      setEstimate(null);
    } finally {
      setLoading(false);
    }
  }, [token, onEstimateReady, buildTarget]);

  useEffect(() => {
    if (!goal || goal.length < 10) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      fetchEstimate(goal);
    }, 700);
    return () => clearTimeout(debounceRef.current);
  }, [goal, fetchEstimate, buildTarget]);

  if (!goal || goal.length < 10) return null;

  return (
    <div className="cost-estimator">
      <Zap size={12} className="ce-icon" />
      {loading ? (
        <span className="ce-loading">Estimating cost...</span>
      ) : estimate ? (
        <div className="ce-content">
          <span className="ce-label">Estimated cost:</span>
          <span className="ce-range">
            {estimate.cost_range?.min_credits}–{estimate.cost_range?.max_credits} credits
          </span>
          <span className="ce-typical">(typically {estimate.cost_range?.typical_credits})</span>
          <div className="ce-tooltip">
            <Info size={10} />
            <span className="ce-tooltip-text">
              {estimate.estimated_steps} steps · {estimate.build_kind} · Final cost depends on actual complexity
            </span>
          </div>
        </div>
      ) : null}
    </div>
  );
}
