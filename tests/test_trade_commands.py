"""
Test suite for trade commands system.

Tests:
1. Command registry (Supabase)
2. Command aliases
3. Natural language phrase matching
4. Controller mappings
5. Position entry/exit commands
"""

import pytest
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase client
supabase: Client = create_client(
    os.environ.get('NEXT_PUBLIC_SUPABASE_URL'),
    os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
)

class TestTradeCommandsRegistry:
    """Test the trade_commands table."""

    def test_commands_exist(self):
        """Verify all expected commands are in the registry."""
        result = supabase.table('trade_commands').select('command').execute()
        commands = [row['command'] for row in result.data]

        expected_commands = [
            '/trade flatten',
            '/trade flatten-smart',
            '/trade close',
            '/trade position',
            '/trade reset',
            '/trade long',
            '/trade short',
            '/trade accumulate',
            '/trade scaleout',
            '/trade reverse',
            '/trade reverse-smart',
            '/trade stop',
            '/trade bracket',
            '/trade price',
            '/trade volume',
            '/trade range'
        ]

        for cmd in expected_commands:
            assert cmd in commands, f"Command {cmd} not found in registry"

    def test_command_categories(self):
        """Verify commands have correct categories."""
        result = supabase.table('trade_commands').select('command, category').execute()

        category_map = {cmd['command']: cmd['category'] for cmd in result.data}

        assert category_map['/trade flatten'] == 'position_management'
        assert category_map['/trade long'] == 'entry'
        assert category_map['/trade reverse'] == 'reversal'
        assert category_map['/trade price'] == 'market_data'

    def test_ai_assisted_flags(self):
        """Verify AI-assisted commands are flagged correctly."""
        result = supabase.table('trade_commands').select('command, is_ai_assisted').execute()

        ai_commands = [row['command'] for row in result.data if row['is_ai_assisted']]

        assert '/trade flatten-smart' in ai_commands
        assert '/trade reverse-smart' in ai_commands
        assert '/trade flatten' not in ai_commands  # Regular flatten is not AI-assisted


class TestTradeAliases:
    """Test the trade_aliases table."""

    def test_flatten_aliases(self):
        """Verify flatten command has all expected aliases."""
        # Get flatten command ID
        cmd_result = supabase.table('trade_commands').select('id').eq('command', '/trade flatten').execute()
        cmd_id = cmd_result.data[0]['id']

        # Get all aliases
        alias_result = supabase.table('trade_aliases').select('alias').eq('command_id', cmd_id).execute()
        aliases = [row['alias'] for row in alias_result.data]

        expected_aliases = ['flat', 'exit', 'close', 'closeposition', 'exitposition', 'sell all']

        for alias in expected_aliases:
            assert alias in aliases, f"Alias '{alias}' not found for /trade flatten"

    def test_long_short_aliases(self):
        """Verify long/short have buy/sell aliases."""
        # Long -> buy
        long_result = supabase.table('trade_commands').select('id').eq('command', '/trade long').execute()
        long_id = long_result.data[0]['id']

        long_aliases = supabase.table('trade_aliases').select('alias').eq('command_id', long_id).execute()
        long_alias_list = [row['alias'] for row in long_aliases.data]

        assert 'buy' in long_alias_list

        # Short -> sell
        short_result = supabase.table('trade_commands').select('id').eq('command', '/trade short').execute()
        short_id = short_result.data[0]['id']

        short_aliases = supabase.table('trade_aliases').select('alias').eq('command_id', short_id).execute()
        short_alias_list = [row['alias'] for row in short_aliases.data]

        assert 'sell' in short_alias_list


class TestTradePhrases:
    """Test natural language phrase mappings."""

    def test_flatten_phrases(self):
        """Verify flatten has natural language phrases."""
        cmd_result = supabase.table('trade_commands').select('id').eq('command', '/trade flatten').execute()
        cmd_id = cmd_result.data[0]['id']

        phrase_result = supabase.table('trade_phrases').select('phrase').eq('command_id', cmd_id).execute()
        phrases = [row['phrase'] for row in phrase_result.data]

        expected_phrases = [
            'get me out',
            'sell everything',
            'close my trade',
            'exit my position'
        ]

        for phrase in expected_phrases:
            assert phrase in phrases, f"Phrase '{phrase}' not found for /trade flatten"

    def test_position_phrases(self):
        """Verify position inquiry has question phrases."""
        cmd_result = supabase.table('trade_commands').select('id').eq('command', '/trade position').execute()
        cmd_id = cmd_result.data[0]['id']

        phrase_result = supabase.table('trade_phrases').select('phrase').eq('command_id', cmd_id).execute()
        phrases = [row['phrase'] for row in phrase_result.data]

        assert "what's my position" in phrases
        assert "am i long or short" in phrases

    def test_confidence_scores(self):
        """Verify all phrases have valid confidence scores."""
        result = supabase.table('trade_phrases').select('phrase, confidence_score').execute()

        for row in result.data:
            score = float(row['confidence_score'])
            assert 0.0 <= score <= 1.0, f"Invalid confidence score {score} for phrase '{row['phrase']}'"


class TestControllerMappings:
    """Test Xbox controller button mappings."""

    def test_all_buttons_mapped(self):
        """Verify all Xbox buttons have mappings."""
        result = supabase.table('controller_mappings').select('button').execute()
        buttons = list(set([row['button'] for row in result.data]))

        expected_buttons = ['LT', 'LB', 'RT', 'RB', 'Y', 'X', 'B', 'A', 'View', 'Menu']

        for btn in expected_buttons:
            assert btn in buttons, f"Button {btn} not mapped"

    def test_spray_mode_buttons(self):
        """Verify LT and RT are configured for spray mode."""
        result = supabase.table('controller_mappings').select('button, mode').eq('mode', 'spray').execute()
        spray_buttons = [row['button'] for row in result.data]

        assert 'LT' in spray_buttons  # Spray buy
        assert 'RT' in spray_buttons  # Spray sell

    def test_flatten_button(self):
        """Verify Y button maps to flatten."""
        result = supabase.table('controller_mappings').select('action_label, trade_commands(command)').eq('button', 'Y').execute()

        assert result.data[0]['action_label'] == 'flatten'
        assert result.data[0]['trade_commands']['command'] == '/trade flatten'

    def test_toggle_ai_assist(self):
        """Verify View button toggles AI assist."""
        result = supabase.table('controller_mappings').select('action_label, mode').eq('button', 'View').execute()

        assert result.data[0]['action_label'] == 'toggle_ai_assist'
        assert result.data[0]['mode'] == 'toggle'


class TestCommandIntegration:
    """Integration tests with API endpoints."""

    @pytest.mark.asyncio
    async def test_position_command(self):
        """Test position status command."""
        # This would require running API
        # For now, just verify the command exists
        result = supabase.table('trade_commands').select('handler_function').eq('command', '/trade position').execute()

        assert result.data[0]['handler_function'] == 'get_position_status'

    @pytest.mark.asyncio
    async def test_close_command(self):
        """Test close position command."""
        result = supabase.table('trade_commands').select('handler_function, is_implemented').eq('command', '/trade close').execute()

        assert result.data[0]['handler_function'] == 'close_position'
        assert result.data[0]['is_implemented'] == True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
