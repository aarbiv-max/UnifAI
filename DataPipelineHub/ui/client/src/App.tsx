import { Route, Switch } from "wouter";
import Dashboard from "@/pages/Dashboard";
import Configuration from "@/pages/Configuration";
import JiraIntegration from "@/pages/JiraIntegration";
import SlackIntegration from "@/pages/SlackIntegration";
import Documents from "@/pages/Documents";
import AgenticAI from "@/pages/AgenticAI";
import AgentRepository from "@/pages/AgentRepository";
import NotFound from "@/pages/not-found";
import { useEffect } from "react";
import { ProjectProvider } from '@/contexts/ProjectContext';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { AuthProvider } from '@/contexts/AuthContext';
import ProtectedRoute from '@/components/auth/ProtectedRoute';

function App() {
  // Set document title
  useEffect(() => {
    document.title = "DataFlow Pro - Modern Pipeline Management";
  }, []);

  return (
    <ThemeProvider>
      <AuthProvider>
        <ProjectProvider>
          <ProtectedRoute>
            <Switch>
              <Route path="/" component={Dashboard} />
              <Route path="/jira" component={JiraIntegration} />
              <Route path="/slack" component={SlackIntegration} />
              <Route path="/documents" component={Documents} />
              <Route path="/repository" component={AgentRepository} />
              <Route path="/agentic-ai" component={AgenticAI} />
              <Route path="/configuration" component={Configuration} />
              <Route component={NotFound} />
            </Switch>
          </ProtectedRoute>
        </ProjectProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;