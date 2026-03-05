import { createContext, useContext } from 'react';
import { useSoulConnection } from '../hooks/useSoulConnection';

const SoulContext = createContext(null);

export function SoulProvider({ children }) {
    const soul = useSoulConnection();
    return (
        <SoulContext.Provider value={soul}>
            {children}
        </SoulContext.Provider>
    );
}

export function useSoul() {
    const ctx = useContext(SoulContext);
    if (!ctx) throw new Error('useSoul must be used within SoulProvider');
    return ctx;
}
