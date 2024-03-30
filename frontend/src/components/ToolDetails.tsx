import { Tool } from "../context/ToolsContext"

interface ToolDetailsProps {
    tool: Tool
}

const ToolDetails: React.FC<ToolDetailsProps> = ({ tool }) => {
    return <>
        <pre>
            <code>
                {JSON.stringify(tool, null, 2)}
            </code>
        </pre>
    </>
}

export default ToolDetails