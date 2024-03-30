import { Button } from "antd"
import { RetweetOutlined } from "@ant-design/icons"

import { useJobs } from "../context/JobContext"
import JobTable from "../components/JobTable"

const JobListPage: React.FC = () => {
    // use the job context to subscribe to the jobs
    const { refreshJobs } = useJobs()
    return <>
        <Button onClick={refreshJobs} icon={<RetweetOutlined />}>Refresh</Button>
        <JobTable />
    </>
}

export default JobListPage