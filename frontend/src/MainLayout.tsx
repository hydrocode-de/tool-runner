import { Layout, Menu, theme } from "antd"
import Title from "antd/es/typography/Title"
import { Link, Outlet } from "react-router-dom"



const MainLayout: React.FC = () => {
    // get theme token
    const { token: {colorBgContainer, borderRadiusLG, colorTextLightSolid} } = theme.useToken()
    return <>
        <Layout style={{height: '100vh', width: '100vw'}}>
            <Layout.Header style={{display: 'flex', alignItems: 'center'}}>
                <Title level={3} style={{color: colorTextLightSolid}}>MetaCatalog Processes</Title>
                <Menu 
                    theme="dark"
                    mode="horizontal"
                    defaultSelectedKeys={['1']}
                    style={{margin: '0 1rem'}}
                    items={[
                        {key: '1', label: <Link to="/jobs">Jobs</Link>},
                        {key: '2', label: <Link to="/tools">Tools</Link>}
                    ]}
                />
            </Layout.Header> 

            <Layout.Content style={{padding: '0 1rem', height: '100%', margin: '0.6rem 0'}}>
                <div style={{height: '100%', background: colorBgContainer, borderRadius: borderRadiusLG, padding: '0.6rem', overflowY: 'auto'}}>
                    <Outlet />
                </div>
            </Layout.Content>

            <Layout.Footer style={{textAlign: 'center'}}>
                ©2024 hydrocode GmbH
            </Layout.Footer>
        </Layout>
    </>
}

export default MainLayout