import { useState } from "react";
import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";
import StatusBar from "@/components/layout/StatusBar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import { Users, Network, Play, Plus, LoaderCircle } from "lucide-react";

// Agentic AI components
import AgentFlowGraph from "@/components/agentic-ai/AgentFlowGraph";
import ExecutionTab from "@/components/agentic-ai/ExecutionTab";
import { StreamingDataProvider } from "@/components/agentic-ai/StreamingDataContext";
import { FlowObject } from '../components/agentic-ai/graphs/interfaces'
import axios from '../http/axiosAgentConfig'

// Create a ReactFlow provider wrapper
import { ReactFlowProvider } from 'reactflow';

export interface GraphNode {
  id: string;
  name: string;
  description: string | null;
}

export default function AgenticAI() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("agent-flow");
  const [selectedFlow, setSelectedFlow] = useState<FlowObject | null>(null);
  const [builtGraphId, setBuiltGraphId] = useState<string | null>(null);
  const [builtGraphName, setBuiltGraphName] = useState<string | null>(null);
  const [selectedGraphId, setSelectedGraphId] = useState<string | null>(null);

  const handleBuildGraph = async () => {
    try {
      const graphId = selectedFlow?.id || `graph-${Date.now()}`;
      const graphName = selectedFlow?.name || "Custom Flow " + Math.floor(Math.random() * 1000);
      
      // Set the graph ID and name
      setBuiltGraphId(graphId);
      setBuiltGraphName(graphName);

      const selectedBlueprint = {
        'blueprintId': graphId,
        'userId': "bob",
      }

      const response = await axios.post('/api/sessions/user.session.create', selectedBlueprint);
      setSelectedGraphId(response.data)

      // Switch to the Execution tab
      setActiveTab("execution");
    } catch (error) {
      console.error('Error create new graph session:', error);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header 
          title="Agentic AI System" 
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} 
        />
        
        <main className="flex-1 overflow-y-auto p-6 bg-background-dark">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <Tabs 
              defaultValue="agent-flow" 
              value={activeTab}
              onValueChange={setActiveTab}
              className="w-full"
            >
              <TabsList className="mb-6">
                <TabsTrigger
                  value="agent-flow"
                  className="data-[state=active]:bg-primary data-[state=active]:text-white"
                  onClick={() => setActiveTab("agent-flow")}
                >
                  <Network className="mr-2 h-4 w-4" />
                  Agent Flow
                </TabsTrigger>
                <TabsTrigger
                  value="execution"
                  className="data-[state=active]:bg-primary data-[state=active]:text-white"
                  onClick={() => setActiveTab("execution")}
                >
                  <Play className="mr-2 h-4 w-4" />
                  Execution
                </TabsTrigger>
              </TabsList>

              {/* Agent Flow Tab */}
              <TabsContent value="agent-flow" className="mt-0">
                <Card className="bg-background-card shadow-card border-gray-800 mb-6">
                  <CardHeader className="py-2 px-6 flex flex-row justify-between items-center">
                    <CardTitle className="text-lg font-heading">Agent Flow Configuration</CardTitle>
                    <Button
                      className="bg-primary hover:bg-opacity-80 flex items-center gap-2"
                      size="sm"
                      onClick={handleBuildGraph}
                    >
                      <LoaderCircle className="h-4 w-4" />
                      Load Flow
                    </Button>
                  </CardHeader>
                  <CardContent className="pt-2 px-4 pb-4">
                    <p className="text-sm text-gray-400">
                      Configure your agent workflow and build a graph to execute with the Agentic AI system.
                      Click "Build Graph" to create a runnable graph and start execution.
                    </p>
                  </CardContent>
                </Card>
                
                <ReactFlowProvider>
                  <AgentFlowGraph selectedFlow={selectedFlow} setSelectedFlow={setSelectedFlow} />
                </ReactFlowProvider>
              </TabsContent>

              {/* Execution Tab */}
              <TabsContent value="execution" className="mt-0">
                {/* TODO: Don't allow the user to chat with the model if there isn't any active 'builtGraphId' */}
                <StreamingDataProvider>
                  <ReactFlowProvider>
                    <ExecutionTab runId={selectedGraphId} />
                  </ReactFlowProvider>
                </StreamingDataProvider>
              </TabsContent>
            </Tabs>
          </motion.div>
        </main>
        
        <StatusBar />
      </div>
    </div>
  );
}