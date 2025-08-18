import React from "react";
import {
  Bot,
  Settings,
  MessagesSquare,
  FileText,
  Brain,
  Wrench,
  Circle,
  Server,
  Search,
  GitBranch,
  Box,
} from "lucide-react";

export interface CategoryDisplay {
  icon: React.ReactNode;
  color: string;
}

export const getCategoryDisplay = (category: string): CategoryDisplay => {
  const categoryMap: { [key: string]: CategoryDisplay } = {
    llms: { icon: <Brain className="w-4 h-4" />, color: "#8A2BE2" },
    tools: { icon: <Wrench className="w-4 h-4" />, color: "#00B0FF" },
    nodes: { icon: <Circle className="w-4 h-4" />, color: "#FFB300" },
    providers: { icon: <Server className="w-4 h-4" />, color: "#FF5722" },
    retrievers: { icon: <Search className="w-4 h-4" />, color: "#4CAF50" },
    conditions: { icon: <GitBranch className="w-4 h-4" />, color: "#9C27B0" },
    default: { icon: <Box className="w-4 h-4" />, color: "#607D8B" },
  };
  return categoryMap[category] || categoryMap.default;
};

export const getCategoryDisplayName = (category: string) => {
  const nameMap: { [key: string]: string } = {
    nodes: "Nodes",
    llms: "LLMs",
    tools: "Tools",
    retrievers: "Retrievers",
    providers: "Providers",
    conditions: "Conditions",
  };

  return (
    nameMap[category] || category.charAt(0).toUpperCase() + category.slice(1)
  );
};