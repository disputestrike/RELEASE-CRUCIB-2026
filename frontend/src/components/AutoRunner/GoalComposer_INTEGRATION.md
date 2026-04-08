# Integration Guide: ExecutionTargetSelector into GoalComposer.jsx

## Changes Required

In `frontend/src/components/AutoRunner/GoalComposer.jsx`:

### 1. Add Import
```jsx
import ExecutionTargetSelector from './ExecutionTargetSelector';
```

### 2. Replace Static Selector with New Component

OLD CODE (remove):
```jsx
<div className="mb-4">
  <label className="block text-sm font-semibold mb-2">Execution Target</label>
  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
    <button className="p-3 border rounded hover:bg-gray-50">
      Full-stack web (Vite + React)
    </button>
    {/* ... other static buttons ... */}
  </div>
</div>
```

NEW CODE (replace with):
```jsx
<div className="mb-4">
  <label className="block text-sm font-semibold mb-2">Execution Target</label>
  <ExecutionTargetSelector
    userRequest={goalDescription}
    onTargetSelected={(suggestion) => {
      setExecutionTarget(suggestion.primary_target);
      setTargetConfidence(suggestion.confidence);
    }}
    onConfirm={(target) => {
      setExecutionTarget(target);
      // Optionally auto-advance to next step
    }}
  />
</div>
```

### 3. Update State Variables
```jsx
const [executionTarget, setExecutionTarget] = useState(null);
const [targetConfidence, setTargetConfidence] = useState(0);
```

### 4. Pass Target Data Forward
When user confirms target, pass it to the job creation:
```jsx
const createJob = () => {
  const jobData = {
    goal: goalDescription,
    executionTarget: executionTarget,
    targetConfidence: targetConfidence,
    // ... other fields
  };
  // Submit to backend
};
```

## Features Enabled

✅ Auto-detection when user types goal description
✅ Auto-confirm for high confidence (>90%)
✅ Conditional UI (hide selector for high confidence)
✅ Full selector only shown for low confidence (<70%)
✅ Confidence score displayed to user
✅ Reasoning displayed to user
✅ "Adjust" button to override AI suggestion
✅ Caching of detection results

## Testing

1. Type: "Build a dashboard with real-time data"
   → Should auto-confirm with Full-stack Web (confidence ~95%)
   → Show "Confirm" + "Adjust" buttons only

2. Type: "Create a tool"
   → Should show full selector (confidence ~40%)
   → User must manually choose target

3. Type: "Make a website"
   → Should show selector with suggestion highlighted (confidence ~75%)
   → User can confirm or choose different target

