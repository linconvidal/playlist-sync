#!/usr/bin/env python3
"""
Test script to debug what the TUI interface actually displays.
"""

import pytest
from spotsync.tui import SpotSyncApp


@pytest.mark.asyncio
async def test_tui_interface_debug():
    """Debug test to see what widgets are actually rendered."""
    app = SpotSyncApp()
    async with app.run_test() as pilot:
        # Take a moment to let the app fully load
        await pilot.pause()
        
        # Check the screen stack
        print(f"Screen stack: {app.screen_stack}")
        print(f"Current screen: {app.screen}")
        print(f"Current screen type: {type(app.screen)}")
        
        # Check if the Browse button exists
        try:
            browse_button = app.query_one("#browse-button")
            print(f"✓ Browse button found: {browse_button}")
        except Exception as e:
            print(f"✗ Browse button NOT found: {e}")
        
        # Check if file display exists
        try:
            file_display = app.query_one("#file-display")
            print(f"✓ File display found: {file_display}")
        except Exception as e:
            print(f"✗ File display NOT found: {e}")
        
        # Check what widgets are actually present in the current screen
        all_widgets = list(app.screen.query("*"))
        print(f"\nAll widgets in current screen ({len(all_widgets)}):")
        for widget in all_widgets:
            if hasattr(widget, 'id') and widget.id:
                print(f"  - {widget.__class__.__name__} (id: {widget.id})")
            else:
                print(f"  - {widget.__class__.__name__}")
        
        # Check what widgets are available at the app level
        all_app_widgets = list(app.query("*"))
        print(f"\nAll widgets in app ({len(all_app_widgets)}):")
        for widget in all_app_widgets:
            if hasattr(widget, 'id') and widget.id:
                print(f"  - {widget.__class__.__name__} (id: {widget.id})")
            else:
                print(f"  - {widget.__class__.__name__}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_tui_interface_debug())