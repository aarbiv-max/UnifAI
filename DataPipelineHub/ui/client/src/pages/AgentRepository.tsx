import React, { useState } from 'react';
import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { ResourceCard } from '../components/agentic-ai/repository/ResourceCard';
import { sampleAgents, sampleMCPs, sampleRetrievers } from '../components/agentic-ai/repository/static-data/exampleResources'
import { 
  Plus, 
  Search, 
  Bot, 
  Server,
  Layers,
} from 'lucide-react';
import { 
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";

export default function AgentRepository() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [agents, setAgents] = useState(sampleAgents);
  const [mcps, setMcps] = useState(sampleMCPs);
  const [retrievers, setRetrievers] = useState(sampleRetrievers);
  const [selectedResourceType, setSelectedResourceType] = useState('agent');
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [currentResource, setCurrentResource] = useState<any>(null);
  const [dialogType, setDialogType] = useState<'agent' | 'mcp' | 'retriever'>('agent');

  const handleEditResource = (resource: any, type: 'agent' | 'mcp' | 'retriever') => {
    setCurrentResource(resource);
    setDialogType(type);
    setIsDialogOpen(true);
  };

  const handleSaveResource = (e: React.FormEvent) => {
    e.preventDefault();
    setIsDialogOpen(false);
    // In a real app, we would save the resource to the backend
    console.log('Saving resource:', currentResource, 'Type:', dialogType);
  };

  const handleCreateNew = () => {
    // Logic to create new resource based on selectedResourceType
    console.log('Creating new:', selectedResourceType);
  };

  const getCurrentResources = () => {
    switch (selectedResourceType) {
      case 'agent': return agents;
      case 'mcp': return mcps;
      case 'retriever': return retrievers;
      default: return [];
    }
  };

  const getResourceCount = (type: string) => {
    switch (type) {
      case 'agent': return agents.length;
      case 'mcp': return mcps.length;
      case 'retriever': return retrievers.length;
      default: return 0;
    }
  };

  const renderEditDialog = () => {
    if (!currentResource) return null;

    return (
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="bg-background-card border-gray-800 text-foreground max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              Edit {dialogType === 'agent' ? 'Agent' : dialogType === 'mcp' ? 'MCP Server' : 'Retriever'} Configuration
            </DialogTitle>
            <DialogDescription>
              Modify the {dialogType === 'agent' ? 'agent' : dialogType === 'mcp' ? 'MCP server' : 'retriever'} settings to customize its behavior.
            </DialogDescription>
          </DialogHeader>
          
          <form onSubmit={handleSaveResource} className="space-y-4">
            {/* Common fields */}
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input 
                id="name" 
                value={currentResource.name}
                onChange={(e) => setCurrentResource({...currentResource, name: e.target.value})}
                className="bg-background-dark"
              />
            </div>

            {/* Agent-specific fields */}
            {dialogType === 'agent' && (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="agent-type">Agent Type</Label>
                    <Select 
                      value={currentResource.type}
                      onValueChange={(value) => setCurrentResource({...currentResource, type: value})}
                    >
                      <SelectTrigger id="agent-type" className="bg-background-dark">
                        <SelectValue placeholder="Select agent type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="nlp">NLP</SelectItem>
                        <SelectItem value="retrieval">Retrieval</SelectItem>
                        <SelectItem value="coding">Coding</SelectItem>
                        <SelectItem value="planning">Planning</SelectItem>
                        <SelectItem value="conversation">Conversation</SelectItem>
                        <SelectItem value="document">Document</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="model-name">Model</Label>
                    <Select 
                      value={currentResource.model_name}
                      onValueChange={(value) => setCurrentResource({...currentResource, model_name: value})}
                    >
                      <SelectTrigger id="model-name" className="bg-background-dark">
                        <SelectValue placeholder="Select model" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="gpt-4">GPT-4</SelectItem>
                        <SelectItem value="gpt-3.5-turbo">GPT-3.5 Turbo</SelectItem>
                        <SelectItem value="claude-2">Claude 2</SelectItem>
                        <SelectItem value="llama-2">Llama 2</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="temperature">Temperature</Label>
                  <div className="flex items-center gap-4">
                    <Input
                      id="temperature"
                      type="range"
                      min="0"
                      max="1"
                      step="0.1"
                      value={currentResource.temperature}
                      onChange={(e) => setCurrentResource({...currentResource, temperature: parseFloat(e.target.value)})}
                      className="flex-grow"
                    />
                    <span className="w-10 text-center">{currentResource.temperature}</span>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="system-prompt">System Prompt</Label>
                  <Textarea 
                    id="system-prompt"
                    value={currentResource.system_prompt}
                    onChange={(e) => setCurrentResource({...currentResource, system_prompt: e.target.value})}
                    rows={6}
                    className="bg-background-dark resize-none"
                  />
                </div>
              </>
            )}

            {/* MCP-specific fields */}
            {dialogType === 'mcp' && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="mcp-url">MCP Server URL</Label>
                  <Input 
                    id="mcp-url" 
                    value={currentResource.url}
                    onChange={(e) => setCurrentResource({...currentResource, url: e.target.value})}
                    className="bg-background-dark"
                    placeholder="https://api.example.com/mcp"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="mcp-token">Authentication Token</Label>
                  <Input 
                    id="mcp-token" 
                    type="password"
                    value={currentResource.token}
                    onChange={(e) => setCurrentResource({...currentResource, token: e.target.value})}
                    className="bg-background-dark"
                    placeholder="Enter authentication token"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="timeout">Timeout (seconds)</Label>
                    <Input 
                      id="timeout" 
                      type="number"
                      value={currentResource.timeout}
                      onChange={(e) => setCurrentResource({...currentResource, timeout: parseInt(e.target.value)})}
                      className="bg-background-dark"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="retry-count">Retry Count</Label>
                    <Input 
                      id="retry-count" 
                      type="number"
                      value={currentResource.retry_count}
                      onChange={(e) => setCurrentResource({...currentResource, retry_count: parseInt(e.target.value)})}
                      className="bg-background-dark"
                    />
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox 
                    id="enabled"
                    checked={currentResource.enabled}
                    onCheckedChange={(checked) => setCurrentResource({...currentResource, enabled: checked})}
                  />
                  <Label htmlFor="enabled">Enable MCP Server</Label>
                </div>
              </>
            )}

            {/* Retriever-specific fields */}
            {dialogType === 'retriever' && (
              <>
                <div className="flex items-center space-x-2">
                  <Checkbox 
                    id="user-data-only"
                    checked={currentResource.use_only_user_data}
                    onCheckedChange={(checked) => setCurrentResource({...currentResource, use_only_user_data: checked})}
                  />
                  <Label htmlFor="user-data-only">Use only user data for retrieval</Label>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="max-results">Max Results</Label>
                    <Input 
                      id="max-results" 
                      type="number"
                      value={currentResource.max_results}
                      onChange={(e) => setCurrentResource({...currentResource, max_results: parseInt(e.target.value)})}
                      className="bg-background-dark"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="similarity-threshold">Similarity Threshold</Label>
                    <div className="flex items-center gap-4">
                      <Input
                        id="similarity-threshold"
                        type="range"
                        min="0"
                        max="1"
                        step="0.1"
                        value={currentResource.similarity_threshold}
                        onChange={(e) => setCurrentResource({...currentResource, similarity_threshold: parseFloat(e.target.value)})}
                        className="flex-grow"
                      />
                      <span className="w-10 text-center">{currentResource.similarity_threshold}</span>
                    </div>
                  </div>
                </div>
                
                {/* Type-specific options */}
                {currentResource.type === 'slack' && (
                  <div className="space-y-2">
                    <Label>Slack Channels</Label>
                    <div className="grid grid-cols-2 gap-2">
                      {currentResource.channels?.map((channel: string) => (
                        <div key={channel} className="flex items-center space-x-2">
                          <Checkbox 
                            id={`channel-${channel}`}
                            checked={currentResource.selected_channels?.includes(channel)}
                            onCheckedChange={(checked) => {
                              const selectedChannels = currentResource.selected_channels || [];
                              if (checked) {
                                setCurrentResource({
                                  ...currentResource, 
                                  selected_channels: [...selectedChannels, channel]
                                });
                              } else {
                                setCurrentResource({
                                  ...currentResource, 
                                  selected_channels: selectedChannels.filter((c: string) => c !== channel)
                                });
                              }
                            }}
                          />
                          <Label htmlFor={`channel-${channel}`}>#{channel}</Label>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {currentResource.type === 'document' && (
                  <div className="space-y-2">
                    <Label>File Types</Label>
                    <div className="grid grid-cols-2 gap-2">
                      {currentResource.file_types?.map((type: string) => (
                        <div key={type} className="flex items-center space-x-2">
                          <Checkbox 
                            id={`type-${type}`}
                            checked={currentResource.selected_file_types?.includes(type)}
                            onCheckedChange={(checked) => {
                              const selectedTypes = currentResource.selected_file_types || [];
                              if (checked) {
                                setCurrentResource({
                                  ...currentResource, 
                                  selected_file_types: [...selectedTypes, type]
                                });
                              } else {
                                setCurrentResource({
                                  ...currentResource, 
                                  selected_file_types: selectedTypes.filter((t: string) => t !== type)
                                });
                              }
                            }}
                          />
                          <Label htmlFor={`type-${type}`}>.{type}</Label>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {currentResource.type === 'web' && (
                  <div className="space-y-2">
                    <Label>Web Domains</Label>
                    <div className="grid grid-cols-1 gap-2">
                      {currentResource.domains?.map((domain: string) => (
                        <div key={domain} className="flex items-center space-x-2">
                          <Checkbox 
                            id={`domain-${domain}`}
                            checked={currentResource.selected_domains?.includes(domain)}
                            onCheckedChange={(checked) => {
                              const selectedDomains = currentResource.selected_domains || [];
                              if (checked) {
                                setCurrentResource({
                                  ...currentResource, 
                                  selected_domains: [...selectedDomains, domain]
                                });
                              } else {
                                setCurrentResource({
                                  ...currentResource, 
                                  selected_domains: selectedDomains.filter((d: string) => d !== domain)
                                });
                              }
                            }}
                          />
                          <Label htmlFor={`domain-${domain}`}>{domain}</Label>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
            
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" className="bg-[#8A2BE2] hover:bg-opacity-80">
                Save Changes
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    );
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Header title="Agent Repository" onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} />

        <main className="flex-1 overflow-y-auto p-6 bg-background-dark">
          <div className="grid grid-cols-12 gap-6">
            {/* Resources Sidebar */}
            <div className="col-span-12 md:col-span-3 lg:col-span-2">
              <Card className="bg-background-card shadow-card border-gray-800 flex flex-col" style={{ height: 'calc(100vh - 100px)' }}>
                <CardHeader className="py-3 px-4 border-b border-gray-800 flex-shrink-0">
                  <div className="flex justify-between items-center">
                    <CardTitle className="text-sm font-medium">Resources</CardTitle>
                    <Button variant="ghost" size="sm" className="h-7 w-7 p-0">
                      <Layers className="h-4 w-4" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="p-0 flex-1 overflow-y-auto">
                  <div className="space-y-1">
                    <Button
                      variant="ghost"
                      className={`w-full justify-start px-4 py-3 rounded-none ${
                        selectedResourceType === 'agent' ? 'bg-[#8A2BE2] bg-opacity-20 text-[#8A2BE2]' : 'text-gray-400'
                      }`}
                      onClick={() => setSelectedResourceType('agent')}
                    >
                      <Bot className="h-4 w-4 mr-2" />
                      Agents ({getResourceCount('agent')})
                    </Button>
                    <Button
                      variant="ghost"
                      className={`w-full justify-start px-4 py-3 rounded-none ${
                        selectedResourceType === 'mcp' ? 'bg-[#8A2BE2] bg-opacity-20 text-[#8A2BE2]' : 'text-gray-400'
                      }`}
                      onClick={() => setSelectedResourceType('mcp')}
                    >
                      <Server className="h-4 w-4 mr-2" />
                      MCPs ({getResourceCount('mcp')})
                    </Button>
                    <Button
                      variant="ghost"
                      className={`w-full justify-start px-4 py-3 rounded-none ${
                        selectedResourceType === 'retriever' ? 'bg-[#8A2BE2] bg-opacity-20 text-[#8A2BE2]' : 'text-gray-400'
                      }`}
                      onClick={() => setSelectedResourceType('retriever')}
                    >
                      <Search className="h-4 w-4 mr-2" />
                      Retrievers ({getResourceCount('retriever')})
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Main Content Area */}
            <div className="col-span-12 md:col-span-9 lg:col-span-10">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-h-screen overflow-y-auto" style={{ height: 'calc(100vh - 100px)' }}>
                {getCurrentResources().map((resource) => <ResourceCard resource={resource} selectedResourceType={selectedResourceType} handleEditResource={handleEditResource}/>)}
              </div>
            </div>
          </div>

          {/* Edit Dialog */}
          {renderEditDialog()}
          </main>
        </div>
    </div>
  );
}