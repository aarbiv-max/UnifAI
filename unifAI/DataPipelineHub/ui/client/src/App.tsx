import { Route, Switch } from "wouter";
import Dashboard from "@/pages/Dashboard";
import Configuration from "@/pages/Configuration";
import JiraIntegration from "@/pages/JiraIntegration";
import SlackIntegration from "@/features/slack/SlackIntegration";
import Documents from "@/pages/Documents";
import AgenticAI from "@/pages/AgenticAI";
import NotFound from "@/pages/not-found";
import { useEffect } from "react";
import { ProjectProvider } from '@/contexts/ProjectContext';
import { ThemeProvider } from '@/contexts/ThemeContext';
import SlackAddSourcePage from "@/features/slack/SlackAddSourcePage";
import { Toaster } from "@/components/ui/toaster";

function App() {
  // Set document title
  useEffect(() => {
    document.title = "DataFlow Pro - Modern Pipeline Management";
  }, []);

  return (
    <ThemeProvider>
      <ProjectProvider>
        <Switch>
          <Route path="/" component={Dashboard} />
          <Route path="/configuration" component={Configuration} />
          <Route path="/jira" component={JiraIntegration} />
          <Route path="/slack" component={SlackIntegration} />
          <Route path="/documents" component={Documents} />
          <Route path="/agentic-ai" component={AgenticAI} />
          <Route path="/slack/add-source" component={SlackAddSourcePage} />
          <Route component={NotFound} />
        </Switch>
        <Toaster />
      </ProjectProvider>
    </ThemeProvider>
  );
}

export default App;
