import { Button, List } from "antd"
import { RetweetOutlined } from "@ant-design/icons"

import { useTools } from "../context/ToolsContext"
import { Link } from "react-router-dom"

const ToolsListPage = () => {
    // use the tool context
    const { tools, refreshTools } = useTools()

    return <>
        <Button onClick={refreshTools} icon={<RetweetOutlined />}>Refresh</Button>
        <List 
            itemLayout="horizontal"
            dataSource={tools}
            renderItem={tool => (
                <List.Item
                    actions={[
                        <Link to={`/tools/${tool.name}/create`}>new</Link>, 
                        <Link to={`/tools/${tool.name}`}>details</Link>
                    ]}
                >
                    <List.Item.Meta 
                        title={tool.title}
                        description={tool.description}
                    />
                </List.Item>
            )}
        />
    </>
}

export default ToolsListPage