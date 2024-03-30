import axios from "axios";
import { createContext, useContext, useState } from "react";
import { useSettings } from "./SettingsContext";

interface InputParameter {
    name: string;
    description?: string;
    type: string;
    array?: boolean;
    optional?: boolean;
    default?: boolean | string | number;
    min?: number;
    max?: number;
    values?: string[];
}

export interface ToolInputData {
    path: string;
    description?: string;
    example?: string;
    extension?: string | string[];
}

export interface Tool {
    name: string;
    title: string;
    description: string;
    version?: string | null;
    parameters: { [key: string]: InputParameter };
    data?: { [key: string]: ToolInputData };
    docker_image: string;
}


// define the interface
interface ToolsContext {
    tools: Tool[];
    refreshTools: () => void;
}

// define the initial state
const initialState: ToolsContext = {
    tools: [],
    refreshTools: () => {}
}

// create the context
const ToolsContext = createContext<ToolsContext>(initialState)

// define the context provider
export const ToolsProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
    // subscribe to the settings context
    const { backendUrl } = useSettings()

    // create the state of the context
    const [tools, setTools] = useState<Tool[]>(initialState.tools)

    // define the refresh function
    const refreshTools = () => {
        axios.get<Tool[]>(`${backendUrl}/tools/full`)
            .then(resp => resp.data)
            .then(data => setTools(data))
            .catch(() => setTools([]))
    }

    // build the current context value
    const value: ToolsContext = {
        tools,
        refreshTools
    }

    return <>
        <ToolsContext.Provider value={value}>
            { children }
        </ToolsContext.Provider>
    </>
}

// define a hook for easier access
export const useTools = () => useContext(ToolsContext)