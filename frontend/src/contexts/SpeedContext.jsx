import React, { createContext, useState, useCallback } from 'react';

export const SpeedContext = createContext();

export function SpeedProvider({ children }) {
  const [selectedSpeed, setSelectedSpeed] = useState('pro');
  const [speedHistory, setSpeedHistory] = useState(['pro']);

  const handleSpeedChange = useCallback((newSpeed) => {
    setSelectedSpeed(newSpeed);
    setSpeedHistory(prev => [...prev, newSpeed]);
  }, []);

  const getSpeedConfig = (speed) => {
    const configs = {
      lite: {
        name: 'Lite',
        model: 'cerebras',
        parallelism: 1,
        tokenMultiplier: 1.0,
        creditCost: 50,
        buildTime: '30-40s'
      },
      pro: {
        name: 'Pro',
        model: 'haiku',
        parallelism: 2.5,
        tokenMultiplier: 1.5,
        creditCost: 100,
        buildTime: '12-16s'
      },
      max: {
        name: 'Max',
        model: 'haiku',
        parallelism: 4.0,
        tokenMultiplier: 2.0,
        creditCost: 150,
        buildTime: '8-10s',
        allAgents: true
      }
    };
    return configs[speed] || configs.pro;
  };

  const value = {
    selectedSpeed,
    setSelectedSpeed: handleSpeedChange,
    speedHistory,
    getSpeedConfig,
    currentConfig: getSpeedConfig(selectedSpeed)
  };

  return (
    <SpeedContext.Provider value={value}>
      {children}
    </SpeedContext.Provider>
  );
}

export function useSpeed() {
  const context = React.useContext(SpeedContext);
  if (!context) {
    throw new Error('useSpeed must be used within SpeedProvider');
  }
  return context;
}
