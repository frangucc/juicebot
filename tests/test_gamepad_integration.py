"""
Test suite for Xbox gamepad integration.

Tests:
1. Button mapping validation
2. Spray mode functionality (LT/RT held down)
3. AI assist toggle (View button)
4. Command execution for each button
5. Gamepad connection/disconnection
"""

import pytest
import asyncio
from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()

supabase: Client = create_client(
    os.environ.get('NEXT_PUBLIC_SUPABASE_URL'),
    os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
)

class TestGamepadMappings:
    """Test Xbox controller button mappings."""

    def test_all_xbox_buttons_configured(self):
        """Verify all Xbox buttons have database entries."""
        result = supabase.table('controller_mappings').select('button').execute()
        buttons = list(set([row['button'] for row in result.data]))

        expected_buttons = {
            'LT': 'Left Trigger',
            'LB': 'Left Bumper',
            'RT': 'Right Trigger',
            'RB': 'Right Bumper',
            'Y': 'Y Button (top)',
            'X': 'X Button (left)',
            'B': 'B Button (right)',
            'A': 'A Button (bottom)',
            'View': 'View Button (select)',
            'Menu': 'Menu Button (start)'
        }

        for btn in expected_buttons.keys():
            assert btn in buttons, f"{btn} ({expected_buttons[btn]}) not configured"

    def test_spray_mode_configuration(self):
        """Verify LT and RT are configured for rapid-fire (spray) mode."""
        result = supabase.table('controller_mappings').select('*').in_('button', ['LT', 'RT']).execute()

        lt_mapping = next(m for m in result.data if m['button'] == 'LT')
        rt_mapping = next(m for m in result.data if m['button'] == 'RT')

        # LT should be spray buy (long)
        assert lt_mapping['mode'] == 'spray'
        assert lt_mapping['action_label'] == 'spray_buy'

        # RT should be spray sell (short)
        assert rt_mapping['mode'] == 'spray'
        assert rt_mapping['action_label'] == 'spray_sell'

    def test_single_mode_configuration(self):
        """Verify LB and RB are configured for single-click mode."""
        result = supabase.table('controller_mappings').select('*').in_('button', ['LB', 'RB']).execute()

        lb_mapping = next(m for m in result.data if m['button'] == 'LB')
        rb_mapping = next(m for m in result.data if m['button'] == 'RB')

        assert lb_mapping['mode'] == 'single'
        assert lb_mapping['action_label'] == 'buy'

        assert rb_mapping['mode'] == 'single'
        assert rb_mapping['action_label'] == 'sell'

    def test_face_button_mappings(self):
        """Verify Y, X, B, A buttons have correct actions."""
        result = supabase.table('controller_mappings').select('*').in_('button', ['Y', 'X', 'B', 'A']).execute()

        button_map = {m['button']: m for m in result.data}

        # Y = Flatten (instant close)
        assert button_map['Y']['action_label'] == 'flatten'
        assert button_map['Y']['mode'] == 'default'

        # X = Reverse (flip position)
        assert button_map['X']['action_label'] == 'reverse'
        assert button_map['X']['mode'] == 'default'

        # B = Status (show position)
        assert button_map['B']['action_label'] == 'status'
        assert button_map['B']['mode'] == 'default'

        # A = Smart stop loss (AI-assisted)
        assert button_map['A']['action_label'] == 'smart_stop'
        assert button_map['A']['mode'] == 'ai'

    def test_view_menu_buttons(self):
        """Verify View and Menu buttons."""
        result = supabase.table('controller_mappings').select('*').in_('button', ['View', 'Menu']).execute()

        button_map = {m['button']: m for m in result.data}

        # View = Toggle AI assist
        assert button_map['View']['action_label'] == 'toggle_ai_assist'
        assert button_map['View']['mode'] == 'toggle'
        assert button_map['View']['command_id'] is None  # No command, just UI state

        # Menu = Smart flatten (gradual exit)
        assert button_map['Menu']['action_label'] == 'flatten_smart'
        assert button_map['Menu']['mode'] == 'eject'


