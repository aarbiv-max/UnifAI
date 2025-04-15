import React, { useEffect, useState } from 'react';
import axios from '../../http/axiosLLMConfig';
import 'chart.js/auto';
import '../../styles.css';
import Charts from '../shared/Charts';

interface ModelData {
  id: string;
  contextLength: number;
  modelName: string;
  modelType: string;
  project: string;
}

const StatisticsGraphs: React.FC = () => {
  const [data, setData] = useState<ModelData[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get('/api/backend/getModels');
        const transformedData = response.data[0].adapters.map((item: any) => ({
          id: item.adapter_uid,
          contextLength: item?.context_length,
          modelName: item.name,
          modelType: response.data[0].model_type,
          project: item.project,
        }));
        
        // Legendary Code (might be relevant again in the near future) 
        // const transformedData = response.data.map((item: any) => ({
        //   id: item._id,
        //   contextLength: item.context_length,
        //   modelName: item.base_model,
        //   modelType: item.model_type,
        //   project: item.project,
        // }));
        setData(transformedData);
      } catch (error) {
        console.error('Error fetching model data:', error);
      }
    };

    fetchData();
  }, []);

  const getProjectsData = () => {
    const projectCounts = data.reduce((acc: Record<string, number>, item) => {
      acc[item.project] = (acc[item.project] || 0) + 1;
      return acc;
    }, {});

    return Object.entries(projectCounts).map(([key, value], idx) => ({
      id: idx,
      label: key,
      value: value,
    }));
  };

  const getModelNameData = () => {
    const modelNameCounts = data.reduce((acc: Record<string, number>, item) => {
      acc[item.modelName] = (acc[item.modelName] || 0) + 1;
      return acc;
    }, {});

    return Object.entries(modelNameCounts).map(([key, value], idx) => ({
      id: idx,
      label: key,
      value: value,
    }));
  };

  const getBarChartData = () => {
    const projects = Array.from(new Set(data.map((item) => item.project)));
    const contextLengths = projects.map((project) =>
      data
        .filter((item) => item.project === project)
        .reduce((sum, item) => sum + item.contextLength, 0)
    );
    return { projects, contextLengths };
  };

  const getLineChartData = () => {
    const modelNames = data.map((item) => item.modelName);
    const contextLengths = data.map((item) => item.contextLength);
    return { modelNames, contextLengths };
  };



  return (
    <div className="statistics-graphs">
      <div className="graph-row">
        <Charts
          type="pie"
          data={getProjectsData()}
          className="graph-container"
          title="Project Distribution"
        />
        <Charts
          type="pie"
          data={getModelNameData()}
          className="graph-container"
          title="Model Name Distribution"
        />
      </div>
      <div className="graph-row">
        <Charts
          type="bar"
          data={getBarChartData().projects.map((project, idx) => ({
            label: project,
            value: getBarChartData().contextLengths[idx],
          }))}
          className="graph-container"
          title="Context Length by Project"
          label="Context Length"
          isHidden={true}
        />
        <Charts
          type="line"
          data={getLineChartData().modelNames.map((modelName, idx) => ({
            label: modelName,
            value: getLineChartData().contextLengths[idx],
          }))}
          className="graph-container"
          title="Context Length by Model"
          label="Context Length"
        />
      </div>
    </div>
  );
};

export default StatisticsGraphs;
