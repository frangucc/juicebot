'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { supabase } from '@/lib/supabase';

interface ControllerMapping {
  button: string;
  action_label: string;
  command_id: string | null;
  mode: string;
  description: string;
  command?: string;
}

interface GamepadState {
  connected: boolean;
  name: string;
  buttons: boolean[];
  axes: number[];
}

export default function GamepadController({ symbol = 'BYND', onCommandExecute }: {
  symbol?: string;
  onCommandExecute?: (command: string, result: any) => void;
}) {
  const [gamepad, setGamepad] = useState<GamepadState>({
    connected: false,
    name: '',
    buttons: [],
    axes: []
  });
  const [mappings, setMappings] = useState<ControllerMapping[]>([]);
  const [aiAssistEnabled, setAiAssistEnabled] = useState(false);
  const [lastPressed, setLastPressed] = useState<string>('');
  const [feedback, setFeedback] = useState<string>('');

  const buttonStates = useRef<boolean[]>([]);
  const sprayIntervals = useRef<{ [key: number]: NodeJS.Timeout }>({});

  // Xbox button index mapping
  const XBOX_BUTTONS = {
    A: 0,
    B: 1,
    X: 2,
    Y: 3,
    LB: 4,
    RB: 5,
    LT: 6,
    RT: 7,
    View: 8,
    Menu: 9,
    LS: 10,  // Left stick press
    RS: 11   // Right stick press
  };

  // Load controller mappings from Supabase
  useEffect(() => {
    const loadMappings = async () => {
      const { data, error } = await supabase
        .from('controller_mappings')
        .select(`
          *,
          trade_commands (command)
        `);

      if (error) {
        console.error('Error loading controller mappings:', error);
        return;
      }

      const enrichedMappings = data.map((m: any) => ({
        ...m,
        command: m.trade_commands?.command
      }));

      setMappings(enrichedMappings);
    };

    loadMappings();
  }, []);

  // Gamepad connection/disconnection detection
  useEffect(() => {
    const handleGamepadConnected = (e: GamepadEvent) => {
      console.log('Gamepad connected:', e.gamepad.id);
      setGamepad({
        connected: true,
        name: e.gamepad.id,
        buttons: Array(e.gamepad.buttons.length).fill(false),
        axes: Array.from(e.gamepad.axes)
      });
      setFeedback('🎮 Xbox controller connected');
      setTimeout(() => setFeedback(''), 2000);
    };

    const handleGamepadDisconnected = (e: GamepadEvent) => {
      console.log('Gamepad disconnected:', e.gamepad.id);
      setGamepad({
        connected: false,
        name: '',
        buttons: [],
        axes: []
      });
      setFeedback('⚠️ Controller disconnected');
    };

    window.addEventListener('gamepadconnected', handleGamepadConnected);
    window.addEventListener('gamepaddisconnected', handleGamepadDisconnected);

    return () => {
      window.removeEventListener('gamepadconnected', handleGamepadConnected);
      window.removeEventListener('gamepaddisconnected', handleGamepadDisconnected);
    };
  }, []);

  // Execute trade command via API
  const executeCommand = useCallback(async (command: string, mode: string) => {
    try {
      let result;

      // Map commands to API endpoints
      if (command === '/trade long') {
        // Single unit buy at current market price
        result = await fetch(`http://localhost:8002/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: 'long 1 @ market',
            symbol: symbol
          })
        }).then(r => r.json());
      } else if (command === '/trade short') {
        result = await fetch(`http://localhost:8002/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: 'short 1 @ market',
            symbol: symbol
          })
        }).then(r => r.json());
      } else if (command === '/trade flatten') {
        result = await fetch(`http://localhost:8002/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: 'close position',
            symbol: symbol
          })
        }).then(r => r.json());
      } else if (command === '/trade position') {
        result = await fetch(`http://localhost:8002/position/${symbol}`).then(r => r.json());
      } else if (command === '/trade price') {
        result = await fetch(`http://localhost:8002/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: 'price',
            symbol: symbol
          })
        }).then(r => r.json());
      }

      if (onCommandExecute) {
        onCommandExecute(command, result);
      }

      return result;
    } catch (error) {
      console.error('Error executing command:', error);
      return null;
    }
  }, [symbol, onCommandExecute]);

  // Handle button press
  const handleButtonPress = useCallback((buttonIndex: number, mapping: ControllerMapping) => {
    if (!mapping.command) return;

    setLastPressed(mapping.button);

    if (mapping.mode === 'spray') {
      // Start spray mode (rapid fire)
      if (!sprayIntervals.current[buttonIndex]) {
        executeCommand(mapping.command, mapping.mode);
        setFeedback(`🔥 ${mapping.action_label.toUpperCase()}`);

        sprayIntervals.current[buttonIndex] = setInterval(() => {
          executeCommand(mapping.command!, mapping.mode);
        }, 200); // Execute every 200ms while held
      }
    } else if (mapping.mode === 'single') {
      // Single press
      executeCommand(mapping.command, mapping.mode);
      setFeedback(`✓ ${mapping.action_label.toUpperCase()}`);
      setTimeout(() => setFeedback(''), 1500);
    } else if (mapping.mode === 'default') {
      // Default action
      executeCommand(mapping.command, mapping.mode);
      setFeedback(`✓ ${mapping.description}`);
      setTimeout(() => setFeedback(''), 2000);
    } else if (mapping.mode === 'toggle') {
      // Toggle AI assist
      setAiAssistEnabled(prev => !prev);
      setFeedback(aiAssistEnabled ? '🤖 AI Assist OFF' : '🤖 AI Assist ON');
      setTimeout(() => setFeedback(''), 2000);
    }
  }, [executeCommand, aiAssistEnabled]);

  // Handle button release
  const handleButtonRelease = useCallback((buttonIndex: number) => {
    // Stop spray mode
    if (sprayIntervals.current[buttonIndex]) {
      clearInterval(sprayIntervals.current[buttonIndex]);
      delete sprayIntervals.current[buttonIndex];
      setFeedback('');
    }
  }, []);

  // Poll gamepad state
  useEffect(() => {
    if (!gamepad.connected) return;

    const pollGamepad = () => {
      const gamepads = navigator.getGamepads();
      const gp = gamepads[0]; // Assume first gamepad

      if (!gp) return;

      // Check each button
      gp.buttons.forEach((button, index) => {
        const pressed = button.pressed;
        const wasPressed = buttonStates.current[index];

        if (pressed && !wasPressed) {
          // Button just pressed
          buttonStates.current[index] = true;

          // Find mapping for this button
          const buttonName = Object.entries(XBOX_BUTTONS).find(([, idx]) => idx === index)?.[0];
          if (buttonName) {
            const mapping = mappings.find(m => m.button === buttonName);
            if (mapping) {
              handleButtonPress(index, mapping);
            }
          }
        } else if (!pressed && wasPressed) {
          // Button just released
          buttonStates.current[index] = false;
          handleButtonRelease(index);
        }
      });

      // Update axes
      setGamepad(prev => ({
        ...prev,
        axes: Array.from(gp.axes)
      }));
    };

    const interval = setInterval(pollGamepad, 16); // ~60fps

    return () => {
      clearInterval(interval);
      // Clear all spray intervals
      Object.values(sprayIntervals.current).forEach(clearInterval);
      sprayIntervals.current = {};
    };
  }, [gamepad.connected, mappings, handleButtonPress, handleButtonRelease]);

  return (
    <div className="fixed bottom-4 right-4 bg-gray-900 border border-gray-700 rounded-lg p-4 min-w-[300px] shadow-lg">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white">Xbox Controller</h3>
        {gamepad.connected ? (
          <span className="text-xs text-green-400 flex items-center gap-1">
            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
            Connected
          </span>
        ) : (
          <span className="text-xs text-gray-500">Disconnected</span>
        )}
      </div>

      {gamepad.connected && (
        <>
          <div className="text-xs text-gray-400 mb-2 truncate" title={gamepad.name}>
            {gamepad.name}
          </div>

          {/* AI Assist Status */}
          <div className="mb-3 pb-3 border-b border-gray-700">
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-400">AI Assist</span>
              <span className={aiAssistEnabled ? 'text-green-400 font-semibold' : 'text-gray-500'}>
                {aiAssistEnabled ? '🤖 ON' : 'OFF'}
              </span>
            </div>
          </div>

          {/* Button Mapping Reference */}
          <div className="space-y-1 text-xs">
            <div className="text-gray-400 font-semibold mb-2">Button Map:</div>
            <div className="grid grid-cols-2 gap-1 text-gray-300">
              <div>LT: Spray Buy</div>
              <div>RT: Spray Sell</div>
              <div>LB: Buy 1</div>
              <div>RB: Sell 1</div>
              <div>Y: Flatten</div>
              <div>X: Reverse</div>
              <div>B: Status</div>
              <div>A: Stop Loss</div>
              <div className="col-span-2">View: Toggle AI</div>
            </div>
          </div>

          {/* Feedback Display */}
          {feedback && (
            <div className="mt-3 pt-3 border-t border-gray-700">
              <div className="text-xs font-semibold text-green-400 animate-pulse">
                {feedback}
              </div>
            </div>
          )}

          {/* Last Pressed */}
          {lastPressed && (
            <div className="mt-2 text-xs text-gray-500">
              Last: {lastPressed}
            </div>
          )}
        </>
      )}

      {!gamepad.connected && (
        <div className="text-xs text-gray-500 text-center py-4">
          <div className="mb-2">Connect Xbox controller via Bluetooth</div>
          <div className="text-[10px] text-gray-600">
            Press any button to activate
          </div>
        </div>
      )}
    </div>
  );
}
