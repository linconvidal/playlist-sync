# BUG REPORT: Comparison Results Screen Flickering Issue

## Problem Description

There is a critical UI issue in the TUI comparison feature where the comparison results screen flickers and behaves incorrectly.

## Exact Behavior Observed

1. User clicks "Compare" button in PlaylistSelectionScreen
2. **PROBLEM**: Empty/incomplete ComparisonResultsScreen appears briefly (< 0.5 seconds)
3. **PROBLEM**: Screen automatically returns to PlaylistSelectionScreen 
4. User must click "Cancel" to return to main screen
5. **WORKAROUND**: Only then does the ComparisonResultsScreen appear properly with data

## Expected Behavior

1. User clicks "Compare" button
2. ComparisonResultsScreen appears immediately with complete data
3. No flickering or return to PlaylistSelectionScreen

## Root Cause Analysis Attempts (All Failed)

### Failed Attempt 1: Race Condition Theory
- **Theory**: async/await timing issues
- **Actions Taken**: Removed async, added delays, used set_timer()
- **Result**: No improvement

### Failed Attempt 2: Screen Transition Theory  
- **Theory**: pop/push screen timing
- **Actions Taken**: Modified screen flow, direct transitions
- **Result**: No improvement

### Failed Attempt 3: Data Loading Theory
- **Theory**: ComparisonResultsScreen created before data ready
- **Actions Taken**: Synchronous comparison, pre-populate data
- **Result**: No improvement

## Technical Details

### Affected Components
- `PlaylistSelectionScreen.on_button_pressed()` (Compare button)
- `ComparisonResultsScreen.__init__()` and `on_mount()`
- `SpotSyncApp.perform_comparison()`

### Current Implementation Flow
```
PlaylistSelectionScreen 
  → _do_comparison() (sync)
  → pop_screen()
  → push_screen(ComparisonResultsScreen)
  → ComparisonResultsScreen.on_mount() populates tables
```

### Suspected Issues
1. **Screen Navigation Bug**: Something causes return to PlaylistSelectionScreen
2. **Data Race**: ComparisonResultsScreen shows before data is ready
3. **Event Loop Issue**: UI events not properly synchronized
4. **Textual Framework Bug**: Framework-level screen management issue

## Code Locations

### PlaylistSelectionScreen.on_button_pressed()
File: `src/spotsync/tui.py:255-280`
- Handles Compare button click
- Calls `_do_comparison()`
- Manages screen transitions

### ComparisonResultsScreen.on_mount()  
File: `src/spotsync/tui.py:442-465`
- Populates DataTables with comparison results
- Critical for displaying data properly

### Current Comparison Flow
File: `src/spotsync/tui.py:282-320`
- `_do_comparison()` method does actual comparison
- Returns fully populated ComparisonResultsScreen

## Debugging Information

### What Works
- Data comparison logic is correct
- ComparisonResultsScreen displays correctly when reached via "Cancel" workaround
- All comparison data is complete and accurate

### What Doesn't Work
- Direct navigation from Compare button to results
- Screen persistence (keeps returning to selection)

## Recommended Investigation Areas

1. **Textual Screen Stack**: Check if multiple screens are being pushed/popped incorrectly
2. **Event Propagation**: Verify button events aren't triggering multiple actions
3. **Exception Handling**: Add comprehensive logging to identify silent failures
4. **Framework Version**: Check if this is a known Textual framework issue

## Temporary Workaround

Users can access comparison results by:
1. Click Compare (screen will flicker)
2. Click Cancel when returned to PlaylistSelectionScreen
3. Results will then display correctly

## Impact

- **Severity**: High - Core feature unusable without workaround
- **User Experience**: Poor - confusing navigation flow
- **Functionality**: Medium - Feature works but requires workaround

## Next Steps for Resolution

1. Add comprehensive debug logging throughout screen transitions
2. Investigate Textual framework screen management patterns
3. Consider alternative screen transition approaches
4. Test with minimal reproduction case
5. Check for event handling conflicts or double-triggering

---

**Date**: 2025-08-02  
**Component**: TUI Comparison Feature  
**Status**: Unresolved  
**Priority**: High