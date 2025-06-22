import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { motion } from 'framer-motion';
import { 
  Edit2, 
  Settings, 
} from 'lucide-react';

interface ResourceCardProps {
    resource: any;
    selectedResourceType: string;
    handleEditResource: (resource: any, type: 'agent' | 'mcp' | 'retriever') => void;
}

export const ResourceCard = ({ 
    resource, 
    selectedResourceType, 
    handleEditResource,
  }: ResourceCardProps) => {
    const isAgent = selectedResourceType === 'agent';
    const isMcp = selectedResourceType === 'mcp';
    const isRetriever = selectedResourceType === 'retriever';

    return (
      <motion.div
        key={resource.id}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <Card className="bg-background-card shadow-card border-gray-800 h-full flex flex-col">
          <CardHeader className={`py-4 px-6 ${resource.color} bg-opacity-10 border-b border-gray-800`}>
            <div className="flex justify-between items-start">
              <div className="flex flex-col items-center justify-center">
                <div className={`${resource.color} p-2 rounded-lg text-white`}>
                  {resource.icon}
                </div>
              </div>
              <CardTitle className="text-lg font-heading">{resource.name}</CardTitle>
              <Button 
                variant="ghost" 
                size="sm" 
                className="text-gray-400 hover:text-gray-100"
                onClick={() => handleEditResource(resource, selectedResourceType as 'agent' | 'mcp' | 'retriever')}
              >
                <Edit2 className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-4 flex-grow">
            <p className="text-sm text-gray-400">{resource.description}</p>
            <div className="mt-4 space-y-2">
              {isAgent && (
                <>
                  <div className="flex justify-between">
                    <span className="text-xs text-gray-500">Type:</span>
                    <span className="text-xs font-medium">{resource.type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-gray-500">Model:</span>
                    <span className="text-xs font-medium">{resource.model_name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-gray-500">Temperature:</span>
                    <span className="text-xs font-medium">{resource.temperature}</span>
                  </div>
                </>
              )}
              {isMcp && (
                <>
                  <div className="flex justify-between">
                    <span className="text-xs text-gray-500">Status:</span>
                    <span className={`text-xs font-medium ${resource.enabled ? 'text-green-400' : 'text-red-400'}`}>
                      {resource.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-gray-500">Timeout:</span>
                    <span className="text-xs font-medium">{resource.timeout}s</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-gray-500">Retries:</span>
                    <span className="text-xs font-medium">{resource.retry_count}</span>
                  </div>
                </>
              )}
              {isRetriever && (
                <>
                  <div className="flex justify-between">
                    <span className="text-xs text-gray-500">Type:</span>
                    <span className="text-xs font-medium">{resource.type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-gray-500">Max Results:</span>
                    <span className="text-xs font-medium">{resource.max_results}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-gray-500">User Data Only:</span>
                    <span className={`text-xs font-medium ${resource.use_only_user_data ? 'text-green-400' : 'text-blue-400'}`}>
                      {resource.use_only_user_data ? 'Yes' : 'No'}
                    </span>
                  </div>
                </>
              )}
            </div>
          </CardContent>
          <CardFooter className="px-6 py-4 border-t border-gray-800 bg-background-dark">
            <Button 
              variant="outline" 
              size="sm" 
              className="w-full flex items-center justify-center gap-2"
            >
              <Settings className="h-3 w-3" />
              Configure
            </Button>
          </CardFooter>
        </Card>
      </motion.div>
    );
  };