import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './styles.css';
import { USER_ROLE } from './components/types/roles';
import Toolbar from './components/navigation/Toolbar';
import WelcomeContent from './components/about/WelcomeContent';
import AIContent from './components/about/AIContent';
import ProjectForm from './components/dataset/ProjectForm';
import FormTable from './components/shared/FormTable';
import Statistics from './components/statistics/Statistics';
import SavedPrompt from './components/inference/SavedPrompt';
import DataSetTable from './components/dataset/DataSetTable';
import TrainingForm from './components/training/TrainingForm';
import ChatComponent from './components/inference/ChatContainer';
import DatasetPreparationTable from './components/dataset/DatasetPreparationTable';
import HelmForm from './components/dataset/HelmForm';

const App: React.FC = () => {
  const [role, setRole] = useState<string>(USER_ROLE);

  return (
    <Router>
      <div className="app">
        <Toolbar role={role} setRole={setRole} />
        <div className="main-content">
          <Routes>
            <Route path="/" element={<WelcomeContent />} />
            <Route path="/ai-content" element={<AIContent />} />
            <Route path="/create-dataset" element={<ProjectForm />} />
            <Route path="/prepare-dataset" element={<HelmForm />} />
            <Route path="/deployed-datasets" element={<DatasetPreparationTable />} />
            <Route path="/dataset-table" element={<DataSetTable />} />
            <Route path="/train-form" element={<TrainingForm />} />
            <Route path="/form-table" element={<FormTable />} />
            <Route path="/chatbot" element={<ChatComponent />} />
            <Route path="/saved-prompts" element={<SavedPrompt />} />
            <Route path="/statistics" element={<Statistics />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
};

export default App;
