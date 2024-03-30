import { useEffect, useState } from "react"
import { Tool, useTools } from "../context/ToolsContext"
import { useNavigate, useParams } from "react-router-dom"
import RunToolForm from "../components/RunToolForm"
import { Empty, Button, UploadFile, notification } from "antd"
import { useJobs } from "../context/JobContext"
import { AxiosError } from "axios"

const CreateJobPage: React.FC = () => {
    // state to handle the tool
    const [tool, setTool] = useState<Tool | undefined>(undefined)
    const [params, setParams] = useState<{[key: string]: any}>({})
    const [data, setData] = useState<{[key: string]: string | UploadFile | undefined}>({})
    const [valid, setValid] = useState<boolean>(false)

    // get a notification context
    const [notificationApi, notificationContext] = notification.useNotification()
    // get the url params for the tool name
    const { toolName } = useParams<{toolName: string}>()

    // get the tools
    const { tools } = useTools()

    // get the create function from the job context
    const { createJob } = useJobs()

    // hook into the navigation component
    const navigate  = useNavigate()
    
    // handler for the create button
    const handleCreate = () => {
        createJob(toolName as string, params, data)
            .then(job => {
                notificationApi.success({
                    message: 'Job Created',
                    description: `Job ${job.job_id} created successfully. Status: ${job.status}`
                })

                // navigate to the job page
                navigate('/jobs')

            })
            .catch((err: AxiosError<{detail: string}>) => {
                console.log(err)
                notificationApi.error({
                    message: 'Backend Error on Job Creation',
                    description: err.response?.data?.detail || err.message,
                })
            })
    }

    // update the tools whenever the context or url changes
    useEffect(() => {
        setTool(tools.find(t => t.name === toolName))
    }, [tools, toolName])

    // use effect to validate the input parameters
    useEffect(() => {
        if (!tool) {
            setValid(false)
            return
        }
        // check all parameters are there 
        setValid(
            Object.values(tool.parameters).map(p => 
                    p.optional || Object.keys(params).includes(p.name)
                )
                .reduce((a, b) => a && b, true)
            )
    }, [params, tool])


    return <>
        { tool ? (
        <>
            { notificationContext }
            <RunToolForm tool={tool} onParamChange={c => setParams(c)} onDataChange={d => setData(d)} />
            <Button disabled={!valid} onClick={handleCreate}>CREATE</Button>
        </>
        ) : <Empty /> }


        
    </>
}

export default CreateJobPage