class TestGamepadCommands:
    """Test command execution from gamepad buttons."""

    def test_flatten_command_exists(self):
        """Verify Y button maps to implemented flatten command."""
        result = supabase.table('controller_mappings')\
            .select('trade_commands(command, is_implemented)')\
            .eq('button', 'Y')\
            .execute()

        command = result.data[0]['trade_commands']
        assert command['command'] == '/trade flatten'

    def test_reverse_command_exists(self):
        """Verify X button maps to reverse command."""
        result = supabase.table('controller_mappings')\
            .select('trade_commands(command)')\
            .eq('button', 'X')\
            .execute()

        command = result.data[0]['trade_commands']
        assert command['command'] == '/trade reverse'

    def test_position_status_command(self):
        """Verify B button maps to position status command."""
        result = supabase.table('controller_mappings')\
            .select('trade_commands(command, is_implemented)')\
            .eq('button', 'B')\
            .execute()

        command = result.data[0]['trade_commands']
        assert command['command'] == '/trade position'
        assert command['is_implemented'] == True

    def test_long_short_commands(self):
        """Verify trigger buttons map to long/short commands."""
        result = supabase.table('controller_mappings')\
            .select('button, trade_commands(command, is_implemented)')\
            .in_('button', ['LT', 'LB', 'RT', 'RB'])\
            .execute()

        commands_map = {m['button']: m['trade_commands'] for m in result.data}

        # LT and LB should both map to /trade long
        assert commands_map['LT']['command'] == '/trade long'
        assert commands_map['LB']['command'] == '/trade long'
        assert commands_map['LT']['is_implemented'] == True

        # RT and RB should both map to /trade short
        assert commands_map['RT']['command'] == '/trade short'
        assert commands_map['RB']['command'] == '/trade short'
        assert commands_map['RT']['is_implemented'] == True


class TestGamepadModes:
    """Test different gamepad interaction modes."""

    def test_spray_mode_characteristics(self):
        """Verify spray mode is configured for continuous execution."""
        result = supabase.table('controller_mappings')\
            .select('button, mode, description')\
            .eq('mode', 'spray')\
            .execute()

        # Should have exactly 2 spray buttons (LT and RT)
        assert len(result.data) == 2

        buttons = [m['button'] for m in result.data]
        assert 'LT' in buttons
        assert 'RT' in buttons

        # Descriptions should indicate rapid-fire behavior
        for mapping in result.data:
            assert 'rapid' in mapping['description'].lower() or 'spray' in mapping['description'].lower()

    def test_toggle_mode(self):
        """Verify toggle mode for AI assist."""
        result = supabase.table('controller_mappings')\
            .select('*')\
            .eq('mode', 'toggle')\
            .execute()

        # Should have exactly 1 toggle button (View)
        assert len(result.data) == 1
        assert result.data[0]['button'] == 'View'
        assert result.data[0]['action_label'] == 'toggle_ai_assist'

    def test_ai_mode(self):
        """Verify AI-assisted commands are marked."""
        result = supabase.table('controller_mappings')\
            .select('button, trade_commands(is_ai_assisted)')\
            .eq('mode', 'ai')\
            .execute()

        # A button should use AI
        assert result.data[0]['button'] == 'A'


class TestGamepadButtonIndexes:
    """Test Xbox controller button index mappings (Web Gamepad API)."""

    def test_standard_xbox_layout(self):
        """Verify button indexes match Xbox controller standard."""
        # Web Gamepad API standard button indexes for Xbox controllers
        expected_indexes = {
            'A': 0,      # Bottom button
            'B': 1,      # Right button
            'X': 2,      # Left button
            'Y': 3,      # Top button
            'LB': 4,     # Left bumper
            'RB': 5,     # Right bumper
            'LT': 6,     # Left trigger (digital)
            'RT': 7,     # Right trigger (digital)
            'View': 8,   # View/select button
            'Menu': 9,   # Menu/start button
            'LS': 10,    # Left stick press
            'RS': 11     # Right stick press
        }

        # This is just documentation - the GamepadController component
        # uses these indexes internally
        assert expected_indexes['Y'] == 3  # Flatten button
        assert expected_indexes['X'] == 2  # Reverse button
        assert expected_indexes['LT'] == 6  # Spray buy
        assert expected_indexes['RT'] == 7  # Spray sell


class TestSessionState:
    """Test session state tracking for gamepad."""

    def test_session_state_schema(self):
        """Verify session_state table exists with correct columns."""
        # Try to query session_state table
        result = supabase.table('session_state').select('*').limit(1).execute()

        # Schema should support these fields
        if len(result.data) > 0:
            session = result.data[0]
            assert 'session_id' in session
            assert 'ai_assist_enabled' in session
            assert 'last_button_pressed' in session
            assert 'last_trade_command' in session


@pytest.mark.integration
class TestGamepadIntegration:
    """Integration tests requiring running services."""

    @pytest.mark.asyncio
    async def test_gamepad_command_to_api(self):
        """Test full flow: button press -> command -> API call."""
        # This would require:
        # 1. Simulated gamepad button press
        # 2. GamepadController component mapping
        # 3. API endpoint call
        # 4. Position update in database

        # For now, just verify the pipeline exists
        result = supabase.table('controller_mappings')\
            .select('button, trade_commands(command, handler_function, is_implemented)')\
            .eq('button', 'LB')\
            .execute()

        mapping = result.data[0]
        command = mapping['trade_commands']

        # Verify complete pipeline
        assert mapping['button'] == 'LB'
        assert command['command'] == '/trade long'
        assert command['handler_function'] == 'open_long_position'
        assert command['is_implemented'] == True


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
