import { createContext, useContext, useState } from "react";

// define the interface and initial state
interface Settings {
    backendUrl: string;
    updateBackendUrl: (newUrl: string) => void;
}

const initialState: Settings = {
    backendUrl: 'http://127.0.0.1:5555/api/v1',
    updateBackendUrl: () => {}
}

// create the context itself
const SettingsContext = createContext<Settings>(initialState)

// define the context provider
export const SettingsProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
    // define the state
    const [backendUrl, setBackendUrl] = useState<string>(initialState.backendUrl)

    // define the update function
    const updateBackendUrl = (newUrl: string) => {
        setBackendUrl(newUrl)
    }
    
    // define the new value of the context object
    const value: Settings = {
        backendUrl,
        updateBackendUrl
    }
    return <>
        <SettingsContext.Provider value={value}>
            { children }
        </SettingsContext.Provider>
    </>
}

// define a hook for easier access
export const useSettings = () => useContext(SettingsContext)