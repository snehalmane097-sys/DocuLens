import Demo from '@/components/demo-analytics';
import {RealWorkspace} from '@/components/real-workspace';
export const metadata={title:'Analytics'};
export default function Page(){return <RealWorkspace mode="analytics" demo={<Demo/>}/>;}