import { useParams } from "react-router-dom"
import { Tool, useTools } from "../context/ToolsContext"
import { useEffect, useState } from "react"
import ToolDetails from "../components/ToolDetails"
import { Empty } from "antd"


const ToolDetailPage: React.FC = () => {
    // state to handle the tool
    const [tool, setTool] = useState<Tool | undefined>(undefined)

    // get the url params for the tool name
    const { toolName } = useParams<{toolName: string}>()

    // get the tool context to filter for the specified tool
    const { tools } = useTools()

    // update the tools whenever the context or url changes
    useEffect(() => {
        setTool(tools.find(t => t.name === toolName))
    }, [tools, toolName])
    
    
    return <>
        { tool ? <ToolDetails tool={tool} />  : <Empty /> }
    </>
}

export default ToolDetailPage