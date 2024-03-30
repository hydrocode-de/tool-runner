import axios from "axios";
import { createContext, useContext, useEffect, useState } from "react";
import { useSettings } from "./SettingsContext";
import { UploadFile } from "antd";

export enum ToolJobStatus {
    PENDING = 'pending',
    RUNNING = 'running',
    COMPLETED = 'completed',
    FAILED = 'failed'
}

export enum ToolResultStatus {
    SUCCESS = 'success',
    WARNING = 'warning',
    ERROR = 'error'
}

export interface ToolJob {
    job_id: string;
    docker_image: string;
    tool_name: string;
    in_dir: string;
    out_dir: string;
    status: ToolJobStatus;
    result_status?: ToolResultStatus;
    error_message?: string;
    runtime?: number;
    timestamp?: string;
}

interface JobsState {
    jobs: ToolJob[];
    refreshJobs: () => Promise<void>,
    createJob: (toolName: string, params: {[key: string]: any}, data: {[key: string]: string | UploadFile | undefined}) => Promise<ToolJob>
    runJob: (jobId: string) => Promise<ToolJob>,
    deleteJob: (jobId: String, keepFiles?: boolean) => Promise<{deleted: string, message: string}>
}


// create the initial state
const initialState: JobsState = {
    jobs: [],
    refreshJobs: () => Promise.reject(),
    createJob: () => Promise.reject(),
    runJob: () => Promise.reject(),
    deleteJob: () => Promise.reject(),
}

// create the context
const JobContext = createContext<JobsState>(initialState)

// create the provider for the context
export const JobProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
    // subscribe to the settings context
    const { backendUrl } = useSettings()
    
    // define the context state
    const [jobs, setJobs] = useState<ToolJob[]>([])

    // define the refresh function
    const refreshJobs = () => {
        return axios.get<ToolJob[]>(`${backendUrl}/jobs`)
            .then(resp => resp.data)
            .then(data => setJobs(data))
            .catch(() => setJobs([]))
    }

    // define the function for creating a job
    const createJob = (toolName: string, params: {[key: string]: any}, data: {[key: string]: string | UploadFile | undefined}): Promise<ToolJob> => {
        // create the form data
        const formData = new FormData()

        // add the parameters
        formData.append('parameters', JSON.stringify(params))

        // filter data for strings
        const localData = Object.fromEntries(Object.entries(data).filter(([_, value]) => typeof value === 'string') as [string, string][])
        // append the local data paths
        formData.append('local_data', JSON.stringify(localData))

        // filter for file objects
        const fileData = Object.fromEntries(Object.entries(data).filter(([_, value]) => !!value && typeof value !== 'string') as [string, UploadFile][])
        // append the file data
        Object.values(fileData).forEach(f => formData.append('files', f.originFileObj!))

        // create a mapping for the files
        // TODO: The mapp here has to map the actual filename to the conf name to be used
        const fileMap = Object.fromEntries(Object.entries(fileData).map(([dataConfName, file]) => [file.name, dataConfName]))
        formData.append('name_mapping', JSON.stringify(fileMap))
        
        // send the actual request
        return axios.post<ToolJob>(
            `${backendUrl}/tool/${toolName}/create`, 
            formData, 
            {
                headers: {
                    'Content-Type': 'multipart/form-data',
                    'accept': 'application/json'
                }
            }
        )
        .then(resp => resp.data)
    }

    const runJob = (jobId: string): Promise<ToolJob> => {
        return axios.post<ToolJob>(`${backendUrl}/job/${jobId}/run`).then(resp => resp.data)
    }

    const deleteJob = (jobId: String, keepFiles?: boolean): Promise<{deleted: string, message: string}> => {
        return axios.delete<{deleted: string, message: string}>(`${backendUrl}/job/${jobId}`, {
            params: {
                keep_files: keepFiles || false
            }
        }).then(resp => resp.data)
    }

    // build the current context value
    const value: JobsState = {
        jobs,
        refreshJobs,
        createJob,
        runJob,
        deleteJob
    }

    // use Effect to refresh the jobs whenever the backend url changes
    useEffect(() => {
        refreshJobs()
    }, [backendUrl])
    
    return <>
        <JobContext.Provider value={value}>
            { children }
        </JobContext.Provider>
    </>
}

// define a hook for easier access
export const useJobs = () => useContext(JobContext)
